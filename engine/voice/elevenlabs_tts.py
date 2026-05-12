import os
import time
import asyncio
import requests
import mimetypes
import struct
from pathlib import Path
from dotenv import load_dotenv
from google import genai
from google.genai import types

load_dotenv()

class TTS100Percent:
    BASE_URL = "https://api.elevenlabs.io/v1"

    def __init__(self):
        # Keys
        self.eleven_key = os.getenv("ELEVENLABS_API_KEY")
        self.gemini_key = os.getenv("GEMINI_API_KEY")
        self.voice_id = os.getenv("ELEVENLABS_VOICE_ID")

        # Config
        self.temp_dir = Path(os.getenv("TEMP_DIR", "./temp"))
        self.temp_dir.mkdir(parents=True, exist_ok=True)
        
        self.headers = {
            "xi-api-key": self.eleven_key,
            "Content-Type": "application/json",
        }

    # =========================================
    # MAIN ENTRY (NEVER FAILS)
    # =========================================
    def generate_audio(self, script: dict, output_path: str) -> str:
        text = self._build_text(script)

        # 1. المحاولة الأولى: ElevenLabs
        try:
            print("🎙️ Attempting ElevenLabs...")
            audio = self._elevenlabs(text)
            if audio: return self._save(output_path, audio)
        except Exception as e:
            print(f"⚠️ ElevenLabs failed: {e}")

        # 2. المحاولة الثانية: Gemini TTS (الخيار المجاني القوي)
        try:
            print("🚀 Switching to Gemini TTS...")
            success = self._gemini_tts(text, output_path)
            if success: return output_path
        except Exception as e:
            print(f"⚠️ Gemini TTS failed: {e}")

        # 3. الخيار الأخير: Edge TTS
        print("🔁 Falling back to Edge TTS...")
        return self._edge_tts(text, output_path)

    # =========================================
    # GEMINI TTS ENGINE (NEW)
    # =========================================
    def _gemini_tts(self, text: str, output_path: str) -> bool:
        if not self.gemini_key: return False
        
        client = genai.Client(api_key=self.gemini_key)
        model = "gemini-3.1-flash-tts-preview"
        
        contents = [types.Content(role="user", parts=[types.Part.from_text(text=text)])]
        
        config = types.GenerateContentConfig(
            response_modalities=["audio"],
            speech_config=types.SpeechConfig(
                voice_config=types.VoiceConfig(
                    prebuilt_voice_config=types.PrebuiltVoiceConfig(voice_name="Zephyr")
                )
            )
        )

        full_audio_data = b""
        mime_type = "audio/L16;rate=24000"

        for chunk in client.models.generate_content_stream(model=model, contents=contents, config=config):
            if chunk.parts and chunk.parts[0].inline_data:
                full_audio_data += chunk.parts[0].inline_data.data
                mime_type = chunk.parts[0].inline_data.mime_type

        if full_audio_data:
            # تحويل البيانات إلى WAV باستخدام الدوال التقنية بالأسفل
            final_wav = self._convert_to_wav(full_audio_data, mime_type)
            self._save(output_path, final_wav)
            return True
        return False

    # =========================================
    # ELEVENLABS
    # =========================================
    def _elevenlabs(self, text: str):
        if not self.eleven_key: return None
        url = f"{self.BASE_URL}/text-to-speech/{self.voice_id}"
        payload = {
            "text": text,
            "model_id": "eleven_turbo_v2",
            "voice_settings": {"stability": 0.4, "similarity_boost": 0.8}
        }
        r = requests.post(url, json=payload, headers=self.headers, timeout=60)
        if r.status_code == 200: return r.content
        return None

    # =========================================
    # EDGE TTS
    # =========================================
    def _edge_tts(self, text: str, output_path: str) -> str:
        try:
            import edge_tts
            async def run():
                communicate = edge_tts.Communicate(text, voice="ar-EG-SalmaNeural")
                await communicate.save(output_path)
            asyncio.run(run())
            return output_path
        except:
            return self._silent_audio(output_path)

    # =========================================
    # UTILS (WAW CONVERSION)
    # =========================================
    def _convert_to_wav(self, audio_data: bytes, mime_type: str) -> bytes:
        params = self._parse_audio_mime_type(mime_type)
        data_size = len(audio_data)
        header = struct.pack(
            "<4sI4s4sIHHIIHH4sI",
            b"RIFF", 36 + data_size, b"WAVE", b"fmt ", 16, 1, 1,
            params["rate"], params["rate"] * (params["bits"] // 8),
            params["bits"] // 8, params["bits"], b"data", data_size
        )
        return header + audio_data

    def _parse_audio_mime_type(self, mime_type: str):
        rate = 24000
        bits = 16
        if "rate=" in mime_type:
            rate = int(mime_type.split("rate=")[1].split(";")[0])
        return {"bits": bits, "rate": rate}

    def _build_text(self, script: dict) -> str:
        scenes = script.get("scenes", [])
        text = " ... ".join(s.get("text", "") for s in scenes)
        return f"{text} ... {script.get('cta', '')}"

    def _save(self, path: str, data: bytes) -> str:
        with open(path, "wb") as f: f.write(data)
        return path

    def _silent_audio(self, output_path: str) -> str:
        import subprocess
        subprocess.run(["ffmpeg", "-y", "-f", "lavfi", "-i", "anullsrc=r=44100:cl=mono", "-t", "5", output_path])
        return output_path
