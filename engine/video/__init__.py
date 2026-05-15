"""
🎬 Video Module — تجهيز البيانات لـ Remotion
═══════════════════════════════════════════════════════════════
بعد التحول لـ Remotion، أصبحت محركات الفيديو تُجهّز البيانات
بدلاً من تنفيذ التأثيرات بـ FFmpeg.

المحركات:
  • CinematicEditor   → جلب الفيديوهات + بناء props لـ Remotion
  • SubtitleEngine    → بناء بيانات الترجمات العربية (JSON)
  • EffectsEngine     → توليد إعدادات التأثيرات (Zoom, Shake, Grade)
  • TransitionEngine  → توليد إعدادات الانتقالات

الفلسفة الجديدة:
  ❌ Python لا يُنفّذ تأثيرات الفيديو
  ✅ Python يُجهّز البيانات (JSON)
  ✅ Remotion ينفذ كل شيء بـ React

الاستخدام:
    from engine.video import CinematicEditor, SubtitleEngine
    from engine.render import RemotionRenderer
    
    # 1. تجهيز البيانات
    editor = CinematicEditor()
    props = editor.build_props_for_remotion(script, audio, subs)
    
    # 2. التصدير
    renderer = RemotionRenderer()
    renderer.render_final(props, "output.mp4")

ميزات Remotion:
  ✓ دعم كامل للعربية (RTL + Arabic Shaping تلقائي)
  ✓ تأثيرات احترافية بـ React/CSS
  ✓ سرعة أكبر بـ 10x من FFmpeg
  ✓ معاينة مباشرة (Live Preview)
═══════════════════════════════════════════════════════════════
"""

import os
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
#                    🆕 دالة شاملة لبناء كل البيانات
# ════════════════════════════════════════════════════════════════════════
def build_complete_props(
    script: dict,
    audio_path: str,
    output_dir: Optional[str] = None,
) -> dict:
    """
    🆕 بناء كل البيانات لـ Remotion دفعة واحدة.

    تجمع كل المحركات (Editor + Subtitles + Effects + Transitions)
    لإنتاج props كامل لـ Remotion.

    Args:
        script: السكربت الكامل من AI
        audio_path: مسار ملف الصوت
        output_dir: مجلد الإخراج (اختياري)

    Returns:
        dict شامل لكل ما يحتاجه Remotion:
        {
            "title": "...",
            "scenes": [...],
            "subtitles": [...],
            "transitions": [...],
            "effects": {...},
            "design": {...},
            "audioPath": "...",
            ...
        }

    مثال الاستخدام:
        from engine.video import build_complete_props
        from engine.render import RemotionRenderer
        
        props = build_complete_props(script, "audio.mp3")
        renderer = RemotionRenderer()
        renderer.render_final(props, "output.mp4")
    """
    scenes = script.get("scenes", [])
    if not scenes:
        raise ValueError("❌ لا توجد مشاهد في السكربت")

    logger.info(f"🎬 بناء props شامل | {len(scenes)} مشهد")

    # 1️⃣ تجهيز المحركات
    editor = CinematicEditor()
    subs_engine = SubtitleEngine()

    # 2️⃣ بناء الترجمات (يحتاجها Editor)
    logger.info("► بناء بيانات الترجمات...")
    subtitles_data = subs_engine.build_subtitles_data(scenes)

    # 3️⃣ بناء props الأساسية (يجلب الفيديوهات)
    logger.info("► بناء props الأساسية...")
    props = editor.build_props_for_remotion(
        script=script,
        audio_path=audio_path,
        subtitle_data=subtitles_data,
    )

    # 4️⃣ إضافة إعدادات التأثيرات
    if _EFFECTS_AVAILABLE:
        logger.info("► إضافة إعدادات التأثيرات...")
        effects = EffectsEngine()
        props["effects"] = effects.get_global_effects()

        # تحديث كل مشهد بتأثيراته الخاصة
        for scene_data in props.get("scenes", []):
            scene_type = scene_data.get("type", "main")
            zoom_type = scene_data.get("zoomEffect", "slow_zoom_in")
            apply_shake = scene_data.get("shake", False)

            scene_effects = effects.get_all_effects_for_scene(
                scene_type=scene_type,
                zoom_type=zoom_type,
                apply_shake=apply_shake,
            )
            scene_data["effectsConfig"] = scene_effects

    # 5️⃣ إضافة إعدادات الانتقالات
    if _TRANSITIONS_AVAILABLE:
        logger.info("► بناء الانتقالات...")
        trans_engine = TransitionEngine()
        props["transitions"] = trans_engine.build_transitions_for_scenes(scenes)

    # 6️⃣ إضافة إعدادات تصميم الترجمات
    props["subtitleStyle"] = subs_engine.get_style_config()

    # 7️⃣ معلومات إضافية
    props["meta"] = {
        "totalScenes": len(scenes),
        "totalSubtitles": len(subtitles_data),
        "totalTransitions": len(props.get("transitions", [])),
        "engines": list_available_engines(),
        "version": "2.0-remotion",
    }

    logger.info(
        f"✓ Props شامل جاهز | "
        f"{props['meta']['totalScenes']} مشهد | "
        f"{props['meta']['totalSubtitles']} ترجمة | "
        f"{props['meta']['totalTransitions']} انتقال"
    )

    return props


# ════════════════════════════════════════════════════════════════════════
#                    دوال مساعدة عامة
# ════════════════════════════════════════════════════════════════════════
def list_available_engines() -> dict:
    """قائمة محركات الفيديو المتاحة وحالتها."""
    return {
        "cinematic_editor":  {
            "available": True,
            "mode": "remotion",
            "description": "جلب الفيديوهات + بناء props",
        },
        "subtitle_engine": {
            "available": True,
            "mode": "remotion",
            "description": "بناء بيانات الترجمات العربية (JSON)",
        },
        "effects_engine": {
            "available": _EFFECTS_AVAILABLE,
            "mode": "remotion",
            "description": "إعدادات التأثيرات (Zoom, Shake, Grade)",
        },
        "transition_engine": {
            "available": _TRANSITIONS_AVAILABLE,
            "mode": "remotion",
            "description": "إعدادات الانتقالات بين المشاهد",
        },
    }


def get_default_dimensions() -> tuple:
    """الأبعاد الافتراضية لـ YouTube Shorts."""
    width = int(os.getenv("VIDEO_WIDTH", "1080"))
    height = int(os.getenv("VIDEO_HEIGHT", "1920"))
    return (width, height)


def get_default_fps() -> int:
    """الـ FPS الافتراضي."""
    return int(os.getenv("VIDEO_FPS", "30"))


def get_default_quality() -> str:
    """جودة الفيديو الافتراضية."""
    return os.getenv("VIDEO_QUALITY", "high")


def get_video_config() -> dict:
    """الحصول على إعدادات الفيديو الكاملة."""
    return {
        "dimensions": get_default_dimensions(),
        "fps": get_default_fps(),
        "quality": get_default_quality(),
        "renderer": os.getenv("RENDERER", "remotion"),
        "use_remotion": os.getenv("USE_REMOTION", "true").lower() == "true",
    }


def print_status() -> None:
    """طباعة حالة المحركات (للتشخيص)."""
    config = get_video_config()
    engines = list_available_engines()

    print("=" * 60)
    print("🎬 Video Module Status")
    print("=" * 60)
    print(f"  Dimensions: {config['dimensions'][0]}x{config['dimensions'][1]}")
    print(f"  FPS: {config['fps']}")
    print(f"  Quality: {config['quality']}")
    print(f"  Renderer: {config['renderer']}")
    print(f"  Use Remotion: {config['use_remotion']}")
    print()
    print("📦 Available Engines:")
    for name, info in engines.items():
        status = "✓" if info["available"] else "✗"
        print(f"  {status} {name:20s} ({info['mode']})")
        print(f"      → {info['description']}")
    print("=" * 60)


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
    # 🆕 الدالة الشاملة
    "build_complete_props",
    # دوال مساعدة
    "list_available_engines",
    "get_default_dimensions",
    "get_default_fps",
    "get_default_quality",
    "get_video_config",
    "print_status",
]


# ════════════════════════════════════════════════════════════════════════
#                    اختبار سريع
# ════════════════════════════════════════════════════════════════════════
if __name__ == "__main__":
    print_status()
