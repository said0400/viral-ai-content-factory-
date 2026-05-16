"""
🎙️ Gemini TTS Engine v2.0 — مع تقسيم النص الطويل
═══════════════════════════════════════════════════════════════
الإصلاحات:
  ✓ تقسيم النص الطويل لقطع
  ✓ دمج الصوت من كل قطعة
  ✓ Retry logic
  ✓ معالجة أفضل للأخطاء
  ✓ Logging تفصيلي

ضع في: engine/voice/gemini_tts_engine.py
═══════════════════════════════════════════════════════════════
"""

import os
import time
import struct
import logging
import mimetypes
from pathlib import Path
from typing import Optional, Dict, List

logger = logging.getLogger(__name__)


class GeminiTTSEngine:
    """محرك توليد الصوت بـ Google Gemini TTS - مع تقسيم النص."""

    # ─── الأصوات المتاحة ──────────────────────────────────────────
    AVAILABLE_VOICES = {
        "Achird": {
            "name": "Achird",
            "description": "صوت ذكوري عميق وحاد",
            "gender": "male",
        },
        "Algenib": {
            "name": "Algenib",
            "description": "صوت ذكوري واضح",
            "gender": "male",
        },
        "Aoede": {
            "name": "Aoede",
            "description": "صوت أنثوي ناعم",
            "gender": "female",
        },
        "Charon": {
            "name": "Charon",
            "description": "صوت ذكوري درامي",
            "gender": "male",
        },
        "Kore": {
            "name": "Kore",
            "description": "صوت أنثوي قوي",
            "gender": "female",
        },
    }

    # ─── Director's Notes ─────────────────────────────────────────
    STYLE_PRESETS = {
        "motivational": {
            "audio_profile": "A smooth, premium commercial voice.",
            "directors_note": "Style: Promo/Hype. Pace: Natural. Accent: Neutral.",
            "scene_context": (
                "Premium commercial. Dynamic pacing—starts intrigued, ends punchy. "
                "Tone is polished, persuasive, and inviting."
            ),
        },
        "educational": {
            "audio_profile": "A clear, authoritative narrator voice.",
            "directors_note": "Style: Documentary/Educational. Pace: Steady. Accent: Neutral.",
            "scene_context": (
                "Premium documentary narration. Clear pacing for understanding. "
                "Tone is knowledgeable, engaging, and trustworthy."
            ),
        },
        "story": {
            "audio_profile": "A warm, expressive storyteller voice.",
            "directors_note": "Style: Narrative/Cinematic. Pace: Natural. Accent: Neutral.",
            "scene_context": (
                "Cinematic storytelling. Pacing varies with emotional beats."
            ),
        },
        "quote": {
            "audio_profile": "A profound, contemplative voice.",
            "directors_note": "Style: Philosophical/Reflective. Pace: Slow. Accent: Neutral.",
            "scene_context": (
                "Profound quote delivery. Slow, deliberate pacing."
            ),
        },
        "promo": {
            "audio_profile": "A smooth, premium commercial voice.",
            "directors_note": "Style: Promo/Hype. Pace: Natural. Accent: Neutral.",
            "scene_context": (
                "Premium commercial. Dynamic pacing—starts intrigued, ends punchy."
            ),
        },
        "viral": {
            "audio_profile": "A high-energy, attention-grabbing voice.",
            "directors_note": "Style: Viral/Social Media. Pace: Fast. Accent: Neutral.",
            "scene_context": (
                "Viral social media content. Energetic pacing."
            ),
        },
        "psychological": {
            "audio_profile": "A deep, thoughtful, mysterious voice.",
            "directors_note": "Style: Psychological/Deep. Pace: Slow and impactful. Accent: Neutral.",
            "scene_context": (
                "Deep psychological content. Slow, weighted pacing for maximum impact."
            ),
        },
    }

    # ─── إعدادات النموذج ──────────────────────────────────────────
    MODEL_NAME = "gemini-3.1-flash-tts-preview"
    DEFAULT_TEMPERATURE = 1.0
    
    # 🆕 إعدادات تقسيم النص
    MAX_CHARS_PER_CHUNK = 500  # 500 حرف لكل قطعة (آمن)
    MAX_RETRIES = 3             # 3 محاولات لكل قطعة
    CHUNK_TIMEOUT = 60          # 60 ثانية لكل قطعة

    # ════════════════════════════════════════════════════════════════
    def __init__(self):
        """تهيئة المحرك."""
        self.api_key = os.getenv("GEMINI_API_KEY", "")

        if not self.api_key:
            raise RuntimeError(
                "❌ GEMINI_API_KEY غير موجود!\n"
                "   أضفه في GitHub Secrets أو .env"
            )

        self.voice_name = os.getenv("GEMINI_VOICE", "Achird")
        self.style_preset = os.getenv("GEMINI_STYLE", "motivational")
        self.temperature = float(os.getenv("GEMINI_TEMPERATURE", "1.0"))
        
        # 🆕 إعدادات قابلة للتخصيص
        self.max_chars = int(os.getenv("GEMINI_MAX_CHARS_PER_CHUNK", str(self.MAX_CHARS_PER_CHUNK)))
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
            f"🎙️ GeminiTTSEngine v2.0 | Voice: {self.voice_name} | "
            f"Style: {self.style_preset} | Max chars/chunk: {self.max_chars}"
        )

    def _init_client(self) -> None:
        """تهيئة Gemini client."""
        try:
            from google import genai
            self._client = genai.Client(api_key=self.api_key)
            logger.debug("✓ Gemini client initialized")
        except ImportError:
            raise RuntimeError(
                "❌ google-genai غير مثبت!\n"
                "   شغّل: pip install google-genai"
            )
        except Exception as e:
            raise RuntimeError(f"❌ فشل تهيئة Gemini client: {e}")

    # ════════════════════════════════════════════════════════════════
    #                    🎯 التوليد الرئيسي مع تقسيم النص
    # ════════════════════════════════════════════════════════════════
    def generate_audio(
        self,
        script: dict,
        output_path: str,
        voice: Optional[str] = None,
        style: Optional[str] = None,
    ) -> str:
        """
        🎯 توليد الصوت مع تقسيم النص الطويل تلقائياً.
        """
        # استخراج النص
        full_text = self._extract_text(script)

        if not full_text.strip():
            raise ValueError("❌ لا يوجد نص للتحويل")

        voice_name = voice or self.voice_name
        style_preset = style or self.style_preset

        logger.info(
            f"🎙️ توليد الصوت | Voice: {voice_name} | "
            f"Style: {style_preset} | Length: {len(full_text)} chars"
        )

        # 🆕 تقسيم النص لقطع
        chunks = self._split_text_into_chunks(full_text)
        logger.info(f"   📦 تقسيم النص إلى {len(chunks)} قطعة")

        Path(output_path).parent.mkdir(parents=True, exist_ok=True)

        # 🆕 توليد كل قطعة وجمعها
        all_audio_data = bytearray()
        successful_chunks = 0

        for i, chunk_text in enumerate(chunks, 1):
            logger.info(f"   🎤 معالجة قطعة {i}/{len(chunks)} ({len(chunk_text)} حرف)")
            
            chunk_audio = self._generate_chunk_with_retry(
                text=chunk_text,
                voice_name=voice_name,
                style_preset=style_preset,
                chunk_num=i,
                total_chunks=len(chunks),
            )
            
            if chunk_audio:
                all_audio_data.extend(chunk_audio)
                successful_chunks += 1
                logger.info(f"   ✓ قطعة {i}/{len(chunks)} ({len(chunk_audio)/1024:.1f} KB)")
            else:
                logger.warning(f"   ⚠ فشلت قطعة {i}/{len(chunks)}")

        if successful_chunks == 0:
            raise RuntimeError("❌ فشلت كل القطع!")

        logger.info(
            f"   ✅ تم توليد {successful_chunks}/{len(chunks)} قطعة "
            f"({len(all_audio_data)/1024:.1f} KB)"
        )

        # حفظ الملف
        self._save_audio(bytes(all_audio_data), output_path)

        file_size_kb = Path(output_path).stat().st_size / 1024
        logger.info(f"✓ تم حفظ الصوت: {output_path} ({file_size_kb:.1f} KB)")

        return output_path

    # ════════════════════════════════════════════════════════════════
    #                    🆕 تقسيم النص الذكي
    # ════════════════════════════════════════════════════════════════
    def _split_text_into_chunks(self, text: str) -> List[str]:
        """
        🆕 تقسيم النص لقطع صغيرة عند نهايات الجمل.
        """
        if len(text) <= self.max_chars:
            return [text]

        chunks = []
        # القواطع المنطقية (مرتبة حسب الأولوية)
        delimiters = ['. ', '! ', '? ', '... ', '،', '؛', '\n', ' ']
        
        remaining = text
        while remaining:
            if len(remaining) <= self.max_chars:
                chunks.append(remaining.strip())
                break
            
            # ابحث عن أفضل نقطة قطع
            best_pos = -1
            chunk_window = remaining[:self.max_chars]
            
            for delim in delimiters:
                pos = chunk_window.rfind(delim)
                if pos > self.max_chars * 0.5:  # على الأقل 50% من الحد
                    best_pos = pos + len(delim)
                    break
            
            if best_pos == -1:
                # لم نجد قاطع منطقي، اقطع عند المسافة
                best_pos = chunk_window.rfind(' ')
                if best_pos == -1:
                    best_pos = self.max_chars
            
            chunks.append(remaining[:best_pos].strip())
            remaining = remaining[best_pos:].strip()
        
        return [c for c in chunks if c]  # إزالة القطع الفارغة

    # ════════════════════════════════════════════════════════════════
    #                    🆕 توليد قطعة مع Retry
    # ════════════════════════════════════════════════════════════════
    def _generate_chunk_with_retry(
        self,
        text: str,
        voice_name: str,
        style_preset: str,
        chunk_num: int,
        total_chunks: int,
    ) -> Optional[bytes]:
        """🆕 توليد قطعة مع إعادة المحاولة عند الفشل."""
        for attempt in range(1, self.max_retries + 1):
            try:
                if attempt > 1:
                    logger.info(f"      🔄 إعادة محاولة {attempt}/{self.max_retries}...")
                    time.sleep(2 * attempt)  # exponential backoff
                
                audio_data = self._generate_speech_chunk(
                    text=text,
                    voice_name=voice_name,
                    style_preset=style_preset,
                )
                
                if audio_data and len(audio_data) > 1000:  # على الأقل 1 KB
                    return audio_data
                else:
                    logger.warning(f"      ⚠ قطعة فارغة (محاولة {attempt})")
                    
            except Exception as e:
                logger.warning(f"      ⚠ فشل (محاولة {attempt}): {str(e)[:100]}")
                if attempt == self.max_retries:
                    logger.error(f"      ❌ فشلت كل المحاولات")
        
        return None

    # ════════════════════════════════════════════════════════════════
    #                    توليد قطعة واحدة بـ Gemini
    # ════════════════════════════════════════════════════════════════
    def _generate_speech_chunk(
        self,
        text: str,
        voice_name: str,
        style_preset: str,
    ) -> bytes:
        """توليد الصوت لقطعة نصية واحدة."""
        from google.genai import types

        style_config = self.STYLE_PRESETS.get(
            style_preset, self.STYLE_PRESETS["motivational"]
        )

        prompt = self._build_professional_prompt(text, style_config)

        contents = [
            types.Content(
                role="user",
                parts=[types.Part.from_text(text=prompt)],
            ),
        ]

        generate_content_config = types.GenerateContentConfig(
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

        # توليد streaming
        audio_chunks = []
        mime_type = None

        for chunk in self._client.models.generate_content_stream(
            model=self.MODEL_NAME,
            contents=contents,
            config=generate_content_config,
        ):
            if chunk.parts is None:
                continue

            if chunk.parts[0].inline_data and chunk.parts[0].inline_data.data:
                inline_data = chunk.parts[0].inline_data
                audio_chunks.append(inline_data.data)
                if mime_type is None:
                    mime_type = inline_data.mime_type

        if not audio_chunks:
            raise RuntimeError("لم يتم استلام أي بيانات صوتية")

        # دمج
        raw_audio = b"".join(audio_chunks)

        # تحويل إلى WAV
        file_extension = mimetypes.guess_extension(mime_type) if mime_type else None
        if file_extension is None or "wav" not in (file_extension or ""):
            raw_audio = self._convert_to_wav(raw_audio, mime_type)

        return raw_audio

    # ════════════════════════════════════════════════════════════════
    #                    استخراج النص
    # ════════════════════════════════════════════════════════════════
    def _extract_text(self, script: dict) -> str:
        """استخراج النص الكامل من السكربت."""
        # 1. جرب full_text
        full_text = script.get("full_text", "").strip()
        if full_text:
            return full_text

        # 2. ثم scenes
        scenes = script.get("scenes", [])
        if scenes:
            texts = [s.get("text", "").strip() for s in scenes if s.get("text")]
            return " ".join(texts)

        # 3. ثم hook
        return script.get("hook", "")

    # ════════════════════════════════════════════════════════════════
    #                    Prompt احترافي
    # ════════════════════════════════════════════════════════════════
    def _build_professional_prompt(self, text: str, style_config: Dict) -> str:
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
    #                    معالجة الصوت
    # ════════════════════════════════════════════════════════════════
    def _save_audio(self, audio_data: bytes, output_path: str) -> None:
        """حفظ بيانات الصوت إلى ملف."""
        original_path = output_path
        wants_mp3 = output_path.endswith(".mp3")
        
        wav_path = output_path.replace(".mp3", ".wav") if wants_mp3 else output_path
        if not wav_path.endswith(".wav"):
            wav_path += ".wav"

        # 🆕 إذا كان عدة قطع WAV، نحتاج معالجة خاصة
        # كل قطعة لها header، نحتاج دمجها بشكل صحيح
        merged_audio = self._merge_wav_chunks(audio_data)
        
        with open(wav_path, "wb") as f:
            f.write(merged_audio)

        if wants_mp3:
            self._convert_wav_to_mp3(wav_path, original_path)
            try:
                Path(wav_path).unlink(missing_ok=True)
            except Exception:
                pass

    def _merge_wav_chunks(self, audio_data: bytes) -> bytes:
        """
        🆕 دمج عدة قطع WAV في ملف واحد صحيح.
        كل قطعة WAV لها header منفصل، نحتاج فصلها ودمج الـ PCM data فقط.
        """
        try:
            # ابحث عن جميع headers الـ RIFF
            chunks_data = []
            sample_rate = 24000
            bits_per_sample = 16
            num_channels = 1
            
            pos = 0
            while pos < len(audio_data):
                # ابحث عن RIFF header
                if audio_data[pos:pos+4] == b'RIFF':
                    # تخطي header (44 bytes)
                    # قراءة sample_rate من position 24
                    if pos + 28 <= len(audio_data):
                        sample_rate = int.from_bytes(audio_data[pos+24:pos+28], 'little')
                    if pos + 36 <= len(audio_data):
                        bits_per_sample = int.from_bytes(audio_data[pos+34:pos+36], 'little')
                    
                    # ابحث عن "data" chunk
                    data_pos = audio_data.find(b'data', pos)
                    if data_pos == -1:
                        break
                    
                    # حجم البيانات
                    data_size = int.from_bytes(
                        audio_data[data_pos+4:data_pos+8], 'little'
                    )
                    
                    # استخرج PCM data
                    pcm_start = data_pos + 8
                    pcm_end = pcm_start + data_size
                    
                    if pcm_end <= len(audio_data):
                        chunks_data.append(audio_data[pcm_start:pcm_end])
                    
                    pos = pcm_end
                else:
                    pos += 1
            
            if not chunks_data:
                # لم نجد WAV headers، نفترض أنها PCM raw
                return audio_data
            
            # دمج كل PCM data
            merged_pcm = b''.join(chunks_data)
            
            # بناء WAV header جديد
            data_size = len(merged_pcm)
            bytes_per_sample = bits_per_sample // 8
            block_align = num_channels * bytes_per_sample
            byte_rate = sample_rate * block_align
            chunk_size = 36 + data_size

            header = struct.pack(
                "<4sI4s4sIHHIIHH4sI",
                b"RIFF",
                chunk_size,
                b"WAVE",
                b"fmt ",
                16,
                1,
                num_channels,
                sample_rate,
                byte_rate,
                block_align,
                bits_per_sample,
                b"data",
                data_size,
            )
            
            return header + merged_pcm
            
        except Exception as e:
            logger.warning(f"⚠ فشل دمج WAV chunks: {e}, استخدام البيانات كما هي")
            return audio_data

    def _convert_wav_to_mp3(self, wav_path: str, mp3_path: str) -> None:
        """تحويل WAV إلى MP3."""
        try:
            from pydub import AudioSegment
            audio = AudioSegment.from_wav(wav_path)
            audio.export(mp3_path, format="mp3", bitrate="192k")
        except Exception as e:
            logger.warning(f"⚠ فشل التحويل إلى MP3: {e}")
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
    #                    دوال مساعدة
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

    # اختبار بنص طويل
    test_script = {
        "full_text": (
            "السلام عليكم ورحمة الله وبركاته. "
            "اليوم سنتحدث عن السر العلمي للنجاح في الحياة. "
            "هل تعلم أن 95% من الناس يفشلون لسبب واحد فقط؟ "
            "إنهم يجهلون قاعدة بسيطة جداً. "
            "دراسة من جامعة هارفارد على آلاف الناجحين "
            "كشفت سراً مذهلاً. "
            "كل من حقق نجاحاً عظيماً... "
            "كان يفعل هذا الأمر بشكل يومي. "
            "إنها قاعدة الـ 1% للتحسن المستمر. "
            "ابدأ اليوم... وستلاحظ الفرق خلال 90 يوم!"
        ),
    }

    output_file = sys.argv[1] if len(sys.argv) > 1 else "test_gemini.wav"

    try:
        engine = GeminiTTSEngine()

        print(f"\n📊 معلومات:")
        print(f"   • Voice: {engine.voice_name}")
        print(f"   • Style: {engine.style_preset}")
        print(f"   • Max chars/chunk: {engine.max_chars}")
        print(f"   • Text length: {len(test_script['full_text'])} chars")

        print(f"\n🎙️ توليد صوت تجريبي → {output_file}")
        engine.generate_audio(test_script, output_file)

        print(f"\n✅ تم بنجاح! تحقق من الملف: {output_file}")

    except Exception as e:
        print(f"\n❌ خطأ: {e}")
        sys.exit(1)
