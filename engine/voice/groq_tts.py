"""
Groq TTS Engine — يستبدل ElevenLabs و Gemini TTS كلياً
يستخدم PlayAI عبر Groq API (يدعم العربية رسمياً)

ضع هذا الملف في: engine/voice/groq_tts.py
واحذف: engine/voice/elevenlabs_tts.py
"""

import os
import asyncio
import shutil
import subprocess
from pathlib import Path

from groq import Groq
from dotenv import load_dotenv

load_dotenv()


# ─── خريطة الأصوات حسب الـ mood ────────────────────────────────────────────
MOOD_VOICE_MAP = {
    "epic":         "Nasser-PlayAI",
    "motivational": "Nasser-PlayAI",
    "dramatic":     "Ahmad-PlayAI",
    "dark":         "Ahmad-PlayAI",
    "emotional":    "Khalid-PlayAI",
    "calm":         "Khalid-PlayAI",
    "romantic":     "Khalid-PlayAI",
    "intelligence": "Ahmad-PlayAI",
}

ARABIC_VOICES  = ["Nasser-PlayAI", "Ahmad-PlayAI", "Khalid-PlayAI"]
EDGE_AR_VOICES = ["ar-SA-HamedNeural", "ar-EG-ShakirNeural", "ar-SA-NaifNeural"]


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
        text  = self._build_text(script)
        mood  = script.get("music_mood", "motivational")
        voice = MOOD_VOICE_MAP.get(mood, "Nasser-PlayAI")

        print(f"  🎙️ Groq TTS | playai-tts-arabic | صوت: {voice}")
        print(f"  📝 طول النص: {len(text)} حرف")

        # 1) playai-tts-arabic بالصوت المناسب
        audio = self._call_groq(text, "playai-tts-arabic", voice)

        # 2) أصوات بديلة من نفس الموديل
        if not audio:
            for alt in ARABIC_VOICES:
                if alt != voice:
                    print(f"  ↩️ جرب صوت: {alt}")
                    audio = self._call_groq(text, "playai-tts-arabic", alt)
                    if audio:
                        break

        # 3) playai-tts العادي
        if not audio:
            print("  ↩️ جرب playai-tts...")
            audio = self._call_groq(text, "playai-tts", "Fritz-PlayAI")

        # 4) Edge TTS مجاني
        if not audio:
            print("  ↩️ Fallback Edge TTS...")
            return self._edge_tts(text, output_path)

        raw_wav = str(self.temp_dir / "groq_raw_voice.wav")
        with open(raw_wav, "wb") as f:
            f.write(audio)

        return self._to_mp3(raw_wav, output_path)

    # ─── استدعاء Groq ───────────────────────────────────────────────────────

    def _call_groq(self, text: str, model: str, voice: str) -> bytes | None:
        try:
            resp = self.client.audio.speech.create(
                model=model,
                voice=voice,
                input=text,
                response_format="wav",
            )
            data = resp.read()
            if data and len(data) > 2000:
                print(f"  ✓ Groq TTS نجح ({len(data):,} bytes)")
                return data
            return None
        except Exception as e:
            print(f"  ⚠️ [{model}/{voice}]: {e}")
            return None

    # ─── بناء النص مع توقفات طبيعية ────────────────────────────────────────

    def _build_text(self, script: dict) -> str:
        parts = []
        for scene in script.get("scenes", []):
            text  = scene.get("text", "").strip()
            pause = float(scene.get("pause_after", 0.3))
            if not text:
                continue
            if pause >= 0.8:
                sep = "... "
            elif pause >= 0.5:
                sep = ".. "
            else:
                sep = "، "
            parts.append(text + sep)

        cta = script.get("cta", "").strip()
        if cta:
            parts.append(cta)

        return " ".join(parts)

    # ─── تحويل WAV → MP3 ────────────────────────────────────────────────────

    def _to_mp3(self, wav_path: str, out: str) -> str:
        result = subprocess.run(
            ["ffmpeg", "-y", "-i", wav_path,
             "-ar", "44100", "-ac", "2", "-b:a", "192k", out],
            capture_output=True,
        )
        if result.returncode != 0:
            shutil.copy(wav_path, out)
        return out

    # ─── Edge TTS fallback ──────────────────────────────────────────────────

    def _edge_tts(self, text: str, output_path: str) -> str:
        try:
            import edge_tts

            async def _run(voice: str) -> bool:
                try:
                    await edge_tts.Communicate(text, voice=voice).save(output_path)
                    return Path(output_path).exists() and Path(output_path).stat().st_size > 1000
                except Exception:
                    return False

            for voice in EDGE_AR_VOICES:
                if asyncio.run(_run(voice)):
                    print(f"  ✓ Edge TTS: {voice}")
                    return output_path
        except ImportError:
            pass

        return self._silence(output_path)

    def _silence(self, out: str) -> str:
        subprocess.run(
            ["ffmpeg", "-y", "-f", "lavfi",
             "-i", "anullsrc=r=44100:cl=stereo",
             "-t", "55", "-b:a", "128k", out],
            capture_output=True,
        )
        return out
