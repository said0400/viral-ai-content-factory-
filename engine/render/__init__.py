"""
🎞️ Render Module — التصدير النهائي للفيديو
═══════════════════════════════════════════════════════════════
يوفر محركات التصدير النهائي:
  • RemotionRenderer → ⭐ المحرك الجديد (دعم كامل للعربية)
  • FFmpegBuilder    → المحرك القديم (Legacy - للتوافق الرجعي)
  • VideoUtils       → أدوات مساعدة (Thumbnails, Info, Validation)

الميزات:
  ✓ تصدير MP4 احترافي مع دعم كامل للعربية (RTL + Arabic Shaping)
  ✓ إعدادات جودة متعددة (medium/high/ultra)
  ✓ توليد Thumbnails تلقائي
  ✓ إضافة Metadata
  ✓ التحقق من توافق المنصات
  ✓ تنظيف الملفات المؤقتة

الاستخدام (الجديد):
    from engine.render import RemotionRenderer
    
    renderer = RemotionRenderer()
    renderer.render_final(
        props={
            "title": "...",
            "subtitles": [...],
            "audioPath": "...",
            ...
        },
        output_path="output/short.mp4",
        quality="high",
    )

الاستخدام (الأدوات المساعدة):
    from engine.render import VideoUtils
    
    utils = VideoUtils()
    utils.create_thumbnail("video.mp4", "thumb.jpg")
    info = utils.get_video_info("video.mp4")

الاستخدام (Legacy - للتوافق الرجعي):
    from engine.render import FFmpegBuilder  # سيُحذف لاحقاً
═══════════════════════════════════════════════════════════════
"""

import os
import logging

logger = logging.getLogger(__name__)

# ─── الاستيرادات الأساسية ────────────────────────────────────────────────

# 🆕 المحرك الجديد (Remotion)
try:
    from engine.render.remotion_renderer import RemotionRenderer
    REMOTION_AVAILABLE = True
except ImportError as e:
    logger.warning(f"⚠ RemotionRenderer غير متاح: {e}")
    RemotionRenderer = None
    REMOTION_AVAILABLE = False

# 🛠️ الأدوات المساعدة
try:
    from engine.render.video_utils import VideoUtils
    UTILS_AVAILABLE = True
except ImportError as e:
    logger.warning(f"⚠ VideoUtils غير متاح: {e}")
    VideoUtils = None
    UTILS_AVAILABLE = False

# 🔁 المحرك القديم (Legacy - سيُحذف لاحقاً)
try:
    from engine.render.ffmpeg_builder import FFmpegBuilder
    FFMPEG_AVAILABLE = True
except ImportError as e:
    logger.debug(f"FFmpegBuilder غير متاح: {e}")
    FFmpegBuilder = None
    FFMPEG_AVAILABLE = False


# ════════════════════════════════════════════════════════════════════════
#                    دوال مساعدة
# ════════════════════════════════════════════════════════════════════════
def get_default_renderer():
    """
    إرجاع المحرك الافتراضي.

    يُفضّل Remotion إذا كان متاحاً، وإلا FFmpeg (legacy).

    Returns:
        RemotionRenderer أو FFmpegBuilder
    """
    use_remotion = os.getenv("USE_REMOTION", "true").lower() in ("true", "1", "yes")

    if use_remotion and REMOTION_AVAILABLE:
        logger.info("🎬 استخدام Remotion Renderer")
        return RemotionRenderer()
    elif FFMPEG_AVAILABLE:
        logger.warning("⚠ Remotion غير متاح، استخدام FFmpeg Builder (Legacy)")
        return FFmpegBuilder()
    else:
        raise RuntimeError(
            "❌ لا يوجد محرك تصدير متاح!\n"
            "   تأكد من تثبيت Remotion أو FFmpeg"
        )


def get_default_quality() -> str:
    """جودة التصدير الافتراضية."""
    return os.getenv("VIDEO_QUALITY", "high")


def list_available_qualities() -> list:
    """قائمة الجودات المتاحة."""
    return ["medium", "high", "ultra"]


def get_recommended_quality_for_platform(platform: str) -> str:
    """
    الحصول على أفضل جودة لمنصة معينة.

    Args:
        platform: youtube / tiktok / instagram / shorts
    """
    recommendations = {
        "youtube":   "high",
        "shorts":    "high",
        "tiktok":    "high",
        "instagram": "high",
        "reels":     "high",
        "twitter":   "medium",
        "preview":   "medium",
    }
    return recommendations.get(platform.lower(), "high")


def get_renderer_info() -> dict:
    """معلومات عن المحركات المتاحة."""
    return {
        "remotion_available": REMOTION_AVAILABLE,
        "ffmpeg_available":   FFMPEG_AVAILABLE,
        "utils_available":    UTILS_AVAILABLE,
        "default_renderer":   "Remotion" if REMOTION_AVAILABLE else "FFmpeg",
        "use_remotion_env":   os.getenv("USE_REMOTION", "true"),
    }


# ════════════════════════════════════════════════════════════════════════
#                    Exports
# ════════════════════════════════════════════════════════════════════════
__all__ = [
    # المحركات
    "RemotionRenderer",
    "FFmpegBuilder",      # legacy
    "VideoUtils",
    
    # الدوال المساعدة
    "get_default_renderer",
    "get_default_quality",
    "list_available_qualities",
    "get_recommended_quality_for_platform",
    "get_renderer_info",
    
    # متغيرات الحالة
    "REMOTION_AVAILABLE",
    "FFMPEG_AVAILABLE",
    "UTILS_AVAILABLE",
]
