"""
🎞️ Transition Engine — انتقالات xfade سينمائية
═══════════════════════════════════════════════════════════════
محرك انتقالات احترافي يستخدم FFmpeg xfade:
  ✓ 15+ نوع transition
  ✓ FPS Normalization تلقائي
  ✓ تجميع حسب الطاقة (high/medium/low)
  ✓ Fallback إلى concat عند الفشل
  ✓ تنظيف تلقائي للملفات المؤقتة

ضع في: engine/video/transition_engine.py
═══════════════════════════════════════════════════════════════
"""

import os
import json
import random
import shutil
import logging
import subprocess
from pathlib import Path
from typing import Optional, List

logger = logging.getLogger(__name__)


class TransitionEngine:
    """محرك الانتقالات السينمائية بين الـ clips."""

    # ─── تصنيف الـ transitions حسب الطاقة ───────────────────────
    ENERGY_HIGH = [
        "fadeblack",
        "fadewhite",
        "zoomin",
        "pixelize",
        "wipeleft",
        "wiperight",
        "circleopen",
        "diagbl",
    ]

    ENERGY_MEDIUM = [
        "fade",
        "slideup",
        "slidedown",
        "slideleft",
        "slideright",
        "smoothleft",
        "smoothright",
    ]

    ENERGY_LOW = [
        "fade",
        "smoothup",
        "smoothdown",
        "circlecrop",
        "rectcrop",
        "dissolve",
    ]

    ALL = list(set(ENERGY_HIGH + ENERGY_MEDIUM + ENERGY_LOW))

    # ─── خريطة الأسماء المخصصة → xfade الرسمية ──────────────────
    TRANSITION_MAP = {
        # أسماء مخصصة → xfade names
        "auto":              None,  # عشوائي
        "flash_white":       "fadewhite",
        "flash_black":       "fadeblack",
        "fade_black":        "fadeblack",
        "fade_white":        "fadewhite",
        "glitch":            "pixelize",
        "pixel":             "pixelize",
        "zoom_burst":        "zoomin",
        "zoom_in":           "zoomin",
        "whip_right":        "wipeleft",
        "whip_left":         "wiperight",
        "wipe_left":         "wipeleft",
        "wipe_right":        "wiperight",
        "cross_dissolve":    "fade",
        "smooth_fade":       "fade",
        "dissolve":          "dissolve",
        "push_up":           "slideup",
        "push_down":         "slidedown",
        "slide_left":        "slideleft",
        "slide_right":       "slideright",
        "smooth_left":       "smoothleft",
        "smooth_right":      "smoothright",
        "circle_open":       "circleopen",
        "circle_close":      "circleclose",
        "circle_crop":       "circlecrop",
        "rect_crop":         "rectcrop",
        "diag_bl":           "diagbl",
        "diag_br":           "diagbr",
        "diag_tl":           "diagtl",
        "diag_tr":           "diagtr",
    }

    # ─── إعدادات الجودة ───────────────────────────────────────────
    QUALITY_PRESETS = {
        "medium": {"crf": 23, "preset": "fast"},
        "high":   {"crf": 20, "preset": "fast"},
        "ultra":  {"crf": 18, "preset": "medium"},
    }

    DEFAULT_TIMEOUT = 120

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

        # مجلد فرعي للـ transitions
        self.trans_dir = self.temp_dir / "transitions"
        self.trans_dir.mkdir(exist_ok=True)

        logger.debug(f"🎞️ TransitionEngine | {self.w}x{self.h}@{self.fps}fps")

    # ════════════════════════════════════════════════════════════════
    #                    الدالة الرئيسية
    # ════════════════════════════════════════════════════════════════
    def apply_transition(
        self,
        clip_a: str,
        clip_b: str,
        output_path: str,
        transition_type: str = "auto",
        duration: float = 0.2,
    ) -> str:
        """
        تطبيق xfade transition بين clipين.

        Args:
            clip_a: الـ clip الأول
            clip_b: الـ clip الثاني
            output_path: مسار الإخراج
            transition_type: نوع الانتقال (auto / flash_white / glitch / ...)
            duration: مدة الانتقال بالثواني (0.1 - 2.0)
        """
        if not self._validate_inputs(clip_a, clip_b):
            return self._concat_fallback(clip_a, clip_b, output_path)

        # تطبيع الـ clipين
        na = self._unique_temp("na")
        nb = self._unique_temp("nb")

        try:
            self._normalize(clip_a, na)
            self._normalize(clip_b, nb)

            # اختيار xfade
            xfade = self._pick_xfade(transition_type)

            # حساب الـ offset
            dur_a = self._get_duration(na)
            offset = max(dur_a - duration - 0.01, 0.0)

            # إعدادات الجودة
            quality_cfg = self.QUALITY_PRESETS.get(
                self.quality, self.QUALITY_PRESETS["high"]
            )

            cmd = [
                "ffmpeg", "-y", "-loglevel", "error",
                "-i", na,
                "-i", nb,
                "-filter_complex",
                (
                    f"[0:v][1:v]xfade="
                    f"transition={xfade}:"
                    f"duration={duration:.2f}:"
                    f"offset={offset:.3f}[outv]"
                ),
                "-map", "[outv]",
                "-c:v", "libx264",
                "-preset", quality_cfg["preset"],
                "-crf", str(quality_cfg["crf"]),
                "-pix_fmt", "yuv420p",
                "-r", str(self.fps),
                "-an",
                output_path,
            ]

            try:
                result = subprocess.run(
                    cmd,
                    capture_output=True,
                    timeout=self.DEFAULT_TIMEOUT,
                )

                if result.returncode == 0 and Path(output_path).exists():
                    logger.debug(f"✓ Transition '{xfade}' applied")
                    return output_path
                else:
                    err = result.stderr.decode("utf-8", errors="ignore")[:200]
                    logger.warning(f"⚠ xfade '{xfade}' failed: {err}")

            except subprocess.TimeoutExpired:
                logger.warning(f"⚠ xfade '{xfade}' timeout")
            except Exception as e:
                logger.warning(f"⚠ xfade error: {e}")

            # Fallback إلى concat بسيط
            return self._concat_fallback(na, nb, output_path)

        finally:
            # تنظيف الملفات المؤقتة
            self._cleanup_files([na, nb])

    # ════════════════════════════════════════════════════════════════
    #                    تطبيع الفيديو
    # ════════════════════════════════════════════════════════════════
    def _normalize(self, input_path: str, output_path: str) -> str:
        """
        تطبيع FPS و pixel format و dimensions.
        مهم جدًا لـ xfade لأنه يحتاج clips متطابقة تمامًا.
        """
        filter_str = (
            f"fps={self.fps},"
            f"scale={self.w}:{self.h}:force_original_aspect_ratio=decrease,"
            f"pad={self.w}:{self.h}:(ow-iw)/2:(oh-ih)/2,"
            f"setsar=1"
        )

        cmd = [
            "ffmpeg", "-y", "-loglevel", "error",
            "-i", input_path,
            "-vf", filter_str,
            "-c:v", "libx264",
            "-preset", "ultrafast",
            "-crf", "23",
            "-pix_fmt", "yuv420p",
            "-an",
            output_path,
        ]

        try:
            result = subprocess.run(
                cmd, capture_output=True, timeout=self.DEFAULT_TIMEOUT
            )
            if result.returncode == 0:
                return output_path
            logger.warning(f"⚠ normalize failed")
        except subprocess.TimeoutExpired:
            logger.warning("⚠ normalize timeout")
        except Exception as e:
            logger.warning(f"⚠ normalize error: {e}")

        # Fallback
        return self._safe_copy(input_path, output_path)

    # ════════════════════════════════════════════════════════════════
    #                    اختيار الـ xfade
    # ════════════════════════════════════════════════════════════════
    def _pick_xfade(self, transition_type: str) -> str:
        """اختيار نوع xfade المناسب."""
        # 1. اسم مباشر من xfade
        if transition_type in self.ALL:
            return transition_type

        # 2. اسم مخصص من الخريطة
        mapped = self.TRANSITION_MAP.get(transition_type)
        if mapped:
            return mapped

        # 3. auto أو غير معروف → عشوائي
        if transition_type == "auto" or transition_type not in self.TRANSITION_MAP:
            return random.choice(self.ENERGY_MEDIUM)

        # 4. الافتراضي
        return "fade"

    # ════════════════════════════════════════════════════════════════
    #                    Fallback (concat)
    # ════════════════════════════════════════════════════════════════
    def _concat_fallback(
        self,
        a: str,
        b: str,
        output_path: str,
    ) -> str:
        """Fallback عند فشل xfade - concat بسيط."""
        list_file = self._unique_temp("cat", ext="txt")

        try:
            with open(list_file, "w", encoding="utf-8") as f:
                f.write(f"file '{Path(a).resolve()}'\n")
                f.write(f"file '{Path(b).resolve()}'\n")

            cmd = [
                "ffmpeg", "-y", "-loglevel", "error",
                "-f", "concat",
                "-safe", "0",
                "-i", list_file,
                "-c:v", "libx264",
                "-preset", "fast",
                "-crf", "22",
                "-pix_fmt", "yuv420p",
                "-r", str(self.fps),
                "-an",
                output_path,
            ]

            result = subprocess.run(
                cmd,
                capture_output=True,
                timeout=self.DEFAULT_TIMEOUT,
            )

            if result.returncode == 0:
                logger.debug("✓ Concat fallback succeeded")
                return output_path

            logger.warning("⚠ Concat fallback failed")

        except Exception as e:
            logger.error(f"❌ Concat error: {e}")
        finally:
            self._cleanup_files([list_file])

        # آخر fallback: نسخ الـ clip الأول
        return self._safe_copy(a, output_path)

    # ════════════════════════════════════════════════════════════════
    #                    دوال مساعدة
    # ════════════════════════════════════════════════════════════════
    def _validate_inputs(self, *paths: str) -> bool:
        """التحقق من وجود الملفات."""
        for path in paths:
            if not Path(path).exists():
                logger.error(f"❌ الملف غير موجود: {path}")
                return False
            if Path(path).stat().st_size < 1000:
                logger.error(f"❌ الملف فارغ أو تالف: {path}")
                return False
        return True

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
            return 3.0

    def _unique_temp(self, prefix: str, ext: str = "mp4") -> str:
        """توليد اسم ملف فريد."""
        pid = os.getpid()
        rnd = random.randint(10000, 99999)
        return str(self.trans_dir / f"{prefix}_{pid}_{rnd}.{ext}")

    def _safe_copy(self, src: str, dst: str) -> str:
        """نسخ آمن."""
        try:
            if Path(src).exists() and src != dst:
                shutil.copy(src, dst)
        except Exception as e:
            logger.error(f"❌ فشل النسخ: {e}")
        return dst

    def _cleanup_files(self, files: List[str]) -> None:
        """حذف ملفات مؤقتة."""
        for f in files:
            try:
                Path(f).unlink(missing_ok=True)
            except Exception:
                pass

    # ════════════════════════════════════════════════════════════════
    #                    دوال عامة إضافية
    # ════════════════════════════════════════════════════════════════
    def get_random_transition(self, energy: str = "medium") -> str:
        """
        الحصول على transition عشوائي حسب الطاقة.

        Args:
            energy: high / medium / low
        """
        if energy == "high":
            return random.choice(self.ENERGY_HIGH)
        elif energy == "low":
            return random.choice(self.ENERGY_LOW)
        else:
            return random.choice(self.ENERGY_MEDIUM)

    def list_transitions(self) -> dict:
        """قائمة بكل الـ transitions المتاحة."""
        return {
            "high":   self.ENERGY_HIGH,
            "medium": self.ENERGY_MEDIUM,
            "low":    self.ENERGY_LOW,
            "custom": list(self.TRANSITION_MAP.keys()),
        }

    def cleanup(self) -> None:
        """تنظيف كل الملفات المؤقتة للـ transitions."""
        try:
            count = 0
            for f in self.trans_dir.glob("*"):
                f.unlink(missing_ok=True)
                count += 1
            if count:
                logger.info(f"🧹 تم تنظيف {count} ملف transition")
        except Exception as e:
            logger.warning(f"⚠ فشل التنظيف: {e}")


# ════════════════════════════════════════════════════════════════════════
#                    اختبار سريع
# ════════════════════════════════════════════════════════════════════════
if __name__ == "__main__":
    import sys

    if len(sys.argv) < 4:
        print("Usage: python transition_engine.py <clip_a> <clip_b> <output> [type]")
        print("\nAvailable transitions:")
        engine = TransitionEngine()
        trans = engine.list_transitions()
        for category, items in trans.items():
            print(f"  {category}: {', '.join(items[:8])}{'...' if len(items) > 8 else ''}")
        sys.exit(1)

    engine = TransitionEngine()
    transition = sys.argv[4] if len(sys.argv) > 4 else "auto"

    print(f"🎞️ Applying '{transition}' transition...")
    result = engine.apply_transition(
        sys.argv[1], sys.argv[2], sys.argv[3], transition, 0.5
    )
    print(f"✓ Done: {result}")
