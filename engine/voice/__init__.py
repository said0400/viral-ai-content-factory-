"""
🎙️ Voice Module — توليد ومعالجة الصوت العربي
═══════════════════════════════════════════════════════════════
يدعم محركات TTS متعددة:
  • edge-tts    (أساسي - مجاني، يدعم العربية بجودة ممتازة)
  • ElevenLabs  (احتياطي - مدفوع، جودة أعلى)

كما يوفر:
  • BreathingEngine → إضافة تنفس طبيعي
  • AudioFX         → معالجة الصوت
  • MusicEngine     → الموسيقى الخلفية

الاستخدام:
    from engine.voice import create_tts_engine
    
    tts = create_tts_engine()              # auto
    tts = create_tts_engine("edge")        # edge-tts فقط
    tts = create_tts_engine("elevenlabs")  # ElevenLabs فقط
═══════════════════════════════════════════════════════════════
"""

import os
import logging
from typing import Optional

logger = logging.getLogger(__name__)

# ─── الاستيرادات الأساسية ────────────────────────────────────────────────
from engine.voice.breathing_engine import BreathingEngine
from engine.voice.audio_fx import AudioFX
from engine.voice.music_engine import MusicEngine

# ─── استيراد آمن لمحركات TTS ─────────────────────────────────────────────
# edge-tts (أساسي)
try:
    from engine.voice.edge_tts_engine import EdgeTTS
    _EDGE_AVAILABLE = True
except ImportError as e:
    EdgeTTS = None
    _EDGE_AVAILABLE = False
    logger.debug(f"edge-tts not available: {e}")

# ElevenLabs (احتياطي)
try:
    from engine.voice.elevenlabs_tts import ElevenLabsTTS
    _ELEVENLABS_AVAILABLE = True
except ImportError as e:
    ElevenLabsTTS = None
    _ELEVENLABS_AVAILABLE = False
    logger.debug(f"elevenlabs not available: {e}")

# Groq TTS (لا يدعم العربية - مُحتفظ به للاستخدامات الأخرى فقط)
try:
    from engine.voice.groq_tts import GroqTTS
    _GROQ_TTS_AVAILABLE = True
except ImportError:
    GroqTTS = None
    _GROQ_TTS_AVAILABLE = False


# ════════════════════════════════════════════════════════════════════════
#                    Factory Function
# ════════════════════════════════════════════════════════════════════════
def create_tts_engine(prefer: str = "auto"):
    """
    إنشاء محرك TTS بناءً على المتاح والمفضّل.

    Args:
        prefer: المحرك المفضل
            - "auto"       → اختيار تلقائي ذكي
            - "edge"       → edge-tts فقط
            - "elevenlabs" → ElevenLabs فقط

    Returns:
        كائن TTS جاهز للاستخدام

    Raises:
        RuntimeError: إذا لم يتوفر أي محرك صالح
    """
    has_elevenlabs = (
        _ELEVENLABS_AVAILABLE
        and bool(os.getenv("ELEVENLABS_API_KEY"))
    )
    has_edge = _EDGE_AVAILABLE  # edge-tts لا يحتاج مفتاح

    # ── طلب صريح ──────────────────────────────────────────────────
    if prefer == "edge":
        if not has_edge:
            raise RuntimeError(
                "❌ edge-tts غير متاح.\n"
                "   ثبّته بـ: pip install edge-tts"
            )
        logger.info("🎙️ TTS: edge-tts")
        return EdgeTTS()

    if prefer == "elevenlabs":
        if not has_elevenlabs:
            raise RuntimeError(
                "❌ ElevenLabs غير متاح.\n"
                "   تأكد من ELEVENLABS_API_KEY ومن تثبيت المكتبة"
            )
        logger.info("🎙️ TTS: ElevenLabs")
        return ElevenLabsTTS()

    # ── الوضع التلقائي (auto) ─────────────────────────────────────
    if prefer == "auto":
        # الأولوية لـ ElevenLabs إذا توفر مفتاحه (جودة أعلى)
        prefer_elevenlabs = (
            os.getenv("PREFER_ELEVENLABS", "false").lower() == "true"
        )

        if prefer_elevenlabs and has_elevenlabs:
            logger.info("🎙️ TTS: ElevenLabs (مُفضّل)")
            return ElevenLabsTTS()

        # الافتراضي: edge-tts (مجاني وممتاز للعربية)
        if has_edge:
            logger.info("🎙️ TTS: edge-tts (افتراضي)")
            return EdgeTTS()

        # احتياطي: ElevenLabs إذا لم يتوفر edge-tts
        if has_elevenlabs:
            logger.info("🎙️ TTS: ElevenLabs (احتياطي)")
            return ElevenLabsTTS()

        # لا يوجد أي محرك متاح
        raise RuntimeError(
            "❌ لا يوجد أي محرك TTS متاح!\n"
            "   ثبّت إحدى المكتبات:\n"
            "     pip install edge-tts\n"
            "     pip install elevenlabs"
        )

    raise ValueError(f"❌ خيار غير معروف: prefer='{prefer}'")


# ════════════════════════════════════════════════════════════════════════
#                    دوال مساعدة
# ════════════════════════════════════════════════════════════════════════
def list_available_engines() -> dict:
    """قائمة محركات TTS المتاحة حالياً."""
    return {
        "edge-tts":   _EDGE_AVAILABLE,
        "elevenlabs": _ELEVENLABS_AVAILABLE and bool(os.getenv("ELEVENLABS_API_KEY")),
        "groq":       _GROQ_TTS_AVAILABLE,  # لا يدعم العربية
    }


def get_default_voice() -> str:
    """الصوت الافتراضي للعربية."""
    return os.getenv("TTS_VOICE", "ar-SA-HamedNeural")


# ════════════════════════════════════════════════════════════════════════
#                    Exports
# ════════════════════════════════════════════════════════════════════════
__all__ = [
    # المحركات
    "EdgeTTS",
    "ElevenLabsTTS",
    "GroqTTS",
    # المعالجة
    "BreathingEngine",
    "AudioFX",
    "MusicEngine",
    # المصنع والمساعدات
    "create_tts_engine",
    "list_available_engines",
    "get_default_voice",
]
