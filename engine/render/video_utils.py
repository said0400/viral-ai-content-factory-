"""
🛠️ Video Utils — أدوات مساعدة للفيديو (FFmpeg/FFprobe)
═══════════════════════════════════════════════════════════════
هذا الملف يحتوي الوظائف المساعدة التي لا يقوم بها Remotion:
  ✓ إنشاء Thumbnails (أسرع بـ FFmpeg)
  ✓ قراءة معلومات الفيديو (Duration, Dimensions, Codecs)
  ✓ التحقق من توافق المنصات
  ✓ إضافة Metadata بعد التصدير

ضع في: engine/render/video_utils.py
═══════════════════════════════════════════════════════════════
"""

import json
import logging
import subprocess
from pathlib import Path
from typing import List, Tuple, Dict

logger = logging.getLogger(__name__)


class VideoUtils:
    """أدوات مساعدة للفيديو باستخدام FFmpeg/FFprobe."""

    # ─── حدود المنصات (MB) ────────────────────────────────────────
    PLATFORM_LIMITS = {
        "youtube_shorts": 256,
        "tiktok":         287,
        "instagram":      650,
        "twitter":        512,
    }

    # ════════════════════════════════════════════════════════════════
    def __init__(self, width: int = 1080, height: int = 1920, fps: int = 30):
        """
        تهيئة الأدوات المساعدة.

        Args:
            width: عرض الفيديو الافتراضي
            height: ارتفاع الفيديو الافتراضي
            fps: الإطارات في الثانية
        """
        self.w = width
        self.h = height
        self.fps = fps

        # فحص FFmpeg
        self._check_ffmpeg()

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
            logger.debug(f"✓ {version_line}")
        except (subprocess.CalledProcessError, FileNotFoundError):
            logger.warning(
                "⚠ FFmpeg غير مثبت! بعض الوظائف لن تعمل.\n"
                "   Ubuntu/Debian: sudo apt install ffmpeg\n"
                "   macOS:         brew install ffmpeg\n"
                "   Windows:       https://ffmpeg.org/download.html"
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

        Returns:
            مسار الـ thumbnail
        """
        if not Path(video).exists():
            raise FileNotFoundError(f"❌ الفيديو غير موجود: {video}")

        Path(output).parent.mkdir(parents=True, exist_ok=True)

        cmd = [
            "ffmpeg", "-y", "-loglevel", "error",
            "-ss", str(timestamp),
            "-i", video,
            "-vframes", "1",
            "-q:v", "2",
        ]

        if resize:
            cmd += [
                "-vf",
                f"scale={self.w}:{self.h}:force_original_aspect_ratio=decrease,"
                f"pad={self.w}:{self.h}:(ow-iw)/2:(oh-ih)/2",
            ]

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
        """
        إنشاء عدة thumbnails من نقاط مختلفة في الفيديو.

        Args:
            video: مسار الفيديو
            output_dir: مجلد الـ thumbnails
            count: عدد الـ thumbnails

        Returns:
            قائمة بمسارات الـ thumbnails
        """
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

    def get_dimensions(self, path: str) -> Tuple[int, int]:
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

    def get_video_info(self, path: str) -> Dict:
        """
        الحصول على معلومات شاملة عن الفيديو.

        Returns:
            dict يحتوي:
              - duration, size_mb, bitrate
              - width, height, fps
              - video_codec, audio_codec
              - audio_channels, audio_rate
        """
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

            # حساب fps بأمان (بدلاً من eval)
            fps = self._safe_fps(video_stream.get("avg_frame_rate", "0/1"))

            return {
                "duration":      float(data.get("format", {}).get("duration", 0)),
                "size_mb":       Path(path).stat().st_size / (1024 * 1024),
                "bitrate":       int(data.get("format", {}).get("bit_rate", 0)) // 1000,
                "width":         video_stream.get("width", 0),
                "height":        video_stream.get("height", 0),
                "video_codec":   video_stream.get("codec_name", "unknown"),
                "audio_codec":   audio_stream.get("codec_name", "unknown"),
                "fps":           fps,
                "audio_channels": audio_stream.get("channels", 0),
                "audio_rate":    audio_stream.get("sample_rate", 0),
            }
        except Exception as e:
            logger.error(f"❌ فشل قراءة معلومات الفيديو: {e}")
            return {}

    @staticmethod
    def _safe_fps(rate_str: str) -> float:
        """تحويل '30/1' إلى 30.0 بأمان (بدون eval)."""
        try:
            if "/" in rate_str:
                num, den = rate_str.split("/")
                den = float(den)
                if den == 0:
                    return 0.0
                return float(num) / den
            return float(rate_str)
        except Exception:
            return 0.0

    # ════════════════════════════════════════════════════════════════
    #                    التحقق من المنصات
    # ════════════════════════════════════════════════════════════════
    def validate_for_platform(
        self,
        video_path: str,
        platform: str = "youtube_shorts",
    ) -> Dict:
        """
        التحقق من توافق الفيديو مع المنصة.

        Args:
            video_path: مسار الفيديو
            platform: youtube_shorts / tiktok / instagram / twitter

        Returns:
            dict: {
                "valid": bool,
                "errors": [...],
                "warnings": [...],
                "info": {...}
            }
        """
        info = self.get_video_info(video_path)
        if not info:
            return {
                "valid": False,
                "errors": ["فشل قراءة معلومات الفيديو"],
                "warnings": [],
                "info": {},
            }

        errors = []
        warnings = []

        # Platform limits
        limit = self.PLATFORM_LIMITS.get(platform, 256)
        if info["size_mb"] > limit:
            errors.append(
                f"الحجم ({info['size_mb']:.1f} MB) يتجاوز حد {platform} ({limit} MB)"
            )

        # YouTube Shorts specific
        if platform == "youtube_shorts":
            if info["duration"] > 60:
                errors.append(f"المدة ({info['duration']:.1f}s) تتجاوز 60 ثانية")
            if info["width"] != 1080 or info["height"] != 1920:
                warnings.append(
                    f"الأبعاد ({info['width']}x{info['height']}) مفضلة 1080x1920"
                )

        # TikTok specific
        elif platform == "tiktok":
            if info["duration"] > 180:
                errors.append(f"المدة ({info['duration']:.1f}s) تتجاوز 3 دقائق")

        # Codec checks
        if info["video_codec"] != "h264":
            warnings.append(
                f"Video codec '{info['video_codec']}' - الموصى به h264"
            )
        if info["audio_codec"] not in ("aac", "mp3"):
            warnings.append(
                f"Audio codec '{info['audio_codec']}' - الموصى به aac"
            )

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
        print("Usage: python video_utils.py <video.mp4> [info|thumbnail|validate]")
        sys.exit(1)

    utils = VideoUtils()
    video = sys.argv[1]
    action = sys.argv[2] if len(sys.argv) > 2 else "info"

    if action == "info":
        info = utils.get_video_info(video)
        print(json.dumps(info, indent=2, ensure_ascii=False))

    elif action == "thumbnail":
        thumb = video.replace(".mp4", "_thumb.jpg")
        utils.create_thumbnail(video, thumb)
        print(f"✓ {thumb}")

    elif action == "validate":
        result = utils.validate_for_platform(video, "youtube_shorts")
        print(json.dumps(result, indent=2, ensure_ascii=False))
