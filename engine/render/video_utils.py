"""
🛠️ Video Utils v2.0 — Pro
═══════════════════════════════════════════════════════════════
أدوات مساعدة للفيديو:
  ✓ Thumbnails (single, multiple, grid)
  ✓ Video info (مع dataclass)
  ✓ Platform validation
  ✓ Audio extraction
  ✓ يستخدم ffmpeg_utils

التحسينات v2.0:
  ✓ VideoInfo dataclass
  ✓ ValidationResult dataclass
  ✓ يستخدم ffmpeg_utils (لا تكرار)
  ✓ Caching للـ metadata
  ✓ Thumbnail grid
  ✓ Audio extraction
═══════════════════════════════════════════════════════════════
"""

from __future__ import annotations

import json
import shutil
import logging
import subprocess
from pathlib import Path
from enum import Enum
from dataclasses import dataclass, field, asdict
from functools import lru_cache
from typing import Optional, Any

from engine.video.voice.ffmpeg_utils import (
    check_ffmpeg_available, check_ffprobe_available,
    run_ffmpeg, get_audio_duration,
)

logger = logging.getLogger(__name__)


# ═══════════════════════════════════════════════════════════════════
# Enums
# ═══════════════════════════════════════════════════════════════════
class Platform(str, Enum):
    """منصات النشر."""
    YOUTUBE_SHORTS = "youtube_shorts"
    YOUTUBE = "youtube"
    TIKTOK = "tiktok"
    INSTAGRAM_REEL = "instagram_reel"
    INSTAGRAM_STORY = "instagram_story"
    TWITTER = "twitter"
    FACEBOOK = "facebook"
    LINKEDIN = "linkedin"


class CodecType(str, Enum):
    """أنواع الـ codecs."""
    H264 = "h264"
    H265 = "h265"
    VP9 = "vp9"
    AV1 = "av1"


# ═══════════════════════════════════════════════════════════════════
# Dataclasses
# ═══════════════════════════════════════════════════════════════════
@dataclass
class VideoInfo:
    """معلومات الفيديو الشاملة."""
    path: str
    duration: float = 0.0
    size_mb: float = 0.0
    bitrate_kbps: int = 0
    
    # Video stream
    width: int = 0
    height: int = 0
    fps: float = 0.0
    video_codec: str = "unknown"
    
    # Audio stream
    audio_codec: str = "unknown"
    audio_channels: int = 0
    audio_rate: int = 0
    has_audio: bool = False
    
    # Computed
    @property
    def aspect_ratio(self) -> str:
        """نسبة الأبعاد كنص."""
        if self.width == 0 or self.height == 0:
            return "unknown"
        
        # حساب GCD
        from math import gcd
        g = gcd(self.width, self.height)
        return f"{self.width // g}:{self.height // g}"
    
    @property
    def is_portrait(self) -> bool:
        """هل portrait (9:16, 4:5, etc.)?"""
        return self.height > self.width
    
    @property
    def is_landscape(self) -> bool:
        """هل landscape (16:9, 4:3, etc.)?"""
        return self.width > self.height
    
    @property
    def is_square(self) -> bool:
        """هل مربع؟"""
        return self.width == self.height
    
    @property
    def resolution_label(self) -> str:
        """تسمية الـ resolution."""
        if self.height >= 2160:
            return "4K"
        elif self.height >= 1440:
            return "2K"
        elif self.height >= 1080:
            return "Full HD"
        elif self.height >= 720:
            return "HD"
        elif self.height >= 480:
            return "SD"
        return "Low"
    
    def to_dict(self) -> dict:
        return {
            **asdict(self),
            "aspect_ratio": self.aspect_ratio,
            "is_portrait": self.is_portrait,
            "is_landscape": self.is_landscape,
            "resolution_label": self.resolution_label,
        }


@dataclass
class ValidationResult:
    """نتيجة validation."""
    valid: bool
    platform: str
    info: Optional[VideoInfo] = None
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    
    @property
    def has_issues(self) -> bool:
        return len(self.errors) > 0 or len(self.warnings) > 0
    
    def to_dict(self) -> dict:
        return {
            "valid": self.valid,
            "platform": self.platform,
            "info": self.info.to_dict() if self.info else None,
            "errors": self.errors,
            "warnings": self.warnings,
            "has_issues": self.has_issues,
        }
    
    def summary(self) -> str:
        status = "✅ Valid" if self.valid else "❌ Invalid"
        lines = [f"📊 Validation: {status} for {self.platform}"]
        
        if self.errors:
            lines.append(f"   Errors ({len(self.errors)}):")
            for e in self.errors:
                lines.append(f"      ❌ {e}")
        
        if self.warnings:
            lines.append(f"   Warnings ({len(self.warnings)}):")
            for w in self.warnings:
                lines.append(f"      ⚠ {w}")
        
        return "\n".join(lines)


@dataclass
class ThumbnailResult:
    """نتيجة إنشاء thumbnail."""
    success: bool
    path: str = ""
    timestamp: float = 0.0
    width: int = 0
    height: int = 0
    file_size: int = 0
    error: Optional[str] = None


# ═══════════════════════════════════════════════════════════════════
# Platform Specifications
# ═══════════════════════════════════════════════════════════════════
@dataclass(frozen=True)
class PlatformSpec:
    """مواصفات منصة."""
    name: str
    max_size_mb: int
    max_duration: float
    min_duration: float = 0
    preferred_aspect: str = "9:16"
    allowed_aspects: tuple[str, ...] = ("9:16",)
    preferred_resolution: tuple[int, int] = (1080, 1920)
    preferred_codec: str = "h264"
    preferred_audio_codec: str = "aac"
    max_bitrate_kbps: int = 8000


PLATFORM_SPECS: dict[str, PlatformSpec] = {
    "youtube_shorts": PlatformSpec(
        name="YouTube Shorts",
        max_size_mb=256, max_duration=60, min_duration=1,
        preferred_aspect="9:16",
        allowed_aspects=("9:16",),
        preferred_resolution=(1080, 1920),
    ),
    "youtube": PlatformSpec(
        name="YouTube",
        max_size_mb=128000, max_duration=43200,  # 12 hours
        preferred_aspect="16:9",
        allowed_aspects=("16:9", "9:16", "4:3", "1:1"),
        preferred_resolution=(1920, 1080),
    ),
    "tiktok": PlatformSpec(
        name="TikTok",
        max_size_mb=287, max_duration=600, min_duration=3,
        preferred_aspect="9:16",
        allowed_aspects=("9:16", "1:1"),
        preferred_resolution=(1080, 1920),
    ),
    "instagram_reel": PlatformSpec(
        name="Instagram Reel",
        max_size_mb=650, max_duration=90, min_duration=3,
        preferred_aspect="9:16",
        allowed_aspects=("9:16",),
        preferred_resolution=(1080, 1920),
    ),
    "instagram_story": PlatformSpec(
        name="Instagram Story",
        max_size_mb=650, max_duration=60,
        preferred_aspect="9:16",
        allowed_aspects=("9:16",),
        preferred_resolution=(1080, 1920),
    ),
    "twitter": PlatformSpec(
        name="Twitter/X",
        max_size_mb=512, max_duration=140,
        preferred_aspect="16:9",
        allowed_aspects=("16:9", "1:1", "9:16"),
        preferred_resolution=(1280, 720),
    ),
    "facebook": PlatformSpec(
        name="Facebook",
        max_size_mb=4000, max_duration=240,
        preferred_aspect="16:9",
        allowed_aspects=("16:9", "9:16", "1:1"),
        preferred_resolution=(1280, 720),
    ),
    "linkedin": PlatformSpec(
        name="LinkedIn",
        max_size_mb=5000, max_duration=600,
        preferred_aspect="16:9",
        allowed_aspects=("16:9", "1:1"),
        preferred_resolution=(1920, 1080),
    ),
}


# ═══════════════════════════════════════════════════════════════════
# Helpers
# ═══════════════════════════════════════════════════════════════════
def safe_fps(rate_str: str) -> float:
    """تحويل '30/1' إلى 30.0 بأمان."""
    try:
        if "/" in rate_str:
            num, den = rate_str.split("/")
            den_val = float(den)
            if den_val == 0:
                return 0.0
            return float(num) / den_val
        return float(rate_str)
    except (ValueError, AttributeError):
        return 0.0


def get_file_signature(path: str) -> str:
    """signature للملف (لـ caching)."""
    import hashlib
    try:
        p = Path(path)
        content = f"{p.name}|{p.stat().st_size}|{p.stat().st_mtime}"
        return hashlib.md5(content.encode()).hexdigest()[:16]
    except Exception:
        return ""


# Cache للـ video info
_video_info_cache: dict[str, VideoInfo] = {}


# ═══════════════════════════════════════════════════════════════════
# Main Class
# ═══════════════════════════════════════════════════════════════════
class VideoUtils:
    """أدوات الفيديو v2.0."""
    
    def __init__(
        self,
        width: int = 1080,
        height: int = 1920,
        fps: int = 30,
        cache_enabled: bool = True,
    ):
        """
        Args:
            width, height: الأبعاد الافتراضية
            fps: الـ FPS
            cache_enabled: تفعيل caching للـ metadata
        """
        self.w = width
        self.h = height
        self.fps = fps
        self.cache_enabled = cache_enabled
        
        # FFmpeg check
        if not check_ffmpeg_available():
            logger.warning(
                "⚠ FFmpeg غير مثبت!\n"
                "   Ubuntu: sudo apt install ffmpeg\n"
                "   macOS:  brew install ffmpeg\n"
                "   Windows: https://ffmpeg.org/"
            )
        
        if not check_ffprobe_available():
            logger.warning("⚠ FFprobe غير مثبت!")
    
    # ═══════════════════════════════════════════════════════════════
    # Video Info (مع caching)
    # ═══════════════════════════════════════════════════════════════
    def get_video_info(
        self,
        path: str,
        use_cache: bool = True,
    ) -> Optional[VideoInfo]:
        """
        🎯 جلب معلومات الفيديو الشاملة.
        
        Args:
            path: مسار الفيديو
            use_cache: استخدام الكاش
        """
        if not Path(path).exists():
            logger.error(f"❌ File not found: {path}")
            return None
        
        # تحقق من الكاش
        if self.cache_enabled and use_cache:
            sig = get_file_signature(path)
            if sig in _video_info_cache:
                return _video_info_cache[sig]
        
        # FFprobe
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
            
            # Streams
            video_stream = next(
                (s for s in data.get("streams", []) if s["codec_type"] == "video"),
                {},
            )
            audio_stream = next(
                (s for s in data.get("streams", []) if s["codec_type"] == "audio"),
                {},
            )
            
            # FPS
            fps = safe_fps(video_stream.get("avg_frame_rate", "0/1"))
            
            # Build VideoInfo
            info = VideoInfo(
                path=path,
                duration=float(data.get("format", {}).get("duration", 0)),
                size_mb=Path(path).stat().st_size / (1024 * 1024),
                bitrate_kbps=int(data.get("format", {}).get("bit_rate", 0)) // 1000,
                width=int(video_stream.get("width", 0)),
                height=int(video_stream.get("height", 0)),
                fps=round(fps, 2),
                video_codec=video_stream.get("codec_name", "unknown"),
                audio_codec=audio_stream.get("codec_name", "unknown") if audio_stream else "none",
                audio_channels=int(audio_stream.get("channels", 0)) if audio_stream else 0,
                audio_rate=int(audio_stream.get("sample_rate", 0)) if audio_stream else 0,
                has_audio=bool(audio_stream),
            )
            
            # حفظ في الكاش
            if self.cache_enabled:
                sig = get_file_signature(path)
                _video_info_cache[sig] = info
            
            return info
            
        except Exception as e:
            logger.error(f"❌ Failed to get info: {e}")
            return None
    
    def get_duration(self, path: str) -> float:
        """مدة الفيديو."""
        info = self.get_video_info(path)
        return info.duration if info else 0.0
    
    def get_dimensions(self, path: str) -> tuple[int, int]:
        """أبعاد الفيديو."""
        info = self.get_video_info(path)
        if info and info.width > 0:
            return (info.width, info.height)
        return (self.w, self.h)
    
    # ═══════════════════════════════════════════════════════════════
    # Thumbnails
    # ═══════════════════════════════════════════════════════════════
    def create_thumbnail(
        self,
        video: str,
        output: str,
        timestamp: float = 1.5,
        resize: bool = True,
        quality: int = 2,
    ) -> ThumbnailResult:
        """
        🎯 إنشاء thumbnail.
        
        Args:
            video: مسار الفيديو
            output: مسار الـ thumbnail
            timestamp: الوقت (بالثواني)
            resize: تحجيم للأبعاد
            quality: 2-31 (2 = أعلى جودة)
        """
        if not Path(video).exists():
            return ThumbnailResult(
                success=False,
                error=f"Video not found: {video}",
            )
        
        Path(output).parent.mkdir(parents=True, exist_ok=True)
        
        # بناء الأمر
        args = [
            "-ss", str(timestamp),
            "-i", video,
            "-vframes", "1",
            "-q:v", str(quality),
        ]
        
        if resize:
            args.extend([
                "-vf",
                f"scale={self.w}:{self.h}:force_original_aspect_ratio=decrease,"
                f"pad={self.w}:{self.h}:(ow-iw)/2:(oh-ih)/2",
            ])
        
        result = run_ffmpeg(
            args=args,
            output_path=output,
            description="Thumbnail",
            audio_config=False,
            timeout=60,
        )
        
        if result.success:
            logger.info(f"✓ Thumbnail: {Path(output).name}")
            return ThumbnailResult(
                success=True,
                path=output,
                timestamp=timestamp,
                width=self.w if resize else 0,
                height=self.h if resize else 0,
                file_size=Path(output).stat().st_size,
            )
        
        return ThumbnailResult(
            success=False,
            error=result.error,
        )
    
    def create_multiple_thumbnails(
        self,
        video: str,
        output_dir: str,
        count: int = 3,
        avoid_edges: bool = True,
    ) -> list[ThumbnailResult]:
        """
        إنشاء عدة thumbnails.
        
        Args:
            video: مسار الفيديو
            output_dir: مجلد الإخراج
            count: العدد
            avoid_edges: تجنب البداية والنهاية
        """
        duration = self.get_duration(video)
        if duration == 0:
            duration = 30.0
        
        # حساب التوقيتات
        if avoid_edges:
            timestamps = [
                duration * (i + 1) / (count + 1)
                for i in range(count)
            ]
        else:
            timestamps = [
                duration * i / count if count > 0 else 0
                for i in range(count)
            ]
        
        Path(output_dir).mkdir(parents=True, exist_ok=True)
        video_name = Path(video).stem
        results = []
        
        for i, ts in enumerate(timestamps):
            output = str(Path(output_dir) / f"{video_name}_thumb_{i+1}.jpg")
            result = self.create_thumbnail(video, output, ts, resize=True)
            results.append(result)
        
        successful = sum(1 for r in results if r.success)
        logger.info(f"✓ {successful}/{count} thumbnails")
        
        return results
    
    def create_thumbnail_grid(
        self,
        video: str,
        output: str,
        rows: int = 2,
        cols: int = 3,
        thumb_width: int = 320,
    ) -> ThumbnailResult:
        """
        🆕 إنشاء grid من thumbnails (للـ preview).
        
        Args:
            video: مسار الفيديو
            output: مسار الـ grid
            rows: عدد الصفوف
            cols: عدد الأعمدة
            thumb_width: عرض كل thumbnail
        """
        if not Path(video).exists():
            return ThumbnailResult(
                success=False,
                error=f"Video not found: {video}",
            )
        
        Path(output).parent.mkdir(parents=True, exist_ok=True)
        
        # عدد الـ thumbnails
        count = rows * cols
        
        # الأمر مع select filter
        result = run_ffmpeg(
            args=[
                "-i", video,
                "-vf",
                f"select='not(mod(n,{count}))',scale={thumb_width}:-1,"
                f"tile={cols}x{rows}",
                "-vframes", "1",
            ],
            output_path=output,
            description="Thumbnail grid",
            audio_config=False,
        )
        
        if result.success:
            logger.info(f"✓ Grid: {Path(output).name} ({rows}x{cols})")
            return ThumbnailResult(
                success=True,
                path=output,
                file_size=Path(output).stat().st_size,
            )
        
        return ThumbnailResult(
            success=False,
            error=result.error,
        )
    
    # ═══════════════════════════════════════════════════════════════
    # Audio Extraction
    # ═══════════════════════════════════════════════════════════════
    def extract_audio(
        self,
        video: str,
        output: str,
        format: str = "mp3",
        bitrate: str = "192k",
    ) -> bool:
        """
        🆕 استخراج الصوت من الفيديو.
        
        Args:
            video: الفيديو
            output: مسار الصوت
            format: mp3 / wav / aac / m4a
            bitrate: bitrate
        """
        if not Path(video).exists():
            logger.error(f"Video not found: {video}")
            return False
        
        # خريطة codecs
        codec_map = {
            "mp3": "libmp3lame",
            "wav": "pcm_s16le",
            "aac": "aac",
            "m4a": "aac",
        }
        codec = codec_map.get(format, "libmp3lame")
        
        Path(output).parent.mkdir(parents=True, exist_ok=True)
        
        result = run_ffmpeg(
            args=[
                "-i", video,
                "-vn",  # no video
                "-c:a", codec,
                "-b:a", bitrate,
            ],
            output_path=output,
            description=f"Extract audio ({format})",
            audio_config=False,
        )
        
        if result.success:
            logger.info(f"✓ Audio extracted: {Path(output).name}")
        
        return result.success
    
    # ═══════════════════════════════════════════════════════════════
    # Platform Validation
    # ═══════════════════════════════════════════════════════════════
    def validate_for_platform(
        self,
        video_path: str,
        platform: str = "youtube_shorts",
    ) -> ValidationResult:
        """
        🎯 التحقق من توافق الفيديو للمنصة.
        
        Args:
            video_path: الفيديو
            platform: المنصة
        """
        result = ValidationResult(
            valid=True,
            platform=platform,
        )
        
        # جلب المعلومات
        info = self.get_video_info(video_path)
        if not info:
            result.valid = False
            result.errors.append("Failed to read video info")
            return result
        
        result.info = info
        
        # المواصفات
        spec = PLATFORM_SPECS.get(platform)
        if not spec:
            result.valid = False
            result.errors.append(f"Unknown platform: {platform}")
            return result
        
        # فحص الحجم
        if info.size_mb > spec.max_size_mb:
            result.errors.append(
                f"File too large: {info.size_mb:.1f}MB "
                f"> {spec.max_size_mb}MB"
            )
        
        # فحص المدة
        if info.duration > spec.max_duration:
            result.errors.append(
                f"Too long: {info.duration:.1f}s "
                f"> {spec.max_duration}s"
            )
        
        if info.duration < spec.min_duration:
            result.errors.append(
                f"Too short: {info.duration:.1f}s "
                f"< {spec.min_duration}s"
            )
        
        # فحص aspect ratio
        if spec.allowed_aspects and info.aspect_ratio not in spec.allowed_aspects:
            result.warnings.append(
                f"Aspect ratio {info.aspect_ratio} not in "
                f"{spec.allowed_aspects}"
            )
        
        # فحص الـ resolution
        if (info.width, info.height) != spec.preferred_resolution:
            result.warnings.append(
                f"Resolution {info.width}x{info.height} "
                f"(preferred: {spec.preferred_resolution[0]}x{spec.preferred_resolution[1]})"
            )
        
        # فحص codec
        if info.video_codec != spec.preferred_codec:
            result.warnings.append(
                f"Video codec '{info.video_codec}' "
                f"(preferred: {spec.preferred_codec})"
            )
        
        if info.has_audio and info.audio_codec != spec.preferred_audio_codec:
            result.warnings.append(
                f"Audio codec '{info.audio_codec}' "
                f"(preferred: {spec.preferred_audio_codec})"
            )
        
        # فحص bitrate
        if info.bitrate_kbps > spec.max_bitrate_kbps:
            result.warnings.append(
                f"Bitrate {info.bitrate_kbps}kbps "
                f"> {spec.max_bitrate_kbps}kbps"
            )
        
        # تحديد النتيجة النهائية
        result.valid = len(result.errors) == 0
        
        return result
    
    # ═══════════════════════════════════════════════════════════════
    # Utility
    # ═══════════════════════════════════════════════════════════════
    @staticmethod
    def list_platforms() -> list[str]:
        """قائمة المنصات."""
        return list(PLATFORM_SPECS.keys())
    
    @staticmethod
    def get_platform_spec(platform: str) -> Optional[PlatformSpec]:
        """مواصفات منصة."""
        return PLATFORM_SPECS.get(platform)
    
    def clear_cache(self) -> int:
        """مسح الكاش."""
        global _video_info_cache
        count = len(_video_info_cache)
        _video_info_cache.clear()
        logger.info(f"🗑 Cleared {count} cached items")
        return count


# ═══════════════════════════════════════════════════════════════════
# اختبار
# ═══════════════════════════════════════════════════════════════════
if __name__ == "__main__":
    import sys
    
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s | %(levelname)s | %(message)s"
    )
    
    if len(sys.argv) < 2:
        print("Usage: python video_utils.py <video.mp4> [action]")
        print("Actions: info, thumbnail, thumbnails, grid, validate, audio")
        sys.exit(1)
    
    utils = VideoUtils()
    video = sys.argv[1]
    action = sys.argv[2] if len(sys.argv) > 2 else "info"
    
    print("=" * 60)
    print(f"🛠️ Video Utils v2.0 - {action}")
    print("=" * 60)
    
    if action == "info":
        info = utils.get_video_info(video)
        if info:
            print(f"\n📊 Video Info:")
            print(f"   Duration: {info.duration:.2f}s")
            print(f"   Size: {info.size_mb:.1f} MB")
            print(f"   Resolution: {info.width}x{info.height} ({info.resolution_label})")
            print(f"   Aspect: {info.aspect_ratio} ({'portrait' if info.is_portrait else 'landscape'})")
            print(f"   FPS: {info.fps}")
            print(f"   Video codec: {info.video_codec}")
            print(f"   Audio: {info.audio_codec} ({info.audio_channels}ch)")
            print(f"   Bitrate: {info.bitrate_kbps} kbps")
    
    elif action == "thumbnail":
        result = utils.create_thumbnail(video, "thumb.jpg")
        if result.success:
            print(f"\n✓ {result.path} ({result.file_size:,} bytes)")
        else:
            print(f"\n❌ {result.error}")
    
    elif action == "thumbnails":
        results = utils.create_multiple_thumbnails(video, "./thumbs", count=5)
        successful = sum(1 for r in results if r.success)
        print(f"\n✓ {successful}/5 thumbnails created")
    
    elif action == "grid":
        result = utils.create_thumbnail_grid(video, "grid.jpg", rows=3, cols=4)
        if result.success:
            print(f"\n✓ {result.path}")
        else:
            print(f"\n❌ {result.error}")
    
    elif action == "validate":
        platforms = utils.list_platforms()
        print(f"\n📱 Validating for all platforms:\n")
        for platform in platforms:
            result = utils.validate_for_platform(video, platform)
            status = "✅" if result.valid else "❌"
            print(f"{status} {platform}")
            if result.errors:
                for e in result.errors:
                    print(f"   ❌ {e}")
            if result.warnings:
                for w in result.warnings[:2]:
                    print(f"   ⚠ {w}")
    
    elif action == "audio":
        success = utils.extract_audio(video, "audio.mp3")
        print(f"\n{'✓' if success else '❌'} Audio extraction")
