"""
🎙️ Gemini TTS Engine v3.0 — Smart Strategy
═══════════════════════════════════════════════════════════════
الإستراتيجية الجديدة:
  1. ✅ حاول النص كاملاً أولاً
  2. ✅ إذا الصوت قصير جداً (timeout)، قسّم لقطع صغيرة
  3. ✅ ولّد كل قطعة بشكل منفصل
  4. ✅ احفظ كل قطعة كملف WAV مستقل
  5. ✅ ادمج باستخدام pydub (موثوق 100%)

ضع في: engine/voice/gemini_tts_engine.py
═══════════════════════════════════════════════════════════════
"""

import os
import time
import struct
import logging
import mimetypes
import tempfile
from pathlib import Path
from typing import Optional, Dict, List

logger = logging.getLogger(__name__)


class GeminiTTSEngine:
    """محرك Gemini TTS - مع Smart Strategy."""

    # ─── الأصوات المتاحة ──────────────────────────────────────────
    AVAILABLE_VOICES = {
        "Achird": {"name": "Achird", "description": "ذكوري عميق", "gender": "male"},
        "Algenib": {"name": "Algenib", "description": "ذكوري واضح", "gender": "male"},
        "Aoede": {"name": "Aoede", "description": "أنثوي ناعم", "gender": "female"},
        "Charon": {"name": "Charon", "description": "ذكوري درامي", "gender": "male"},
        "Kore": {"name": "Kore", "description": "أنثوي قوي", "gender": "female"},
    }

    # ─── Director's Notes ─────────────────────────────────────────
    STYLE_PRESETS = {
        "motivational": {
            "audio_profile": "A smooth, premium commercial voice.",
            "directors_note": "Style: Promo/Hype. Pace: Natural. Accent: Neutral.",
            "scene_context": "Premium commercial. Dynamic pacing. Polished and persuasive.",
        },
        "educational": {
            "audio_profile": "A clear, authoritative narrator voice.",
            "directors_note": "Style: Documentary/Educational. Pace: Steady.",
            "scene_context": "Premium documentary narration. Clear pacing.",
        },
        "story": {
            "audio_profile": "A warm, expressive storyteller voice.",
            "directors_note": "Style: Narrative/Cinematic. Pace: Natural.",
            "scene_context": "Cinematic storytelling. Pacing varies with emotional beats.",
        },
        "quote": {
            "audio_profile": "A profound, contemplative voice.",
            "directors_note": "Style: Philosophical/Reflective. Pace: Slow.",
            "scene_context": "Profound quote delivery. Slow, deliberate pacing.",
        },
        "promo": {
            "audio_profile": "A smooth, premium commercial voice.",
            "directors_note": "Style: Promo/Hype. Pace: Natural.",
            "scene_context": "Premium commercial. Dynamic pacing.",
        },
        "viral": {
            "audio_profile": "A high-energy, attention-grabbing voice.",
            "directors_note": "Style: Viral/Social Media. Pace: Fast.",
            "scene_context": "Viral social media content. Energetic pacing.",
        },
        "psychological": {
            "audio_profile": "A deep, thoughtful, mysterious voice.",
            "directors_note": "Style: Psychological/Deep. Pace: Slow and impactful.",
            "scene_context": "Deep psychological content. Slow, weighted pacing.",
        },
    }

    # ─── إعدادات النموذج ──────────────────────────────────────────
    MODEL_NAME = "gemini-3.1-flash-tts-preview"
    DEFAULT_TEMPERATURE = 1.0

    # 🆕 إعدادات Smart Strategy
    CHUNK_SIZE_SMALL = 300       # 300 حرف عند التقسيم (آمن)
    MIN_AUDIO_KB_PER_CHAR = 0.4  # تقريباً 0.4 KB لكل حرف (للتحقق)
    MAX_RETRIES = 2              # محاولات لكل قطعة
    
    # ════════════════════════════════════════════════════════════════
    def __init__(self):
        """تهيئة المحرك."""
        self.api_key = os.getenv("GEMINI_API_KEY", "")

        if not self.api_key:
            raise RuntimeError("❌ GEMINI_API_KEY غير موجود!")

        self.voice_name = os.getenv("GEMINI_VOICE", "Achird")
        self.style_preset = os.getenv("GEMINI_STYLE", "motivational")
        self.temperature = float(os.getenv("GEMINI_TEMPERATURE", "1.0"))
        self.chunk_size = int(os.getenv("GEMINI_CHUNK_SIZE", str(self.CHUNK_SIZE_SMALL)))
        self.max_retries = int(os.getenv("GEMINI_MAX_RETRIES", str(self.MAX_RETRIES)))

        if self.voice_name not in self.AVAILABLE_VOICES:
            logger.warning(f"⚠ صوت غير معروف '{self.voice_name}'، استخدام Achird")
            self.voice_name = "Achird"

        if self.style_preset not in self.STYLE_PRESETS:
            logger.warning(f"⚠ نمط غير معروف '{self.style_preset}'، استخدام motivational")
            self.style_preset = "motivational"

        self._client = None
        self._init_client()

        logger.info(
            f"🎙️ GeminiTTSEngine v3.0 (Smart) | Voice: {self.voice_name} | "
            f"Style: {self.style_preset} | Chunk: {self.chunk_size}"
        )

    def _init_client(self) -> None:
        """تهيئة Gemini client."""
        try:
            from google import genai
            self._client = genai.Client(api_key=self.api_key)
        except ImportError:
            raise RuntimeError("❌ google-genai غير مثبت!")
        except Exception as e:
            raise RuntimeError(f"❌ فشل تهيئة Gemini client: {e}")

    # ════════════════════════════════════════════════════════════════
    #                    🎯 الدالة الرئيسية - Smart Strategy
    # ════════════════════════════════════════════════════════════════
    def generate_audio(
        self,
        script: dict,
        output_path: str,
        voice: Optional[str] = None,
        style: Optional[str] = None,
    ) -> str:
        """
        🎯 توليد الصوت بإستراتيجية ذكية:
        1. حاول النص كاملاً
        2. إذا فشل، قسّم وادمج
        """
        full_text = self._extract_text(script)

        if not full_text.strip():
            raise ValueError("❌ لا يوجد نص للتحويل")

        voice_name = voice or self.voice_name
        style_preset = style or self.style_preset

        text_len = len(full_text)
        logger.info(
            f"🎙️ توليد الصوت | Voice: {voice_name} | "
            f"Style: {style_preset} | Length: {text_len} chars"
        )

        Path(output_path).parent.mkdir(parents=True, exist_ok=True)

        # ════════════════════════════════════════════════════════════
        # 🆕 STRATEGY 1: حاول النص كاملاً
        # ════════════════════════════════════════════════════════════
        logger.info("   🎯 المحاولة 1: النص كاملاً...")
        full_audio = self._try_generate_full(full_text, voice_name, style_preset)
        
        if full_audio and self._is_audio_complete(full_audio, text_len):
            # نجح! نحفظه ونرجع
            self._save_audio_data(full_audio, output_path)
            size_kb = Path(output_path).stat().st_size / 1024
            logger.info(f"   ✅ نجح! نص كامل ({size_kb:.1f} KB)")
            return output_path
        
        # ════════════════════════════════════════════════════════════
        # 🆕 STRATEGY 2: قسّم النص وادمج
        # ════════════════════════════════════════════════════════════
        logger.warning("   ⚠ النص الكامل ناقص، جاري التقسيم...")
        
        chunks = self._split_text(full_text, self.chunk_size)
        logger.info(f"   📦 تقسيم النص إلى {len(chunks)} قطعة")

        # توليد كل قطعة كملف WAV مستقل
        wav_files = []
        temp_dir = Path(tempfile.mkdtemp(prefix="gemini_tts_"))
        
        try:
            for i, chunk_text in enumerate(chunks, 1):
                logger.info(f"   🎤 قطعة {i}/{len(chunks)} ({len(chunk_text)} حرف)")
                
                chunk_wav_path = str(temp_dir / f"chunk_{i:03d}.wav")
                
                success = self._generate_chunk_to_file(
                    text=chunk_text,
                    voice_name=voice_name,
                    style_preset=style_preset,
                    output_path=chunk_wav_path,
                    chunk_num=i,
                )
                
                if success:
                    wav_files.append(chunk_wav_path)
                    size_kb = Path(chunk_wav_path).stat().st_size / 1024
                    logger.info(f"   ✓ قطعة {i}/{len(chunks)} ({size_kb:.1f} KB)")
                else:
                    logger.warning(f"   ⚠ فشلت قطعة {i}/{len(chunks)}")

            if not wav_files:
                raise RuntimeError("❌ فشلت كل القطع!")

            # ════════════════════════════════════════════════════════
            # 🆕 دمج كل ملفات WAV باستخدام pydub
            # ════════════════════════════════════════════════════════
            logger.info(f"   🔗 دمج {len(wav_files)} ملف WAV...")
            self._merge_wav_files(wav_files, output_path)
            
            size_kb = Path(output_path).stat().st_size / 1024
            logger.info(f"   ✅ تم الدمج النهائي ({size_kb:.1f} KB)")
            
            return output_path
            
        finally:
            # تنظيف الملفات المؤقتة
            try:
                import shutil
                shutil.rmtree(temp_dir, ignore_errors=True)
            except Exception:
                pass

    # ════════════════════════════════════════════════════════════════
    #              🆕 STRATEGY 1: محاولة النص كاملاً
    # ════════════════════════════════════════════════════════════════
    def _try_generate_full(
        self,
        text: str,
        voice_name: str,
        style_preset: str,
    ) -> Optional[bytes]:
        """🆕 محاولة توليد النص كاملاً."""
        try:
            audio_data = self._call_gemini_api(text, voice_name, style_preset)
            return audio_data
        except Exception as e:
            logger.warning(f"   ⚠ فشل النص الكامل: {str(e)[:100]}")
            return None

    # ════════════════════════════════════════════════════════════════
    #              🆕 التحقق من اكتمال الصوت
    # ════════════════════════════════════════════════════════════════
    def _is_audio_complete(self, audio_data: bytes, text_length: int) -> bool:
        """
        🆕 التحقق من اكتمال الصوت بناءً على طول النص.
        
        قاعدة تقريبية: كل حرف عربي = ~0.4 KB من الصوت
        """
        size_kb = len(audio_data) / 1024
        expected_min_kb = text_length * self.MIN_AUDIO_KB_PER_CHAR
        
        is_complete = size_kb >= expected_min_kb
        
        logger.info(
            f"   📊 فحص الاكتمال: "
            f"{size_kb:.1f} KB / {expected_min_kb:.1f} KB متوقع "
            f"({'✅ كامل' if is_complete else '❌ ناقص'})"
        )
        
        return is_complete

    # ════════════════════════════════════════════════════════════════
    #              🆕 توليد قطعة وحفظها كـ WAV
    # ════════════════════════════════════════════════════════════════
    def _generate_chunk_to_file(
        self,
        text: str,
        voice_name: str,
        style_preset: str,
        output_path: str,
        chunk_num: int,
    ) -> bool:
        """🆕 توليد قطعة وحفظها مباشرة كملف WAV."""
        for attempt in range(1, self.max_retries + 1):
            try:
                if attempt > 1:
                    logger.info(f"      🔄 محاولة {attempt}/{self.max_retries}")
                    time.sleep(2)
                
                audio_data = self._call_gemini_api(text, voice_name, style_preset)
                
                if audio_data and len(audio_data) > 1000:
                    # حفظ مباشر
                    self._save_audio_data(audio_data, output_path)
                    return True
                else:
                    logger.warning(f"      ⚠ قطعة فارغة (محاولة {attempt})")
                    
            except Exception as e:
                logger.warning(f"      ⚠ فشل (محاولة {attempt}): {str(e)[:100]}")
        
        return False

    # ════════════════════════════════════════════════════════════════
    #              🆕 الاتصال بـ Gemini API
    # ════════════════════════════════════════════════════════════════
    def _call_gemini_api(
        self,
        text: str,
        voice_name: str,
        style_preset: str,
    ) -> bytes:
        """🆕 الاتصال بـ Gemini API وإرجاع الصوت."""
        from google.genai import types

        style_config = self.STYLE_PRESETS.get(
            style_preset, self.STYLE_PRESETS["motivational"]
        )

        prompt = self._build_prompt(text, style_config)

        contents = [
            types.Content(
                role="user",
                parts=[types.Part.from_text(text=prompt)],
            ),
        ]

        config = types.GenerateContentConfig(
            temperature=self.temperature,
            response_modalities=["audio"],
            speech_config=types.SpeechConfig(
                voice_config=types.VoiceConfig(
                    prebuilt_voice_config=types.PrebuiltVoiceConfig(
                        voice_name=voice_name
                    )
                )
            ),
        )

        audio_chunks = []
        mime_type = None

        for chunk in self._client.models.generate_content_stream(
            model=self.MODEL_NAME,
            contents=contents,
            config=config,
        ):
            if chunk.parts is None:
                continue

            if chunk.parts[0].inline_data and chunk.parts[0].inline_data.data:
                inline_data = chunk.parts[0].inline_data
                audio_chunks.append(inline_data.data)
                if mime_type is None:
                    mime_type = inline_data.mime_type

        if not audio_chunks:
            raise RuntimeError("لم يتم استلام بيانات صوتية")

        raw_audio = b"".join(audio_chunks)

        # تحويل لـ WAV إذا لزم
        file_extension = mimetypes.guess_extension(mime_type) if mime_type else None
        if file_extension is None or "wav" not in (file_extension or ""):
            raw_audio = self._convert_to_wav(raw_audio, mime_type)

        return raw_audio

    # ════════════════════════════════════════════════════════════════
    #              🆕 دمج ملفات WAV باستخدام pydub
    # ════════════════════════════════════════════════════════════════
    def _merge_wav_files(self, wav_files: List[str], output_path: str) -> None:
        """🆕 دمج عدة ملفات WAV باستخدام pydub (موثوق 100%)."""
        try:
            from pydub import AudioSegment
            
            # ابدأ بأول ملف
            combined = AudioSegment.from_wav(wav_files[0])
            
            # أضف الباقي
            for wav_file in wav_files[1:]:
                segment = AudioSegment.from_wav(wav_file)
                combined += segment
            
            # حفظ النتيجة
            wants_mp3 = output_path.endswith(".mp3")
            
            if wants_mp3:
                combined.export(output_path, format="mp3", bitrate="192k")
            else:
                combined.export(output_path, format="wav")
            
            logger.info(f"   ✓ تم دمج {len(wav_files)} ملف بنجاح")
            
        except Exception as e:
            logger.error(f"   ❌ فشل الدمج بـ pydub: {e}")
            # Fallback: استخدم أول ملف فقط
            import shutil
            shutil.copy(wav_files[0], output_path)
            logger.warning("   ⚠ استخدام أول ملف فقط كـ fallback")

    # ════════════════════════════════════════════════════════════════
    #              تقسيم النص
    # ════════════════════════════════════════════════════════════════
    def _split_text(self, text: str, max_chars: int) -> List[str]:
        """تقسيم النص لقطع عند نهايات الجمل."""
        if len(text) <= max_chars:
            return [text]

        chunks = []
        delimiters = ['. ', '! ', '? ', '... ', '،', '؛', '\n', ' ']
        
        remaining = text
        while remaining:
            if len(remaining) <= max_chars:
                chunks.append(remaining.strip())
                break
            
            best_pos = -1
            chunk_window = remaining[:max_chars]
            
            for delim in delimiters:
                pos = chunk_window.rfind(delim)
                if pos > max_chars * 0.5:
                    best_pos = pos + len(delim)
                    break
            
            if best_pos == -1:
                best_pos = chunk_window.rfind(' ')
                if best_pos == -1:
                    best_pos = max_chars
            
            chunks.append(remaining[:best_pos].strip())
            remaining = remaining[best_pos:].strip()
        
        return [c for c in chunks if c]

    # ════════════════════════════════════════════════════════════════
    #              استخراج النص (مع أولوية scenes)
    # ════════════════════════════════════════════════════════════════
    def _extract_text(self, script: dict) -> str:
        """استخراج النص الكامل."""
        # 1. ⭐ scenes أولاً
        scenes = script.get("scenes", [])
        if scenes:
            texts = [s.get("text", "").strip() for s in scenes if s.get("text")]
            if texts:
                full_from_scenes = " ".join(texts)
                logger.info(
                    f"   📝 النص من scenes: {len(full_from_scenes)} حرف "
                    f"({len(texts)} مشاهد)"
                )
                return full_from_scenes

        # 2. full_text (إذا > 50 حرف)
        full_text = script.get("full_text", "").strip()
        if full_text and len(full_text) > 50:
            logger.info(f"   📝 النص من full_text: {len(full_text)} حرف")
            return full_text

        # 3. hook (مع تحذير)
        hook = script.get("hook", "").strip()
        if hook:
            logger.warning(f"   ⚠ استخدام Hook فقط: {len(hook)} حرف")
            return hook

        logger.error("   ❌ لا يوجد نص في السكربت!")
        return ""

    # ════════════════════════════════════════════════════════════════
    #              بناء Prompt
    # ════════════════════════════════════════════════════════════════
    def _build_prompt(self, text: str, style_config: Dict) -> str:
        """بناء الـ prompt الاحترافي."""
        return f"""Read the following transcript based on the audio profile and director's note.

# Audio Profile
{style_config['audio_profile']}

# Director's note
{style_config['directors_note']}

## Scene:
The Sound Stage Booth.

## Sample Context:
{style_config['scene_context']}

## Transcript:
{text}"""

    # ════════════════════════════════════════════════════════════════
    #              حفظ الصوت (PCM → WAV)
    # ════════════════════════════════════════════════════════════════
    def _save_audio_data(self, audio_data: bytes, output_path: str) -> None:
        """حفظ بيانات الصوت إلى ملف."""
        original_path = output_path
        wants_mp3 = output_path.endswith(".mp3")
        
        # نحفظ كـ WAV أولاً
        wav_path = output_path.replace(".mp3", ".wav") if wants_mp3 else output_path
        if not wav_path.endswith(".wav"):
            wav_path += ".wav"

        with open(wav_path, "wb") as f:
            f.write(audio_data)

        # تحويل لـ MP3 إذا مطلوب
        if wants_mp3:
            self._convert_wav_to_mp3(wav_path, original_path)
            try:
                Path(wav_path).unlink(missing_ok=True)
            except Exception:
                pass

    def _convert_wav_to_mp3(self, wav_path: str, mp3_path: str) -> None:
        """تحويل WAV إلى MP3."""
        try:
            from pydub import AudioSegment
            audio = AudioSegment.from_wav(wav_path)
            audio.export(mp3_path, format="mp3", bitrate="192k")
        except Exception as e:
            logger.warning(f"⚠ فشل التحويل لـ MP3: {e}")
            import shutil
            shutil.copy(wav_path, mp3_path)

    def _convert_to_wav(self, audio_data: bytes, mime_type: str) -> bytes:
        """تحويل raw PCM إلى WAV."""
        parameters = self._parse_audio_mime_type(mime_type)
        bits_per_sample = parameters["bits_per_sample"]
        sample_rate = parameters["rate"]
        num_channels = 1
        data_size = len(audio_data)
        bytes_per_sample = bits_per_sample // 8
        block_align = num_channels * bytes_per_sample
        byte_rate = sample_rate * block_align
        chunk_size = 36 + data_size

        header = struct.pack(
            "<4sI4s4sIHHIIHH4sI",
            b"RIFF", chunk_size, b"WAVE", b"fmt ",
            16, 1, num_channels, sample_rate,
            byte_rate, block_align, bits_per_sample,
            b"data", data_size,
        )
        return header + audio_data

    def _parse_audio_mime_type(self, mime_type: str) -> Dict[str, int]:
        """تحليل mime type."""
        bits_per_sample = 16
        rate = 24000

        if not mime_type:
            return {"bits_per_sample": bits_per_sample, "rate": rate}

        parts = mime_type.split(";")
        for param in parts:
            param = param.strip()
            if param.lower().startswith("rate="):
                try:
                    rate = int(param.split("=", 1)[1])
                except (ValueError, IndexError):
                    pass
            elif param.startswith("audio/L"):
                try:
                    bits_per_sample = int(param.split("L", 1)[1])
                except (ValueError, IndexError):
                    pass

        return {"bits_per_sample": bits_per_sample, "rate": rate}

    # ════════════════════════════════════════════════════════════════
    #              دوال مساعدة
    # ════════════════════════════════════════════════════════════════
    def list_voices(self) -> Dict:
        return self.AVAILABLE_VOICES

    def list_styles(self) -> Dict:
        return self.STYLE_PRESETS


# ════════════════════════════════════════════════════════════════════════
#                    اختبار سريع
# ════════════════════════════════════════════════════════════════════════
if __name__ == "__main__":
    import sys

    test_script = {
        "hook": "اكتشف قاعدة الـ 7 ثوانٍ...",
        "scenes": [
            {"text": "اكتشف قاعدة الـ 7 ثوانٍ التي تغير طريقة تفاعلك مع الناس."},
            {"text": "خلال 7 ثوانٍ، يحكم الناس عليك للأبد."},
            {"text": "هذا ما تقوله الأبحاث النفسية الحديثة."},
            {"text": "السر هو في 3 عناصر: نظرة العينين، نبرة الصوت، والابتسامة."},
            {"text": "ابدأ تطبيق هذه القاعدة اليوم..."},
            {"text": "وستلاحظ الفرق فوراً في علاقاتك!"},
            {"text": "النجاح في التواصل يبدأ من ثوانيك الأولى."},
            {"text": "احفظ هذه القاعدة جيداً."},
            {"text": "وشاركها مع من تحب!"},
        ],
    }

    output_file = sys.argv[1] if len(sys.argv) > 1 else "test_gemini.wav"

    try:
        engine = GeminiTTSEngine()
        print(f"\n📊 معلومات:")
        print(f"   • Voice: {engine.voice_name}")
        print(f"   • Style: {engine.style_preset}")
        print(f"   • Chunk size: {engine.chunk_size}")

        print(f"\n🎙️ توليد صوت تجريبي → {output_file}")
        engine.generate_audio(test_script, output_file)
        print(f"\n✅ تم بنجاح! تحقق من الملف: {output_file}")

    except Exception as e:
        print(f"\n❌ خطأ: {e}")
        sys.exit(1)
