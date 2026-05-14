"""
🎞️ Render Module — التصدير النهائي للفيديو
═══════════════════════════════════════════════════════════════
يوفر محركات التصدير النهائي:
  • FFmpegBuilder → التصدير النهائي إلى MP4 (H.264 + AAC)

الميزات:
  ✓ تصدير MP4 متوافق مع YouTube / TikTok / Instagram
  ✓ إعدادات جودة متعددة (medium/high/ultra)
  ✓ توليد Thumbnails تلقائي
  ✓ إضافة Metadata
  ✓ تنظيف الملفات المؤقتة

الاستخدام:
    from engine.render import FFmpegBuilder
    
    renderer = FFmpegBuilder()
    renderer.render_final(
        input_video="assembled.mp4",
        output_path="output/short.mp4",
        quality="high",
    )
═══════════════════════════════════════════════════════════════
"""

import os
import logging

logger = logging.getLogger(__name__)

# ─── الاستيرادات الأساسية ────────────────────────────────────────────────
from engine.render.ffmpeg_builder import FFmpegBuilder


# ════════════════════════════════════════════════════════════════════════
#                    دوال مساعدة
# ════════════════════════════════════════════════════════════════════════
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


# ════════════════════════════════════════════════════════════════════════
#                    Exports
# ════════════════════════════════════════════════════════════════════════
__all__ = [
    "FFmpegBuilder",
    "get_default_quality",
    "list_available_qualities",
    "get_recommended_quality_for_platform",
]
