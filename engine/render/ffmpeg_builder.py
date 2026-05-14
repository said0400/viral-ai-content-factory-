"""
🎞️ FFmpeg Builder — التصدير النهائي للفيديو
═══════════════════════════════════════════════════════════════
محرك التصدير النهائي يوفر:
  ✓ MP4 متوافق مع YouTube/TikTok/Instagram (H.264 + AAC)
  ✓ 3 مستويات جودة (medium/high/ultra)
  ✓ Metadata كاملة (عربية + إنجليزية)
  ✓ Thumbnails متعددة (1080x1920)
  ✓ تحقق من حجم الملف
  ✓ تنظيف ذكي للملفات المؤقتة

ضع في: engine/render/ffmpeg_builder.py
═══════════════════════════════════════════════════════════════
"""

import os
import json
import shutil
import logging
import subprocess
from pathlib import Path
from typing import Optional, Dict, List

logger = logging.getLogger(__name__)


class FFmpegBuilder:
    """محرك التصدير النهائي إلى MP4."""

    # ─── Presets الجودة (متطابق مع main.py) ──────────────────────
    QUALITY_PRESETS = {
        "medium": {
            "crf":          "23",
            "preset":       "fast",
            "audio_bitrate": "128k",
            "audio_rate":    "44100",
            "video_bitrate": None,  # CRF mode
        },
        "high": {
            "crf":          "19",
            "preset":       "medium",
            "audio_bitrate": "192k",
            "audio_rate":    "44100",
            "video_bitrate": None,
        },
        "ultra": {
            "crf":          "17",
            "preset":       "slow",
            "audio_bitrate": "256k",
            "audio_rate":    "48000",
            "video_bitrate": None,
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

    DEFAULT_TIMEOUT = 600  # 10 دقائق

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

        # فحص FFmpeg
        self._check_ffmpeg()

        logger.info(
            f"🎞️ FFmpegBuilder | {self.w}x{self.h}@{self.fps}fps"
        )

    def _check_ffmpeg(self) -> None:
        """التحقق من تثبيت FFmpeg."""
        try:
            result = subprocess.run(
                ["ffmpeg", "-version"],
                capture_output=True,
                text=True,
                timeout=10,
                check=True,
            )
            version_line = result.stdout.splitlines()[0]
            logger.info(f"✓ {version_line}")
        except (subprocess.CalledProcessError, FileNotFoundError):
            raise RuntimeError(
                "❌ FFmpeg غير مثبت!\n"
                "   Ubuntu/Debian: sudo apt install ffmpeg\n"
                "   macOS:         brew install ffmpeg\n"
                "   Windows:       https://ffmpeg.org/download.html"
            )

    # ════════════════════════════════════════════════════════════════
    #                    التصدير الرئيسي
    # ════════════════════════════════════════════════════════════════
    def render_final(
        self,
        input_video: str,
        output_path: str,
        quality: str = "high",
        metadata: Optional[Dict] = None,
        preset: Optional[str] = None,  # legacy support
    ) -> str:
        """
        التصدير النهائي للفيديو.

        Args:
            input_video: مسار الفيديو المُدخل
            output_path: مسار الفيديو الناتج
            quality: medium / high / ultra
            metadata: بيانات وصفية (title, description, etc.)
            preset: legacy parameter (tiktok/reels/preview)

        Returns:
            مسار الفيديو النهائي
        """
        # دعم Legacy
        if preset and quality == "high":
            quality = self.LEGACY_PRESETS.get(preset, "high")

        # الحصول على إعدادات الجودة
        cfg = self.QUALITY_PRESETS.get(quality, self.QUALITY_PRESETS["high"])
        metadata = metadata or {}

        # التحقق من المدخلات
        if not Path(input_video).exists():
            raise FileNotFoundError(f"❌ الفيديو المُدخل غير موجود: {input_video}")

        # التأكد من وجود مجلد الإخراج
        Path(output_path).parent.mkdir(parents=True, exist_ok=True)

        logger.info(f"🚀 التصدير النهائي [{quality}]...")

        # بناء الأمر
        cmd = self._build_render_command(input_video, output_path, cfg, metadata)

        # التنفيذ
        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                timeout=self.DEFAULT_TIMEOUT,
            )

            if result.returncode != 0:
                err = result.stderr.decode("utf-8", errors="ignore")[:500]
                raise RuntimeError(f"❌ فشل التصدير: {err}")

        except subprocess.TimeoutExpired:
            raise RuntimeError(f"❌ التصدير تجاوز الوقت ({self.DEFAULT_TIMEOUT}s)")

        # التحقق من الناتج
        if not Path(output_path).exists():
            raise RuntimeError("❌ ملف الإخراج لم يُنشأ")

        # عرض المعلومات
        self._print_output_info(output_path)

        return output_path

    def _build_render_command(
        self,
        input_video: str,
        output_path: str,
        cfg: dict,
        metadata: Dict,
    ) -> List[str]:
        """بناء أمر FFmpeg للتصدير."""
        cmd = [
            "ffmpeg", "-y", "-loglevel", "error",
            "-i", input_video,

            # Video codec
            "-c:v", "libx264",
            "-crf", cfg["crf"],
            "-preset", cfg["preset"],
            "-profile:v", "high",
            "-level:v", "4.1",
            "-pix_fmt", "yuv420p",
            "-r", str(self.fps),

            # Audio codec
            "-c:a", "aac",
            "-b:a", cfg["audio_bitrate"],
            "-ar", cfg["audio_rate"],
            "-ac", "2",

            # Streaming optimization
            "-movflags", "+faststart",
        ]

        # إضافة Metadata
        if metadata:
            cmd.extend(self._build_metadata_args(metadata))

        cmd.append(output_path)
        return cmd

    def _build_metadata_args(self, metadata: Dict) -> List[str]:
        """بناء معاملات Metadata."""
        args = []

        # الحقول المدعومة
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
                # تنظيف القيمة
                value = str(value).replace('"', "'")[:200]
                args.extend(["-metadata", f"{ffmpeg_key}={value}"])

        return args

    def _print_output_info(self, path: str) -> None:
        """عرض معلومات الفيديو الناتج."""
        try:
            size_mb = Path(path).stat().st_size / (1024 * 1024)
            duration = self.get_duration(path)
            w, h = self.get_dimensions(path)

            logger.info(f"✓ {Path(path).name}")
            logger.info(
                f"  📦 {size_mb:.1f} MB | "
                f"⏱ {duration:.1f}s | "
                f"📐 {w}x{h} | "
                f"🎞 {self.fps}fps"
            )

            # تحذير إذا تجاوز حدود المنصات
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
        """
        إنشاء thumbnail من الفيديو.

        Args:
            video: مسار الفيديو
            output: مسار الـ thumbnail
            timestamp: الوقت بالثواني لأخذ اللقطة
            resize: تحجيم للأبعاد المطلوبة
        """
        if not Path(video).exists():
            raise FileNotFoundError(f"❌ الفيديو غير موجود: {video}")

        cmd = [
            "ffmpeg", "-y", "-loglevel", "error",
            "-ss", str(timestamp),
            "-i", video,
            "-vframes", "1",
            "-q:v", "2",
        ]

        if resize:
            cmd += ["-vf", f"scale={self.w}:{self.h}:force_original_aspect_ratio=decrease,"
                          f"pad={self.w}:{self.h}:(ow-iw)/2:(oh-ih)/2"]

        cmd.append(output)

        try:
            subprocess.run(
                cmd,
                check=True,
                capture_output=True,
                timeout=60,
            )
            logger.info(f"✓ Thumbnail: {Path(output).name}")
            return output
        except subprocess.CalledProcessError as e:
            err = e.stderr.decode("utf-8", errors="ignore")[:200]
            raise RuntimeError(f"❌ فشل إنشاء thumbnail: {err}")

    def create_multiple_thumbnails(
        self,
        video: str,
        output_dir: str,
        count: int = 3,
    ) -> List[str]:
        """إنشاء عدة thumbnails من نقاط مختلفة في الفيديو."""
        try:
            duration = self.get_duration(video)
        except Exception:
            duration = 30.0

        # نقاط متفرقة (تجنب البداية والنهاية)
        timestamps = [
            duration * (i + 1) / (count + 1)
            for i in range(count)
        ]

        Path(output_dir).mkdir(parents=True, exist_ok=True)
        thumbnails = []

        video_name = Path(video).stem
        for i, ts in enumerate(timestamps):
            output = str(Path(output_dir) / f"{video_name}_thumb_{i+1}.jpg")
            try:
                self.create_thumbnail(video, output, ts, resize=True)
                thumbnails.append(output)
            except Exception as e:
                logger.warning(f"⚠ فشل thumbnail {i+1}: {e}")

        return thumbnails

    # ════════════════════════════════════════════════════════════════
    #                    معلومات الفيديو
    # ════════════════════════════════════════════════════════════════
    def get_duration(self, path: str) -> float:
        """الحصول على مدة الفيديو بالثواني."""
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
            return 0.0

    def get_dimensions(self, path: str) -> tuple:
        """الحصول على أبعاد الفيديو."""
        try:
            result = subprocess.run(
                [
                    "ffprobe", "-v", "quiet",
                    "-print_format", "json",
                    "-show_streams",
                    path,
                ],
                capture_output=True,
                text=True,
                timeout=30,
                check=True,
            )
            data = json.loads(result.stdout)
            for stream in data.get("streams", []):
                if stream.get("codec_type") == "video":
                    return int(stream["width"]), int(stream["height"])
        except Exception as e:
            logger.warning(f"⚠ فشل قراءة الأبعاد: {e}")
        return self.w, self.h

    def get_video_info(self, path: str) -> dict:
        """الحصول على معلومات شاملة عن الفيديو."""
        try:
            result = subprocess.run(
                [
                    "ffprobe", "-v", "quiet",
                    "-print_format", "json",
                    "-show_format",
                    "-show_streams",
                    path,
                ],
                capture_output=True,
                text=True,
                timeout=30,
                check=True,
            )
            data = json.loads(result.stdout)

            video_stream = next(
                (s for s in data.get("streams", []) if s["codec_type"] == "video"),
                {},
            )
            audio_stream = next(
                (s for s in data.get("streams", []) if s["codec_type"] == "audio"),
                {},
            )

            return {
                "duration":      float(data.get("format", {}).get("duration", 0)),
                "size_mb":       Path(path).stat().st_size / (1024 * 1024),
                "bitrate":       int(data.get("format", {}).get("bit_rate", 0)) // 1000,
                "width":         video_stream.get("width", 0),
                "height":        video_stream.get("height", 0),
                "video_codec":   video_stream.get("codec_name", "unknown"),
                "audio_codec":   audio_stream.get("codec_name", "unknown"),
                "fps":           eval(video_stream.get("avg_frame_rate", "0/1")),
                "audio_channels": audio_stream.get("channels", 0),
                "audio_rate":    audio_stream.get("sample_rate", 0),
            }
        except Exception as e:
            logger.error(f"❌ فشل قراءة معلومات الفيديو: {e}")
            return {}

    # ════════════════════════════════════════════════════════════════
    #                    التنظيف
    # ════════════════════════════════════════════════════════════════
    def cleanup_temp(self, keep_subdirs: bool = False) -> None:
        """
        تنظيف الملفات المؤقتة.

        Args:
            keep_subdirs: الإبقاء على المجلدات الفرعية
        """
        try:
            if not self.temp_dir.exists():
                return

            count = 0
            if keep_subdirs:
                # احذف الملفات فقط (ليس المجلدات)
                for f in self.temp_dir.rglob("*"):
                    if f.is_file():
                        f.unlink(missing_ok=True)
                        count += 1
            else:
                # احذف كل شيء
                shutil.rmtree(self.temp_dir, ignore_errors=True)
                self.temp_dir.mkdir(parents=True, exist_ok=True)
                count = -1  # غير معروف

            if count > 0:
                logger.info(f"🧹 تم تنظيف {count} ملف مؤقت")
            else:
                logger.info("🧹 تم تنظيف الملفات المؤقتة")

        except Exception as e:
            logger.warning(f"⚠ فشل التنظيف: {e}")

    def cleanup_specific(self, patterns: List[str]) -> int:
        """حذف ملفات محددة بناءً على patterns."""
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

    # ════════════════════════════════════════════════════════════════
    #                    دوال مساعدة
    # ════════════════════════════════════════════════════════════════
    def validate_for_platform(self, video_path: str, platform: str = "youtube_shorts") -> dict:
        """التحقق من توافق الفيديو مع المنصة."""
        info = self.get_video_info(video_path)
        if not info:
            return {"valid": False, "errors": ["فشل قراءة معلومات الفيديو"]}

        errors = []
        warnings = []

        # Platform limits
        limit = self.PLATFORM_LIMITS.get(platform, 256)
        if info["size_mb"] > limit:
            errors.append(f"الحجم ({info['size_mb']:.1f} MB) يتجاوز حد {platform} ({limit} MB)")

        # YouTube Shorts specific
        if platform == "youtube_shorts":
            if info["duration"] > 60:
                errors.append(f"المدة ({info['duration']:.1f}s) تتجاوز 60 ثانية")
            if info["width"] != 1080 or info["height"] != 1920:
                warnings.append(f"الأبعاد ({info['width']}x{info['height']}) مفضلة 1080x1920")

        # Codec checks
        if info["video_codec"] != "h264":
            warnings.append(f"Video codec '{info['video_codec']}' - الموصى به h264")
        if info["audio_codec"] not in ("aac", "mp3"):
            warnings.append(f"Audio codec '{info['audio_codec']}' - الموصى به aac")

        return {
            "valid": len(errors) == 0,
            "errors": errors,
            "warnings": warnings,
            "info": info,
        }


# ════════════════════════════════════════════════════════════════════════
#                    اختبار سريع
# ════════════════════════════════════════════════════════════════════════
if __name__ == "__main__":
    import sys

    if len(sys.argv) < 2:
        print("Usage: python ffmpeg_builder.py <video.mp4> [info|thumbnail|validate]")
        sys.exit(1)

    builder = FFmpegBuilder()
    video = sys.argv[1]
    action = sys.argv[2] if len(sys.argv) > 2 else "info"

    if action == "info":
        info = builder.get_video_info(video)
        print(json.dumps(info, indent=2))

    elif action == "thumbnail":
        thumb = video.replace(".mp4", "_thumb.jpg")
        builder.create_thumbnail(video, thumb)
        print(f"✓ {thumb}")

    elif action == "validate":
        result = builder.validate_for_platform(video, "youtube_shorts")
        print(json.dumps(result, indent=2, ensure_ascii=False))
