"""
🎬 Remotion Renderer — التصدير النهائي للفيديو بـ Remotion
═══════════════════════════════════════════════════════════════
محرك التصدير الجديد يوفر:
  ✓ MP4 احترافي مع دعم كامل للعربية (RTL + Shaping)
  ✓ 3 مستويات جودة (medium/high/ultra)
  ✓ Metadata كاملة
  ✓ Thumbnails متعددة (عبر FFmpeg المساعد)
  ✓ تحقق من حجم الملف
  ✓ تنظيف ذكي للملفات المؤقتة

ضع في: engine/render/remotion_renderer.py
═══════════════════════════════════════════════════════════════
"""

import os
import json
import shutil
import logging
import subprocess
from pathlib import Path
from typing import Optional, Dict, List

from .video_utils import VideoUtils

logger = logging.getLogger(__name__)


class RemotionRenderer:
    """محرك التصدير النهائي باستخدام Remotion."""

    # ─── Presets الجودة (متطابق مع main.py) ──────────────────────
    QUALITY_PRESETS = {
        "medium": {
            "crf":          "23",
            "jpeg_quality": "80",
            "concurrency":  "2",
            "audio_bitrate": "128k",
        },
        "high": {
            "crf":          "19",
            "jpeg_quality": "90",
            "concurrency":  "4",
            "audio_bitrate": "192k",
        },
        "ultra": {
            "crf":          "17",
            "jpeg_quality": "95",
            "concurrency":  "8",
            "audio_bitrate": "256k",
        },
    }

    # ─── Legacy presets (للتوافق الرجعي) ─────────────────────────
    LEGACY_PRESETS = {
        "tiktok":  "high",
        "reels":   "ultra",
        "shorts":  "high",
        "preview": "medium",
    }

    # ─── حدود المنصات (MB) ────────────────────────────────────────
    PLATFORM_LIMITS = {
        "youtube_shorts": 256,
        "tiktok":         287,
        "instagram":      650,
        "twitter":        512,
    }

    DEFAULT_TIMEOUT = 1200  # 20 دقيقة (Remotion أبطأ من FFmpeg)

    # ════════════════════════════════════════════════════════════════
    def __init__(self):
        """تهيئة محرك التصدير."""
        self.w = int(os.getenv("VIDEO_WIDTH",  "1080"))
        self.h = int(os.getenv("VIDEO_HEIGHT", "1920"))
        self.fps = int(os.getenv("VIDEO_FPS",  "30"))

        self.temp_dir = Path(os.getenv("TEMP_DIR",   "./temp"))
        self.out_dir = Path(os.getenv("OUTPUT_DIR", "./output"))
        self.temp_dir.mkdir(parents=True, exist_ok=True)
        self.out_dir.mkdir(parents=True, exist_ok=True)

        # مسار مشروع Remotion
        self.remotion_dir = Path(
            os.getenv("REMOTION_DIR", Path(__file__).parent.parent.parent / "remotion")
        ).resolve()

        # composition ID الافتراضي
        self.composition_id = os.getenv("REMOTION_COMPOSITION", "ShortsVideo")

        # ملفات مساعدة (Thumbnails, video info)
        self.utils = VideoUtils(width=self.w, height=self.h, fps=self.fps)

        # فحص Node.js و Remotion
        self._check_node()
        self._check_remotion()

        logger.info(
            f"🎬 RemotionRenderer | {self.w}x{self.h}@{self.fps}fps"
        )
        logger.info(f"   📁 Remotion dir: {self.remotion_dir}")

    def _check_node(self) -> None:
        """التحقق من تثبيت Node.js."""
        try:
            result = subprocess.run(
                ["node", "--version"],
                capture_output=True,
                text=True,
                timeout=10,
                check=True,
            )
            version = result.stdout.strip()
            logger.info(f"✓ Node.js {version}")
        except (subprocess.CalledProcessError, FileNotFoundError):
            raise RuntimeError(
                "❌ Node.js غير مثبت!\n"
                "   حمّل من: https://nodejs.org/\n"
                "   النسخة المطلوبة: 18 أو أحدث"
            )

    def _check_remotion(self) -> None:
        """التحقق من تثبيت Remotion."""
        if not self.remotion_dir.exists():
            raise RuntimeError(
                f"❌ مجلد Remotion غير موجود: {self.remotion_dir}\n"
                f"   شغّل: cd remotion && npm install"
            )

        node_modules = self.remotion_dir / "node_modules"
        if not node_modules.exists():
            raise RuntimeError(
                f"❌ Remotion غير مُثبّت!\n"
                f"   شغّل: cd {self.remotion_dir} && npm install"
            )

        logger.info("✓ Remotion installed")

    # ════════════════════════════════════════════════════════════════
    #                    التصدير الرئيسي
    # ════════════════════════════════════════════════════════════════
    def render_final(
        self,
        props: Dict,
        output_path: str,
        quality: str = "high",
        composition_id: Optional[str] = None,
        metadata: Optional[Dict] = None,
        preset: Optional[str] = None,  # legacy support
    ) -> str:
        """
        التصدير النهائي للفيديو باستخدام Remotion.

        Args:
            props: البيانات التي ستُمرّر لـ Remotion
                   مثال: {
                       "title": "...",
                       "subtitles": [...],
                       "audioPath": "...",
                       "backgroundPath": "...",
                       ...
                   }
            output_path: مسار الفيديو الناتج
            quality: medium / high / ultra
            composition_id: اسم الـ Composition في Remotion
            metadata: بيانات وصفية (تُضاف بعد التصدير عبر FFmpeg)
            preset: legacy parameter (tiktok/reels/preview)

        Returns:
            مسار الفيديو النهائي
        """
        # دعم Legacy
        if preset and quality == "high":
            quality = self.LEGACY_PRESETS.get(preset, "high")

        # الحصول على إعدادات الجودة
        cfg = self.QUALITY_PRESETS.get(quality, self.QUALITY_PRESETS["high"])

        # تحديد الـ Composition
        comp_id = composition_id or self.composition_id

        # التأكد من وجود مجلد الإخراج
        output_path = str(Path(output_path).resolve())
        Path(output_path).parent.mkdir(parents=True, exist_ok=True)

        logger.info(f"🚀 التصدير بـ Remotion [{quality}] | Composition: {comp_id}")

        # 1) كتابة props إلى ملف JSON مؤقت
        props_file = self._write_props(props)

        try:
            # 2) تشغيل Remotion render
            self._run_remotion(
                composition_id=comp_id,
                output_path=output_path,
                props_file=props_file,
                cfg=cfg,
            )

            # 3) إضافة Metadata (إذا وُجدت) عبر FFmpeg
            if metadata:
                self._add_metadata(output_path, metadata)

            # 4) التحقق من الناتج
            if not Path(output_path).exists():
                raise RuntimeError("❌ ملف الإخراج لم يُنشأ")

            # 5) عرض المعلومات
            self._print_output_info(output_path)

            return output_path

        finally:
            # حذف ملف props المؤقت
            try:
                Path(props_file).unlink(missing_ok=True)
            except Exception:
                pass

    def _write_props(self, props: Dict) -> str:
        """كتابة props إلى ملف JSON مؤقت."""
        props_file = self.temp_dir / "remotion_props.json"
        with open(props_file, "w", encoding="utf-8") as f:
            json.dump(props, f, ensure_ascii=False, indent=2)
        logger.debug(f"📝 Props written to: {props_file}")
        return str(props_file)

    def _run_remotion(
        self,
        composition_id: str,
        output_path: str,
        props_file: str,
        cfg: dict,
    ) -> None:
        """تشغيل أمر Remotion render."""
        cmd = [
            "npx", "remotion", "render",
            "src/index.ts",
            composition_id,
            output_path,
            "--props", props_file,
            "--concurrency", cfg["concurrency"],
            "--jpeg-quality", cfg["jpeg_quality"],
            "--crf", cfg["crf"],
            "--codec", "h264",
            "--pixel-format", "yuv420p",
            "--log", "error",
        ]

        logger.info(f"   ⏳ Rendering... (timeout: {self.DEFAULT_TIMEOUT}s)")

        try:
            result = subprocess.run(
                cmd,
                cwd=str(self.remotion_dir),
                capture_output=True,
                text=True,
                timeout=self.DEFAULT_TIMEOUT,
            )

            if result.returncode != 0:
                err = (result.stderr or result.stdout)[:1000]
                raise RuntimeError(f"❌ فشل Remotion render:\n{err}")

        except subprocess.TimeoutExpired:
            raise RuntimeError(f"❌ Remotion تجاوز الوقت ({self.DEFAULT_TIMEOUT}s)")

    def _add_metadata(self, video_path: str, metadata: Dict) -> None:
        """إضافة metadata بعد التصدير عبر FFmpeg."""
        if not metadata:
            return

        temp_output = video_path.replace(".mp4", "_meta.mp4")

        cmd = [
            "ffmpeg", "-y", "-loglevel", "error",
            "-i", video_path,
            "-c", "copy",
        ]

        # إضافة metadata
        cmd.extend(self._build_metadata_args(metadata))
        cmd.append(temp_output)

        try:
            subprocess.run(cmd, check=True, capture_output=True, timeout=120)
            # استبدال الملف الأصلي
            shutil.move(temp_output, video_path)
            logger.info("✓ Metadata added")
        except Exception as e:
            logger.warning(f"⚠ فشل إضافة metadata: {e}")
            Path(temp_output).unlink(missing_ok=True)

    def _build_metadata_args(self, metadata: Dict) -> List[str]:
        """بناء معاملات Metadata لـ FFmpeg."""
        args = []
        field_map = {
            "title":       "title",
            "description": "comment",
            "comment":     "comment",
            "author":      "author",
            "artist":      "artist",
            "album":       "album",
            "year":        "date",
            "genre":       "genre",
        }

        for key, ffmpeg_key in field_map.items():
            value = metadata.get(key)
            if value:
                value = str(value).replace('"', "'")[:200]
                args.extend(["-metadata", f"{ffmpeg_key}={value}"])

        return args

    def _print_output_info(self, path: str) -> None:
        """عرض معلومات الفيديو الناتج."""
        try:
            size_mb = Path(path).stat().st_size / (1024 * 1024)
            duration = self.utils.get_duration(path)
            w, h = self.utils.get_dimensions(path)

            logger.info(f"✓ {Path(path).name}")
            logger.info(
                f"  📦 {size_mb:.1f} MB | "
                f"⏱ {duration:.1f}s | "
                f"📐 {w}x{h} | "
                f"🎞 {self.fps}fps"
            )

            self._check_platform_limits(size_mb)

        except Exception as e:
            logger.warning(f"⚠ فشل قراءة معلومات الملف: {e}")

    def _check_platform_limits(self, size_mb: float) -> None:
        """تحذير إذا تجاوز الفيديو حدود المنصات."""
        for platform, limit in self.PLATFORM_LIMITS.items():
            if size_mb > limit:
                logger.warning(
                    f"⚠ الحجم ({size_mb:.1f} MB) يتجاوز حد {platform} ({limit} MB)"
                )

    # ════════════════════════════════════════════════════════════════
    #                    Thumbnails (عبر FFmpeg)
    # ════════════════════════════════════════════════════════════════
    def create_thumbnail(
        self,
        video: str,
        output: str,
        timestamp: float = 1.5,
        resize: bool = True,
    ) -> str:
        """إنشاء thumbnail (يستخدم FFmpeg لأنه أسرع)."""
        return self.utils.create_thumbnail(video, output, timestamp, resize)

    def create_multiple_thumbnails(
        self,
        video: str,
        output_dir: str,
        count: int = 3,
    ) -> List[str]:
        """إنشاء عدة thumbnails."""
        return self.utils.create_multiple_thumbnails(video, output_dir, count)

    # ════════════════════════════════════════════════════════════════
    #                    معلومات الفيديو
    # ════════════════════════════════════════════════════════════════
    def get_duration(self, path: str) -> float:
        return self.utils.get_duration(path)

    def get_dimensions(self, path: str) -> tuple:
        return self.utils.get_dimensions(path)

    def get_video_info(self, path: str) -> dict:
        return self.utils.get_video_info(path)

    def validate_for_platform(self, video_path: str, platform: str = "youtube_shorts") -> dict:
        return self.utils.validate_for_platform(video_path, platform)

    # ════════════════════════════════════════════════════════════════
    #                    التنظيف
    # ════════════════════════════════════════════════════════════════
    def cleanup_temp(self, keep_subdirs: bool = False) -> None:
        """تنظيف الملفات المؤقتة."""
        try:
            if not self.temp_dir.exists():
                return

            count = 0
            if keep_subdirs:
                for f in self.temp_dir.rglob("*"):
                    if f.is_file():
                        f.unlink(missing_ok=True)
                        count += 1
            else:
                shutil.rmtree(self.temp_dir, ignore_errors=True)
                self.temp_dir.mkdir(parents=True, exist_ok=True)
                count = -1

            if count > 0:
                logger.info(f"🧹 تم تنظيف {count} ملف مؤقت")
            else:
                logger.info("🧹 تم تنظيف الملفات المؤقتة")

        except Exception as e:
            logger.warning(f"⚠ فشل التنظيف: {e}")

    def cleanup_specific(self, patterns: List[str]) -> int:
        """حذف ملفات محددة."""
        count = 0
        try:
            for pattern in patterns:
                for f in self.temp_dir.rglob(pattern):
                    if f.is_file():
                        f.unlink(missing_ok=True)
                        count += 1
            if count:
                logger.info(f"🧹 تم حذف {count} ملف")
        except Exception as e:
            logger.warning(f"⚠ فشل الحذف: {e}")
        return count


# ════════════════════════════════════════════════════════════════════════
#                    اختبار سريع
# ════════════════════════════════════════════════════════════════════════
if __name__ == "__main__":
    import sys

    if len(sys.argv) < 2:
        print("Usage: python remotion_renderer.py <command> [args]")
        print("Commands:")
        print("  info <video.mp4>")
        print("  thumbnail <video.mp4>")
        print("  validate <video.mp4>")
        sys.exit(1)

    renderer = RemotionRenderer()
    action = sys.argv[1]

    if action == "info" and len(sys.argv) >= 3:
        info = renderer.get_video_info(sys.argv[2])
        print(json.dumps(info, indent=2))

    elif action == "thumbnail" and len(sys.argv) >= 3:
        video = sys.argv[2]
        thumb = video.replace(".mp4", "_thumb.jpg")
        renderer.create_thumbnail(video, thumb)
        print(f"✓ {thumb}")

    elif action == "validate" and len(sys.argv) >= 3:
        result = renderer.validate_for_platform(sys.argv[2], "youtube_shorts")
        print(json.dumps(result, indent=2, ensure_ascii=False))
