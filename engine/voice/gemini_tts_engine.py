"""
🎙️ Gemini TTS Engine v4.0 — Scene-by-Scene Pro
═══════════════════════════════════════════════════════════════
الإستراتيجية:
  1. ✅ يولّد كل مشهد بشكل مستقل (Parallel)
  2. ✅ Caching لكل مشهد (توفير API calls)
  3. ✅ يحفظ كل مشهد كملف WAV
  4. ✅ يدمج الكل بـ pydub
  5. ✅ Retry لكل مشهد عند الفشل
  6. ✅ يستخدم voice_tone لكل مشهد
  7. ✅ Progress tracking دقيق

التحسينات v4.0:
  ✓ يرث من BaseTTS
  ✓ TTSResult dataclass
  ✓ Parallel scene generation
  ✓ Per-scene caching
  ✓ Per-scene voice_tone
  ✓ Progress callback
  ✓ Stats tracking
  ✓ Better error handling
═══════════════════════════════════════════════════════════════
"""

from __future__ import annotations

import os
import time
import shutil
import struct
import logging
import mimetypes
import tempfile
from pathlib import Path
from enum import Enum
from dataclasses import dataclass, field
from concurrent.futures import ThreadPoolExecutor, as_completed
from threading import Lock
from typing import Optional, Callable

from engine.video.voice.base_tts import (
    BaseTTS, TTSResult, TTSStatus, VoiceInfo,
    TTSConstants, estimate_duration, get_text_hash
)

logger = logging.getLogger(__name__)


# ═══════════════════════════════════════════════════════════════════
# Voice & Style Definitions
# ═══════════════════════════════════════════════════════════════════
GEMINI_VOICES: dict[str, VoiceInfo] = {
    "Achird": VoiceInfo(
        "Achird", "Achird", "male", "multi",
        "ذكوري عميق - مناسب للسرد",
        provider="gemini"
    ),
    "Algenib": VoiceInfo(
        "Algenib", "Algenib", "male", "multi",
        "ذكوري واضح - مناسب للتعليم",
        provider="gemini"
    ),
    "Aoede": VoiceInfo(
        "Aoede", "Aoede", "female", "multi",
        "أنثوي ناعم - مناسب للقصص",
        provider="gemini"
    ),
    "Charon": VoiceInfo(
        "Charon", "Charon", "male", "multi",
        "ذكوري درامي - مناسب للتشويق",
        provider="gemini"
    ),
    "Kore": VoiceInfo(
        "Kore", "Kore", "female", "multi",
        "أنثوي قوي - مناسب للتحفيز",
        provider="gemini"
    ),
}


# ═══════════════════════════════════════════════════════════════════
# Style Presets (Director's Notes)
# ═══════════════════════════════════════════════════════════════════
@dataclass(frozen=True)
class StylePreset:
    """Preset أسلوب التلاوة."""
    name: str
    audio_profile: str
    directors_note: str
    scene_context: str


STYLE_PRESETS: dict[str, StylePreset] = {
    "motivational": StylePreset(
        "motivational",
        "A smooth, premium commercial voice.",
        "Style: Promo/Hype. Pace: Natural. Accent: Neutral.",
        "Premium commercial. Dynamic pacing. Polished and persuasive.",
    ),
    "educational": StylePreset(
        "educational",
        "A clear, authoritative narrator voice.",
        "Style: Documentary/Educational. Pace: Steady.",
        "Premium documentary narration. Clear pacing.",
    ),
    "story": StylePreset(
        "story",
        "A warm, expressive storyteller voice.",
        "Style: Narrative/Cinematic. Pace: Natural.",
        "Cinematic storytelling. Pacing varies with emotional beats.",
    ),
    "quote": StylePreset(
        "quote",
        "A profound, contemplative voice.",
        "Style: Philosophical/Reflective. Pace: Slow.",
        "Profound quote delivery. Slow, deliberate pacing.",
    ),
    "promo": StylePreset(
        "promo",
        "A smooth, premium commercial voice.",
        "Style: Promo/Hype. Pace: Natural.",
        "Premium commercial. Dynamic pacing.",
    ),
    "viral": StylePreset(
        "viral",
        "A high-energy, attention-grabbing voice.",
        "Style: Viral/Social Media. Pace: Fast.",
        "Viral social media content. Energetic pacing.",
    ),
    "psychological": StylePreset(
        "psychological",
        "A deep, thoughtful, mysterious voice.",
        "Style: Psychological/Deep. Pace: Slow and impactful.",
        "Deep psychological content. Slow, weighted pacing.",
    ),
}


# ═══════════════════════════════════════════════════════════════════
# Mappings
# ═══════════════════════════════════════════════════════════════════
MOOD_VOICE_MAP: dict[str, str] = {
    "motivation":    "Achird",
    "dark":          "Charon",
    "sigma":         "Achird",
    "psychological": "Charon",
    "educational":   "Algenib",
    "scientific":    "Algenib",
    "emotional":     "Aoede",
    "sad":           "Aoede",
    "romantic":      "Aoede",
    "horror":        "Charon",
}

MOOD_STYLE_MAP: dict[str, str] = {
    "motivation":    "motivational",
    "educational":   "educational",
    "story":         "story",
    "psychological": "psychological",
    "dark":          "psychological",
    "sigma":         "psychological",
    "emotional":     "story",
    "sad":           "story",
}

# Voice tone → style override (لكل مشهد)
TONE_TO_STYLE: dict[str, str] = {
    "intense":       "viral",
    "calm":          "story",
    "cold":          "psychological",
    "curious":       "educational",
    "authoritative": "motivational",
    "powerful":      "promo",
}


# ═══════════════════════════════════════════════════════════════════
# Stats
# ═══════════════════════════════════════════════════════════════════
@dataclass
class GeminiTTSStats:
    """إحصائيات الاستخدام."""
    total_scenes: int = 0
    successful_scenes: int = 0
    failed_scenes: int = 0
    cached_scenes: int = 0
    total_chars: int = 0
    total_time: float = 0.0
    
    @property
    def success_rate(self) -> float:
        if self.total_scenes == 0:
            return 0.0
        return (self.successful_scenes / self.total_scenes) * 100
    
    def summary(self) -> str:
        return (
            f"📊 Gemini TTS Stats:\n"
            f"   • Scenes: {self.successful_scenes}/{self.total_scenes} "
            f"({self.success_rate:.1f}%)\n"
            f"   • Cached: {self.cached_scenes}\n"
            f"   • Failed: {self.failed_scenes}\n"
            f"   • Chars: {self.total_chars:,}\n"
            f"   • Time: {self.total_time:.1f}s"
        )


# ═══════════════════════════════════════════════════════════════════
# Constants
# ═══════════════════════════════════════════════════════════════════
class GeminiTTSConstants:
    """ثوابت Gemini TTS."""
    
    # ⚠️ تحقق من اسم الموديل الصحيح في Google AI Studio
    MODEL_NAME = "gemini-2.5-flash-preview-tts"
    # MODEL_NAME = "gemini-3.1-flash-tts-preview"  # نسخة قديمة
    
    DEFAULT_VOICE = "Achird"
    DEFAULT_STYLE = "motivational"
    DEFAULT_TEMPERATURE = 1.0
    
    MAX_RETRIES = 2
    RETRY_DELAY = 2
    
    MIN_AUDIO_SIZE = 500  # bytes
    SCENE_TEXT_MIN_CHARS = 50  # للتقسيم التلقائي
    SCENE_TEXT_MAX_CHARS = 200
    
    PARALLEL_SCENES_DEFAULT = 3  # عدد المشاهد المتوازية


# ═══════════════════════════════════════════════════════════════════
# Main Class
# ═══════════════════════════════════════════════════════════════════
class GeminiTTSEngine(BaseTTS):
    """محرك Gemini TTS v4.0 - Scene-by-Scene Pro."""
    
    PROVIDER_NAME = "gemini_tts"
    PAUSE_FORMAT = "simple"
    MAX_TEXT_LENGTH = GeminiTTSConstants.SCENE_TEXT_MAX_CHARS
    
    def __init__(
        self,
        api_key: Optional[str] = None,
        voice: Optional[str] = None,
        style: Optional[str] = None,
        temperature: Optional[float] = None,
        cache_enabled: bool = True,
        parallel_scenes: int = GeminiTTSConstants.PARALLEL_SCENES_DEFAULT,
    ):
        """
        Args:
            api_key: مفتاح Gemini API
            voice: الصوت الافتراضي
            style: الـ style الافتراضي
            temperature: درجة العشوائية
            cache_enabled: تفعيل الكاش (موفّر API calls!)
            parallel_scenes: عدد المشاهد المتوازية
        """
        super().__init__(cache_enabled=cache_enabled)
        
        # API Key
        self.api_key = api_key or os.getenv("GEMINI_API_KEY", "")
        if not self.api_key:
            raise RuntimeError("❌ GEMINI_API_KEY غير موجود!")
        
        # إعدادات
        self.voice_name = self._validate_voice(
            voice or os.getenv("GEMINI_VOICE", GeminiTTSConstants.DEFAULT_VOICE)
        )
        self.style_preset = self._validate_style(
            style or os.getenv("GEMINI_STYLE", GeminiTTSConstants.DEFAULT_STYLE)
        )
        self.temperature = float(
            temperature or 
            os.getenv("GEMINI_TEMPERATURE", GeminiTTSConstants.DEFAULT_TEMPERATURE)
        )
        self.max_retries = int(
            os.getenv("GEMINI_MAX_RETRIES", GeminiTTSConstants.MAX_RETRIES)
        )
        self.parallel_scenes = parallel_scenes
        
        # Stats
        self.stats = GeminiTTSStats()
        self._stats_lock = Lock()
        
        # Pre-import للمكتبات (أسرع)
        self._init_libs()
        self._init_client()
        
        logger.info(
            f"🎙️ GeminiTTS v4.0 | Voice: {self.voice_name} | "
            f"Style: {self.style_preset} | Parallel: {parallel_scenes}"
        )
    
    # ═══════════════════════════════════════════════════════════════
    # Initialization
    # ═══════════════════════════════════════════════════════════════
    def _validate_voice(self, voice: str) -> str:
        if voice not in GEMINI_VOICES:
            logger.warning(
                f"⚠ Voice '{voice}' غير معروف، "
                f"استخدام {GeminiTTSConstants.DEFAULT_VOICE}"
            )
            return GeminiTTSConstants.DEFAULT_VOICE
        return voice
    
    def _validate_style(self, style: str) -> str:
        if style not in STYLE_PRESETS:
            logger.warning(
                f"⚠ Style '{style}' غير معروف، "
                f"استخدام {GeminiTTSConstants.DEFAULT_STYLE}"
            )
            return GeminiTTSConstants.DEFAULT_STYLE
        return style
    
    def _init_libs(self) -> None:
        """تحميل المكتبات مسبقاً."""
        try:
            from google import genai
            from google.genai import types
            from pydub import AudioSegment
            self._genai = genai
            self._types = types
            self._AudioSegment = AudioSegment
        except ImportError as e:
            raise RuntimeError(
                f"❌ مكتبات مفقودة: {e}\n"
                f"   pip install google-genai pydub"
            )
    
    def _init_client(self) -> None:
        """تهيئة Gemini client."""
        try:
            self._client = self._genai.Client(api_key=self.api_key)
        except Exception as e:
            raise RuntimeError(f"❌ فشل تهيئة Gemini: {e}")
    
    # ═══════════════════════════════════════════════════════════════
    # Override: Voice Selection
    # ═══════════════════════════════════════════════════════════════
    def _select_voice_for_mood(self, mood: str) -> str:
        """اختيار الصوت حسب المزاج."""
        return MOOD_VOICE_MAP.get(mood, self.voice_name)
    
    def _select_style_for_mood(self, mood: str) -> str:
        """اختيار الـ style حسب المزاج."""
        return MOOD_STYLE_MAP.get(mood, self.style_preset)
    
    def _select_style_for_tone(self, voice_tone: str) -> Optional[str]:
        """اختيار style خاص للنبرة."""
        return TONE_TO_STYLE.get(voice_tone)
    
    # ═══════════════════════════════════════════════════════════════
    # Main API (Override)
    # ═══════════════════════════════════════════════════════════════
    def generate_audio(
        self,
        script: dict,
        output_path: str,
        voice: Optional[str] = None,
        style: Optional[str] = None,
        progress_callback: Optional[Callable[[float, str], None]] = None,
    ) -> TTSResult:
        """توليد الصوت مشهد بمشهد."""
        start_time = time.time()
        self._ensure_output_dir(output_path)
        
        # الإعدادات
        mood = script.get("music_mood", "motivation")
        voice_name = voice or self._select_voice(script, mood)
        style_preset = style or self._select_style_for_mood(mood)
        
        # استخراج المشاهد
        scenes_data = self._get_scenes_data(script)
        
        if not scenes_data:
            return TTSResult(
                status=TTSStatus.FAILED,
                output_path=output_path,
                voice_used=voice_name,
                error="No text to convert",
            )
        
        total_chars = sum(len(s["text"]) for s in scenes_data)
        logger.info(
            f"🎙️ Gemini TTS | Voice: {voice_name} | "
            f"Style: {style_preset} | {len(scenes_data)} مشهد | "
            f"{total_chars} حرف"
        )
        
        if progress_callback:
            progress_callback(0.05, f"إعداد {len(scenes_data)} مشهد")
        
        # توليد المشاهد (متوازي)
        temp_dir = Path(tempfile.mkdtemp(prefix="gemini_tts_"))
        
        try:
            wav_files = self._generate_scenes_parallel(
                scenes_data=scenes_data,
                voice_name=voice_name,
                default_style=style_preset,
                temp_dir=temp_dir,
                progress_callback=progress_callback,
            )
            
            if not wav_files:
                return TTSResult(
                    status=TTSStatus.FAILED,
                    output_path=output_path,
                    voice_used=voice_name,
                    error="All scenes failed",
                )
            
            # دمج
            if progress_callback:
                progress_callback(0.9, "دمج الملفات...")
            
            self._merge_wav_files(wav_files, output_path)
            
            # النتيجة
            elapsed = time.time() - start_time
            with self._stats_lock:
                self.stats.total_time += elapsed
            
            file_size = Path(output_path).stat().st_size
            
            if progress_callback:
                progress_callback(1.0, "تم!")
            
            logger.info(
                f"   ✅ تم! {len(wav_files)}/{len(scenes_data)} مشهد "
                f"({file_size / 1024:.1f} KB) في {elapsed:.1f}s"
            )
            
            return TTSResult(
                status=TTSStatus.SUCCESS,
                output_path=output_path,
                voice_used=voice_name,
                text_length=total_chars,
                file_size=file_size,
                duration_estimate=estimate_duration(
                    " ".join(s["text"] for s in scenes_data)
                ),
            )
            
        except Exception as e:
            logger.error(f"❌ فشل توليد الصوت: {e}")
            return self._silence_result(output_path, str(e))
        
        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)
    
    # ═══════════════════════════════════════════════════════════════
    # Scene Extraction
    # ═══════════════════════════════════════════════════════════════
    def _get_scenes_data(self, script: dict) -> list[dict]:
        """استخراج بيانات المشاهد (نص + tone)."""
        scenes = script.get("scenes", [])
        
        if scenes:
            data = []
            for scene in scenes:
                text = scene.get("text", "").strip()
                if text:
                    data.append({
                        "text": text,
                        "voice_tone": scene.get("voice_tone", "intense"),
                        "id": scene.get("id", len(data)),
                    })
            
            if data:
                logger.info(f"   📝 {len(data)} مشاهد من scenes")
                return data
        
        # Fallback: full_text
        full_text = script.get("full_text", "").strip()
        if full_text and len(full_text) > GeminiTTSConstants.SCENE_TEXT_MIN_CHARS:
            chunks = self._split_text(
                full_text,
                GeminiTTSConstants.SCENE_TEXT_MAX_CHARS
            )
            logger.info(f"   📝 {len(chunks)} مشاهد من full_text")
            return [
                {"text": c, "voice_tone": "intense", "id": i}
                for i, c in enumerate(chunks)
            ]
        
        # Last resort: hook
        hook = script.get("hook", "").strip()
        if hook:
            logger.warning(f"   ⚠ Hook فقط")
            return [{"text": hook, "voice_tone": "intense", "id": 0}]
        
        return []
    
    # ═══════════════════════════════════════════════════════════════
    # Parallel Scene Generation
    # ═══════════════════════════════════════════════════════════════
    def _generate_scenes_parallel(
        self,
        scenes_data: list[dict],
        voice_name: str,
        default_style: str,
        temp_dir: Path,
        progress_callback: Optional[Callable] = None,
    ) -> list[str]:
        """توليد المشاهد بشكل متوازٍ."""
        results: dict[int, Optional[str]] = {}
        completed_count = 0
        total = len(scenes_data)
        
        with ThreadPoolExecutor(max_workers=self.parallel_scenes) as executor:
            futures = {
                executor.submit(
                    self._generate_single_scene,
                    scene_data=scene_data,
                    scene_index=i,
                    voice_name=voice_name,
                    default_style=default_style,
                    temp_dir=temp_dir,
                ): i
                for i, scene_data in enumerate(scenes_data)
            }
            
            for future in as_completed(futures):
                idx = futures[future]
                try:
                    wav_path = future.result()
                    results[idx] = wav_path
                except Exception as e:
                    logger.error(f"   ❌ مشهد {idx + 1}: {e}")
                    results[idx] = None
                
                completed_count += 1
                if progress_callback:
                    progress = 0.1 + (completed_count / total) * 0.75
                    progress_callback(
                        progress,
                        f"مشهد {completed_count}/{total}"
                    )
        
        # إعادة الترتيب
        ordered = [results[i] for i in range(total) if results.get(i)]
        return ordered
    
    def _generate_single_scene(
        self,
        scene_data: dict,
        scene_index: int,
        voice_name: str,
        default_style: str,
        temp_dir: Path,
    ) -> Optional[str]:
        """توليد مشهد واحد مع caching و retry."""
        text = scene_data["text"]
        voice_tone = scene_data.get("voice_tone", "intense")
        
        # اختيار style حسب tone
        style_for_tone = self._select_style_for_tone(voice_tone)
        actual_style = style_for_tone or default_style
        
        # تحقق من الكاش
        if self.cache_enabled:
            cached = self._get_cached(text, voice_name, actual_style)
            if cached:
                # نسخ للـ temp_dir
                dest = temp_dir / f"scene_{scene_index:03d}.wav"
                shutil.copy(cached, dest)
                
                with self._stats_lock:
                    self.stats.cached_scenes += 1
                    self.stats.total_scenes += 1
                    self.stats.successful_scenes += 1
                
                logger.info(
                    f"   ⚡ مشهد {scene_index + 1} (cache): "
                    f"{text[:40]}..."
                )
                return str(dest)
        
        logger.info(
            f"   🎤 مشهد {scene_index + 1} "
            f"({len(text)} حرف, tone={voice_tone}): "
            f"{text[:40]}..."
        )
        
        # توليد مع retry
        chunk_wav = str(temp_dir / f"scene_{scene_index:03d}.wav")
        
        for attempt in range(1, self.max_retries + 1):
            try:
                if attempt > 1:
                    time.sleep(GeminiTTSConstants.RETRY_DELAY)
                
                audio_data = self._call_gemini_api(
                    text, voice_name, actual_style
                )
                
                if audio_data and len(audio_data) > GeminiTTSConstants.MIN_AUDIO_SIZE:
                    with open(chunk_wav, "wb") as f:
                        f.write(audio_data)
                    
                    # حفظ في الكاش
                    if self.cache_enabled:
                        self._save_to_cache(
                            chunk_wav, text, voice_name, actual_style
                        )
                    
                    with self._stats_lock:
                        self.stats.total_scenes += 1
                        self.stats.successful_scenes += 1
                        self.stats.total_chars += len(text)
                    
                    return chunk_wav
                
            except Exception as e:
                logger.warning(
                    f"      ⚠ مشهد {scene_index + 1} "
                    f"محاولة {attempt}: {str(e)[:80]}"
                )
        
        # فشل
        with self._stats_lock:
            self.stats.total_scenes += 1
            self.stats.failed_scenes += 1
        
        return None
    
    # ═══════════════════════════════════════════════════════════════
    # Gemini API Call
    # ═══════════════════════════════════════════════════════════════
    def _call_gemini_api(
        self,
        text: str,
        voice_name: str,
        style_preset: str,
    ) -> bytes:
        """استدعاء Gemini API."""
        style_config = STYLE_PRESETS.get(
            style_preset, STYLE_PRESETS["motivational"]
        )
        
        prompt = self._build_prompt(text, style_config)
        
        contents = [
            self._types.Content(
                role="user",
                parts=[self._types.Part.from_text(text=prompt)],
            ),
        ]
        
        config = self._types.GenerateContentConfig(
            temperature=self.temperature,
            response_modalities=["audio"],
            speech_config=self._types.SpeechConfig(
                voice_config=self._types.VoiceConfig(
                    prebuilt_voice_config=self._types.PrebuiltVoiceConfig(
                        voice_name=voice_name
                    )
                )
            ),
        )
        
        audio_chunks = []
        mime_type = None
        
        for chunk in self._client.models.generate_content_stream(
            model=GeminiTTSConstants.MODEL_NAME,
            contents=contents,
            config=config,
        ):
            # ⭐ تصحيح: استخدام candidates بدلاً من parts مباشرة
            if not chunk.candidates:
                continue
            
            candidate = chunk.candidates[0]
            if not candidate.content or not candidate.content.parts:
                continue
            
            part = candidate.content.parts[0]
            if part.inline_data and part.inline_data.data:
                audio_chunks.append(part.inline_data.data)
                if mime_type is None:
                    mime_type = part.inline_data.mime_type
        
        if not audio_chunks:
            raise RuntimeError("لم يتم استلام بيانات صوتية")
        
        raw_audio = b"".join(audio_chunks)
        
        # تحويل لـ WAV
        ext = mimetypes.guess_extension(mime_type) if mime_type else None
        if ext is None or "wav" not in (ext or ""):
            raw_audio = self._convert_to_wav(raw_audio, mime_type)
        
        return raw_audio
    
    # ═══════════════════════════════════════════════════════════════
    # WAV Merging
    # ═══════════════════════════════════════════════════════════════
    def _merge_wav_files(
        self,
        wav_files: list[str],
        output_path: str,
    ) -> None:
        """دمج ملفات WAV."""
        if not wav_files:
            raise RuntimeError("لا توجد ملفات للدمج")
        
        try:
            combined = self._AudioSegment.from_wav(wav_files[0])
            
            for wav_file in wav_files[1:]:
                segment = self._AudioSegment.from_wav(wav_file)
                combined += segment
            
            # Export حسب الامتداد
            if output_path.endswith(".mp3"):
                combined.export(
                    output_path,
                    format="mp3",
                    bitrate="192k",
                )
            else:
                combined.export(output_path, format="wav")
            
            logger.info(f"   ✓ دُمج {len(wav_files)} ملف")
            
        except Exception as e:
            logger.error(f"   ❌ فشل الدمج: {e}")
            # Fallback: نسخ الأول
            shutil.copy(wav_files[0], output_path)
    
    # ═══════════════════════════════════════════════════════════════
    # Text Splitting
    # ═══════════════════════════════════════════════════════════════
    def _split_text(self, text: str, max_chars: int) -> list[str]:
        """تقسيم النص."""
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
    
    # ═══════════════════════════════════════════════════════════════
    # Prompt Building
    # ═══════════════════════════════════════════════════════════════
    def _build_prompt(self, text: str, style_config: StylePreset) -> str:
        """بناء الـ prompt."""
        return f"""Read the following transcript based on the audio profile and director's note.

# Audio Profile
{style_config.audio_profile}

# Director's note
{style_config.directors_note}

## Scene:
The Sound Stage Booth.

## Sample Context:
{style_config.scene_context}

## Transcript:
{text}"""
    
    # ═══════════════════════════════════════════════════════════════
    # WAV Conversion (PCM → WAV)
    # ═══════════════════════════════════════════════════════════════
    def _convert_to_wav(self, audio_data: bytes, mime_type: str) -> bytes:
        """تحويل PCM إلى WAV."""
        params = self._parse_mime(mime_type)
        bps = params["bits_per_sample"]
        rate = params["rate"]
        nc = 1  # mono
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
    
    def _parse_mime(self, mime_type: str) -> dict[str, int]:
        """استخراج معلومات MIME."""
        bps = 16
        rate = 24000
        
        if not mime_type:
            return {"bits_per_sample": bps, "rate": rate}
        
        for param in mime_type.split(";"):
            param = param.strip()
            if param.lower().startswith("rate="):
                try:
                    rate = int(param.split("=", 1)[1])
                except (ValueError, IndexError):
                    pass
            elif param.startswith("audio/L"):
                try:
                    bps = int(param.split("L", 1)[1])
                except (ValueError, IndexError):
                    pass
        
        return {"bits_per_sample": bps, "rate": rate}
    
    # ═══════════════════════════════════════════════════════════════
    # Required from BaseTTS (لا تُستخدم - override generate_audio)
    # ═══════════════════════════════════════════════════════════════
    def _generate_audio_data(
        self,
        text: str,
        voice: str,
        **kwargs,
    ) -> Optional[bytes]:
        """للتوافق مع BaseTTS - نص واحد بدون scenes."""
        try:
            return self._call_gemini_api(
                text, voice, kwargs.get("style", self.style_preset)
            )
        except Exception as e:
            logger.error(f"❌ فشل: {e}")
            return None
    
    # ═══════════════════════════════════════════════════════════════
    # Public Utilities
    # ═══════════════════════════════════════════════════════════════
    @staticmethod
    def list_voices() -> dict[str, VoiceInfo]:
        """قائمة الأصوات."""
        return GEMINI_VOICES.copy()
    
    @staticmethod
    def list_styles() -> dict[str, StylePreset]:
        """قائمة الـ styles."""
        return STYLE_PRESETS.copy()
    
    def print_stats(self):
        """طباعة الإحصائيات."""
        print(self.stats.summary())


# ═══════════════════════════════════════════════════════════════════
# اختبار سريع
# ═══════════════════════════════════════════════════════════════════
if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s | %(levelname)s | %(message)s"
    )
    
    print("=" * 60)
    print("🎙️ Gemini TTS v4.0 Test")
    print("=" * 60)
    
    print(f"\n📋 Voices: {len(GEMINI_VOICES)}")
    for vid, info in GEMINI_VOICES.items():
        print(f"   • {info.name} ({info.gender}) - {info.description}")
    
    print(f"\n🎨 Styles: {len(STYLE_PRESETS)}")
    for name in STYLE_PRESETS:
        print(f"   • {name}")
    
    try:
        tts = GeminiTTSEngine(
            cache_enabled=True,
            parallel_scenes=3,
        )
        
        test_script = {
            "scenes": [
                {
                    "text": "هل تعلم أن 95% من الناس يفشلون بسبب هذا الخطأ؟",
                    "voice_tone": "curious",
                },
                {
                    "text": "السر بسيط جداً... لكن قليلين من يطبقونه.",
                    "voice_tone": "intense",
                },
                {
                    "text": "ابدأ الآن وستلاحظ الفرق بعد 21 يوم.",
                    "voice_tone": "authoritative",
                },
            ],
            "cta": "شارك هذا الفيديو!",
            "music_mood": "motivation",
        }
        
        def progress(p, msg):
            print(f"  [{p*100:3.0f}%] {msg}")
        
        result = tts.generate_audio(
            test_script,
            "test_gemini.mp3",
            progress_callback=progress,
        )
        
        print(f"\n📊 Result:")
        print(f"   Status: {result.status.value}")
        print(f"   Success: {result.success}")
        print(f"   Voice: {result.voice_used}")
        print(f"   Duration: ~{result.duration_estimate:.1f}s")
        print(f"   File: {result.file_size:,} bytes")
        
        print()
        tts.print_stats()
        
    except RuntimeError as e:
        print(f"\n❌ {e}")
