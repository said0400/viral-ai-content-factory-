"""
🎙️ Voice Module v2.0 — توليد ومعالجة الصوت العربي
═══════════════════════════════════════════════════════════════
يدعم محركات TTS متعددة:
  • Edge TTS    (أساسي - مجاني)
  • Groq TTS    (orpheus arabic)
  • Gemini TTS  (Google)
  • ElevenLabs  (premium)
═══════════════════════════════════════════════════════════════
"""

from __future__ import annotations

import os
import logging
from typing import Optional, Literal

logger = logging.getLogger(__name__)

__version__ = "2.0.0"

# ═══════════════════════════════════════════════════════════════
# Type Aliases
# ═══════════════════════════════════════════════════════════════
TTSEngineType = Literal["auto", "edge", "elevenlabs", "gemini", "groq"]


# ═══════════════════════════════════════════════════════════════
# Lazy imports للأمان
# ═══════════════════════════════════════════════════════════════
def _try_import(module_name: str, class_name: str):
    """استيراد آمن للـ classes."""
    try:
        module = __import__(module_name, fromlist=[class_name])
        return getattr(module, class_name), True
    except (ImportError, AttributeError) as e:
        logger.debug(f"{class_name} not available: {e}")
        return None, False


# ═══════════════════════════════════════════════════════════════
# Availability Checks
# ═══════════════════════════════════════════════════════════════
def check_edge_available() -> bool:
    try:
        import edge_tts
        return True
    except ImportError:
        return False


def check_groq_available() -> bool:
    if not os.getenv("GROQ_API_KEY"):
        return False
    try:
        from groq import Groq
        return True
    except ImportError:
        return False


def check_gemini_available() -> bool:
    if not os.getenv("GEMINI_API_KEY"):
        return False
    try:
        from google import genai
        return True
    except ImportError:
        return False


def check_elevenlabs_available() -> bool:
    if not os.getenv("ELEVENLABS_API_KEY"):
        return False
    try:
        import requests
        return True
    except ImportError:
        return False


def get_available_engines() -> list[str]:
    """قائمة المحركات المتاحة."""
    available = []
    if check_edge_available():
        available.append("edge")
    if check_groq_available():
        available.append("groq")
    if check_gemini_available():
        available.append("gemini")
    if check_elevenlabs_available():
        available.append("elevenlabs")
    return available


# ═══════════════════════════════════════════════════════════════
# Factory Function
# ═══════════════════════════════════════════════════════════════
def create_tts_engine(prefer: TTSEngineType = "auto", **kwargs):
    """
    🏭 إنشاء محرك TTS.
    
    Args:
        prefer: المحرك المفضل (auto/edge/groq/gemini/elevenlabs)
        **kwargs: arguments للـ engine
    
    Returns:
        TTS engine instance
    """
    # قراءة من البيئة إذا auto
    if prefer == "auto":
        env_pref = os.getenv("TTS_ENGINE", "auto").lower()
        if env_pref != "auto":
            prefer = env_pref  # type: ignore
    
    # Aliases
    aliases = {"edge-tts": "edge", "edge_tts": "edge"}
    prefer = aliases.get(prefer, prefer)
    
    # ═══ Edge ═══
    if prefer == "edge":
        try:
            from engine.video.voice.edge_tts_engine import EdgeTTS
            logger.info("🎙️ TTS: EdgeTTS")
            return EdgeTTS(**kwargs)
        except ImportError as e:
            raise RuntimeError(
                f"❌ EdgeTTS غير متاح: {e}\n"
                f"   pip install edge-tts"
            )
    
    # ═══ Groq ═══
    if prefer == "groq":
        try:
            from engine.video.voice.groq_tts import GroqTTS
            logger.info("🎙️ TTS: GroqTTS")
            return GroqTTS(**kwargs)
        except ImportError as e:
            raise RuntimeError(
                f"❌ GroqTTS غير متاح: {e}\n"
                f"   تحقق من GROQ_API_KEY"
            )
    
    # ═══ Gemini ═══
    if prefer == "gemini":
        try:
            from engine.video.voice.gemini_tts_engine import GeminiTTSEngine
            logger.info("🎙️ TTS: GeminiTTS")
            return GeminiTTSEngine(**kwargs)
        except ImportError as e:
            raise RuntimeError(
                f"❌ GeminiTTS غير متاح: {e}\n"
                f"   pip install google-genai"
            )
    
    # ═══ ElevenLabs ═══
    if prefer == "elevenlabs":
        try:
            from engine.video.voice.elevenlabs_tts import ElevenLabsTTS
            logger.info("🎙️ TTS: ElevenLabsTTS")
            return ElevenLabsTTS(**kwargs)
        except ImportError as e:
            raise RuntimeError(
                f"❌ ElevenLabsTTS غير متاح: {e}\n"
                f"   تحقق من ELEVENLABS_API_KEY"
            )
    
    # ═══ Auto Mode ═══
    if prefer == "auto":
        # ترتيب الأولوية
        priority = ["edge", "groq", "gemini", "elevenlabs"]
        
        # تفضيلات خاصة
        if os.getenv("PREFER_GEMINI", "false").lower() == "true":
            priority = ["gemini"] + [e for e in priority if e != "gemini"]
        
        if os.getenv("PREFER_ELEVENLABS", "false").lower() == "true":
            priority = ["elevenlabs"] + [e for e in priority if e != "elevenlabs"]
        
        # جرب بالترتيب
        available = get_available_engines()
        for engine in priority:
            if engine in available:
                try:
                    logger.info(f"🎙️ Auto-selected: {engine}")
                    return create_tts_engine(prefer=engine, **kwargs)
                except Exception as e:
                    logger.warning(f"⚠ فشل {engine}: {e}")
                    continue
        
        raise RuntimeError(
            "❌ لا يوجد محرك TTS متاح!\n"
            "   ثبّت أحد:\n"
            "     • pip install edge-tts (مجاني)\n"
            "     • pip install groq\n"
            "     • pip install google-genai\n"
        )
    
    raise ValueError(
        f"❌ محرك غير معروف: '{prefer}'\n"
        f"   المتاح: auto, edge, groq, gemini, elevenlabs"
    )


# ═══════════════════════════════════════════════════════════════
# Convenience Functions
# ═══════════════════════════════════════════════════════════════
def get_default_voice() -> str:
    """الصوت الافتراضي."""
    return os.getenv("TTS_VOICE", "ar-SA-HamedNeural")


def get_default_engine() -> str:
    """المحرك الافتراضي."""
    return os.getenv("TTS_ENGINE", "auto")


def list_available_engines() -> dict[str, bool]:
    """قاموس بحالة كل محرك."""
    return {
        "edge": check_edge_available(),
        "groq": check_groq_available(),
        "gemini": check_gemini_available(),
        "elevenlabs": check_elevenlabs_available(),
    }


# ═══════════════════════════════════════════════════════════════
# Lazy imports للـ classes
# ═══════════════════════════════════════════════════════════════
def __getattr__(name: str):
    """Lazy import للـ TTS classes."""
    
    if name == "EdgeTTS":
        try:
            from engine.video.voice.edge_tts_engine import EdgeTTS
            return EdgeTTS
        except ImportError as e:
            raise ImportError(f"EdgeTTS غير متاح: {e}")
    
    if name == "GroqTTS":
        try:
            from engine.video.voice.groq_tts import GroqTTS
            return GroqTTS
        except ImportError as e:
            raise ImportError(f"GroqTTS غير متاح: {e}")
    
    if name == "GeminiTTSEngine":
        try:
            from engine.video.voice.gemini_tts_engine import GeminiTTSEngine
            return GeminiTTSEngine
        except ImportError as e:
            raise ImportError(f"GeminiTTS غير متاح: {e}")
    
    if name == "ElevenLabsTTS":
        try:
            from engine.video.voice.elevenlabs_tts import ElevenLabsTTS
            return ElevenLabsTTS
        except ImportError as e:
            raise ImportError(f"ElevenLabsTTS غير متاح: {e}")
    
    if name == "WhisperTranscriber":
        try:
            from engine.video.voice.whisper_transcriber import WhisperTranscriber
            return WhisperTranscriber
        except ImportError as e:
            raise ImportError(f"Whisper غير متاح: {e}")
    
    if name == "AudioFX":
        try:
            from engine.video.voice.audio_fx import AudioFX
            return AudioFX
        except ImportError as e:
            raise ImportError(f"AudioFX غير متاح: {e}")
    
    if name == "MusicEngine":
        try:
            from engine.video.voice.music_engine import MusicEngine
            return MusicEngine
        except ImportError as e:
            raise ImportError(f"MusicEngine غير متاح: {e}")
    
    if name == "SFXManager":
        try:
            from engine.video.voice.sfx_manager import SFXManager
            return SFXManager
        except ImportError as e:
            raise ImportError(f"SFXManager غير متاح: {e}")
    
    if name == "BreathingEngine":
        try:
            from engine.video.voice.breathing_engine import BreathingEngine
            return BreathingEngine
        except ImportError as e:
            raise ImportError(f"BreathingEngine غير متاح: {e}")
    
    if name == "AudioOptimizer":
        try:
            from engine.video.voice.audio_optimizer import AudioOptimizer
            return AudioOptimizer
        except ImportError as e:
            raise ImportError(f"AudioOptimizer غير متاح: {e}")
    
    raise AttributeError(
        f"module 'engine.video.voice' has no attribute '{name}'"
    )


# ═══════════════════════════════════════════════════════════════
# Public API
# ═══════════════════════════════════════════════════════════════
__all__ = [
    "__version__",
    
    # Factory
    "create_tts_engine",
    
    # Lazy-loaded classes
    "EdgeTTS",
    "GroqTTS",
    "GeminiTTSEngine",
    "ElevenLabsTTS",
    "WhisperTranscriber",
    "AudioFX",
    "MusicEngine",
    "SFXManager",
    "BreathingEngine",
    "AudioOptimizer",
    
    # Helpers
    "check_edge_available",
    "check_groq_available",
    "check_gemini_available",
    "check_elevenlabs_available",
    "get_available_engines",
    "list_available_engines",
    "get_default_voice",
    "get_default_engine",
    
    # Types
    "TTSEngineType",
]
