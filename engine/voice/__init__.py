"""
🎙️ Voice Module — توليد ومعالجة الصوت العربي
═══════════════════════════════════════════════════════════════
يدعم محركات TTS متعددة:
  • edge-tts    (أساسي - مجاني، يدعم العربية بجودة ممتازة)
  • ElevenLabs  (مدفوع، جودة عالية)
  • 🆕 Gemini TTS (Google - 5 أصوات احترافية مع Director's Notes)

كما يوفر:
  • BreathingEngine → إضافة تنفس طبيعي
  • AudioFX         → معالجة الصوت
  • MusicEngine     → الموسيقى الخلفية

الاستخدام:
    from engine.voice import create_tts_engine
    
    tts = create_tts_engine()              # auto
    tts = create_tts_engine("edge")        # edge-tts فقط
    tts = create_tts_engine("elevenlabs")  # ElevenLabs فقط
    tts = create_tts_engine("gemini")      # 🆕 Gemini TTS
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

# 🆕 Gemini TTS (جديد)
try:
    from engine.voice.gemini_tts_engine import GeminiTTSEngine
    _GEMINI_AVAILABLE = True
except ImportError as e:
    GeminiTTSEngine = None
    _GEMINI_AVAILABLE = False
    logger.debug(f"gemini TTS not available: {e}")

# Groq TTS (لا يدعم العربية - مُحتفظ به للاستخدامات الأخرى)
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
            - "auto"       → اختيار تلقائي ذكي (يقرأ TTS_ENGINE من .env)
            - "edge"       → edge-tts فقط (مجاني)
            - "elevenlabs" → ElevenLabs فقط (مدفوع، جودة عالية)
            - "gemini"     → 🆕 Gemini TTS (Google)

    Returns:
        كائن TTS جاهز للاستخدام

    Raises:
        RuntimeError: إذا لم يتوفر أي محرك صالح
    """
    # 🆕 إذا كان prefer = "auto"، اقرأ من TTS_ENGINE
    if prefer == "auto":
        prefer = os.getenv("TTS_ENGINE", "auto").lower()

    has_elevenlabs = (
        _ELEVENLABS_AVAILABLE
        and bool(os.getenv("ELEVENLABS_API_KEY"))
    )
    has_edge = _EDGE_AVAILABLE  # edge-tts لا يحتاج مفتاح
    has_gemini = (
        _GEMINI_AVAILABLE
        and bool(os.getenv("GEMINI_API_KEY"))
    )

    # ── 🆕 طلب Gemini TTS ─────────────────────────────────────────
    if prefer == "gemini":
        if not has_gemini:
            raise RuntimeError(
                "❌ Gemini TTS غير متاح.\n"
                "   تأكد من:\n"
                "     1. GEMINI_API_KEY موجود في .env\n"
                "     2. ثبّت: pip install google-genai"
            )
        logger.info("🎙️ TTS: Gemini (Google) ⭐")
        return GeminiTTSEngine()

    # ── طلب edge-tts ──────────────────────────────────────────────
    if prefer in ("edge", "edge_tts", "edge-tts"):
        if not has_edge:
            raise RuntimeError(
                "❌ edge-tts غير متاح.\n"
                "   ثبّته بـ: pip install edge-tts"
            )
        logger.info("🎙️ TTS: edge-tts")
        return EdgeTTS()

    # ── طلب ElevenLabs ────────────────────────────────────────────
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
        # 🆕 الأولوية لـ Gemini إذا توفر مفتاحه
        prefer_gemini = (
            os.getenv("PREFER_GEMINI", "false").lower() == "true"
        )

        # الأولوية لـ ElevenLabs إذا توفر مفتاحه
        prefer_elevenlabs = (
            os.getenv("PREFER_ELEVENLABS", "false").lower() == "true"
        )

        if prefer_gemini and has_gemini:
            logger.info("🎙️ TTS: Gemini (مُفضّل) ⭐")
            return GeminiTTSEngine()

        if prefer_elevenlabs and has_elevenlabs:
            logger.info("🎙️ TTS: ElevenLabs (مُفضّل)")
            return ElevenLabsTTS()

        # الافتراضي: edge-tts (مجاني وممتاز للعربية)
        if has_edge:
            logger.info("🎙️ TTS: edge-tts (افتراضي)")
            return EdgeTTS()

        # احتياطي 1: Gemini
        if has_gemini:
            logger.info("🎙️ TTS: Gemini (احتياطي) ⭐")
            return GeminiTTSEngine()

        # احتياطي 2: ElevenLabs
        if has_elevenlabs:
            logger.info("🎙️ TTS: ElevenLabs (احتياطي)")
            return ElevenLabsTTS()

        # لا يوجد أي محرك متاح
        raise RuntimeError(
            "❌ لا يوجد أي محرك TTS متاح!\n"
            "   ثبّت إحدى المكتبات:\n"
            "     pip install edge-tts\n"
            "     pip install elevenlabs\n"
            "     pip install google-genai"
        )

    raise ValueError(
        f"❌ خيار غير معروف: prefer='{prefer}'\n"
        f"   الخيارات المتاحة: auto, edge, elevenlabs, gemini"
    )


# ════════════════════════════════════════════════════════════════════════
#                    دوال مساعدة
# ════════════════════════════════════════════════════════════════════════
def list_available_engines() -> dict:
    """قائمة محركات TTS المتاحة حالياً."""
    return {
        "edge-tts":   _EDGE_AVAILABLE,
        "elevenlabs": _ELEVENLABS_AVAILABLE and bool(os.getenv("ELEVENLABS_API_KEY")),
        "gemini":     _GEMINI_AVAILABLE and bool(os.getenv("GEMINI_API_KEY")),
        "groq":       _GROQ_TTS_AVAILABLE,
    }


def get_default_voice() -> str:
    """الصوت الافتراضي للعربية."""
    return os.getenv("TTS_VOICE", "ar-SA-HamedNeural")


def get_default_engine() -> str:
    """المحرك الافتراضي من .env."""
    return os.getenv("TTS_ENGINE", "auto")


def print_engines_status() -> None:
    """طباعة حالة كل المحركات (للتشخيص)."""
    engines = list_available_engines()
    print("=" * 50)
    print("🎙️  TTS Engines Status")
    print("=" * 50)
    for name, available in engines.items():
        status = "✅" if available else "❌"
        print(f"  {status} {name}")
    print(f"\n  Default engine: {get_default_engine()}")
    print(f"  Default voice:  {get_default_voice()}")
    print("=" * 50)


# ════════════════════════════════════════════════════════════════════════
#                    Exports
# ════════════════════════════════════════════════════════════════════════
__all__ = [
    # المحركات
    "EdgeTTS",
    "ElevenLabsTTS",
    "GeminiTTSEngine",  # 🆕
    "GroqTTS",
    # المعالجة
    "BreathingEngine",
    "AudioFX",
    "MusicEngine",
    # المصنع والمساعدات
    "create_tts_engine",
    "list_available_engines",
    "get_default_voice",
    "get_default_engine",
    "print_engines_status",
]


# ════════════════════════════════════════════════════════════════════════
#                    اختبار سريع
# ════════════════════════════════════════════════════════════════════════
if __name__ == "__main__":
    print_engines_status()
