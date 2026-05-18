"""
🎙️ ElevenLabs TTS Engine v2.0
═══════════════════════════════════════════════════════════════
محرك TTS احترافي عالي الجودة

التحسينات v2.0:
  ✓ يرث من BaseTTS (لا تكرار)
  ✓ TTSResult dataclass
  ✓ Caching ذكي (يوفر credits)
  ✓ Session للـ HTTP (أسرع)
  ✓ تحقق من credits قبل الإرسال
  ✓ تقسيم النصوص الطويلة
  ✓ Usage tracking
  ✓ يستخدم voice_tone و mood
═══════════════════════════════════════════════════════════════
"""

from __future__ import annotations

import os
import time
import logging
from pathlib import Path
from dataclasses import dataclass, field
from typing import Optional

import requests
from dotenv import load_dotenv

from engine.video.voice.base_tts import (
    BaseTTS, TTSResult, TTSStatus, VoiceInfo,
    TTSConstants, estimate_duration
)

load_dotenv()
logger = logging.getLogger(__name__)


# ═══════════════════════════════════════════════════════════════════
# Voices (Public ElevenLabs IDs)
# ═══════════════════════════════════════════════════════════════════
ELEVENLABS_VOICES: dict[str, VoiceInfo] = {
    "adam_deep": VoiceInfo(
        "pNInz6obpgDQGcFmaJgB", "Adam", "male", "multi",
        "صوت ذكوري عميق - مناسب للسرد والقصص",
        provider="elevenlabs"
    ),
    "antoni_strong": VoiceInfo(
        "ErXwobaYiN019PkySvjV", "Antoni", "male", "multi",
        "ذكوري قوي - مناسب للتحفيز",
        provider="elevenlabs"
    ),
    "bella_warm": VoiceInfo(
        "EXAVITQu4vr4xnSDxMaL", "Bella", "female", "multi",
        "نسائي دافئ - مناسب للعاطفة",
        provider="elevenlabs"
    ),
    "rachel_calm": VoiceInfo(
        "21m00Tcm4TlvDq8ikWAM", "Rachel", "female", "multi",
        "نسائي هادئ - مناسب للتعليم",
        provider="elevenlabs"
    ),
}

# Mood → Voice ID
MOOD_VOICE_MAP: dict[str, str] = {
    "motivation":    "pNInz6obpgDQGcFmaJgB",   # Adam
    "dark":          "pNInz6obpgDQGcFmaJgB",   # Adam
    "sigma":         "ErXwobaYiN019PkySvjV",   # Antoni
    "psychological": "21m00Tcm4TlvDq8ikWAM",   # Rachel
    "educational":   "21m00Tcm4TlvDq8ikWAM",   # Rachel
    "scientific":    "21m00Tcm4TlvDq8ikWAM",   # Rachel
    "emotional":     "EXAVITQu4vr4xnSDxMaL",   # Bella
    "sad":           "EXAVITQu4vr4xnSDxMaL",   # Bella
    "romantic":      "EXAVITQu4vr4xnSDxMaL",   # Bella
}

# Voice tone → Settings
TONE_SETTINGS_MAP: dict[str, dict] = {
    "calm":          {"stability": 0.7, "style": 0.3},
    "cold":          {"stability": 0.8, "style": 0.2},
    "intense":       {"stability": 0.4, "style": 0.7},
    "aggressive":    {"stability": 0.3, "style": 0.8},
    "authoritative": {"stability": 0.6, "style": 0.5},
    "curious":       {"stability": 0.5, "style": 0.6},
    "powerful":      {"stability": 0.5, "style": 0.7},
    "emotionless":   {"stability": 0.9, "style": 0.1},
}


# ═══════════════════════════════════════════════════════════════════
# Usage Tracking
# ═══════════════════════════════════════════════════════════════════
@dataclass
class ElevenLabsStats:
    """إحصائيات الاستخدام."""
    total_requests: int = 0
    successful: int = 0
    failed: int = 0
    cached_hits: int = 0
    total_chars_sent: int = 0
    total_chars_saved_by_cache: int = 0
    
    def summary(self) -> str:
        return (
            f"📊 ElevenLabs Stats:\n"
            f"   • Requests: {self.total_requests}\n"
            f"   • Success: {self.successful}\n"
            f"   • Failed: {self.failed}\n"
            f"   • Cache hits: {self.cached_hits}\n"
            f"   • Chars sent: {self.total_chars_sent:,}\n"
            f"   • Chars saved by cache: {self.total_chars_saved_by_cache:,}"
        )


# ═══════════════════════════════════════════════════════════════════
# Constants
# ═══════════════════════════════════════════════════════════════════
class ElevenLabsConstants:
    """ثوابت ElevenLabs."""
    
    BASE_URL = "https://api.elevenlabs.io/v1"
    
    ARABIC_MODELS = [
        "eleven_multilingual_v2",
        "eleven_turbo_v2_5",
        "eleven_flash_v2_5",
    ]
    
    DEFAULT_VOICE_ID = "pNInz6obpgDQGcFmaJgB"  # Adam
    DEFAULT_MODEL = "eleven_multilingual_v2"
    
    MAX_RETRIES = 3
    RETRY_DELAY = 2
    REQUEST_TIMEOUT = 120
    
    MAX_CHARS_PER_REQUEST = 5000  # حد ElevenLabs
    
    # Voice settings defaults
    DEFAULT_STABILITY = 0.5
    DEFAULT_SIMILARITY = 0.75
    DEFAULT_STYLE = 0.5
    
    # تكلفة تقريبية لكل حرف (للتقدير)
    COST_PER_CHAR = 0.00003  # $30 per 1M chars (تقريبي)


# ═══════════════════════════════════════════════════════════════════
# Main Class
# ═══════════════════════════════════════════════════════════════════
class ElevenLabsTTS(BaseTTS):
    """محرك ElevenLabs TTS - v2.0."""
    
    PROVIDER_NAME = "elevenlabs"
    PAUSE_FORMAT = "ssml"  # ElevenLabs يدعم break tags
    MAX_TEXT_LENGTH = ElevenLabsConstants.MAX_CHARS_PER_REQUEST
    
    def __init__(
        self,
        api_key: Optional[str] = None,
        voice_id: Optional[str] = None,
        model_id: Optional[str] = None,
        cache_enabled: bool = True,
        check_credits: bool = True,
    ):
        """
        Args:
            api_key: مفتاح API
            voice_id: معرف الصوت الافتراضي
            model_id: الموديل المستخدم
            cache_enabled: تفعيل الكاش (موفّر للـ credits!)
            check_credits: التحقق من credits قبل الإرسال
        """
        super().__init__(cache_enabled=cache_enabled)
        
        # API Key
        self.api_key = api_key or os.getenv("ELEVENLABS_API_KEY")
        if not self.api_key:
            raise ValueError(
                "❌ ELEVENLABS_API_KEY غير موجود\n"
                "   احصل عليه من: https://elevenlabs.io/app/settings/api-keys"
            )
        
        # إعدادات
        self.default_voice_id = (
            voice_id or
            os.getenv("ELEVENLABS_VOICE_ID") or
            ElevenLabsConstants.DEFAULT_VOICE_ID
        )
        self.default_model = (
            model_id or
            os.getenv("ELEVENLABS_MODEL") or
            ElevenLabsConstants.DEFAULT_MODEL
        )
        
        # Voice settings
        self.stability = float(
            os.getenv("ELEVENLABS_STABILITY", ElevenLabsConstants.DEFAULT_STABILITY)
        )
        self.similarity = float(
            os.getenv("ELEVENLABS_SIMILARITY", ElevenLabsConstants.DEFAULT_SIMILARITY)
        )
        self.style = float(
            os.getenv("ELEVENLABS_STYLE", ElevenLabsConstants.DEFAULT_STYLE)
        )
        self.use_speaker_boost = (
            os.getenv("ELEVENLABS_SPEAKER_BOOST", "true").lower() == "true"
        )
        
        # HTTP Session (أسرع من requests منفصلة)
        self.session = requests.Session()
        self.session.headers.update({
            "xi-api-key": self.api_key,
            "Content-Type": "application/json",
            "Accept": "audio/mpeg",
        })
        
        # Stats
        self.stats = ElevenLabsStats()
        self.check_credits_enabled = check_credits
        
        logger.info(
            f"✓ ElevenLabs v2.0 | Voice: {self.default_voice_id[:8]}... | "
            f"Model: {self.default_model}"
        )
    
    # ═══════════════════════════════════════════════════════════════
    # Override: Voice Selection
    # ═══════════════════════════════════════════════════════════════
    def _select_voice_for_mood(self, mood: str) -> str:
        """اختيار الصوت حسب المزاج."""
        return MOOD_VOICE_MAP.get(mood, self.default_voice_id)
    
    # ═══════════════════════════════════════════════════════════════
    # Override: Generation
    # ═══════════════════════════════════════════════════════════════
    def _generate_audio_data(
        self,
        text: str,
        voice: str,
        voice_tone: str = "intense",
        **kwargs,
    ) -> Optional[bytes]:
        """توليد البيانات الصوتية."""
        # تحقق من الـ credits
        if self.check_credits_enabled:
            remaining = self.get_remaining_chars()
            if remaining is not None and remaining < len(text):
                raise RuntimeError(
                    f"❌ Credits غير كافية: "
                    f"متبقي {remaining}، مطلوب {len(text)}"
                )
        
        # تقسيم النصوص الطويلة
        if len(text) > self.MAX_TEXT_LENGTH:
            return self._generate_chunked(text, voice, voice_tone)
        
        return self._generate_single(text, voice, voice_tone)
    
    def _generate_single(
        self,
        text: str,
        voice: str,
        voice_tone: str = "intense",
    ) -> Optional[bytes]:
        """توليد دفعة واحدة."""
        last_error = None
        
        for attempt in range(1, ElevenLabsConstants.MAX_RETRIES + 1):
            model_idx = min(attempt - 1, len(ElevenLabsConstants.ARABIC_MODELS) - 1)
            model = ElevenLabsConstants.ARABIC_MODELS[model_idx]
            
            logger.info(
                f"🤖 ElevenLabs [{attempt}/{ElevenLabsConstants.MAX_RETRIES}] "
                f"{model}"
            )
            
            try:
                audio = self._call_api(text, voice, model, voice_tone)
                
                if audio and len(audio) > TTSConstants.MIN_FILE_SIZE_BYTES:
                    self.stats.total_requests += 1
                    self.stats.successful += 1
                    self.stats.total_chars_sent += len(text)
                    return audio
                
            except Exception as e:
                last_error = e
                self.stats.total_requests += 1
                self.stats.failed += 1
                logger.warning(f"⚠ محاولة {attempt}: {e}")
                
                if attempt < ElevenLabsConstants.MAX_RETRIES:
                    time.sleep(ElevenLabsConstants.RETRY_DELAY * attempt)
        
        logger.error(f"❌ فشلت كل المحاولات: {last_error}")
        return None
    
    def _generate_chunked(
        self,
        text: str,
        voice: str,
        voice_tone: str,
    ) -> Optional[bytes]:
        """تقسيم النص الطويل."""
        logger.info(f"📦 تقسيم النص ({len(text)} حرف)")
        
        chunks = self._split_text(text)
        audio_parts = []
        
        for i, chunk in enumerate(chunks, 1):
            logger.info(f"   Chunk {i}/{len(chunks)} ({len(chunk)} حرف)")
            
            audio = self._generate_single(chunk, voice, voice_tone)
            if not audio:
                logger.error(f"❌ فشل chunk {i}")
                return None
            
            audio_parts.append(audio)
        
        # دمج بسيط (ElevenLabs MP3 streams قابلة للدمج المباشر)
        return b"".join(audio_parts)
    
    def _split_text(self, text: str) -> list[str]:
        """تقسيم النص على الجمل."""
        # تقسيم على نهايات الجمل
        sentences = []
        current = ""
        
        for char in text:
            current += char
            if char in ".!?؟" and len(current) > 100:
                sentences.append(current.strip())
                current = ""
        
        if current.strip():
            sentences.append(current.strip())
        
        # تجميع لـ chunks
        chunks = []
        current_chunk = ""
        
        for sentence in sentences:
            if len(current_chunk) + len(sentence) < self.MAX_TEXT_LENGTH - 100:
                current_chunk += " " + sentence
            else:
                if current_chunk:
                    chunks.append(current_chunk.strip())
                current_chunk = sentence
        
        if current_chunk:
            chunks.append(current_chunk.strip())
        
        return chunks
    
    # ═══════════════════════════════════════════════════════════════
    # API Call
    # ═══════════════════════════════════════════════════════════════
    def _call_api(
        self,
        text: str,
        voice: str,
        model: str,
        voice_tone: str = "intense",
    ) -> Optional[bytes]:
        """استدعاء API."""
        url = f"{ElevenLabsConstants.BASE_URL}/text-to-speech/{voice}"
        
        # تخصيص الإعدادات حسب النبرة
        tone_settings = TONE_SETTINGS_MAP.get(voice_tone, {})
        stability = tone_settings.get("stability", self.stability)
        style = tone_settings.get("style", self.style)
        
        payload = {
            "text": text,
            "model_id": model,
            "voice_settings": {
                "stability": stability,
                "similarity_boost": self.similarity,
                "style": style,
                "use_speaker_boost": self.use_speaker_boost,
            },
        }
        
        response = self.session.post(
            url,
            json=payload,
            timeout=ElevenLabsConstants.REQUEST_TIMEOUT,
        )
        
        if response.status_code == 200:
            return response.content
        
        # معالجة الأخطاء
        self._handle_error(response)
        return None
    
    def _handle_error(self, response: requests.Response) -> None:
        """معالجة أخطاء API."""
        code = response.status_code
        
        if code == 401:
            raise RuntimeError("❌ مفتاح ElevenLabs غير صحيح")
        elif code == 422:
            raise RuntimeError(
                f"❌ بيانات غير صالحة: {response.text[:200]}"
            )
        elif code == 429:
            raise RuntimeError("❌ تجاوز الحد - Rate Limit")
        elif code == 402:
            raise RuntimeError("❌ Credits منتهية!")
        else:
            raise RuntimeError(
                f"HTTP {code}: {response.text[:200]}"
            )
    
    # ═══════════════════════════════════════════════════════════════
    # Override: text building with voice_tone
    # ═══════════════════════════════════════════════════════════════
    def generate_audio(
        self,
        script: dict,
        output_path: str,
        progress_callback=None,
    ) -> TTSResult:
        """Override لاستخدام voice_tone."""
        # إضافة voice_tone من أول مشهد
        first_scene = (script.get("scenes") or [{}])[0]
        voice_tone = first_scene.get("voice_tone", "intense")
        
        # حفظ في kwargs للاستخدام في _generate_audio_data
        # (نمرر عبر التعديل المؤقت)
        original_method = self._generate_audio_data
        
        def wrapped(text, voice, **kwargs):
            return original_method(text, voice, voice_tone=voice_tone, **kwargs)
        
        self._generate_audio_data = wrapped
        
        try:
            result = super().generate_audio(script, output_path, progress_callback)
            # إضافة تقدير التكلفة
            result.cost_estimate = (
                result.text_length * ElevenLabsConstants.COST_PER_CHAR
            )
            return result
        finally:
            self._generate_audio_data = original_method
    
    # ═══════════════════════════════════════════════════════════════
    # User Info & Voices
    # ═══════════════════════════════════════════════════════════════
    def get_user_info(self) -> dict:
        """معلومات الحساب."""
        try:
            response = self.session.get(
                f"{ElevenLabsConstants.BASE_URL}/user",
                timeout=30,
            )
            if response.status_code == 200:
                return response.json()
        except Exception as e:
            logger.error(f"❌ فشل جلب المعلومات: {e}")
        return {}
    
    def get_remaining_chars(self) -> Optional[int]:
        """الأحرف المتبقية."""
        info = self.get_user_info()
        try:
            sub = info.get("subscription", {})
            return sub.get("character_limit", 0) - sub.get("character_count", 0)
        except Exception:
            return None
    
    def list_account_voices(self) -> list:
        """جلب الأصوات في الحساب."""
        try:
            response = self.session.get(
                f"{ElevenLabsConstants.BASE_URL}/voices",
                timeout=30,
            )
            if response.status_code == 200:
                return response.json().get("voices", [])
        except Exception as e:
            logger.error(f"❌ فشل جلب الأصوات: {e}")
        return []
    
    @staticmethod
    def list_voices() -> dict[str, VoiceInfo]:
        """الأصوات الافتراضية."""
        return ELEVENLABS_VOICES.copy()
    
    # ═══════════════════════════════════════════════════════════════
    # Cleanup
    # ═══════════════════════════════════════════════════════════════
    def close(self):
        """إغلاق الـ session."""
        if hasattr(self, 'session'):
            self.session.close()
    
    def __del__(self):
        self.close()
    
    def print_stats(self):
        """طباعة الإحصائيات."""
        print(self.stats.summary())
        
        remaining = self.get_remaining_chars()
        if remaining is not None:
            print(f"   • Remaining credits: {remaining:,} chars")


# ═══════════════════════════════════════════════════════════════════
# اختبار سريع
# ═══════════════════════════════════════════════════════════════════
if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s | %(levelname)s | %(message)s"
    )
    
    print("=" * 60)
    print("🎙️ ElevenLabs TTS v2.0 Test")
    print("=" * 60)
    
    try:
        tts = ElevenLabsTTS(cache_enabled=True)
        
        # معلومات الحساب
        remaining = tts.get_remaining_chars()
        if remaining is not None:
            print(f"\n💰 Remaining: {remaining:,} characters")
        
        # اختبار
        test_script = {
            "scenes": [
                {
                    "text": "مرحباً بكم في عالم الإبداع.",
                    "pause_after": 0.5,
                    "voice_tone": "intense",
                },
                {
                    "text": "هنا تبدأ القصة.",
                    "pause_after": 0.8,
                    "voice_tone": "curious",
                },
            ],
            "cta": "تابعونا للمزيد!",
            "music_mood": "motivation",
        }
        
        result = tts.generate_audio(test_script, "test_elevenlabs.mp3")
        
        print(f"\n📊 Result:")
        print(f"   Status: {result.status.value}")
        print(f"   Success: {result.success}")
        print(f"   Voice: {result.voice_used[:8]}...")
        print(f"   Chars: {result.text_length}")
        print(f"   Cost: ~${result.cost_estimate:.6f}")
        print(f"   Cached: {result.cached}")
        
        print()
        tts.print_stats()
        
    except ValueError as e:
        print(f"\n❌ {e}")
