"""
🎙️ Base TTS Engine
═══════════════════════════════════════════════════════════════
الكلاس الأساسي لجميع محركات TTS

يحتوي على:
  ✓ TTSResult dataclass
  ✓ Text building (مع pause markers)
  ✓ Caching system
  ✓ Silence fallback
  ✓ Voice selection
  ✓ FFmpeg utilities
═══════════════════════════════════════════════════════════════
"""

from __future__ import annotations

import os
import shutil
import hashlib
import logging
import subprocess
from abc import ABC, abstractmethod
from pathlib import Path
from enum import Enum
from dataclasses import dataclass, field
from typing import Optional, Callable, Any

logger = logging.getLogger(__name__)


# ═══════════════════════════════════════════════════════════════════
# Enums & Types
# ═══════════════════════════════════════════════════════════════════
class TTSStatus(str, Enum):
    """حالة توليد الصوت."""
    SUCCESS = "success"
    FALLBACK_VOICE = "fallback_voice"
    CACHED = "cached"
    SILENCE = "silence"
    FAILED = "failed"


@dataclass
class TTSResult:
    """نتيجة توليد الصوت."""
    status: TTSStatus
    output_path: str
    voice_used: str = ""
    text_length: int = 0
    file_size: int = 0
    duration_estimate: float = 0.0
    error: Optional[str] = None
    cached: bool = False
    cost_estimate: float = 0.0  # بالعملة أو حروف
    
    @property
    def success(self) -> bool:
        return self.status in (
            TTSStatus.SUCCESS,
            TTSStatus.FALLBACK_VOICE,
            TTSStatus.CACHED,
        )


@dataclass(frozen=True)
class VoiceInfo:
    """معلومات صوت."""
    voice_id: str
    name: str
    gender: str
    lang: str
    description: str = ""
    provider: str = ""


# ═══════════════════════════════════════════════════════════════════
# Constants
# ═══════════════════════════════════════════════════════════════════
class TTSConstants:
    """الثوابت المشتركة."""
    
    MIN_FILE_SIZE_BYTES = 1000
    DEFAULT_SILENCE_DURATION = 30
    WORDS_PER_SECOND_ARABIC = 2.5


# ═══════════════════════════════════════════════════════════════════
# Utility Functions
# ═══════════════════════════════════════════════════════════════════
def check_ffmpeg_available() -> bool:
    """التحقق من توفر FFmpeg."""
    return shutil.which("ffmpeg") is not None


def get_text_hash(text: str, *args) -> str:
    """إنشاء hash للـ caching."""
    content = "|".join([text] + [str(a) for a in args])
    return hashlib.md5(content.encode()).hexdigest()[:16]


def estimate_duration(text: str) -> float:
    """تقدير المدة بالثواني."""
    word_count = len(text.split())
    return word_count / TTSConstants.WORDS_PER_SECOND_ARABIC


def get_pause_marker(pause_duration: float, format: str = "simple") -> str:
    """
    تحويل مدة الوقفة لعلامة.
    
    Args:
        pause_duration: مدة الوقفة بالثواني
        format: "simple" أو "ssml"
    """
    if format == "ssml":
        if pause_duration >= 0.8:
            return '<break time="1s"/>'
        elif pause_duration >= 0.5:
            return '<break time="0.6s"/>'
        elif pause_duration >= 0.3:
            return '<break time="0.3s"/>'
        return ""
    
    # simple format
    if pause_duration >= 0.8:
        return "... "
    elif pause_duration >= 0.5:
        return ".. "
    elif pause_duration >= 0.3:
        return ", "
    return " "


# ═══════════════════════════════════════════════════════════════════
# Base TTS Class
# ═══════════════════════════════════════════════════════════════════
class BaseTTS(ABC):
    """الكلاس الأساسي لجميع محركات TTS."""
    
    PROVIDER_NAME: str = "base"
    PAUSE_FORMAT: str = "simple"  # "simple" أو "ssml"
    MAX_TEXT_LENGTH: int = 5000
    
    def __init__(
        self,
        cache_enabled: bool = True,
        cache_dir: Optional[str] = None,
    ):
        self.cache_enabled = cache_enabled
        
        # المجلدات
        self.temp_dir = Path(os.getenv("TEMP_DIR", "./temp"))
        self.temp_dir.mkdir(parents=True, exist_ok=True)
        
        if cache_enabled:
            cache_path = cache_dir or self.temp_dir / f"tts_cache_{self.PROVIDER_NAME}"
            self.cache_dir = Path(cache_path)
            self.cache_dir.mkdir(parents=True, exist_ok=True)
        else:
            self.cache_dir = None
        
        # FFmpeg
        self._ffmpeg_available = check_ffmpeg_available()
        if not self._ffmpeg_available:
            logger.warning(
                f"⚠ FFmpeg غير متاح في {self.PROVIDER_NAME}"
            )
    
    # ═══════════════════════════════════════════════════════════════
    # Abstract Methods
    # ═══════════════════════════════════════════════════════════════
    @abstractmethod
    def _generate_audio_data(
        self,
        text: str,
        voice: str,
        **kwargs,
    ) -> Optional[bytes]:
        """التوليد الفعلي - يجب تطبيقه في subclasses."""
        pass
    
    @abstractmethod
    def _select_voice_for_mood(self, mood: str) -> str:
        """اختيار الصوت حسب المزاج."""
        pass
    
    # ═══════════════════════════════════════════════════════════════
    # Public API
    # ═══════════════════════════════════════════════════════════════
    def generate_audio(
        self,
        script: dict,
        output_path: str,
        progress_callback: Optional[Callable[[float, str], None]] = None,
    ) -> TTSResult:
        """توليد صوت من السكربت."""
        self._ensure_output_dir(output_path)
        
        # بناء النص
        full_text = self._build_full_text(script)
        if not full_text.strip():
            logger.error("❌ النص فارغ!")
            return self._silence_result(output_path, "Empty text")
        
        # اختيار الصوت
        mood = script.get("music_mood", "motivation")
        voice = self._select_voice(script, mood)
        
        logger.info(
            f"🎙️ {self.PROVIDER_NAME} | Voice: {voice} | "
            f"Text: {len(full_text)} chars"
        )
        
        if progress_callback:
            progress_callback(0.1, f"إعداد {self.PROVIDER_NAME}")
        
        # تحقق من الكاش
        if self.cache_enabled:
            cached = self._get_cached(full_text, voice)
            if cached:
                shutil.copy(cached, output_path)
                logger.info("⚡ من الكاش")
                
                if progress_callback:
                    progress_callback(1.0, "من الكاش")
                
                return TTSResult(
                    status=TTSStatus.CACHED,
                    output_path=output_path,
                    voice_used=voice,
                    text_length=len(full_text),
                    file_size=Path(output_path).stat().st_size,
                    duration_estimate=estimate_duration(full_text),
                    cached=True,
                )
        
        # التوليد
        if progress_callback:
            progress_callback(0.4, "توليد الصوت...")
        
        try:
            audio_data = self._generate_audio_data(full_text, voice)
            
            if not audio_data or len(audio_data) < TTSConstants.MIN_FILE_SIZE_BYTES:
                raise RuntimeError("Audio data too small")
            
            # حفظ
            with open(output_path, "wb") as f:
                f.write(audio_data)
            
            # كاش
            if self.cache_enabled:
                self._save_to_cache(output_path, full_text, voice)
            
            if progress_callback:
                progress_callback(1.0, "تم!")
            
            logger.info(
                f"✓ {self.PROVIDER_NAME} | "
                f"{len(audio_data) / 1024:.1f} KB"
            )
            
            return TTSResult(
                status=TTSStatus.SUCCESS,
                output_path=output_path,
                voice_used=voice,
                text_length=len(full_text),
                file_size=len(audio_data),
                duration_estimate=estimate_duration(full_text),
                cost_estimate=len(full_text),  # حروف
            )
            
        except Exception as e:
            logger.error(f"❌ فشل {self.PROVIDER_NAME}: {e}")
            return self._silence_result(output_path, str(e))
    
    def generate_for_text(
        self,
        text: str,
        output_path: str,
        voice: Optional[str] = None,
        **kwargs,
    ) -> TTSResult:
        """توليد لنص بسيط."""
        if not text or not text.strip():
            return TTSResult(
                status=TTSStatus.FAILED,
                output_path=output_path,
                error="Empty text",
            )
        
        self._ensure_output_dir(output_path)
        voice = voice or self._select_voice_for_mood("motivation")
        
        try:
            audio_data = self._generate_audio_data(text, voice, **kwargs)
            
            if audio_data and len(audio_data) > TTSConstants.MIN_FILE_SIZE_BYTES:
                with open(output_path, "wb") as f:
                    f.write(audio_data)
                
                return TTSResult(
                    status=TTSStatus.SUCCESS,
                    output_path=output_path,
                    voice_used=voice,
                    text_length=len(text),
                    file_size=len(audio_data),
                    duration_estimate=estimate_duration(text),
                )
            
            raise RuntimeError("Generation failed")
            
        except Exception as e:
            logger.error(f"❌ فشل: {e}")
            return self._silence_result(output_path, str(e))
    
    # ═══════════════════════════════════════════════════════════════
    # Text Building
    # ═══════════════════════════════════════════════════════════════
    def _build_full_text(self, script: dict) -> str:
        """تجميع النص من المشاهد."""
        parts = []
        
        for scene in script.get("scenes", []):
            text = scene.get("text", "").strip()
            pause = float(scene.get("pause_after", 0.3))
            
            if not text:
                continue
            
            parts.append(text)
            
            marker = get_pause_marker(pause, self.PAUSE_FORMAT)
            if marker:
                parts.append(marker)
        
        # CTA
        cta = script.get("cta", "").strip()
        if cta:
            parts.append(get_pause_marker(1.0, self.PAUSE_FORMAT))
            parts.append(cta)
        
        return " ".join(parts).strip()
    
    # ═══════════════════════════════════════════════════════════════
    # Voice Selection
    # ═══════════════════════════════════════════════════════════════
    def _select_voice(self, script: dict, mood: str) -> str:
        """اختيار الصوت."""
        # من السكربت
        if "voice" in script:
            return script["voice"]
        
        # من البيئة
        env_voice = os.getenv(f"TTS_VOICE_{self.PROVIDER_NAME.upper()}")
        if env_voice:
            return env_voice
        
        # من المزاج
        return self._select_voice_for_mood(mood)
    
    # ═══════════════════════════════════════════════════════════════
    # Caching
    # ═══════════════════════════════════════════════════════════════
    def _get_cached(self, text: str, voice: str, *extra) -> Optional[str]:
        """البحث في الكاش."""
        if not self.cache_enabled or not self.cache_dir:
            return None
        
        cache_key = get_text_hash(text, voice, *extra)
        cache_path = self.cache_dir / f"{cache_key}.mp3"
        
        if (cache_path.exists() and
            cache_path.stat().st_size > TTSConstants.MIN_FILE_SIZE_BYTES):
            return str(cache_path)
        return None
    
    def _save_to_cache(
        self,
        source_path: str,
        text: str,
        voice: str,
        *extra,
    ) -> None:
        """حفظ في الكاش."""
        if not self.cache_enabled or not self.cache_dir:
            return
        
        try:
            cache_key = get_text_hash(text, voice, *extra)
            cache_path = self.cache_dir / f"{cache_key}.mp3"
            shutil.copy(source_path, cache_path)
            logger.debug(f"💾 محفوظ: {cache_key}")
        except Exception as e:
            logger.warning(f"⚠ فشل الكاش: {e}")
    
    def clear_cache(self) -> int:
        """مسح الكاش."""
        if not self.cache_enabled or not self.cache_dir:
            return 0
        
        count = 0
        for f in self.cache_dir.glob("*.mp3"):
            f.unlink()
            count += 1
        
        logger.info(f"🗑 حُذف {count} ملف")
        return count
    
    # ═══════════════════════════════════════════════════════════════
    # Silence Fallback
    # ═══════════════════════════════════════════════════════════════
    def _silence_result(
        self,
        output_path: str,
        error: str,
        duration: int = TTSConstants.DEFAULT_SILENCE_DURATION,
    ) -> TTSResult:
        """إنشاء صمت كآخر احتياطي."""
        if not self._ffmpeg_available:
            return TTSResult(
                status=TTSStatus.FAILED,
                output_path=output_path,
                error=f"{error} | FFmpeg غير متاح",
            )
        
        try:
            subprocess.run(
                [
                    "ffmpeg", "-y", "-f", "lavfi",
                    "-i", "anullsrc=r=44100:cl=stereo",
                    "-t", str(duration),
                    "-c:a", "libmp3lame", "-b:a", "128k",
                    output_path,
                ],
                capture_output=True,
                check=True,
                timeout=30,
            )
            
            return TTSResult(
                status=TTSStatus.SILENCE,
                output_path=output_path,
                voice_used="silence",
                duration_estimate=float(duration),
                file_size=Path(output_path).stat().st_size,
                error=error,
            )
            
        except Exception as e:
            return TTSResult(
                status=TTSStatus.FAILED,
                output_path=output_path,
                error=f"{error} | Silence: {e}",
            )
    
    # ═══════════════════════════════════════════════════════════════
    # Utility
    # ═══════════════════════════════════════════════════════════════
    def _ensure_output_dir(self, output_path: str) -> None:
        """التأكد من وجود مجلد الـ output."""
        Path(output_path).parent.mkdir(parents=True, exist_ok=True)
