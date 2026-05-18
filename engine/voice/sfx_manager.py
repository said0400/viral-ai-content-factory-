"""
🔊 SFX Manager v3.0 — Pro
═══════════════════════════════════════════════════════════════
مدير المؤثرات الصوتية الذكي:
  ✓ Scene-aware (type, energy, transition)
  ✓ Smart selection (no repeats)
  ✓ Priority-based (احتفظ بالـ SFX للمشاهد المهمة)
  ✓ Metadata caching
  ✓ يُرجع SFXTrack من audio_fx
  ✓ Result dataclass

التحسينات v3.0:
  ✓ يستخدم SFXTrack من audio_fx
  ✓ Smart priority selection
  ✓ Energy & transition aware
  ✓ History tracking
  ✓ Metadata caching
═══════════════════════════════════════════════════════════════
"""

from __future__ import annotations

import os
import json
import random
import hashlib
import logging
from pathlib import Path
from enum import Enum
from dataclasses import dataclass, field
from collections import deque
from threading import Lock
from typing import Optional

# استيراد SFXTrack من audio_fx (نفس الـ dataclass!)
from engine.video.voice.audio_fx import SFXTrack
from engine.video.voice.ffmpeg_utils import get_audio_duration

logger = logging.getLogger(__name__)


# ═══════════════════════════════════════════════════════════════════
# Enums
# ═══════════════════════════════════════════════════════════════════
class SFXIntensity(str, Enum):
    """شدة المؤثر."""
    SUBTLE = "subtle"      # خفيف
    NORMAL = "normal"      # عادي
    STRONG = "strong"      # قوي
    EPIC = "epic"          # ملحمي


class SceneType(str, Enum):
    """أنواع المشاهد."""
    HOOK = "hook"
    INTRO = "intro"
    BUILD = "build"
    MAIN = "main"
    PEAK = "peak"
    RESOLUTION = "resolution"
    OUTRO = "outro"
    CTA = "cta"


# ═══════════════════════════════════════════════════════════════════
# Dataclasses
# ═══════════════════════════════════════════════════════════════════
@dataclass
class SFXFile:
    """ملف مؤثر صوتي."""
    path: str
    name: str
    sfx_type: str
    duration: float = 0.0
    file_size: int = 0
    
    @property
    def filename(self) -> str:
        return Path(self.path).name


@dataclass
class SFXScenePlan:
    """خطة SFX لمشهد."""
    scene_id: int
    scene_type: str
    sfx_track: Optional[SFXTrack] = None
    reason: str = ""
    priority_score: float = 0.0


@dataclass
class SFXResult:
    """نتيجة توليد SFX."""
    success: bool
    tracks: list[SFXTrack] = field(default_factory=list)
    plans: list[SFXScenePlan] = field(default_factory=list)
    total_scenes: int = 0
    sfx_added: int = 0
    error: Optional[str] = None
    
    @property
    def coverage_percent(self) -> float:
        if self.total_scenes == 0:
            return 0.0
        return (self.sfx_added / self.total_scenes) * 100
    
    def summary(self) -> str:
        if not self.success:
            return f"❌ {self.error}"
        
        return (
            f"📊 SFX Result:\n"
            f"   • Scenes: {self.total_scenes}\n"
            f"   • SFX added: {self.sfx_added} "
            f"({self.coverage_percent:.0f}% coverage)\n"
            f"   • Tracks: {len(self.tracks)}"
        )


# ═══════════════════════════════════════════════════════════════════
# Configuration
# ═══════════════════════════════════════════════════════════════════
# Scene type → SFX types (مع priority)
SCENE_SFX_MAP: dict[str, list[str]] = {
    "hook":       ["impact", "whoosh", "drum"],
    "intro":      ["impact", "drum", "swoosh"],
    "build":      ["whoosh", "swoosh", "click"],
    "main":       ["whoosh", "click"],
    "peak":       ["impact", "drum", "glitch"],
    "resolution": ["bell", "sparkle"],
    "cta":        ["click", "bell"],
    "outro":      ["bell", "sparkle"],
}

# Scene type → volume
SCENE_VOLUME_MAP: dict[str, float] = {
    "hook":       0.45,
    "intro":      0.45,
    "build":      0.30,
    "main":       0.25,
    "peak":       0.50,
    "resolution": 0.25,
    "cta":        0.35,
    "outro":      0.25,
}

# Scene type → priority (للاختيار عند نفاد الـ slots)
SCENE_PRIORITY_MAP: dict[str, float] = {
    "hook":       10.0,   # أعلى أولوية
    "peak":       9.0,
    "outro":      8.0,
    "cta":        7.0,
    "intro":      6.0,
    "resolution": 5.0,
    "build":      3.0,
    "main":       1.0,
}

# Transition → SFX type
TRANSITION_SFX_MAP: dict[str, str] = {
    "cinematic_flash":  "impact",
    "smooth_fade":      "swoosh",
    "cross_dissolve":   "whoosh",
    "glitch":           "glitch",
    "zoom_in":          "whoosh",
    "fast_cut":         "click",
}

# Voice tone → intensity preference
TONE_INTENSITY_MAP: dict[str, SFXIntensity] = {
    "whisper":       SFXIntensity.SUBTLE,
    "calm":          SFXIntensity.SUBTLE,
    "cold":          SFXIntensity.NORMAL,
    "intense":       SFXIntensity.STRONG,
    "aggressive":    SFXIntensity.EPIC,
    "powerful":      SFXIntensity.STRONG,
    "authoritative": SFXIntensity.NORMAL,
    "curious":       SFXIntensity.SUBTLE,
}


# ═══════════════════════════════════════════════════════════════════
# Constants
# ═══════════════════════════════════════════════════════════════════
class SFXConstants:
    """ثوابت."""
    
    # Audio extensions (case-insensitive عبر glob)
    AUDIO_EXTENSIONS = ("mp3", "wav", "m4a", "ogg", "aac", "flac")
    
    # Timing
    DEFAULT_OFFSET = -0.2  # قبل المشهد بـ 0.2s
    HOOK_OFFSET = -0.3     # الـ hook يحتاج أبكر
    
    # History
    HISTORY_SIZE = 10
    
    # Limits
    DEFAULT_MAX_SFX = 5
    MIN_SCENE_DURATION_FOR_SFX = 1.5
    
    # Cache
    METADATA_CACHE_VERSION = "v1"


# ═══════════════════════════════════════════════════════════════════
# Helpers
# ═══════════════════════════════════════════════════════════════════
def get_file_signature(path: Path) -> str:
    """signature للملف."""
    try:
        stat = path.stat()
        content = f"{path.name}|{stat.st_size}|{stat.st_mtime}"
        return hashlib.md5(content.encode()).hexdigest()[:12]
    except Exception:
        return ""


def get_audio_files(directory: Path) -> list[Path]:
    """جلب ملفات صوتية (case-insensitive)."""
    files = set()
    for ext in SFXConstants.AUDIO_EXTENSIONS:
        # case-insensitive: lowercase + uppercase
        files.update(directory.glob(f"*.{ext}"))
        files.update(directory.glob(f"*.{ext.upper()}"))
    return sorted(files)


# ═══════════════════════════════════════════════════════════════════
# Main Class
# ═══════════════════════════════════════════════════════════════════
class SFXManager:
    """مدير المؤثرات الصوتية v3.0."""
    
    def __init__(
        self,
        sfx_dir: Optional[str] = None,
        enabled: Optional[bool] = None,
        max_sfx_per_video: Optional[int] = None,
        default_volume: float = 0.35,
        load_metadata: bool = True,
        cache_enabled: bool = True,
    ):
        """
        Args:
            sfx_dir: مجلد SFX
            enabled: تفعيل
            max_sfx_per_video: الحد الأقصى
            default_volume: حجم افتراضي
            load_metadata: تحميل metadata
            cache_enabled: caching للـ metadata
        """
        # Settings
        self.sfx_dir = Path(
            sfx_dir or os.getenv("SFX_DIR", "engine/assets/sfx")
        )
        
        if enabled is None:
            enabled = os.getenv("ENABLE_SFX", "true").lower() == "true"
        self.enabled = enabled
        
        self.max_sfx = int(
            max_sfx_per_video or os.getenv("MAX_SFX_PER_VIDEO", "5")
        )
        self.default_volume = float(
            os.getenv("SFX_VOLUME", default_volume)
        )
        
        # Cache
        self.cache_enabled = cache_enabled
        if cache_enabled:
            self.cache_dir = Path(
                os.getenv("TEMP_DIR", "./temp")
            ) / "sfx_metadata_cache"
            self.cache_dir.mkdir(parents=True, exist_ok=True)
            self.cache_file = self.cache_dir / "sfx_library.json"
        else:
            self.cache_dir = None
            self.cache_file = None
        
        # History (لتجنب التكرار)
        self.history: deque[str] = deque(maxlen=SFXConstants.HISTORY_SIZE)
        
        # Thread safety
        self._lock = Lock()
        
        # Library
        self.library: dict[str, list[SFXFile]] = {}
        self._scan_library(load_metadata=load_metadata)
        
        # Stats
        total = sum(len(files) for files in self.library.values())
        
        logger.info(
            f"🔊 SFXManager v3.0 | "
            f"Enabled: {self.enabled} | Max: {self.max_sfx}"
        )
        logger.info(f"   📂 {self.sfx_dir}")
        logger.info(f"   📚 {total} ملف")
        
        if self.library:
            for sfx_type, files in sorted(self.library.items()):
                logger.info(f"      • {sfx_type}: {len(files)} ملف")
    
    # ═══════════════════════════════════════════════════════════════
    # Library Scanning
    # ═══════════════════════════════════════════════════════════════
    def _scan_library(self, load_metadata: bool = True) -> None:
        """مسح المكتبة."""
        if not self.sfx_dir.exists():
            self.sfx_dir.mkdir(parents=True, exist_ok=True)
            return
        
        # Cache
        cached = self._load_metadata_cache() if load_metadata else {}
        
        for sfx_subdir in self.sfx_dir.iterdir():
            if not sfx_subdir.is_dir():
                continue
            
            sfx_type = sfx_subdir.name.lower()
            files = []
            
            for file_path in get_audio_files(sfx_subdir):
                sfx_file = self._build_sfx_file(
                    file_path, sfx_type, cached, load_metadata
                )
                if sfx_file:
                    files.append(sfx_file)
            
            if files:
                self.library[sfx_type] = files
        
        # حفظ cache
        if load_metadata:
            self._save_metadata_cache()
    
    def _build_sfx_file(
        self,
        path: Path,
        sfx_type: str,
        cached: dict,
        load_metadata: bool,
    ) -> Optional[SFXFile]:
        """بناء SFXFile."""
        try:
            signature = get_file_signature(path)
            cache_key = f"{path.name}_{signature}"
            
            if cache_key in cached:
                meta = cached[cache_key]
                return SFXFile(
                    path=str(path),
                    name=path.stem,
                    sfx_type=sfx_type,
                    duration=meta.get("duration", 0),
                    file_size=meta.get("file_size", 0),
                )
            
            duration = 0.0
            if load_metadata:
                duration = get_audio_duration(str(path))
            
            sfx_file = SFXFile(
                path=str(path),
                name=path.stem,
                sfx_type=sfx_type,
                duration=duration,
                file_size=path.stat().st_size,
            )
            
            cached[cache_key] = {
                "duration": sfx_file.duration,
                "file_size": sfx_file.file_size,
            }
            
            return sfx_file
            
        except Exception as e:
            logger.warning(f"⚠ {path.name}: {e}")
            return None
    
    # ═══════════════════════════════════════════════════════════════
    # Metadata Cache
    # ═══════════════════════════════════════════════════════════════
    def _load_metadata_cache(self) -> dict:
        """تحميل cache."""
        if not self.cache_file or not self.cache_file.exists():
            return {}
        
        try:
            with open(self.cache_file, "r", encoding="utf-8") as f:
                data = json.load(f)
            
            if data.get("version") != SFXConstants.METADATA_CACHE_VERSION:
                return {}
            
            return data.get("files", {})
        except Exception:
            return {}
    
    def _save_metadata_cache(self) -> None:
        """حفظ cache."""
        if not self.cache_file:
            return
        
        try:
            all_files = {}
            for files in self.library.values():
                for f in files:
                    sig = get_file_signature(Path(f.path))
                    key = f"{Path(f.path).name}_{sig}"
                    all_files[key] = {
                        "duration": f.duration,
                        "file_size": f.file_size,
                    }
            
            with open(self.cache_file, "w", encoding="utf-8") as f:
                json.dump({
                    "version": SFXConstants.METADATA_CACHE_VERSION,
                    "files": all_files,
                }, f, indent=2, ensure_ascii=False)
        except Exception as e:
            logger.warning(f"⚠ Cache save: {e}")
    
    # ═══════════════════════════════════════════════════════════════
    # Main API
    # ═══════════════════════════════════════════════════════════════
    def get_sfx_for_scenes(
        self,
        scenes: list[dict],
        max_sfx: Optional[int] = None,
    ) -> SFXResult:
        """
        🎯 توليد SFX لجميع المشاهد بذكاء.
        
        خوارزمية:
        1. حساب priority لكل scene
        2. ترتيب حسب priority
        3. اختيار أفضل N scenes
        4. توليد SFX لها
        """
        result = SFXResult(
            success=True,
            total_scenes=len(scenes),
        )
        
        if not self.enabled:
            logger.info("⏭ SFX معطّلة")
            return result
        
        if not scenes:
            return result
        
        if not self.library:
            result.success = False
            result.error = "No SFX library found"
            logger.warning("⚠ لا توجد SFX!")
            return result
        
        max_to_add = max_sfx if max_sfx is not None else self.max_sfx
        
        logger.info(f"🔊 توليد SFX لـ {len(scenes)} مشهد (max: {max_to_add})")
        
        # 1. حساب priority + بناء plans
        all_plans = self._build_scene_plans(scenes)
        
        # 2. ترتيب حسب priority
        all_plans.sort(key=lambda p: p.priority_score, reverse=True)
        
        # 3. اختيار أفضل max_to_add
        selected_plans = all_plans[:max_to_add]
        
        # 4. توليد SFX
        cumulative_times = self._calculate_cumulative_times(scenes)
        
        # ترتيب مرة أخرى حسب scene_id (للترتيب الزمني)
        selected_plans.sort(key=lambda p: p.scene_id)
        
        for plan in selected_plans:
            scene = scenes[plan.scene_id]
            scene_start = cumulative_times[plan.scene_id]
            
            sfx_file = self._select_sfx_for_plan(plan, scene)
            
            if sfx_file:
                # تحديد التوقيت
                offset = (
                    SFXConstants.HOOK_OFFSET
                    if plan.scene_type == "hook"
                    else SFXConstants.DEFAULT_OFFSET
                )
                start_time = max(scene_start + offset, 0)
                
                # تحديد الحجم
                volume = self._calculate_volume(scene, plan.scene_type)
                
                # بناء SFXTrack
                track = SFXTrack(
                    path=sfx_file.path,
                    start_time=start_time,
                    volume=volume,
                )
                
                plan.sfx_track = track
                result.tracks.append(track)
                result.sfx_added += 1
                
                self._add_to_history(sfx_file.path)
                
                logger.info(
                    f"   ✓ Scene {plan.scene_id} ({plan.scene_type}, "
                    f"priority={plan.priority_score:.1f}): "
                    f"{sfx_file.filename} @ {start_time:.1f}s "
                    f"(vol={volume:.2f})"
                )
        
        result.plans = all_plans
        
        logger.info(
            f"✓ {result.sfx_added}/{result.total_scenes} scenes "
            f"({result.coverage_percent:.0f}% coverage)"
        )
        return result
    
    # ═══════════════════════════════════════════════════════════════
    # Scene Planning
    # ═══════════════════════════════════════════════════════════════
    def _build_scene_plans(self, scenes: list[dict]) -> list[SFXScenePlan]:
        """بناء plans لكل scene."""
        plans = []
        
        for i, scene in enumerate(scenes):
            scene_type = scene.get("type", "main")
            duration = float(scene.get("duration", 3.0))
            energy = float(scene.get("energy", 0.5))
            
            # تخطي المشاهد القصيرة جداً
            if duration < SFXConstants.MIN_SCENE_DURATION_FOR_SFX:
                continue
            
            # حساب priority
            base_priority = SCENE_PRIORITY_MAP.get(scene_type, 1.0)
            energy_bonus = energy * 2.0  # طاقة عالية = أولوية
            priority = base_priority + energy_bonus
            
            plans.append(SFXScenePlan(
                scene_id=i,
                scene_type=scene_type,
                priority_score=priority,
            ))
        
        return plans
    
    def _calculate_cumulative_times(self, scenes: list[dict]) -> list[float]:
        """حساب وقت بداية كل مشهد."""
        times = []
        cumulative = 0.0
        
        for scene in scenes:
            times.append(cumulative)
            duration = float(scene.get("duration", 3.0))
            pause = float(scene.get("pause_after", 0.3))
            cumulative += duration + pause
        
        return times
    
    # ═══════════════════════════════════════════════════════════════
    # SFX Selection (Smart)
    # ═══════════════════════════════════════════════════════════════
    def _select_sfx_for_plan(
        self,
        plan: SFXScenePlan,
        scene: dict,
    ) -> Optional[SFXFile]:
        """اختيار SFX ذكي للـ plan."""
        # 1. تحقق من transition
        transition = scene.get("transition", "")
        if transition in TRANSITION_SFX_MAP:
            sfx_type = TRANSITION_SFX_MAP[transition]
            sfx = self._get_sfx_from_type(sfx_type, avoid_recent=True)
            if sfx:
                plan.reason = f"transition_{transition}"
                return sfx
        
        # 2. SFX المناسبة للـ scene type
        candidate_types = SCENE_SFX_MAP.get(plan.scene_type, ["whoosh"])
        
        for sfx_type in candidate_types:
            sfx = self._get_sfx_from_type(sfx_type, avoid_recent=True)
            if sfx:
                plan.reason = f"scene_type_{plan.scene_type}"
                return sfx
        
        # 3. أي SFX متاح
        for sfx_type, files in self.library.items():
            non_recent = [
                f for f in files if f.path not in self.history
            ]
            if non_recent:
                plan.reason = "fallback_any"
                return random.choice(non_recent)
            if files:
                plan.reason = "fallback_recent"
                return random.choice(files)
        
        return None
    
    def _get_sfx_from_type(
        self,
        sfx_type: str,
        avoid_recent: bool = True,
    ) -> Optional[SFXFile]:
        """جلب SFX من type معين."""
        if sfx_type not in self.library:
            return None
        
        files = self.library[sfx_type]
        if not files:
            return None
        
        if avoid_recent:
            available = [f for f in files if f.path not in self.history]
            if available:
                return random.choice(available)
        
        return random.choice(files)
    
    # ═══════════════════════════════════════════════════════════════
    # Volume Calculation
    # ═══════════════════════════════════════════════════════════════
    def _calculate_volume(
        self,
        scene: dict,
        scene_type: str,
    ) -> float:
        """حساب الحجم الذكي."""
        # base من scene_type
        base_volume = SCENE_VOLUME_MAP.get(scene_type, self.default_volume)
        
        # تعديل حسب energy
        energy = float(scene.get("energy", 0.5))
        energy_multiplier = 0.7 + (energy * 0.6)  # 0.7-1.3
        
        # تعديل حسب voice_tone
        voice_tone = scene.get("voice_tone", "intense")
        intensity = TONE_INTENSITY_MAP.get(voice_tone, SFXIntensity.NORMAL)
        
        intensity_multipliers = {
            SFXIntensity.SUBTLE: 0.7,
            SFXIntensity.NORMAL: 1.0,
            SFXIntensity.STRONG: 1.2,
            SFXIntensity.EPIC: 1.4,
        }
        intensity_mult = intensity_multipliers[intensity]
        
        # حساب النهائي
        final_volume = base_volume * energy_multiplier * intensity_mult
        
        # حدود
        return max(0.1, min(0.8, final_volume))
    
    # ═══════════════════════════════════════════════════════════════
    # History
    # ═══════════════════════════════════════════════════════════════
    def _add_to_history(self, path: str) -> None:
        with self._lock:
            self.history.append(path)
    
    def clear_history(self) -> None:
        with self._lock:
            self.history.clear()
    
    # ═══════════════════════════════════════════════════════════════
    # Utility (Backward Compatible)
    # ═══════════════════════════════════════════════════════════════
    def get_sfx_for_scenes_legacy(
        self,
        scenes: list[dict],
    ) -> list[tuple[str, float, float]]:
        """متوافق مع v2 - يُرجع tuples."""
        result = self.get_sfx_for_scenes(scenes)
        return [
            (t.path, t.start_time, t.volume)
            for t in result.tracks
        ]
    
    def list_sfx_types(self) -> list[str]:
        return list(self.library.keys())
    
    def get_sfx_files(self, sfx_type: str) -> list[SFXFile]:
        return self.library.get(sfx_type.lower(), [])
    
    def get_status(self) -> dict:
        total = sum(len(files) for files in self.library.values())
        return {
            "sfx_dir": str(self.sfx_dir),
            "enabled": self.enabled,
            "total_files": total,
            "max_sfx": self.max_sfx,
            "types": {
                t: {
                    "count": len(files),
                    "total_duration": round(
                        sum(f.duration for f in files), 1
                    ),
                }
                for t, files in self.library.items()
            },
            "history_size": len(self.history),
            "cache_enabled": self.cache_enabled,
        }
    
    def rescan_library(self, load_metadata: bool = True) -> int:
        """إعادة مسح."""
        self.library.clear()
        self._scan_library(load_metadata=load_metadata)
        return sum(len(files) for files in self.library.values())


# ═══════════════════════════════════════════════════════════════════
# اختبار
# ═══════════════════════════════════════════════════════════════════
if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s | %(levelname)s | %(message)s"
    )
    
    print("=" * 60)
    print("🔊 SFX Manager v3.0 Test")
    print("=" * 60)
    
    manager = SFXManager()
    
    print("\n📊 Status:")
    status = manager.get_status()
    print(f"   📂 Dir: {status['sfx_dir']}")
    print(f"   📦 Files: {status['total_files']}")
    print(f"   🎯 Max: {status['max_sfx']}")
    
    if status['types']:
        print("\n   Types:")
        for sfx_type, info in sorted(status['types'].items()):
            print(
                f"      • {sfx_type}: {info['count']} files "
                f"({info['total_duration']:.1f}s)"
            )
    
    # اختبار scenes
    test_scenes = [
        {
            "id": 0,
            "type": "hook",
            "duration": 3.0,
            "pause_after": 0.4,
            "energy": 0.95,
            "voice_tone": "intense",
            "transition": "cinematic_flash",
        },
        {
            "id": 1,
            "type": "build",
            "duration": 4.0,
            "pause_after": 0.3,
            "energy": 0.6,
            "voice_tone": "curious",
        },
        {
            "id": 2,
            "type": "peak",
            "duration": 3.5,
            "pause_after": 0.5,
            "energy": 0.9,
            "voice_tone": "powerful",
        },
        {
            "id": 3,
            "type": "main",
            "duration": 4.0,
            "pause_after": 0.3,
            "energy": 0.5,
            "voice_tone": "authoritative",
        },
        {
            "id": 4,
            "type": "cta",
            "duration": 3.0,
            "pause_after": 0.0,
            "energy": 0.7,
            "voice_tone": "powerful",
        },
    ]
    
    print("\n🎬 Testing with 5 scenes...")
    result = manager.get_sfx_for_scenes(test_scenes)
    
    print()
    print(result.summary())
    
    print("\n📋 Selected tracks:")
    for track in result.tracks:
        print(
            f"   • {Path(track.path).name} @ "
            f"{track.start_time:.1f}s (vol={track.volume:.2f})"
        )
