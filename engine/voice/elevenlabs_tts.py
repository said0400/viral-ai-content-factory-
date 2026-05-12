"""
ElevenLabs TTS Engine - Human Performance Optimized
"""

import os
import json
import time
import subprocess
import requests
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()


class ElevenLabsTTS:

    BASE_URL = "https://api.elevenlabs.io/v1"

    # تم تقليل stability لزيادة العاطفة والتنفس البشري
    VOICE_SETTINGS = {
        "stability": 0.30, 
        "similarity_boost": 0.80,
        "style": 0.70,
        "use_speaker_boost": True,
    }

    def __init__(self):
        self.api_key = os.getenv("ELEVENLABS_API_KEY")
        self.voice_id = os.getenv("ELEVENLABS_VOICE_ID", "21m00Tcm4TlvDq8ikWAM")
        self.temp_dir = Path(os.getenv("TEMP_DIR", "./temp"))
        self.temp_dir.mkdir(parents=True, exist_ok=True)
        if not self.api_key:
            raise ValueError("ELEVENLABS_API_KEY not found in .env")
        self.headers = {
            "xi-api-key": self.api_key,
            "Content-Type": "application/json",
        }

    def generate_audio(self, script: dict, output_path: str) -> str:
        text = self._build_text(script)
        data = self._call_api(text)
        Path(output_path).parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, "wb") as f:
            f.write(data)
        return output_path

    def _build_text(self, script: dict) -> str:
        parts = ["<break time='700ms'/>"]
        scenes = script.get("scenes", [])
        for i, scene in enumerate(scenes):
            text = scene.get("text", "")
            pause_ms = int(scene.get("pause_after", 0.3) * 1000)
            
            # حل مشكلة AttributeError مع الحفاظ على المنطق
            emphasis_data = scene.get("emphasis", [])
            if isinstance(emphasis_data, list):
                for emp in emphasis_data:
                    # التحقق مما إذا كان emp قاموساً أم نصاً مباشراً
                    w = emp.get("word", "") if isinstance(emp, dict) else str(emp)
                    if w and w in text:
                        # استبدال الكلمة بعلامة التوكيد
                        text = text.replace(w, f'<emphasis level="strong">{w}</emphasis>', 1)
            
            parts.append(text)
            if i < len(scenes) - 1:
                parts.append(f"<break time='{pause_ms}ms'/>")
        
        parts.append("<break time='500ms'/>")
        cta = script.get("cta", "")
        if cta:
            parts.append(f'<emphasis level="moderate">{cta}</emphasis>')
        
        return " ".join(parts)

    def _call_api(self, text: str, retries: int = 3) -> bytes:
        url = f"{self.BASE_URL}/text-to-speech/{self.voice_id}"
        # موديل v2 هو الوحيد الذي يدعم المشاعر العالية بالعربية
        payload = {
            "text": text,
            "model_id": "eleven_multilingual_v2",
            "voice_settings": self.VOICE_SETTINGS,
        }
        for attempt in range(retries):
            try:
                r = requests.post(url, json=payload, headers=self.headers, timeout=60)
                if r.status_code == 429:
                    time.sleep(2 ** (attempt + 1))
                    continue
                if r.status_code == 401:
                    raise ValueError("ElevenLabs API key invalid.")
                r.raise_for_status()
                return r.content
            except requests.exceptions.RequestException as e:
                if attempt == retries - 1:
                    raise RuntimeError(f"ElevenLabs failed: {e}") from e
                time.sleep(2)
        raise RuntimeError("ElevenLabs failed after all retries.")

    def get_audio_duration(self, path: str) -> float:
        r = subprocess.run(
            ["ffprobe", "-v", "quiet", "-print_format", "json", "-show_format", path],
            capture_output=True, text=True, check=True,
        )
        return float(json.loads(r.stdout)["format"]["duration"])

    def list_voices(self) -> list:
        r = requests.get(f"{self.BASE_URL}/voices", headers=self.headers, timeout=15)
        r.raise_for_status()
        return [{"id": v["voice_id"], "name": v["name"]} for v in r.json().get("voices", [])]
