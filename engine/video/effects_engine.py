"""
🎨 Effects Engine — مولّد إعدادات التأثيرات لـ Remotion
═══════════════════════════════════════════════════════════════
بعد التحول لـ Remotion، أصبح هذا الملف مسؤولاً عن:
  ✓ توليد إعدادات الـ Zoom (يُنفّذها Remotion بـ interpolate)
  ✓ توليد إعدادات الـ Shake (يُنفّذها Remotion بـ Math.sin)
  ✓ توليد إعدادات الـ Color Grade (CSS filters)
  ✓ توليد إعدادات الـ Letterbox
  ✓ توليد إعدادات الـ Fade/Flash/Glitch

التغييرات الكبيرة:
  ❌ حُذف: كل FFmpeg subprocess calls
  ❌ حُذف: تطبيق التأثيرات (Remotion يقوم بها)
  ✅ احتُفظ: أسماء التأثيرات وإعداداتها
  ✅ أُضيف: دوال get_*_config() لتمرير الإعدادات لـ Remotion

ملاحظة:
  • التأثيرات لم تعد تُطبّق هنا، بل في Remotion components
  • هذا الملف الآن "مرجع تكوين" بدلاً من "محرك تنفيذ"

ضع في: engine/video/effects_engine.py
═══════════════════════════════════════════════════════════════
"""

import os
import logging
from pathlib import Path
from typing import Optional, Dict, List

logger = logging.getLogger(__name__)


class EffectsEngine:
    """مولّد إعدادات التأثيرات البصرية لـ Remotion."""

    # ════════════════════════════════════════════════════════════════
    #                    إعدادات الـ Zoom
    # ════════════════════════════════════════════════════════════════
    ZOOM_CONFIGS = {
        "slow_zoom_in": {
            "type": "scale",
            "from": 1.0,
            "to": 1.12,
            "easing": "ease-out",
            "originX": "50%",
            "originY": "50%",
        },
        "slow_zoom_out": {
            "type": "scale",
            "from": 1.12,
            "to": 1.0,
            "easing": "ease-out",
            "originX": "50%",
            "originY": "50%",
        },
        "punch_zoom": {
            "type": "scale",
            "from": 1.0,
            "to": 1.15,
            "easing": "ease-in-out",
            "originX": "50%",
            "originY": "50%",
            "fast": True,  # خلال 0.5 ثانية فقط
        },
        "drift_right": {
            "type": "translate",
            "scale": 1.06,
            "fromX": 0,
            "toX": -50,  # بكسل
            "easing": "linear",
        },
        "drift_left": {
            "type": "translate",
            "scale": 1.06,
            "fromX": -50,
            "toX": 0,
            "easing": "linear",
        },
        "drift_up": {
            "type": "translate",
            "scale": 1.06,
            "fromY": 0,
            "toY": -50,
            "easing": "linear",
        },
        "drift_down": {
            "type": "translate",
            "scale": 1.06,
            "fromY": -50,
            "toY": 0,
            "easing": "linear",
        },
        "static": {
            "type": "none",
            "scale": 1.0,
        },
    }

    # ════════════════════════════════════════════════════════════════
    #                    إعدادات الـ Shake
    # ════════════════════════════════════════════════════════════════
    SHAKE_PRESETS = {
        "subtle": {
            "intensity": 1.0,
            "frequencyX": 0.7,
            "frequencyY": 1.1,
            "enabled": True,
        },
        "normal": {
            "intensity": 2.0,
            "frequencyX": 0.7,
            "frequencyY": 1.1,
            "enabled": True,
        },
        "intense": {
            "intensity": 4.0,
            "frequencyX": 0.9,
            "frequencyY": 1.3,
            "enabled": True,
        },
        "off": {
            "enabled": False,
        },
    }

    # ════════════════════════════════════════════════════════════════
    #                    إعدادات الـ Color Grade
    # ════════════════════════════════════════════════════════════════
    GRADE_CONFIGS = {
        "cinematic_warm": {
            "filter": "contrast(1.15) saturate(1.12) brightness(0.95)",
            "tint": {"r": 1.05, "g": 1.0, "b": 0.95},
            "vignette": True,
            "vignetteIntensity": 0.5,
            "grain": True,
            "grainIntensity": 0.04,
        },
        "cinematic_cool": {
            "filter": "contrast(1.18) saturate(1.05) brightness(0.92)",
            "tint": {"r": 0.95, "g": 1.0, "b": 1.08},
            "vignette": True,
            "vignetteIntensity": 0.6,
            "grain": True,
            "grainIntensity": 0.04,
        },
        "dramatic_dark": {
            "filter": "contrast(1.25) saturate(0.95) brightness(0.85)",
            "tint": {"r": 0.92, "g": 0.95, "b": 1.0},
            "vignette": True,
            "vignetteIntensity": 0.8,
            "grain": True,
            "grainIntensity": 0.05,
        },
        "natural": {
            "filter": "contrast(1.05) saturate(1.0) brightness(1.0)",
            "vignette": False,
            "grain": False,
        },
        "off": {
            "filter": "none",
            "vignette": False,
            "grain": False,
        },
    }

    # ════════════════════════════════════════════════════════════════
    #                    إعدادات Letterbox
    # ════════════════════════════════════════════════════════════════
    LETTERBOX_CONFIGS = {
        "cinematic": {
            "enabled": True,
            "barRatio": 0.055,
            "color": "#000000",
            "opacity": 0.92,
        },
        "thin": {
            "enabled": True,
            "barRatio": 0.03,
            "color": "#000000",
            "opacity": 1.0,
        },
        "thick": {
            "enabled": True,
            "barRatio": 0.08,
            "color": "#000000",
            "opacity": 1.0,
        },
        "off": {
            "enabled": False,
        },
    }

    # ════════════════════════════════════════════════════════════════
    def __init__(self, video_width: int = 1080, video_height: int = 1920):
        """
        Args:
            video_width: عرض الفيديو
            video_height: ارتفاع الفيديو
        """
        self.w = video_width
        self.h = video_height
        self.fps = int(os.getenv("VIDEO_FPS", "30"))
        self.quality = os.getenv("VIDEO_QUALITY", "high")

        # إعدادات قابلة للتخصيص من .env
        self.enable_grain = os.getenv("ENABLE_FILM_GRAIN", "true").lower() == "true"
        self.enable_vignette = os.getenv("ENABLE_VIGNETTE", "true").lower() == "true"
        self.enable_letterbox = os.getenv("ENABLE_LETTERBOX", "true").lower() == "true"
        self.grade_style = os.getenv("GRADE_STYLE", "cinematic_warm")
        self.shake_preset = os.getenv("SHAKE_PRESET", "normal")
        self.letterbox_style = os.getenv("LETTERBOX_STYLE", "cinematic")

        logger.debug(f"🎨 EffectsEngine (Remotion mode) | {self.w}x{self.h}@{self.fps}fps")

    # ════════════════════════════════════════════════════════════════
    #                    🆕 دوال إرجاع الإعدادات
    # ════════════════════════════════════════════════════════════════
    def get_zoom_config(self, zoom_type: str = "slow_zoom_in") -> Dict:
        """
        إرجاع إعدادات الـ Zoom لـ Remotion.

        Args:
            zoom_type: slow_zoom_in / slow_zoom_out / punch_zoom /
                       drift_right / drift_left / drift_up / drift_down / static

        Returns:
            dict بإعدادات الزوم لـ Remotion component
        """
        config = self.ZOOM_CONFIGS.get(zoom_type, self.ZOOM_CONFIGS["slow_zoom_in"])
        return {
            "name": zoom_type,
            **config,
        }

    def get_shake_config(self, preset: Optional[str] = None) -> Dict:
        """
        إرجاع إعدادات الـ Shake لـ Remotion.

        Args:
            preset: subtle / normal / intense / off
        """
        preset = preset or self.shake_preset
        config = self.SHAKE_PRESETS.get(preset, self.SHAKE_PRESETS["normal"])
        return {
            "name": preset,
            **config,
        }

    def get_grade_config(self, style: Optional[str] = None) -> Dict:
        """
        إرجاع إعدادات التدرج اللوني لـ Remotion.

        Args:
            style: cinematic_warm / cinematic_cool / dramatic_dark / natural / off
        """
        style = style or self.grade_style
        config = self.GRADE_CONFIGS.get(style, self.GRADE_CONFIGS["cinematic_warm"]).copy()

        # تعطيل grain/vignette حسب env
        if not self.enable_grain:
            config["grain"] = False
        if not self.enable_vignette:
            config["vignette"] = False

        return {
            "name": style,
            **config,
        }

    def get_letterbox_config(self, style: Optional[str] = None) -> Dict:
        """
        إرجاع إعدادات الـ Letterbox لـ Remotion.

        Args:
            style: cinematic / thin / thick / off
        """
        style = style or self.letterbox_style
        config = self.LETTERBOX_CONFIGS.get(style, self.LETTERBOX_CONFIGS["cinematic"]).copy()

        # تعطيل حسب env
        if not self.enable_letterbox:
            config["enabled"] = False

        return {
            "name": style,
            **config,
        }

    def get_fade_config(
        self,
        fade_in_duration: float = 0.5,
        fade_out_duration: float = 0.5,
    ) -> Dict:
        """إعدادات الـ Fade in/out."""
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
    ) -> Dict:
        """إعدادات تأثير الفلاش."""
        return {
            "enabled": True,
            "intensity": intensity,
            "duration": duration,
            "color": "#FFFFFF",
        }

    def get_glitch_config(
        self,
        intensity: float = 0.5,
    ) -> Dict:
        """إعدادات تأثير الـ Glitch."""
        return {
            "enabled": True,
            "intensity": intensity,
            "chromaShift": 2,
            "noise": int(intensity * 30),
        }

    def get_blur_config(self, sigma: float = 5.0) -> Dict:
        """إعدادات تأثير الـ Blur."""
        return {
            "enabled": True,
            "sigma": sigma,
            "filter": f"blur({sigma}px)",
        }

    # ════════════════════════════════════════════════════════════════
    #                    🆕 الدالة الشاملة للمشاهد
    # ════════════════════════════════════════════════════════════════
    def get_all_effects_for_scene(
        self,
        scene_type: str = "main",
        zoom_type: str = "slow_zoom_in",
        apply_shake: bool = False,
    ) -> Dict:
        """
        إرجاع كل تأثيرات المشهد دفعة واحدة لـ Remotion.

        Args:
            scene_type: hook / build / peak / resolution / cta / main
            zoom_type: نوع الزوم
            apply_shake: تطبيق الاهتزاز؟

        Returns:
            dict شامل بكل التأثيرات
        """
        return {
            "sceneType": scene_type,
            "zoom": self.get_zoom_config(zoom_type),
            "shake": self.get_shake_config(
                "normal" if apply_shake else "off"
            ),
            "grade": self.get_grade_config(),
            "letterbox": self.get_letterbox_config(),
        }

    def get_global_effects(self) -> Dict:
        """
        إرجاع التأثيرات العامة (للفيديو كاملاً).

        Returns:
            dict يحتوي: grade, letterbox, fade
        """
        return {
            "grade": self.get_grade_config(),
            "letterbox": self.get_letterbox_config(),
            "fade": self.get_fade_config(),
        }

    # ════════════════════════════════════════════════════════════════
    #                    دوال مساعدة
    # ════════════════════════════════════════════════════════════════
    def list_available_zooms(self) -> List[str]:
        """قائمة أنواع الـ Zoom المتاحة."""
        return list(self.ZOOM_CONFIGS.keys())

    def list_available_grades(self) -> List[str]:
        """قائمة أنماط التدرج اللوني المتاحة."""
        return list(self.GRADE_CONFIGS.keys())

    def list_available_shakes(self) -> List[str]:
        """قائمة إعدادات الاهتزاز المتاحة."""
        return list(self.SHAKE_PRESETS.keys())

    def list_available_letterboxes(self) -> List[str]:
        """قائمة أنماط الـ Letterbox المتاحة."""
        return list(self.LETTERBOX_CONFIGS.keys())

    @staticmethod
    def validate_input(path: str) -> bool:
        """التحقق من وجود الملف."""
        if not Path(path).exists():
            logger.error(f"❌ الملف غير موجود: {path}")
            return False
        if Path(path).stat().st_size < 1000:
            logger.error(f"❌ الملف فارغ أو تالف: {path}")
            return False
        return True

    # ════════════════════════════════════════════════════════════════
    #                    🔁 دوال Legacy (Deprecated)
    # ════════════════════════════════════════════════════════════════
    def apply_zoom_effect(self, *args, **kwargs):
        """⚠️ DEPRECATED: استخدم get_zoom_config() بدلاً منها."""
        raise DeprecationWarning(
            "❌ apply_zoom_effect() لم تعد مدعومة!\n"
            "   استخدم: get_zoom_config(zoom_type)\n"
            "   ثم مرّر النتيجة لـ Remotion في props"
        )

    def apply_smooth_shake(self, *args, **kwargs):
        """⚠️ DEPRECATED: استخدم get_shake_config() بدلاً منها."""
        raise DeprecationWarning(
            "❌ apply_smooth_shake() لم تعد مدعومة!\n"
            "   استخدم: get_shake_config(preset)"
        )

    def apply_cinematic_grade(self, *args, **kwargs):
        """⚠️ DEPRECATED: استخدم get_grade_config() بدلاً منها."""
        raise DeprecationWarning(
            "❌ apply_cinematic_grade() لم تعد مدعومة!\n"
            "   استخدم: get_grade_config(style)"
        )

    def add_letterbox(self, *args, **kwargs):
        """⚠️ DEPRECATED: استخدم get_letterbox_config() بدلاً منها."""
        raise DeprecationWarning(
            "❌ add_letterbox() لم تعد مدعومة!\n"
            "   استخدم: get_letterbox_config(style)"
        )

    def scale_and_crop(self, *args, **kwargs):
        """⚠️ DEPRECATED: Remotion يتعامل مع الأبعاد تلقائياً."""
        raise DeprecationWarning(
            "❌ scale_and_crop() لم تعد ضرورية!\n"
            "   Remotion يتعامل مع الأبعاد عبر CSS object-fit"
        )

    def trim_clip(self, *args, **kwargs):
        """⚠️ DEPRECATED: Remotion يقص تلقائياً عبر startFrom/endAt."""
        raise DeprecationWarning(
            "❌ trim_clip() لم تعد ضرورية!\n"
            "   Remotion يستخدم: <Video startFrom={...} endAt={...} />"
        )

    def loop_clip_to_duration(self, *args, **kwargs):
        """⚠️ DEPRECATED: Remotion يكرر تلقائياً عبر <Loop>."""
        raise DeprecationWarning(
            "❌ loop_clip_to_duration() لم تعد ضرورية!\n"
            "   Remotion يستخدم: <Loop>...</Loop>"
        )


# ════════════════════════════════════════════════════════════════════════
#                    اختبار سريع
# ════════════════════════════════════════════════════════════════════════
if __name__ == "__main__":
    import json

    fx = EffectsEngine()

    print("✓ EffectsEngine (Remotion mode) جاهز")
    print(f"  Dimensions: {fx.w}x{fx.h}")
    print(f"  FPS: {fx.fps}")
    print(f"  Grade style: {fx.grade_style}")
    print(f"  Letterbox: {fx.letterbox_style}")
    print(f"  Shake: {fx.shake_preset}")

    print("\n📦 Available zooms:")
    for z in fx.list_available_zooms():
        print(f"   • {z}")

    print("\n📦 Available grades:")
    for g in fx.list_available_grades():
        print(f"   • {g}")

    print("\n🎨 Sample scene effects (hook):")
    effects = fx.get_all_effects_for_scene(
        scene_type="hook",
        zoom_type="punch_zoom",
        apply_shake=True,
    )
    print(json.dumps(effects, indent=2, ensure_ascii=False))
