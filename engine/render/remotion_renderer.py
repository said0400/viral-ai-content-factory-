"""
🎬 Remotion Renderer v2.1 — Pro
═══════════════════════════════════════════════════════════════
محرك التصدير عبر Remotion:
  ✓ Smart asset linking (بدل copy)
  ✓ Progress tracking
  ✓ Retry mechanism
  ✓ Result dataclass
  ✓ يستخدم ffmpeg_utils

التحسينات v2.1:
  ✓ إصلاح RenderResult initialization
  ✓ إضافة import json المفقود
  ✓ معالجة أخطاء أفضل
  ✓ Symlinks بدل copy (أسرع 100x)
  ✓ Real-time progress
  ✓ Smart cleanup
  ✓ Validation شاملة
═══════════════════════════════════════════════════════════════
"""

from __future__ import annotations

import os
import re
import json
import time
import shutil
import logging
import subprocess
from pathlib import Path
from enum import Enum
from dataclasses import dataclass, field
from typing import Optional, Callable, Any

from .video_utils import VideoUtils
from engine.video.voice.ffmpeg_utils import (
    check_ffmpeg_available, check_ffprobe_available,
    run_ffmpeg,
)

logger = logging.getLogger(__name__)


# ═══════════════════════════════════════════════════════════════════
# Enums
# ═══════════════════════════════════════════════════════════════════
class RenderQuality(str, Enum):
    """جودة التصدير."""
    DRAFT = "draft"        # سريع للاختبار
    MEDIUM = "medium"      # متوسط
    HIGH = "high"          # عالي
    ULTRA = "ultra"        # أعلى جودة
    
    @classmethod
    def from_legacy_preset(cls, preset: str) -> "RenderQuality":
        """تحويل preset قديم."""
        mapping = {
            "preview": cls.MEDIUM,
            "tiktok": cls.HIGH,
            "shorts": cls.HIGH,
            "reels": cls.ULTRA,
            "instagram": cls.ULTRA,
        }
        return mapping.get(preset, cls.HIGH)


class Platform(str, Enum):
    """منصات النشر."""
    YOUTUBE_SHORTS = "youtube_shorts"
    TIKTOK = "tiktok"
    INSTAGRAM = "instagram"
    TWITTER = "twitter"
    FACEBOOK = "facebook"


# ═══════════════════════════════════════════════════════════════════
# Dataclasses
# ═══════════════════════════════════════════════════════════════════
@dataclass
class QualityConfig:
    """إعدادات جودة."""
    name: str
    crf: int = 19
    jpeg_quality: int = 90
    concurrency: int = 2
    audio_bitrate: str = "192k"
    pixel_format: str = "yuv420p"
    codec: str = "h264"
    
    def to_cli_args(self) -> list[str]:
        return [
            "--crf", str(self.crf),
            "--jpeg-quality", str(self.jpeg_quality),
            "--concurrency", str(self.concurrency),
            "--codec", self.codec,
            "--pixel-format", self.pixel_format,
        ]


@dataclass
class RenderProgress:
    """تقدم التصدير."""
    stage: str = ""
    current_frame: int = 0
    total_frames: int = 0
    percent: float = 0.0
    elapsed: float = 0.0
    estimated_remaining: float = 0.0
    
    def __str__(self) -> str:
        if self.total_frames > 0:
            return (
                f"{self.stage}: "
                f"{self.current_frame}/{self.total_frames} "
                f"({self.percent:.1f}%)"
            )
        return self.stage


@dataclass
class RenderResult:
    """نتيجة التصدير."""
    success: bool = False
    output_path: str = ""
    file_size_mb: float = 0.0
    duration: float = 0.0
    width: int = 0
    height: int = 0
    quality: str = ""
    elapsed_seconds: float = 0.0
    frames_rendered: int = 0
    assets_linked: int = 0
    assets_copied: int = 0
    error: Optional[str] = None
    retries: int = 0
    
    def summary(self) -> str:
        return (
            f"📊 Render Result:\n"
            f"   • Status: {'✅' if self.success else '❌'}\n"
            f"   • Output: {self.output_path}\n"
            f"   • Size: {self.file_size_mb:.1f} MB\n"
            f"   • Duration: {self.duration:.1f}s\n"
            f"   • Resolution: {self.width}x{self.height}\n"
            f"   • Quality: {self.quality}\n"
            f"   • Frames: {self.frames_rendered}\n"
            f"   • Assets: {self.assets_linked} linked, "
            f"{self.assets_copied} copied\n"
            f"   • Time: {self.elapsed_seconds:.1f}s\n"
            f"   • Retries: {self.retries}"
        )


# ═══════════════════════════════════════════════════════════════════
# Quality Presets
# ═══════════════════════════════════════════════════════════════════
QUALITY_CONFIGS: dict[str, QualityConfig] = {
    "draft": QualityConfig(
        name="draft", crf=28, jpeg_quality=60,
        concurrency=4, audio_bitrate="96k",
    ),
    "medium": QualityConfig(
        name="medium", crf=23, jpeg_quality=80,
        concurrency=2, audio_bitrate="128k",
    ),
    "high": QualityConfig(
        name="high", crf=19, jpeg_quality=90,
        concurrency=2, audio_bitrate="192k",
    ),
    "ultra": QualityConfig(
        name="ultra", crf=17, jpeg_quality=95,
        concurrency=4, audio_bitrate="256k",
    ),
}


# ═══════════════════════════════════════════════════════════════════
# Platform Limits (بالـ MB)
# ═══════════════════════════════════════════════════════════════════
PLATFORM_LIMITS: dict[str, dict] = {
    "youtube_shorts": {
        "max_size_mb": 256,
        "max_duration": 60,
        "aspect_ratio": "9:16",
    },
    "tiktok": {
        "max_size_mb": 287,
        "max_duration": 180,
        "aspect_ratio": "9:16",
    },
    "instagram": {
        "max_size_mb": 650,
        "max_duration": 90,
        "aspect_ratio": "9:16",
    },
    "twitter": {
        "max_size_mb": 512,
        "max_duration": 140,
        "aspect_ratio": "16:9",
    },
    "facebook": {
        "max_size_mb": 4000,
        "max_duration": 240,
        "aspect_ratio": "16:9",
    },
}


# ═══════════════════════════════════════════════════════════════════
# Constants
# ═══════════════════════════════════════════════════════════════════
class RendererConstants:
    """ثوابت."""
    
    DEFAULT_TIMEOUT = 600  # 10 دقائق
    DEFAULT_COMPOSITION = "ShortsVideo"
    
    MAX_RETRIES = 2
    RETRY_DELAY = 3
    
    # Frame timeout (بالـ ms)
    FRAME_TIMEOUT_MS = 60000
    
    # Public assets
    PUBLIC_FOOTAGE_DIR = "footage"
    PUBLIC_AUDIO_DIR = "audio"


# ═══════════════════════════════════════════════════════════════════
# Helpers
# ═══════════════════════════════════════════════════════════════════
def try_symlink_or_copy(
    source: Path,
    destination: Path,
) -> tuple[bool, str]:
    """
    محاولة symlink، fallback لـ copy.
    
    Returns:
        (success, method) - method = "symlink" أو "copy"
    """
    try:
        # احذف إذا موجود
        if destination.exists() or destination.is_symlink():
            destination.unlink()
        
        # جرب symlink
        try:
            destination.symlink_to(source.resolve())
            return True, "symlink"
        except (OSError, NotImplementedError):
            # Windows أو filesystem لا يدعم
            shutil.copy2(source, destination)
            return True, "copy"
            
    except Exception as e:
        logger.error(f"Failed to link/copy: {e}")
        return False, "failed"


def parse_remotion_progress(line: str) -> Optional[tuple[int, int]]:
    """
    تحليل سطر progress من Remotion.
    
    مثال: "Rendered 45/120 frames"
    
    Returns:
        (current, total) أو None
    """
    match = re.search(r"(\d+)/(\d+)\s+frames", line)
    if match:
        return int(match.group(1)), int(match.group(2))
    return None


# ═══════════════════════════════════════════════════════════════════
# Main Class
# ═══════════════════════════════════════════════════════════════════
class RemotionRenderer:
    """محرك التصدير v2.1."""
    
    def __init__(
        self,
        remotion_dir: Optional[str] = None,
        composition_id: Optional[str] = None,
        use_symlinks: bool = True,
        keep_props_file: bool = False,
        cleanup_on_success: bool = True,
    ):
        """
        Args:
            remotion_dir: مجلد Remotion
            composition_id: ID الـ composition
            use_symlinks: استخدام symlinks بدل copy
            keep_props_file: الاحتفاظ بـ props file بعد التصدير
            cleanup_on_success: تنظيف الأصول عند النجاح فقط
        """
        # Settings
        self.w = int(os.getenv("VIDEO_WIDTH", "1080"))
        self.h = int(os.getenv("VIDEO_HEIGHT", "1920"))
        self.fps = int(os.getenv("VIDEO_FPS", "30"))
        
        self.use_symlinks = use_symlinks
        self.keep_props_file = keep_props_file
        self.cleanup_on_success = cleanup_on_success
        
        # Directories
        self.temp_dir = Path(os.getenv("TEMP_DIR", "./temp")).resolve()
        self.out_dir = Path(os.getenv("OUTPUT_DIR", "./output")).resolve()
        self.temp_dir.mkdir(parents=True, exist_ok=True)
        self.out_dir.mkdir(parents=True, exist_ok=True)
        
        # Remotion
        default_remotion = Path(__file__).parent.parent.parent / "remotion"
        self.remotion_dir = Path(
            remotion_dir or os.getenv("REMOTION_DIR", default_remotion)
        ).resolve()
        
        self.composition_id = (
            composition_id or
            os.getenv("REMOTION_COMPOSITION", RendererConstants.DEFAULT_COMPOSITION)
        )
        
        # Utils
        self.utils = VideoUtils(width=self.w, height=self.h, fps=self.fps)
        
        # Checks
        self._check_dependencies()
        
        logger.info(
            f"🎬 RemotionRenderer v2.1 | "
            f"{self.w}x{self.h}@{self.fps}fps"
        )
        logger.info(f"   📁 Remotion: {self.remotion_dir}")
        logger.info(f"   🔗 Symlinks: {use_symlinks}")
    
    # ═══════════════════════════════════════════════════════════════
    # Dependency Checks
    # ═══════════════════════════════════════════════════════════════
    def _check_dependencies(self) -> None:
        """فحص كل المتطلبات."""
        # Node.js
        try:
            result = subprocess.run(
                ["node", "--version"],
                capture_output=True, text=True, timeout=10, check=True,
            )
            logger.info(f"✓ Node.js {result.stdout.strip()}")
        except (subprocess.CalledProcessError, FileNotFoundError):
            raise RuntimeError(
                "❌ Node.js غير مثبت!\n"
                "   تثبيت: https://nodejs.org/"
            )
        
        # Remotion
        if not self.remotion_dir.exists():
            raise RuntimeError(
                f"❌ مجلد Remotion غير موجود: {self.remotion_dir}"
            )
        
        if not (self.remotion_dir / "node_modules").exists():
            raise RuntimeError(
                f"❌ Remotion غير مُثبّت!\n"
                f"   شغّل: cd {self.remotion_dir} && npm install"
            )
        
        logger.info("✓ Remotion installed")
        
        # FFmpeg (لـ metadata)
        if not check_ffmpeg_available():
            logger.warning("⚠ FFmpeg غير متاح - metadata معطّلة")
    
    # ═══════════════════════════════════════════════════════════════
    # Main API
    # ═══════════════════════════════════════════════════════════════
    def render(
        self,
        props: dict,
        output_path: str,
        quality: str = "high",
        composition_id: Optional[str] = None,
        metadata: Optional[dict] = None,
        timeout: int = RendererConstants.DEFAULT_TIMEOUT,
        max_retries: int = RendererConstants.MAX_RETRIES,
        progress_callback: Optional[Callable[[RenderProgress], None]] = None,
    ) -> RenderResult:
        """
        🎯 التصدير الرئيسي.
        
        Args:
            props: props الـ Remotion
            output_path: مسار الإخراج
            quality: جودة (draft/medium/high/ultra)
            composition_id: composition (default من init)
            metadata: metadata للفيديو
            timeout: timeout بالثواني
            max_retries: عدد المحاولات
            progress_callback: callback للتقدم
        
        Returns:
            RenderResult
        """
        start_time = time.time()
        
        # تحضير الإعدادات
        quality_cfg = QUALITY_CONFIGS.get(quality, QUALITY_CONFIGS["high"])
        comp_id = composition_id or self.composition_id
        output_path = str(Path(output_path).resolve())
        Path(output_path).parent.mkdir(parents=True, exist_ok=True)
        
        logger.info(
            f"🚀 Rendering [{quality}] | "
            f"Composition: {comp_id} → {Path(output_path).name}"
        )
        
        # Validation
        if progress_callback:
            progress_callback(RenderProgress(stage="Validating props"))
        
        try:
            self._validate_props(props)
        except ValueError as e:
            return RenderResult(
                success=False,
                output_path=output_path,
                quality=quality,
                error=f"Validation: {e}",
                elapsed_seconds=time.time() - start_time,
            )
        
        # نسخ/ربط الأصول
        if progress_callback:
            progress_callback(RenderProgress(stage="Preparing assets"))
        
        assets_linked = 0
        assets_copied = 0
        
        try:
            assets_linked, assets_copied = self._prepare_assets(props)
        except Exception as e:
            return RenderResult(
                success=False,
                output_path=output_path,
                quality=quality,
                error=f"Asset preparation: {e}",
                elapsed_seconds=time.time() - start_time,
            )
        
        # كتابة props
        try:
            props_file = self._write_props(props)
        except Exception as e:
            return RenderResult(
                success=False,
                output_path=output_path,
                quality=quality,
                error=f"Failed to write props: {e}",
                elapsed_seconds=time.time() - start_time,
                assets_linked=assets_linked,
                assets_copied=assets_copied,
            )
        
        # Render مع retry
        render_success = False
        last_error = None
        retries = 0
        
        for attempt in range(1, max_retries + 1):
            if attempt > 1:
                logger.warning(f"⚠ Retry {attempt}/{max_retries}")
                time.sleep(RendererConstants.RETRY_DELAY)
                retries += 1
            
            if progress_callback:
                progress_callback(RenderProgress(
                    stage=f"Rendering (attempt {attempt})"
                ))
            
            try:
                self._run_remotion(
                    comp_id,
                    output_path,
                    props_file,
                    quality_cfg,
                    timeout,
                    progress_callback,
                )
                render_success = True
                break
                
            except Exception as e:
                last_error = e
                logger.error(f"❌ Render failed: {e}")
        
        # ✅ FIXED: بناء النتيجة مع success صريحاً
        if not render_success:
            return RenderResult(
                success=False,
                output_path=output_path,
                quality=quality,
                error=f"Render failed: {last_error}",
                elapsed_seconds=time.time() - start_time,
                assets_linked=assets_linked,
                assets_copied=assets_copied,
                retries=retries,
            )
        
        # Validation للـ output
        if not Path(output_path).exists():
            return RenderResult(
                success=False,
                output_path=output_path,
                quality=quality,
                error="Output file not created",
                elapsed_seconds=time.time() - start_time,
                assets_linked=assets_linked,
                assets_copied=assets_copied,
                retries=retries,
            )
        
        # إضافة metadata
        if metadata:
            if progress_callback:
                progress_callback(RenderProgress(stage="Adding metadata"))
            self._add_metadata(output_path, metadata)
        
        # معلومات الفيديو
        file_size_mb = 0.0
        duration = 0.0
        width = 0
        height = 0
        frames_rendered = 0
        
        try:
            file_size_mb = Path(output_path).stat().st_size / (1024 * 1024)
            duration = self.utils.get_duration(output_path)
            width, height = self.utils.get_dimensions(output_path)
            frames_rendered = int(duration * self.fps)
        except Exception as e:
            logger.warning(f"⚠ Failed to read output info: {e}")
        
        # Cleanup
        if self.cleanup_on_success:
            if progress_callback:
                progress_callback(RenderProgress(stage="Cleaning up"))
            self._cleanup_public_assets()
        
        if not self.keep_props_file:
            try:
                Path(props_file).unlink(missing_ok=True)
            except Exception:
                pass
        
        if progress_callback:
            progress_callback(RenderProgress(stage="Done!", percent=100))
        
        # ✅ FIXED: بناء النتيجة الناجحة مع success صريحاً
        result = RenderResult(
            success=True,
            output_path=output_path,
            file_size_mb=file_size_mb,
            duration=duration,
            width=width,
            height=height,
            quality=quality,
            elapsed_seconds=time.time() - start_time,
            frames_rendered=frames_rendered,
            assets_linked=assets_linked,
            assets_copied=assets_copied,
            retries=retries,
        )
        
        logger.info(result.summary())
        return result
    
    # ═══════════════════════════════════════════════════════════════
    # Backward Compatibility
    # ═══════════════════════════════════════════════════════════════
    def render_final(
        self,
        props: dict,
        output_path: str,
        quality: str = "high",
        composition_id: Optional[str] = None,
        metadata: Optional[dict] = None,
        preset: Optional[str] = None,
    ) -> str:
        """متوافق مع v1."""
        # Legacy preset support
        if preset and quality == "high":
            quality = RenderQuality.from_legacy_preset(preset).value
        
        result = self.render(
            props=props,
            output_path=output_path,
            quality=quality,
            composition_id=composition_id,
            metadata=metadata,
        )
        
        if not result.success:
            raise RuntimeError(result.error)
        
        return result.output_path
    
    # ═══════════════════════════════════════════════════════════════
    # Validation
    # ═══════════════════════════════════════════════════════════════
    def _validate_props(self, props: dict) -> None:
        """فحص props."""
        logger.info("🔍 Validating props...")
        
        # Required fields
        required = ["scenes", "totalDuration", "fps", "width", "height"]
        missing = [f for f in required if f not in props]
        if missing:
            raise ValueError(f"Missing fields: {missing}")
        
        scenes = props.get("scenes", [])
        if not scenes:
            raise ValueError("No scenes provided!")
        
        logger.info(f"   ✓ {len(scenes)} scenes")
        
        # فحص scenes
        for i, scene in enumerate(scenes):
            bg_path = scene.get("backgroundPath", "")
            if bg_path and not Path(bg_path).exists():
                logger.warning(f"   ⚠ Scene {i} video missing: {bg_path}")
        
        # فحص audio
        audio_path = props.get("audioPath", "")
        if audio_path and Path(audio_path).exists():
            size_kb = Path(audio_path).stat().st_size / 1024
            logger.info(f"   ✓ Audio: {size_kb:.1f} KB")
        elif audio_path:
            logger.warning(f"   ⚠ Audio missing: {audio_path}")
        
        # Subtitles
        subtitles = props.get("subtitles", [])
        if subtitles:
            logger.info(f"   ✓ Subtitles: {len(subtitles)}")
        
        logger.info(f"   ✓ Duration: {props.get('totalDuration')}s")
        logger.info("✅ Validation passed")
    
    # ═══════════════════════════════════════════════════════════════
    # Asset Preparation (Symlinks!)
    # ═══════════════════════════════════════════════════════════════
    def _prepare_assets(self, props: dict) -> tuple[int, int]:
        """
        تحضير الأصول (symlink أو copy).
        
        Returns:
            (linked_count, copied_count)
        """
        logger.info(
            f"📦 Preparing assets ({'symlink' if self.use_symlinks else 'copy'})..."
        )
        
        public_dir = self.remotion_dir / "public"
        public_dir.mkdir(exist_ok=True)
        
        public_footage = public_dir / RendererConstants.PUBLIC_FOOTAGE_DIR
        public_audio = public_dir / RendererConstants.PUBLIC_AUDIO_DIR
        public_footage.mkdir(exist_ok=True)
        public_audio.mkdir(exist_ok=True)
        
        linked_count = 0
        copied_count = 0
        
        # Audio
        audio_path = props.get("audioPath", "")
        if audio_path and Path(audio_path).exists():
            audio_src = Path(audio_path)
            audio_dest = public_audio / audio_src.name
            
            if self.use_symlinks:
                success, method = try_symlink_or_copy(audio_src, audio_dest)
                if success:
                    if method == "symlink":
                        linked_count += 1
                    else:
                        copied_count += 1
            else:
                shutil.copy2(audio_src, audio_dest)
                copied_count += 1
            
            # Update path
            props["audioPath"] = f"audio/{audio_src.name}"
            logger.info(f"   ✓ Audio: {audio_src.name}")
        
        # Videos
        for scene in props.get("scenes", []):
            bg_path = scene.get("backgroundPath", "")
            if not bg_path or not Path(bg_path).exists():
                continue
            
            video_src = Path(bg_path)
            video_dest = public_footage / video_src.name
            
            if self.use_symlinks:
                success, method = try_symlink_or_copy(video_src, video_dest)
                if success:
                    if method == "symlink":
                        linked_count += 1
                    else:
                        copied_count += 1
            else:
                shutil.copy2(video_src, video_dest)
                copied_count += 1
            
            # Update path
            scene["backgroundPath"] = f"footage/{video_src.name}"
        
        logger.info(
            f"   ✓ Assets: {linked_count} linked, {copied_count} copied"
        )
        
        return linked_count, copied_count
    
    def _cleanup_public_assets(self) -> None:
        """تنظيف public assets."""
        try:
            public_dir = self.remotion_dir / "public"
            for subdir in [
                RendererConstants.PUBLIC_FOOTAGE_DIR,
                RendererConstants.PUBLIC_AUDIO_DIR,
            ]:
                target = public_dir / subdir
                if target.exists():
                    # حذف المحتويات (مع symlinks)
                    for item in target.iterdir():
                        if item.is_symlink() or item.is_file():
                            item.unlink(missing_ok=True)
                        else:
                            shutil.rmtree(item, ignore_errors=True)
            logger.info("🧹 Cleaned public assets")
        except Exception as e:
            logger.warning(f"⚠ Cleanup failed: {e}")
    
    # ═══════════════════════════════════════════════════════════════
    # Props File
    # ═══════════════════════════════════════════════════════════════
    def _write_props(self, props: dict) -> str:
        """كتابة props."""
        props_file = self.temp_dir / "remotion_props.json"
        with open(props_file, "w", encoding="utf-8") as f:
            json.dump(props, f, ensure_ascii=False, indent=2)
        
        size_kb = props_file.stat().st_size / 1024
        logger.info(f"📝 Props: {props_file.name} ({size_kb:.1f} KB)")
        return str(props_file.resolve())
    
    # ═══════════════════════════════════════════════════════════════
    # Remotion Execution (مع Progress)
    # ═══════════════════════════════════════════════════════════════
    def _run_remotion(
        self,
        composition_id: str,
        output_path: str,
        props_file: str,
        quality_cfg: QualityConfig,
        timeout: int,
        progress_callback: Optional[Callable[[RenderProgress], None]] = None,
    ) -> None:
        """تشغيل Remotion مع progress."""
        cmd = [
            "npx", "remotion", "render",
            "src/index.ts",
            composition_id,
            output_path,
            "--props", props_file,
            *quality_cfg.to_cli_args(),
            "--log", "verbose",
            "--timeout", str(RendererConstants.FRAME_TIMEOUT_MS),
        ]
        
        logger.info("=" * 60)
        logger.info("🎬 Running Remotion...")
        logger.info("=" * 60)
        
        start_time = time.time()
        process = None
        
        try:
            # استخدام Popen لقراءة output في real-time
            process = subprocess.Popen(
                cmd,
                cwd=str(self.remotion_dir),
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                bufsize=1,
            )
            
            total_frames = 0
            
            # قراءة output
            if process.stdout:
                for line in process.stdout:
                    line = line.strip()
                    if not line:
                        continue
                    
                    # تحليل progress
                    progress_data = parse_remotion_progress(line)
                    if progress_data and progress_callback:
                        current, total = progress_data
                        total_frames = total
                        elapsed = time.time() - start_time
                        percent = (current / total * 100) if total > 0 else 0
                        
                        # تقدير الوقت المتبقي
                        if current > 0:
                            time_per_frame = elapsed / current
                            remaining = (total - current) * time_per_frame
                        else:
                            remaining = 0
                        
                        progress_callback(RenderProgress(
                            stage="Rendering",
                            current_frame=current,
                            total_frames=total,
                            percent=percent,
                            elapsed=elapsed,
                            estimated_remaining=remaining,
                        ))
                    
                    # log مهم
                    if "error" in line.lower() or "warn" in line.lower():
                        logger.warning(f"   {line}")
                    elif progress_data:
                        # progress فقط للسطور المهمة
                        pass
                    else:
                        logger.debug(f"   {line}")
            
            # انتظار النهاية
            process.wait(timeout=timeout)
            
            if process.returncode != 0:
                raise RuntimeError(
                    f"Remotion failed (exit code: {process.returncode})"
                )
            
            elapsed = time.time() - start_time
            logger.info(
                f"✅ Render complete in {elapsed:.1f}s "
                f"({total_frames} frames)"
            )
            
        except subprocess.TimeoutExpired:
            if process:
                process.kill()
            raise RuntimeError(f"Render timeout ({timeout}s)")
    
    # ═══════════════════════════════════════════════════════════════
    # Metadata
    # ═══════════════════════════════════════════════════════════════
    def _add_metadata(self, video_path: str, metadata: dict) -> None:
        """إضافة metadata."""
        if not metadata or not check_ffmpeg_available():
            return
        
        temp_output = video_path.replace(".mp4", "_meta.mp4")
        
        metadata_args = self._build_metadata_args(metadata)
        if not metadata_args:
            return
        
        result = run_ffmpeg(
            ["-i", video_path, "-c", "copy"] + metadata_args,
            temp_output,
            description="Adding metadata",
            audio_config=False,
        )
        
        if result.success:
            shutil.move(temp_output, video_path)
            logger.info("✓ Metadata added")
        else:
            Path(temp_output).unlink(missing_ok=True)
            logger.warning(f"⚠ Metadata failed: {result.error}")
    
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
                # تنظيف
                value = str(value).replace('"', "'")[:200]
                args.extend(["-metadata", f"{ffmpeg_key}={value}"])
        
        return args
    
    # ═══════════════════════════════════════════════════════════════
    # Platform Validation
    # ═══════════════════════════════════════════════════════════════
    def validate_for_platform(
        self,
        video_path: str,
        platform: str = "youtube_shorts",
    ) -> dict:
        """التحقق من توافق الفيديو للمنصة."""
        if not Path(video_path).exists():
            return {"valid": False, "error": "File not found"}
        
        limits = PLATFORM_LIMITS.get(platform)
        if not limits:
            return {
                "valid": False,
                "error": f"Unknown platform: {platform}",
            }
        
        size_mb = Path(video_path).stat().st_size / (1024 * 1024)
        duration = self.utils.get_duration(video_path)
        
        issues = []
        
        if size_mb > limits["max_size_mb"]:
            issues.append(
                f"File too large: {size_mb:.1f}MB > {limits['max_size_mb']}MB"
            )
        
        if duration > limits["max_duration"]:
            issues.append(
                f"Too long: {duration:.1f}s > {limits['max_duration']}s"
            )
        
        return {
            "valid": len(issues) == 0,
            "platform": platform,
            "file_size_mb": round(size_mb, 1),
            "duration": round(duration, 1),
            "limits": limits,
            "issues": issues,
        }
    
    # ═══════════════════════════════════════════════════════════════
    # Utility (delegated)
    # ═══════════════════════════════════════════════════════════════
    def create_thumbnail(self, video, output, timestamp=1.5, resize=True):
        return self.utils.create_thumbnail(video, output, timestamp, resize)
    
    def create_multiple_thumbnails(self, video, output_dir, count=3):
        return self.utils.create_multiple_thumbnails(video, output_dir, count)
    
    def get_duration(self, path):
        return self.utils.get_duration(path)
    
    def get_dimensions(self, path):
        return self.utils.get_dimensions(path)
    
    def get_video_info(self, path):
        return self.utils.get_video_info(path)
    
    # ═══════════════════════════════════════════════════════════════
    # Cleanup
    # ═══════════════════════════════════════════════════════════════
    def cleanup_temp(self, keep_props: bool = False) -> int:
        """تنظيف temp files."""
        if not self.temp_dir.exists():
            return 0
        
        count = 0
        try:
            for item in self.temp_dir.iterdir():
                if keep_props and item.name == "remotion_props.json":
                    continue
                
                if item.is_file():
                    item.unlink()
                    count += 1
                elif item.is_dir():
                    shutil.rmtree(item, ignore_errors=True)
                    count += 1
            
            logger.info(f"🧹 Cleaned {count} items from temp")
        except Exception as e:
            logger.warning(f"⚠ Cleanup failed: {e}")
        
        return count
    
    def cleanup_specific(self, patterns: list[str]) -> int:
        """تنظيف patterns محددة."""
        count = 0
        try:
            for pattern in patterns:
                for f in self.temp_dir.rglob(pattern):
                    if f.is_file():
                        f.unlink(missing_ok=True)
                        count += 1
        except Exception:
            pass
        return count
    
    @staticmethod
    def list_qualities() -> list[str]:
        """قائمة الجودات."""
        return list(QUALITY_CONFIGS.keys())
    
    @staticmethod
    def list_platforms() -> list[str]:
        """قائمة المنصات."""
        return list(PLATFORM_LIMITS.keys())


# ═══════════════════════════════════════════════════════════════════
# اختبار
# ═══════════════════════════════════════════════════════════════════
if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s | %(levelname)s | %(message)s"
    )
    
    print("=" * 60)
    print("🎬 Remotion Renderer v2.1")
    print("=" * 60)
    
    try:
        renderer = RemotionRenderer(use_symlinks=True)
        
        print(f"\n📋 Settings:")
        print(f"   • Resolution: {renderer.w}x{renderer.h}")
        print(f"   • FPS: {renderer.fps}")
        print(f"   • Composition: {renderer.composition_id}")
        print(f"   • Use symlinks: {renderer.use_symlinks}")
        
        print(f"\n📦 Available qualities: {renderer.list_qualities()}")
        print(f"📱 Available platforms: {renderer.list_platforms()}")
        
        print("\n✅ Ready!")
        
    except RuntimeError as e:
        print(f"\n❌ {e}")
