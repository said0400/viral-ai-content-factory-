"""
🎙️ Voice Module v2.0 — Bridge to engine/voice/
═══════════════════════════════════════════════════════════════
هذا الملف يعمل كـ bridge بين:
  • engine.video.voice (المسار الذي يستخدمه الكود الجديد)
  • engine.voice (المسار الفعلي للملفات)
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
# Factory Function (يستخدم engine.voice وليس engine.video.voice)
# ═══════════════════════════════════════════════════════════════
def create_tts_engine(prefer: TTSEngineType = "auto", **kwargs):
    """
    🏭 إنشاء محرك TTS.
    
    Args:
        prefer: المحرك المفضل (auto/edge/groq/gemini/elevenlabs)
    
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
            from engine.voice.edge_tts_engine import EdgeTTS
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
            from engine.voice.groq_tts import GroqTTS
            logger.info("🎙️ TTS: GroqTTS")
            return GroqTTS(**kwargs)
        except ImportError as e:
            raise RuntimeError(
                f"❌ GroqTTS غير متاح: {e}"
            )
    
    # ═══ Gemini ═══
    if prefer == "gemini":
        try:
            from engine.voice.gemini_tts_engine import GeminiTTSEngine
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
            from engine.voice.elevenlabs_tts import ElevenLabsTTS
            logger.info("🎙️ TTS: ElevenLabsTTS")
            return ElevenLabsTTS(**kwargs)
        except ImportError as e:
            raise RuntimeError(
                f"❌ ElevenLabsTTS غير متاح: {e}"
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
            "❌ لا يوجد محرك TTS متاح!"
        )
    
    raise ValueError(
        f"❌ محرك غير معروف: '{prefer}'\n"
        f"   المتاح: auto, edge, groq, gemini, elevenlabs"
    )


# ═══════════════════════════════════════════════════════════════
# Helpers
# ═══════════════════════════════════════════════════════════════
def get_default_voice() -> str:
    return os.getenv("TTS_VOICE", "ar-SA-HamedNeural")


def get_default_engine() -> str:
    return os.getenv("TTS_ENGINE", "auto")


def list_available_engines() -> dict[str, bool]:
    return {
        "edge": check_edge_available(),
        "groq": check_groq_available(),
        "gemini": check_gemini_available(),
        "elevenlabs": check_elevenlabs_available(),
    }


# ═══════════════════════════════════════════════════════════════
# Lazy imports للـ classes (من engine.voice)
# ═══════════════════════════════════════════════════════════════
def __getattr__(name: str):
    """Lazy import للـ TTS classes من engine.voice."""
    
    if name == "EdgeTTS":
        try:
            from engine.voice.edge_tts_engine import EdgeTTS
            return EdgeTTS
        except ImportError as e:
            raise ImportError(f"EdgeTTS: {e}")
    
    if name == "GroqTTS":
        try:
            from engine.voice.groq_tts import GroqTTS
            return GroqTTS
        except ImportError as e:
            raise ImportError(f"GroqTTS: {e}")
    
    if name == "GeminiTTSEngine":
        try:
            from engine.voice.gemini_tts_engine import GeminiTTSEngine
            return GeminiTTSEngine
        except ImportError as e:
            raise ImportError(f"GeminiTTS: {e}")
    
    if name == "ElevenLabsTTS":
        try:
            from engine.voice.elevenlabs_tts import ElevenLabsTTS
            return ElevenLabsTTS
        except ImportError as e:
            raise ImportError(f"ElevenLabsTTS: {e}")
    
    if name == "WhisperTranscriber":
        try:
            from engine.voice.whisper_transcriber import WhisperTranscriber
            return WhisperTranscriber
        except ImportError as e:
            raise ImportError(f"Whisper: {e}")
    
    if name == "AudioFX":
        try:
            from engine.voice.audio_fx import AudioFX
            return AudioFX
        except ImportError as e:
            raise ImportError(f"AudioFX: {e}")
    
    if name == "MusicEngine":
        try:
            from engine.voice.music_engine import MusicEngine
            return MusicEngine
        except ImportError as e:
            raise ImportError(f"MusicEngine: {e}")
    
    if name == "SFXManager":
        try:
            from engine.voice.sfx_manager import SFXManager
            return SFXManager
        except ImportError as e:
            raise ImportError(f"SFXManager: {e}")
    
    if name == "BreathingEngine":
        try:
            from engine.voice.breathing_engine import BreathingEngine
            return BreathingEngine
        except ImportError as e:
            raise ImportError(f"BreathingEngine: {e}")
    
    if name == "AudioOptimizer":
        try:
            from engine.voice.audio_optimizer import AudioOptimizer
            return AudioOptimizer
        except ImportError as e:
            raise ImportError(f"AudioOptimizer: {e}")
    
    raise AttributeError(
        f"module 'engine.video.voice' has no attribute '{name}'"
    )


# ═══════════════════════════════════════════════════════════════
# Public API
# ═══════════════════════════════════════════════════════════════
__all__ = [
    "__version__",
    "create_tts_engine",
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
    "check_edge_available",
    "check_groq_available",
    "check_gemini_available",
    "check_elevenlabs_available",
    "get_available_engines",
    "list_available_engines",
    "get_default_voice",
    "get_default_engine",
    "TTSEngineType",
]
