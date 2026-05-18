"""
🎞️ FFmpeg Builder v2.0 — Pro
═══════════════════════════════════════════════════════════════
محرك التصدير النهائي (مبسّط):
  ✓ تصدير MP4 احترافي
  ✓ Concat لعدة فيديوهات
  ✓ Merge مع audio منفصل
  ✓ Progress tracking
  ✓ Result dataclass
  ✓ يفوّض الباقي لـ VideoUtils

التحسينات v2.0:
  ✓ يستخدم ffmpeg_utils
  ✓ يفوّض لـ VideoUtils
  ✓ RenderResult dataclass
  ✓ Progress callback
  ✓ Concat support
  ✓ Audio merge
  ✓ لا eval()
═══════════════════════════════════════════════════════════════
"""

from __future__ import annotations

import os
import time
import shutil
import logging
import subprocess
from pathlib import Path
from enum import Enum
from dataclasses import dataclass, field
from typing import Optional, Callable

from engine.video.voice.ffmpeg_utils import (
    check_ffmpeg_available, run_ffmpeg, get_audio_duration,
)
from .video_utils import VideoUtils, VideoInfo

logger = logging.getLogger(__name__)


# ═══════════════════════════════════════════════════════════════════
# Enums
# ═══════════════════════════════════════════════════════════════════
class RenderQuality(str, Enum):
    """جودة التصدير."""
    DRAFT = "draft"
    MEDIUM = "medium"
    HIGH = "high"
    ULTRA = "ultra"


# ═══════════════════════════════════════════════════════════════════
# Dataclasses
# ═══════════════════════════════════════════════════════════════════
@dataclass
class QualityPreset:
    """preset جودة."""
    name: str
    crf: int = 19
    preset: str = "medium"  # ultrafast → veryslow
    audio_bitrate: str = "192k"
    audio_rate: int = 44100
    video_bitrate: Optional[str] = None  # None = CRF mode
    profile: str = "high"
    level: str = "4.1"
    
    def to_args(self) -> list[str]:
        """تحويل لـ FFmpeg args."""
        args = [
            "-c:v", "libx264",
            "-crf", str(self.crf),
            "-preset", self.preset,
            "-profile:v", self.profile,
            "-level:v", self.level,
            "-pix_fmt", "yuv420p",
            "-c:a", "aac",
            "-b:a", self.audio_bitrate,
            "-ar", str(self.audio_rate),
            "-ac", "2",
        ]
        
        if self.video_bitrate:
            args.extend(["-b:v", self.video_bitrate])
        
        return args


@dataclass
class RenderResult:
    """نتيجة التصدير."""
    success: bool
    output_path: str = ""
    file_size_mb: float = 0.0
    duration: float = 0.0
    width: int = 0
    height: int = 0
    quality: str = ""
    elapsed_seconds: float = 0.0
    error: Optional[str] = None
    info: Optional[VideoInfo] = None
    
    def summary(self) -> str:
        return (
            f"📊 Render Result:\n"
            f"   • Status: {'✅' if self.success else '❌'}\n"
            f"   • Output: {Path(self.output_path).name if self.output_path else 'N/A'}\n"
            f"   • Size: {self.file_size_mb:.1f} MB\n"
            f"   • Duration: {self.duration:.1f}s\n"
            f"   • Resolution: {self.width}x{self.height}\n"
            f"   • Quality: {self.quality}\n"
            f"   • Time: {self.elapsed_seconds:.1f}s"
        )


# ═══════════════════════════════════════════════════════════════════
# Presets
# ═══════════════════════════════════════════════════════════════════
QUALITY_PRESETS: dict[str, QualityPreset] = {
    "draft": QualityPreset(
        name="draft", crf=28, preset="ultrafast",
        audio_bitrate="96k", audio_rate=44100,
    ),
    "medium": QualityPreset(
        name="medium", crf=23, preset="fast",
        audio_bitrate="128k", audio_rate=44100,
    ),
    "high": QualityPreset(
        name="high", crf=19, preset="medium",
        audio_bitrate="192k", audio_rate=44100,
    ),
    "ultra": QualityPreset(
        name="ultra", crf=17, preset="slow",
        audio_bitrate="256k", audio_rate=48000,
    ),
}

# Legacy presets
LEGACY_PRESETS: dict[str, str] = {
    "tiktok": "high",
    "reels": "ultra",
    "shorts": "high",
    "preview": "medium",
}


# ═══════════════════════════════════════════════════════════════════
# Constants
# ═══════════════════════════════════════════════════════════════════
class BuilderConstants:
    """ثوابت."""
    
    DEFAULT_TIMEOUT = 600  # 10 دقائق
    MAX_METADATA_LENGTH = 200
    
    # Streaming optimization
    STREAMING_FLAGS = ["-movflags", "+faststart"]


# ═══════════════════════════════════════════════════════════════════
# Main Class
# ═══════════════════════════════════════════════════════════════════
class FFmpegBuilder:
    """محرك التصدير v2.0."""
    
    def __init__(
        self,
        width: Optional[int] = None,
        height: Optional[int] = None,
        fps: Optional[int] = None,
    ):
        """
        Args:
            width, height, fps: أبعاد افتراضية
        """
        # Settings
        self.w = width or int(os.getenv("VIDEO_WIDTH", "1080"))
        self.h = height or int(os.getenv("VIDEO_HEIGHT", "1920"))
        self.fps = fps or int(os.getenv("VIDEO_FPS", "30"))
        
        # Directories
        self.temp_dir = Path(os.getenv("TEMP_DIR", "./temp"))
        self.out_dir = Path(os.getenv("OUTPUT_DIR", "./output"))
        self.temp_dir.mkdir(parents=True, exist_ok=True)
        self.out_dir.mkdir(parents=True, exist_ok=True)
        
        # FFmpeg check
        if not check_ffmpeg_available():
            raise RuntimeError(
                "❌ FFmpeg غير مثبت!\n"
                "   Ubuntu: sudo apt install ffmpeg\n"
                "   macOS:  brew install ffmpeg"
            )
        
        # Utils (للـ thumbnails, info, validation)
        self.utils = VideoUtils(
            width=self.w,
            height=self.h,
            fps=self.fps,
        )
        
        logger.info(
            f"🎞️ FFmpegBuilder v2.0 | {self.w}x{self.h}@{self.fps}fps"
        )
    
    # ═══════════════════════════════════════════════════════════════
    # Main Render
    # ═══════════════════════════════════════════════════════════════
    def render(
        self,
        input_video: str,
        output_path: str,
        quality: str = "high",
        metadata: Optional[dict] = None,
        input_audio: Optional[str] = None,
        timeout: int = BuilderConstants.DEFAULT_TIMEOUT,
        progress_callback: Optional[Callable[[str], None]] = None,
    ) -> RenderResult:
        """
        🎯 التصدير النهائي.
        
        Args:
            input_video: الفيديو المُدخل
            output_path: مسار الإخراج
            quality: draft / medium / high / ultra
            metadata: metadata للفيديو
            input_audio: صوت منفصل (اختياري)
            timeout: timeout بالثواني
            progress_callback: callback للحالة
        """
        start_time = time.time()
        
        # Validation
        if not Path(input_video).exists():
            return RenderResult(
                success=False,
                error=f"Video not found: {input_video}",
            )
        
        if input_audio and not Path(input_audio).exists():
            return RenderResult(
                success=False,
                error=f"Audio not found: {input_audio}",
            )
        
        # Quality preset
        preset = QUALITY_PRESETS.get(quality, QUALITY_PRESETS["high"])
        
        # Output directory
        Path(output_path).parent.mkdir(parents=True, exist_ok=True)
        
        logger.info(f"🚀 Rendering [{quality}]...")
        if progress_callback:
            progress_callback(f"Starting [{quality}]")
        
        # Build command
        cmd_args = self._build_render_args(
            input_video=input_video,
            input_audio=input_audio,
            preset=preset,
            metadata=metadata,
        )
        
        # Execute
        if progress_callback:
            progress_callback("Encoding...")
        
        result = run_ffmpeg(
            args=cmd_args,
            output_path=output_path,
            description=f"Render {quality}",
            audio_config=False,  # نضع config يدوياً
            timeout=timeout,
        )
        
        elapsed = time.time() - start_time
        
        if not result.success:
            return RenderResult(
                success=False,
                output_path=output_path,
                quality=quality,
                error=result.error,
                elapsed_seconds=elapsed,
            )
        
        # جلب معلومات الـ output
        if progress_callback:
            progress_callback("Validating output...")
        
        info = self.utils.get_video_info(output_path)
        
        render_result = RenderResult(
            success=True,
            output_path=output_path,
            quality=quality,
            elapsed_seconds=elapsed,
            info=info,
        )
        
        if info:
            render_result.file_size_mb = info.size_mb
            render_result.duration = info.duration
            render_result.width = info.width
            render_result.height = info.height
        
        # تحذيرات platform
        self._check_platform_warnings(render_result)
        
        logger.info(render_result.summary())
        
        if progress_callback:
            progress_callback("Done!")
        
        return render_result
    
    # ═══════════════════════════════════════════════════════════════
    # Backward Compatibility
    # ═══════════════════════════════════════════════════════════════
    def render_final(
        self,
        input_video: str,
        output_path: str,
        quality: str = "high",
        metadata: Optional[dict] = None,
        preset: Optional[str] = None,
    ) -> str:
        """متوافق مع v1."""
        # Legacy preset
        if preset and quality == "high":
            quality = LEGACY_PRESETS.get(preset, "high")
        
        result = self.render(
            input_video=input_video,
            output_path=output_path,
            quality=quality,
            metadata=metadata,
        )
        
        if not result.success:
            raise RuntimeError(result.error)
        
        return result.output_path
    
    # ═══════════════════════════════════════════════════════════════
    # Concat Videos
    # ═══════════════════════════════════════════════════════════════
    def concat_videos(
        self,
        video_paths: list[str],
        output_path: str,
        quality: str = "high",
        method: str = "demuxer",  # demuxer or filter
    ) -> RenderResult:
        """
        🆕 دمج عدة فيديوهات.
        
        Args:
            video_paths: قائمة الفيديوهات
            output_path: مسار الإخراج
            quality: الجودة
            method: demuxer (سريع) أو filter (للترميز)
        """
        start_time = time.time()
        
        # Validation
        valid_videos = [v for v in video_paths if Path(v).exists()]
        if not valid_videos:
            return RenderResult(
                success=False,
                error="No valid videos",
            )
        
        if len(valid_videos) == 1:
            # نسخ مباشر
            shutil.copy(valid_videos[0], output_path)
            info = self.utils.get_video_info(output_path)
            return RenderResult(
                success=True,
                output_path=output_path,
                quality=quality,
                info=info,
                file_size_mb=info.size_mb if info else 0,
                duration=info.duration if info else 0,
                width=info.width if info else 0,
                height=info.height if info else 0,
                elapsed_seconds=time.time() - start_time,
            )
        
        logger.info(f"🔗 Concatenating {len(valid_videos)} videos...")
        
        if method == "demuxer":
            return self._concat_demuxer(valid_videos, output_path, quality, start_time)
        else:
            return self._concat_filter(valid_videos, output_path, quality, start_time)
    
    def _concat_demuxer(
        self,
        videos: list[str],
        output_path: str,
        quality: str,
        start_time: float,
    ) -> RenderResult:
        """دمج بـ concat demuxer (سريع، يحتاج نفس الـ codec)."""
        # إنشاء list file
        list_file = self.temp_dir / f"concat_{int(time.time())}.txt"
        try:
            with open(list_file, "w", encoding="utf-8") as f:
                for v in videos:
                    abs_path = Path(v).resolve()
                    f.write(f"file '{abs_path}'\n")
            
            preset = QUALITY_PRESETS.get(quality, QUALITY_PRESETS["high"])
            
            args = [
                "-f", "concat",
                "-safe", "0",
                "-i", str(list_file),
                "-c", "copy",  # نسخ بدون re-encode (أسرع)
            ]
            
            result = run_ffmpeg(
                args=args,
                output_path=output_path,
                description="Concat (demuxer)",
                audio_config=False,
            )
            
            if not result.success:
                # Fallback: filter method
                logger.warning("⚠ Demuxer failed, trying filter...")
                return self._concat_filter(videos, output_path, quality, start_time)
            
            info = self.utils.get_video_info(output_path)
            return RenderResult(
                success=True,
                output_path=output_path,
                quality=quality,
                info=info,
                file_size_mb=info.size_mb if info else 0,
                duration=info.duration if info else 0,
                width=info.width if info else 0,
                height=info.height if info else 0,
                elapsed_seconds=time.time() - start_time,
            )
            
        finally:
            list_file.unlink(missing_ok=True)
    
    def _concat_filter(
        self,
        videos: list[str],
        output_path: str,
        quality: str,
        start_time: float,
    ) -> RenderResult:
        """دمج بـ concat filter (re-encode، يعمل دائماً)."""
        # بناء filter
        inputs = []
        for v in videos:
            inputs.extend(["-i", v])
        
        n = len(videos)
        filter_str = "".join(
            f"[{i}:v][{i}:a]"
            for i in range(n)
        ) + f"concat=n={n}:v=1:a=1[outv][outa]"
        
        preset = QUALITY_PRESETS.get(quality, QUALITY_PRESETS["high"])
        
        args = inputs + [
            "-filter_complex", filter_str,
            "-map", "[outv]",
            "-map", "[outa]",
            *preset.to_args(),
        ]
        
        result = run_ffmpeg(
            args=args,
            output_path=output_path,
            description="Concat (filter)",
            audio_config=False,
        )
        
        if not result.success:
            return RenderResult(
                success=False,
                output_path=output_path,
                error=result.error,
                elapsed_seconds=time.time() - start_time,
            )
        
        info = self.utils.get_video_info(output_path)
        return RenderResult(
            success=True,
            output_path=output_path,
            quality=quality,
            info=info,
            file_size_mb=info.size_mb if info else 0,
            duration=info.duration if info else 0,
            width=info.width if info else 0,
            height=info.height if info else 0,
            elapsed_seconds=time.time() - start_time,
        )
    
    # ═══════════════════════════════════════════════════════════════
    # Merge Audio
    # ═══════════════════════════════════════════════════════════════
    def merge_video_audio(
        self,
        video_path: str,
        audio_path: str,
        output_path: str,
        replace_audio: bool = True,
    ) -> RenderResult:
        """
        🆕 دمج صوت مع فيديو.
        
        Args:
            video_path: الفيديو
            audio_path: الصوت
            output_path: الإخراج
            replace_audio: استبدال الصوت الأصلي (True) أو mix (False)
        """
        start_time = time.time()
        
        if not Path(video_path).exists() or not Path(audio_path).exists():
            return RenderResult(
                success=False,
                error="Input files not found",
            )
        
        logger.info(f"🔊 Merging audio with video...")
        
        if replace_audio:
            args = [
                "-i", video_path,
                "-i", audio_path,
                "-c:v", "copy",  # نسخ video بدون re-encode
                "-c:a", "aac",
                "-b:a", "192k",
                "-map", "0:v:0",
                "-map", "1:a:0",
                "-shortest",
            ]
        else:
            # mix الـ audios
            args = [
                "-i", video_path,
                "-i", audio_path,
                "-filter_complex",
                "[0:a][1:a]amix=inputs=2:duration=longest[aout]",
                "-map", "0:v",
                "-map", "[aout]",
                "-c:v", "copy",
                "-c:a", "aac",
                "-b:a", "192k",
            ]
        
        result = run_ffmpeg(
            args=args,
            output_path=output_path,
            description="Merge audio",
            audio_config=False,
        )
        
        elapsed = time.time() - start_time
        
        if not result.success:
            return RenderResult(
                success=False,
                output_path=output_path,
                error=result.error,
                elapsed_seconds=elapsed,
            )
        
        info = self.utils.get_video_info(output_path)
        return RenderResult(
            success=True,
            output_path=output_path,
            info=info,
            file_size_mb=info.size_mb if info else 0,
            duration=info.duration if info else 0,
            width=info.width if info else 0,
            height=info.height if info else 0,
            elapsed_seconds=elapsed,
        )
    
    # ═══════════════════════════════════════════════════════════════
    # Command Building
    # ═══════════════════════════════════════════════════════════════
    def _build_render_args(
        self,
        input_video: str,
        preset: QualityPreset,
        input_audio: Optional[str] = None,
        metadata: Optional[dict] = None,
    ) -> list[str]:
        """بناء FFmpeg args."""
        args = ["-i", input_video]
        
        # Audio منفصل
        if input_audio:
            args.extend(["-i", input_audio, "-map", "0:v", "-map", "1:a"])
        
        # FPS + Quality
        args.extend(["-r", str(self.fps)])
        args.extend(preset.to_args())
        
        # Streaming optimization
        args.extend(BuilderConstants.STREAMING_FLAGS)
        
        # Metadata
        if metadata:
            args.extend(self._build_metadata_args(metadata))
        
        return args
    
    @staticmethod
    def _build_metadata_args(metadata: dict) -> list[str]:
        """بناء metadata args."""
        args = []
        
        field_map = {
            "title": "title",
            "description": "comment",
            "comment": "comment",
            "author": "author",
            "artist": "artist",
            "album": "album",
            "year": "date",
            "genre": "genre",
        }
        
        for key, ffmpeg_key in field_map.items():
            value = metadata.get(key)
            if value:
                value = str(value).replace('"', "'")[:BuilderConstants.MAX_METADATA_LENGTH]
                args.extend(["-metadata", f"{ffmpeg_key}={value}"])
        
        return args
    
    # ═══════════════════════════════════════════════════════════════
    # Platform Warnings
    # ═══════════════════════════════════════════════════════════════
    def _check_platform_warnings(self, result: RenderResult) -> None:
        """تحذيرات platform."""
        # سيستخدم validate_for_platform من VideoUtils
        for platform in ["youtube_shorts", "tiktok", "instagram_reel"]:
            validation = self.utils.validate_for_platform(
                result.output_path,
                platform,
            )
            
            if validation.errors:
                logger.warning(f"⚠ {platform}: {validation.errors[0]}")
    
    # ═══════════════════════════════════════════════════════════════
    # Delegated to VideoUtils
    # ═══════════════════════════════════════════════════════════════
    def create_thumbnail(self, video, output, timestamp=1.5, resize=True):
        """يفوّض لـ VideoUtils."""
        result = self.utils.create_thumbnail(video, output, timestamp, resize)
        return result.path if result.success else ""
    
    def create_multiple_thumbnails(self, video, output_dir, count=3):
        """يفوّض لـ VideoUtils."""
        results = self.utils.create_multiple_thumbnails(video, output_dir, count)
        return [r.path for r in results if r.success]
    
    def get_duration(self, path):
        """يفوّض لـ VideoUtils."""
        return self.utils.get_duration(path)
    
    def get_dimensions(self, path):
        """يفوّض لـ VideoUtils."""
        return self.utils.get_dimensions(path)
    
    def get_video_info(self, path):
        """يفوّض لـ VideoUtils."""
        info = self.utils.get_video_info(path)
        return info.to_dict() if info else {}
    
    def validate_for_platform(self, video_path, platform="youtube_shorts"):
        """يفوّض لـ VideoUtils."""
        result = self.utils.validate_for_platform(video_path, platform)
        return result.to_dict()
    
    # ═══════════════════════════════════════════════════════════════
    # Cleanup
    # ═══════════════════════════════════════════════════════════════
    def cleanup_temp(self, keep_subdirs: bool = False) -> int:
        """تنظيف temp."""
        count = 0
        try:
            if not self.temp_dir.exists():
                return 0
            
            if keep_subdirs:
                for f in self.temp_dir.rglob("*"):
                    if f.is_file():
                        f.unlink(missing_ok=True)
                        count += 1
            else:
                shutil.rmtree(self.temp_dir, ignore_errors=True)
                self.temp_dir.mkdir(parents=True, exist_ok=True)
            
            logger.info(f"🧹 Cleaned {count} files")
        except Exception as e:
            logger.warning(f"⚠ Cleanup failed: {e}")
        
        return count
    
    def cleanup_specific(self, patterns: list[str]) -> int:
        """تنظيف patterns."""
        count = 0
        try:
            for pattern in patterns:
                for f in self.temp_dir.rglob(pattern):
                    if f.is_file():
                        f.unlink(missing_ok=True)
                        count += 1
            
            if count > 0:
                logger.info(f"🧹 Deleted {count} files")
        except Exception as e:
            logger.warning(f"⚠ Cleanup failed: {e}")
        
        return count
    
    @staticmethod
    def list_qualities() -> list[str]:
        """قائمة الجودات."""
        return list(QUALITY_PRESETS.keys())


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
        print("Usage: python ffmpeg_builder.py <video.mp4> [action] [args]")
        print("Actions: render, concat, merge, info")
        sys.exit(1)
    
    builder = FFmpegBuilder()
    video = sys.argv[1]
    action = sys.argv[2] if len(sys.argv) > 2 else "info"
    
    print("=" * 60)
    print(f"🎞️ FFmpeg Builder v2.0 - {action}")
    print("=" * 60)
    
    if action == "render":
        output = sys.argv[3] if len(sys.argv) > 3 else "output.mp4"
        quality = sys.argv[4] if len(sys.argv) > 4 else "high"
        
        def progress(msg):
            print(f"  → {msg}")
        
        result = builder.render(
            video, output, quality=quality,
            progress_callback=progress,
        )
        print()
        print(result.summary())
    
    elif action == "concat":
        # python script.py video1.mp4 concat output.mp4 video2.mp4 video3.mp4
        output = sys.argv[3]
        videos = [video] + sys.argv[4:]
        
        result = builder.concat_videos(videos, output)
        print()
        print(result.summary())
    
    elif action == "merge":
        # python script.py video.mp4 merge audio.mp3 output.mp4
        audio = sys.argv[3]
        output = sys.argv[4]
        
        result = builder.merge_video_audio(video, audio, output)
        print()
        print(result.summary())
    
    elif action == "info":
        info = builder.get_video_info(video)
        import json
        print(json.dumps(info, indent=2, ensure_ascii=False))
    
    print("\n✅ Done!")
