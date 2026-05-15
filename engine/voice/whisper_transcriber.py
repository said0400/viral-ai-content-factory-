"""
🎤 Whisper Transcriber — استخراج توقيتات الكلمات من الصوت
═══════════════════════════════════════════════════════════════
يستخدم faster-whisper لتحليل الصوت العربي:
  ✓ توقيت دقيق لكل كلمة
  ✓ تجميع الكلمات في مجموعات (TikTok style)
  ✓ دعم كامل للعربية
  ✓ سريع (faster-whisper × 4 من openai-whisper)

ضع في: engine/voice/whisper_transcriber.py
═══════════════════════════════════════════════════════════════
"""

import os
import logging
from pathlib import Path
from typing import List, Dict, Optional

logger = logging.getLogger(__name__)

# Lazy import - لا نحمّل المكتبة إلا عند الحاجة
_whisper_model = None


class WhisperTranscriber:
    """محرك تحليل الصوت واستخراج توقيتات الكلمات."""

    # ─── إعدادات Whisper ──────────────────────────────────────────
    MODEL_SIZE = os.getenv("WHISPER_MODEL", "small")
    # tiny / base / small / medium / large-v3
    # small = توازن جيد بين الدقة والسرعة (~244 MB)
    # medium = أدق لكن أكبر (~769 MB)

    LANGUAGE = "ar"  # عربي
    
    # ═══════════════════════════════════════════════════════════════
    def __init__(self):
        """تهيئة المحرك."""
        self.model = None
        logger.info(f"🎤 WhisperTranscriber | Model: {self.MODEL_SIZE}")

    def _load_model(self):
        """تحميل النموذج (مرة واحدة فقط)."""
        global _whisper_model
        
        if _whisper_model is not None:
            self.model = _whisper_model
            return

        try:
            from faster_whisper import WhisperModel
            
            logger.info(f"📥 تحميل نموذج Whisper [{self.MODEL_SIZE}]...")
            
            # CPU-friendly settings
            _whisper_model = WhisperModel(
                self.MODEL_SIZE,
                device="cpu",
                compute_type="int8",  # أسرع وأخف
                cpu_threads=4,
                num_workers=1,
            )
            
            self.model = _whisper_model
            logger.info("✅ تم تحميل Whisper بنجاح")
            
        except ImportError:
            raise RuntimeError(
                "❌ faster-whisper غير مثبت!\n"
                "   شغّل: pip install faster-whisper"
            )
        except Exception as e:
            raise RuntimeError(f"❌ فشل تحميل Whisper: {e}")

    # ═══════════════════════════════════════════════════════════════
    #                    التحليل الرئيسي
    # ═══════════════════════════════════════════════════════════════
    def transcribe_with_word_timings(
        self,
        audio_path: str,
        language: str = "ar",
    ) -> List[Dict]:
        """
        🎯 تحليل الصوت وإرجاع توقيتات كل كلمة.

        Args:
            audio_path: مسار ملف الصوت
            language: اللغة (افتراضي: ar)

        Returns:
            قائمة الكلمات مع توقيتاتها:
            [
                {
                    "word": "السلام",
                    "start": 0.0,
                    "end": 0.5,
                    "probability": 0.95
                },
                {
                    "word": "عليكم",
                    "start": 0.5,
                    "end": 1.0,
                    "probability": 0.92
                },
                ...
            ]
        """
        if not Path(audio_path).exists():
            raise FileNotFoundError(f"❌ ملف الصوت غير موجود: {audio_path}")

        # تحميل النموذج (lazy)
        self._load_model()

        logger.info(f"🎤 تحليل الصوت: {Path(audio_path).name}")
        logger.info(f"   📁 Size: {Path(audio_path).stat().st_size / 1024:.1f} KB")

        try:
            # تشغيل Whisper مع word_timestamps=True
            segments, info = self.model.transcribe(
                audio_path,
                language=language,
                word_timestamps=True,  # 🎯 المفتاح السحري
                vad_filter=True,       # تجاهل الصمت
                vad_parameters=dict(
                    min_silence_duration_ms=300,
                ),
                beam_size=5,
                temperature=0.0,
            )

            logger.info(f"   🌍 Detected language: {info.language}")
            logger.info(f"   ⏱ Audio duration: {info.duration:.1f}s")

            # استخراج كل الكلمات
            words = []
            for segment in segments:
                if segment.words:
                    for word in segment.words:
                        words.append({
                            "word": word.word.strip(),
                            "start": round(word.start, 3),
                            "end": round(word.end, 3),
                            "probability": round(word.probability, 3),
                        })

            logger.info(f"   ✓ تم استخراج {len(words)} كلمة")
            return words

        except Exception as e:
            logger.error(f"❌ فشل التحليل: {e}")
            return []

    # ═══════════════════════════════════════════════════════════════
    #                    تجميع الكلمات (TikTok Style)
    # ═══════════════════════════════════════════════════════════════
    def group_words_into_chunks(
        self,
        words: List[Dict],
        max_words_per_chunk: int = 4,
        max_chunk_duration: float = 2.5,
        min_chunk_duration: float = 0.8,
    ) -> List[Dict]:
        """
        🎯 تجميع الكلمات في مجموعات قصيرة (TikTok style).

        Args:
            words: قائمة الكلمات من transcribe_with_word_timings
            max_words_per_chunk: أقصى كلمات في المجموعة
            max_chunk_duration: أقصى مدة للمجموعة (ثواني)
            min_chunk_duration: أقل مدة للمجموعة (ثواني)

        Returns:
            قائمة المجموعات (للعرض كترجمات):
            [
                {
                    "id": 0,
                    "text": "السلام عليكم ورحمة",
                    "start": 0.0,
                    "end": 1.5,
                    "duration": 1.5,
                    "words": [
                        {"word": "السلام", "start": 0.0, "end": 0.5},
                        {"word": "عليكم", "start": 0.5, "end": 1.0},
                        {"word": "ورحمة", "start": 1.0, "end": 1.5}
                    ]
                },
                ...
            ]
        """
        if not words:
            return []

        chunks = []
        current_chunk = []
        chunk_id = 0

        for word in words:
            # إذا كانت المجموعة فارغة، أضف الكلمة
            if not current_chunk:
                current_chunk.append(word)
                continue

            # حساب مدة المجموعة لو أضفنا هذه الكلمة
            potential_duration = word["end"] - current_chunk[0]["start"]
            potential_words = len(current_chunk) + 1

            # هل نُغلق المجموعة الحالية؟
            should_close = (
                potential_words > max_words_per_chunk or
                potential_duration > max_chunk_duration or
                # إغلاق عند علامات الترقيم
                self._ends_with_punctuation(current_chunk[-1]["word"])
            )

            if should_close:
                # حفظ المجموعة الحالية
                chunks.append(self._build_chunk(current_chunk, chunk_id))
                chunk_id += 1
                current_chunk = [word]
            else:
                current_chunk.append(word)

        # إضافة آخر مجموعة
        if current_chunk:
            chunks.append(self._build_chunk(current_chunk, chunk_id))

        # التحقق من المجموعات القصيرة جداً
        chunks = self._merge_short_chunks(chunks, min_chunk_duration)

        logger.info(f"📦 تم تجميع {len(words)} كلمة في {len(chunks)} مجموعة")
        return chunks

    def _build_chunk(self, words: List[Dict], chunk_id: int) -> Dict:
        """بناء مجموعة من قائمة كلمات."""
        return {
            "id": chunk_id,
            "text": " ".join(w["word"] for w in words),
            "start": words[0]["start"],
            "end": words[-1]["end"],
            "duration": round(words[-1]["end"] - words[0]["start"], 3),
            "words": words,
        }

    def _ends_with_punctuation(self, word: str) -> bool:
        """تحقق من انتهاء الكلمة بعلامة ترقيم."""
        return word.rstrip().endswith((
            ".", "،", "؟", "!", "؛", ":", 
            "...", "?", ",",
        ))

    def _merge_short_chunks(
        self,
        chunks: List[Dict],
        min_duration: float,
    ) -> List[Dict]:
        """دمج المجموعات القصيرة جداً مع التالية."""
        if len(chunks) <= 1:
            return chunks

        merged = []
        i = 0
        while i < len(chunks):
            current = chunks[i]

            # إذا كانت قصيرة جداً وليست الأخيرة
            if current["duration"] < min_duration and i + 1 < len(chunks):
                next_chunk = chunks[i + 1]
                # دمجها مع التالية
                combined = self._build_chunk(
                    current["words"] + next_chunk["words"],
                    len(merged),
                )
                merged.append(combined)
                i += 2  # تخطي التالية لأنها دُمجت
            else:
                # إعادة ترقيم الـ id
                current["id"] = len(merged)
                merged.append(current)
                i += 1

        return merged

    # ═══════════════════════════════════════════════════════════════
    #                    دالة شاملة
    # ═══════════════════════════════════════════════════════════════
    def transcribe_to_subtitles(
        self,
        audio_path: str,
        max_words_per_chunk: int = 4,
        max_chunk_duration: float = 2.5,
    ) -> List[Dict]:
        """
        🎯 الدالة الرئيسية: من الصوت إلى ترجمات جاهزة.

        Args:
            audio_path: مسار الصوت
            max_words_per_chunk: أقصى كلمات في كل ترجمة
            max_chunk_duration: أقصى مدة لكل ترجمة

        Returns:
            قائمة الترجمات الجاهزة لـ Remotion
        """
        # 1. استخراج الكلمات
        words = self.transcribe_with_word_timings(audio_path)
        
        if not words:
            logger.warning("⚠ لم يتم استخراج أي كلمات")
            return []

        # 2. تجميعها في مجموعات (TikTok style)
        chunks = self.group_words_into_chunks(
            words,
            max_words_per_chunk=max_words_per_chunk,
            max_chunk_duration=max_chunk_duration,
        )

        return chunks


# ════════════════════════════════════════════════════════════════════════
#                    اختبار سريع
# ════════════════════════════════════════════════════════════════════════
if __name__ == "__main__":
    import sys
    import json

    if len(sys.argv) < 2:
        print("Usage: python whisper_transcriber.py <audio.mp3>")
        sys.exit(1)

    audio_file = sys.argv[1]
    
    transcriber = WhisperTranscriber()
    subtitles = transcriber.transcribe_to_subtitles(audio_file)
    
    print("\n📝 الترجمات:")
    print(json.dumps(subtitles, indent=2, ensure_ascii=False))
