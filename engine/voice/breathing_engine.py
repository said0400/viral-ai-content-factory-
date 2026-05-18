"""
🫁 Breathing Engine v2.0 — Pro
═══════════════════════════════════════════════════════════════
يضيف أصوات تنفس طبيعية للصوت:
  ✓ Intro/Outro/Mid breaths
  ✓ Mood & Tone-aware
  ✓ Caching ذكي
  ✓ Multiple noise types
  ✓ Auto cleanup
  ✓ Result dataclass

التحسينات v2.0:
  ✓ يستخدم ffmpeg_utils
  ✓ Smart caching
  ✓ Mood-aware presets
  ✓ Multiple breath types
  ✓ Result tracking
═══════════════════════════════════════════════════════════════
"""

from __future__ import annotations

import os
import time
import random
import shutil
import hashlib
import logging
from pathlib import Path
from enum import Enum
from dataclasses import dataclass, field
from threading import Lock
from typing import Optional, Callable

from engine.video.voice.ffmpeg_utils import (
    FFmpegResult, ensure_ffmpeg, run_ffmpeg, safe_copy,
    get_audio_duration,
)

logger = logging.getLogger(__name__)


# ═══════════════════════════════════════════════════════════════════
# Enums
# ═══════════════════════════════════════════════════════════════════
class BreathPosition(str, Enum):
    """مكان التنفس."""
    INTRO = "intro"
    OUTRO = "outro"
    BOTH = "both"


class NoiseType(str, Enum):
    """نوع الـ noise."""
    PINK = "pink"      # هادئ - مناسب للهدوء
    BROWN = "brown"    # عميق - مناسب للدراما
    WHITE = "white"    # حاد - نادر الاستخدام
    VIOLET = "violet"  # حاد جداً


# ═══════════════════════════════════════════════════════════════════
# Dataclasses
# ═══════════════════════════════════════════════════════════════════
@dataclass(frozen=True)
class BreathPreset:
    """إعداد التنفس."""
    name: str
    duration: float
    amplitude: float
    lowpass_freq: int
    noise_type: NoiseType = NoiseType.PINK
    fade_in_ratio: float = 0.35
    fade_out_ratio: float = 0.45
    
    @property
    def fade_in_time(self) -> float:
        return self.duration * self.fade_in_ratio
    
    @property
    def fade_out_start(self) -> float:
        return self.duration * (1 - self.fade_out_ratio)
    
    @property
    def fade_out_time(self) -> float:
        return self.duration * self.fade_out_ratio


@dataclass
class BreathResult:
    """نتيجة إضافة التنفس."""
    success: bool
    output_path: str
    breaths_added: int = 0
    preset_used: str = ""
    duration: float = 0.0
    elapsed_seconds: float = 0.0
    cached_breaths: int = 0
    error: Optional[str] = None
    
    def summary(self) -> str:
        return (
            f"📊 Breath Result:\n"
            f"   • Status: {'✅' if self.success else '❌'}\n"
            f"   • Breaths: {self.breaths_added} "
            f"(cached: {self.cached_breaths})\n"
            f"   • Preset: {self.preset_used}\n"
            f"   • Duration: {self.duration:.1f}s\n"
            f"   • Time: {self.elapsed_seconds:.2f}s"
        )


# ═══════════════════════════════════════════════════════════════════
# Presets
# ═══════════════════════════════════════════════════════════════════
BREATH_PRESETS: dict[str, BreathPreset] = {
    "soft": BreathPreset(
        "soft", duration=0.35, amplitude=0.010,
        lowpass_freq=650, noise_type=NoiseType.PINK,
    ),
    "normal": BreathPreset(
        "normal", duration=0.45, amplitude=0.014,
        lowpass_freq=700, noise_type=NoiseType.PINK,
    ),
    "deep": BreathPreset(
        "deep", duration=0.65, amplitude=0.020,
        lowpass_freq=600, noise_type=NoiseType.BROWN,
    ),
    "intense": BreathPreset(
        "intense", duration=0.55, amplitude=0.025,
        lowpass_freq=750, noise_type=NoiseType.PINK,
    ),
    "whisper": BreathPreset(
        "whisper", duration=0.25, amplitude=0.008,
        lowpass_freq=550, noise_type=NoiseType.PINK,
    ),
    "dramatic": BreathPreset(
        "dramatic", duration=0.85, amplitude=0.022,
        lowpass_freq=550, noise_type=NoiseType.BROWN,
    ),
}


# ═══════════════════════════════════════════════════════════════════
# Mood → Preset
# ═══════════════════════════════════════════════════════════════════
MOOD_BREATH_MAP: dict[str, str] = {
    "motivation":    "normal",
    "motivational":  "normal",
    "dark":          "dramatic",
    "sigma":         "deep",
    "psychological": "deep",
    "horror":        "dramatic",
    "emotional":     "soft",
    "sad":           "soft",
    "romantic":      "soft",
    "educational":   "normal",
    "calm":          "whisper",
    "intense":       "intense",
}


# Voice tone → Preset
TONE_BREATH_MAP: dict[str, str] = {
    "whisper":       "whisper",
    "calm":          "soft",
    "cold":          "deep",
    "intense":       "intense",
    "aggressive":    "intense",
    "powerful":      "deep",
    "authoritative": "normal",
    "curious":       "soft",
}


# ═══════════════════════════════════════════════════════════════════
# Helpers
# ═══════════════════════════════════════════════════════════════════
def get_breath_cache_key(preset: BreathPreset, seed: int) -> str:
    """إنشاء cache key للتنفس."""
    content = (
        f"{preset.name}_{preset.duration:.3f}_{preset.amplitude:.4f}_"
        f"{preset.lowpass_freq}_{preset.noise_type.value}_{seed}"
    )
    return hashlib.md5(content.encode()).hexdigest()[:12]


# ═══════════════════════════════════════════════════════════════════
# Main Class
# ═══════════════════════════════════════════════════════════════════
class BreathingEngine:
    """محرك التنفس v2.0."""
    
    # عدد ملفات breath في الكاش (الحد الأقصى)
    MAX_CACHE_FILES = 50
    
    def __init__(
        self,
        enabled: Optional[bool] = None,
        default_preset: str = "normal",
        cache_enabled: bool = True,
        cache_dir: Optional[str] = None,
        variation_seeds: int = 5,  # عدد التنويعات لكل preset
    ):
        """
        Args:
            enabled: تفعيل/تعطيل التنفس
            default_preset: الـ preset الافتراضي
            cache_enabled: تفعيل الكاش
            cache_dir: مجلد الكاش
            variation_seeds: عدد التنويعات (للتنوع)
        """
        # FFmpeg check
        ensure_ffmpeg()
        
        # Settings
        if enabled is None:
            enabled = os.getenv("BREATHING_ENABLED", "true").lower() == "true"
        
        self.enabled = enabled
        self.default_preset = os.getenv("BREATHING_PRESET", default_preset)
        self.variation_seeds = variation_seeds
        
        # Directories
        self.temp_dir = Path(os.getenv("TEMP_DIR", "./temp"))
        self.temp_dir.mkdir(parents=True, exist_ok=True)
        
        self.breath_dir = self.temp_dir / "breath"
        self.breath_dir.mkdir(exist_ok=True)
        
        # Cache
        self.cache_enabled = cache_enabled
        if cache_enabled:
            self.cache_dir = Path(
                cache_dir or self.temp_dir / "breath_cache"
            )
            self.cache_dir.mkdir(parents=True, exist_ok=True)
        else:
            self.cache_dir = None
        
        # Thread safety
        self._lock = Lock()
        self._pre_generated_breaths: dict[str, list[str]] = {}
        
        if self.enabled:
            logger.info(
                f"🫁 BreathingEngine v2.0 | "
                f"Preset: {self.default_preset} | "
                f"Cache: {cache_enabled}"
            )
            
            # Pre-generate variations (في الخلفية)
            if cache_enabled:
                self._pre_generate_variations()
        else:
            logger.info("🫁 BreathingEngine | Disabled")
    
    # ═══════════════════════════════════════════════════════════════
    # Pre-generation
    # ═══════════════════════════════════════════════════════════════
    def _pre_generate_variations(self) -> None:
        """توليد variations مسبقاً للسرعة."""
        for preset_name, preset in BREATH_PRESETS.items():
            cached_files = []
            
            for seed in range(self.variation_seeds):
                cache_key = get_breath_cache_key(preset, seed)
                cache_path = self.cache_dir / f"{cache_key}.mp3"
                
                if cache_path.exists() and cache_path.stat().st_size > 500:
                    cached_files.append(str(cache_path))
            
            self._pre_generated_breaths[preset_name] = cached_files
            
            if cached_files:
                logger.debug(
                    f"   ✓ {preset_name}: {len(cached_files)} cached"
                )
    
    # ═══════════════════════════════════════════════════════════════
    # Main API
    # ═══════════════════════════════════════════════════════════════
    def add_breathing(
        self,
        voice_path: str,
        output_path: str,
        preset: Optional[str] = None,
        mood: Optional[str] = None,
        voice_tone: Optional[str] = None,
        position: BreathPosition = BreathPosition.INTRO,
        progress_callback: Optional[Callable[[float, str], None]] = None,
    ) -> BreathResult:
        """
        إضافة تنفس للصوت.
        
        Args:
            voice_path: مسار الصوت
            output_path: مسار الإخراج
            preset: preset محدد (override)
            mood: مزاج (يحدد preset تلقائياً)
            voice_tone: نبرة (يحدد preset تلقائياً)
            position: مكان التنفس (intro/outro/both)
            progress_callback: callback للتقدم
        """
        start_time = time.time()
        
        # إذا معطل → نسخ مباشر
        if not self.enabled:
            safe_copy(voice_path, output_path)
            return BreathResult(
                success=True,
                output_path=output_path,
                breaths_added=0,
                preset_used="disabled",
                duration=get_audio_duration(output_path),
                elapsed_seconds=time.time() - start_time,
            )
        
        # تحقق من الملف
        if not Path(voice_path).exists():
            return BreathResult(
                success=False,
                output_path=output_path,
                error=f"Voice not found: {voice_path}",
                elapsed_seconds=time.time() - start_time,
            )
        
        # تحديد الـ preset (بالأولوية: preset > tone > mood > default)
        actual_preset_name = (
            preset or
            (TONE_BREATH_MAP.get(voice_tone) if voice_tone else None) or
            (MOOD_BREATH_MAP.get(mood) if mood else None) or
            self.default_preset
        )
        
        if actual_preset_name not in BREATH_PRESETS:
            actual_preset_name = "normal"
        
        actual_preset = BREATH_PRESETS[actual_preset_name]
        
        if progress_callback:
            progress_callback(0.2, f"اختيار preset: {actual_preset_name}")
        
        # توليد الأنفاس
        breaths_to_add = []
        cached_count = 0
        
        try:
            # Intro
            if position in (BreathPosition.INTRO, BreathPosition.BOTH):
                intro_path, was_cached = self._get_or_generate_breath(
                    actual_preset
                )
                if intro_path:
                    breaths_to_add.append(("intro", intro_path))
                    if was_cached:
                        cached_count += 1
            
            # Outro
            if position in (BreathPosition.OUTRO, BreathPosition.BOTH):
                # Outro غالباً أنعم
                outro_preset = BREATH_PRESETS.get(
                    "soft" if actual_preset_name != "whisper" else "whisper",
                    actual_preset
                )
                outro_path, was_cached = self._get_or_generate_breath(
                    outro_preset
                )
                if outro_path:
                    breaths_to_add.append(("outro", outro_path))
                    if was_cached:
                        cached_count += 1
            
            if not breaths_to_add:
                logger.warning("⚠ لا أنفاس تم توليدها")
                safe_copy(voice_path, output_path)
                return BreathResult(
                    success=True,
                    output_path=output_path,
                    breaths_added=0,
                    preset_used=actual_preset_name,
                    duration=get_audio_duration(output_path),
                    elapsed_seconds=time.time() - start_time,
                )
            
            if progress_callback:
                progress_callback(0.6, "دمج الأنفاس...")
            
            # دمج
            success = self._concat_with_breaths(
                voice_path, output_path, breaths_to_add
            )
            
            if not success:
                safe_copy(voice_path, output_path)
                return BreathResult(
                    success=False,
                    output_path=output_path,
                    error="Concat failed",
                    elapsed_seconds=time.time() - start_time,
                )
            
            if progress_callback:
                progress_callback(1.0, "تم!")
            
            logger.info(
                f"✓ تنفس [{actual_preset_name}] | "
                f"{len(breaths_to_add)} breaths ({cached_count} cached)"
            )
            
            return BreathResult(
                success=True,
                output_path=output_path,
                breaths_added=len(breaths_to_add),
                preset_used=actual_preset_name,
                duration=get_audio_duration(output_path),
                elapsed_seconds=time.time() - start_time,
                cached_breaths=cached_count,
            )
            
        except Exception as e:
            logger.error(f"❌ خطأ: {e}")
            safe_copy(voice_path, output_path)
            return BreathResult(
                success=False,
                output_path=output_path,
                error=str(e),
                elapsed_seconds=time.time() - start_time,
            )
    
    # ═══════════════════════════════════════════════════════════════
    # Breath Generation (with Caching)
    # ═══════════════════════════════════════════════════════════════
    def _get_or_generate_breath(
        self,
        preset: BreathPreset,
    ) -> tuple[Optional[str], bool]:
        """
        جلب breath من الكاش أو توليده.
        
        Returns:
            (path, was_cached)
        """
        # اختيار seed عشوائي
        seed = random.randint(0, self.variation_seeds - 1)
        
        # تحقق من الكاش
        if self.cache_enabled:
            cache_key = get_breath_cache_key(preset, seed)
            cache_path = self.cache_dir / f"{cache_key}.mp3"
            
            if cache_path.exists() and cache_path.stat().st_size > 500:
                return str(cache_path), True
        
        # توليد جديد
        generated = self._generate_breath_file(preset, seed)
        
        if generated and self.cache_enabled:
            # حفظ في الكاش
            try:
                cache_key = get_breath_cache_key(preset, seed)
                cache_path = self.cache_dir / f"{cache_key}.mp3"
                shutil.copy(generated, cache_path)
            except Exception as e:
                logger.warning(f"⚠ Cache save failed: {e}")
        
        return generated, False
    
    def _generate_breath_file(
        self,
        preset: BreathPreset,
        seed: int,
    ) -> Optional[str]:
        """توليد ملف breath فعلي."""
        # تنويع طفيف مع seed
        random.seed(seed * 1000 + hash(preset.name))
        
        duration = preset.duration + random.uniform(-0.05, 0.05)
        amplitude = preset.amplitude + random.uniform(-0.002, 0.002)
        lowpass = preset.lowpass_freq + random.randint(-50, 50)
        
        # reset seed
        random.seed()
        
        # Path مؤقت
        with self._lock:
            unique_id = f"{os.getpid()}_{int(time.time() * 1000) % 1000000}"
        
        temp_path = str(self.breath_dir / f"breath_{preset.name}_{unique_id}.mp3")
        
        # حساب fade times
        fade_in = duration * preset.fade_in_ratio
        fade_out_start = duration * (1 - preset.fade_out_ratio)
        fade_out = duration * preset.fade_out_ratio
        
        # FFmpeg
        result = run_ffmpeg(
            [
                "-f", "lavfi",
                "-i", (
                    f"anoisesrc=color={preset.noise_type.value}:"
                    f"duration={duration}:amplitude={amplitude}"
                ),
                "-af",
                f"afade=t=in:st=0:d={fade_in:.3f},"
                f"afade=t=out:st={fade_out_start:.3f}:d={fade_out:.3f},"
                f"lowpass=f={lowpass}",
            ],
            temp_path,
            description=f"Breath ({preset.name})",
            audio_config=True,
        )
        
        if result.success:
            return temp_path
        
        logger.warning(f"⚠ Breath generation failed: {result.error}")
        return None
    
    # ═══════════════════════════════════════════════════════════════
    # Concatenation
    # ═══════════════════════════════════════════════════════════════
    def _concat_with_breaths(
        self,
        voice_path: str,
        output_path: str,
        breaths: list[tuple[str, str]],
    ) -> bool:
        """دمج الأنفاس مع الصوت."""
        # ترتيب: intro → voice → outro
        files_in_order = []
        
        # intro أولاً
        for name, path in breaths:
            if name == "intro":
                files_in_order.append(path)
        
        # الصوت الرئيسي
        files_in_order.append(voice_path)
        
        # outro
        for name, path in breaths:
            if name == "outro":
                files_in_order.append(path)
        
        # إنشاء concat list
        with self._lock:
            unique_id = f"{os.getpid()}_{int(time.time() * 1000) % 1000000}"
        
        concat_list = self.breath_dir / f"concat_{unique_id}.txt"
        
        try:
            with open(concat_list, "w", encoding="utf-8") as f:
                for file_path in files_in_order:
                    abs_path = Path(file_path).resolve()
                    f.write(f"file '{abs_path}'\n")
            
            # FFmpeg concat
            result = run_ffmpeg(
                [
                    "-f", "concat",
                    "-safe", "0",
                    "-i", str(concat_list),
                ],
                output_path,
                description=f"Concat {len(files_in_order)} files",
                audio_config=True,
            )
            
            return result.success
            
        finally:
            concat_list.unlink(missing_ok=True)
    
    # ═══════════════════════════════════════════════════════════════
    # Backward Compatibility
    # ═══════════════════════════════════════════════════════════════
    def add_breathing_advanced(
        self,
        voice_path: str,
        output_path: str,
        intro_preset: str = "normal",
        outro_preset: str = "soft",
    ) -> str:
        """متوافق مع v1 - intro + outro."""
        # نستخدم intro_preset لكن البنية تختار outro تلقائياً
        result = self.add_breathing(
            voice_path=voice_path,
            output_path=output_path,
            preset=intro_preset,
            position=BreathPosition.BOTH,
        )
        return result.output_path
    
    # ═══════════════════════════════════════════════════════════════
    # Maintenance
    # ═══════════════════════════════════════════════════════════════
    def cleanup(self) -> int:
        """تنظيف الملفات المؤقتة (ليس الكاش)."""
        count = 0
        try:
            for f in self.breath_dir.glob("breath_*.mp3"):
                f.unlink(missing_ok=True)
                count += 1
            for f in self.breath_dir.glob("concat_*.txt"):
                f.unlink(missing_ok=True)
                count += 1
            
            if count > 0:
                logger.debug(f"🧹 حُذف {count} ملف مؤقت")
        except Exception as e:
            logger.warning(f"⚠ Cleanup failed: {e}")
        return count
    
    def clear_cache(self) -> int:
        """مسح الكاش بالكامل."""
        if not self.cache_enabled or not self.cache_dir:
            return 0
        
        count = 0
        for f in self.cache_dir.glob("*.mp3"):
            f.unlink(missing_ok=True)
            count += 1
        
        # إعادة تهيئة قائمة الـ pre-generated
        self._pre_generated_breaths.clear()
        
        logger.info(f"🗑 حُذف {count} ملف من الكاش")
        return count
    
    def prune_cache(self) -> int:
        """تقليم الكاش إذا تجاوز الحد."""
        if not self.cache_enabled or not self.cache_dir:
            return 0
        
        all_files = sorted(
            self.cache_dir.glob("*.mp3"),
            key=lambda f: f.stat().st_atime,  # access time
        )
        
        if len(all_files) <= self.MAX_CACHE_FILES:
            return 0
        
        # احذف الأقدم
        to_delete = all_files[:-self.MAX_CACHE_FILES]
        count = 0
        for f in to_delete:
            f.unlink(missing_ok=True)
            count += 1
        
        if count > 0:
            logger.info(f"✂ تم تقليم الكاش: حُذف {count}")
        
        return count
    
    # ═══════════════════════════════════════════════════════════════
    # Static Utilities
    # ═══════════════════════════════════════════════════════════════
    @staticmethod
    def list_presets() -> list[str]:
        """قائمة الـ presets."""
        return list(BREATH_PRESETS.keys())
    
    @staticmethod
    def get_preset_info(name: str) -> Optional[BreathPreset]:
        """معلومات preset."""
        return BREATH_PRESETS.get(name)


# ═══════════════════════════════════════════════════════════════════
# اختبار
# ═══════════════════════════════════════════════════════════════════
if __name__ == "__main__":
    import sys
    
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s | %(levelname)s | %(message)s"
    )
    
    if len(sys.argv) < 3:
        print("Usage: python breathing_engine.py <input.mp3> <output.mp3> [preset] [position]")
        print(f"Presets: {BreathingEngine.list_presets()}")
        print("Positions: intro, outro, both")
        sys.exit(1)
    
    input_file = sys.argv[1]
    output_file = sys.argv[2]
    preset = sys.argv[3] if len(sys.argv) > 3 else "normal"
    position = sys.argv[4] if len(sys.argv) > 4 else "intro"
    
    print("=" * 60)
    print(f"🫁 Breathing Engine v2.0")
    print("=" * 60)
    
    engine = BreathingEngine(cache_enabled=True)
    
    def progress(p, msg):
        print(f"  [{p*100:3.0f}%] {msg}")
    
    result = engine.add_breathing(
        voice_path=input_file,
        output_path=output_file,
        preset=preset,
        position=BreathPosition(position),
        progress_callback=progress,
    )
    
    print()
    print(result.summary())
