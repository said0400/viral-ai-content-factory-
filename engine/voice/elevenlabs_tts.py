# engine/voice/elevenlabs_tts.py

import os
import struct
import asyncio
import requests
from pathlib import Path
from dotenv import load_dotenv
from google import genai
from google.genai import types

load_dotenv()

class ElevenLabsTTS:
    """
    TTS Engine — يجرب بالترتيب:
    1. Gemini 3.1 Flash TTS (مجاني وقوي)
    2. ElevenLabs
    3. Edge TTS (احتياطي)
    """

    BASE_URL = "https://api.elevenlabs.io/v1"

    def __init__(self):
        self.eleven_key = os.getenv("ELEVENLABS_API_KEY")
        self.gemini_key = os.getenv("GEMINI_API_KEY")
        self.voice_id   = os.getenv("ELEVENLABS_VOICE_ID")
        self.temp_dir   = Path(os.getenv("TEMP_DIR", "./temp"))
        self.temp_dir.mkdir(parents=True, exist_ok=True)
        self.headers = {
            "xi-api-key": self.eleven_key,
            "Content-Type": "application/json",
        }

    # ── MAIN ENTRY ────────────────────────────────────────────────────
    def generate_audio(self, script: dict, output_path: str) -> str:
        text = self._build_text(script)

        # 1. Gemini TTS أولاً (مجاني)
        try:
            print("🚀 Trying Gemini TTS...")
            if self._gemini_tts(text, output_path):
                print("✓ Gemini TTS success")
                return output_path
        except Exception as e:
            print(f"⚠️ Gemini TTS failed: {e}")

        # 2. ElevenLabs
        try:
            print("🎙️ Trying ElevenLabs...")
            audio = self._elevenlabs(text)
            if audio:
                print("✓ ElevenLabs success")
                return self._save(output_path, audio)
        except Exception as e:
            print(f"⚠️ ElevenLabs failed: {e}")

        # 3. Edge TTS احتياطي
        print("🔁 Falling back to Edge TTS...")
        return self._edge_tts(text, output_path)

    # ── GEMINI TTS ────────────────────────────────────────────────────
    def _gemini_tts(self, text: str, output_path: str) -> bool:
        if not self.gemini_key:
            return False

        client  = genai.Client(api_key=self.gemini_key)
        model   = "gemini-3.1-flash-tts-preview"
        contents = [types.Content(
            role="user",
            parts=[types.Part.from_text(text=text)]
        )]
        config = types.GenerateContentConfig(
            response_modalities=["audio"],
            speech_config=types.SpeechConfig(
                voice_config=types.VoiceConfig(
                    prebuilt_voice_config=types.PrebuiltVoiceConfig(
                        voice_name="Zephyr"
                    )
                )
            )
        )

        full_audio = b""
        mime_type  = "audio/L16;rate=24000"

        for chunk in client.models.generate_content_stream(
            model=model, contents=contents, config=config
        ):
            if chunk.parts and chunk.parts[0].inline_data:
                full_audio += chunk.parts[0].inline_data.data
                mime_type   = chunk.parts[0].inline_data.mime_type

        if full_audio:
            wav = self._convert_to_wav(full_audio, mime_type)
            self._save(output_path, wav)
            return True
        return False

    # ── ELEVENLABS ────────────────────────────────────────────────────
    def _elevenlabs(self, text: str):
        if not self.eleven_key or not self.voice_id:
            return None
        url = f"{self.BASE_URL}/text-to-speech/{self.voice_id}"
        payload = {
            "text": text,
            "model_id": "eleven_turbo_v2",
            "voice_settings": {"stability": 0.4, "similarity_boost": 0.8}
        }
        r = requests.post(url, json=payload, headers=self.headers, timeout=60)
        return r.content if r.status_code == 200 else None

    # ── EDGE TTS ──────────────────────────────────────────────────────
    def _edge_tts(self, text: str, output_path: str) -> str:
        try:
            import edge_tts
            async def run():
                communicate = edge_tts.Communicate(text, voice="ar-EG-SalmaNeural")
                await communicate.save(output_path)
            asyncio.run(run())
            return output_path
        except Exception:
            return self._silent_audio(output_path)

    # ── UTILS ─────────────────────────────────────────────────────────
    def _convert_to_wav(self, audio_data: bytes, mime_type: str) -> bytes:
        params     = self._parse_mime(mime_type)
        rate       = params["rate"]
        bits       = params["bits"]
        data_size  = len(audio_data)
        header = struct.pack(
            "<4sI4s4sIHHIIHH4sI",
            b"RIFF", 36 + data_size, b"WAVE",
            b"fmt ", 16, 1, 1,
            rate, rate * (bits // 8),
            bits // 8, bits,
            b"data", data_size
        )
        return header + audio_data

    def _parse_mime(self, mime_type: str) -> dict:
        rate = 24000
        bits = 16
        for part in mime_type.split(";"):
            part = part.strip()
            if part.startswith("rate="):
                try:
                    rate = int(part.split("=")[1])
                except ValueError:
                    pass
        return {"rate": rate, "bits": bits}

    def _build_text(self, script: dict) -> str:
        scenes = script.get("scenes", [])
        parts  = [s.get("text", "") for s in scenes]
        cta    = script.get("cta", "")
        return " ... ".join(parts) + (f" ... {cta}" if cta else "")

    def _save(self, path: str, data: bytes) -> str:
        with open(path, "wb") as f:
            f.write(data)
        return path

    def _silent_audio(self, output_path: str) -> str:
        import subprocess
        subprocess.run([
            "ffmpeg", "-y", "-f", "lavfi",
            "-i", "anullsrc=r=44100:cl=mono",
            "-t", "5", output_path
        ])
        return output_path
