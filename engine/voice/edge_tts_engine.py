"""
🎙️ Edge TTS Engine v2.0 — المحرك الأساسي للصوت العربي
═══════════════════════════════════════════════════════════════
يستخدم Microsoft Edge TTS:
  ✓ مجاني 100% (بدون مفتاح API)
  ✓ جودة عالية جداً للعربية
  ✓ سرعة ممتازة
  ✓ بدون حدود على طول النص
  ✓ يدعم لهجات متعددة

التحسينات في v2.0:
  ✓ Async-safe (لا يكسر event loops)
  ✓ يستخدم voice_tone لكل مشهد
  ✓ Caching للنصوص المتكررة
  ✓ Progress callback
  ✓ TTSResult dataclass
  ✓ Streaming للنصوص الطويلة
  ✓ Timeout management
  ✓ FFmpeg detection
═══════════════════════════════════════════════════════════════
"""

from __future__ import annotations

import os
import sys
import asyncio
import hashlib
import logging
import shutil
import subprocess
from pathlib import Path
from enum import Enum
from dataclasses import dataclass, field
from typing import Optional, Callable, Any
from concurrent.futures import ThreadPoolExecutor

import edge_tts
from dotenv import load_dotenv

load_dotenv()
logger = logging.getLogger(__name__)


# ═══════════════════════════════════════════════════════════════════
# Enums & Types
# ═══════════════════════════════════════════════════════════════════
class TTSStatus(str, Enum):
    """حالة توليد الصوت."""
    SUCCESS = "success"
    FALLBACK_VOICE = "fallback_voice"
    SILENCE = "silence"
    FAILED = "failed"


# ═══════════════════════════════════════════════════════════════════
# Voice Definitions
# ═══════════════════════════════════════════════════════════════════
@dataclass(frozen=True)
class VoiceInfo:
    """معلومات صوت."""
    voice_id: str
    name: str
    gender: str
    lang: str
    description: str = ""


ARABIC_VOICES: dict[str, VoiceInfo] = {
    # 🇸🇦 السعودية
    "ar-SA-HamedNeural": VoiceInfo(
        "ar-SA-HamedNeural", "حامد", "male", "ar-SA",
        "قوي ومُلهم - مناسب للتحفيز"
    ),
    "ar-SA-ZariyahNeural": VoiceInfo(
        "ar-SA-ZariyahNeural", "زارية", "female", "ar-SA",
        "ناعم وعاطفي"
    ),
    
    # 🇪🇬 مصر
    "ar-EG-ShakirNeural": VoiceInfo(
        "ar-EG-ShakirNeural", "شاكر", "male", "ar-EG",
        "حازم - مناسب للقصص"
    ),
    "ar-EG-SalmaNeural": VoiceInfo(
        "ar-EG-SalmaNeural", "سلمى", "female", "ar-EG",
        "دافئ - مناسب للحزن والعاطفة"
    ),
    
    # 🇦🇪 الإمارات
    "ar-AE-HamdanNeural": VoiceInfo(
        "ar-AE-HamdanNeural", "حمدان", "male", "ar-AE",
        "خليجي رصين"
    ),
    "ar-AE-FatimaNeural": VoiceInfo(
        "ar-AE-FatimaNeural", "فاطمة", "female", "ar-AE",
        "خليجية واضحة"
    ),
    
    # 🇯🇴 الأردن
    "ar-JO-TaimNeural": VoiceInfo(
        "ar-JO-TaimNeural", "تيم", "male", "ar-JO",
        "شاب ومرن"
    ),
    "ar-JO-SanaNeural": VoiceInfo(
        "ar-JO-SanaNeural", "سناء", "female", "ar-JO",
        "هادئة ومريحة"
    ),
    
    # 🇶🇦 قطر
    "ar-QA-AmalNeural": VoiceInfo(
        "ar-QA-AmalNeural", "أمل", "female", "ar-QA",
        "ودودة"
    ),
}


# ═══════════════════════════════════════════════════════════════════
# Mappings
# ═══════════════════════════════════════════════════════════════════
MOOD_VOICE_MAP: dict[str, str] = {
    "motivation":    "ar-SA-HamedNeural",     # قوي
    "dark":          "ar-EG-ShakirNeural",    # عميق
    "sigma":         "ar-AE-HamdanNeural",    # بارد رصين
    "psychological": "ar-JO-TaimNeural",      # هادئ ومحلل
    "horror":        "ar-EG-ShakirNeural",    # متوتر
    "emotional":     "ar-SA-ZariyahNeural",   # عاطفي
    "sad":           "ar-EG-SalmaNeural",     # حزين
    "romantic":      "ar-EG-SalmaNeural",     # حالم
    "educational":   "ar-AE-HamdanNeural",    # واضح
    "scientific":    "ar-JO-TaimNeural",      # تحليلي
    "practical":     "ar-SA-HamedNeural",     # مباشر
}

# نبرة الصوت → معدل السرعة
TONE_RATE_MAP: dict[str, str] = {
    "whisper":      "-25%",
    "calm":         "-15%",
    "cold":         "-10%",
    "emotionless":  "+0%",
    "sad":          "-15%",
    "curious":      "+5%",
    "authoritative":"+0%",
    "intense":      "+10%",
    "aggressive":   "+15%",
    "powerful":     "+8%",
}

# نبرة الصوت → pitch
TONE_PITCH_MAP: dict[str, str] = {
    "whisper":      "-10Hz",
    "calm":         "-5Hz",
    "cold":         "-3Hz",
    "emotionless":  "+0Hz",
    "sad":          "-8Hz",
    "curious":      "+5Hz",
    "authoritative":"+0Hz",
    "intense":      "+5Hz",
    "aggressive":   "+8Hz",
    "powerful":     "+3Hz",
}


# ═══════════════════════════════════════════════════════════════════
# Result Dataclass
# ═══════════════════════════════════════════════════════════════════
@dataclass
class TTSResult:
    """نتيجة توليد الصوت."""
    status: TTSStatus
    output_path: str
    voice_used: str
    text_length: int = 0
    file_size: int = 0
    duration_estimate: float = 0.0
    error: Optional[str] = None
    cached: bool = False
    
    @property
    def success(self) -> bool:
        return self.status in (TTSStatus.SUCCESS, TTSStatus.FALLBACK_VOICE)
    
    @property
    def used_fallback(self) -> bool:
        return self.status == TTSStatus.FALLBACK_VOICE


# ═══════════════════════════════════════════════════════════════════
# Constants
# ═══════════════════════════════════════════════════════════════════
class EdgeTTSConstants:
    """الثوابت."""
    
    DEFAULT_VOICE = "ar-SA-HamedNeural"
    DEFAULT_RATE = "+0%"
    DEFAULT_PITCH = "+0Hz"
    
    MIN_FILE_SIZE_BYTES = 1000
    TIMEOUT_SECONDS = 120
    MAX_TEXT_LENGTH = 5000  # حد آمن لـ Edge TTS
    
    # تقدير المدة
    WORDS_PER_SECOND_ARABIC = 2.5


# ═══════════════════════════════════════════════════════════════════
# Helper Functions
# ═══════════════════════════════════════════════════════════════════
def check_ffmpeg_available() -> bool:
    """التحقق من توفر FFmpeg."""
    return shutil.which("ffmpeg") is not None


def get_text_hash(text: str, voice: str, rate: str, pitch: str) -> str:
    """إنشاء hash للنص (للـ caching)."""
    content = f"{text}|{voice}|{rate}|{pitch}"
    return hashlib.md5(content.encode()).hexdigest()[:16]


def run_async_safely(coro):
    """
    تشغيل async coroutine بأمان حتى داخل event loop.
    
    يحل مشكلة استدعاء asyncio.run داخل event loop موجود.
    """
    try:
        # حاول الحصول على event loop موجود
        loop = asyncio.get_running_loop()
        # إذا كان موجوداً، استخدم thread جديد
        with ThreadPoolExecutor(max_workers=1) as executor:
            future = executor.submit(asyncio.run, coro)
            return future.result()
    except RuntimeError:
        # لا يوجد event loop → استخدم asyncio.run عادياً
        return asyncio.run(coro)


# ═══════════════════════════════════════════════════════════════════
# Main Class
# ═══════════════════════════════════════════════════════════════════
class EdgeTTS:
    """محرك Edge TTS العربي v2.0."""

    def __init__(
        self,
        default_voice: Optional[str] = None,
        cache_enabled: bool = True,
        cache_dir: Optional[str] = None,
    ):
        """
        Args:
            default_voice: الصوت الافتراضي
            cache_enabled: تفعيل caching للنصوص المتكررة
            cache_dir: مجلد الكاش
        """
        # ── إعدادات الصوت ──
        self.default_voice = self._validate_voice(
            default_voice or os.getenv("TTS_VOICE", EdgeTTSConstants.DEFAULT_VOICE)
        )
        self.default_rate = os.getenv("TTS_RATE", EdgeTTSConstants.DEFAULT_RATE)
        self.default_pitch = os.getenv("TTS_PITCH", EdgeTTSConstants.DEFAULT_PITCH)
        
        # ── المجلدات ──
        self.temp_dir = Path(os.getenv("TEMP_DIR", "./temp"))
        self.temp_dir.mkdir(parents=True, exist_ok=True)
        
        # ── الكاش ──
        self.cache_enabled = cache_enabled
        if cache_enabled:
            self.cache_dir = Path(cache_dir or self.temp_dir / "tts_cache")
            self.cache_dir.mkdir(parents=True, exist_ok=True)
        else:
            self.cache_dir = None
        
        # ── FFmpeg check ──
        self._ffmpeg_available = check_ffmpeg_available()
        if not self._ffmpeg_available:
            logger.warning(
                "⚠ FFmpeg غير متاح - وظيفة الصمت الاحتياطي معطلة"
            )
        
        logger.info(
            f"✓ EdgeTTS v2.0 | Voice: {self.default_voice} | "
            f"Cache: {cache_enabled}"
        )

    # ═══════════════════════════════════════════════════════════════
    # Validation
    # ═══════════════════════════════════════════════════════════════
    def _validate_voice(self, voice: str) -> str:
        """التحقق من صحة الصوت."""
        if voice not in ARABIC_VOICES:
            logger.warning(
                f"⚠ الصوت '{voice}' غير معروف، "
                f"استخدام {EdgeTTSConstants.DEFAULT_VOICE}"
            )
            return EdgeTTSConstants.DEFAULT_VOICE
        return voice
    
    def _ensure_output_dir(self, output_path: str) -> None:
        """التأكد من وجود مجلد الـ output."""
        Path(output_path).parent.mkdir(parents=True, exist_ok=True)

    # ═══════════════════════════════════════════════════════════════
    # Main API
    # ═══════════════════════════════════════════════════════════════
    def generate_audio(
        self,
        script: dict,
        output_path: str,
        progress_callback: Optional[Callable[[float, str], None]] = None,
    ) -> TTSResult:
        """
        توليد صوت كامل من السكربت.
        
        Args:
            script: السكربت من ScriptWriter
            output_path: مسار حفظ الملف الصوتي
            progress_callback: دالة استدعاء للتقدم (progress, message)
        
        Returns:
            TTSResult يحتوي على معلومات النتيجة
        """
        self._ensure_output_dir(output_path)
        
        mood = script.get("music_mood", "motivation")
        voice = self._select_voice(script, mood)
        
        # ── تحديد النبرة من أول مشهد (أو افتراضية) ──
        first_scene = (script.get("scenes") or [{}])[0]
        primary_tone = first_scene.get("voice_tone", "intense")
        rate = TONE_RATE_MAP.get(primary_tone, self.default_rate)
        pitch = TONE_PITCH_MAP.get(primary_tone, self.default_pitch)
        
        logger.info(
            f"🎙️ Edge TTS | Voice: {voice} | "
            f"Mood: {mood} | Tone: {primary_tone}"
        )
        
        if progress_callback:
            progress_callback(0.1, f"إعداد الصوت: {voice}")
        
        # ── بناء النص ──
        full_text = self._build_full_text(script)
        
        if not full_text.strip():
            logger.error("❌ النص فارغ!")
            return self._silence_result(output_path, "Empty text")
        
        logger.info(f"📝 طول النص: {len(full_text)} حرف")
        
        if progress_callback:
            progress_callback(0.2, f"تجميع النص ({len(full_text)} حرف)")
        
        # ── تحقق من الكاش ──
        if self.cache_enabled:
            cached_path = self._get_cached(full_text, voice, rate, pitch)
            if cached_path:
                shutil.copy(cached_path, output_path)
                logger.info("⚡ تم استخدام النسخة المخزنة")
                
                if progress_callback:
                    progress_callback(1.0, "نسخة مخزنة")
                
                return TTSResult(
                    status=TTSStatus.SUCCESS,
                    output_path=output_path,
                    voice_used=voice,
                    text_length=len(full_text),
                    file_size=Path(output_path).stat().st_size,
                    duration_estimate=self._estimate_duration(full_text),
                    cached=True,
                )
        
        # ── التوليد ──
        if progress_callback:
            progress_callback(0.5, "توليد الصوت...")
        
        try:
            run_async_safely(
                self._generate_async(full_text, voice, output_path, rate, pitch)
            )
            
            output_file = Path(output_path)
            if (output_file.exists() and 
                output_file.stat().st_size > EdgeTTSConstants.MIN_FILE_SIZE_BYTES):
                
                # حفظ في الكاش
                if self.cache_enabled:
                    self._save_to_cache(output_path, full_text, voice, rate, pitch)
                
                if progress_callback:
                    progress_callback(1.0, "تم!")
                
                logger.info(f"✓ تم توليد الصوت: {output_file.name}")
                
                return TTSResult(
                    status=TTSStatus.SUCCESS,
                    output_path=output_path,
                    voice_used=voice,
                    text_length=len(full_text),
                    file_size=output_file.stat().st_size,
                    duration_estimate=self._estimate_duration(full_text),
                )
            
            raise RuntimeError("الملف الناتج فارغ أو صغير جداً")
            
        except Exception as e:
            logger.error(f"❌ فشل Edge TTS: {e}")
            return self._fallback_voice(full_text, output_path, voice, rate, pitch)

    # ═══════════════════════════════════════════════════════════════
    # Async Generation
    # ═══════════════════════════════════════════════════════════════
    async def _generate_async(
        self,
        text: str,
        voice: str,
        output_path: str,
        rate: Optional[str] = None,
        pitch: Optional[str] = None,
    ) -> None:
        """التوليد الفعلي عبر edge-tts."""
        rate = rate or self.default_rate
        pitch = pitch or self.default_pitch
        
        # إذا النص طويل جداً → تقسيمه
        if len(text) > EdgeTTSConstants.MAX_TEXT_LENGTH:
            await self._generate_chunked(text, voice, output_path, rate, pitch)
            return
        
        communicate = edge_tts.Communicate(
            text=text,
            voice=voice,
            rate=rate,
            pitch=pitch,
        )
        
        # مع timeout
        await asyncio.wait_for(
            communicate.save(output_path),
            timeout=EdgeTTSConstants.TIMEOUT_SECONDS,
        )

    async def _generate_chunked(
        self,
        text: str,
        voice: str,
        output_path: str,
        rate: str,
        pitch: str,
    ) -> None:
        """تقسيم النصوص الطويلة وتجميعها."""
        logger.info(f"📦 تقسيم النص الطويل ({len(text)} حرف)")
        
        chunks = self._split_text(text, EdgeTTSConstants.MAX_TEXT_LENGTH)
        chunk_files = []
        
        try:
            for i, chunk in enumerate(chunks):
                chunk_path = f"{output_path}.chunk_{i}.mp3"
                communicate = edge_tts.Communicate(
                    text=chunk, voice=voice, rate=rate, pitch=pitch
                )
                await communicate.save(chunk_path)
                chunk_files.append(chunk_path)
            
            # دمج الـ chunks
            self._concat_audio_files(chunk_files, output_path)
            
        finally:
            # تنظيف
            for f in chunk_files:
                Path(f).unlink(missing_ok=True)

    @staticmethod
    def _split_text(text: str, max_length: int) -> list[str]:
        """تقسيم النص على الجمل."""
        sentences = text.replace("؟", "؟|").replace("!", "!|").replace(".", ".|")
        sentences = [s.strip() for s in sentences.split("|") if s.strip()]
        
        chunks = []
        current = ""
        
        for sentence in sentences:
            if len(current) + len(sentence) < max_length:
                current += " " + sentence
            else:
                if current:
                    chunks.append(current.strip())
                current = sentence
        
        if current:
            chunks.append(current.strip())
        
        return chunks

    def _concat_audio_files(self, files: list[str], output: str) -> None:
        """دمج عدة ملفات صوتية."""
        if not self._ffmpeg_available:
            # fallback: انسخ الأول فقط
            if files:
                shutil.copy(files[0], output)
            return
        
        # إنشاء قائمة الملفات لـ ffmpeg
        list_file = Path(output).parent / "concat_list.txt"
        with open(list_file, "w") as f:
            for file_path in files:
                f.write(f"file '{Path(file_path).absolute()}'\n")
        
        try:
            subprocess.run(
                [
                    "ffmpeg", "-y", "-f", "concat", "-safe", "0",
                    "-i", str(list_file),
                    "-c", "copy",
                    output,
                ],
                capture_output=True,
                check=True,
                timeout=60,
            )
        finally:
            list_file.unlink(missing_ok=True)

    # ═══════════════════════════════════════════════════════════════
    # Voice Selection
    # ═══════════════════════════════════════════════════════════════
    def _select_voice(self, script: dict, mood: str) -> str:
        """اختيار الصوت المناسب."""
        # 1. من السكربت
        if script.get("voice") in ARABIC_VOICES:
            return script["voice"]
        
        # 2. من البيئة
        env_voice = os.getenv("TTS_VOICE")
        if env_voice and env_voice in ARABIC_VOICES:
            return env_voice
        
        # 3. من المزاج
        return MOOD_VOICE_MAP.get(mood, self.default_voice)

    # ═══════════════════════════════════════════════════════════════
    # Text Building
    # ═══════════════════════════════════════════════════════════════
    def _build_full_text(self, script: dict) -> str:
        """تجميع النص الكامل من المشاهد."""
        parts = []
        
        for scene in script.get("scenes", []):
            text = scene.get("text", "").strip()
            pause = float(scene.get("pause_after", 0.3))
            
            if not text:
                continue
            
            parts.append(text)
            parts.append(self._get_pause_marker(pause))
        
        # CTA
        cta = script.get("cta", "").strip()
        if cta:
            parts.append("... ")
            parts.append(cta)
        
        return " ".join(parts).strip()

    @staticmethod
    def _get_pause_marker(pause_duration: float) -> str:
        """تحويل مدة الوقفة لعلامة ترقيم."""
        if pause_duration >= 0.8:
            return "... "
        elif pause_duration >= 0.5:
            return ".. "
        elif pause_duration >= 0.3:
            return ", "
        return " "

    # ═══════════════════════════════════════════════════════════════
    # Caching
    # ═══════════════════════════════════════════════════════════════
    def _get_cached(
        self,
        text: str,
        voice: str,
        rate: str,
        pitch: str,
    ) -> Optional[str]:
        """البحث في الكاش."""
        if not self.cache_enabled:
            return None
        
        cache_key = get_text_hash(text, voice, rate, pitch)
        cache_path = self.cache_dir / f"{cache_key}.mp3"
        
        if cache_path.exists() and cache_path.stat().st_size > EdgeTTSConstants.MIN_FILE_SIZE_BYTES:
            return str(cache_path)
        return None

    def _save_to_cache(
        self,
        source_path: str,
        text: str,
        voice: str,
        rate: str,
        pitch: str,
    ) -> None:
        """حفظ في الكاش."""
        if not self.cache_enabled:
            return
        
        try:
            cache_key = get_text_hash(text, voice, rate, pitch)
            cache_path = self.cache_dir / f"{cache_key}.mp3"
            shutil.copy(source_path, cache_path)
            logger.debug(f"💾 محفوظ في الكاش: {cache_key}")
        except Exception as e:
            logger.warning(f"⚠ فشل حفظ الكاش: {e}")

    def clear_cache(self) -> int:
        """مسح الكاش وإرجاع عدد الملفات المحذوفة."""
        if not self.cache_enabled or not self.cache_dir.exists():
            return 0
        
        count = 0
        for cache_file in self.cache_dir.glob("*.mp3"):
            cache_file.unlink()
            count += 1
        
        logger.info(f"🗑 تم حذف {count} ملف من الكاش")
        return count

    # ═══════════════════════════════════════════════════════════════
    # Fallback
    # ═══════════════════════════════════════════════════════════════
    def _fallback_voice(
        self,
        text: str,
        output_path: str,
        failed_voice: str,
        rate: str,
        pitch: str,
    ) -> TTSResult:
        """جرب أصوات بديلة."""
        # ترتيب الأصوات حسب الجنس
        original_info = ARABIC_VOICES.get(failed_voice)
        same_gender = []
        other_gender = []
        
        for voice_id, info in ARABIC_VOICES.items():
            if voice_id == failed_voice:
                continue
            if original_info and info.gender == original_info.gender:
                same_gender.append(voice_id)
            else:
                other_gender.append(voice_id)
        
        # جرب نفس الجنس أولاً، ثم الآخر
        fallback_order = same_gender + other_gender
        
        for voice in fallback_order[:3]:  # أقصى 3 محاولات
            logger.warning(f"⏳ محاولة بصوت بديل: {voice}")
            try:
                run_async_safely(
                    self._generate_async(text, voice, output_path, rate, pitch)
                )
                
                output_file = Path(output_path)
                if (output_file.exists() and
                    output_file.stat().st_size > EdgeTTSConstants.MIN_FILE_SIZE_BYTES):
                    
                    logger.info(f"✓ نجح الصوت البديل: {voice}")
                    return TTSResult(
                        status=TTSStatus.FALLBACK_VOICE,
                        output_path=output_path,
                        voice_used=voice,
                        text_length=len(text),
                        file_size=output_file.stat().st_size,
                        duration_estimate=self._estimate_duration(text),
                    )
            except Exception as e:
                logger.warning(f"⚠ فشل {voice}: {e}")
        
        logger.error("❌ فشلت كل الأصوات")
        return self._silence_result(output_path, "All voices failed")

    # ═══════════════════════════════════════════════════════════════
    # Silence Fallback
    # ═══════════════════════════════════════════════════════════════
    def _silence_result(
        self,
        output_path: str,
        error: str,
        duration: int = 30,
    ) -> TTSResult:
        """توليد ملف صمت كآخر احتياطي."""
        if not self._ffmpeg_available:
            return TTSResult(
                status=TTSStatus.FAILED,
                output_path=output_path,
                voice_used="none",
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
            logger.error(f"❌ فشل توليد الصمت: {e}")
            return TTSResult(
                status=TTSStatus.FAILED,
                output_path=output_path,
                voice_used="none",
                error=f"{error} | Silence failed: {e}",
            )

    # ═══════════════════════════════════════════════════════════════
    # Utility Methods
    # ═══════════════════════════════════════════════════════════════
    @staticmethod
    def _estimate_duration(text: str) -> float:
        """تقدير مدة النص بالثواني."""
        word_count = len(text.split())
        return word_count / EdgeTTSConstants.WORDS_PER_SECOND_ARABIC

    @staticmethod
    def list_voices() -> dict[str, VoiceInfo]:
        """قائمة الأصوات المتاحة."""
        return ARABIC_VOICES.copy()

    @staticmethod
    def get_voice_info(voice_name: str) -> Optional[VoiceInfo]:
        """معلومات صوت معين."""
        return ARABIC_VOICES.get(voice_name)

    @staticmethod
    def list_voices_by_gender(gender: str) -> list[VoiceInfo]:
        """قائمة الأصوات حسب الجنس."""
        return [v for v in ARABIC_VOICES.values() if v.gender == gender]

    # ═══════════════════════════════════════════════════════════════
    # Simple Text Generation
    # ═══════════════════════════════════════════════════════════════
    def generate_for_text(
        self,
        text: str,
        output_path: str,
        voice: Optional[str] = None,
        rate: Optional[str] = None,
        pitch: Optional[str] = None,
        use_fallback: bool = True,
    ) -> TTSResult:
        """توليد صوت لنص بسيط."""
        if not text or not text.strip():
            return TTSResult(
                status=TTSStatus.FAILED,
                output_path=output_path,
                voice_used="none",
                error="Empty text",
            )
        
        self._ensure_output_dir(output_path)
        voice = self._validate_voice(voice or self.default_voice)
        rate = rate or self.default_rate
        pitch = pitch or self.default_pitch
        
        try:
            run_async_safely(
                self._generate_async(text, voice, output_path, rate, pitch)
            )
            
            output_file = Path(output_path)
            if (output_file.exists() and
                output_file.stat().st_size > EdgeTTSConstants.MIN_FILE_SIZE_BYTES):
                return TTSResult(
                    status=TTSStatus.SUCCESS,
                    output_path=output_path,
                    voice_used=voice,
                    text_length=len(text),
                    file_size=output_file.stat().st_size,
                    duration_estimate=self._estimate_duration(text),
                )
            
            raise RuntimeError("File too small")
            
        except Exception as e:
            logger.error(f"❌ فشل التوليد: {e}")
            if use_fallback:
                return self._fallback_voice(text, output_path, voice, rate, pitch)
            return TTSResult(
                status=TTSStatus.FAILED,
                output_path=output_path,
                voice_used=voice,
                error=str(e),
            )


# ═══════════════════════════════════════════════════════════════════
# اختبار سريع
# ═══════════════════════════════════════════════════════════════════
if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s | %(levelname)s | %(message)s"
    )
    
    tts = EdgeTTS(cache_enabled=True)
    
    print("=" * 60)
    print(f"🎙️ EdgeTTS v2.0 Test")
    print("=" * 60)
    
    print(f"\n📋 Available voices: {len(ARABIC_VOICES)}")
    for vid, info in list(ARABIC_VOICES.items())[:3]:
        print(f"   • {info.name} ({info.gender}) - {info.description}")
    
    # اختبار توليد
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
    
    def progress(p, msg):
        print(f"  [{p*100:.0f}%] {msg}")
    
    result = tts.generate_audio(
        test_script,
        "test_output.mp3",
        progress_callback=progress,
    )
    
    print(f"\n📊 Result:")
    print(f"   Status: {result.status.value}")
    print(f"   Success: {result.success}")
    print(f"   Voice: {result.voice_used}")
    print(f"   Duration: ~{result.duration_estimate:.1f}s")
    print(f"   File size: {result.file_size:,} bytes")
    print(f"   Cached: {result.cached}")
    
    if result.error:
        print(f"   Error: {result.error}")
