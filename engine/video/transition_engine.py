"""
🎞️ Transition Engine — مولّد إعدادات الانتقالات لـ Remotion
═══════════════════════════════════════════════════════════════
بعد التحول لـ Remotion، أصبح هذا الملف مسؤولاً عن:
  ✓ توليد إعدادات الانتقالات (يُنفّذها Remotion بـ TransitionSeries)
  ✓ تصنيف الانتقالات حسب الطاقة (high/medium/low)
  ✓ خريطة أسماء Remotion-compatible
  ✓ توليد انتقالات ذكية لكل المشاهد دفعة واحدة

التغييرات الكبيرة:
  ❌ حُذف: FFmpeg xfade (يُستبدل بـ Remotion TransitionSeries)
  ❌ حُذف: تطبيع الفيديو (Remotion يطبّع تلقائياً)
  ❌ حُذف: concat fallback (Remotion يجمع تلقائياً)
  ✅ احتُفظ: تصنيف الانتقالات + الاختيار الذكي
  ✅ أُضيف: get_transition_config() لـ Remotion
  ✅ أُضيف: build_transitions_for_scenes()

Remotion Transitions Available:
  • fade        — تلاشي بسيط
  • slide       — انزلاق
  • wipe        — مسح
  • flip        — قلب
  • clockWipe   — مسح ساعة
  • iris        — قزحية
  • none        — بدون

ضع في: engine/video/transition_engine.py
═══════════════════════════════════════════════════════════════
"""

import os
import random
import logging
from pathlib import Path
from typing import List, Dict, Optional

logger = logging.getLogger(__name__)


class TransitionEngine:
    """مولّد إعدادات الانتقالات السينمائية لـ Remotion."""

    # ════════════════════════════════════════════════════════════════
    #              تصنيف الانتقالات حسب الطاقة
    # ════════════════════════════════════════════════════════════════
    # Remotion-native transitions (من @remotion/transitions)
    
    ENERGY_HIGH = [
        "fade-black",      # تلاشي للأسود
        "fade-white",      # تلاشي للأبيض
        "iris-burst",      # قزحية متفجرة
        "wipe-left",       # مسح من اليمين لليسار
        "wipe-right",      # مسح من اليسار لليمين
        "flip-horizontal", # قلب أفقي
        "zoom-in",         # تكبير قوي
        "pixelate",        # بكسلات
    ]

    ENERGY_MEDIUM = [
        "fade",            # تلاشي عادي
        "slide-up",        # انزلاق للأعلى
        "slide-down",      # انزلاق للأسفل
        "slide-left",      # انزلاق لليسار
        "slide-right",     # انزلاق لليمين
        "wipe-up",         # مسح للأعلى
        "wipe-down",       # مسح للأسفل
    ]

    ENERGY_LOW = [
        "fade",            # تلاشي خفيف
        "smooth-fade",     # تلاشي ناعم
        "dissolve",        # ذوبان
        "iris-open",       # قزحية فاتحة
        "iris-close",      # قزحية مغلقة
        "clock-wipe",      # مسح ساعة
    ]

    ALL = list(set(ENERGY_HIGH + ENERGY_MEDIUM + ENERGY_LOW))

    # ════════════════════════════════════════════════════════════════
    #         خريطة الأسماء المخصصة → Remotion names
    # ════════════════════════════════════════════════════════════════
    TRANSITION_MAP = {
        # auto = عشوائي
        "auto":              None,
        "none":              "none",
        
        # تلاشي
        "fade":              "fade",
        "fade_black":        "fade-black",
        "fade_white":        "fade-white",
        "flash_black":       "fade-black",
        "flash_white":       "fade-white",
        "cross_dissolve":    "fade",
        "smooth_fade":       "smooth-fade",
        "dissolve":          "dissolve",

        # انزلاق
        "push_up":           "slide-up",
        "push_down":         "slide-down",
        "slide_left":        "slide-left",
        "slide_right":       "slide-right",
        "smooth_left":       "slide-left",
        "smooth_right":      "slide-right",
        "smooth_up":         "slide-up",
        "smooth_down":       "slide-down",

        # مسح
        "wipe_left":         "wipe-left",
        "wipe_right":        "wipe-right",
        "wipe_up":           "wipe-up",
        "wipe_down":         "wipe-down",
        "whip_right":        "wipe-left",
        "whip_left":         "wipe-right",

        # تكبير
        "zoom_burst":        "zoom-in",
        "zoom_in":           "zoom-in",
        "zoom_out":          "zoom-out",

        # قزحية
        "circle_open":       "iris-open",
        "circle_close":      "iris-close",
        "circle_crop":       "iris-burst",
        "iris":              "iris-open",

        # خاصة
        "glitch":            "pixelate",
        "pixel":             "pixelate",
        "pixelize":          "pixelate",
        "flip":              "flip-horizontal",
        "flip_h":            "flip-horizontal",
        "flip_v":            "flip-vertical",
        "clock":             "clock-wipe",

        # قص (rect/diag)
        "rect_crop":         "iris-burst",
        "diag_bl":           "wipe-left",
        "diag_br":           "wipe-right",
        "diag_tl":           "wipe-up",
        "diag_tr":           "wipe-down",
    }

    # ════════════════════════════════════════════════════════════════
    #              إعدادات Easing لكل نوع
    # ════════════════════════════════════════════════════════════════
    EASING_PRESETS = {
        "fade":            "ease-in-out",
        "fade-black":      "ease-in",
        "fade-white":      "ease-in",
        "smooth-fade":     "ease-in-out",
        "dissolve":        "linear",
        "slide-up":        "ease-out",
        "slide-down":      "ease-out",
        "slide-left":      "ease-out",
        "slide-right":     "ease-out",
        "wipe-left":       "ease-in-out",
        "wipe-right":      "ease-in-out",
        "wipe-up":         "ease-in-out",
        "wipe-down":       "ease-in-out",
        "zoom-in":         "ease-in",
        "zoom-out":        "ease-out",
        "iris-open":       "ease-out",
        "iris-close":      "ease-in",
        "iris-burst":      "ease-in",
        "flip-horizontal": "ease-in-out",
        "flip-vertical":   "ease-in-out",
        "clock-wipe":      "linear",
        "pixelate":        "ease-in-out",
        "none":            "linear",
    }

    # ════════════════════════════════════════════════════════════════
    #              مدة الانتقال حسب النوع
    # ════════════════════════════════════════════════════════════════
    DURATION_PRESETS = {
        # سريعة (0.2s)
        "fade-black":      0.2,
        "fade-white":      0.2,
        "zoom-in":         0.25,
        "iris-burst":      0.25,
        "pixelate":        0.3,

        # متوسطة (0.4s)
        "fade":            0.4,
        "smooth-fade":     0.5,
        "slide-up":        0.4,
        "slide-down":      0.4,
        "slide-left":      0.4,
        "slide-right":     0.4,
        "wipe-left":       0.4,
        "wipe-right":      0.4,
        "wipe-up":         0.4,
        "wipe-down":       0.4,

        # بطيئة (0.6s+)
        "dissolve":        0.6,
        "iris-open":       0.6,
        "iris-close":      0.6,
        "clock-wipe":      0.7,
        "flip-horizontal": 0.5,
        "flip-vertical":   0.5,

        # افتراضي
        "default":         0.4,
        "none":            0.0,
    }

    # ════════════════════════════════════════════════════════════════
    #         خريطة المشهد → الانتقالات المناسبة
    # ════════════════════════════════════════════════════════════════
    SCENE_TYPE_TRANSITIONS = {
        "hook":       ENERGY_HIGH,       # افتتاحية → قوية
        "build":      ENERGY_MEDIUM,     # بناء → متوسطة
        "peak":       ENERGY_HIGH,       # ذروة → قوية
        "resolution": ENERGY_MEDIUM,     # حل → متوسطة
        "cta":        ENERGY_LOW,        # call to action → خفيفة
        "main":       ENERGY_MEDIUM,     # عام → متوسطة
        "intro":      ENERGY_HIGH,       # مقدمة → قوية
        "outro":      ENERGY_LOW,        # خاتمة → خفيفة
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

        # إعدادات قابلة للتخصيص
        self.default_duration = float(os.getenv("TRANSITION_DURATION", "0.4"))
        self.default_energy = os.getenv("TRANSITION_ENERGY", "medium")
        self.enable_random = os.getenv("ENABLE_RANDOM_TRANSITIONS", "true").lower() == "true"

        logger.debug(
            f"🎞️ TransitionEngine (Remotion mode) | "
            f"Energy: {self.default_energy} | Duration: {self.default_duration}s"
        )

    # ════════════════════════════════════════════════════════════════
    #              🆕 الدالة الرئيسية
    # ════════════════════════════════════════════════════════════════
    def get_transition_config(
        self,
        transition_type: str = "auto",
        duration: Optional[float] = None,
        scene_type: Optional[str] = None,
    ) -> Dict:
        """
        🆕 إرجاع إعدادات الانتقال لـ Remotion.

        Args:
            transition_type: نوع الانتقال (auto / fade / slide_left / ...)
            duration: مدة الانتقال (إذا None، يُحسب تلقائياً)
            scene_type: نوع المشهد (للاختيار الذكي)

        Returns:
            dict بإعدادات الانتقال:
            {
                "name": "fade",
                "duration": 0.4,
                "easing": "ease-in-out",
                "direction": "from-left",  # للـ slide/wipe
                "color": "#000000",         # للـ fade-black
            }
        """
        # 1. حل الاسم
        resolved = self._resolve_transition(transition_type, scene_type)

        # 2. تحديد المدة
        if duration is None:
            duration = self.DURATION_PRESETS.get(
                resolved, self.DURATION_PRESETS["default"]
            )

        # 3. بناء الإعدادات
        config = {
            "name": resolved,
            "duration": round(duration, 3),
            "easing": self.EASING_PRESETS.get(resolved, "ease-in-out"),
        }

        # 4. خصائص خاصة لكل نوع
        config.update(self._get_type_specific_props(resolved))

        return config

    def _resolve_transition(
        self,
        transition_type: str,
        scene_type: Optional[str] = None,
    ) -> str:
        """حل اسم الانتقال إلى Remotion-compatible name."""
        # 1. اسم مباشر متاح
        if transition_type in self.ALL:
            return transition_type

        # 2. اسم مخصص من الخريطة
        mapped = self.TRANSITION_MAP.get(transition_type)
        if mapped is not None:
            return mapped if mapped else self._random_for_scene(scene_type)

        # 3. auto أو غير معروف → عشوائي حسب نوع المشهد
        return self._random_for_scene(scene_type)

    def _random_for_scene(self, scene_type: Optional[str] = None) -> str:
        """اختيار انتقال عشوائي مناسب للمشهد."""
        if scene_type and scene_type in self.SCENE_TYPE_TRANSITIONS:
            pool = self.SCENE_TYPE_TRANSITIONS[scene_type]
        else:
            pool = self._get_pool_by_energy(self.default_energy)

        return random.choice(pool) if self.enable_random else pool[0]

    def _get_pool_by_energy(self, energy: str) -> List[str]:
        """الحصول على pool حسب مستوى الطاقة."""
        pools = {
            "high": self.ENERGY_HIGH,
            "medium": self.ENERGY_MEDIUM,
            "low": self.ENERGY_LOW,
        }
        return pools.get(energy.lower(), self.ENERGY_MEDIUM)

    def _get_type_specific_props(self, transition_name: str) -> Dict:
        """خصائص إضافية حسب نوع الانتقال."""
        props = {}

        # Slide & Wipe → direction
        if transition_name.startswith("slide-") or transition_name.startswith("wipe-"):
            direction = transition_name.split("-")[1]
            props["direction"] = direction  # left, right, up, down

        # Fade-black/white → color
        elif transition_name == "fade-black":
            props["color"] = "#000000"
        elif transition_name == "fade-white":
            props["color"] = "#FFFFFF"

        # Zoom → scale
        elif transition_name == "zoom-in":
            props["scaleFrom"] = 1.0
            props["scaleTo"] = 1.5
        elif transition_name == "zoom-out":
            props["scaleFrom"] = 1.5
            props["scaleTo"] = 1.0

        # Iris → shape
        elif transition_name.startswith("iris-"):
            props["shape"] = "circle"
            if transition_name == "iris-burst":
                props["scale"] = 2.0

        # Flip → axis
        elif transition_name == "flip-horizontal":
            props["axis"] = "x"
        elif transition_name == "flip-vertical":
            props["axis"] = "y"

        # Pixelate → strength
        elif transition_name == "pixelate":
            props["pixelSize"] = 20

        return props

    # ════════════════════════════════════════════════════════════════
    #              🆕 بناء انتقالات لكل المشاهد
    # ════════════════════════════════════════════════════════════════
    def build_transitions_for_scenes(
        self,
        scenes: List[Dict],
        default_type: str = "auto",
    ) -> List[Dict]:
        """
        🆕 بناء قائمة انتقالات لكل المشاهد.

        Args:
            scenes: قائمة المشاهد
            default_type: النوع الافتراضي

        Returns:
            قائمة الانتقالات (واحد بين كل مشهدين متتاليين)
            [
                {
                    "fromScene": 0,
                    "toScene": 1,
                    "name": "fade",
                    "duration": 0.4,
                    "easing": "ease-in-out",
                },
                ...
            ]
        """
        if len(scenes) < 2:
            return []

        transitions = []
        used_recently = []  # لتجنب التكرار المباشر

        for i in range(1, len(scenes)):
            scene_type = scenes[i].get("type", "main")

            # اختيار transition من pool المشهد
            pool = self.SCENE_TYPE_TRANSITIONS.get(
                scene_type, self.ENERGY_MEDIUM
            )

            # تجنب التكرار (آخر 2 transitions)
            available = [t for t in pool if t not in used_recently[-2:]]
            if not available:
                available = pool

            transition_name = random.choice(available) if self.enable_random else available[0]
            used_recently.append(transition_name)

            # الحصول على الإعدادات الكاملة
            config = self.get_transition_config(
                transition_type=transition_name,
                scene_type=scene_type,
            )

            transitions.append({
                "fromScene": i - 1,
                "toScene": i,
                **config,
            })

        return transitions

    # ════════════════════════════════════════════════════════════════
    #              دوال مساعدة عامة
    # ════════════════════════════════════════════════════════════════
    def get_random_transition(
        self,
        energy: str = "medium",
    ) -> Dict:
        """
        الحصول على transition عشوائي حسب الطاقة.

        Args:
            energy: high / medium / low

        Returns:
            dict كامل بالإعدادات
        """
        pool = self._get_pool_by_energy(energy)
        name = random.choice(pool)
        return self.get_transition_config(name)

    def list_transitions(self) -> Dict:
        """قائمة بكل الانتقالات المتاحة."""
        return {
            "high": self.ENERGY_HIGH,
            "medium": self.ENERGY_MEDIUM,
            "low": self.ENERGY_LOW,
            "all": self.ALL,
            "custom_aliases": list(self.TRANSITION_MAP.keys()),
        }

    def get_transition_info(self, transition_name: str) -> Dict:
        """معلومات تفصيلية عن transition محدد."""
        resolved = self._resolve_transition(transition_name)
        return {
            "input": transition_name,
            "resolved": resolved,
            "duration": self.DURATION_PRESETS.get(resolved, 0.4),
            "easing": self.EASING_PRESETS.get(resolved, "ease-in-out"),
            "props": self._get_type_specific_props(resolved),
        }

    # ════════════════════════════════════════════════════════════════
    #              🔁 دوال Legacy (Deprecated)
    # ════════════════════════════════════════════════════════════════
    def apply_transition(self, *args, **kwargs):
        """⚠️ DEPRECATED: استخدم get_transition_config() بدلاً منها."""
        raise DeprecationWarning(
            "❌ apply_transition() لم تعد مدعومة!\n"
            "   استخدم: get_transition_config(transition_type)\n"
            "   ثم مرّر النتيجة لـ Remotion في props\n"
            "\n"
            "   مثال:\n"
            "   config = engine.get_transition_config('fade', duration=0.5)\n"
            "   # سيُمرّر إلى Remotion's <TransitionSeries>"
        )

    def cleanup(self) -> None:
        """⚠️ لم تعد ضرورية - لا توجد ملفات مؤقتة."""
        logger.debug("✓ لا حاجة للتنظيف في Remotion mode")


# ════════════════════════════════════════════════════════════════════════
#                    اختبار سريع
# ════════════════════════════════════════════════════════════════════════
if __name__ == "__main__":
    import json

    engine = TransitionEngine()

    print("✓ TransitionEngine (Remotion mode) جاهز")
    print(f"  Default energy: {engine.default_energy}")
    print(f"  Default duration: {engine.default_duration}s")
    print(f"  Random enabled: {engine.enable_random}")

    print("\n📦 Transitions by energy:")
    transitions = engine.list_transitions()
    print(f"  High: {transitions['high'][:5]}...")
    print(f"  Medium: {transitions['medium'][:5]}...")
    print(f"  Low: {transitions['low'][:5]}...")

    print("\n🎯 اختبار get_transition_config:")
    for name in ["fade", "flash_black", "slide_left", "auto"]:
        config = engine.get_transition_config(name)
        print(f"\n  {name}:")
        print(f"    {json.dumps(config, indent=4, ensure_ascii=False)}")

    print("\n🎬 اختبار build_transitions_for_scenes:")
    test_scenes = [
        {"type": "hook"},
        {"type": "build"},
        {"type": "peak"},
        {"type": "resolution"},
        {"type": "cta"},
    ]
    all_trans = engine.build_transitions_for_scenes(test_scenes)
    print(json.dumps(all_trans, indent=2, ensure_ascii=False))
