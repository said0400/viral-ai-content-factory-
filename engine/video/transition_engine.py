"""
🎞️ Transition Engine v2.0 — Pro
═══════════════════════════════════════════════════════════════
مولّد إعدادات الانتقالات لـ Remotion

التحسينات v2.0:
  ✓ Dataclasses للـ configs
  ✓ Energy-aware (يستخدم scene.energy)
  ✓ Smart selection (avoid recent)
  ✓ Result dataclass
  ✓ Validation
  ✓ Mood-based pools
═══════════════════════════════════════════════════════════════
"""

from __future__ import annotations

import os
import random
import logging
import warnings
from enum import Enum
from dataclasses import dataclass, field, asdict
from collections import deque
from typing import Optional

logger = logging.getLogger(__name__)


# ═══════════════════════════════════════════════════════════════════
# Enums
# ═══════════════════════════════════════════════════════════════════
class EnergyLevel(str, Enum):
    """مستويات الطاقة."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    
    @classmethod
    def from_value(cls, value: float) -> "EnergyLevel":
        if value < 0.4:
            return cls.LOW
        elif value < 0.7:
            return cls.MEDIUM
        return cls.HIGH


# ═══════════════════════════════════════════════════════════════════
# Dataclasses
# ═══════════════════════════════════════════════════════════════════
@dataclass
class TransitionConfig:
    """إعدادات انتقال."""
    name: str
    duration: float = 0.4
    easing: str = "ease-in-out"
    direction: Optional[str] = None  # left/right/up/down
    color: Optional[str] = None      # للـ fade-black/white
    scale_from: Optional[float] = None
    scale_to: Optional[float] = None
    shape: Optional[str] = None
    scale: Optional[float] = None
    axis: Optional[str] = None
    pixel_size: Optional[int] = None
    
    def to_dict(self) -> dict:
        result = {
            "name": self.name,
            "duration": round(self.duration, 3),
            "easing": self.easing,
        }
        
        # إضافة الخصائص الموجودة فقط
        optional_props = {
            "direction": self.direction,
            "color": self.color,
            "scaleFrom": self.scale_from,
            "scaleTo": self.scale_to,
            "shape": self.shape,
            "scale": self.scale,
            "axis": self.axis,
            "pixelSize": self.pixel_size,
        }
        
        for key, value in optional_props.items():
            if value is not None:
                result[key] = value
        
        return result


@dataclass
class SceneTransition:
    """انتقال بين مشهدين."""
    from_scene: int
    to_scene: int
    config: TransitionConfig
    
    def to_dict(self) -> dict:
        return {
            "fromScene": self.from_scene,
            "toScene": self.to_scene,
            **self.config.to_dict(),
        }


@dataclass
class TransitionsResult:
    """نتيجة بناء الانتقالات."""
    success: bool
    transitions: list[SceneTransition] = field(default_factory=list)
    total_count: int = 0
    types_used: dict[str, int] = field(default_factory=dict)
    error: Optional[str] = None
    
    def to_dict(self) -> dict:
        return {
            "transitions": [t.to_dict() for t in self.transitions],
            "totalCount": self.total_count,
            "typesUsed": self.types_used,
        }
    
    def summary(self) -> str:
        types_str = ", ".join(
            f"{name}: {count}"
            for name, count in self.types_used.items()
        )
        return (
            f"📊 Transitions Result:\n"
            f"   • Status: {'✅' if self.success else '❌'}\n"
            f"   • Count: {self.total_count}\n"
            f"   • Types: {types_str}"
        )


# ═══════════════════════════════════════════════════════════════════
# Transitions Catalog
# ═══════════════════════════════════════════════════════════════════
# Energy pools (tuples = immutable)
ENERGY_HIGH: tuple[str, ...] = (
    "fade-black",       # تلاشي للأسود
    "fade-white",       # تلاشي للأبيض
    "iris-burst",       # قزحية متفجرة
    "wipe-left",
    "wipe-right",
    "flip-horizontal",  # قلب أفقي
    "zoom-in",          # تكبير
    "pixelate",
)

ENERGY_MEDIUM: tuple[str, ...] = (
    "fade",
    "slide-up",
    "slide-down",
    "slide-left",
    "slide-right",
    "wipe-up",
    "wipe-down",
)

ENERGY_LOW: tuple[str, ...] = (
    "fade",
    "smooth-fade",
    "dissolve",
    "iris-open",
    "iris-close",
    "clock-wipe",
)

# All transitions (مع الترتيب)
ALL_TRANSITIONS: tuple[str, ...] = tuple(
    dict.fromkeys(ENERGY_HIGH + ENERGY_MEDIUM + ENERGY_LOW)
)


# ═══════════════════════════════════════════════════════════════════
# Aliases Mapping (custom names → Remotion names)
# ═══════════════════════════════════════════════════════════════════
TRANSITION_ALIASES: dict[str, Optional[str]] = {
    "auto": None,
    "none": "none",
    
    # تلاشي
    "fade": "fade",
    "fade_black": "fade-black",
    "fade_white": "fade-white",
    "flash_black": "fade-black",
    "flash_white": "fade-white",
    "cross_dissolve": "fade",
    "smooth_fade": "smooth-fade",
    "dissolve": "dissolve",
    
    # انزلاق
    "push_up": "slide-up",
    "push_down": "slide-down",
    "slide_left": "slide-left",
    "slide_right": "slide-right",
    "smooth_left": "slide-left",
    "smooth_right": "slide-right",
    "smooth_up": "slide-up",
    "smooth_down": "slide-down",
    
    # مسح
    "wipe_left": "wipe-left",
    "wipe_right": "wipe-right",
    "wipe_up": "wipe-up",
    "wipe_down": "wipe-down",
    "whip_right": "wipe-left",
    "whip_left": "wipe-right",
    
    # تكبير
    "zoom_burst": "zoom-in",
    "zoom_in": "zoom-in",
    "zoom_out": "zoom-out",
    
    # قزحية
    "circle_open": "iris-open",
    "circle_close": "iris-close",
    "circle_crop": "iris-burst",
    "iris": "iris-open",
    
    # خاصة
    "glitch": "pixelate",
    "pixel": "pixelate",
    "pixelize": "pixelate",
    "flip": "flip-horizontal",
    "flip_h": "flip-horizontal",
    "flip_v": "flip-vertical",
    "clock": "clock-wipe",
    "cinematic_flash": "fade-white",
    
    # قص
    "rect_crop": "iris-burst",
    "diag_bl": "wipe-left",
    "diag_br": "wipe-right",
    "diag_tl": "wipe-up",
    "diag_tr": "wipe-down",
}


# ═══════════════════════════════════════════════════════════════════
# Easing Presets
# ═══════════════════════════════════════════════════════════════════
EASING_PRESETS: dict[str, str] = {
    "fade": "ease-in-out",
    "fade-black": "ease-in",
    "fade-white": "ease-in",
    "smooth-fade": "ease-in-out",
    "dissolve": "linear",
    "slide-up": "ease-out",
    "slide-down": "ease-out",
    "slide-left": "ease-out",
    "slide-right": "ease-out",
    "wipe-left": "ease-in-out",
    "wipe-right": "ease-in-out",
    "wipe-up": "ease-in-out",
    "wipe-down": "ease-in-out",
    "zoom-in": "ease-in",
    "zoom-out": "ease-out",
    "iris-open": "ease-out",
    "iris-close": "ease-in",
    "iris-burst": "ease-in",
    "flip-horizontal": "ease-in-out",
    "flip-vertical": "ease-in-out",
    "clock-wipe": "linear",
    "pixelate": "ease-in-out",
    "none": "linear",
}


# ═══════════════════════════════════════════════════════════════════
# Duration Presets
# ═══════════════════════════════════════════════════════════════════
DURATION_PRESETS: dict[str, float] = {
    # سريعة
    "fade-black": 0.2,
    "fade-white": 0.2,
    "zoom-in": 0.25,
    "iris-burst": 0.25,
    "pixelate": 0.3,
    
    # متوسطة
    "fade": 0.4,
    "smooth-fade": 0.5,
    "slide-up": 0.4,
    "slide-down": 0.4,
    "slide-left": 0.4,
    "slide-right": 0.4,
    "wipe-left": 0.4,
    "wipe-right": 0.4,
    "wipe-up": 0.4,
    "wipe-down": 0.4,
    
    # بطيئة
    "dissolve": 0.6,
    "iris-open": 0.6,
    "iris-close": 0.6,
    "clock-wipe": 0.7,
    "flip-horizontal": 0.5,
    "flip-vertical": 0.5,
    
    "default": 0.4,
    "none": 0.0,
}


# ═══════════════════════════════════════════════════════════════════
# Scene Type → Energy Pool
# ═══════════════════════════════════════════════════════════════════
SCENE_TYPE_POOLS: dict[str, tuple[str, ...]] = {
    "hook":       ENERGY_HIGH,
    "intro":      ENERGY_HIGH,
    "peak":       ENERGY_HIGH,
    "build":      ENERGY_MEDIUM,
    "main":       ENERGY_MEDIUM,
    "resolution": ENERGY_MEDIUM,
    "cta":        ENERGY_LOW,
    "outro":      ENERGY_LOW,
}


# ═══════════════════════════════════════════════════════════════════
# Mood → Preferred Transitions
# ═══════════════════════════════════════════════════════════════════
MOOD_TRANSITION_PREFERENCE: dict[str, tuple[str, ...]] = {
    "motivation":    ("zoom-in", "fade-white", "slide-up", "wipe-up"),
    "dark":          ("fade-black", "dissolve", "iris-close", "fade"),
    "sigma":         ("fade-black", "wipe-left", "iris-burst"),
    "psychological": ("dissolve", "fade", "iris-open"),
    "horror":        ("pixelate", "fade-black", "iris-close"),
    "emotional":     ("smooth-fade", "dissolve", "fade"),
    "sad":           ("smooth-fade", "dissolve", "iris-close"),
    "educational":   ("fade", "slide-up", "slide-right"),
    "scientific":    ("fade", "wipe-right", "clock-wipe"),
}


# ═══════════════════════════════════════════════════════════════════
# Constants
# ═══════════════════════════════════════════════════════════════════
class TransitionConstants:
    """ثوابت."""
    
    DEFAULT_DURATION = 0.4
    MIN_DURATION = 0.1
    MAX_DURATION = 2.0
    
    HISTORY_SIZE = 3  # عدد الانتقالات الأخيرة (لتجنب التكرار)


# ═══════════════════════════════════════════════════════════════════
# Main Class
# ═══════════════════════════════════════════════════════════════════
class TransitionEngine:
    """مولّد انتقالات v2.0."""
    
    def __init__(
        self,
        video_width: int = 1080,
        video_height: int = 1920,
        default_energy: str = "medium",
        default_duration: float = TransitionConstants.DEFAULT_DURATION,
        enable_random: bool = True,
    ):
        """
        Args:
            video_width, video_height: أبعاد الفيديو
            default_energy: مستوى الطاقة الافتراضي
            default_duration: مدة افتراضية
            enable_random: تفعيل العشوائية
        """
        self.w = video_width
        self.h = video_height
        self.fps = int(os.getenv("VIDEO_FPS", "30"))
        
        # Settings
        self.default_duration = float(
            os.getenv("TRANSITION_DURATION", default_duration)
        )
        self.default_energy = os.getenv("TRANSITION_ENERGY", default_energy)
        self.enable_random = (
            enable_random and
            os.getenv("ENABLE_RANDOM_TRANSITIONS", "true").lower() == "true"
        )
        
        # History (لتجنب التكرار)
        self.history: deque[str] = deque(maxlen=TransitionConstants.HISTORY_SIZE)
        
        logger.debug(
            f"🎞️ TransitionEngine v2.0 | "
            f"Energy: {self.default_energy} | "
            f"Duration: {self.default_duration}s"
        )
    
    # ═══════════════════════════════════════════════════════════════
    # Validation
    # ═══════════════════════════════════════════════════════════════
    def _validate_duration(self, duration: float) -> float:
        """تحقق من duration."""
        if duration < TransitionConstants.MIN_DURATION:
            logger.warning(
                f"⚠ Duration {duration} too short, "
                f"using {TransitionConstants.MIN_DURATION}"
            )
            return TransitionConstants.MIN_DURATION
        
        if duration > TransitionConstants.MAX_DURATION:
            logger.warning(
                f"⚠ Duration {duration} too long, "
                f"using {TransitionConstants.MAX_DURATION}"
            )
            return TransitionConstants.MAX_DURATION
        
        return duration
    
    # ═══════════════════════════════════════════════════════════════
    # Resolution
    # ═══════════════════════════════════════════════════════════════
    def _resolve_transition(
        self,
        transition_type: str,
        scene_type: Optional[str] = None,
        mood: Optional[str] = None,
        energy: Optional[float] = None,
    ) -> str:
        """حل اسم الانتقال."""
        # 1. اسم مباشر
        if transition_type in ALL_TRANSITIONS:
            return transition_type
        
        # 2. من aliases
        mapped = TRANSITION_ALIASES.get(transition_type)
        if mapped is not None:
            if mapped:  # ليس None ولا فارغ
                return mapped
        
        # 3. auto أو غير معروف → smart selection
        return self._smart_select(scene_type, mood, energy)
    
    def _smart_select(
        self,
        scene_type: Optional[str] = None,
        mood: Optional[str] = None,
        energy: Optional[float] = None,
    ) -> str:
        """اختيار ذكي."""
        # priority order:
        # 1. Energy → high/medium/low
        # 2. Mood preference
        # 3. Scene type
        # 4. Default
        
        pool = None
        
        # 1. Energy-based
        if energy is not None:
            energy_level = EnergyLevel.from_value(energy)
            pool = self._get_pool_by_energy(energy_level.value)
        
        # 2. Mood preference (مدمج مع pool)
        if mood and mood in MOOD_TRANSITION_PREFERENCE:
            mood_pool = MOOD_TRANSITION_PREFERENCE[mood]
            if pool:
                # تقاطع: من الـ pool ومن mood
                intersection = [t for t in pool if t in mood_pool]
                if intersection:
                    pool = tuple(intersection)
                else:
                    pool = mood_pool
            else:
                pool = mood_pool
        
        # 3. Scene type
        if not pool and scene_type:
            pool = SCENE_TYPE_POOLS.get(scene_type)
        
        # 4. Default
        if not pool:
            pool = self._get_pool_by_energy(self.default_energy)
        
        # تجنب التكرار
        if self.enable_random:
            available = [t for t in pool if t not in self.history]
            if available:
                pool = tuple(available)
        
        # اختيار
        if self.enable_random:
            selected = random.choice(pool)
        else:
            selected = pool[0]
        
        self.history.append(selected)
        return selected
    
    def _get_pool_by_energy(self, energy: str) -> tuple[str, ...]:
        """Pool حسب الطاقة."""
        pools = {
            "high": ENERGY_HIGH,
            "medium": ENERGY_MEDIUM,
            "low": ENERGY_LOW,
        }
        return pools.get(energy.lower(), ENERGY_MEDIUM)
    
    # ═══════════════════════════════════════════════════════════════
    # Config Building
    # ═══════════════════════════════════════════════════════════════
    def get_transition_config(
        self,
        transition_type: str = "auto",
        duration: Optional[float] = None,
        scene_type: Optional[str] = None,
        mood: Optional[str] = None,
        energy: Optional[float] = None,
    ) -> TransitionConfig:
        """
        🎯 إرجاع إعدادات الانتقال.
        
        Args:
            transition_type: نوع
            duration: مدة (تلقائي إن None)
            scene_type: نوع المشهد
            mood: المزاج
            energy: مستوى الطاقة (0-1)
        """
        # حل الاسم
        resolved = self._resolve_transition(
            transition_type, scene_type, mood, energy
        )
        
        # المدة
        if duration is None:
            duration = DURATION_PRESETS.get(resolved, DURATION_PRESETS["default"])
        else:
            duration = self._validate_duration(duration)
        
        # بناء الـ config
        config = TransitionConfig(
            name=resolved,
            duration=duration,
            easing=EASING_PRESETS.get(resolved, "ease-in-out"),
        )
        
        # خصائص خاصة
        self._apply_type_specific_props(config, resolved)
        
        return config
    
    def _apply_type_specific_props(
        self,
        config: TransitionConfig,
        name: str,
    ) -> None:
        """تطبيق خصائص خاصة."""
        # Slide & Wipe → direction
        if name.startswith("slide-") or name.startswith("wipe-"):
            config.direction = name.split("-")[1]
        
        # Fade colors
        elif name == "fade-black":
            config.color = "#000000"
        elif name == "fade-white":
            config.color = "#FFFFFF"
        
        # Zoom
        elif name == "zoom-in":
            config.scale_from = 1.0
            config.scale_to = 1.5
        elif name == "zoom-out":
            config.scale_from = 1.5
            config.scale_to = 1.0
        
        # Iris
        elif name.startswith("iris-"):
            config.shape = "circle"
            if name == "iris-burst":
                config.scale = 2.0
        
        # Flip
        elif name == "flip-horizontal":
            config.axis = "x"
        elif name == "flip-vertical":
            config.axis = "y"
        
        # Pixelate
        elif name == "pixelate":
            config.pixel_size = 20
    
    # ═══════════════════════════════════════════════════════════════
    # Build for Scenes
    # ═══════════════════════════════════════════════════════════════
    def build_for_scenes(
        self,
        scenes: list[dict],
        mood: Optional[str] = None,
        default_type: str = "auto",
    ) -> TransitionsResult:
        """
        🎯 بناء انتقالات لكل المشاهد.
        
        Args:
            scenes: قائمة المشاهد
            mood: المزاج العام
            default_type: نوع افتراضي
        """
        if len(scenes) < 2:
            return TransitionsResult(
                success=True,
                transitions=[],
                total_count=0,
            )
        
        # reset history
        self.history.clear()
        
        transitions = []
        types_used: dict[str, int] = {}
        
        for i in range(1, len(scenes)):
            scene = scenes[i]
            scene_type = scene.get("type", "main")
            energy = float(scene.get("energy", 0.5))
            
            # احترام scene.transition إذا موجود
            requested = scene.get("transition", default_type)
            
            config = self.get_transition_config(
                transition_type=requested,
                scene_type=scene_type,
                mood=mood,
                energy=energy,
            )
            
            transitions.append(SceneTransition(
                from_scene=i - 1,
                to_scene=i,
                config=config,
            ))
            
            types_used[config.name] = types_used.get(config.name, 0) + 1
        
        result = TransitionsResult(
            success=True,
            transitions=transitions,
            total_count=len(transitions),
            types_used=types_used,
        )
        
        logger.info(
            f"✓ Built {result.total_count} transitions "
            f"({len(types_used)} unique types)"
        )
        return result
    
    # ═══════════════════════════════════════════════════════════════
    # Random Selection
    # ═══════════════════════════════════════════════════════════════
    def get_random_transition(
        self,
        energy: str = "medium",
        avoid_recent: bool = True,
    ) -> TransitionConfig:
        """transition عشوائي حسب الطاقة."""
        pool = self._get_pool_by_energy(energy)
        
        if avoid_recent:
            available = [t for t in pool if t not in self.history]
            if available:
                pool = tuple(available)
        
        name = random.choice(pool)
        self.history.append(name)
        
        return self.get_transition_config(name)
    
    # ═══════════════════════════════════════════════════════════════
    # Listing
    # ═══════════════════════════════════════════════════════════════
    def list_transitions(self) -> dict:
        """قائمة بكل الانتقالات."""
        return {
            "high": list(ENERGY_HIGH),
            "medium": list(ENERGY_MEDIUM),
            "low": list(ENERGY_LOW),
            "all": list(ALL_TRANSITIONS),
            "aliases": list(TRANSITION_ALIASES.keys()),
        }
    
    def get_transition_info(self, name: str) -> dict:
        """معلومات عن transition."""
        resolved = self._resolve_transition(name)
        config = self.get_transition_config(resolved)
        return {
            "input": name,
            "resolved": resolved,
            **config.to_dict(),
        }
    
    # ═══════════════════════════════════════════════════════════════
    # Backward Compatibility
    # ═══════════════════════════════════════════════════════════════
    def build_transitions_for_scenes(
        self,
        scenes: list[dict],
        default_type: str = "auto",
    ) -> list[dict]:
        """متوافق مع v1 - يُرجع list of dicts."""
        result = self.build_for_scenes(scenes, default_type=default_type)
        return [t.to_dict() for t in result.transitions]
    
    # ═══════════════════════════════════════════════════════════════
    # Deprecated
    # ═══════════════════════════════════════════════════════════════
    def apply_transition(self, *args, **kwargs):
        warnings.warn(
            "apply_transition() deprecated. "
            "Use get_transition_config() and pass to Remotion.",
            DeprecationWarning,
            stacklevel=2,
        )
        raise RuntimeError("Not supported in Remotion mode")
    
    def cleanup(self) -> None:
        """لا حاجة - لا ملفات مؤقتة."""
        logger.debug("No cleanup needed in Remotion mode")


# ═══════════════════════════════════════════════════════════════════
# اختبار
# ═══════════════════════════════════════════════════════════════════
if __name__ == "__main__":
    import json
    
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s | %(levelname)s | %(message)s"
    )
    
    print("=" * 60)
    print("🎞️ Transition Engine v2.0")
    print("=" * 60)
    
    engine = TransitionEngine()
    
    print(f"\n📋 Settings:")
    print(f"   • Default energy: {engine.default_energy}")
    print(f"   • Default duration: {engine.default_duration}s")
    print(f"   • Random: {engine.enable_random}")
    
    print(f"\n📦 Available:")
    transitions = engine.list_transitions()
    print(f"   • High energy: {len(transitions['high'])} types")
    print(f"   • Medium: {len(transitions['medium'])} types")
    print(f"   • Low: {len(transitions['low'])} types")
    print(f"   • All: {len(transitions['all'])} unique")
    print(f"   • Aliases: {len(transitions['aliases'])}")
    
    # اختبار configs
    print("\n🎯 Sample configs:")
    for name in ["fade", "flash_black", "slide_left", "zoom_in"]:
        config = engine.get_transition_config(name)
        print(f"\n   {name}:")
        print(json.dumps(config.to_dict(), indent=4, ensure_ascii=False))
    
    # اختبار scenes
    print("\n🎬 Building transitions for 5 scenes (dark mood):")
    test_scenes = [
        {"type": "hook", "energy": 0.95, "transition": "flash_black"},
        {"type": "build", "energy": 0.5, "transition": "cross_dissolve"},
        {"type": "peak", "energy": 0.9},
        {"type": "resolution", "energy": 0.4},
        {"type": "cta", "energy": 0.7, "transition": "fade_black"},
    ]
    
    result = engine.build_for_scenes(test_scenes, mood="dark")
    print()
    print(result.summary())
    
    print("\n📋 Transitions:")
    for t in result.transitions:
        print(
            f"   • Scene {t.from_scene} → {t.to_scene}: "
            f"{t.config.name} ({t.config.duration}s)"
        )
