"""
🎙️ Gemini TTS Engine — توليد الصوت العربي بـ Google Gemini
═══════════════════════════════════════════════════════════════
يستخدم Gemini 3.1 Flash TTS:
  ✓ صوت طبيعي وعالي الجودة
  ✓ دعم كامل للعربية
  ✓ تحكم كامل في الـ Style والـ Pace
  ✓ 5 أصوات احترافية مختلفة
  ✓ نمط Director's Note لتحكم أفضل

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
    """محرك توليد الصوت بـ Google Gemini TTS."""

    # ─── الأصوات المتاحة ──────────────────────────────────────────
    AVAILABLE_VOICES = {
        "Achird": {
            "name": "Achird",
            "description": "صوت ذكوري عميق وحاد - مناسب للتحفيزي",
            "gender": "male",
            "style": "deep",
        },
        "Algenib": {
            "name": "Algenib",
            "description": "صوت ذكوري واضح - مناسب للسرد",
            "gender": "male",
            "style": "clear",
        },
        "Aoede": {
            "name": "Aoede",
            "description": "صوت أنثوي ناعم - مناسب للقصص",
            "gender": "female",
            "style": "soft",
        },
        "Charon": {
            "name": "Charon",
            "description": "صوت ذكوري درامي - مناسب للمحتوى الجاد",
            "gender": "male",
            "style": "dramatic",
        },
        "Kore": {
            "name": "Kore",
            "description": "صوت أنثوي قوي - مناسب للأخبار",
            "gender": "female",
            "style": "strong",
        },
    }

    # ─── أنماط الصوت (Director's Notes) ──────────────────────────
    STYLE_PRESETS = {
        "motivational": {
            "audio_profile": "A smooth, premium commercial voice with strong emotional impact.",
            "directors_note": (
                "Style: Inspirational/Motivational. "
                "Pace: Dynamic, builds energy. "
                "Tone: Powerful, uplifting, persuasive. "
                "Accent: Neutral Modern Standard Arabic."
            ),
            "scene_context": (
                "Premium motivational content. Dynamic pacing—starts intriguing, "
                "builds momentum, ends with powerful call-to-action. "
                "Tone is polished, persuasive, and inspiring."
            ),
        },
        "educational": {
            "audio_profile": "A clear, authoritative narrator voice.",
            "directors_note": (
                "Style: Educational/Documentary. "
                "Pace: Steady, clear. "
                "Tone: Knowledgeable, engaging, trustworthy. "
                "Accent: Neutral Modern Standard Arabic."
            ),
            "scene_context": (
                "Educational documentary narration. Clear pacing for understanding, "
                "engaging tone to maintain attention."
            ),
        },
        "story": {
            "audio_profile": "A warm, expressive storyteller voice.",
            "directors_note": (
                "Style: Narrative/Storytelling. "
                "Pace: Natural with emotional variation. "
                "Tone: Engaging, expressive, cinematic. "
                "Accent: Neutral Modern Standard Arabic."
            ),
            "scene_context": (
                "Cinematic storytelling. Pacing varies with emotional beats. "
                "Tone is warm and immersive."
            ),
        },
        "quote": {
            "audio_profile": "A profound, contemplative voice.",
            "directors_note": (
                "Style: Philosophical/Reflective. "
                "Pace: Slow, deliberate. "
                "Tone: Deep, thoughtful, meaningful. "
                "Accent: Neutral Modern Standard Arabic."
            ),
            "scene_context": (
                "Profound quote delivery. Slow, deliberate pacing with weight on each word. "
                "Tone is contemplative and impactful."
            ),
        },
        "promo": {
            "audio_profile": "A smooth, premium commercial voice.",
            "directors_note": (
                "Style: Promo/Hype. "
                "Pace: Natural. "
                "Accent: Neutral."
            ),
            "scene_context": (
                "Premium commercial. Dynamic pacing—starts intrigued, ends punchy. "
                "Tone is polished, persuasive, and inviting."
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

        # الإعدادات
        self.voice_name = os.getenv("GEMINI_VOICE", "Achird")
        self.style_preset = os.getenv("GEMINI_STYLE", "motivational")

        # تأكد من صحة الإعدادات
        if self.voice_name not in self.AVAILABLE_VOICES:
            logger.warning(
                f"⚠ صوت غير معروف '{self.voice_name}'، استخدام Achird"
            )
            self.voice_name = "Achird"

        # تحميل client
        self._client = None
        self._init_client()

        logger.info(
            f"🎙️ GeminiTTSEngine | Voice: {self.voice_name} | "
            f"Style: {self.style_preset}"
        )

    def _init_client(self) -> None:
        """تهيئة Gemini client (lazy)."""
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
            script: السكربت الكامل (يحتوي full_text أو scenes)
            output_path: مسار ملف الصوت الناتج
            voice: اسم الصوت (اختياري)
            style: نمط الأداء (اختياري)

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
    #                    توليد الصوت بـ Gemini
    # ════════════════════════════════════════════════════════════════
    def _generate_speech(
        self,
        text: str,
        voice_name: str,
        style_preset: str,
    ) -> bytes:
        """توليد الصوت بـ Gemini API."""
        from google.genai import types

        # بناء الـ prompt
        style_config = self.STYLE_PRESETS.get(
            style_preset, self.STYLE_PRESETS["motivational"]
        )

        prompt = self._build_prompt(text, style_config)

        # إعداد الـ contents
        contents = [
            types.Content(
                role="user",
                parts=[types.Part.from_text(text=prompt)],
            ),
        ]

        # إعدادات التوليد
        generate_content_config = types.GenerateContentConfig(
            temperature=self.DEFAULT_TEMPERATURE,
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
            elif chunk.text:
                logger.debug(f"   📝 {chunk.text}")

        if not audio_chunks:
            raise RuntimeError("❌ لم يتم استلام أي بيانات صوتية")

        # دمج كل القطع
        audio_data = b"".join(audio_chunks)

        # تحويل إلى WAV إذا كان raw PCM
        if mime_type and "wav" not in mime_type.lower():
            audio_data = self._convert_to_wav(audio_data, mime_type)

        logger.info(
            f"   ✓ تم استلام {len(audio_chunks)} chunks "
            f"({len(audio_data) / 1024:.1f} KB)"
        )

        return audio_data

    def _build_prompt(self, text: str, style_config: Dict) -> str:
        """بناء الـ prompt لـ Gemini."""
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
        if not output_path.endswith((".wav", ".mp3", ".m4a")):
            output_path += ".wav"

        with open(output_path, "wb") as f:
            f.write(audio_data)

        # إذا كان MP3 مطلوب، حوّل من WAV
        if output_path.endswith(".mp3"):
            self._convert_wav_to_mp3(output_path)

    def _convert_wav_to_mp3(self, wav_path: str) -> None:
        """تحويل WAV إلى MP3 باستخدام pydub."""
        try:
            from pydub import AudioSegment
            
            audio = AudioSegment.from_wav(wav_path)
            mp3_path = wav_path  # نفس الاسم
            audio.export(mp3_path, format="mp3", bitrate="192k")
            logger.debug(f"✓ تم التحويل إلى MP3: {mp3_path}")
            
        except Exception as e:
            logger.warning(f"⚠ فشل التحويل إلى MP3: {e}")

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
        return header + audio_data

    def _parse_audio_mime_type(self, mime_type: str) -> Dict[str, int]:
        """تحليل mime type لاستخراج معلومات الصوت."""
        bits_per_sample = 16
        rate = 24000

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

    # اختبار بسيط
    test_script = {
        "full_text": "السلام عليكم ورحمة الله وبركاته. هذا اختبار لمحرك Gemini TTS العربي.",
    }

    output_file = sys.argv[1] if len(sys.argv) > 1 else "test_gemini.wav"

    try:
        engine = GeminiTTSEngine()
        
        print("\n📦 الأصوات المتاحة:")
        for name, info in engine.list_voices().items():
            print(f"   • {name}: {info['description']}")

        print(f"\n🎙️ توليد صوت تجريبي → {output_file}")
        engine.generate_audio(test_script, output_file)
        
        print(f"\n✅ تم بنجاح! تحقق من الملف: {output_file}")
        
    except Exception as e:
        print(f"\n❌ خطأ: {e}")
        sys.exit(1)
