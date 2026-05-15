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
  ✓ 🆕 Verbose logging للتشخيص
  ✓ 🆕 التحقق من الملفات قبل البدء

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

    # ─── Presets الجودة ───────────────────────────────────────────
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
            "concurrency":  "2",  # 🆕 خفّضت من 4 لأن GitHub Actions ضعيف
            "audio_bitrate": "192k",
        },
        "ultra": {
            "crf":          "17",
            "jpeg_quality": "95",
            "concurrency":  "4",  # 🆕 خفّضت من 8
            "audio_bitrate": "256k",
        },
    }

    # ─── Legacy presets ──────────────────────────────────────────
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

    # 🆕 timeout أقصر (10 دقائق)
    DEFAULT_TIMEOUT = 600

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

        # ملفات مساعدة
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
        preset: Optional[str] = None,
    ) -> str:
        """التصدير النهائي للفيديو باستخدام Remotion."""
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

        # 🆕 1) فحص Props قبل البدء
        self._validate_props(props)

        # 2) كتابة props إلى ملف JSON مؤقت
        props_file = self._write_props(props)

        try:
            # 3) تشغيل Remotion render
            self._run_remotion(
                composition_id=comp_id,
                output_path=output_path,
                props_file=props_file,
                cfg=cfg,
            )

            # 4) إضافة Metadata
            if metadata:
                self._add_metadata(output_path, metadata)

            # 5) التحقق من الناتج
            if not Path(output_path).exists():
                raise RuntimeError("❌ ملف الإخراج لم يُنشأ")

            # 6) عرض المعلومات
            self._print_output_info(output_path)

            return output_path

        finally:
            # 🆕 لا نحذف props_file حتى نقدر نُشخّص الأخطاء
            logger.info(f"📝 Props file kept for debugging: {props_file}")

    # 🆕 فحص Props قبل البدء
    def _validate_props(self, props: Dict) -> None:
        """التحقق من صحة الـ props قبل إرسالها لـ Remotion."""
        logger.info("🔍 Validating props...")

        # 1) فحص الحقول الأساسية
        required_fields = ["scenes", "totalDuration", "fps", "width", "height"]
        for field in required_fields:
            if field not in props:
                raise ValueError(f"❌ Missing required field: {field}")

        # 2) فحص المشاهد
        scenes = props.get("scenes", [])
        if not scenes:
            raise ValueError("❌ No scenes provided!")

        logger.info(f"   ✓ {len(scenes)} scenes")

        # 3) فحص ملفات الفيديو لكل مشهد
        missing_videos = []
        for i, scene in enumerate(scenes):
            bg_path = scene.get("backgroundPath", "")
            if bg_path:
                if not Path(bg_path).exists():
                    missing_videos.append((i, bg_path))
                    logger.warning(f"   ⚠ Scene {i} video not found: {bg_path}")
                else:
                    size_kb = Path(bg_path).stat().st_size / 1024
                    logger.info(f"   ✓ Scene {i} video: {size_kb:.1f} KB")
            else:
                logger.warning(f"   ⚠ Scene {i} has no background video!")

        if missing_videos and len(missing_videos) == len(scenes):
            raise RuntimeError(
                f"❌ All {len(scenes)} background videos are missing!\n"
                f"   تأكد من PEXELS_API_KEY و PIXABAY_API_KEY"
            )

        # 4) فحص ملف الصوت
        audio_path = props.get("audioPath", "")
        if audio_path:
            if not Path(audio_path).exists():
                raise FileNotFoundError(
                    f"❌ Audio file not found: {audio_path}"
                )
            audio_size_kb = Path(audio_path).stat().st_size / 1024
            logger.info(f"   ✓ Audio: {audio_size_kb:.1f} KB ({audio_path})")
        else:
            logger.warning("   ⚠ No audio path provided")

        # 5) فحص الترجمات
        subtitles = props.get("subtitles", [])
        logger.info(f"   ✓ {len(subtitles)} subtitles")

        # 6) فحص المدة
        duration = props.get("totalDuration", 0)
        if duration <= 0:
            raise ValueError(f"❌ Invalid duration: {duration}")

        logger.info(f"   ✓ Duration: {duration}s")
        logger.info(f"   ✓ Dimensions: {props.get('width')}x{props.get('height')}")
        logger.info(f"   ✓ FPS: {props.get('fps')}")
        logger.info("✅ Props validation passed!")

    def _write_props(self, props: Dict) -> str:
        """كتابة props إلى ملف JSON مؤقت."""
        props_file = self.temp_dir / "remotion_props.json"

        with open(props_file, "w", encoding="utf-8") as f:
            json.dump(props, f, ensure_ascii=False, indent=2)

        # 🆕 معلومات تشخيصية
        file_size_kb = props_file.stat().st_size / 1024
        logger.info(f"📝 Props written: {props_file} ({file_size_kb:.1f} KB)")

        return str(props_file)

    def _run_remotion(
        self,
        composition_id: str,
        output_path: str,
        props_file: str,
        cfg: dict,
    ) -> None:
        """تشغيل أمر Remotion render مع verbose logging."""
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
            # 🆕 verbose logging
            "--log", "verbose",
            # 🆕 تعطيل المعاينة في headless
            "--browser-executable", "",
            # 🆕 timeout للـ delayRender (مهم جداً!)
            "--timeout", "30000",
        ]

        logger.info("=" * 60)
        logger.info(f"🎬 Running Remotion render...")
        logger.info(f"   ⏱ Timeout: {self.DEFAULT_TIMEOUT}s")
        logger.info(f"   📋 Composition: {composition_id}")
        logger.info(f"   📁 Working dir: {self.remotion_dir}")
        logger.info(f"   📄 Props file: {props_file}")
        logger.info(f"   📤 Output: {output_path}")
        logger.info(f"   ⚙️ Concurrency: {cfg['concurrency']}")
        logger.info(f"   ⚙️ CRF: {cfg['crf']}")
        logger.info("=" * 60)

        try:
            # 🆕 طباعة الـ stdout/stderr مباشرة (live)
            result = subprocess.run(
                cmd,
                cwd=str(self.remotion_dir),
                timeout=self.DEFAULT_TIMEOUT,
                # ❌ لا نستخدم capture_output لنرى الـ output مباشرة
            )

            if result.returncode != 0:
                raise RuntimeError(
                    f"❌ Remotion failed (exit code: {result.returncode})\n"
                    f"   تفقّد الـ logs أعلاه لتعرف السبب"
                )

            logger.info("✅ Remotion render completed!")

        except subprocess.TimeoutExpired:
            raise RuntimeError(
                f"❌ Remotion timeout ({self.DEFAULT_TIMEOUT}s)!\n"
                f"   الأسباب المحتملة:\n"
                f"     1. ملفات الفيديو/الصوت تالفة أو غير موجودة\n"
                f"     2. الـ Composition يحتوي infinite loop\n"
                f"     3. delayRender() لم يستدعي continueRender()\n"
                f"     4. حجم الـ rendering كبير جداً"
            )

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

        cmd.extend(self._build_metadata_args(metadata))
        cmd.append(temp_output)

        try:
            subprocess.run(cmd, check=True, capture_output=True, timeout=120)
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
    #                    Thumbnails
    # ════════════════════════════════════════════════════════════════
    def create_thumbnail(
        self,
        video: str,
        output: str,
        timestamp: float = 1.5,
        resize: bool = True,
    ) -> str:
        return self.utils.create_thumbnail(video, output, timestamp, resize)

    def create_multiple_thumbnails(
        self,
        video: str,
        output_dir: str,
        count: int = 3,
    ) -> List[str]:
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
