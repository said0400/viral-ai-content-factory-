"""
🎨 Effects Engine v2.0 — Pro
═══════════════════════════════════════════════════════════════
مولّد إعدادات التأثيرات لـ Remotion

التحسينات v2.0:
  ✓ Dataclasses للـ configs (immutable + type-safe)
  ✓ Mood-aware presets
  ✓ Energy-aware shake intensity
  ✓ Auto effects per scene type
  ✓ Transition configs
  ✓ Validation
═══════════════════════════════════════════════════════════════
"""

from __future__ import annotations

import os
import logging
import warnings
from enum import Enum
from dataclasses import dataclass, field, asdict
from typing import Optional, Any

logger = logging.getLogger(__name__)


# ═══════════════════════════════════════════════════════════════════
# Enums
# ═══════════════════════════════════════════════════════════════════
class ZoomType(str, Enum):
    """أنواع الزوم."""
    SLOW_ZOOM_IN = "slow_zoom_in"
    SLOW_ZOOM_OUT = "slow_zoom_out"
    PUNCH_ZOOM = "punch_zoom"
    DRIFT_RIGHT = "drift_right"
    DRIFT_LEFT = "drift_left"
    DRIFT_UP = "drift_up"
    DRIFT_DOWN = "drift_down"
    STATIC = "static"


class ShakePreset(str, Enum):
    """شدة الاهتزاز."""
    OFF = "off"
    SUBTLE = "subtle"
    NORMAL = "normal"
    INTENSE = "intense"
    EXTREME = "extreme"


class GradeStyle(str, Enum):
    """التدرج اللوني."""
    CINEMATIC_WARM = "cinematic_warm"
    CINEMATIC_COOL = "cinematic_cool"
    DRAMATIC_DARK = "dramatic_dark"
    BRIGHT_VIBRANT = "bright_vibrant"
    EMOTIONAL_SOFT = "emotional_soft"
    NATURAL = "natural"
    OFF = "off"


class LetterboxStyle(str, Enum):
    """الـ Letterbox."""
    CINEMATIC = "cinematic"
    THIN = "thin"
    THICK = "thick"
    OFF = "off"


class TransitionType(str, Enum):
    """أنواع الانتقالات."""
    NONE = "none"
    SMOOTH_FADE = "smooth_fade"
    CROSS_DISSOLVE = "cross_dissolve"
    FADE_BLACK = "fade_black"
    FLASH_BLACK = "flash_black"
    FLASH_WHITE = "flash_white"
    ZOOM_BURST = "zoom_burst"
    GLITCH = "glitch"
    SLIDE_LEFT = "slide_left"
    SLIDE_RIGHT = "slide_right"


# ═══════════════════════════════════════════════════════════════════
# Dataclasses
# ═══════════════════════════════════════════════════════════════════
@dataclass(frozen=True)
class ZoomConfig:
    """إعدادات الزوم."""
    name: str
    type: str  # scale / translate / none
    from_value: float = 1.0
    to_value: float = 1.12
    easing: str = "ease-out"
    origin_x: str = "50%"
    origin_y: str = "50%"
    fast: bool = False
    
    # للـ translate
    from_x: float = 0
    to_x: float = 0
    from_y: float = 0
    to_y: float = 0
    scale: float = 1.0
    
    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "type": self.type,
            "from": self.from_value,
            "to": self.to_value,
            "easing": self.easing,
            "originX": self.origin_x,
            "originY": self.origin_y,
            "fast": self.fast,
            "fromX": self.from_x,
            "toX": self.to_x,
            "fromY": self.from_y,
            "toY": self.to_y,
            "scale": self.scale,
        }


@dataclass(frozen=True)
class ShakeConfig:
    """إعدادات الاهتزاز."""
    name: str
    enabled: bool = True
    intensity: float = 2.0
    frequency_x: float = 0.7
    frequency_y: float = 1.1
    
    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "enabled": self.enabled,
            "intensity": self.intensity,
            "frequencyX": self.frequency_x,
            "frequencyY": self.frequency_y,
        }


@dataclass(frozen=True)
class GradeConfig:
    """إعدادات التدرج اللوني."""
    name: str
    filter_str: str = "none"
    tint_r: float = 1.0
    tint_g: float = 1.0
    tint_b: float = 1.0
    vignette: bool = False
    vignette_intensity: float = 0.5
    grain: bool = False
    grain_intensity: float = 0.04
    
    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "filter": self.filter_str,
            "tint": {
                "r": self.tint_r,
                "g": self.tint_g,
                "b": self.tint_b,
            },
            "vignette": self.vignette,
            "vignetteIntensity": self.vignette_intensity,
            "grain": self.grain,
            "grainIntensity": self.grain_intensity,
        }


@dataclass(frozen=True)
class LetterboxConfig:
    """إعدادات Letterbox."""
    name: str
    enabled: bool = True
    bar_ratio: float = 0.055
    color: str = "#000000"
    opacity: float = 0.92
    
    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "enabled": self.enabled,
            "barRatio": self.bar_ratio,
            "color": self.color,
            "opacity": self.opacity,
        }


@dataclass(frozen=True)
class TransitionConfig:
    """إعدادات الانتقال."""
    name: str
    duration: float = 0.3
    easing: str = "ease-in-out"
    
    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "duration": self.duration,
            "easing": self.easing,
        }


@dataclass
class SceneEffects:
    """جميع تأثيرات المشهد."""
    scene_type: str
    zoom: ZoomConfig
    shake: ShakeConfig
    grade: GradeConfig
    letterbox: LetterboxConfig
    transition: Optional[TransitionConfig] = None
    fade_in: bool = False
    fade_out: bool = False
    
    def to_dict(self) -> dict:
        return {
            "sceneType": self.scene_type,
            "zoom": self.zoom.to_dict(),
            "shake": self.shake.to_dict(),
            "grade": self.grade.to_dict(),
            "letterbox": self.letterbox.to_dict(),
            "transition": self.transition.to_dict() if self.transition else None,
            "fadeIn": self.fade_in,
            "fadeOut": self.fade_out,
        }


# ═══════════════════════════════════════════════════════════════════
# Presets
# ═══════════════════════════════════════════════════════════════════
ZOOM_CONFIGS: dict[str, ZoomConfig] = {
    "slow_zoom_in": ZoomConfig(
        name="slow_zoom_in", type="scale",
        from_value=1.0, to_value=1.12, easing="ease-out",
    ),
    "slow_zoom_out": ZoomConfig(
        name="slow_zoom_out", type="scale",
        from_value=1.12, to_value=1.0, easing="ease-out",
    ),
    "punch_zoom": ZoomConfig(
        name="punch_zoom", type="scale",
        from_value=1.0, to_value=1.15, easing="ease-in-out",
        fast=True,
    ),
    "drift_right": ZoomConfig(
        name="drift_right", type="translate",
        scale=1.06, from_x=0, to_x=-50, easing="linear",
    ),
    "drift_left": ZoomConfig(
        name="drift_left", type="translate",
        scale=1.06, from_x=-50, to_x=0, easing="linear",
    ),
    "drift_up": ZoomConfig(
        name="drift_up", type="translate",
        scale=1.06, from_y=0, to_y=-50, easing="linear",
    ),
    "drift_down": ZoomConfig(
        name="drift_down", type="translate",
        scale=1.06, from_y=-50, to_y=0, easing="linear",
    ),
    "static": ZoomConfig(
        name="static", type="none", from_value=1.0, to_value=1.0,
    ),
}


SHAKE_PRESETS: dict[str, ShakeConfig] = {
    "off": ShakeConfig(name="off", enabled=False),
    "subtle": ShakeConfig(
        name="subtle", intensity=1.0,
        frequency_x=0.7, frequency_y=1.1,
    ),
    "normal": ShakeConfig(
        name="normal", intensity=2.0,
        frequency_x=0.7, frequency_y=1.1,
    ),
    "intense": ShakeConfig(
        name="intense", intensity=4.0,
        frequency_x=0.9, frequency_y=1.3,
    ),
    "extreme": ShakeConfig(
        name="extreme", intensity=7.0,
        frequency_x=1.2, frequency_y=1.5,
    ),
}


GRADE_CONFIGS: dict[str, GradeConfig] = {
    "cinematic_warm": GradeConfig(
        name="cinematic_warm",
        filter_str="contrast(1.15) saturate(1.12) brightness(0.95)",
        tint_r=1.05, tint_g=1.0, tint_b=0.95,
        vignette=True, vignette_intensity=0.5,
        grain=True, grain_intensity=0.04,
    ),
    "cinematic_cool": GradeConfig(
        name="cinematic_cool",
        filter_str="contrast(1.18) saturate(1.05) brightness(0.92)",
        tint_r=0.95, tint_g=1.0, tint_b=1.08,
        vignette=True, vignette_intensity=0.6,
        grain=True, grain_intensity=0.04,
    ),
    "dramatic_dark": GradeConfig(
        name="dramatic_dark",
        filter_str="contrast(1.25) saturate(0.95) brightness(0.85)",
        tint_r=0.92, tint_g=0.95, tint_b=1.0,
        vignette=True, vignette_intensity=0.8,
        grain=True, grain_intensity=0.05,
    ),
    "bright_vibrant": GradeConfig(
        name="bright_vibrant",
        filter_str="contrast(1.1) saturate(1.25) brightness(1.05)",
        tint_r=1.02, tint_g=1.02, tint_b=1.0,
        vignette=False,
        grain=False,
    ),
    "emotional_soft": GradeConfig(
        name="emotional_soft",
        filter_str="contrast(1.05) saturate(0.95) brightness(0.98)",
        tint_r=1.0, tint_g=0.98, tint_b=1.02,
        vignette=True, vignette_intensity=0.4,
        grain=True, grain_intensity=0.03,
    ),
    "natural": GradeConfig(
        name="natural",
        filter_str="contrast(1.05) saturate(1.0) brightness(1.0)",
    ),
    "off": GradeConfig(name="off"),
}


LETTERBOX_CONFIGS: dict[str, LetterboxConfig] = {
    "cinematic": LetterboxConfig(
        name="cinematic", enabled=True,
        bar_ratio=0.055, opacity=0.92,
    ),
    "thin": LetterboxConfig(
        name="thin", enabled=True,
        bar_ratio=0.03, opacity=1.0,
    ),
    "thick": LetterboxConfig(
        name="thick", enabled=True,
        bar_ratio=0.08, opacity=1.0,
    ),
    "off": LetterboxConfig(name="off", enabled=False),
}


TRANSITION_CONFIGS: dict[str, TransitionConfig] = {
    "none": TransitionConfig(name="none", duration=0),
    "smooth_fade": TransitionConfig(name="smooth_fade", duration=0.5),
    "cross_dissolve": TransitionConfig(name="cross_dissolve", duration=0.4),
    "fade_black": TransitionConfig(name="fade_black", duration=0.6),
    "flash_black": TransitionConfig(name="flash_black", duration=0.2),
    "flash_white": TransitionConfig(name="flash_white", duration=0.15),
    "zoom_burst": TransitionConfig(name="zoom_burst", duration=0.3, easing="ease-out"),
    "glitch": TransitionConfig(name="glitch", duration=0.25),
    "slide_left": TransitionConfig(name="slide_left", duration=0.4),
    "slide_right": TransitionConfig(name="slide_right", duration=0.4),
}


# ═══════════════════════════════════════════════════════════════════
# Mappings
# ═══════════════════════════════════════════════════════════════════
# Scene type → Default Zoom
SCENE_ZOOM_MAP: dict[str, str] = {
    "hook": "punch_zoom",
    "intro": "punch_zoom",
    "build": "slow_zoom_in",
    "main": "slow_zoom_in",
    "peak": "punch_zoom",
    "resolution": "slow_zoom_out",
    "outro": "slow_zoom_out",
    "cta": "drift_right",
}

# Scene type → Should shake?
SCENE_SHAKE_MAP: dict[str, str] = {
    "hook": "normal",
    "peak": "intense",
    "intro": "subtle",
    "build": "off",
    "main": "off",
    "resolution": "off",
    "outro": "subtle",
    "cta": "off",
}

# Mood → Grade
MOOD_GRADE_MAP: dict[str, str] = {
    "motivation":    "cinematic_warm",
    "motivational":  "cinematic_warm",
    "dark":          "dramatic_dark",
    "sigma":         "dramatic_dark",
    "psychological": "dramatic_dark",
    "horror":        "dramatic_dark",
    "emotional":     "emotional_soft",
    "sad":           "emotional_soft",
    "romantic":      "emotional_soft",
    "educational":   "cinematic_cool",
    "scientific":    "cinematic_cool",
    "practical":     "bright_vibrant",
    "calm":          "natural",
}

# Energy → Shake intensity boost
def adjust_shake_for_energy(
    base_shake: str,
    energy: float,
) -> str:
    """تعديل shake حسب energy."""
    if base_shake == "off":
        return "off"
    
    if energy >= 0.9:
        # رفع المستوى
        upgrades = {
            "subtle": "normal",
            "normal": "intense",
            "intense": "extreme",
        }
        return upgrades.get(base_shake, base_shake)
    
    if energy <= 0.3:
        # تخفيض المستوى
        downgrades = {
            "extreme": "intense",
            "intense": "normal",
            "normal": "subtle",
            "subtle": "off",
        }
        return downgrades.get(base_shake, base_shake)
    
    return base_shake


# ═══════════════════════════════════════════════════════════════════
# Main Class
# ═══════════════════════════════════════════════════════════════════
class EffectsEngine:
    """مولّد إعدادات التأثيرات v2.0."""
    
    def __init__(
        self,
        video_width: int = 1080,
        video_height: int = 1920,
        default_grade: Optional[str] = None,
        default_letterbox: Optional[str] = None,
    ):
        """
        Args:
            video_width: عرض الفيديو
            video_height: ارتفاع الفيديو
            default_grade: التدرج الافتراضي
            default_letterbox: الـ letterbox الافتراضي
        """
        self.w = video_width
        self.h = video_height
        self.fps = int(os.getenv("VIDEO_FPS", "30"))
        self.quality = os.getenv("VIDEO_QUALITY", "high")
        
        # Settings من env (يُعاد قراءتها)
        self._reload_settings(default_grade, default_letterbox)
        
        logger.debug(
            f"🎨 EffectsEngine v2.0 | {self.w}x{self.h}@{self.fps}fps | "
            f"Grade: {self.default_grade} | Letterbox: {self.default_letterbox}"
        )
    
    def _reload_settings(
        self,
        default_grade: Optional[str] = None,
        default_letterbox: Optional[str] = None,
    ):
        """إعادة تحميل الإعدادات من env."""
        self.enable_grain = (
            os.getenv("ENABLE_FILM_GRAIN", "true").lower() == "true"
        )
        self.enable_vignette = (
            os.getenv("ENABLE_VIGNETTE", "true").lower() == "true"
        )
        self.enable_letterbox = (
            os.getenv("ENABLE_LETTERBOX", "true").lower() == "true"
        )
        
        self.default_grade = (
            default_grade or os.getenv("GRADE_STYLE", "cinematic_warm")
        )
        self.default_shake = os.getenv("SHAKE_PRESET", "normal")
        self.default_letterbox = (
            default_letterbox or os.getenv("LETTERBOX_STYLE", "cinematic")
        )
    
    # ═══════════════════════════════════════════════════════════════
    # Validation
    # ═══════════════════════════════════════════════════════════════
    def _validate_zoom(self, zoom_type: str) -> str:
        if zoom_type not in ZOOM_CONFIGS:
            logger.warning(
                f"⚠ Zoom '{zoom_type}' غير معروف، استخدام 'slow_zoom_in'"
            )
            return "slow_zoom_in"
        return zoom_type
    
    def _validate_shake(self, preset: str) -> str:
        if preset not in SHAKE_PRESETS:
            logger.warning(
                f"⚠ Shake '{preset}' غير معروف، استخدام 'normal'"
            )
            return "normal"
        return preset
    
    def _validate_grade(self, style: str) -> str:
        if style not in GRADE_CONFIGS:
            logger.warning(
                f"⚠ Grade '{style}' غير معروف، استخدام 'cinematic_warm'"
            )
            return "cinematic_warm"
        return style
    
    def _validate_letterbox(self, style: str) -> str:
        if style not in LETTERBOX_CONFIGS:
            logger.warning(
                f"⚠ Letterbox '{style}' غير معروف، استخدام 'cinematic'"
            )
            return "cinematic"
        return style
    
    def _validate_transition(self, name: str) -> str:
        if name not in TRANSITION_CONFIGS:
            logger.warning(
                f"⚠ Transition '{name}' غير معروف، استخدام 'cross_dissolve'"
            )
            return "cross_dissolve"
        return name
    
    # ═══════════════════════════════════════════════════════════════
    # Config Getters (مع validation)
    # ═══════════════════════════════════════════════════════════════
    def get_zoom_config(self, zoom_type: str = "slow_zoom_in") -> ZoomConfig:
        """إعدادات الزوم."""
        zoom_type = self._validate_zoom(zoom_type)
        return ZOOM_CONFIGS[zoom_type]
    
    def get_shake_config(self, preset: Optional[str] = None) -> ShakeConfig:
        """إعدادات الاهتزاز."""
        preset = preset or self.default_shake
        preset = self._validate_shake(preset)
        return SHAKE_PRESETS[preset]
    
    def get_grade_config(self, style: Optional[str] = None) -> GradeConfig:
        """إعدادات التدرج اللوني."""
        style = style or self.default_grade
        style = self._validate_grade(style)
        config = GRADE_CONFIGS[style]
        
        # تطبيق env toggles
        if not self.enable_grain or not self.enable_vignette:
            # إنشاء نسخة معدّلة
            return GradeConfig(
                name=config.name,
                filter_str=config.filter_str,
                tint_r=config.tint_r,
                tint_g=config.tint_g,
                tint_b=config.tint_b,
                vignette=config.vignette and self.enable_vignette,
                vignette_intensity=config.vignette_intensity,
                grain=config.grain and self.enable_grain,
                grain_intensity=config.grain_intensity,
            )
        
        return config
    
    def get_letterbox_config(
        self,
        style: Optional[str] = None,
    ) -> LetterboxConfig:
        """إعدادات Letterbox."""
        style = style or self.default_letterbox
        style = self._validate_letterbox(style)
        config = LETTERBOX_CONFIGS[style]
        
        # env toggle
        if not self.enable_letterbox:
            return LetterboxConfig(
                name=config.name,
                enabled=False,
                bar_ratio=config.bar_ratio,
                color=config.color,
                opacity=config.opacity,
            )
        
        return config
    
    def get_transition_config(
        self,
        transition_type: str = "cross_dissolve",
    ) -> TransitionConfig:
        """إعدادات الانتقال."""
        transition_type = self._validate_transition(transition_type)
        return TRANSITION_CONFIGS[transition_type]
    
    # ═══════════════════════════════════════════════════════════════
    # Smart Effects (per scene)
    # ═══════════════════════════════════════════════════════════════
    def get_effects_for_scene(
        self,
        scene: dict,
        mood: str = "motivation",
        is_first: bool = False,
        is_last: bool = False,
    ) -> SceneEffects:
        """
        🎯 إعدادات ذكية للمشهد (يستخدم كل scene data).
        
        Args:
            scene: dict المشهد (يحتوي type, energy, transition, إلخ)
            mood: المزاج العام
            is_first: هل المشهد الأول؟
            is_last: هل المشهد الأخير؟
        """
        scene_type = scene.get("type", "main")
        energy = float(scene.get("energy", 0.5))
        
        # Zoom: من scene.camera_motion أو من scene_type
        zoom_type = scene.get(
            "camera_motion",
            SCENE_ZOOM_MAP.get(scene_type, "slow_zoom_in")
        )
        
        # Shake: من scene_type + تعديل حسب energy
        base_shake = SCENE_SHAKE_MAP.get(scene_type, "off")
        actual_shake = adjust_shake_for_energy(base_shake, energy)
        
        # Grade: حسب mood
        grade_style = MOOD_GRADE_MAP.get(mood, self.default_grade)
        
        # Transition: من scene.transition
        transition_name = scene.get("transition", "cross_dissolve")
        if is_first:
            transition_name = "none"
        
        # Fades
        fade_in = is_first
        fade_out = is_last
        
        return SceneEffects(
            scene_type=scene_type,
            zoom=self.get_zoom_config(zoom_type),
            shake=self.get_shake_config(actual_shake),
            grade=self.get_grade_config(grade_style),
            letterbox=self.get_letterbox_config(),
            transition=self.get_transition_config(transition_name),
            fade_in=fade_in,
            fade_out=fade_out,
        )
    
    def get_effects_for_all_scenes(
        self,
        scenes: list[dict],
        mood: str = "motivation",
    ) -> list[SceneEffects]:
        """🎯 إعدادات لكل المشاهد."""
        return [
            self.get_effects_for_scene(
                scene=scene,
                mood=mood,
                is_first=(i == 0),
                is_last=(i == len(scenes) - 1),
            )
            for i, scene in enumerate(scenes)
        ]
    
    # ═══════════════════════════════════════════════════════════════
    # Global Effects
    # ═══════════════════════════════════════════════════════════════
    def get_global_effects(
        self,
        mood: str = "motivation",
    ) -> dict:
        """التأثيرات العامة للفيديو كاملاً."""
        grade_style = MOOD_GRADE_MAP.get(mood, self.default_grade)
        
        return {
            "grade": self.get_grade_config(grade_style).to_dict(),
            "letterbox": self.get_letterbox_config().to_dict(),
            "fade": self.get_fade_config(),
            "mood": mood,
        }
    
    # ═══════════════════════════════════════════════════════════════
    # Additional Configs
    # ═══════════════════════════════════════════════════════════════
    def get_fade_config(
        self,
        fade_in_duration: float = 0.5,
        fade_out_duration: float = 0.5,
    ) -> dict:
        """إعدادات Fade in/out."""
        return {
            "fadeIn": {
                "enabled": True,
                "duration": fade_in_duration,
                "color": "#000000",
            },
            "fadeOut": {
                "enabled": True,
                "duration": fade_out_duration,
                "color": "#000000",
            },
        }
    
    def get_flash_config(
        self,
        intensity: float = 1.5,
        duration: float = 0.2,
        color: str = "#FFFFFF",
    ) -> dict:
        """إعدادات الفلاش."""
        return {
            "enabled": True,
            "intensity": intensity,
            "duration": duration,
            "color": color,
        }
    
    def get_glitch_config(self, intensity: float = 0.5) -> dict:
        """إعدادات Glitch."""
        return {
            "enabled": True,
            "intensity": intensity,
            "chromaShift": int(intensity * 4),
            "noise": int(intensity * 30),
        }
    
    def get_blur_config(self, sigma: float = 5.0) -> dict:
        """إعدادات Blur."""
        return {
            "enabled": True,
            "sigma": sigma,
            "filter": f"blur({sigma}px)",
        }
    
    # ═══════════════════════════════════════════════════════════════
    # Listing
    # ═══════════════════════════════════════════════════════════════
    @staticmethod
    def list_available_zooms() -> list[str]:
        return list(ZOOM_CONFIGS.keys())
    
    @staticmethod
    def list_available_shakes() -> list[str]:
        return list(SHAKE_PRESETS.keys())
    
    @staticmethod
    def list_available_grades() -> list[str]:
        return list(GRADE_CONFIGS.keys())
    
    @staticmethod
    def list_available_letterboxes() -> list[str]:
        return list(LETTERBOX_CONFIGS.keys())
    
    @staticmethod
    def list_available_transitions() -> list[str]:
        return list(TRANSITION_CONFIGS.keys())
    
    # ═══════════════════════════════════════════════════════════════
    # Deprecated Methods (مع warnings صحيحة)
    # ═══════════════════════════════════════════════════════════════
    def apply_zoom_effect(self, *args, **kwargs):
        warnings.warn(
            "apply_zoom_effect() deprecated. "
            "Use get_zoom_config() and pass to Remotion props.",
            DeprecationWarning,
            stacklevel=2,
        )
        raise RuntimeError("Not supported in Remotion mode")
    
    def apply_smooth_shake(self, *args, **kwargs):
        warnings.warn(
            "apply_smooth_shake() deprecated. Use get_shake_config().",
            DeprecationWarning,
            stacklevel=2,
        )
        raise RuntimeError("Not supported in Remotion mode")
    
    def apply_cinematic_grade(self, *args, **kwargs):
        warnings.warn(
            "apply_cinematic_grade() deprecated. Use get_grade_config().",
            DeprecationWarning,
            stacklevel=2,
        )
        raise RuntimeError("Not supported in Remotion mode")
    
    def add_letterbox(self, *args, **kwargs):
        warnings.warn(
            "add_letterbox() deprecated. Use get_letterbox_config().",
            DeprecationWarning,
            stacklevel=2,
        )
        raise RuntimeError("Not supported in Remotion mode")
    
    # ═══════════════════════════════════════════════════════════════
    # Backward Compatibility
    # ═══════════════════════════════════════════════════════════════
    def get_all_effects_for_scene(
        self,
        scene_type: str = "main",
        zoom_type: str = "slow_zoom_in",
        apply_shake: bool = False,
    ) -> dict:
        """متوافق مع v1 - يُرجع dict."""
        # بناء scene dict مؤقت
        scene = {
            "type": scene_type,
            "camera_motion": zoom_type,
            "energy": 0.5,
        }
        
        effects = self.get_effects_for_scene(scene)
        
        # override shake إذا apply_shake=True
        if apply_shake and effects.shake.name == "off":
            effects.shake = self.get_shake_config("normal")
        
        return effects.to_dict()


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
    print("🎨 Effects Engine v2.0")
    print("=" * 60)
    
    fx = EffectsEngine()
    
    print(f"\n📐 Settings:")
    print(f"   • {fx.w}x{fx.h}@{fx.fps}fps")
    print(f"   • Grade: {fx.default_grade}")
    print(f"   • Shake: {fx.default_shake}")
    print(f"   • Letterbox: {fx.default_letterbox}")
    
    print(f"\n📦 Available:")
    print(f"   • Zooms: {len(ZOOM_CONFIGS)}")
    print(f"   • Shakes: {len(SHAKE_PRESETS)}")
    print(f"   • Grades: {len(GRADE_CONFIGS)}")
    print(f"   • Transitions: {len(TRANSITION_CONFIGS)}")
    
    # اختبار scenes
    test_scenes = [
        {"type": "hook", "energy": 0.95, "transition": "flash_black"},
        {"type": "build", "energy": 0.5, "transition": "cross_dissolve"},
        {"type": "peak", "energy": 1.0, "transition": "zoom_burst"},
        {"type": "cta", "energy": 0.7, "transition": "fade_black"},
    ]
    
    print(f"\n🎬 Effects for 4 scenes (mood: dark):")
    all_effects = fx.get_effects_for_all_scenes(test_scenes, mood="dark")
    
    for i, effects in enumerate(all_effects):
        print(f"\n   Scene {i} ({effects.scene_type}):")
        print(f"      • Zoom: {effects.zoom.name}")
        print(f"      • Shake: {effects.shake.name} (enabled: {effects.shake.enabled})")
        print(f"      • Grade: {effects.grade.name}")
        if effects.transition:
            print(f"      • Transition: {effects.transition.name}")
        if effects.fade_in:
            print(f"      • Fade in: ✓")
        if effects.fade_out:
            print(f"      • Fade out: ✓")
    
    # Global effects
    print(f"\n🌐 Global effects (mood: dark):")
    global_fx = fx.get_global_effects(mood="dark")
    print(f"   • Grade: {global_fx['grade']['name']}")
    print(f"   • Letterbox: {global_fx['letterbox']['name']}")
