"""
🎞️ Render Module v2.0 — التصدير النهائي
═══════════════════════════════════════════════════════════════
محركات التصدير:
  • RemotionRenderer → ⭐ الأساسي (دعم العربية الكامل)
  • FFmpegBuilder    → احتياطي (concat, merge, render)
  • VideoUtils       → أدوات (thumbnails, info, validation)

الاستخدام:
    from engine.render import quick_render
    
    result = quick_render(
        props=props,
        output_path="output.mp4",
        quality="high",
    )

أو:
    from engine.render import RenderOrchestrator
    
    orch = RenderOrchestrator(prefer="remotion")
    result = orch.render(props, "output.mp4")

التحسينات v2.0:
  ✓ Lazy loading
  ✓ Dataclasses في exports
  ✓ RenderOrchestrator
  ✓ Quick render
  ✓ Diagnostic tools
═══════════════════════════════════════════════════════════════
"""

from __future__ import annotations

import os
import logging
from enum import Enum
from typing import Optional, Literal, TYPE_CHECKING, Any, Union

logger = logging.getLogger(__name__)


# ═══════════════════════════════════════════════════════════════════
# Version
# ═══════════════════════════════════════════════════════════════════
__version__ = "2.0.0"


# ═══════════════════════════════════════════════════════════════════
# Types
# ═══════════════════════════════════════════════════════════════════
RendererType = Literal["auto", "remotion", "ffmpeg"]
QualityType = Literal["draft", "medium", "high", "ultra"]


# ═══════════════════════════════════════════════════════════════════
# Eager Imports (الأساسيات)
# ═══════════════════════════════════════════════════════════════════
from engine.render.video_utils import (
    VideoUtils,
    VideoInfo,
    ValidationResult,
    ThumbnailResult,
    PlatformSpec,
    Platform,
    PLATFORM_SPECS,
)


# ═══════════════════════════════════════════════════════════════════
# Lazy Imports (المحركات)
# ═══════════════════════════════════════════════════════════════════
if TYPE_CHECKING:
    from engine.render.remotion_renderer import (
        RemotionRenderer, RenderResult as RemotionRenderResult,
        RenderProgress, RenderQuality, QualityConfig,
    )
    from engine.render.ffmpeg_builder import (
        FFmpegBuilder, RenderResult as FFmpegRenderResult,
        QualityPreset,
    )


def _lazy_import_remotion():
    """استيراد RemotionRenderer عند الحاجة."""
    try:
        from engine.render.remotion_renderer import (
            RemotionRenderer, RenderResult, RenderProgress,
            RenderQuality, QualityConfig, PLATFORM_LIMITS,
        )
        return {
            "RemotionRenderer": RemotionRenderer,
            "RenderResult": RenderResult,
            "RenderProgress": RenderProgress,
            "RenderQuality": RenderQuality,
            "QualityConfig": QualityConfig,
            "PLATFORM_LIMITS": PLATFORM_LIMITS,
        }, True
    except ImportError as e:
        logger.debug(f"RemotionRenderer not available: {e}")
        return None, False


def _lazy_import_ffmpeg():
    """استيراد FFmpegBuilder عند الحاجة."""
    try:
        from engine.render.ffmpeg_builder import (
            FFmpegBuilder, RenderResult, QualityPreset,
            QUALITY_PRESETS, LEGACY_PRESETS,
        )
        return {
            "FFmpegBuilder": FFmpegBuilder,
            "FFmpegRenderResult": RenderResult,
            "QualityPreset": QualityPreset,
            "QUALITY_PRESETS": QUALITY_PRESETS,
            "LEGACY_PRESETS": LEGACY_PRESETS,
        }, True
    except ImportError as e:
        logger.debug(f"FFmpegBuilder not available: {e}")
        return None, False


# ═══════════════════════════════════════════════════════════════════
# Availability Check
# ═══════════════════════════════════════════════════════════════════
def is_remotion_available() -> bool:
    """فحص توفر Remotion."""
    _, available = _lazy_import_remotion()
    return available


def is_ffmpeg_available() -> bool:
    """فحص توفر FFmpeg."""
    _, available = _lazy_import_ffmpeg()
    return available


# ═══════════════════════════════════════════════════════════════════
# Platform Quality Recommendations
# ═══════════════════════════════════════════════════════════════════
PLATFORM_QUALITY_MAP: dict[str, str] = {
    "youtube":         "high",
    "youtube_shorts":  "high",
    "shorts":          "high",
    "tiktok":          "high",
    "instagram":       "high",
    "instagram_reel":  "high",
    "instagram_story": "medium",
    "reels":           "high",
    "twitter":         "medium",
    "facebook":        "high",
    "linkedin":        "high",
    "preview":         "draft",
    "test":            "draft",
}


# ═══════════════════════════════════════════════════════════════════
# Render Orchestrator
# ═══════════════════════════════════════════════════════════════════
class RenderOrchestrator:
    """منسّق ذكي للتصدير."""
    
    def __init__(
        self,
        prefer: RendererType = "auto",
        cache_enabled: bool = True,
    ):
        """
        Args:
            prefer: المحرك المفضل (auto/remotion/ffmpeg)
            cache_enabled: تفعيل caching
        """
        self.prefer = prefer
        self.cache_enabled = cache_enabled
        
        # تحديد المحرك
        self._renderer = None
        self._renderer_type = self._select_renderer()
        
        logger.info(
            f"🎞️ RenderOrchestrator v2.0 | "
            f"Type: {self._renderer_type}"
        )
    
    def _select_renderer(self) -> str:
        """اختيار المحرك."""
        # تحقق من preference
        if self.prefer == "remotion":
            if not is_remotion_available():
                raise RuntimeError("❌ Remotion غير متاح")
            return "remotion"
        
        if self.prefer == "ffmpeg":
            if not is_ffmpeg_available():
                raise RuntimeError("❌ FFmpeg غير متاح")
            return "ffmpeg"
        
        # auto: تحقق من env
        use_remotion = os.getenv("USE_REMOTION", "true").lower() in (
            "true", "1", "yes"
        )
        
        if use_remotion and is_remotion_available():
            return "remotion"
        
        if is_ffmpeg_available():
            logger.warning(
                "⚠ Remotion not available, falling back to FFmpeg"
            )
            return "ffmpeg"
        
        raise RuntimeError(
            "❌ لا يوجد محرك تصدير متاح!\n"
            "   تأكد من تثبيت Remotion أو FFmpeg"
        )
    
    @property
    def renderer(self):
        """جلب المحرك (lazy)."""
        if self._renderer is None:
            if self._renderer_type == "remotion":
                classes, _ = _lazy_import_remotion()
                self._renderer = classes["RemotionRenderer"]()
            else:
                classes, _ = _lazy_import_ffmpeg()
                self._renderer = classes["FFmpegBuilder"]()
        
        return self._renderer
    
    @property
    def renderer_type(self) -> str:
        """نوع المحرك."""
        return self._renderer_type
    
    def render(
        self,
        output_path: str,
        props: Optional[dict] = None,
        input_video: Optional[str] = None,
        quality: str = "high",
        **kwargs,
    ):
        """
        🎯 التصدير الموحّد.
        
        Args:
            output_path: مسار الإخراج
            props: للـ Remotion
            input_video: للـ FFmpeg
            quality: الجودة
            **kwargs: إضافي للمحرك
        """
        if self._renderer_type == "remotion":
            if not props:
                raise ValueError("Remotion يحتاج props")
            return self.renderer.render(
                props=props,
                output_path=output_path,
                quality=quality,
                **kwargs,
            )
        else:
            if not input_video:
                raise ValueError("FFmpeg يحتاج input_video")
            return self.renderer.render(
                input_video=input_video,
                output_path=output_path,
                quality=quality,
                **kwargs,
            )


# ═══════════════════════════════════════════════════════════════════
# Convenience Functions
# ═══════════════════════════════════════════════════════════════════
def quick_render(
    output_path: str,
    props: Optional[dict] = None,
    input_video: Optional[str] = None,
    quality: str = "high",
    prefer: RendererType = "auto",
    **kwargs,
):
    """
    🚀 تصدير سريع.
    
    Examples:
        # Remotion
        result = quick_render(
            props=props,
            output_path="out.mp4",
            quality="high",
        )
        
        # FFmpeg
        result = quick_render(
            input_video="input.mp4",
            output_path="out.mp4",
            quality="high",
            prefer="ffmpeg",
        )
    """
    orchestrator = RenderOrchestrator(prefer=prefer)
    return orchestrator.render(
        output_path=output_path,
        props=props,
        input_video=input_video,
        quality=quality,
        **kwargs,
    )


def get_default_renderer():
    """متوافق مع v1 - يُرجع instance."""
    orchestrator = RenderOrchestrator(prefer="auto")
    return orchestrator.renderer


# ═══════════════════════════════════════════════════════════════════
# Quality Helpers
# ═══════════════════════════════════════════════════════════════════
def get_default_quality() -> str:
    """الجودة الافتراضية."""
    return os.getenv("VIDEO_QUALITY", "high")


def list_available_qualities() -> list[str]:
    """قائمة الجودات."""
    return ["draft", "medium", "high", "ultra"]


def get_recommended_quality_for_platform(platform: str) -> str:
    """جودة موصى بها لـ platform."""
    return PLATFORM_QUALITY_MAP.get(platform.lower(), "high")


def list_supported_platforms() -> list[str]:
    """قائمة المنصات المدعومة."""
    return list(PLATFORM_SPECS.keys())


# ═══════════════════════════════════════════════════════════════════
# Info & Diagnostic
# ═══════════════════════════════════════════════════════════════════
def get_info() -> dict:
    """معلومات الموديول."""
    return {
        "version": __version__,
        "renderers": {
            "remotion": {
                "available": is_remotion_available(),
                "description": "Modern (Arabic-friendly)",
            },
            "ffmpeg": {
                "available": is_ffmpeg_available(),
                "description": "Classic (legacy)",
            },
            "utils": {
                "available": True,
                "description": "Helpers (thumbnails, info)",
            },
        },
        "default_quality": get_default_quality(),
        "available_qualities": list_available_qualities(),
        "supported_platforms": list_supported_platforms(),
        "use_remotion_env": os.getenv("USE_REMOTION", "true"),
    }


def get_renderer_info() -> dict:
    """متوافق مع v1."""
    return {
        "remotion_available": is_remotion_available(),
        "ffmpeg_available": is_ffmpeg_available(),
        "utils_available": True,
        "default_renderer": (
            "Remotion" if is_remotion_available() else "FFmpeg"
        ),
        "use_remotion_env": os.getenv("USE_REMOTION", "true"),
    }


def print_status() -> None:
    """طباعة حالة شاملة."""
    info = get_info()
    
    print("=" * 60)
    print(f"🎞️ Render Module v{info['version']}")
    print("=" * 60)
    
    print(f"\n📦 Renderers:")
    for name, details in info["renderers"].items():
        status = "✅" if details["available"] else "❌"
        print(f"   {status} {name:10s} - {details['description']}")
    
    print(f"\n⚙️ Defaults:")
    print(f"   • Quality: {info['default_quality']}")
    print(f"   • USE_REMOTION: {info['use_remotion_env']}")
    
    print(f"\n📊 Qualities: {info['available_qualities']}")
    print(f"\n📱 Platforms: {len(info['supported_platforms'])}")
    for p in info["supported_platforms"]:
        recommended = PLATFORM_QUALITY_MAP.get(p, "high")
        print(f"   • {p:20s} → {recommended}")
    
    print("=" * 60)


# ═══════════════════════════════════════════════════════════════════
# Lazy Loading via __getattr__
# ═══════════════════════════════════════════════════════════════════
def __getattr__(name: str):
    """Lazy import للـ classes."""
    
    # Remotion
    if name == "RemotionRenderer":
        classes, ok = _lazy_import_remotion()
        if not ok:
            raise ImportError(
                "RemotionRenderer غير متاح.\n"
                "تأكد من تثبيت Node.js و Remotion."
            )
        return classes["RemotionRenderer"]
    
    if name in ("RenderProgress", "RenderQuality", "QualityConfig"):
        classes, ok = _lazy_import_remotion()
        if ok and name in classes:
            return classes[name]
    
    # FFmpeg
    if name == "FFmpegBuilder":
        classes, ok = _lazy_import_ffmpeg()
        if not ok:
            raise ImportError(
                "FFmpegBuilder غير متاح.\n"
                "تأكد من تثبيت FFmpeg."
            )
        return classes["FFmpegBuilder"]
    
    if name in ("QualityPreset",):
        classes, ok = _lazy_import_ffmpeg()
        if ok and name in classes:
            return classes[name]
    
    # Compatibility
    if name == "REMOTION_AVAILABLE":
        return is_remotion_available()
    if name == "FFMPEG_AVAILABLE":
        return is_ffmpeg_available()
    if name == "UTILS_AVAILABLE":
        return True
    
    raise AttributeError(
        f"module 'engine.render' has no attribute '{name}'"
    )


# ═══════════════════════════════════════════════════════════════════
# Public API
# ═══════════════════════════════════════════════════════════════════
__all__ = [
    # Version
    "__version__",
    
    # Core (eager)
    "VideoUtils",
    "VideoInfo",
    "ValidationResult",
    "ThumbnailResult",
    "PlatformSpec",
    "Platform",
    "PLATFORM_SPECS",
    
    # Lazy classes
    "RemotionRenderer",
    "FFmpegBuilder",
    "RenderProgress",
    "RenderQuality",
    "QualityConfig",
    "QualityPreset",
    
    # Orchestrator
    "RenderOrchestrator",
    
    # Functions
    "quick_render",
    "get_default_renderer",
    "is_remotion_available",
    "is_ffmpeg_available",
    "get_default_quality",
    "list_available_qualities",
    "get_recommended_quality_for_platform",
    "list_supported_platforms",
    "get_info",
    "get_renderer_info",
    "print_status",
    
    # Compatibility
    "REMOTION_AVAILABLE",
    "FFMPEG_AVAILABLE",
    "UTILS_AVAILABLE",
    
    # Types
    "RendererType",
    "QualityType",
]


# ═══════════════════════════════════════════════════════════════════
# اختبار
# ═══════════════════════════════════════════════════════════════════
if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s | %(levelname)s | %(message)s"
    )
    
    print_status()
    
    print("\n🧪 Testing imports...")
    
    try:
        # VideoUtils (eager)
        print(f"   ✅ VideoUtils: {VideoUtils.__name__}")
        
        # Remotion (lazy)
        if is_remotion_available():
            from engine.render import RemotionRenderer
            print(f"   ✅ RemotionRenderer (lazy)")
        
        # FFmpeg (lazy)
        if is_ffmpeg_available():
            from engine.render import FFmpegBuilder
            print(f"   ✅ FFmpegBuilder (lazy)")
        
        # Orchestrator
        print(f"\n🎯 Testing orchestrator...")
        try:
            orch = RenderOrchestrator(prefer="auto")
            print(f"   ✅ Type: {orch.renderer_type}")
        except RuntimeError as e:
            print(f"   ⚠ {e}")
        
        print("\n✅ All imports work!")
        
    except Exception as e:
        print(f"\n❌ Error: {e}")
