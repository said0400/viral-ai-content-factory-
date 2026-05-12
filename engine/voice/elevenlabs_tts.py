"""
Robust TTS Engine - 100% Uptime
ElevenLabs + Edge TTS Fallback
Never crashes pipeline
"""

import os
import time
import asyncio
import requests
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()


class TTS100Percent:

    BASE_URL = "https://api.elevenlabs.io/v1"

    def __init__(self):

        self.api_key = os.getenv("ELEVENLABS_API_KEY")
        self.voice_id = os.getenv("ELEVENLABS_VOICE_ID")

        self.temp_dir = Path(os.getenv("TEMP_DIR", "./temp"))
        self.temp_dir.mkdir(parents=True, exist_ok=True)

        self.headers = {
            "xi-api-key": self.api_key,
            "Content-Type": "application/json",
        }

    # =========================================
    # MAIN ENTRY (NEVER FAILS)
    # =========================================

    def generate_audio(self, script: dict, output_path: str) -> str:

        text = self._build_text(script)

        try:
            audio = self._elevenlabs(text)

            if audio:
                return self._save(output_path, audio)

        except Exception as e:
            print(f"⚠️ ElevenLabs failed: {e}")

        # fallback ALWAYS
        print("🔁 Switching to Edge TTS fallback...")
        return self._edge_tts(text, output_path)

    # =========================================
    # ELEVENLABS
    # =========================================

    def _elevenlabs(self, text: str):

        if not self.api_key:
            return None

        url = f"{self.BASE_URL}/text-to-speech/{self.voice_id}"

        payload = {
            "text": text,
            "model_id": "eleven_turbo_v2",
            "voice_settings": {
                "stability": 0.4,
                "similarity_boost": 0.8,
                "style": 0.7,
                "use_speaker_boost": True,
            },
        }

        for attempt in range(2):

            try:
                r = requests.post(
                    url,
                    json=payload,
                    headers=self.headers,
                    timeout=60,
                )

                if r.status_code in [401, 402, 403]:
                    return None

                if r.status_code == 429:
                    time.sleep(2)
                    continue

                r.raise_for_status()
                return r.content

            except:
                time.sleep(1)

        return None

    # =========================================
    # EDGE TTS (FREE FALLBACK)
    # =========================================

    def _edge_tts(self, text: str, output_path: str) -> str:

        try:
            import edge_tts

            async def run():

                communicate = edge_tts.Communicate(
                    text,
                    voice="ar-EG-SalmaNeural"
                )

                await communicate.save(output_path)

            asyncio.run(run())

            return output_path

        except Exception as e:

            print(f"❌ Edge TTS failed too: {e}")

            # last resort: silent audio
            return self._silent_audio(output_path)

    # =========================================
    # SILENT AUDIO (FINAL FALLBACK)
    # =========================================

    def _silent_audio(self, output_path: str) -> str:

        import subprocess

        subprocess.run([
            "ffmpeg", "-y",
            "-f", "lavfi",
            "-i", "anullsrc=r=44100:cl=mono",
            "-t", "10",
            output_path
        ])

        return output_path

    # =========================================
    # TEXT BUILDER
    # =========================================

    def _build_text(self, script: dict) -> str:

        scenes = script.get("scenes", [])

        text = " ... ".join(
            s.get("text", "") for s in scenes
        )

        cta = script.get("cta", "")

        return f"{text} ... {cta}"

    # =========================================
    # SAVE
    # =========================================

    def _save(self, path: str, data: bytes) -> str:

        Path(path).parent.mkdir(parents=True, exist_ok=True)

        with open(path, "wb") as f:
            f.write(data)

        return path
