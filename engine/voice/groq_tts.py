"""
🎙️ Groq TTS Engine v2.0 — Pro
═══════════════════════════════════════════════════════════════
الموديل: canopylabs/orpheus-arabic-saudi
الأصوات: fahad, sultan, noura, lulwa

⚠️ حد المحرك: 200 حرف لكل طلب (نقسم تلقائياً)

التحسينات v2.0:
  ✓ يرث من BaseTTS
  ✓ TTSResult dataclass
  ✓ Parallel chunk processing
  ✓ Caching ذكي
  ✓ يستخدم EdgeTTS class الموجود
  ✓ Cleanup تلقائي للملفات المؤقتة
  ✓ Stats tracking
  ✓ pydub بدل ffmpeg للدمج
═══════════════════════════════════════════════════════════════
"""

from __future__ import annotations

import os
import time
import shutil
import logging
import tempfile
import subprocess
from pathlib import Path
from dataclasses import dataclass, field
from concurrent.futures import ThreadPoolExecutor, as_completed
from threading import Lock
from typing import Optional, Callable

from groq import Groq
from dotenv import load_dotenv

from engine.video.voice.base_tts import (
    BaseTTS, TTSResult, TTSStatus, VoiceInfo,
    TTSConstants, estimate_duration
)

load_dotenv()
logger = logging.getLogger(__name__)


# ═══════════════════════════════════════════════════════════════════
# Voices
# ═══════════════════════════════════════════════════════════════════
GROQ_VOICES: dict[str, VoiceInfo] = {
    "fahad": VoiceInfo(
        "fahad", "Fahad", "male", "ar-SA",
        "صوت ذكوري عميق - تحفيزي",
        provider="groq"
    ),
    "sultan": VoiceInfo(
        "sultan", "Sultan", "male", "ar-SA",
        "صوت ذكوري رسمي - دراماتيكي",
        provider="groq"
    ),
    "noura": VoiceInfo(
        "noura", "Noura", "female", "ar-SA",
        "صوت أنثوي - عاطفي",
        provider="groq"
    ),
    "lulwa": VoiceInfo(
        "lulwa", "Lulwa", "female", "ar-SA",
        "صوت أنثوي - دافئ",
        provider="groq"
    ),
}


# ═══════════════════════════════════════════════════════════════════
# Mappings
# ═══════════════════════════════════════════════════════════════════
MOOD_VOICE_MAP: dict[str, str] = {
    "epic":          "fahad",
    "motivational":  "fahad",
    "motivation":    "fahad",
    "dramatic":      "sultan",
    "dark":          "sultan",
    "sigma":         "sultan",
    "psychological": "sultan",
    "horror":        "sultan",
    "emotional":     "noura",
    "sad":           "noura",
    "romantic":      "lulwa",
    "calm":          "lulwa",
    "educational":   "sultan",
    "scientific":    "sultan",
}


# ═══════════════════════════════════════════════════════════════════
# Stats
# ═══════════════════════════════════════════════════════════════════
@dataclass
class GroqTTSStats:
    """إحصائيات."""
    total_chunks: int = 0
    successful_chunks: int = 0
    failed_chunks: int = 0
    cached_chunks: int = 0
    fallback_used: int = 0
    total_chars: int = 0
    total_time: float = 0.0
    
    @property
    def success_rate(self) -> float:
        if self.total_chunks == 0:
            return 0.0
        return (self.successful_chunks / self.total_chunks) * 100
    
    def summary(self) -> str:
        return (
            f"📊 Groq TTS Stats:\n"
            f"   • Chunks: {self.successful_chunks}/{self.total_chunks} "
            f"({self.success_rate:.1f}%)\n"
            f"   • Cached: {self.cached_chunks}\n"
            f"   • Failed: {self.failed_chunks}\n"
            f"   • Fallback used: {self.fallback_used}\n"
            f"   • Chars: {self.total_chars:,}\n"
            f"   • Time: {self.total_time:.1f}s"
        )


# ═══════════════════════════════════════════════════════════════════
# Constants
# ═══════════════════════════════════════════════════════════════════
class GroqTTSConstants:
    """ثوابت Groq TTS."""
    
    ARABIC_MODEL = "playai-tts-arabic"
    
    MAX_CHARS = 190  # حد الموديل 200، نترك هامش
    
    DEFAULT_VOICE = "fahad"
    
    MAX_RETRIES = 2
    RETRY_DELAY = 2
    REQUEST_TIMEOUT = 60
    
    PARALLEL_CHUNKS = 3
    
    # ملف صمت
    SILENCE_DURATION = 30


# ═══════════════════════════════════════════════════════════════════
# Main Class
# ═══════════════════════════════════════════════════════════════════
class GroqTTS(BaseTTS):
    """محرك Groq TTS v2.0."""
    
    PROVIDER_NAME = "groq_tts"
    PAUSE_FORMAT = "simple"
    MAX_TEXT_LENGTH = GroqTTSConstants.MAX_CHARS
    
    def __init__(
        self,
        api_key: Optional[str] = None,
        cache_enabled: bool = True,
        parallel_chunks: int = GroqTTSConstants.PARALLEL_CHUNKS,
        enable_edge_fallback: bool = True,
    ):
        """
        Args:
            api_key: مفتاح Groq
            cache_enabled: تفعيل الكاش
            parallel_chunks: عدد الـ chunks المتوازية
            enable_edge_fallback: استخدام EdgeTTS كاحتياطي
        """
        super().__init__(cache_enabled=cache_enabled)
        
        self.api_key = api_key or os.getenv("GROQ_API_KEY")
        if not self.api_key:
            raise ValueError("❌ GROQ_API_KEY غير موجود")
        
        self.client = Groq(api_key=self.api_key)
        self.parallel_chunks = parallel_chunks
        self.enable_edge_fallback = enable_edge_fallback
        
        # pydub for merging
        try:
            from pydub import AudioSegment
            self._AudioSegment = AudioSegment
        except ImportError:
            raise RuntimeError("❌ pydub غير مثبت: pip install pydub")
        
        # Edge TTS for fallback
        self._edge_tts = None
        if enable_edge_fallback:
            try:
                from engine.video.voice.edge_tts_engine import EdgeTTS
                self._edge_tts = EdgeTTS(cache_enabled=cache_enabled)
                logger.info("✓ Edge TTS fallback enabled")
            except Exception as e:
                logger.warning(f"⚠ Edge TTS fallback غير متاح: {e}")
        
        # Stats
        self.stats = GroqTTSStats()
        self._stats_lock = Lock()
        
        logger.info(
            f"🎙️ Groq TTS v2.0 | Model: {GroqTTSConstants.ARABIC_MODEL} | "
            f"Parallel: {parallel_chunks}"
        )
    
    # ═══════════════════════════════════════════════════════════════
    # Voice Selection (Override)
    # ═══════════════════════════════════════════════════════════════
    def _select_voice_for_mood(self, mood: str) -> str:
        """اختيار الصوت حسب المزاج."""
        return MOOD_VOICE_MAP.get(mood, GroqTTSConstants.DEFAULT_VOICE)
    
    # ═══════════════════════════════════════════════════════════════
    # Main Generation (Override)
    # ═══════════════════════════════════════════════════════════════
    def generate_audio(
        self,
        script: dict,
        output_path: str,
        progress_callback: Optional[Callable[[float, str], None]] = None,
    ) -> TTSResult:
        """توليد الصوت من السكربت."""
        start_time = time.time()
        self._ensure_output_dir(output_path)
        
        # الإعدادات
        mood = script.get("music_mood", "motivation")
        voice = self._select_voice(script, mood)
        
        # بناء الـ chunks
        chunks = self._build_chunks(script)
        
        if not chunks:
            return TTSResult(
                status=TTSStatus.FAILED,
                output_path=output_path,
                voice_used=voice,
                error="No text to convert",
            )
        
        total_chars = sum(len(c) for c in chunks)
        logger.info(
            f"🎙️ Groq TTS | Voice: {voice} | "
            f"{len(chunks)} chunks | {total_chars} حرف"
        )
        
        if progress_callback:
            progress_callback(0.05, f"إعداد {len(chunks)} chunks")
        
        # توليد parallel
        temp_dir = Path(tempfile.mkdtemp(prefix="groq_tts_"))
        
        try:
            wav_files = self._generate_chunks_parallel(
                chunks=chunks,
                voice=voice,
                temp_dir=temp_dir,
                progress_callback=progress_callback,
            )
            
            if not wav_files:
                return self._silence_result(
                    output_path,
                    "All chunks failed",
                )
            
            # دمج
            if progress_callback:
                progress_callback(0.9, "دمج الملفات...")
            
            self._merge_audio_files(wav_files, output_path)
            
            # إحصائيات
            elapsed = time.time() - start_time
            with self._stats_lock:
                self.stats.total_time += elapsed
            
            file_size = Path(output_path).stat().st_size
            
            if progress_callback:
                progress_callback(1.0, "تم!")
            
            full_text = " ".join(chunks)
            
            logger.info(
                f"   ✅ تم! {len(wav_files)}/{len(chunks)} chunks "
                f"({file_size / 1024:.1f} KB) في {elapsed:.1f}s"
            )
            
            return TTSResult(
                status=TTSStatus.SUCCESS,
                output_path=output_path,
                voice_used=voice,
                text_length=total_chars,
                file_size=file_size,
                duration_estimate=estimate_duration(full_text),
            )
            
        except Exception as e:
            logger.error(f"❌ فشل التوليد: {e}")
            return self._silence_result(output_path, str(e))
        
        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)
    
    # ═══════════════════════════════════════════════════════════════
    # Chunking
    # ═══════════════════════════════════════════════════════════════
    def _build_chunks(self, script: dict) -> list[str]:
        """بناء chunks تحت حد الـ MAX_CHARS."""
        chunks = []
        current = ""
        max_chars = GroqTTSConstants.MAX_CHARS
        
        for scene in script.get("scenes", []):
            text = scene.get("text", "").strip()
            pause = float(scene.get("pause_after", 0.3))
            
            if not text:
                continue
            
            # اختر فاصل مناسب
            sep = "... " if pause >= 0.8 else (".. " if pause >= 0.5 else "، ")
            sentence = text + sep
            
            # إذا الجملة وحدها تتجاوز الحد، قسّمها
            if len(sentence) > max_chars:
                if current.strip():
                    chunks.append(current.strip())
                    current = ""
                for sub in self._split_long_text(sentence, max_chars):
                    chunks.append(sub.strip())
            elif len(current) + len(sentence) > max_chars:
                if current.strip():
                    chunks.append(current.strip())
                current = sentence
            else:
                current += sentence
        
        # CTA
        cta = script.get("cta", "").strip()
        if cta:
            if len(current) + len(cta) > max_chars:
                if current.strip():
                    chunks.append(current.strip())
                chunks.append(cta)
            else:
                current += " " + cta
        
        if current.strip():
            chunks.append(current.strip())
        
        return chunks if chunks else []
    
    def _split_long_text(self, text: str, max_chars: int) -> list[str]:
        """تقسيم النص الطويل على حدود الكلمات."""
        words = text.split()
        parts = []
        current = ""
        
        for word in words:
            if len(current) + len(word) + 1 > max_chars:
                if current:
                    parts.append(current.strip())
                current = word + " "
            else:
                current += word + " "
        
        if current.strip():
            parts.append(current.strip())
        
        return parts if parts else [text[:max_chars]]
    
    # ═══════════════════════════════════════════════════════════════
    # Parallel Chunk Generation
    # ═══════════════════════════════════════════════════════════════
    def _generate_chunks_parallel(
        self,
        chunks: list[str],
        voice: str,
        temp_dir: Path,
        progress_callback: Optional[Callable] = None,
    ) -> list[str]:
        """توليد chunks بشكل متوازٍ."""
        results: dict[int, Optional[str]] = {}
        completed_count = 0
        total = len(chunks)
        
        with ThreadPoolExecutor(max_workers=self.parallel_chunks) as executor:
            futures = {
                executor.submit(
                    self._generate_single_chunk,
                    chunk=chunk,
                    chunk_index=i,
                    voice=voice,
                    temp_dir=temp_dir,
                ): i
                for i, chunk in enumerate(chunks)
            }
            
            for future in as_completed(futures):
                idx = futures[future]
                try:
                    wav_path = future.result()
                    results[idx] = wav_path
                except Exception as e:
                    logger.error(f"   ❌ chunk {idx + 1}: {e}")
                    results[idx] = None
                
                completed_count += 1
                if progress_callback:
                    progress = 0.1 + (completed_count / total) * 0.75
                    progress_callback(
                        progress,
                        f"chunk {completed_count}/{total}"
                    )
        
        return [results[i] for i in range(total) if results.get(i)]
    
    def _generate_single_chunk(
        self,
        chunk: str,
        chunk_index: int,
        voice: str,
        temp_dir: Path,
    ) -> Optional[str]:
        """توليد chunk واحد مع caching و fallback."""
        # تحقق من الكاش
        if self.cache_enabled:
            cached = self._get_cached(chunk, voice)
            if cached:
                dest = temp_dir / f"chunk_{chunk_index:03d}.wav"
                shutil.copy(cached, dest)
                
                with self._stats_lock:
                    self.stats.cached_chunks += 1
                    self.stats.total_chunks += 1
                    self.stats.successful_chunks += 1
                
                logger.info(
                    f"   ⚡ chunk {chunk_index + 1} (cache): "
                    f"{chunk[:40]}..."
                )
                return str(dest)
        
        logger.info(
            f"   🎤 chunk {chunk_index + 1} "
            f"({len(chunk)} حرف): {chunk[:40]}..."
        )
        
        chunk_path = str(temp_dir / f"chunk_{chunk_index:03d}.wav")
        
        # محاولة Groq أولاً
        if self._try_groq(chunk, voice, chunk_path):
            if self.cache_enabled:
                self._save_to_cache(chunk_path, chunk, voice)
            
            with self._stats_lock:
                self.stats.total_chunks += 1
                self.stats.successful_chunks += 1
                self.stats.total_chars += len(chunk)
            
            return chunk_path
        
        # محاولة أصوات Groq البديلة
        for alt_voice in GROQ_VOICES.keys():
            if alt_voice == voice:
                continue
            if self._try_groq(chunk, alt_voice, chunk_path):
                if self.cache_enabled:
                    self._save_to_cache(chunk_path, chunk, alt_voice)
                
                with self._stats_lock:
                    self.stats.total_chunks += 1
                    self.stats.successful_chunks += 1
                    self.stats.total_chars += len(chunk)
                
                logger.info(f"      ✓ نجح بصوت بديل: {alt_voice}")
                return chunk_path
        
        # Fallback: Edge TTS
        if self.enable_edge_fallback and self._edge_tts:
            if self._try_edge_fallback(chunk, chunk_path):
                with self._stats_lock:
                    self.stats.total_chunks += 1
                    self.stats.successful_chunks += 1
                    self.stats.fallback_used += 1
                    self.stats.total_chars += len(chunk)
                
                logger.info(f"      ✓ نجح Edge TTS fallback")
                return chunk_path
        
        # فشل تام
        with self._stats_lock:
            self.stats.total_chunks += 1
            self.stats.failed_chunks += 1
        
        return None
    
    # ═══════════════════════════════════════════════════════════════
    # API Calls
    # ═══════════════════════════════════════════════════════════════
    def _try_groq(
        self,
        text: str,
        voice: str,
        output_path: str,
    ) -> bool:
        """محاولة Groq TTS."""
        for attempt in range(1, GroqTTSConstants.MAX_RETRIES + 1):
            try:
                if attempt > 1:
                    time.sleep(GroqTTSConstants.RETRY_DELAY)
                
                resp = self.client.audio.speech.create(
                    model=GroqTTSConstants.ARABIC_MODEL,
                    voice=voice,
                    input=text,
                    response_format="wav",
                )
                
                data = resp.read()
                if data and len(data) > 500:
                    with open(output_path, "wb") as f:
                        f.write(data)
                    return True
                
            except Exception as e:
                logger.warning(
                    f"      ⚠ Groq [{voice}] محاولة {attempt}: "
                    f"{str(e)[:80]}"
                )
        
        return False
    
    def _try_edge_fallback(self, text: str, output_path: str) -> bool:
        """محاولة Edge TTS كاحتياطي."""
        if not self._edge_tts:
            return False
        
        try:
            # استخدم Edge TTS مباشرة
            mp3_path = output_path.replace(".wav", ".mp3")
            result = self._edge_tts.generate_for_text(
                text=text,
                output_path=mp3_path,
                use_fallback=True,
            )
            
            if result.success:
                # تحويل لـ WAV
                self._convert_mp3_to_wav(mp3_path, output_path)
                Path(mp3_path).unlink(missing_ok=True)
                return Path(output_path).exists()
            
        except Exception as e:
            logger.warning(f"      ⚠ Edge fallback: {e}")
        
        return False
    
    # ═══════════════════════════════════════════════════════════════
    # Audio Operations
    # ═══════════════════════════════════════════════════════════════
    def _merge_audio_files(
        self,
        files: list[str],
        output_path: str,
    ) -> None:
        """دمج ملفات الصوت بـ pydub."""
        try:
            combined = self._AudioSegment.from_wav(files[0])
            
            for f in files[1:]:
                segment = self._AudioSegment.from_wav(f)
                combined += segment
            
            # Export
            if output_path.endswith(".mp3"):
                combined.export(
                    output_path,
                    format="mp3",
                    bitrate="192k",
                )
            else:
                combined.export(output_path, format="wav")
            
            logger.info(f"   ✓ دُمج {len(files)} ملف")
            
        except Exception as e:
            logger.error(f"   ❌ فشل الدمج: {e}")
            # Fallback: نسخ الأول
            shutil.copy(files[0], output_path)
    
    def _convert_mp3_to_wav(self, mp3_path: str, wav_path: str) -> None:
        """تحويل MP3 إلى WAV."""
        try:
            audio = self._AudioSegment.from_mp3(mp3_path)
            audio.export(wav_path, format="wav")
        except Exception as e:
            logger.error(f"❌ MP3→WAV failed: {e}")
    
    # ═══════════════════════════════════════════════════════════════
    # Required from BaseTTS (للتوافق)
    # ═══════════════════════════════════════════════════════════════
    def _generate_audio_data(
        self,
        text: str,
        voice: str,
        **kwargs,
    ) -> Optional[bytes]:
        """للنصوص البسيطة (single chunk)."""
        try:
            resp = self.client.audio.speech.create(
                model=GroqTTSConstants.ARABIC_MODEL,
                voice=voice,
                input=text[:GroqTTSConstants.MAX_CHARS],
                response_format="wav",
            )
            return resp.read()
        except Exception as e:
            logger.error(f"❌ Groq: {e}")
            return None
    
    # ═══════════════════════════════════════════════════════════════
    # Utilities
    # ═══════════════════════════════════════════════════════════════
    @staticmethod
    def list_voices() -> dict[str, VoiceInfo]:
        """قائمة الأصوات."""
        return GROQ_VOICES.copy()
    
    def print_stats(self):
        """طباعة الإحصائيات."""
        print(self.stats.summary())


# ═══════════════════════════════════════════════════════════════════
# اختبار سريع
# ═══════════════════════════════════════════════════════════════════
if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s | %(levelname)s | %(message)s"
    )
    
    print("=" * 60)
    print("🎙️ Groq TTS v2.0 Test")
    print("=" * 60)
    
    print(f"\n📋 Voices: {len(GROQ_VOICES)}")
    for vid, info in GROQ_VOICES.items():
        print(f"   • {info.name} ({info.gender}) - {info.description}")
    
    try:
        tts = GroqTTS(
            cache_enabled=True,
            parallel_chunks=3,
            enable_edge_fallback=True,
        )
        
        test_script = {
            "scenes": [
                {
                    "text": "هل تعلم أن 95% من الناس يفشلون بسبب هذا الخطأ؟",
                    "pause_after": 0.5,
                },
                {
                    "text": "السر بسيط جداً، لكن قليلين من يطبقونه.",
                    "pause_after": 0.7,
                },
                {
                    "text": "ابدأ الآن وستلاحظ الفرق بعد 21 يوم.",
                    "pause_after": 0.3,
                },
            ],
            "cta": "شارك هذا الفيديو!",
            "music_mood": "motivation",
        }
        
        def progress(p, msg):
            print(f"  [{p*100:3.0f}%] {msg}")
        
        result = tts.generate_audio(
            test_script,
            "test_groq.mp3",
            progress_callback=progress,
        )
        
        print(f"\n📊 Result:")
        print(f"   Status: {result.status.value}")
        print(f"   Success: {result.success}")
        print(f"   Voice: {result.voice_used}")
        print(f"   Duration: ~{result.duration_estimate:.1f}s")
        print(f"   File: {result.file_size:,} bytes")
        
        print()
        tts.print_stats()
        
    except ValueError as e:
        print(f"\n❌ {e}")
