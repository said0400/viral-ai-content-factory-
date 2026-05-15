"""
🎙️ Gemini TTS Engine — صوت احترافي مع Director's Notes متطورة
═══════════════════════════════════════════════════════════════
يستخدم Gemini 3.1 Flash TTS:
  ✓ Promo/Hype style (Premium Commercial Voice)
  ✓ 5 أصوات احترافية
  ✓ Director's Notes متطورة لكل نمط
  ✓ Sound Stage Booth context
  ✓ تحكم دقيق في الـ Pace والـ Tone

ضع في: engine/voice/gemini_tts_engine.py
═══════════════════════════════════════════════════════════════
"""

import os
import struct
import logging
import mimetypes
from pathlib import Path
from typing import Optional, Dict

logger = logging.getLogger(__name__)


class GeminiTTSEngine:
    """محرك توليد الصوت الاحترافي بـ Google Gemini TTS."""

    # ─── الأصوات المتاحة ──────────────────────────────────────────
    AVAILABLE_VOICES = {
        "Achird": {
            "name": "Achird",
            "description": "صوت ذكوري عميق وحاد - مثالي للـ Promo",
            "gender": "male",
            "style": "deep premium",
        },
        "Algenib": {
            "name": "Algenib",
            "description": "صوت ذكوري واضح - مناسب للسرد",
            "gender": "male",
            "style": "clear narrator",
        },
        "Aoede": {
            "name": "Aoede",
            "description": "صوت أنثوي ناعم - مناسب للقصص",
            "gender": "female",
            "style": "soft storyteller",
        },
        "Charon": {
            "name": "Charon",
            "description": "صوت ذكوري درامي - مناسب للمحتوى الجاد",
            "gender": "male",
            "style": "dramatic deep",
        },
        "Kore": {
            "name": "Kore",
            "description": "صوت أنثوي قوي - مناسب للأخبار",
            "gender": "female",
            "style": "strong news",
        },
    }

    # ═════════════════════════════════════════════════════════════════
    # 🎬 Director's Notes احترافية (مطابقة لـ Sound Stage Booth)
    # ═════════════════════════════════════════════════════════════════
    STYLE_PRESETS = {
        # ⭐ النمط الافتراضي - Promo/Hype (مطابق لمثالك)
        "motivational": {
            "audio_profile": "A smooth, premium commercial voice.",
            "directors_note": "Style: Promo/Hype. Pace: Natural. Accent: Neutral.",
            "scene_context": (
                "Premium commercial. Dynamic pacing—starts intrigued, ends punchy. "
                "Tone is polished, persuasive, and inviting."
            ),
        },
        
        # 🎓 تعليمي
        "educational": {
            "audio_profile": "A clear, authoritative narrator voice.",
            "directors_note": "Style: Documentary/Educational. Pace: Steady. Accent: Neutral.",
            "scene_context": (
                "Premium documentary narration. Clear pacing for understanding. "
                "Tone is knowledgeable, engaging, and trustworthy."
            ),
        },
        
        # 📖 قصص
        "story": {
            "audio_profile": "A warm, expressive storyteller voice.",
            "directors_note": "Style: Narrative/Cinematic. Pace: Natural. Accent: Neutral.",
            "scene_context": (
                "Cinematic storytelling. Pacing varies with emotional beats—slow during reflection, "
                "builds during tension. Tone is warm, immersive, and captivating."
            ),
        },
        
        # 💭 اقتباسات
        "quote": {
            "audio_profile": "A profound, contemplative voice.",
            "directors_note": "Style: Philosophical/Reflective. Pace: Slow. Accent: Neutral.",
            "scene_context": (
                "Profound quote delivery. Slow, deliberate pacing with weight on each word. "
                "Tone is contemplative, deep, and impactful."
            ),
        },
        
        # 📢 ترويجي (نفس motivational)
        "promo": {
            "audio_profile": "A smooth, premium commercial voice.",
            "directors_note": "Style: Promo/Hype. Pace: Natural. Accent: Neutral.",
            "scene_context": (
                "Premium commercial. Dynamic pacing—starts intrigued, ends punchy. "
                "Tone is polished, persuasive, and inviting."
            ),
        },
        
        # 🎯 محتوى تيكتوك / ريلز
        "viral": {
            "audio_profile": "A high-energy, attention-grabbing voice.",
            "directors_note": "Style: Viral/Social Media. Pace: Fast and engaging. Accent: Neutral.",
            "scene_context": (
                "Viral social media content. Energetic pacing that hooks attention immediately. "
                "Tone is exciting, modern, and relatable."
            ),
        },
        
        # 🎙️ بودكاست
        "podcast": {
            "audio_profile": "A conversational, warm podcast host voice.",
            "directors_note": "Style: Conversational/Podcast. Pace: Natural conversation. Accent: Neutral.",
            "scene_context": (
                "Premium podcast hosting. Natural conversational pacing. "
                "Tone is friendly, intelligent, and engaging."
            ),
        },
        
        # 📰 أخبار
        "news": {
            "audio_profile": "A professional news anchor voice.",
            "directors_note": "Style: News/Broadcast. Pace: Clear and authoritative. Accent: Neutral.",
            "scene_context": (
                "Professional news broadcast. Authoritative pacing with clarity. "
                "Tone is professional, credible, and informative."
            ),
        },
    }

    # ─── إعدادات النموذج ──────────────────────────────────────────
    MODEL_NAME = "gemini-3.1-flash-tts-preview"
    DEFAULT_TEMPERATURE = 1.0

    # ════════════════════════════════════════════════════════════════
    def __init__(self):
        """تهيئة المحرك."""
        self.api_key = os.getenv("GEMINI_API_KEY", "")

        if not self.api_key:
            raise RuntimeError(
                "❌ GEMINI_API_KEY غير موجود!\n"
                "   أضفه في GitHub Secrets أو .env"
            )

        # الإعدادات من .env
        self.voice_name = os.getenv("GEMINI_VOICE", "Achird")
        self.style_preset = os.getenv("GEMINI_STYLE", "motivational")
        self.temperature = float(os.getenv("GEMINI_TEMPERATURE", "1.0"))

        # تحقق من صحة الإعدادات
        if self.voice_name not in self.AVAILABLE_VOICES:
            logger.warning(
                f"⚠ صوت غير معروف '{self.voice_name}'، استخدام Achird"
            )
            self.voice_name = "Achird"

        if self.style_preset not in self.STYLE_PRESETS:
            logger.warning(
                f"⚠ نمط غير معروف '{self.style_preset}'، استخدام motivational"
            )
            self.style_preset = "motivational"

        # تحميل client
        self._client = None
        self._init_client()

        logger.info(
            f"🎙️ GeminiTTSEngine | Voice: {self.voice_name} | "
            f"Style: {self.style_preset} | Temp: {self.temperature}"
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
    #                    التوليد الرئيسي
    # ════════════════════════════════════════════════════════════════
    def generate_audio(
        self,
        script: dict,
        output_path: str,
        voice: Optional[str] = None,
        style: Optional[str] = None,
    ) -> str:
        """
        🎯 توليد الصوت من السكربت.

        Args:
            script: السكربت الكامل
            output_path: مسار ملف الصوت الناتج
            voice: اسم الصوت (اختياري - يتجاوز الافتراضي)
            style: نمط الأداء (اختياري - يتجاوز الافتراضي)

        Returns:
            مسار الملف الناتج
        """
        # استخراج النص
        full_text = self._extract_text(script)

        if not full_text.strip():
            raise ValueError("❌ لا يوجد نص للتحويل")

        # استخدم القيم المرسلة أو الافتراضية
        voice_name = voice or self.voice_name
        style_preset = style or self.style_preset

        logger.info(
            f"🎙️ توليد الصوت | Voice: {voice_name} | "
            f"Style: {style_preset} | Length: {len(full_text)} chars"
        )

        # التأكد من وجود مجلد الإخراج
        Path(output_path).parent.mkdir(parents=True, exist_ok=True)

        # توليد الصوت
        try:
            audio_data = self._generate_speech(
                text=full_text,
                voice_name=voice_name,
                style_preset=style_preset,
            )

            # حفظ الملف
            self._save_audio(audio_data, output_path)

            # عرض المعلومات
            file_size_kb = Path(output_path).stat().st_size / 1024
            logger.info(f"✓ تم حفظ الصوت: {output_path} ({file_size_kb:.1f} KB)")

            return output_path

        except Exception as e:
            logger.error(f"❌ فشل توليد الصوت: {e}")
            raise

    def _extract_text(self, script: dict) -> str:
        """استخراج النص الكامل من السكربت."""
        # 1. جرب full_text أولاً
        full_text = script.get("full_text", "").strip()
        if full_text:
            return full_text

        # 2. ثم جمّع من المشاهد
        scenes = script.get("scenes", [])
        if scenes:
            texts = [s.get("text", "").strip() for s in scenes if s.get("text")]
            return " ".join(texts)

        # 3. ثم hook
        return script.get("hook", "")

    # ════════════════════════════════════════════════════════════════
    #                    🎬 توليد الصوت بـ Director's Note
    # ════════════════════════════════════════════════════════════════
    def _generate_speech(
        self,
        text: str,
        voice_name: str,
        style_preset: str,
    ) -> bytes:
        """توليد الصوت بـ Gemini API مع Director's Note احترافية."""
        from google.genai import types

        # 🎯 بناء الـ prompt المطابق تماماً للنمط الاحترافي
        style_config = self.STYLE_PRESETS.get(
            style_preset, self.STYLE_PRESETS["motivational"]
        )

        prompt = self._build_professional_prompt(text, style_config)

        # طباعة الـ prompt للتشخيص
        logger.debug(f"📝 Prompt:\n{prompt[:300]}...")

        # إعداد الـ contents
        contents = [
            types.Content(
                role="user",
                parts=[types.Part.from_text(text=prompt)],
            ),
        ]

        # إعدادات التوليد
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

        # توليد الصوت (streaming)
        logger.info("   ⏳ جاري التوليد...")

        audio_chunks = []
        mime_type = None
        chunk_count = 0

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
                chunk_count += 1
                
                # طباعة التقدم كل 5 chunks
                if chunk_count % 5 == 0:
                    logger.info(f"   📥 استلام... ({chunk_count} chunks)")
                    
            elif chunk.text:
                logger.debug(f"   📝 {chunk.text}")

        if not audio_chunks:
            raise RuntimeError("❌ لم يتم استلام أي بيانات صوتية")

        # دمج كل القطع
        audio_data = b"".join(audio_chunks)

        # تحويل إلى WAV إذا كان raw PCM
        file_extension = mimetypes.guess_extension(mime_type) if mime_type else None
        if file_extension is None or "wav" not in (file_extension or ""):
            audio_data = self._convert_to_wav(audio_data, mime_type)

        logger.info(
            f"   ✓ تم استلام {chunk_count} chunks "
            f"({len(audio_data) / 1024:.1f} KB)"
        )

        return audio_data

    # ════════════════════════════════════════════════════════════════
    # 🎯 🎯 🎯 الـ Prompt الاحترافي (مطابق تماماً لمثالك) 🎯 🎯 🎯
    # ════════════════════════════════════════════════════════════════
    def _build_professional_prompt(self, text: str, style_config: Dict) -> str:
        """
        🎯 بناء الـ prompt الاحترافي بنفس صيغة Sound Stage Booth.
        
        مطابق تماماً للـ prompt الذي يعطي أفضل نتائج صوتية.
        """
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
        # تحديد الامتداد
        original_path = output_path
        wants_mp3 = output_path.endswith(".mp3")
        
        # حفظ كـ WAV أولاً
        wav_path = output_path.replace(".mp3", ".wav") if wants_mp3 else output_path
        if not wav_path.endswith(".wav"):
            wav_path += ".wav"

        with open(wav_path, "wb") as f:
            f.write(audio_data)

        # تحويل إلى MP3 إذا مطلوب
        if wants_mp3:
            self._convert_wav_to_mp3(wav_path, original_path)
            # حذف الـ WAV المؤقت
            try:
                Path(wav_path).unlink(missing_ok=True)
            except Exception:
                pass

    def _convert_wav_to_mp3(self, wav_path: str, mp3_path: str) -> None:
        """تحويل WAV إلى MP3 باستخدام pydub."""
        try:
            from pydub import AudioSegment
            audio = AudioSegment.from_wav(wav_path)
            audio.export(mp3_path, format="mp3", bitrate="192k")
            logger.debug(f"✓ تم التحويل إلى MP3: {mp3_path}")
        except Exception as e:
            logger.warning(f"⚠ فشل التحويل إلى MP3: {e}")
            # نسخ WAV كـ fallback
            import shutil
            shutil.copy(wav_path, mp3_path)

    def _convert_to_wav(self, audio_data: bytes, mime_type: str) -> bytes:
        """تحويل raw PCM إلى WAV (مطابق لمثالك)."""
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
            b"RIFF",          # ChunkID
            chunk_size,       # ChunkSize
            b"WAVE",          # Format
            b"fmt ",          # Subchunk1ID
            16,               # Subchunk1Size (16 for PCM)
            1,                # AudioFormat (1 for PCM)
            num_channels,     # NumChannels
            sample_rate,      # SampleRate
            byte_rate,        # ByteRate
            block_align,      # BlockAlign
            bits_per_sample,  # BitsPerSample
            b"data",          # Subchunk2ID
            data_size         # Subchunk2Size
        )
        return header + audio_data

    def _parse_audio_mime_type(self, mime_type: str) -> Dict[str, int]:
        """تحليل mime type (مطابق لمثالك)."""
        bits_per_sample = 16
        rate = 24000

        if not mime_type:
            return {"bits_per_sample": bits_per_sample, "rate": rate}

        parts = mime_type.split(";")
        for param in parts:
            param = param.strip()
            if param.lower().startswith("rate="):
                try:
                    rate_str = param.split("=", 1)[1]
                    rate = int(rate_str)
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
        """قائمة الأصوات المتاحة."""
        return self.AVAILABLE_VOICES

    def list_styles(self) -> Dict:
        """قائمة الأنماط المتاحة."""
        return self.STYLE_PRESETS


# ════════════════════════════════════════════════════════════════════════
#                    اختبار سريع
# ════════════════════════════════════════════════════════════════════════
if __name__ == "__main__":
    import sys

    # اختبار بسيط بنفس مثالك
    test_script = {
        "full_text": "السلام عليكم",
    }

    output_file = sys.argv[1] if len(sys.argv) > 1 else "test_gemini.wav"

    try:
        engine = GeminiTTSEngine()

        print("\n📦 الأصوات المتاحة:")
        for name, info in engine.list_voices().items():
            print(f"   • {name}: {info['description']}")

        print(f"\n🎬 الأنماط المتاحة:")
        for name in engine.list_styles().keys():
            print(f"   • {name}")

        print(f"\n🎙️ توليد صوت تجريبي → {output_file}")
        engine.generate_audio(test_script, output_file)

        print(f"\n✅ تم بنجاح! تحقق من الملف: {output_file}")

    except Exception as e:
        print(f"\n❌ خطأ: {e}")
        sys.exit(1)
