"""
🎙️ Voice Module v2.0 — توليد ومعالجة الصوت العربي
═══════════════════════════════════════════════════════════════
يدعم محركات TTS متعددة:
  • EdgeTTS         (أساسي - مجاني)
  • GroqTTS         (عربي - canopylabs orpheus)
  • GeminiTTS       (Google - Director's Notes)
  • ElevenLabsTTS   (مدفوع - أعلى جودة)

كما يوفر:
  • BreathingEngine     → تنفس طبيعي
  • AudioFX             → معالجة صوتية
  • AudioOptimizer      → تحسين الصوت
  • MusicEngine         → موسيقى خلفية
  • SFXManager          → مؤثرات صوتية
  • WhisperTranscriber  → استخراج الترجمات

الاستخدام:
    from engine.video.voice import create_tts_engine
    
    tts = create_tts_engine()              # auto
    tts = create_tts_engine("edge")        # محدد
    tts = quick_tts("نص", "out.mp3")       # سريع
═══════════════════════════════════════════════════════════════
"""

from __future__ import annotations

import os
import logging
from functools import lru_cache
from typing import Optional, Literal, TYPE_CHECKING, Any

logger = logging.getLogger(__name__)


# ═══════════════════════════════════════════════════════════════════
# Version
# ═══════════════════════════════════════════════════════════════════
__version__ = "2.0.0"


# ═══════════════════════════════════════════════════════════════════
# Type Aliases
# ═══════════════════════════════════════════════════════════════════
TTSEngineType = Literal["auto", "edge", "elevenlabs", "gemini", "groq"]


# ═══════════════════════════════════════════════════════════════════
# Eager Imports (الأساسيات - تُستورد دائماً)
# ═══════════════════════════════════════════════════════════════════
from engine.video.voice.base_tts import (
    BaseTTS, TTSResult, TTSStatus, VoiceInfo, TTSConstants,
)
from engine.video.voice.ffmpeg_utils import (
    FFmpegResult, FFmpegConstants,
    check_ffmpeg_available, check_ffprobe_available,
    get_audio_duration, get_audio_info,
)

# Audio processing (lightweight)
from engine.video.voice.breathing_engine import BreathingEngine, BreathResult
from engine.video.voice.audio_fx import (
    AudioFX, AudioFXResult, SFXTrack,
    LoudnessPreset, VoiceMood,
)
from engine.video.voice.audio_optimizer import (
    AudioOptimizer, OptimizationResult, OptimizationPreset,
    OptimizationConfig,
)
from engine.video.voice.music_engine import (
    MusicEngine, MusicTrack, MusicResult, EnergyLevel,
)
from engine.video.voice.sfx_manager import (
    SFXManager, SFXResult, SFXFile, SFXIntensity,
)


# ═══════════════════════════════════════════════════════════════════
# Lazy Imports (TTS engines - تُستورد عند الحاجة)
# ═══════════════════════════════════════════════════════════════════
if TYPE_CHECKING:
    from engine.video.voice.edge_tts_engine import EdgeTTS
    from engine.video.voice.elevenlabs_tts import ElevenLabsTTS
    from engine.video.voice.gemini_tts_engine import GeminiTTSEngine
    from engine.video.voice.groq_tts import GroqTTS
    from engine.video.voice.whisper_transcriber import (
        WhisperTranscriber, TranscriptionResult, SubtitleChunk, WordTiming,
    )


def _lazy_import_edge():
    """استيراد EdgeTTS عند الحاجة."""
    try:
        from engine.video.voice.edge_tts_engine import EdgeTTS
        return EdgeTTS, True
    except ImportError as e:
        logger.debug(f"EdgeTTS not available: {e}")
        return None, False


def _lazy_import_elevenlabs():
    """استيراد ElevenLabsTTS عند الحاجة."""
    try:
        from engine.video.voice.elevenlabs_tts import ElevenLabsTTS
        return ElevenLabsTTS, True
    except ImportError as e:
        logger.debug(f"ElevenLabs not available: {e}")
        return None, False


def _lazy_import_gemini():
    """استيراد GeminiTTS عند الحاجة."""
    try:
        from engine.video.voice.gemini_tts_engine import GeminiTTSEngine
        return GeminiTTSEngine, True
    except ImportError as e:
        logger.debug(f"GeminiTTS not available: {e}")
        return None, False


def _lazy_import_groq():
    """استيراد GroqTTS عند الحاجة."""
    try:
        from engine.video.voice.groq_tts import GroqTTS
        return GroqTTS, True
    except ImportError as e:
        logger.debug(f"GroqTTS not available: {e}")
        return None, False


def _lazy_import_whisper():
    """استيراد Whisper عند الحاجة."""
    try:
        from engine.video.voice.whisper_transcriber import (
            WhisperTranscriber, TranscriptionResult,
            SubtitleChunk, WordTiming,
        )
        return {
            "WhisperTranscriber": WhisperTranscriber,
            "TranscriptionResult": TranscriptionResult,
            "SubtitleChunk": SubtitleChunk,
            "WordTiming": WordTiming,
        }, True
    except ImportError as e:
        logger.debug(f"Whisper not available: {e}")
        return None, False


# ═══════════════════════════════════════════════════════════════════
# Availability Check
# ═══════════════════════════════════════════════════════════════════
def check_engine_available(engine: str) -> bool:
    """التحقق من توفر محرك معين."""
    if engine == "edge":
        _, ok = _lazy_import_edge()
        return ok
    
    elif engine == "elevenlabs":
        if not os.getenv("ELEVENLABS_API_KEY"):
            return False
        _, ok = _lazy_import_elevenlabs()
        return ok
    
    elif engine == "gemini":
        if not os.getenv("GEMINI_API_KEY"):
            return False
        _, ok = _lazy_import_gemini()
        return ok
    
    elif engine == "groq":
        if not os.getenv("GROQ_API_KEY"):
            return False
        _, ok = _lazy_import_groq()
        return ok
    
    return False


def get_available_engines() -> list[str]:
    """قائمة المحركات المتاحة."""
    available = []
    for engine in ["edge", "groq", "gemini", "elevenlabs"]:
        if check_engine_available(engine):
            available.append(engine)
    return available


def list_available_engines() -> dict[str, bool]:
    """قاموس بحالة كل محرك."""
    return {
        "edge": check_engine_available("edge"),
        "groq": check_engine_available("groq"),
        "gemini": check_engine_available("gemini"),
        "elevenlabs": check_engine_available("elevenlabs"),
        "whisper": _lazy_import_whisper()[1],
    }


# ═══════════════════════════════════════════════════════════════════
# Factory Function (مع caching)
# ═══════════════════════════════════════════════════════════════════
def create_tts_engine(
    prefer: TTSEngineType = "auto",
    **kwargs,
):
    """
    🏭 إنشاء محرك TTS ذكي.
    
    Args:
        prefer: المحرك المفضل
            - "auto"       → اختيار تلقائي (حسب الأولوية)
            - "edge"       → EdgeTTS (مجاني)
            - "groq"       → GroqTTS (عربي - orpheus)
            - "gemini"     → GeminiTTS (Director's Notes)
            - "elevenlabs" → ElevenLabsTTS (مدفوع)
        **kwargs: arguments للـ engine
    
    Returns:
        TTS instance
    
    Raises:
        RuntimeError: إذا لا يوجد محرك متاح
        ValueError: إذا الـ prefer غير صحيح
    """
    # قراءة من البيئة إذا auto
    if prefer == "auto":
        env_pref = os.getenv("TTS_ENGINE", "auto").lower()
        if env_pref != "auto":
            prefer = env_pref  # type: ignore
    
    # Normalize aliases
    aliases = {
        "edge-tts": "edge",
        "edge_tts": "edge",
    }
    prefer = aliases.get(prefer, prefer)  # type: ignore
    
    # ── محرك محدد ──
    if prefer in ("edge", "groq", "gemini", "elevenlabs"):
        return _create_specific_engine(prefer, **kwargs)
    
    # ── auto mode ──
    if prefer == "auto":
        return _create_auto_engine(**kwargs)
    
    raise ValueError(
        f"❌ خيار غير معروف: '{prefer}'\n"
        f"   المتاح: auto, edge, groq, gemini, elevenlabs"
    )


def _create_specific_engine(engine: str, **kwargs):
    """إنشاء محرك محدد."""
    engine_loaders = {
        "edge": (_lazy_import_edge, "EdgeTTS", "edge-tts"),
        "groq": (_lazy_import_groq, "GroqTTS", "GROQ_API_KEY"),
        "gemini": (_lazy_import_gemini, "GeminiTTSEngine", "GEMINI_API_KEY"),
        "elevenlabs": (
            _lazy_import_elevenlabs, "ElevenLabsTTS", "ELEVENLABS_API_KEY"
        ),
    }
    
    if engine not in engine_loaders:
        raise ValueError(f"Unknown engine: {engine}")
    
    loader, name, requirement = engine_loaders[engine]
    cls, available = loader()
    
    if not available:
        raise RuntimeError(
            f"❌ {name} غير متاح.\n"
            f"   تحقق من:\n"
            f"     • تثبيت المكتبة المطلوبة\n"
            f"     • {requirement} (إذا API key)"
        )
    
    logger.info(f"🎙️ TTS: {name}")
    return cls(**kwargs)


def _create_auto_engine(**kwargs):
    """اختيار تلقائي حسب الأولوية."""
    # ترتيب الأولوية (يمكن تعديله من البيئة)
    priority_order = os.getenv(
        "TTS_PRIORITY",
        "edge,groq,gemini,elevenlabs"  # الافتراضي
    ).split(",")
    priority_order = [e.strip().lower() for e in priority_order]
    
    # تفضيلات خاصة
    if os.getenv("PREFER_GEMINI", "false").lower() == "true":
        priority_order = ["gemini"] + [e for e in priority_order if e != "gemini"]
    
    if os.getenv("PREFER_ELEVENLABS", "false").lower() == "true":
        priority_order = ["elevenlabs"] + [
            e for e in priority_order if e != "elevenlabs"
        ]
    
    # جرب بالترتيب
    for engine in priority_order:
        if check_engine_available(engine):
            try:
                logger.info(f"🎙️ TTS: {engine} (auto)")
                return _create_specific_engine(engine, **kwargs)
            except Exception as e:
                logger.warning(f"⚠ فشل {engine}: {e}")
                continue
    
    # لا يوجد محرك متاح
    raise RuntimeError(
        "❌ لا يوجد محرك TTS متاح!\n"
        "   ثبّت أحد:\n"
        "     • pip install edge-tts (مجاني)\n"
        "     • pip install groq (عربي)\n"
        "     • pip install google-genai (Gemini)\n"
        "     • pip install elevenlabs (مدفوع)"
    )


# ═══════════════════════════════════════════════════════════════════
# Convenience Functions
# ═══════════════════════════════════════════════════════════════════
def quick_tts(
    text: str,
    output_path: str,
    voice: Optional[str] = None,
    engine: TTSEngineType = "auto",
) -> TTSResult:
    """
    🚀 توليد سريع لنص واحد.
    
    Examples:
        >>> from engine.video.voice import quick_tts
        >>> result = quick_tts("مرحباً", "hello.mp3")
        >>> print(result.success)
    """
    tts = create_tts_engine(prefer=engine)
    return tts.generate_for_text(text, output_path, voice=voice)


def get_default_voice() -> str:
    """الصوت الافتراضي."""
    return os.getenv("TTS_VOICE", "ar-SA-HamedNeural")


def get_default_engine() -> str:
    """المحرك الافتراضي."""
    return os.getenv("TTS_ENGINE", "auto")


def get_info() -> dict:
    """معلومات الموديول."""
    return {
        "version": __version__,
        "available_engines": get_available_engines(),
        "ffmpeg_available": check_ffmpeg_available(),
        "ffprobe_available": check_ffprobe_available(),
        "default_engine": get_default_engine(),
        "default_voice": get_default_voice(),
    }


# ═══════════════════════════════════════════════════════════════════
# Diagnostic
# ═══════════════════════════════════════════════════════════════════
def print_engines_status() -> None:
    """طباعة حالة كل المحركات."""
    info = get_info()
    engines = list_available_engines()
    
    print("=" * 60)
    print(f"🎙️  Voice Module v{__version__} — Status")
    print("=" * 60)
    
    # System
    print(f"\n📦 System:")
    print(f"   FFmpeg:  {'✅' if info['ffmpeg_available'] else '❌'}")
    print(f"   FFprobe: {'✅' if info['ffprobe_available'] else '❌'}")
    
    # TTS Engines
    print(f"\n🎙️ TTS Engines:")
    for name, available in engines.items():
        if name == "whisper":
            continue
        status = "✅" if available else "❌"
        print(f"   {status} {name}")
    
    # Other
    print(f"\n🔧 Other:")
    print(f"   {'✅' if engines.get('whisper') else '❌'} whisper (transcription)")
    
    # Defaults
    print(f"\n⚙️ Defaults:")
    print(f"   Engine: {info['default_engine']}")
    print(f"   Voice:  {info['default_voice']}")
    
    # Available
    print(f"\n🎯 Available: {info['available_engines'] or 'NONE'}")
    
    print("=" * 60)


# ═══════════════════════════════════════════════════════════════════
# Lazy Loading via __getattr__
# ═══════════════════════════════════════════════════════════════════
def __getattr__(name: str):
    """Lazy import للـ TTS engines الفردية."""
    
    if name == "EdgeTTS":
        cls, ok = _lazy_import_edge()
        if not ok:
            raise ImportError(
                "EdgeTTS غير متاح. ثبّت: pip install edge-tts"
            )
        return cls
    
    if name == "ElevenLabsTTS":
        cls, ok = _lazy_import_elevenlabs()
        if not ok:
            raise ImportError(
                "ElevenLabsTTS غير متاح. ثبّت: pip install elevenlabs"
            )
        return cls
    
    if name == "GeminiTTSEngine":
        cls, ok = _lazy_import_gemini()
        if not ok:
            raise ImportError(
                "GeminiTTS غير متاح. ثبّت: pip install google-genai"
            )
        return cls
    
    if name == "GroqTTS":
        cls, ok = _lazy_import_groq()
        if not ok:
            raise ImportError(
                "GroqTTS غير متاح. ثبّت: pip install groq"
            )
        return cls
    
    # Whisper
    if name in (
        "WhisperTranscriber", "TranscriptionResult",
        "SubtitleChunk", "WordTiming",
    ):
        whisper_classes, ok = _lazy_import_whisper()
        if not ok:
            raise ImportError(
                "Whisper غير متاح. ثبّت: pip install faster-whisper"
            )
        return whisper_classes[name]
    
    raise AttributeError(
        f"module 'engine.video.voice' has no attribute '{name}'"
    )


# ═══════════════════════════════════════════════════════════════════
# Public API
# ═══════════════════════════════════════════════════════════════════
__all__ = [
    # Version
    "__version__",
    
    # Base classes
    "BaseTTS",
    "TTSResult",
    "TTSStatus",
    "VoiceInfo",
    "TTSConstants",
    
    # FFmpeg utils
    "FFmpegResult",
    "FFmpegConstants",
    "check_ffmpeg_available",
    "check_ffprobe_available",
    "get_audio_duration",
    "get_audio_info",
    
    # Audio processing
    "BreathingEngine",
    "BreathResult",
    "AudioFX",
    "AudioFXResult",
    "SFXTrack",
    "LoudnessPreset",
    "VoiceMood",
    "AudioOptimizer",
    "OptimizationResult",
    "OptimizationPreset",
    "OptimizationConfig",
    "MusicEngine",
    "MusicTrack",
    "MusicResult",
    "EnergyLevel",
    "SFXManager",
    "SFXResult",
    "SFXFile",
    "SFXIntensity",
    
    # TTS engines (lazy)
    "EdgeTTS",
    "ElevenLabsTTS",
    "GeminiTTSEngine",
    "GroqTTS",
    
    # Whisper (lazy)
    "WhisperTranscriber",
    "TranscriptionResult",
    "SubtitleChunk",
    "WordTiming",
    
    # Factory & utilities
    "create_tts_engine",
    "quick_tts",
    "check_engine_available",
    "get_available_engines",
    "list_available_engines",
    "get_default_voice",
    "get_default_engine",
    "get_info",
    "print_engines_status",
    
    # Types
    "TTSEngineType",
]


# ═══════════════════════════════════════════════════════════════════
# Module Initialization Log
# ═══════════════════════════════════════════════════════════════════
def _log_module_status():
    """طباعة حالة الموديول (debug only)."""
    if logger.isEnabledFor(logging.DEBUG):
        available = get_available_engines()
        logger.debug(
            f"📦 engine.video.voice v{__version__} loaded | "
            f"Engines: {available or 'NONE'}"
        )


_log_module_status()


# ═══════════════════════════════════════════════════════════════════
# اختبار سريع
# ═══════════════════════════════════════════════════════════════════
if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s | %(levelname)s | %(message)s"
    )
    
    print_engines_status()
    
    print("\n🧪 Testing imports...")
    try:
        # Audio processing (eager)
        engines = list_available_engines()
        print(f"\n✅ Audio processing classes loaded")
        
        # TTS (lazy)
        if engines.get("edge"):
            from engine.video.voice import EdgeTTS
            print(f"✅ EdgeTTS lazy import works")
        
        if engines.get("whisper"):
            from engine.video.voice import WhisperTranscriber
            print(f"✅ WhisperTranscriber lazy import works")
        
        print("\n✅ All imports successful!")
        
    except Exception as e:
        print(f"\n❌ Error: {e}")
