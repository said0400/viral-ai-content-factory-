"""
🎙️ Gemini TTS Engine v4.3 — Final Fix (Chunked & Optimized)
═══════════════════════════════════════════════════════════════════
الإصلاحات المخصصة:
  ✓ تجميع كافة المشاهد وتقسيمها إلى جزأين فقط (2 Parts) لتقليل طلبات الـ API.
  ✓ تعديل وقت الانتظار عند الفشل (Rate Limit) ليكون 70 ثانية بين المحاولات.
═══════════════════════════════════════════════════════════════════
"""

from __future__ import annotations

import os
import re
import io
import time
import shutil
import logging
import tempfile
import hashlib
from pathlib import Path
from dataclasses import dataclass
from threading import Lock
from typing import Optional, Callable, List, Dict

from engine.video.voice.base_tts import (
    BaseTTS, TTSResult, TTSStatus, VoiceInfo,
    TTSConstants, estimate_duration
)

logger = logging.getLogger(__name__)

# ═══════════════════════════════════════════════════════════════════
# Voice & Style Definitions
# ═══════════════════════════════════════════════════════════════════
GEMINI_VOICES: Dict[str, VoiceInfo] = {
    "Achird": VoiceInfo("Achird", "Achird", "male", "multi", "ذكوري عميق", provider="gemini"),
    "Algenib": VoiceInfo("Algenib", "Algenib", "male", "multi", "ذكوري واضح", provider="gemini"),
    "Aoede": VoiceInfo("Aoede", "Aoede", "female", "multi", "أنثوي ناعم", provider="gemini"),
    "Charon": VoiceInfo("Charon", "Charon", "male", "multi", "ذكوري درامي", provider="gemini"),
    "Kore": VoiceInfo("Kore", "Kore", "female", "multi", "أنثوي قوي", provider="gemini"),
}

MOOD_VOICE_MAP: Dict[str, str] = {
    "motivation": "Achird", "motivational": "Achird",
    "dark": "Charon", "sigma": "Achird",
    "psychological": "Charon", "educational": "Algenib",
    "scientific": "Algenib", "emotional": "Aoede",
    "sad": "Aoede", "romantic": "Aoede",
    "horror": "Charon", "story": "Aoede", "quote": "Algenib",
}


@dataclass(frozen=True)
class StylePreset:
    name: str
    audio_profile: str
    directors_note: str
    scene_context: str


STYLE_PRESETS: Dict[str, StylePreset] = {
    "motivational": StylePreset("motivational", "A smooth, premium commercial voice.", "Style: Promo/Hype. Pace: Natural.", "Premium commercial."),
    "educational": StylePreset("educational", "A clear, authoritative narrator voice.", "Style: Documentary. Pace: Steady.", "Documentary narration."),
    "story": StylePreset("story", "A warm, expressive storyteller voice.", "Style: Narrative. Pace: Natural.", "Cinematic storytelling."),
    "quote": StylePreset("quote", "A profound, contemplative voice.", "Style: Philosophical. Pace: Slow.", "Profound quote delivery."),
    "viral": StylePreset("viral", "A high-energy voice.", "Style: Viral. Pace: Fast.", "Energetic content."),
    "psychological": StylePreset("psychological", "A deep, mysterious voice.", "Style: Psychological. Pace: Slow.", "Deep content."),
}


# ═══════════════════════════════════════════════════════════════════
# Constants
# ═══════════════════════════════════════════════════════════════════
class GeminiTTSConstants:
    MODEL_NAME = "gemini-2.5-flash-preview-tts"
    DEFAULT_VOICE = "Achird"
    DEFAULT_STYLE = "motivational"
    MAX_RETRIES = 5
    FIXED_RETRY_DELAY = 70.0    # ✅ تم التعديل إلى 70 ثانية عند الفشل
    INTER_REQUEST_DELAY = 20.0  
    MIN_AUDIO_SIZE = 500
    SCENE_TEXT_MAX_CHARS = 250
    RAW_PCM_SAMPLE_WIDTH = 2
    RAW_PCM_FRAME_RATE = 24000
    RAW_PCM_CHANNELS = 1


# ═══════════════════════════════════════════════════════════════════
# Main Engine
# ═══════════════════════════════════════════════════════════════════
class GeminiTTSEngine(BaseTTS):
    PROVIDER_NAME = "gemini_tts"

    def __init__(
        self,
        api_key: Optional[str] = None,
        voice: Optional[str] = None,
        style: Optional[str] = None,
        cache_enabled: bool = True,
        parallel_scenes: int = 1,
        **kwargs,
    ):
        super().__init__(cache_enabled=cache_enabled)
        self.api_key = api_key or os.getenv("GEMINI_API_KEY")
        if not self.api_key:
            raise RuntimeError("❌ GEMINI_API_KEY is required")

        self.voice_name = voice if voice in GEMINI_VOICES else GeminiTTSConstants.DEFAULT_VOICE
        self.style_preset = style if style in STYLE_PRESETS else GeminiTTSConstants.DEFAULT_STYLE
        self.inter_request_delay = float(os.getenv("GEMINI_INTER_DELAY", GeminiTTSConstants.INTER_REQUEST_DELAY))

        self._last_request_time = 0.0
        self._lock = Lock()
        self._init_libs()
        self._init_client()

        logger.info(f"🎙️ GeminiTTS v4.3 | Voice: {self.voice_name} | Delay: {self.inter_request_delay}s")

    def _init_libs(self):
        try:
            from google import genai
            from google.genai import types
            from pydub import AudioSegment
            self._genai = genai
            self._types = types
            self._AudioSegment = AudioSegment
        except ImportError as e:
            raise RuntimeError(f"❌ Missing: {e}\n   pip install google-genai pydub")

    def _init_client(self):
        self._client = self._genai.Client(api_key=self.api_key)

    def _generate_audio_data(self, text: str, voice: str, **kwargs) -> Optional[bytes]:
        try:
            return self._call_api(text)
        except Exception as e:
            logger.error(f"❌ فشل: {e}")
            return None

    def _select_voice_for_mood(self, mood: str) -> str:
        return MOOD_VOICE_MAP.get(mood, self.voice_name)

    def _wait_for_rate_limit(self):
        with self._lock:
            elapsed = time.time() - self._last_request_time
            if elapsed < self.inter_request_delay:
                wait = self.inter_request_delay - elapsed
                logger.debug(f"   ⏱  انتظار {wait:.1f}s بين الجزأين")
                time.sleep(wait)
            self._last_request_time = time.time()

    # ═══════════════════════════════════════════════════════════════
    # Main API (تعديل التقسيم إلى جزأين والانتظار 70 ثانية)
    # ═══════════════════════════════════════════════════════════════
    def generate_audio(
        self,
        script: dict,
        output_path: str,
        progress_callback: Optional[Callable] = None,
        **kwargs,
    ) -> TTSResult:
        start_time = time.time()
        self._ensure_output_dir(output_path)

        scenes = self._extract_scenes(script)
        if not scenes:
            return TTSResult(status=TTSStatus.FAILED, output_path=output_path, error="No scenes")

        # 1. تقسيم كافة المشاهد إلى جزأين فقط
        mid_point = (len(scenes) + 1) // 2
        part_1 = scenes[:mid_point]
        part_2 = scenes[mid_point:]
        
        chunks = []
        if part_1:
            chunks.append(" . ".join([s.get("text", "").strip() for s in part_1 if s.get("text", "").strip()]))
        if part_2:
            chunks.append(" . ".join([s.get("text", "").strip() for s in part_2 if s.get("text", "").strip()]))

        total_chars = sum(len(c) for c in chunks)
        logger.info(f"🎙️ Gemini TTS | تم تقسيم النص إلى {len(chunks)} أجزاء بدلاً من {len(scenes)} مشاهد لتفادي الـ Rate Limit")

        temp_dir = Path(tempfile.mkdtemp(prefix="gemini_tts_"))
        audio_files = []

        try:
            for i, text_chunk in enumerate(chunks):
                if progress_callback:
                    progress_callback(0.1 + (i / len(chunks)) * 0.75, f"جزء {i+1}/{len(chunks)}")

                if i > 0:
                    self._wait_for_rate_limit()

                audio_path = self._process_chunk(text_chunk, i, temp_dir)
                if audio_path:
                    audio_files.append(audio_path)
                else:
                    logger.warning(f"  ⚠ فشل توليد الجزء {i+1}")

            if not audio_files:
                return TTSResult(status=TTSStatus.FAILED, output_path=output_path, error="All scenes failed")

            if progress_callback:
                progress_callback(0.9, "دمج الملفات الصوتية للأجزاء...")

            self._merge_audio(audio_files, output_path)

            elapsed = time.time() - start_time
            file_size = Path(output_path).stat().st_size if Path(output_path).exists() else 0

            if progress_callback:
                progress_callback(1.0, "تم!")

            logger.info(f"   ✅ تم! نجح توليد {len(audio_files)}/{len(chunks)} جزء ({file_size/1024:.1f} KB) في {elapsed:.1f}s")

            return TTSResult(
                status=TTSStatus.SUCCESS if len(audio_files) == len(chunks) else TTSStatus.PARTIAL,
                output_path=output_path,
                voice_used=self.voice_name,
                text_length=total_chars,
                file_size=file_size,
                duration_estimate=estimate_duration(" ".join(chunks[:len(audio_files)])),
            )

        except Exception as e:
            logger.error(f"❌ فشل السكربت بالكامل: {e}")
            return self._silence_result(output_path, str(e))

        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)

    # ═══════════════════════════════════════════════════════════════
    # Chunk Processing (انتظار 70 ثانية عند الخطأ)
    # ═══════════════════════════════════════════════════════════════
    def _process_chunk(self, text: str, index: int, temp_dir: Path) -> Optional[str]:
        if not text.strip():
            return None

        logger.info(f"   🎤 جاري معالجة الجزء {index+1} ({len(text)} حرف)...")
        chunk_path = str(temp_dir / f"chunk_{index:03d}.raw")

        for attempt in range(GeminiTTSConstants.MAX_RETRIES):
            try:
                if attempt > 0:
                    # تعديل صريح: الانتظار 70 ثانية ثابتة عند حدوث أي فشل في المحاولة السابقة
                    logger.info(f"      ⏱  فشل سابق أو حد استخدام.. انتظار 70 ثانية تماماً قبل المحاولة {attempt+1}...")
                    time.sleep(GeminiTTSConstants.FIXED_RETRY_DELAY)

                audio_data = self._call_api(text)

                if audio_data and len(audio_data) > GeminiTTSConstants.MIN_AUDIO_SIZE:
                    with open(chunk_path, "wb") as f:
                        f.write(audio_data)
                    return chunk_path

            except Exception as e:
                error_str = str(e)
                logger.warning(f"      ⚠ خطأ في المحاولة {attempt+1}: {error_str[:90]}")

        return None

    # ═══════════════════════════════════════════════════════════════
    # API Call
    # ═══════════════════════════════════════════════════════════════
    def _call_api(self, text: str) -> bytes:
        style = STYLE_PRESETS.get(self.style_preset, STYLE_PRESETS["motivational"])

        prompt = (
            f"Read this transcript with the following style.\n\n"
            f"Audio Profile: {style.audio_profile}\n"
            f"Director's Note: {style.directors_note}\n\n"
            f"Transcript:\n{text}"
        )

        config = self._types.GenerateContentConfig(
            response_modalities=["audio"],
            speech_config=self._types.SpeechConfig(
                voice_config=self._types.VoiceConfig(
                    prebuilt_voice_config=self._types.PrebuiltVoiceConfig(
                        voice_name=self.voice_name
                    )
                )
            ),
        )

        response = self._client.models.generate_content(
            model=GeminiTTSConstants.MODEL_NAME,
            contents=prompt,
            config=config,
        )

        if not response.candidates:
            raise RuntimeError("لم يتم استلام رد من نموذج الصوت")

        candidate = response.candidates[0]
        if not candidate.content or not candidate.content.parts:
            raise RuntimeError("لا محتوى في رد Gemini")

        audio_parts = []
        for part in candidate.content.parts:
            if part.inline_data and part.inline_data.data:
                audio_parts.append(part.inline_data.data)

        if not audio_parts:
            raise RuntimeError("لم يتم استلام بيانات صوتية من الـ API")

        return b"".join(audio_parts)

    # ═══════════════════════════════════════════════════════════════
    # Audio Merging
    # ═══════════════════════════════════════════════════════════════
    def _merge_audio(self, files: List[str], output: str):
        if not files:
            raise RuntimeError("لا توجد ملفات لدمجها")

        combined = self._AudioSegment.empty()

        for f in files:
            segment = None
            try:
                segment = self._AudioSegment.from_file(f)
            except Exception:
                pass

            if segment is None:
                try:
                    with open(f, "rb") as fh:
                        raw_data = fh.read()

                    if len(raw_data) > 100:
                        segment = self._AudioSegment(
                            data=raw_data,
                            sample_width=GeminiTTSConstants.RAW_PCM_SAMPLE_WIDTH,
                            frame_rate=GeminiTTSConstants.RAW_PCM_FRAME_RATE,
                            channels=GeminiTTSConstants.RAW_PCM_CHANNELS,
                        )
                        logger.info(f"   ✓ {Path(f).name} → تم التحويل كـ raw PCM")
                except Exception as e2:
                    logger.error(f"   ❌ فشل دمج {Path(f).name}: {e2}")
                    continue

            if segment is not None:
                combined += segment

        if len(combined) == 0:
            raise RuntimeError("الملفات الصوتية المدمجة فارغة")

        fmt = "mp3" if output.endswith(".mp3") else "wav"
        combined.export(output, format=fmt, bitrate="192k" if fmt == "mp3" else None)
        logger.info(f"   ✓ دُمج بنجاح {len(files)} كتل صوتية.")

    # ═══════════════════════════════════════════════════════════════
    # Scene Extraction
    # ═══════════════════════════════════════════════════════════════
    def _extract_scenes(self, script: dict) -> List[dict]:
        scenes = script.get("scenes", [])
        if scenes:
            return [s for s in scenes if s.get("text", "").strip()]

        full_text = script.get("full_text", "").strip()
        if full_text:
            max_c = GeminiTTSConstants.SCENE_TEXT_MAX_CHARS
            chunks = []
            while full_text:
                if len(full_text) <= max_c:
                    chunks.append({"text": full_text})
                    break
                pos = full_text[:max_c].rfind(".")
                if pos == -1:
                    pos = full_text[:max_c].rfind(" ")
                if pos == -1:
                    pos = max_c
                chunks.append({"text": full_text[:pos+1].strip()})
                full_text = full_text[pos+1:].strip()
            return chunks

        hook = script.get("hook", "").strip()
        return [{"text": hook}] if hook else []

    @staticmethod
    def list_voices():
        return GEMINI_VOICES.copy()

    @staticmethod
    def list_styles():
        return STYLE_PRESETS.copy()
