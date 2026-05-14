"""
🎨 Effects Engine — التأثيرات البصرية السينمائية
═══════════════════════════════════════════════════════════════
محرك تأثيرات احترافي يوفر:
  ✓ Scale & Crop للأبعاد العمودية (1080x1920)
  ✓ Zoom حقيقي تدريجي (zoompan) - ليس scale ثابت!
  ✓ Camera Shake طبيعي بدوال مثلثية
  ✓ Loop ذكي للفيديوهات القصيرة
  ✓ Cinematic Color Grading
  ✓ Letterbox سينمائي
  ✓ Glitch / Flash / Vignette إضافية

ضع في: engine/video/effects_engine.py
═══════════════════════════════════════════════════════════════
"""

import os
import shutil
import logging
import subprocess
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)


class EffectsEngine:
    """محرك التأثيرات البصرية السينمائية."""

    # ─── إعدادات الجودة ───────────────────────────────────────────
    QUALITY_PRESETS = {
        "medium": {"crf": 23, "preset": "fast"},
        "high":   {"crf": 19, "preset": "fast"},   # fast لـ GitHub Actions
        "ultra":  {"crf": 17, "preset": "medium"},
    }

    # ─── Timeout افتراضي ──────────────────────────────────────────
    DEFAULT_TIMEOUT = 180  # 3 دقائق

    # ════════════════════════════════════════════════════════════════
    def __init__(self, video_width: int = 1080, video_height: int = 1920):
        """
        Args:
            video_width: عرض الفيديو
            video_height: ارتفاع الفيديو
        """
        self.w = video_width
        self.h = video_height
        self.fps = int(os.getenv("VIDEO_FPS", "30"))
        self.quality = os.getenv("VIDEO_QUALITY", "high")

        self.temp_dir = Path(os.getenv("TEMP_DIR", "./temp"))
        self.temp_dir.mkdir(parents=True, exist_ok=True)

        # إعدادات قابلة للتخصيص
        self.enable_grain = os.getenv("ENABLE_FILM_GRAIN", "true").lower() == "true"
        self.enable_vignette = os.getenv("ENABLE_VIGNETTE", "true").lower() == "true"

        logger.debug(f"🎨 EffectsEngine | {self.w}x{self.h}@{self.fps}fps")

    # ════════════════════════════════════════════════════════════════
    #                    Scale & Crop
    # ════════════════════════════════════════════════════════════════
    def scale_and_crop(self, input_path: str, output_path: str) -> str:
        """تحجيم وقص الفيديو للأبعاد العمودية المطلوبة."""
        if not self._validate_input(input_path):
            return self._safe_copy(input_path, output_path)

        filter_str = (
            f"scale={self.w}:{self.h}:force_original_aspect_ratio=increase,"
            f"crop={self.w}:{self.h}"
        )

        if self._run_ffmpeg(
            ["-i", input_path, "-vf", filter_str],
            output_path,
            description="scale_and_crop",
        ):
            return output_path

        return self._safe_copy(input_path, output_path)

    # ════════════════════════════════════════════════════════════════
    #                    Trim (قص)
    # ════════════════════════════════════════════════════════════════
    def trim_clip(
        self,
        input_path: str,
        output_path: str,
        start: float,
        duration: float,
    ) -> str:
        """قص جزء من الفيديو."""
        if not self._validate_input(input_path):
            return self._safe_copy(input_path, output_path)

        if self._run_ffmpeg(
            [
                "-ss", str(start),
                "-i", input_path,
                "-t", str(duration),
            ],
            output_path,
            description=f"trim ({duration:.1f}s)",
        ):
            return output_path

        return self._safe_copy(input_path, output_path)

    # ════════════════════════════════════════════════════════════════
    #                    Zoom Effects
    # ════════════════════════════════════════════════════════════════
    def apply_zoom_effect(
        self,
        input_path: str,
        output_path: str,
        zoom_type: str = "slow_zoom_in",
        duration: float = 3.0,
    ) -> str:
        """
        تطبيق تأثير zoom سينمائي.

        Args:
            zoom_type: slow_zoom_in / slow_zoom_out / drift_right /
                       drift_left / drift_up / drift_down / punch_zoom / static
            duration: مدة المقطع بالثواني
        """
        if not self._validate_input(input_path):
            return self._safe_copy(input_path, output_path)

        zoom_configs = {
            "slow_zoom_in": {
                "z_start": 1.0, "z_end": 1.12,
                "x_expr": "iw/2-(iw/zoom/2)",
                "y_expr": "ih/2-(ih/zoom/2)",
            },
            "slow_zoom_out": {
                "z_start": 1.12, "z_end": 1.0,
                "x_expr": "iw/2-(iw/zoom/2)",
                "y_expr": "ih/2-(ih/zoom/2)",
            },
            "drift_right": {
                "z_start": 1.06, "z_end": 1.06,
                "x_expr": "(iw-iw/zoom)*on/duration",
                "y_expr": "ih/2-(ih/zoom/2)",
            },
            "drift_left": {
                "z_start": 1.06, "z_end": 1.06,
                "x_expr": "(iw-iw/zoom)*(1-on/duration)",
                "y_expr": "ih/2-(ih/zoom/2)",
            },
            "drift_up": {
                "z_start": 1.06, "z_end": 1.06,
                "x_expr": "iw/2-(iw/zoom/2)",
                "y_expr": "(ih-ih/zoom)*(1-on/duration)",
            },
            "drift_down": {
                "z_start": 1.06, "z_end": 1.06,
                "x_expr": "iw/2-(iw/zoom/2)",
                "y_expr": "(ih-ih/zoom)*on/duration",
            },
        }

        # Punch zoom = scale سريع
        if zoom_type == "punch_zoom":
            return self._static_scale(input_path, output_path, 1.15)

        # Static = بدون حركة (نسخ مباشر)
        if zoom_type == "static":
            return self._static_scale(input_path, output_path, 1.0)

        # Zoompan الديناميكي
        cfg = zoom_configs.get(zoom_type, zoom_configs["slow_zoom_in"])
        return self._zoompan(
            input_path, output_path, duration,
            z_start=cfg["z_start"],
            z_end=cfg["z_end"],
            x_expr=cfg["x_expr"],
            y_expr=cfg["y_expr"],
        )

    def _zoompan(
        self,
        inp: str,
        out: str,
        duration: float,
        z_start: float,
        z_end: float,
        x_expr: str,
        y_expr: str,
    ) -> str:
        """تطبيق zoompan تدريجي."""
        n_frames = max(int(duration * self.fps), 1)

        # معادلة الـ zoom التدريجي
        z_delta = z_end - z_start
        if abs(z_delta) > 0.001:
            z_expr = f"{z_start}+{z_delta:.4f}*on/{n_frames}"
        else:
            z_expr = str(z_start)

        # filter بدون trim (لتجنب bug)
        filter_str = (
            f"zoompan="
            f"z='{z_expr}':"
            f"x='{x_expr}':"
            f"y='{y_expr}':"
            f"d={n_frames}:"
            f"s={self.w}x{self.h}:"
            f"fps={self.fps}"
        )

        if self._run_ffmpeg(
            ["-i", inp, "-vf", filter_str, "-t", str(duration)],
            out,
            description=f"zoompan ({z_start}→{z_end})",
        ):
            return out

        # Fallback إلى static scale
        logger.warning("⚠ zoompan فشل، استخدام static scale")
        return self._static_scale(inp, out, (z_start + z_end) / 2)

    def _static_scale(self, inp: str, out: str, scale: float) -> str:
        """Scale ثابت للفيديو."""
        sw = int(self.w * scale)
        sh = int(self.h * scale)
        # تأكد أن الأبعاد زوجية
        sw = sw if sw % 2 == 0 else sw + 1
        sh = sh if sh % 2 == 0 else sh + 1

        if scale == 1.0:
            # بدون تغيير - نسخ سريع
            return self._safe_copy(inp, out)

        filter_str = f"scale={sw}:{sh},crop={self.w}:{self.h}"

        if self._run_ffmpeg(
            ["-i", inp, "-vf", filter_str],
            out,
            description=f"static scale ({scale}x)",
        ):
            return out

        return self._safe_copy(inp, out)

    # ════════════════════════════════════════════════════════════════
    #                    Camera Shake
    # ════════════════════════════════════════════════════════════════
    def apply_smooth_shake(
        self,
        input_path: str,
        output_path: str,
        intensity: float = 2.0,
    ) -> str:
        """تطبيق اهتزاز طبيعي للكاميرا."""
        if not self._validate_input(input_path):
            return self._safe_copy(input_path, output_path)

        margin = max(int(intensity * 2), 4)
        cw = self.w - margin * 2
        ch = self.h - margin * 2
        # تأكد أن الأبعاد زوجية
        cw = cw if cw % 2 == 0 else cw - 1
        ch = ch if ch % 2 == 0 else ch - 1

        # حركة طبيعية بدوال مثلثية بترددات مختلفة
        filter_str = (
            f"crop={cw}:{ch}:"
            f"'{margin}+{intensity:.1f}*sin(2*PI*t*0.7)':"
            f"'{margin}+{intensity:.1f}*cos(2*PI*t*1.1)',"
            f"scale={self.w}:{self.h}"
        )

        if self._run_ffmpeg(
            ["-i", input_path, "-vf", filter_str],
            output_path,
            description=f"shake ({intensity})",
        ):
            return output_path

        return self._safe_copy(input_path, output_path)

    # ════════════════════════════════════════════════════════════════
    #                    Loop
    # ════════════════════════════════════════════════════════════════
    def loop_clip_to_duration(
        self,
        input_path: str,
        output_path: str,
        target_duration: float,
    ) -> str:
        """تكرار الفيديو حتى يصل للمدة المطلوبة."""
        if not self._validate_input(input_path):
            return self._safe_copy(input_path, output_path)

        if self._run_ffmpeg(
            [
                "-stream_loop", "-1",
                "-i", input_path,
                "-t", str(target_duration),
            ],
            output_path,
            description=f"loop ({target_duration:.1f}s)",
        ):
            return output_path

        return self._safe_copy(input_path, output_path)

    # ════════════════════════════════════════════════════════════════
    #                    Cinematic Color Grading
    # ════════════════════════════════════════════════════════════════
    def apply_cinematic_grade(
        self,
        input_path: str,
        output_path: str,
    ) -> str:
        """تطبيق تدرج لوني سينمائي احترافي."""
        if not self._validate_input(input_path):
            return self._safe_copy(input_path, output_path)

        # بناء filter chain
        filters = []

        # Color curves (سينمائي دافئ)
        filters.append(
            "curves="
            "r='0/0 0.2/0.19 0.5/0.53 0.8/0.86 1/1':"
            "g='0/0 0.2/0.19 0.5/0.50 0.8/0.82 1/1':"
            "b='0/0 0.2/0.23 0.5/0.52 0.8/0.78 1/1'"
        )

        # Master contrast
        filters.append("curves=master='0/0 0.15/0.08 0.5/0.5 0.85/0.92 1/1'")

        # Saturation boost
        filters.append("hue=s=1.12")

        # Vignette (اختياري)
        if self.enable_vignette:
            filters.append("vignette=PI/4")

        # Film grain (اختياري)
        if self.enable_grain:
            filters.append("noise=alls=4:allf=t+u")

        filter_chain = ",".join(filters)

        # استخدام إعدادات الجودة
        quality_cfg = self.QUALITY_PRESETS.get(
            self.quality, self.QUALITY_PRESETS["high"]
        )

        if self._run_ffmpeg(
            ["-i", input_path, "-vf", filter_chain],
            output_path,
            description="cinematic grade",
            preset=quality_cfg["preset"],
            crf=quality_cfg["crf"],
            keep_audio=True,
        ):
            return output_path

        return self._safe_copy(input_path, output_path)

    # ════════════════════════════════════════════════════════════════
    #                    Letterbox
    # ════════════════════════════════════════════════════════════════
    def add_letterbox(
        self,
        input_path: str,
        output_path: str,
        bar_ratio: float = 0.055,
    ) -> str:
        """إضافة شرائط سوداء علوية وسفلية (سينمائي)."""
        if not self._validate_input(input_path):
            return self._safe_copy(input_path, output_path)

        bar_h = int(self.h * bar_ratio)

        filter_str = (
            f"drawbox=x=0:y=0:w={self.w}:h={bar_h}:color=black@0.92:t=fill,"
            f"drawbox=x=0:y={self.h-bar_h}:w={self.w}:h={bar_h}:"
            f"color=black@0.92:t=fill"
        )

        if self._run_ffmpeg(
            ["-i", input_path, "-vf", filter_str],
            output_path,
            description="letterbox",
            keep_audio=True,
        ):
            return output_path

        return self._safe_copy(input_path, output_path)

    # ════════════════════════════════════════════════════════════════
    #                    تأثيرات إضافية
    # ════════════════════════════════════════════════════════════════
    def apply_flash(
        self,
        input_path: str,
        output_path: str,
        intensity: float = 1.5,
        duration: float = 0.2,
    ) -> str:
        """تطبيق فلاش أبيض في البداية."""
        if not self._validate_input(input_path):
            return self._safe_copy(input_path, output_path)

        filter_str = (
            f"eq=brightness=0:contrast=1:saturation=1,"
            f"fade=t=in:st=0:d={duration}:color=white"
        )

        if self._run_ffmpeg(
            ["-i", input_path, "-vf", filter_str],
            output_path,
            description="flash",
        ):
            return output_path

        return self._safe_copy(input_path, output_path)

    def apply_glitch(
        self,
        input_path: str,
        output_path: str,
        intensity: float = 0.5,
    ) -> str:
        """تطبيق تأثير glitch."""
        if not self._validate_input(input_path):
            return self._safe_copy(input_path, output_path)

        filter_str = (
            f"noise=alls={int(intensity*30)}:allf=t,"
            f"chromashift=cbh=2:crv=2"
        )

        if self._run_ffmpeg(
            ["-i", input_path, "-vf", filter_str],
            output_path,
            description="glitch",
        ):
            return output_path

        return self._safe_copy(input_path, output_path)

    def apply_blur(
        self,
        input_path: str,
        output_path: str,
        sigma: float = 5.0,
    ) -> str:
        """تطبيق ضبابية."""
        if not self._validate_input(input_path):
            return self._safe_copy(input_path, output_path)

        if self._run_ffmpeg(
            ["-i", input_path, "-vf", f"gblur=sigma={sigma}"],
            output_path,
            description=f"blur ({sigma})",
        ):
            return output_path

        return self._safe_copy(input_path, output_path)

    def apply_fade_in(
        self,
        input_path: str,
        output_path: str,
        duration: float = 1.0,
    ) -> str:
        """fade in من الأسود."""
        if not self._validate_input(input_path):
            return self._safe_copy(input_path, output_path)

        if self._run_ffmpeg(
            ["-i", input_path, "-vf", f"fade=t=in:st=0:d={duration}"],
            output_path,
            description=f"fade_in ({duration}s)",
        ):
            return output_path

        return self._safe_copy(input_path, output_path)

    def apply_fade_out(
        self,
        input_path: str,
        output_path: str,
        duration: float = 1.0,
        video_duration: Optional[float] = None,
    ) -> str:
        """fade out إلى الأسود."""
        if not self._validate_input(input_path):
            return self._safe_copy(input_path, output_path)

        # إذا لم تُحدد مدة الفيديو، احسبها
        if video_duration is None:
            video_duration = self._get_duration(input_path)

        start = max(video_duration - duration, 0)

        if self._run_ffmpeg(
            ["-i", input_path, "-vf", f"fade=t=out:st={start}:d={duration}"],
            output_path,
            description=f"fade_out ({duration}s)",
        ):
            return output_path

        return self._safe_copy(input_path, output_path)

    # ════════════════════════════════════════════════════════════════
    #                    دوال مساعدة داخلية
    # ════════════════════════════════════════════════════════════════
    def _validate_input(self, path: str) -> bool:
        """التحقق من وجود الملف."""
        if not Path(path).exists():
            logger.error(f"❌ الملف غير موجود: {path}")
            return False
        if Path(path).stat().st_size < 1000:
            logger.error(f"❌ الملف فارغ أو تالف: {path}")
            return False
        return True

    def _run_ffmpeg(
        self,
        args: list,
        output_path: str,
        description: str = "FFmpeg",
        preset: str = "fast",
        crf: int = 22,
        keep_audio: bool = False,
    ) -> bool:
        """تشغيل FFmpeg مع إعدادات موحدة."""
        cmd = (
            ["ffmpeg", "-y", "-loglevel", "error"]
            + args
            + [
                "-c:v", "libx264",
                "-preset", preset,
                "-crf", str(crf),
                "-pix_fmt", "yuv420p",
                "-r", str(self.fps),
            ]
        )

        if keep_audio:
            cmd += ["-c:a", "copy"]
        else:
            cmd += ["-an"]

        cmd.append(output_path)

        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                timeout=self.DEFAULT_TIMEOUT,
            )
            if result.returncode == 0:
                return True
            else:
                err = result.stderr.decode("utf-8", errors="ignore")[:200]
                logger.warning(f"⚠ {description} failed: {err}")
                return False
        except subprocess.TimeoutExpired:
            logger.error(f"❌ {description} timeout")
            return False
        except Exception as e:
            logger.error(f"❌ {description} error: {e}")
            return False

    def _safe_copy(self, src: str, dst: str) -> str:
        """نسخ آمن."""
        try:
            if Path(src).exists() and src != dst:
                shutil.copy(src, dst)
        except Exception as e:
            logger.error(f"❌ فشل النسخ: {e}")
        return dst

    def _get_duration(self, path: str) -> float:
        """الحصول على مدة الفيديو."""
        try:
            result = subprocess.run(
                [
                    "ffprobe", "-v", "quiet",
                    "-show_entries", "format=duration",
                    "-of", "default=noprint_wrappers=1:nokey=1",
                    path,
                ],
                capture_output=True,
                text=True,
                timeout=30,
                check=True,
            )
            return float(result.stdout.strip())
        except Exception as e:
            logger.warning(f"⚠ فشل قراءة المدة: {e}")
            return 5.0


# ════════════════════════════════════════════════════════════════════════
#                    اختبار سريع
# ════════════════════════════════════════════════════════════════════════
if __name__ == "__main__":
    import sys

    if len(sys.argv) < 3:
        print("Usage: python effects_engine.py <input.mp4> <output.mp4> [zoom_type]")
        sys.exit(1)

    fx = EffectsEngine()
    zoom = sys.argv[3] if len(sys.argv) > 3 else "slow_zoom_in"

    print(f"🎨 Applying {zoom}...")
    fx.apply_zoom_effect(sys.argv[1], sys.argv[2], zoom, 5.0)
    print(f"✓ Done: {sys.argv[2]}")
