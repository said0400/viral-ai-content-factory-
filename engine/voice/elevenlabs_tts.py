"""
ElevenLabs TTS Engine - Human Performance Optimized
Fallback + Retry + Dynamic Model System
"""

import os
import json
import time
import requests
import subprocess

from pathlib import Path
from dotenv import load_dotenv

load_dotenv()


class ElevenLabsTTS:

    BASE_URL = "https://api.elevenlabs.io/v1"

    # إعدادات صوتية محسنة للمحتوى السينمائي
    VOICE_SETTINGS = {
        "stability": 0.38,
        "similarity_boost": 0.85,
        "style": 0.78,
        "use_speaker_boost": True,
    }

    # موديلات احتياطية تلقائية
    MODELS = [
        "eleven_multilingual_v2",
        "eleven_turbo_v2",
        "eleven_multilingual_v1",
    ]

    def __init__(self):

        self.api_key = os.getenv("ELEVENLABS_API_KEY")

        self.voice_id = os.getenv(
            "ELEVENLABS_VOICE_ID",
            "21m00Tcm4TlvDq8ikWAM"
        )

        self.temp_dir = Path(
            os.getenv("TEMP_DIR", "./temp")
        )

        self.temp_dir.mkdir(
            parents=True,
            exist_ok=True
        )

        if not self.api_key:
            raise EnvironmentError(
                "ELEVENLABS_API_KEY not found in .env"
            )

        self.headers = {
            "xi-api-key": self.api_key,
            "Content-Type": "application/json",
        }

    # =========================================
    # MAIN AUDIO GENERATION
    # =========================================

    def generate_audio(
        self,
        script: dict,
        output_path: str
    ) -> str:

        text = self._build_text(script)

        text = self._clean_text(text)

        audio_data = self._call_api(text)

        output = Path(output_path)

        output.parent.mkdir(
            parents=True,
            exist_ok=True
        )

        with open(output, "wb") as f:
            f.write(audio_data)

        return str(output)

    # =========================================
    # BUILD CINEMATIC TEXT
    # =========================================

    def _build_text(self, script: dict) -> str:

        scenes = script.get("scenes", [])

        parts = []

        for scene in scenes:

            text = scene.get("text", "").strip()

            if not text:
                continue

            pause_after = float(
                scene.get("pause_after", 0.4)
            )

            # pauses طبيعية للبشر
            if pause_after >= 0.8:
                text += " ..."
            elif pause_after >= 0.5:
                text += ".."

            parts.append(text)

        cta = script.get("cta", "").strip()

        if cta:
            parts.append(cta)

        return " ".join(parts)

    # =========================================
    # CLEAN TEXT
    # =========================================

    def _clean_text(self, text: str) -> str:

        replacements = {
            "—": "-",
            "“": '"',
            "”": '"',
            "\n": " ",
            "\t": " ",
            "  ": " ",
        }

        for old, new in replacements.items():
            text = text.replace(old, new)

        return text.strip()

    # =========================================
    # CALL ELEVENLABS API
    # =========================================

    def _call_api(
        self,
        text: str,
        retries: int = 3
    ) -> bytes:

        url = f"{self.BASE_URL}/text-to-speech/{self.voice_id}"

        last_error = None

        for model in self.MODELS:

            print(f"🎤 Trying model: {model}")

            payload = {
                "text": text,
                "model_id": model,
                "voice_settings": self.VOICE_SETTINGS,
            }

            for attempt in range(retries):

                try:

                    response = requests.post(
                        url,
                        json=payload,
                        headers=self.headers,
                        timeout=90,
                    )

                    # رصيد منتهي
                    if response.status_code == 402:
                        print(
                            f"⚠️ Model {model} requires paid credits."
                        )
                        break

                    # rate limit
                    if response.status_code == 429:

                        wait_time = 2 ** (attempt + 1)

                        print(
                            f"⏳ Rate limited. Waiting {wait_time}s..."
                        )

                        time.sleep(wait_time)

                        continue

                    # API KEY خاطئة
                    if response.status_code == 401:
                        raise EnvironmentError(
                            "Invalid ElevenLabs API Key."
                        )

                    response.raise_for_status()

                    print(f"✓ Using model: {model}")

                    return response.content

                except requests.exceptions.RequestException as e:

                    last_error = e

                    print(
                        f"⚠️ Attempt {attempt + 1} failed for {model}"
                    )

                    time.sleep(2)

        raise RuntimeError(
            f"All ElevenLabs models failed. Last error: {last_error}"
        )

    # =========================================
    # AUDIO DURATION
    # =========================================

    def get_audio_duration(
        self,
        path: str
    ) -> float:

        result = subprocess.run(
            [
                "ffprobe",
                "-v",
                "quiet",
                "-print_format",
                "json",
                "-show_format",
                path,
            ],
            capture_output=True,
            text=True,
            check=True,
        )

        data = json.loads(result.stdout)

        return float(
            data["format"]["duration"]
        )

    # =========================================
    # LIST AVAILABLE VOICES
    # =========================================

    def list_voices(self) -> list:

        response = requests.get(
            f"{self.BASE_URL}/voices",
            headers=self.headers,
            timeout=20,
        )

        response.raise_for_status()

        voices = response.json().get(
            "voices",
            []
        )

        return [
            {
                "id": v["voice_id"],
                "name": v["name"]
            }
            for v in voices
        ]
