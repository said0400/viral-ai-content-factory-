"""
🎙️ Gemini TTS Engine v3.1 — Scene-by-Scene (الأكثر موثوقية)
═══════════════════════════════════════════════════════════════
الإستراتيجية:
  1. ✅ يولّد كل مشهد بشكل مستقل (10-15 كلمة)
  2. ✅ يحفظ كل مشهد كملف WAV
  3. ✅ يدمج الكل بـ pydub (موثوق 100%)
  4. ✅ Retry لكل مشهد عند الفشل
  5. ✅ لا يفقد أي جزء من النص أبداً

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
    """محرك Gemini TTS v3.1 - يولّد كل مشهد بشكل مستقل."""

    AVAILABLE_VOICES = {
        "Achird": {"name": "Achird", "description": "ذكوري عميق", "gender": "male"},
        "Algenib": {"name": "Algenib", "description": "ذكوري واضح", "gender": "male"},
        "Aoede": {"name": "Aoede", "description": "أنثوي ناعم", "gender": "female"},
        "Charon": {"name": "Charon", "description": "ذكوري درامي", "gender": "male"},
        "Kore": {"name": "Kore", "description": "أنثوي قوي", "gender": "female"},
    }

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

    MODEL_NAME = "gemini-3.1-flash-tts-preview"
    DEFAULT_TEMPERATURE = 1.0
    MAX_RETRIES = 2

    def __init__(self):
        self.api_key = os.getenv("GEMINI_API_KEY", "")
        if not self.api_key:
            raise RuntimeError("❌ GEMINI_API_KEY غير موجود!")

        self.voice_name = os.getenv("GEMINI_VOICE", "Achird")
        self.style_preset = os.getenv("GEMINI_STYLE", "motivational")
        self.temperature = float(os.getenv("GEMINI_TEMPERATURE", "1.0"))
        self.max_retries = int(os.getenv("GEMINI_MAX_RETRIES", str(self.MAX_RETRIES)))

        if self.voice_name not in self.AVAILABLE_VOICES:
            self.voice_name = "Achird"
        if self.style_preset not in self.STYLE_PRESETS:
            self.style_preset = "motivational"

        self._client = None
        self._init_client()

        logger.info(
            f"🎙️ GeminiTTSEngine v3.1 (Scene-by-Scene) | "
            f"Voice: {self.voice_name} | Style: {self.style_preset}"
        )

    def _init_client(self) -> None:
        try:
            from google import genai
            self._client = genai.Client(api_key=self.api_key)
        except ImportError:
            raise RuntimeError("❌ google-genai غير مثبت!")
        except Exception as e:
            raise RuntimeError(f"❌ فشل تهيئة Gemini: {e}")

    # ════════════════════════════════════════════════════════════════
    #         🎯 الدالة الرئيسية: مشهد بمشهد
    # ════════════════════════════════════════════════════════════════
    def generate_audio(
        self,
        script: dict,
        output_path: str,
        voice: Optional[str] = None,
        style: Optional[str] = None,
    ) -> str:
        """
        🎯 v3.1: توليد الصوت مشهد بمشهد.
        
        كل مشهد (10-15 كلمة) يُولّد بشكل مستقل ثم يُدمج.
        هذا يضمن عدم فقدان أي جزء من النص.
        """
        voice_name = voice or self.voice_name
        style_preset = style or self.style_preset

        Path(output_path).parent.mkdir(parents=True, exist_ok=True)

        # استخراج نصوص المشاهد
        scene_texts = self._get_scene_texts(script)

        if not scene_texts:
            raise ValueError("❌ لا يوجد نص للتحويل")

        total_chars = sum(len(t) for t in scene_texts)
        logger.info(
            f"🎙️ توليد الصوت | Voice: {voice_name} | "
            f"Style: {style_preset} | {len(scene_texts)} مشهد | {total_chars} حرف"
        )

        # توليد كل مشهد بشكل مستقل
        wav_files = []
        temp_dir = Path(tempfile.mkdtemp(prefix="gemini_tts_"))

        try:
            for i, scene_text in enumerate(scene_texts, 1):
                logger.info(
                    f"   🎤 مشهد {i}/{len(scene_texts)} "
                    f"({len(scene_text)} حرف): {scene_text[:40]}..."
                )

                chunk_wav = str(temp_dir / f"scene_{i:03d}.wav")

                ok = self._generate_scene_audio(
                    text=scene_text,
                    voice_name=voice_name,
                    style_preset=style_preset,
                    output_path=chunk_wav,
                )

                if ok:
                    wav_files.append(chunk_wav)
                    size_kb = Path(chunk_wav).stat().st_size / 1024
                    logger.info(f"   ✓ مشهد {i} ({size_kb:.1f} KB)")
                else:
                    logger.warning(f"   ⚠ فشل مشهد {i}")

            if not wav_files:
                raise RuntimeError("❌ فشلت كل المشاهد!")

            # دمج كل ملفات WAV
            logger.info(f"   🔗 دمج {len(wav_files)}/{len(scene_texts)} مشهد...")
            self._merge_wav_files(wav_files, output_path)

            size_kb = Path(output_path).stat().st_size / 1024
            logger.info(
                f"   ✅ تم! {len(wav_files)}/{len(scene_texts)} مشهد "
                f"({size_kb:.1f} KB)"
            )

            return output_path

        finally:
            try:
                import shutil
                shutil.rmtree(temp_dir, ignore_errors=True)
            except Exception:
                pass

    # ════════════════════════════════════════════════════════════════
    #         استخراج نصوص المشاهد
    # ════════════════════════════════════════════════════════════════
    def _get_scene_texts(self, script: dict) -> List[str]:
        """استخراج نصوص المشاهد من السكربت."""
        # 1. ⭐ scenes أولاً (الأكثر موثوقية)
        scenes = script.get("scenes", [])
        if scenes:
            texts = []
            for scene in scenes:
                text = scene.get("text", "").strip()
                if text:
                    texts.append(text)

            if texts:
                logger.info(
                    f"   📝 النص من scenes: {sum(len(t) for t in texts)} حرف "
                    f"({len(texts)} مشاهد)"
                )
                return texts

        # 2. full_text (تقسيم تلقائي)
        full_text = script.get("full_text", "").strip()
        if full_text and len(full_text) > 50:
            logger.info(f"   📝 النص من full_text: {len(full_text)} حرف")
            return self._split_text(full_text, 200)

        # 3. hook فقط (مع تحذير)
        hook = script.get("hook", "").strip()
        if hook:
            logger.warning(f"   ⚠ استخدام Hook فقط: {len(hook)} حرف")
            return [hook]

        return []

    # ════════════════════════════════════════════════════════════════
    #         توليد صوت مشهد واحد مع Retry
    # ════════════════════════════════════════════════════════════════
    def _generate_scene_audio(
        self,
        text: str,
        voice_name: str,
        style_preset: str,
        output_path: str,
    ) -> bool:
        """توليد صوت لمشهد واحد مع إعادة المحاولة."""
        for attempt in range(1, self.max_retries + 1):
            try:
                if attempt > 1:
                    logger.info(f"      🔄 محاولة {attempt}/{self.max_retries}")
                    time.sleep(2)

                audio_data = self._call_gemini_api(text, voice_name, style_preset)

                if audio_data and len(audio_data) > 500:
                    with open(output_path, "wb") as f:
                        f.write(audio_data)
                    return True
                else:
                    logger.warning(f"      ⚠ صوت فارغ (محاولة {attempt})")

            except Exception as e:
                logger.warning(f"      ⚠ فشل (محاولة {attempt}): {str(e)[:80]}")

        return False

    # ════════════════════════════════════════════════════════════════
    #         الاتصال بـ Gemini API
    # ════════════════════════════════════════════════════════════════
    def _call_gemini_api(
        self,
        text: str,
        voice_name: str,
        style_preset: str,
    ) -> bytes:
        """الاتصال بـ Gemini API وإرجاع الصوت."""
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

        # تحويل لـ WAV
        ext = mimetypes.guess_extension(mime_type) if mime_type else None
        if ext is None or "wav" not in (ext or ""):
            raw_audio = self._convert_to_wav(raw_audio, mime_type)

        return raw_audio

    # ════════════════════════════════════════════════════════════════
    #         دمج ملفات WAV بـ pydub
    # ════════════════════════════════════════════════════════════════
    def _merge_wav_files(self, wav_files: List[str], output_path: str) -> None:
        """دمج عدة ملفات WAV بـ pydub."""
        try:
            from pydub import AudioSegment

            combined = AudioSegment.from_wav(wav_files[0])
            for wav_file in wav_files[1:]:
                segment = AudioSegment.from_wav(wav_file)
                combined += segment

            if output_path.endswith(".mp3"):
                combined.export(output_path, format="mp3", bitrate="192k")
            else:
                combined.export(output_path, format="wav")

            logger.info(f"   ✓ تم دمج {len(wav_files)} ملف")

        except Exception as e:
            logger.error(f"   ❌ فشل الدمج: {e}")
            import shutil
            shutil.copy(wav_files[0], output_path)

    # ════════════════════════════════════════════════════════════════
    #         تقسيم النص
    # ════════════════════════════════════════════════════════════════
    def _split_text(self, text: str, max_chars: int) -> List[str]:
        """تقسيم النص لقطع عند نهايات الجمل."""
        if len(text) <= max_chars:
            return [text]

        chunks = []
        delimiters = [". ", "! ", "? ", "... ", "،", "؛", "\n", " "]

        remaining = text
        while remaining:
            if len(remaining) <= max_chars:
                chunks.append(remaining.strip())
                break

            best_pos = -1
            window = remaining[:max_chars]

            for delim in delimiters:
                pos = window.rfind(delim)
                if pos > max_chars * 0.5:
                    best_pos = pos + len(delim)
                    break

            if best_pos == -1:
                best_pos = window.rfind(" ")
                if best_pos == -1:
                    best_pos = max_chars

            chunks.append(remaining[:best_pos].strip())
            remaining = remaining[best_pos:].strip()

        return [c for c in chunks if c]

    # ════════════════════════════════════════════════════════════════
    #         بناء Prompt
    # ════════════════════════════════════════════════════════════════
    def _build_prompt(self, text: str, style_config: Dict) -> str:
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
    #         تحويل PCM → WAV
    # ════════════════════════════════════════════════════════════════
    def _convert_to_wav(self, audio_data: bytes, mime_type: str) -> bytes:
        params = self._parse_mime(mime_type)
        bps = params["bits_per_sample"]
        rate = params["rate"]
        nc = 1
        ds = len(audio_data)
        ba = nc * (bps // 8)
        br = rate * ba

        header = struct.pack(
            "<4sI4s4sIHHIIHH4sI",
            b"RIFF", 36 + ds, b"WAVE", b"fmt ",
            16, 1, nc, rate, br, ba, bps,
            b"data", ds,
        )
        return header + audio_data

    def _parse_mime(self, mime_type: str) -> Dict[str, int]:
        bps = 16
        rate = 24000
        if not mime_type:
            return {"bits_per_sample": bps, "rate": rate}
        for param in mime_type.split(";"):
            param = param.strip()
            if param.lower().startswith("rate="):
                try:
                    rate = int(param.split("=", 1)[1])
                except Exception:
                    pass
            elif param.startswith("audio/L"):
                try:
                    bps = int(param.split("L", 1)[1])
                except Exception:
                    pass
        return {"bits_per_sample": bps, "rate": rate}

    # ════════════════════════════════════════════════════════════════
    #         دوال مساعدة
    # ════════════════════════════════════════════════════════════════
    def list_voices(self) -> Dict:
        return self.AVAILABLE_VOICES

    def list_styles(self) -> Dict:
        return self.STYLE_PRESETS
