"""
🎬 Video Module — تحرير الفيديو السينمائي
═══════════════════════════════════════════════════════════════
يوفر محركات متكاملة لإنتاج فيديوهات Shorts احترافية:

  • CinematicEditor   → التحرير السينمائي وتجميع المشاهد
  • EffectsEngine     → التأثيرات البصرية (Zoom, Shake, Glitch...)
  • TransitionEngine  → الانتقالات بين المشاهد
  • SubtitleEngine    → الترجمة العربية الاحترافية (RTL)

الاستخدام:
    from engine.video import CinematicEditor, SubtitleEngine
    
    editor = CinematicEditor()
    subs = SubtitleEngine(width=1080, height=1920)
═══════════════════════════════════════════════════════════════
"""

import logging
from typing import Optional

logger = logging.getLogger(__name__)

# ─── الاستيرادات الأساسية ────────────────────────────────────────────────
from engine.video.cinematic_editor import CinematicEditor
from engine.video.subtitle_engine import SubtitleEngine

# ─── استيرادات اختيارية (آمنة) ────────────────────────────────────────────
try:
    from engine.video.effects_engine import EffectsEngine
    _EFFECTS_AVAILABLE = True
except ImportError as e:
    EffectsEngine = None
    _EFFECTS_AVAILABLE = False
    logger.debug(f"EffectsEngine not available: {e}")

try:
    from engine.video.transition_engine import TransitionEngine
    _TRANSITIONS_AVAILABLE = True
except ImportError as e:
    TransitionEngine = None
    _TRANSITIONS_AVAILABLE = False
    logger.debug(f"TransitionEngine not available: {e}")


# ════════════════════════════════════════════════════════════════════════
#                    دوال مساعدة
# ════════════════════════════════════════════════════════════════════════
def list_available_engines() -> dict:
    """قائمة محركات الفيديو المتاحة."""
    return {
        "cinematic_editor":  True,
        "subtitle_engine":   True,
        "effects_engine":    _EFFECTS_AVAILABLE,
        "transition_engine": _TRANSITIONS_AVAILABLE,
    }


def get_default_dimensions() -> tuple:
    """الأبعاد الافتراضية لـ YouTube Shorts."""
    import os
    width = int(os.getenv("VIDEO_WIDTH", "1080"))
    height = int(os.getenv("VIDEO_HEIGHT", "1920"))
    return (width, height)


def get_default_fps() -> int:
    """الـ FPS الافتراضي."""
    import os
    return int(os.getenv("VIDEO_FPS", "30"))


# ════════════════════════════════════════════════════════════════════════
#                    Exports
# ════════════════════════════════════════════════════════════════════════
__all__ = [
    # المحركات الأساسية
    "CinematicEditor",
    "SubtitleEngine",
    # المحركات الاختيارية
    "EffectsEngine",
    "TransitionEngine",
    # دوال مساعدة
    "list_available_engines",
    "get_default_dimensions",
    "get_default_fps",
]
