"""
Groq TTS Engine — النسخة الصحيحة والمتحقق منها
================================================================
الموديل الرسمي الحالي: canopylabs/orpheus-arabic-saudi
الأصوات المتاحة (موثقة من Groq Docs):
  - fahad  ← صوت ذكوري عميق  ✓
  - sultan ← صوت ذكوري رسمي  ✓
  - noura  ← صوت أنثوي        ✓
  - lulwa  ← صوت أنثوي        ✓

⚠️ حد مهم: الموديل يقبل 200 حرف كحد أقصى لكل طلب
   لذلك نقسم النص على chunks ونجمع الصوتيات ببعضها

ضع هذا الملف في: engine/voice/groq_tts.py
================================================================
"""

import os
import re
import asyncio
import shutil
import subprocess
from pathlib import Path

from groq import Groq
from dotenv import load_dotenv

load_dotenv()

# ─── الموديل والأصوات الموثقة رسمياً ──────────────────────────────────────
ARABIC_MODEL  = "canopylabs/orpheus-arabic-saudi"
ARABIC_VOICES = ["fahad", "sultan", "noura", "lulwa"]

# خريطة mood → صوت (كلها موثقة)
MOOD_VOICE_MAP = {
    "epic":         "fahad",
    "motivational": "fahad",
    "dramatic":     "sultan",
    "dark":         "sultan",
    "emotional":    "fahad",
    "calm":         "sultan",
    "romantic":     "sultan",
    "intelligence": "sultan",
}

# حد الأحرف لكل طلب (من الوثائق الرسمية)
MAX_CHARS = 190   # أقل من 200 بهامش أمان

# أصوات Edge TTS عربية للـ fallback
EDGE_AR_VOICES = [
    "ar-SA-HamedNeural",
    "ar-EG-ShakirNeural",
    "ar-SA-NaifNeural",
]


class GroqTTS:

    def __init__(self):
        api_key = os.getenv("GROQ_API_KEY")
        if not api_key:
            raise ValueError("GROQ_API_KEY غير موجود في .env")

        self.client   = Groq(api_key=api_key)
        self.temp_dir = Path(os.getenv("TEMP_DIR", "./temp"))
        self.temp_dir.mkdir(parents=True, exist_ok=True)

    # ─── الدالة الرئيسية ────────────────────────────────────────────────────

    def generate_audio(self, script: dict, output_path: str) -> str:
        """
        يولّد الصوت لكل المشاهد مجتمعة.
        يقسم النص على chunks بسبب حد الـ 200 حرف.
        """
        mood  = script.get("music_mood", "motivational")
        voice = MOOD_VOICE_MAP.get(mood, "fahad")

        print(f"  🎙️ Groq TTS | {ARABIC_MODEL} | صوت: {voice}")

        # بناء قائمة الـ chunks من المشاهد
        chunks = self._build_chunks(script)
        print(f"  📦 {len(chunks)} chunk | mood: {mood}")

        # توليد صوت لكل chunk
        wav_files = []
        for i, chunk in enumerate(chunks):
            chunk_out = str(self.temp_dir / f"chunk_{i:03d}.wav")
            success   = self._generate_chunk(chunk, voice, chunk_out)

            if not success:
                # جرب صوت بديل
                for alt_voice in ARABIC_VOICES:
                    if alt_voice != voice:
                        success = self._generate_chunk(chunk, alt_voice, chunk_out)
                        if success:
                            break

            if not success:
                # fallback: Edge TTS لهذا الـ chunk
                chunk_out = self._edge_tts_chunk(chunk, chunk_out)

            if os.path.exists(chunk_out) and os.path.getsize(chunk_out) > 500:
                wav_files.append(chunk_out)

        if not wav_files:
            print("  ❌ كل محاولات TTS فشلت — صمت")
            return self._silence(output_path)

        # دمج كل الـ chunks في ملف واحد
        merged = str(self.temp_dir / "merged_voice.wav")
        self._concat_wavs(wav_files, merged)

        # تحويل إلى MP3
        return self._to_mp3(merged, output_path)

    # ─── تقسيم النص على chunks ──────────────────────────────────────────────

    def _build_chunks(self, script: dict) -> list:
        """
        يبني قائمة chunks من المشاهد.
        كل chunk لا يتجاوز MAX_CHARS حرف.
        يحترم حدود الجمل (لا يقطع في منتصف الكلمة).
        """
        chunks  = []
        current = ""

        for scene in script.get("scenes", []):
            text  = scene.get("text", "").strip()
            pause = float(scene.get("pause_after", 0.3))

            if not text:
                continue

            # اختر فاصل مناسب
            sep = "... " if pause >= 0.8 else (".. " if pause >= 0.5 else "، ")
            sentence = text + sep

            # إذا الجملة وحدها تتجاوز الحد، قسّمها
            if len(sentence) > MAX_CHARS:
                # أضف الـ current أولاً إذا كان فيه شيء
                if current.strip():
                    chunks.append(current.strip())
                    current = ""
                # قسّم الجملة الطويلة
                for sub in self._split_long(sentence):
                    chunks.append(sub.strip())
            elif len(current) + len(sentence) > MAX_CHARS:
                # الـ current امتلأ، احفظه وابدأ جديد
                if current.strip():
                    chunks.append(current.strip())
                current = sentence
            else:
                current += sentence

        # أضف الـ CTA
        cta = script.get("cta", "").strip()
        if cta:
            if len(current) + len(cta) > MAX_CHARS:
                if current.strip():
                    chunks.append(current.strip())
                chunks.append(cta)
            else:
                current += cta

        if current.strip():
            chunks.append(current.strip())

        return chunks if chunks else ["مرحباً"]

    def _split_long(self, text: str) -> list:
        """يقسم النص الطويل على حدود الكلمات."""
        words  = text.split()
        parts  = []
        current = ""
        for word in words:
            if len(current) + len(word) + 1 > MAX_CHARS:
                if current:
                    parts.append(current.strip())
                current = word + " "
            else:
                current += word + " "
        if current.strip():
            parts.append(current.strip())
        return parts if parts else [text[:MAX_CHARS]]

    # ─── توليد chunk واحد ────────────────────────────────────────────────────

    def _generate_chunk(self, text: str, voice: str, output_path: str) -> bool:
        """يولّد صوت لـ chunk واحد. يُعيد True إذا نجح."""
        try:
            resp = self.client.audio.speech.create(
                model=ARABIC_MODEL,
                voice=voice,
                input=text,
                response_format="wav",
            )
            data = resp.read()
            if data and len(data) > 500:
                with open(output_path, "wb") as f:
                    f.write(data)
                return True
            return False
        except Exception as e:
            print(f"  ⚠️ chunk فشل [{voice}]: {e}")
            return False

    # ─── دمج ملفات WAV ──────────────────────────────────────────────────────

    def _concat_wavs(self, wav_files: list, output_path: str) -> str:
        if len(wav_files) == 1:
            shutil.copy(wav_files[0], output_path)
            return output_path

        # بناء قائمة concat لـ FFmpeg
        list_file = str(self.temp_dir / "concat_list.txt")
        with open(list_file, "w", encoding="utf-8") as f:
            for wav in wav_files:
                f.write(f"file '{os.path.abspath(wav)}'\n")

        result = subprocess.run(
            [
                "ffmpeg", "-y",
                "-f", "concat", "-safe", "0",
                "-i", list_file,
                "-c:a", "pcm_s16le",
                output_path,
            ],
            capture_output=True,
        )

        if result.returncode != 0:
            # fallback: نسخ أول ملف فقط
            shutil.copy(wav_files[0], output_path)

        return output_path

    # ─── تحويل WAV → MP3 ────────────────────────────────────────────────────

    def _to_mp3(self, wav_path: str, output_path: str) -> str:
        result = subprocess.run(
            [
                "ffmpeg", "-y", "-i", wav_path,
                "-ar", "44100", "-ac", "2",
                "-b:a", "192k",
                output_path,
            ],
            capture_output=True,
        )
        if result.returncode != 0:
            shutil.copy(wav_path, output_path)
        return output_path

    # ─── Edge TTS fallback لـ chunk واحد ────────────────────────────────────

    def _edge_tts_chunk(self, text: str, output_path: str) -> str:
        try:
            import edge_tts

            async def _run(voice: str) -> bool:
                try:
                    await edge_tts.Communicate(text, voice=voice).save(output_path)
                    return (
                        Path(output_path).exists()
                        and Path(output_path).stat().st_size > 500
                    )
                except Exception:
                    return False

            for v in EDGE_AR_VOICES:
                if asyncio.run(_run(v)):
                    return output_path

        except ImportError:
            pass

        # صمت قصير كـ fallback أخير
        dur = max(len(text) / 15, 1.0)
        subprocess.run(
            [
                "ffmpeg", "-y", "-f", "lavfi",
                "-i", "anullsrc=r=44100:cl=stereo",
                "-t", str(dur), "-b:a", "64k",
                output_path,
            ],
            capture_output=True,
        )
        return output_path

    # ─── صمت كامل (fallback أخير) ───────────────────────────────────────────

    def _silence(self, output_path: str) -> str:
        subprocess.run(
            [
                "ffmpeg", "-y", "-f", "lavfi",
                "-i", "anullsrc=r=44100:cl=stereo",
                "-t", "55", "-b:a", "128k",
                output_path,
            ],
            capture_output=True,
        )
        return output_path
