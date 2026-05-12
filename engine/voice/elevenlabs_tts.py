# engine/voice/elevenlabs_tts.py

import os
import struct
import asyncio
import mimetypes
import requests
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

class ElevenLabsTTS:
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
        print(f"📝 Text length: {len(text)} chars")

        # 1. ElevenLabs
        try:
            print("🎙️ Trying ElevenLabs...")
            audio = self._elevenlabs(text)
            if audio and len(audio) > 1000:
                print(f"✓ ElevenLabs success ({len(audio)} bytes)")
                return self._save(output_path, audio)
        except Exception as e:
            print(f"⚠️ ElevenLabs failed: {e}")

        # 2. Gemini TTS مع prompt احترافي للعربية
        try:
            print("🚀 Trying Gemini TTS...")
            if self._gemini_tts(text, output_path):
                print("✓ Gemini TTS success")
                return output_path
        except Exception as e:
            print(f"⚠️ Gemini TTS failed: {e}")

        # 3. Edge TTS عربي
        try:
            print("🔁 Trying Edge TTS (Arabic)...")
            result = self._edge_tts(text, output_path)
            if result and Path(result).exists() and Path(result).stat().st_size > 1000:
                print("✓ Edge TTS success")
                return result
        except Exception as e:
            print(f"⚠️ Edge TTS failed: {e}")

        print("⚠️ All TTS failed — generating silence")
        return self._silent_audio(output_path)

    # ── GEMINI TTS (بالطريقة الصحيحة) ────────────────────────────────
    def _gemini_tts(self, text: str, output_path: str) -> bool:
        if not self.gemini_key:
            return False

        from google import genai
        from google.genai import types

        client = genai.Client(api_key=self.gemini_key)
        model  = "gemini-3.1-flash-tts-preview"

        # Prompt احترافي للمحتوى التحفيزي العربي
        prompt = f"""Read the following Arabic transcript based on the audio profile and director's note.

# Audio Profile
A powerful and inspiring Arabic motivational narrator.

# Director's note
Style: Dramatic and emotional. Pace: Measured with pauses for impact. Accent: Modern Standard Arabic (Fusha).

## Scene:
A cinematic short video for social media about success and ambition.

## Sample Context:
Deep resonant voice, emotional delivery, dramatic pauses between sentences, inspiring tone.

## Transcript:
{text}"""

        contents = [types.Content(
            role="user",
            parts=[types.Part.from_text(text=prompt)]
        )]

        config = types.GenerateContentConfig(
            temperature=1,
            response_modalities=["audio"],
            speech_config=types.SpeechConfig(
                voice_config=types.VoiceConfig(
                    prebuilt_voice_config=types.PrebuiltVoiceConfig(
                        voice_name="Umbriel"  # صوت عميق وتحفيزي
                    )
                )
            )
        )

        full_audio = b""
        mime_type  = "audio/L16;rate=24000"

        for chunk in client.models.generate_content_stream(
            model=model, contents=contents, config=config
        ):
            if chunk.parts is None:
                continue
            if chunk.parts[0].inline_data and chunk.parts[0].inline_data.data:
                inline_data = chunk.parts[0].inline_data
                full_audio += inline_data.data
                mime_type   = inline_data.mime_type

        print(f"  Gemini audio bytes: {len(full_audio)}")

        if full_audio and len(full_audio) > 1000:
            # نفس طريقة Google الرسمية
            ext = mimetypes.guess_extension(mime_type)
            if ext is None:
                wav = self._convert_to_wav(full_audio, mime_type)
                self._save(output_path, wav)
            else:
                # تحويل لـ wav على كل حال لضمان التوافق
                wav = self._convert_to_wav(full_audio, mime_type)
                self._save(output_path, wav)
            return True

        return False

    # ── ELEVENLABS ────────────────────────────────────────────────────
    def _elevenlabs(self, text: str):
        if not self.eleven_key or not self.voice_id:
            print("  ℹ️ ElevenLabs keys not set")
            return None
        url = f"{self.BASE_URL}/text-to-speech/{self.voice_id}"
        payload = {
            "text": text,
            "model_id": "eleven_turbo_v2",
            "voice_settings": {"stability": 0.4, "similarity_boost": 0.8}
        }
        r = requests.post(url, json=payload, headers=self.headers, timeout=90)
        if r.status_code == 200:
            return r.content
        print(f"  ℹ️ ElevenLabs HTTP {r.status_code}: {r.text[:100]}")
        return None

    # ── EDGE TTS ──────────────────────────────────────────────────────
    def _edge_tts(self, text: str, output_path: str) -> str:
        import edge_tts

        voices = [
            "ar-EG-ShakirNeural",
            "ar-SA-HamedNeural",
            "ar-EG-SalmaNeural",
        ]

        for voice in voices:
            try:
                async def run(v=voice):
                    communicate = edge_tts.Communicate(text, voice=v)
                    await communicate.save(output_path)
                asyncio.run(run())
                if Path(output_path).exists() and Path(output_path).stat().st_size > 1000:
                    print(f"  ✓ Edge voice: {voice}")
                    return output_path
            except Exception as e:
                print(f"  ⚠️ {voice}: {e}")
        return None

    # ── UTILS ─────────────────────────────────────────────────────────
    def _convert_to_wav(self, audio_data: bytes, mime_type: str) -> bytes:
        params    = self._parse_mime(mime_type)
        rate      = params["rate"]
        bits      = params["bits_per_sample"]
        num_ch    = 1
        data_size = len(audio_data)
        block_align = num_ch * (bits // 8)
        byte_rate   = rate * block_align
        header = struct.pack(
            "<4sI4s4sIHHIIHH4sI",
            b"RIFF", 36 + data_size, b"WAVE",
            b"fmt ", 16, 1, num_ch,
            rate, byte_rate,
            block_align, bits,
            b"data", data_size
        )
        return header + audio_data

    def _parse_mime(self, mime_type: str) -> dict:
        bits_per_sample = 16
        rate = 24000
        for part in mime_type.split(";"):
            part = part.strip()
            if part.lower().startswith("rate="):
                try:
                    rate = int(part.split("=", 1)[1])
                except ValueError:
                    pass
            elif part.startswith("audio/L"):
                try:
                    bits_per_sample = int(part.split("L", 1)[1])
                except ValueError:
                    pass
        return {"bits_per_sample": bits_per_sample, "rate": rate}

    def _build_text(self, script: dict) -> str:
        scenes = script.get("scenes", [])
        parts  = [s.get("text", "").strip() for s in scenes if s.get("text", "").strip()]
        cta    = script.get("cta", "").strip()
        full   = " . ".join(parts)
        if cta:
            full += f" . {cta}"
        print(f"  📜 Scenes: {len(parts)} | CTA: {'yes' if cta else 'no'}")
        return full

    def _save(self, path: str, data: bytes) -> str:
        with open(path, "wb") as f:
            f.write(data)
        return path

    def _silent_audio(self, output_path: str) -> str:
        import subprocess
        subprocess.run([
            "ffmpeg", "-y", "-f", "lavfi",
            "-i", "anullsrc=r=44100:cl=stereo",
            "-t", "30", output_path
        ], capture_output=True)
        return output_path
