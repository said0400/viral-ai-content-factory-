"""
🎤 Whisper Transcriber v2.0 — Pro
═══════════════════════════════════════════════════════════════
يستخدم faster-whisper لتحليل الصوت العربي:
  ✓ توقيت دقيق لكل كلمة
  ✓ تجميع TikTok style
  ✓ دعم GPU/CPU تلقائي
  ✓ Caching ذكي
  ✓ Export إلى SRT/VTT/JSON
  ✓ Progress tracking

التحسينات v2.0:
  ✓ Thread-safe model loading
  ✓ Caching للنتائج (md5 hash)
  ✓ GPU auto-detection
  ✓ TranscriptionResult dataclass
  ✓ Multiple output formats
  ✓ Better Arabic handling
  ✓ Progress callback
  ✓ File size validation
═══════════════════════════════════════════════════════════════
"""

from __future__ import annotations

import os
import re
import json
import hashlib
import logging
from pathlib import Path
from enum import Enum
from dataclasses import dataclass, field, asdict
from threading import Lock
from typing import Optional, Callable, Any

logger = logging.getLogger(__name__)


# ═══════════════════════════════════════════════════════════════════
# Enums
# ═══════════════════════════════════════════════════════════════════
class ModelSize(str, Enum):
    """أحجام نموذج Whisper."""
    TINY = "tiny"           # ~39 MB - سريع جداً، دقة محدودة
    BASE = "base"           # ~74 MB - متوازن خفيف
    SMALL = "small"         # ~244 MB - توازن جيد
    MEDIUM = "medium"       # ~769 MB - دقة عالية
    LARGE_V2 = "large-v2"   # ~1.5 GB - دقة ممتازة
    LARGE_V3 = "large-v3"   # ~1.5 GB - الأحدث والأدق


class ComputeType(str, Enum):
    """نوع الحوسبة."""
    INT8 = "int8"           # CPU optimized
    INT8_FLOAT16 = "int8_float16"  # GPU mixed
    FLOAT16 = "float16"     # GPU
    FLOAT32 = "float32"     # GPU precision


# ═══════════════════════════════════════════════════════════════════
# Dataclasses
# ═══════════════════════════════════════════════════════════════════
@dataclass
class WordTiming:
    """توقيت كلمة واحدة."""
    word: str
    start: float
    end: float
    probability: float = 1.0
    
    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class SubtitleChunk:
    """مجموعة كلمات (للترجمة)."""
    id: int
    text: str
    start: float
    end: float
    duration: float
    words: list[WordTiming] = field(default_factory=list)
    
    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "text": self.text,
            "start": self.start,
            "end": self.end,
            "duration": self.duration,
            "words": [w.to_dict() for w in self.words],
        }


@dataclass
class TranscriptionResult:
    """نتيجة التحليل الكاملة."""
    audio_path: str
    language: str
    duration: float
    words: list[WordTiming] = field(default_factory=list)
    chunks: list[SubtitleChunk] = field(default_factory=list)
    full_text: str = ""
    cached: bool = False
    processing_time: float = 0.0
    
    @property
    def word_count(self) -> int:
        return len(self.words)
    
    @property
    def chunk_count(self) -> int:
        return len(self.chunks)
    
    def to_dict(self) -> dict:
        return {
            "audio_path": self.audio_path,
            "language": self.language,
            "duration": self.duration,
            "word_count": self.word_count,
            "chunk_count": self.chunk_count,
            "full_text": self.full_text,
            "words": [w.to_dict() for w in self.words],
            "chunks": [c.to_dict() for c in self.chunks],
            "cached": self.cached,
            "processing_time": self.processing_time,
        }


# ═══════════════════════════════════════════════════════════════════
# Constants
# ═══════════════════════════════════════════════════════════════════
class WhisperConstants:
    """الثوابت."""
    
    DEFAULT_MODEL = ModelSize.SMALL
    DEFAULT_LANGUAGE = "ar"
    
    # Chunking
    DEFAULT_MAX_WORDS = 4
    DEFAULT_MAX_DURATION = 2.5
    DEFAULT_MIN_DURATION = 0.8
    
    # VAD
    VAD_MIN_SILENCE_MS = 300
    
    # Beam search
    BEAM_SIZE = 5
    
    # حدود الملفات
    MAX_FILE_SIZE_MB = 500
    
    # Cache
    CACHE_VERSION = "v2"


# علامات الترقيم العربية والإنجليزية
ARABIC_PUNCTUATION = (".", "،", "؟", "!", "؛", ":", "...", "?", ",", "،", "«", "»", "…")


# ═══════════════════════════════════════════════════════════════════
# Helper Functions
# ═══════════════════════════════════════════════════════════════════
def clean_arabic_word(word: str) -> str:
    """تنظيف الكلمة العربية."""
    if not word:
        return ""
    
    # إزالة المسافات الزائدة
    word = word.strip()
    
    # إزالة الـ markers
    for ch in ("\u200f", "\u200e", "\ufeff"):
        word = word.replace(ch, "")
    
    return word


def get_audio_hash(audio_path: str, model_size: str) -> str:
    """إنشاء hash للـ audio file + model."""
    file_path = Path(audio_path)
    
    # استخدم: size + mtime + model
    stat = file_path.stat()
    content = f"{file_path.name}|{stat.st_size}|{stat.st_mtime}|{model_size}|{WhisperConstants.CACHE_VERSION}"
    
    return hashlib.md5(content.encode()).hexdigest()[:16]


def detect_best_device() -> tuple[str, str]:
    """كشف أفضل device متاح (GPU/CPU)."""
    try:
        import torch
        if torch.cuda.is_available():
            return "cuda", ComputeType.FLOAT16.value
    except ImportError:
        pass
    
    return "cpu", ComputeType.INT8.value


# ═══════════════════════════════════════════════════════════════════
# Model Manager (Thread-Safe Singleton)
# ═══════════════════════════════════════════════════════════════════
class WhisperModelManager:
    """مدير النماذج (singleton thread-safe)."""
    
    _instances: dict[str, Any] = {}
    _lock = Lock()
    
    @classmethod
    def get_model(
        cls,
        model_size: str,
        device: str = "auto",
        compute_type: str = "auto",
    ):
        """الحصول على model instance (مرة واحدة فقط)."""
        # Auto-detect device
        if device == "auto":
            device, auto_compute = detect_best_device()
            if compute_type == "auto":
                compute_type = auto_compute
        elif compute_type == "auto":
            compute_type = (
                ComputeType.FLOAT16.value if device == "cuda"
                else ComputeType.INT8.value
            )
        
        cache_key = f"{model_size}_{device}_{compute_type}"
        
        with cls._lock:
            if cache_key not in cls._instances:
                try:
                    from faster_whisper import WhisperModel
                except ImportError:
                    raise RuntimeError(
                        "❌ faster-whisper غير مثبت!\n"
                        "   pip install faster-whisper"
                    )
                
                logger.info(
                    f"📥 تحميل Whisper [{model_size}] | "
                    f"Device: {device} | Compute: {compute_type}"
                )
                
                cls._instances[cache_key] = WhisperModel(
                    model_size,
                    device=device,
                    compute_type=compute_type,
                    cpu_threads=int(os.getenv("WHISPER_CPU_THREADS", "4")),
                    num_workers=1,
                )
                
                logger.info(f"✅ Whisper جاهز [{cache_key}]")
            
            return cls._instances[cache_key]
    
    @classmethod
    def clear_cache(cls):
        """مسح كل النماذج من الذاكرة."""
        with cls._lock:
            cls._instances.clear()
        logger.info("🗑 تم مسح كل نماذج Whisper")


# ═══════════════════════════════════════════════════════════════════
# Main Class
# ═══════════════════════════════════════════════════════════════════
class WhisperTranscriber:
    """محرك تحليل الصوت v2.0."""
    
    def __init__(
        self,
        model_size: Optional[str] = None,
        device: str = "auto",
        compute_type: str = "auto",
        cache_enabled: bool = True,
        cache_dir: Optional[str] = None,
    ):
        """
        Args:
            model_size: حجم النموذج
            device: cpu/cuda/auto
            compute_type: int8/float16/auto
            cache_enabled: تفعيل الكاش
            cache_dir: مجلد الكاش
        """
        # Settings
        self.model_size = (
            model_size or
            os.getenv("WHISPER_MODEL", WhisperConstants.DEFAULT_MODEL.value)
        )
        self.device = device
        self.compute_type = compute_type
        
        # Cache
        self.cache_enabled = cache_enabled
        if cache_enabled:
            self.cache_dir = Path(
                cache_dir or
                Path(os.getenv("TEMP_DIR", "./temp")) / "whisper_cache"
            )
            self.cache_dir.mkdir(parents=True, exist_ok=True)
        else:
            self.cache_dir = None
        
        logger.info(
            f"🎤 WhisperTranscriber v2.0 | Model: {self.model_size}"
        )
    
    # ═══════════════════════════════════════════════════════════════
    # Main API
    # ═══════════════════════════════════════════════════════════════
    def transcribe(
        self,
        audio_path: str,
        language: str = WhisperConstants.DEFAULT_LANGUAGE,
        progress_callback: Optional[Callable[[float, str], None]] = None,
    ) -> TranscriptionResult:
        """
        🎯 تحليل شامل للصوت.
        
        Args:
            audio_path: مسار الصوت
            language: اللغة (ar/en/auto)
            progress_callback: callback للتقدم
        
        Returns:
            TranscriptionResult كامل
        """
        import time
        start_time = time.time()
        
        # ── Validation ──
        audio_file = Path(audio_path)
        if not audio_file.exists():
            raise FileNotFoundError(f"❌ ملف غير موجود: {audio_path}")
        
        file_size_mb = audio_file.stat().st_size / (1024 * 1024)
        if file_size_mb > WhisperConstants.MAX_FILE_SIZE_MB:
            raise ValueError(
                f"❌ الملف كبير جداً: {file_size_mb:.1f} MB "
                f"(الحد: {WhisperConstants.MAX_FILE_SIZE_MB} MB)"
            )
        
        logger.info(
            f"🎤 تحليل: {audio_file.name} ({file_size_mb:.1f} MB)"
        )
        
        if progress_callback:
            progress_callback(0.05, "بدء التحليل...")
        
        # ── تحقق من الكاش ──
        if self.cache_enabled:
            cached = self._get_cached_result(audio_path)
            if cached:
                logger.info("⚡ من الكاش")
                cached.cached = True
                cached.processing_time = 0.0
                
                if progress_callback:
                    progress_callback(1.0, "من الكاش")
                
                return cached
        
        # ── تحميل النموذج ──
        if progress_callback:
            progress_callback(0.1, "تحميل النموذج...")
        
        model = WhisperModelManager.get_model(
            self.model_size,
            self.device,
            self.compute_type,
        )
        
        # ── التحليل ──
        if progress_callback:
            progress_callback(0.3, "تحليل الصوت...")
        
        try:
            segments, info = model.transcribe(
                audio_path,
                language=language if language != "auto" else None,
                word_timestamps=True,
                vad_filter=True,
                vad_parameters={
                    "min_silence_duration_ms": WhisperConstants.VAD_MIN_SILENCE_MS,
                },
                beam_size=WhisperConstants.BEAM_SIZE,
                temperature=0.0,
            )
            
            logger.info(
                f"   🌍 Language: {info.language} | "
                f"Duration: {info.duration:.1f}s"
            )
            
            if progress_callback:
                progress_callback(0.6, "استخراج الكلمات...")
            
            # ── استخراج الكلمات ──
            words = self._extract_words(segments)
            
            if not words:
                logger.warning("⚠ لم يتم استخراج كلمات")
            
            if progress_callback:
                progress_callback(0.8, "تجميع الترجمات...")
            
            # ── تجميع chunks ──
            chunks = self.group_words_into_chunks(words)
            
            # ── النص الكامل ──
            full_text = " ".join(w.word for w in words)
            
            # ── النتيجة ──
            elapsed = time.time() - start_time
            result = TranscriptionResult(
                audio_path=audio_path,
                language=info.language,
                duration=info.duration,
                words=words,
                chunks=chunks,
                full_text=full_text,
                processing_time=elapsed,
            )
            
            # ── حفظ الكاش ──
            if self.cache_enabled:
                self._save_to_cache(audio_path, result)
            
            if progress_callback:
                progress_callback(1.0, f"تم! {len(words)} كلمة")
            
            logger.info(
                f"   ✅ {len(words)} كلمة | "
                f"{len(chunks)} chunk | "
                f"{elapsed:.1f}s"
            )
            
            return result
            
        except Exception as e:
            logger.error(f"❌ فشل التحليل: {e}")
            raise
    
    # ═══════════════════════════════════════════════════════════════
    # Word Extraction
    # ═══════════════════════════════════════════════════════════════
    def _extract_words(self, segments) -> list[WordTiming]:
        """استخراج الكلمات من segments."""
        words = []
        
        for segment in segments:
            if not segment.words:
                continue
            
            for word in segment.words:
                cleaned = clean_arabic_word(word.word)
                if not cleaned:
                    continue
                
                words.append(WordTiming(
                    word=cleaned,
                    start=round(word.start, 3),
                    end=round(word.end, 3),
                    probability=round(word.probability, 3),
                ))
        
        return words
    
    # ═══════════════════════════════════════════════════════════════
    # Chunking (TikTok Style)
    # ═══════════════════════════════════════════════════════════════
    def group_words_into_chunks(
        self,
        words: list[WordTiming],
        max_words: int = WhisperConstants.DEFAULT_MAX_WORDS,
        max_duration: float = WhisperConstants.DEFAULT_MAX_DURATION,
        min_duration: float = WhisperConstants.DEFAULT_MIN_DURATION,
    ) -> list[SubtitleChunk]:
        """
        🎯 تجميع الكلمات في مجموعات قصيرة.
        
        Args:
            words: قائمة WordTiming
            max_words: أقصى كلمات لكل chunk
            max_duration: أقصى مدة
            min_duration: أقل مدة (للدمج)
        """
        if not words:
            return []
        
        chunks = []
        current: list[WordTiming] = []
        
        for word in words:
            if not current:
                current.append(word)
                continue
            
            potential_duration = word.end - current[0].start
            potential_words = len(current) + 1
            
            should_close = (
                potential_words > max_words or
                potential_duration > max_duration or
                self._ends_with_punctuation(current[-1].word)
            )
            
            if should_close:
                chunks.append(self._build_chunk(current, len(chunks)))
                current = [word]
            else:
                current.append(word)
        
        # آخر مجموعة
        if current:
            chunks.append(self._build_chunk(current, len(chunks)))
        
        # دمج القصيرة
        chunks = self._merge_short_chunks(chunks, min_duration, max_duration)
        
        logger.debug(
            f"📦 {len(words)} كلمة → {len(chunks)} chunk"
        )
        return chunks
    
    @staticmethod
    def _build_chunk(words: list[WordTiming], chunk_id: int) -> SubtitleChunk:
        """بناء chunk."""
        text = " ".join(w.word for w in words)
        return SubtitleChunk(
            id=chunk_id,
            text=text,
            start=words[0].start,
            end=words[-1].end,
            duration=round(words[-1].end - words[0].start, 3),
            words=words,
        )
    
    @staticmethod
    def _ends_with_punctuation(word: str) -> bool:
        """فحص نهاية الكلمة."""
        return word.rstrip().endswith(ARABIC_PUNCTUATION)
    
    @staticmethod
    def _merge_short_chunks(
        chunks: list[SubtitleChunk],
        min_duration: float,
        max_duration: float,
    ) -> list[SubtitleChunk]:
        """دمج المجموعات القصيرة (مع احترام max_duration)."""
        if len(chunks) <= 1:
            return chunks
        
        merged: list[SubtitleChunk] = []
        i = 0
        
        while i < len(chunks):
            current = chunks[i]
            
            # إذا قصيرة وممكن دمجها
            if (current.duration < min_duration and
                i + 1 < len(chunks)):
                
                next_chunk = chunks[i + 1]
                combined_duration = next_chunk.end - current.start
                
                # تأكد أن الدمج لا يتجاوز max_duration
                if combined_duration <= max_duration:
                    combined_words = current.words + next_chunk.words
                    combined = WhisperTranscriber._build_chunk(
                        combined_words, len(merged)
                    )
                    merged.append(combined)
                    i += 2
                    continue
            
            # لا دمج → احتفظ
            current.id = len(merged)
            merged.append(current)
            i += 1
        
        return merged
    
    # ═══════════════════════════════════════════════════════════════
    # Caching
    # ═══════════════════════════════════════════════════════════════
    def _get_cached_result(self, audio_path: str) -> Optional[TranscriptionResult]:
        """جلب من الكاش."""
        if not self.cache_enabled or not self.cache_dir:
            return None
        
        try:
            cache_key = get_audio_hash(audio_path, self.model_size)
            cache_file = self.cache_dir / f"{cache_key}.json"
            
            if not cache_file.exists():
                return None
            
            with open(cache_file, "r", encoding="utf-8") as f:
                data = json.load(f)
            
            # إعادة بناء الـ dataclasses
            words = [
                WordTiming(**w) for w in data.get("words", [])
            ]
            chunks = [
                SubtitleChunk(
                    id=c["id"],
                    text=c["text"],
                    start=c["start"],
                    end=c["end"],
                    duration=c["duration"],
                    words=[WordTiming(**w) for w in c.get("words", [])],
                )
                for c in data.get("chunks", [])
            ]
            
            return TranscriptionResult(
                audio_path=data["audio_path"],
                language=data["language"],
                duration=data["duration"],
                words=words,
                chunks=chunks,
                full_text=data.get("full_text", ""),
            )
            
        except Exception as e:
            logger.warning(f"⚠ فشل جلب الكاش: {e}")
            return None
    
    def _save_to_cache(
        self,
        audio_path: str,
        result: TranscriptionResult,
    ) -> None:
        """حفظ في الكاش."""
        if not self.cache_enabled or not self.cache_dir:
            return
        
        try:
            cache_key = get_audio_hash(audio_path, self.model_size)
            cache_file = self.cache_dir / f"{cache_key}.json"
            
            with open(cache_file, "w", encoding="utf-8") as f:
                json.dump(
                    result.to_dict(),
                    f,
                    indent=2,
                    ensure_ascii=False,
                )
            
            logger.debug(f"💾 محفوظ: {cache_key}")
            
        except Exception as e:
            logger.warning(f"⚠ فشل حفظ الكاش: {e}")
    
    def clear_cache(self) -> int:
        """مسح الكاش."""
        if not self.cache_enabled or not self.cache_dir:
            return 0
        
        count = 0
        for f in self.cache_dir.glob("*.json"):
            f.unlink()
            count += 1
        
        logger.info(f"🗑 تم حذف {count} ملف")
        return count
    
    # ═══════════════════════════════════════════════════════════════
    # Convenience Methods (للتوافق الخلفي)
    # ═══════════════════════════════════════════════════════════════
    def transcribe_with_word_timings(
        self,
        audio_path: str,
        language: str = "ar",
    ) -> list[dict]:
        """متوافق مع v1 - يُرجع قائمة dicts."""
        result = self.transcribe(audio_path, language)
        return [w.to_dict() for w in result.words]
    
    def transcribe_to_subtitles(
        self,
        audio_path: str,
        max_words_per_chunk: int = WhisperConstants.DEFAULT_MAX_WORDS,
        max_chunk_duration: float = WhisperConstants.DEFAULT_MAX_DURATION,
    ) -> list[dict]:
        """متوافق مع v1 - يُرجع قائمة chunks."""
        result = self.transcribe(audio_path)
        
        # إعادة التجميع بالإعدادات المطلوبة
        chunks = self.group_words_into_chunks(
            result.words,
            max_words=max_words_per_chunk,
            max_duration=max_chunk_duration,
        )
        
        return [c.to_dict() for c in chunks]
    
    # ═══════════════════════════════════════════════════════════════
    # Export Formats
    # ═══════════════════════════════════════════════════════════════
    def export_to_srt(
        self,
        result: TranscriptionResult,
        output_path: str,
    ) -> str:
        """تصدير إلى SRT."""
        Path(output_path).parent.mkdir(parents=True, exist_ok=True)
        
        lines = []
        for i, chunk in enumerate(result.chunks, 1):
            start_srt = self._seconds_to_srt_time(chunk.start)
            end_srt = self._seconds_to_srt_time(chunk.end)
            
            lines.append(str(i))
            lines.append(f"{start_srt} --> {end_srt}")
            lines.append(chunk.text)
            lines.append("")
        
        Path(output_path).write_text(
            "\n".join(lines),
            encoding="utf-8"
        )
        
        logger.info(f"📄 SRT saved: {output_path}")
        return output_path
    
    def export_to_vtt(
        self,
        result: TranscriptionResult,
        output_path: str,
    ) -> str:
        """تصدير إلى WebVTT."""
        Path(output_path).parent.mkdir(parents=True, exist_ok=True)
        
        lines = ["WEBVTT", ""]
        for chunk in result.chunks:
            start_vtt = self._seconds_to_vtt_time(chunk.start)
            end_vtt = self._seconds_to_vtt_time(chunk.end)
            
            lines.append(f"{start_vtt} --> {end_vtt}")
            lines.append(chunk.text)
            lines.append("")
        
        Path(output_path).write_text(
            "\n".join(lines),
            encoding="utf-8"
        )
        
        logger.info(f"📄 VTT saved: {output_path}")
        return output_path
    
    def export_to_json(
        self,
        result: TranscriptionResult,
        output_path: str,
    ) -> str:
        """تصدير إلى JSON."""
        Path(output_path).parent.mkdir(parents=True, exist_ok=True)
        
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(
                result.to_dict(),
                f,
                indent=2,
                ensure_ascii=False,
            )
        
        logger.info(f"📄 JSON saved: {output_path}")
        return output_path
    
    @staticmethod
    def _seconds_to_srt_time(seconds: float) -> str:
        """تحويل ثواني إلى HH:MM:SS,mmm."""
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        secs = seconds % 60
        return f"{hours:02d}:{minutes:02d}:{secs:06.3f}".replace(".", ",")
    
    @staticmethod
    def _seconds_to_vtt_time(seconds: float) -> str:
        """تحويل ثواني إلى HH:MM:SS.mmm."""
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        secs = seconds % 60
        return f"{hours:02d}:{minutes:02d}:{secs:06.3f}"


# ═══════════════════════════════════════════════════════════════════
# اختبار سريع
# ═══════════════════════════════════════════════════════════════════
if __name__ == "__main__":
    import sys
    
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s | %(levelname)s | %(message)s"
    )
    
    if len(sys.argv) < 2:
        print("Usage: python whisper_transcriber.py <audio.mp3>")
        sys.exit(1)
    
    audio_file = sys.argv[1]
    
    print("=" * 60)
    print("🎤 Whisper Transcriber v2.0 Test")
    print("=" * 60)
    
    transcriber = WhisperTranscriber(cache_enabled=True)
    
    def progress(p, msg):
        print(f"  [{p*100:3.0f}%] {msg}")
    
    result = transcriber.transcribe(
        audio_file,
        progress_callback=progress,
    )
    
    print(f"\n📊 Result:")
    print(f"   Language: {result.language}")
    print(f"   Duration: {result.duration:.1f}s")
    print(f"   Words: {result.word_count}")
    print(f"   Chunks: {result.chunk_count}")
    print(f"   Cached: {result.cached}")
    print(f"   Processing time: {result.processing_time:.1f}s")
    
    print(f"\n📝 First 3 chunks:")
    for chunk in result.chunks[:3]:
        print(f"   [{chunk.start:.2f}-{chunk.end:.2f}] {chunk.text}")
    
    # تصدير
    print("\n💾 Exporting...")
    transcriber.export_to_srt(result, "output.srt")
    transcriber.export_to_vtt(result, "output.vtt")
    transcriber.export_to_json(result, "output.json")
    
    print("\n✅ Done!")
