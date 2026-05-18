"""
🎚️ Audio FX Engine v2.0 — Pro
═══════════════════════════════════════════════════════════════
محرك معالجة صوتي احترافي:
  ✓ Voice processing (mood-aware)
  ✓ Music processing مع ducking
  ✓ Audio mixing متعدد المسارات
  ✓ Loudness normalization
  ✓ Caching ذكي
  ✓ Result dataclass

التحسينات v2.0:
  ✓ يستخدم ffmpeg_utils.py
  ✓ AudioFXResult dataclass
  ✓ SFXTrack dataclass
  ✓ Mood-aware processing
  ✓ Volume ducking
  ✓ Custom presets
  ✓ Caching
═══════════════════════════════════════════════════════════════
"""

from __future__ import annotations

import os
import time
import shutil
import hashlib
import logging
from pathlib import Path
from enum import Enum
from dataclasses import dataclass, field
from typing import Optional, Callable

from engine.video.voice.ffmpeg_utils import (
    FFmpegResult, FFmpegConstants,
    ensure_ffmpeg, run_ffmpeg, safe_copy,
    get_audio_duration, generate_silence,
)

logger = logging.getLogger(__name__)


# ═══════════════════════════════════════════════════════════════════
# Enums
# ═══════════════════════════════════════════════════════════════════
class LoudnessPreset(str, Enum):
    """Presets للـ loudness."""
    YOUTUBE = "youtube"      # -14 LUFS
    TIKTOK = "tiktok"        # -14 LUFS
    INSTAGRAM = "instagram"  # -14 LUFS
    SPOTIFY = "spotify"      # -14 LUFS
    PODCAST = "podcast"      # -16 LUFS
    BROADCAST = "broadcast"  # -23 LUFS (EBU R128)


class VoiceMood(str, Enum):
    """مزاج الصوت."""
    NEUTRAL = "neutral"
    INTENSE = "intense"
    CALM = "calm"
    DARK = "dark"
    BRIGHT = "bright"
    DRAMATIC = "dramatic"


# ═══════════════════════════════════════════════════════════════════
# Dataclasses
# ═══════════════════════════════════════════════════════════════════
@dataclass
class LoudnessConfig:
    """إعدادات الـ loudness."""
    I: float    # Integrated loudness
    TP: float   # True peak
    LRA: float  # Loudness range


@dataclass
class SFXTrack:
    """مسار مؤثر صوتي."""
    path: str
    start_time: float
    volume: float = 1.0
    
    @property
    def exists(self) -> bool:
        return Path(self.path).exists()


@dataclass
class AudioFXResult:
    """نتيجة المعالجة."""
    success: bool
    output_path: str
    duration: float = 0.0
    file_size: int = 0
    operations_applied: list[str] = field(default_factory=list)
    elapsed_seconds: float = 0.0
    cached: bool = False
    error: Optional[str] = None
    
    def summary(self) -> str:
        return (
            f"📊 AudioFX Result:\n"
            f"   • Status: {'✅' if self.success else '❌'}\n"
            f"   • Duration: {self.duration:.1f}s\n"
            f"   • Size: {self.file_size / 1024:.0f} KB\n"
            f"   • Operations: {', '.join(self.operations_applied)}\n"
            f"   • Time: {self.elapsed_seconds:.1f}s\n"
            f"   • Cached: {self.cached}"
        )


# ═══════════════════════════════════════════════════════════════════
# Presets
# ═══════════════════════════════════════════════════════════════════
LOUDNESS_PRESETS: dict[str, LoudnessConfig] = {
    "youtube":   LoudnessConfig(I=-14, TP=-1.0, LRA=7),
    "tiktok":    LoudnessConfig(I=-14, TP=-1.0, LRA=7),
    "instagram": LoudnessConfig(I=-14, TP=-1.0, LRA=7),
    "spotify":   LoudnessConfig(I=-14, TP=-1.0, LRA=7),
    "podcast":   LoudnessConfig(I=-16, TP=-1.5, LRA=11),
    "broadcast": LoudnessConfig(I=-23, TP=-1.0, LRA=7),
}


# ═══════════════════════════════════════════════════════════════════
# Voice Filter Templates (حسب المزاج)
# ═══════════════════════════════════════════════════════════════════
MOOD_FILTER_TEMPLATES: dict[str, dict] = {
    "neutral": {
        "eq_low": "equalizer=f=200:t=o:w=2:g=3",
        "eq_mid": "equalizer=f=3000:t=o:w=2:g=1",
        "eq_high": "equalizer=f=8000:t=o:w=2:g=-1",
        "bass": "bass=g=3:f=80:t=o:w=0.8",
        "echo": "aecho=0.6:0.5:35|45:0.18|0.10",
    },
    "intense": {
        "eq_low": "equalizer=f=200:t=o:w=2:g=4",
        "eq_mid": "equalizer=f=3000:t=o:w=2:g=3",
        "eq_high": "equalizer=f=8000:t=o:w=2:g=1",
        "bass": "bass=g=4:f=80:t=o:w=0.8",
        "echo": "aecho=0.7:0.6:40|60:0.20|0.12",
    },
    "calm": {
        "eq_low": "equalizer=f=200:t=o:w=2:g=2",
        "eq_mid": "equalizer=f=3000:t=o:w=2:g=0",
        "eq_high": "equalizer=f=8000:t=o:w=2:g=-2",
        "bass": "bass=g=2:f=80:t=o:w=0.8",
        "echo": None,  # بدون echo للهادئ
    },
    "dark": {
        "eq_low": "equalizer=f=150:t=o:w=2:g=5",
        "eq_mid": "equalizer=f=2000:t=o:w=2:g=-1",
        "eq_high": "equalizer=f=8000:t=o:w=2:g=-3",
        "bass": "bass=g=6:f=60:t=o:w=0.8",
        "echo": "aecho=0.7:0.5:50|80:0.25|0.15",
    },
    "bright": {
        "eq_low": "equalizer=f=200:t=o:w=2:g=2",
        "eq_mid": "equalizer=f=3000:t=o:w=2:g=3",
        "eq_high": "equalizer=f=10000:t=o:w=2:g=2",
        "bass": "bass=g=2:f=80:t=o:w=0.8",
        "echo": None,
    },
    "dramatic": {
        "eq_low": "equalizer=f=200:t=o:w=2:g=4",
        "eq_mid": "equalizer=f=2500:t=o:w=2:g=2",
        "eq_high": "equalizer=f=8000:t=o:w=2:g=0",
        "bass": "bass=g=5:f=70:t=o:w=0.8",
        "echo": "aecho=0.8:0.7:60|90:0.30|0.20",
    },
}


# ═══════════════════════════════════════════════════════════════════
# Helper
# ═══════════════════════════════════════════════════════════════════
def get_cache_key(*args) -> str:
    """إنشاء cache key."""
    content = "|".join(str(a) for a in args)
    return hashlib.md5(content.encode()).hexdigest()[:16]


# ═══════════════════════════════════════════════════════════════════
# Main Class
# ═══════════════════════════════════════════════════════════════════
class AudioFX:
    """محرك معالجة الصوت v2.0."""
    
    def __init__(
        self,
        loudness_preset: str = "youtube",
        voice_volume: float = 1.0,
        music_volume: float = 0.15,
        echo_enabled: bool = True,
        cache_enabled: bool = True,
        cache_dir: Optional[str] = None,
    ):
        # FFmpeg check
        ensure_ffmpeg()
        
        # Settings
        self.loudness_preset = loudness_preset
        self.voice_volume = float(os.getenv("VOICE_VOLUME", voice_volume))
        self.music_volume = float(os.getenv("MUSIC_VOLUME", music_volume))
        self.echo_enabled = (
            os.getenv("VOICE_ECHO_ENABLED", str(echo_enabled)).lower() == "true"
        )
        
        # Cache
        self.cache_enabled = cache_enabled
        if cache_enabled:
            self.cache_dir = Path(
                cache_dir or
                Path(os.getenv("TEMP_DIR", "./temp")) / "audio_fx_cache"
            )
            self.cache_dir.mkdir(parents=True, exist_ok=True)
        else:
            self.cache_dir = None
        
        # Temp
        self.temp_dir = Path(os.getenv("TEMP_DIR", "./temp"))
        self.temp_dir.mkdir(parents=True, exist_ok=True)
        
        logger.info(
            f"🎚️ AudioFX v2.0 | Loudness: {loudness_preset} | "
            f"Voice: {self.voice_volume} | Music: {self.music_volume}"
        )
    
    # ═══════════════════════════════════════════════════════════════
    # Voice Processing
    # ═══════════════════════════════════════════════════════════════
    def process_voice(
        self,
        voice_path: str,
        output_path: str,
        mood: str = "neutral",
        progress_callback: Optional[Callable[[float, str], None]] = None,
    ) -> AudioFXResult:
        """معالجة الصوت البشري (مع mood-awareness)."""
        start = time.time()
        operations = []
        
        if not self._validate_input(voice_path):
            return AudioFXResult(
                success=False,
                output_path=output_path,
                error="Invalid input",
            )
        
        # تحقق من الكاش
        if self.cache_enabled:
            cache_key = get_cache_key(
                voice_path, mood, self.loudness_preset,
                self.echo_enabled, "voice"
            )
            cached = self._get_cached(cache_key)
            if cached:
                shutil.copy(cached, output_path)
                logger.info("⚡ Voice من الكاش")
                
                if progress_callback:
                    progress_callback(1.0, "من الكاش")
                
                return AudioFXResult(
                    success=True,
                    output_path=output_path,
                    duration=get_audio_duration(output_path),
                    file_size=Path(output_path).stat().st_size,
                    operations_applied=["cached"],
                    elapsed_seconds=time.time() - start,
                    cached=True,
                )
        
        if progress_callback:
            progress_callback(0.2, f"تطبيق فلاتر ({mood})...")
        
        # بناء filter chain حسب المزاج
        filter_chain = self._build_voice_filters(mood)
        operations.append(f"voice_processing_{mood}")
        
        if self.echo_enabled:
            operations.append("echo")
        operations.append("loudnorm")
        
        if progress_callback:
            progress_callback(0.5, "معالجة الصوت...")
        
        # محاولة المعالجة الكاملة
        result = run_ffmpeg(
            ["-i", voice_path, "-af", filter_chain],
            output_path,
            description="Voice processing",
        )
        
        if result.success:
            # حفظ في الكاش
            if self.cache_enabled:
                self._save_to_cache(output_path, cache_key)
            
            if progress_callback:
                progress_callback(1.0, "تم!")
            
            logger.info(f"✓ Voice processed ({mood})")
            return AudioFXResult(
                success=True,
                output_path=output_path,
                duration=result.duration,
                file_size=result.file_size,
                operations_applied=operations,
                elapsed_seconds=time.time() - start,
            )
        
        # Fallback 1: loudnorm فقط
        logger.warning("⚠ Full processing failed, trying loudnorm...")
        preset = LOUDNESS_PRESETS[self.loudness_preset]
        result = run_ffmpeg(
            [
                "-i", voice_path,
                "-af", f"loudnorm=I={preset.I}:TP={preset.TP}:LRA={preset.LRA}",
            ],
            output_path,
            description="Loudnorm only",
        )
        
        if result.success:
            return AudioFXResult(
                success=True,
                output_path=output_path,
                duration=result.duration,
                file_size=result.file_size,
                operations_applied=["loudnorm_fallback"],
                elapsed_seconds=time.time() - start,
            )
        
        # Fallback 2: copy
        logger.warning("⚠ Copying original")
        if safe_copy(voice_path, output_path):
            return AudioFXResult(
                success=True,
                output_path=output_path,
                duration=get_audio_duration(output_path),
                file_size=Path(output_path).stat().st_size,
                operations_applied=["copy_only"],
                elapsed_seconds=time.time() - start,
            )
        
        return AudioFXResult(
            success=False,
            output_path=output_path,
            elapsed_seconds=time.time() - start,
            error=result.error,
        )
    
    def _build_voice_filters(self, mood: str) -> str:
        """بناء filter chain حسب المزاج."""
        template = MOOD_FILTER_TEMPLATES.get(
            mood, MOOD_FILTER_TEMPLATES["neutral"]
        )
        preset = LOUDNESS_PRESETS[self.loudness_preset]
        
        filters = [
            template["eq_low"],
            template["eq_mid"],
            template["eq_high"],
            # Compressor
            "compand=attacks=0.02:decays=0.15:"
            "points=-90/-90|-60/-30|-30/-15|-10/-8|0/-6:"
            "gain=4:volume=-90:delay=0.05",
        ]
        
        # Echo (اختياري حسب mood)
        if self.echo_enabled and template["echo"]:
            filters.append(template["echo"])
        
        # Bass
        filters.append(template["bass"])
        
        # Loudness
        filters.append(
            f"loudnorm=I={preset.I}:TP={preset.TP}:LRA={preset.LRA}"
        )
        
        return ",".join(filters)
    
    # ═══════════════════════════════════════════════════════════════
    # Music Processing
    # ═══════════════════════════════════════════════════════════════
    def process_music(
        self,
        music_path: str,
        output_path: str,
        volume: float = 0.20,
        fade_in: float = 2.0,
        fade_out: float = 3.0,
        normalize: bool = True,
        target_duration: Optional[float] = None,
    ) -> AudioFXResult:
        """معالجة الموسيقى."""
        start = time.time()
        operations = []
        
        if not self._validate_input(music_path):
            return AudioFXResult(
                success=False,
                output_path=output_path,
                error="Invalid input",
            )
        
        # المدة
        duration = target_duration or get_audio_duration(music_path)
        if duration <= 0:
            safe_copy(music_path, output_path)
            return AudioFXResult(
                success=True,
                output_path=output_path,
                operations_applied=["copy"],
                elapsed_seconds=time.time() - start,
            )
        
        # بناء filters
        fade_out_start = max(duration - fade_out, 0.1)
        
        filter_parts = [
            f"volume={volume}",
            f"afade=t=in:st=0:d={fade_in}",
            f"afade=t=out:st={fade_out_start:.2f}:d={fade_out}",
        ]
        operations.extend(["volume", "fade_in", "fade_out"])
        
        if normalize:
            filter_parts.append("loudnorm=I=-20:TP=-2:LRA=11")
            operations.append("normalize")
        
        filter_chain = ",".join(filter_parts)
        
        # تنفيذ
        args = ["-i", music_path, "-af", filter_chain]
        if target_duration:
            args.extend(["-t", str(target_duration)])
        
        result = run_ffmpeg(
            args,
            output_path,
            description="Music processing",
        )
        
        if result.success:
            logger.info(f"✓ Music processed (vol={volume})")
            return AudioFXResult(
                success=True,
                output_path=output_path,
                duration=result.duration,
                file_size=result.file_size,
                operations_applied=operations,
                elapsed_seconds=time.time() - start,
            )
        
        # Fallback
        safe_copy(music_path, output_path)
        return AudioFXResult(
            success=False,
            output_path=output_path,
            elapsed_seconds=time.time() - start,
            error=result.error,
        )
    
    # ═══════════════════════════════════════════════════════════════
    # Audio Mixing (Voice + Music + SFX + Ducking)
    # ═══════════════════════════════════════════════════════════════
    def mix_audio_tracks(
        self,
        voice_path: str,
        music_path: str,
        sfx_tracks: list[SFXTrack],
        output_path: str,
        total_duration: float,
        music_volume: Optional[float] = None,
        voice_volume: Optional[float] = None,
        enable_ducking: bool = True,
        progress_callback: Optional[Callable[[float, str], None]] = None,
    ) -> AudioFXResult:
        """
        مزج Voice + Music + SFX مع volume ducking.
        
        Args:
            enable_ducking: تخفيض الموسيقى عند الكلام (sidechain)
        """
        start = time.time()
        operations = []
        
        # ── Validation ──
        if not self._validate_input(voice_path):
            return AudioFXResult(
                success=False,
                output_path=output_path,
                error="Voice file invalid",
            )
        
        has_music = self._validate_input(music_path)
        if not has_music:
            logger.warning("⚠ لا موسيقى، نسخ الصوت فقط")
            safe_copy(voice_path, output_path)
            return AudioFXResult(
                success=True,
                output_path=output_path,
                duration=get_audio_duration(output_path),
                file_size=Path(output_path).stat().st_size,
                operations_applied=["voice_only"],
                elapsed_seconds=time.time() - start,
            )
        
        # Volumes
        v_vol = voice_volume if voice_volume is not None else self.voice_volume
        m_vol = music_volume if music_volume is not None else self.music_volume
        safe_dur = max(float(total_duration), 1.0)
        fade_start = max(safe_dur - 3.0, 0.1)
        
        # Valid SFX
        valid_sfx = [s for s in sfx_tracks if s.exists and s.start_time < safe_dur]
        
        if progress_callback:
            progress_callback(0.1, f"إعداد المزج ({len(valid_sfx)} SFX)")
        
        # ── بناء الـ inputs ──
        inputs = ["-i", voice_path, "-i", music_path]
        for sfx in valid_sfx:
            inputs += ["-i", sfx.path]
        
        # ── بناء filter chain ──
        filter_parts = []
        
        # 1. Voice
        filter_parts.append(f"[0:a]volume={v_vol}[voice]")
        operations.append("voice")
        
        # 2. Music (مع ducking إذا مفعل)
        if enable_ducking:
            # Sidechain compression: الموسيقى تنخفض عند الكلام
            filter_parts.append(
                f"[1:a]aloop=loop=-1:size=2147483647,"
                f"atrim=duration={safe_dur:.2f},"
                f"volume={m_vol},"
                f"afade=t=in:st=0:d=2,"
                f"afade=t=out:st={fade_start:.2f}:d=3[music_raw]"
            )
            filter_parts.append(
                f"[music_raw][voice]sidechaincompress="
                f"threshold=0.05:ratio=8:attack=20:release=300[music]"
            )
            operations.append("music_with_ducking")
        else:
            filter_parts.append(
                f"[1:a]aloop=loop=-1:size=2147483647,"
                f"atrim=duration={safe_dur:.2f},"
                f"volume={m_vol},"
                f"afade=t=in:st=0:d=2,"
                f"afade=t=out:st={fade_start:.2f}:d=3[music]"
            )
            operations.append("music")
        
        # 3. SFX
        sfx_labels = []
        for i, sfx in enumerate(valid_sfx):
            delay_ms = int(sfx.start_time * 1000)
            label = f"sfx{i}"
            filter_parts.append(
                f"[{i + 2}:a]adelay={delay_ms}|{delay_ms},"
                f"volume={sfx.volume}[{label}]"
            )
            sfx_labels.append(f"[{label}]")
        
        if sfx_labels:
            operations.append(f"sfx_{len(sfx_labels)}_tracks")
        
        # 4. Final mix
        all_inputs = "[voice][music]" + "".join(sfx_labels)
        total_inputs = 2 + len(valid_sfx)
        filter_parts.append(
            f"{all_inputs}amix=inputs={total_inputs}:"
            f"duration=first:normalize=0[out]"
        )
        
        if progress_callback:
            progress_callback(0.5, "مزج المسارات...")
        
        # ── تنفيذ ──
        result = run_ffmpeg(
            inputs + [
                "-filter_complex", ";".join(filter_parts),
                "-map", "[out]",
            ],
            output_path,
            description=f"Mix (voice+music+{len(valid_sfx)} SFX)",
        )
        
        if result.success:
            if progress_callback:
                progress_callback(1.0, "تم!")
            
            logger.info(f"✓ Mixed successfully")
            return AudioFXResult(
                success=True,
                output_path=output_path,
                duration=result.duration,
                file_size=result.file_size,
                operations_applied=operations,
                elapsed_seconds=time.time() - start,
            )
        
        # Fallback: voice + music فقط
        logger.warning("⚠ Full mix failed, trying voice + music...")
        return self._mix_voice_music_only(
            voice_path, music_path, output_path,
            safe_dur, m_vol, v_vol, start,
        )
    
    def _mix_voice_music_only(
        self,
        voice_path: str,
        music_path: str,
        output_path: str,
        duration: float,
        music_vol: float,
        voice_vol: float,
        start_time: float,
    ) -> AudioFXResult:
        """مزج voice + music فقط."""
        filters = (
            f"[0:a]volume={voice_vol}[v];"
            f"[1:a]aloop=loop=-1:size=2147483647,"
            f"atrim=duration={duration:.2f},"
            f"volume={music_vol}[m];"
            f"[v][m]amix=inputs=2:duration=first:normalize=0[out]"
        )
        
        result = run_ffmpeg(
            [
                "-i", voice_path,
                "-i", music_path,
                "-filter_complex", filters,
                "-map", "[out]",
            ],
            output_path,
            description="Voice + Music",
        )
        
        if result.success:
            return AudioFXResult(
                success=True,
                output_path=output_path,
                duration=result.duration,
                file_size=result.file_size,
                operations_applied=["voice_music_fallback"],
                elapsed_seconds=time.time() - start_time,
            )
        
        # آخر fallback
        safe_copy(voice_path, output_path)
        return AudioFXResult(
            success=False,
            output_path=output_path,
            elapsed_seconds=time.time() - start_time,
            error=result.error,
        )
    
    # ═══════════════════════════════════════════════════════════════
    # Simple Operations
    # ═══════════════════════════════════════════════════════════════
    def normalize(
        self,
        input_path: str,
        output_path: str,
        preset: Optional[str] = None,
    ) -> AudioFXResult:
        """Loudness normalization."""
        preset_name = preset or self.loudness_preset
        cfg = LOUDNESS_PRESETS.get(preset_name, LOUDNESS_PRESETS["youtube"])
        
        result = run_ffmpeg(
            [
                "-i", input_path,
                "-af", f"loudnorm=I={cfg.I}:TP={cfg.TP}:LRA={cfg.LRA}",
            ],
            output_path,
            description=f"Normalize ({preset_name})",
        )
        
        return AudioFXResult(
            success=result.success,
            output_path=output_path,
            duration=result.duration,
            file_size=result.file_size,
            operations_applied=[f"normalize_{preset_name}"],
            elapsed_seconds=result.elapsed_seconds,
            error=result.error,
        )
    
    def add_silence(
        self,
        duration: float,
        output_path: str,
    ) -> AudioFXResult:
        """توليد صمت."""
        result = generate_silence(duration, output_path)
        return AudioFXResult(
            success=result.success,
            output_path=output_path,
            duration=duration,
            file_size=result.file_size,
            operations_applied=["silence"],
            elapsed_seconds=result.elapsed_seconds,
            error=result.error,
        )
    
    # ═══════════════════════════════════════════════════════════════
    # Caching
    # ═══════════════════════════════════════════════════════════════
    def _get_cached(self, cache_key: str) -> Optional[str]:
        """جلب من الكاش."""
        if not self.cache_enabled or not self.cache_dir:
            return None
        cache_path = self.cache_dir / f"{cache_key}.mp3"
        if cache_path.exists() and cache_path.stat().st_size > 1000:
            return str(cache_path)
        return None
    
    def _save_to_cache(self, source_path: str, cache_key: str) -> None:
        """حفظ في الكاش."""
        if not self.cache_enabled or not self.cache_dir:
            return
        try:
            cache_path = self.cache_dir / f"{cache_key}.mp3"
            shutil.copy(source_path, cache_path)
        except Exception as e:
            logger.warning(f"⚠ Cache save failed: {e}")
    
    def clear_cache(self) -> int:
        """مسح الكاش."""
        if not self.cache_enabled or not self.cache_dir:
            return 0
        count = 0
        for f in self.cache_dir.glob("*.mp3"):
            f.unlink()
            count += 1
        logger.info(f"🗑 حُذف {count} ملف")
        return count
    
    # ═══════════════════════════════════════════════════════════════
    # Validation
    # ═══════════════════════════════════════════════════════════════
    def _validate_input(self, path: str) -> bool:
        """التحقق من الملف."""
        if not Path(path).exists():
            logger.error(f"❌ غير موجود: {path}")
            return False
        if Path(path).stat().st_size < 100:
            logger.error(f"❌ فارغ/تالف: {path}")
            return False
        return True
    
    # ═══════════════════════════════════════════════════════════════
    # Utility (للتوافق الخلفي)
    # ═══════════════════════════════════════════════════════════════
    def get_audio_duration(self, path: str) -> float:
        """مدة الصوت."""
        return get_audio_duration(path)
    
    @staticmethod
    def list_loudness_presets() -> list[str]:
        return list(LOUDNESS_PRESETS.keys())
    
    @staticmethod
    def list_voice_moods() -> list[str]:
        return list(MOOD_FILTER_TEMPLATES.keys())


# ═══════════════════════════════════════════════════════════════════
# اختبار سريع
# ═══════════════════════════════════════════════════════════════════
if __name__ == "__main__":
    import sys
    
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s | %(levelname)s | %(message)s"
    )
    
    if len(sys.argv) < 3:
        print("Usage: python audio_fx.py <input.mp3> <output.mp3> [mood]")
        print(f"Moods: {AudioFX.list_voice_moods()}")
        sys.exit(1)
    
    fx = AudioFX(loudness_preset="youtube")
    
    mood = sys.argv[3] if len(sys.argv) > 3 else "neutral"
    
    result = fx.process_voice(sys.argv[1], sys.argv[2], mood=mood)
    print()
    print(result.summary())
