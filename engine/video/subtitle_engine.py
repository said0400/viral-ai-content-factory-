"""
📝 Subtitle Engine — مولّد بيانات الترجمات لـ Remotion
═══════════════════════════════════════════════════════════════
بعد التحول لـ Remotion، أصبح هذا الملف مسؤولاً عن:
  ✓ بناء بيانات الترجمات كـ JSON (text + timings)
  ✓ تقسيم النصوص الطويلة لأجزاء قصيرة
  ✓ توليد توقيتات كلمة بكلمة (للأنيميشن)
  ✓ توفير إعدادات تصميم الترجمات

التغييرات الكبيرة:
  ❌ حُذف: arabic_reshaper (غير ضروري في Remotion!)
  ❌ حُذف: bidi.algorithm (غير ضروري في Remotion!)
  ❌ حُذف: PIL.Image لرسم النص
  ❌ حُذف: توليد PNG لكل مشهد
  ❌ حُذف: Glow و Shadow بـ Gaussian Blur
  ✅ أُضيف: build_subtitles_data() لـ JSON
  ✅ أُضيف: split_into_chunks() لتقسيم النص
  ✅ أُضيف: get_style_config() لتصميم Remotion

ميزة كبيرة:
  • Remotion يدعم العربية natively (RTL + Shaping تلقائي)
  • لا حاجة لمكتبات خارجية مثل arabic_reshaper
  • النص يُعرض بشكل صحيح 100%

ضع في: engine/video/subtitle_engine.py
═══════════════════════════════════════════════════════════════
"""

import os
import logging
from pathlib import Path
from typing import List, Dict, Optional, Tuple

logger = logging.getLogger(__name__)


class SubtitleEngine:
    """مولّد بيانات الترجمات لـ Remotion."""

    # ════════════════════════════════════════════════════════════════
    #                    إعدادات الخط الافتراضية
    # ════════════════════════════════════════════════════════════════
    DEFAULT_FONTS = {
        "primary": "Cairo",      # ⭐ الافتراضي
        "fallback": [
            "Tajawal",
            "Almarai",
            "Noto Sans Arabic",
            "sans-serif",
        ],
    }

    # ════════════════════════════════════════════════════════════════
    #                    أنماط تصميم الترجمات
    # ════════════════════════════════════════════════════════════════
    STYLE_PRESETS = {
        "cinematic": {
            "fontSize": 78,
            "fontWeight": 900,
            "color": "#FFFFFF",
            "backgroundColor": "rgba(0,0,0,0.0)",
            "textShadow": "0 4px 20px rgba(0,0,0,0.95), 0 0 40px rgba(0,0,0,0.8)",
            "stroke": {
                "width": 2,
                "color": "#000000",
            },
            "glow": {
                "enabled": True,
                "color": "rgba(255,255,255,0.6)",
                "blur": 8,
            },
            "padding": "0 60px",
            "lineHeight": 1.4,
            "letterSpacing": "0em",
            "position": "bottom",  # top / center / bottom
            "positionOffset": 0.78,  # نسبة من الارتفاع
        },
        "modern": {
            "fontSize": 70,
            "fontWeight": 700,
            "color": "#FFFFFF",
            "backgroundColor": "rgba(0,0,0,0.55)",
            "textShadow": "0 2px 8px rgba(0,0,0,0.9)",
            "borderRadius": 16,
            "padding": "20px 40px",
            "lineHeight": 1.5,
            "letterSpacing": "0em",
            "position": "bottom",
            "positionOffset": 0.85,
        },
        "highlight": {
            "fontSize": 85,
            "fontWeight": 900,
            "color": "#FFD700",
            "backgroundColor": "rgba(0,0,0,0.0)",
            "textShadow": "0 6px 25px rgba(0,0,0,0.95), 0 0 50px rgba(255,215,0,0.4)",
            "stroke": {
                "width": 3,
                "color": "#000000",
            },
            "padding": "0 60px",
            "lineHeight": 1.3,
            "position": "center",
            "positionOffset": 0.5,
        },
        "minimal": {
            "fontSize": 60,
            "fontWeight": 600,
            "color": "#FFFFFF",
            "backgroundColor": "rgba(0,0,0,0.0)",
            "textShadow": "0 2px 6px rgba(0,0,0,0.8)",
            "padding": "0 40px",
            "lineHeight": 1.5,
            "position": "bottom",
            "positionOffset": 0.88,
        },
    }

    # ════════════════════════════════════════════════════════════════
    #                    إعدادات تقسيم النص
    # ════════════════════════════════════════════════════════════════
    MAX_CHARS_PER_LINE = 35       # أقصى عدد حروف في السطر
    MAX_WORDS_PER_CHUNK = 8       # أقصى عدد كلمات في الجزء
    MAX_CHUNK_DURATION = 3.5      # أقصى مدة للجزء (ثواني)

    # ════════════════════════════════════════════════════════════════
    def __init__(self, width: int = 1080, height: int = 1920):
        """
        Args:
            width: عرض الفيديو
            height: ارتفاع الفيديو
        """
        self.w = width
        self.h = height

        # إعدادات قابلة للتخصيص من .env
        self.font_size = int(os.getenv("SUBTITLE_SIZE", "78"))
        self.font_family = os.getenv("SUBTITLE_FONT", "Cairo")
        self.style_preset = os.getenv("SUBTITLE_STYLE", "cinematic")
        self.enable_word_timings = os.getenv(
            "ENABLE_WORD_TIMINGS", "false"
        ).lower() == "true"

        # مجلد للملفات المؤقتة (إذا احتجناه)
        self.temp_dir = Path(os.getenv("TEMP_DIR", "./temp")) / "subtitles"
        self.temp_dir.mkdir(parents=True, exist_ok=True)

        logger.info(
            f"📝 SubtitleEngine (Remotion mode) | "
            f"Style: {self.style_preset} | Size: {self.font_size}"
        )

    # ════════════════════════════════════════════════════════════════
    #                    🆕 الدالة الرئيسية
    # ════════════════════════════════════════════════════════════════
    def build_subtitles_data(
        self,
        scenes: List[Dict],
        split_long_text: bool = True,
    ) -> List[Dict]:
        """
        🆕 بناء بيانات الترجمات كـ JSON لـ Remotion.

        Args:
            scenes: قائمة المشاهد [{text, duration, pause_after}, ...]
            split_long_text: تقسيم النصوص الطويلة لأجزاء؟

        Returns:
            قائمة الترجمات [
                {
                    "id": 0,
                    "text": "السلام عليكم",
                    "start": 0.0,
                    "end": 2.5,
                    "duration": 2.5,
                    "sceneId": 0,
                    "words": [
                        {"text": "السلام", "start": 0.0, "end": 1.2},
                        {"text": "عليكم", "start": 1.3, "end": 2.5}
                    ]
                },
                ...
            ]
        """
        if not scenes:
            logger.warning("⚠ لا توجد مشاهد")
            return []

        subtitles = []
        cumulative_time = 0.0
        sub_id = 0

        for scene_idx, scene in enumerate(scenes):
            text = scene.get("text", "").strip()
            duration = float(scene.get("duration", 3.0))
            pause = float(scene.get("pause_after", 0.3))

            if not text:
                cumulative_time += duration + pause
                continue

            # تقسيم النص الطويل لأجزاء
            if split_long_text and self._is_long_text(text):
                chunks = self.split_into_chunks(text, duration)
            else:
                chunks = [(text, duration)]

            # بناء كل جزء كترجمة منفصلة
            chunk_start = cumulative_time
            for chunk_text, chunk_duration in chunks:
                subtitle = {
                    "id": sub_id,
                    "text": chunk_text,
                    "start": round(chunk_start, 3),
                    "end": round(chunk_start + chunk_duration, 3),
                    "duration": round(chunk_duration, 3),
                    "sceneId": scene_idx,
                }

                # إضافة توقيتات الكلمات (للـ Karaoke effect)
                if self.enable_word_timings:
                    subtitle["words"] = self.build_word_timings(
                        chunk_text, chunk_start, chunk_duration
                    )

                subtitles.append(subtitle)
                chunk_start += chunk_duration
                sub_id += 1

            cumulative_time += duration + pause

        logger.info(f"✓ تم بناء {len(subtitles)} ترجمة من {len(scenes)} مشهد")
        return subtitles

    # ════════════════════════════════════════════════════════════════
    #                    🆕 تقسيم النص الطويل
    # ════════════════════════════════════════════════════════════════
    def _is_long_text(self, text: str) -> bool:
        """التحقق إن كان النص طويلاً ويحتاج تقسيم."""
        words_count = len(text.split())
        return (
            words_count > self.MAX_WORDS_PER_CHUNK
            or len(text) > self.MAX_CHARS_PER_LINE * 2
        )

    def split_into_chunks(
        self,
        text: str,
        total_duration: float,
    ) -> List[Tuple[str, float]]:
        """
        تقسيم النص الطويل لأجزاء قصيرة مع توزيع المدة.

        Args:
            text: النص الكامل
            total_duration: المدة الإجمالية

        Returns:
            قائمة الأجزاء [(text, duration), ...]
        """
        words = text.split()
        if not words:
            return [(text, total_duration)]

        chunks_text = []
        current_chunk = []
        current_length = 0

        for word in words:
            word_length = len(word) + 1  # +1 للمسافة

            # إذا تجاوزنا الحد، ابدأ جزء جديد
            if (
                len(current_chunk) >= self.MAX_WORDS_PER_CHUNK
                or current_length + word_length > self.MAX_CHARS_PER_LINE * 2
            ):
                if current_chunk:
                    chunks_text.append(" ".join(current_chunk))
                current_chunk = [word]
                current_length = word_length
            else:
                current_chunk.append(word)
                current_length += word_length

        # إضافة آخر جزء
        if current_chunk:
            chunks_text.append(" ".join(current_chunk))

        # توزيع المدة على الأجزاء بالتناسب مع طول كل جزء
        total_chars = sum(len(c) for c in chunks_text)
        chunks = []

        for chunk_text in chunks_text:
            ratio = len(chunk_text) / total_chars if total_chars > 0 else 1 / len(chunks_text)
            chunk_duration = total_duration * ratio
            # حد أدنى للمدة
            chunk_duration = max(chunk_duration, 1.0)
            # حد أقصى
            chunk_duration = min(chunk_duration, self.MAX_CHUNK_DURATION)
            chunks.append((chunk_text, chunk_duration))

        return chunks

    # ════════════════════════════════════════════════════════════════
    #                    🆕 توقيتات الكلمات (Karaoke)
    # ════════════════════════════════════════════════════════════════
    def build_word_timings(
        self,
        text: str,
        start_time: float,
        duration: float,
    ) -> List[Dict]:
        """
        بناء توقيتات كلمة بكلمة (للـ Karaoke effect).

        Args:
            text: النص
            start_time: وقت البداية
            duration: المدة الإجمالية

        Returns:
            [{"text": "كلمة", "start": 0.0, "end": 0.5}, ...]
        """
        words = text.split()
        if not words:
            return []

        # توزيع المدة بالتناسب مع طول كل كلمة
        total_chars = sum(len(w) for w in words)
        words_data = []
        current_time = start_time

        for word in words:
            ratio = len(word) / total_chars if total_chars > 0 else 1 / len(words)
            word_duration = duration * ratio
            # حد أدنى
            word_duration = max(word_duration, 0.15)

            words_data.append({
                "text": word,
                "start": round(current_time, 3),
                "end": round(current_time + word_duration, 3),
            })
            current_time += word_duration

        return words_data

    # ════════════════════════════════════════════════════════════════
    #                    🆕 إعدادات التصميم
    # ════════════════════════════════════════════════════════════════
    def get_style_config(self, preset: Optional[str] = None) -> Dict:
        """
        إرجاع إعدادات تصميم الترجمات لـ Remotion.

        Args:
            preset: cinematic / modern / highlight / minimal

        Returns:
            dict بكل خصائص التصميم
        """
        preset = preset or self.style_preset
        config = self.STYLE_PRESETS.get(
            preset, self.STYLE_PRESETS["cinematic"]
        ).copy()

        # تخصيص حجم الخط من .env
        if self.font_size != 78:
            config["fontSize"] = self.font_size

        # تخصيص الخط
        config["fontFamily"] = self._build_font_family()
        config["preset"] = preset
        config["direction"] = "rtl"
        config["textAlign"] = "center"

        return config

    def _build_font_family(self) -> str:
        """بناء font-family CSS مع fallbacks."""
        primary = self.font_family or self.DEFAULT_FONTS["primary"]
        fallbacks = ", ".join(
            f"'{f}'" for f in self.DEFAULT_FONTS["fallback"]
        )
        return f"'{primary}', {fallbacks}"

    def get_full_subtitle_props(
        self,
        scenes: List[Dict],
        style_preset: Optional[str] = None,
    ) -> Dict:
        """
        إرجاع كل بيانات الترجمات مع التصميم لـ Remotion دفعة واحدة.

        Returns:
            {
                "subtitles": [...],
                "style": {...},
                "totalCount": 10,
            }
        """
        subtitles = self.build_subtitles_data(scenes)
        style = self.get_style_config(style_preset)

        return {
            "subtitles": subtitles,
            "style": style,
            "totalCount": len(subtitles),
        }

    # ════════════════════════════════════════════════════════════════
    #                    دوال مساعدة
    # ════════════════════════════════════════════════════════════════
    def list_available_styles(self) -> List[str]:
        """قائمة أنماط التصميم المتاحة."""
        return list(self.STYLE_PRESETS.keys())

    def estimate_reading_time(self, text: str, wpm: int = 150) -> float:
        """
        تقدير وقت القراءة للنص بالعربية.

        Args:
            text: النص
            wpm: كلمات في الدقيقة (افتراضي 150)

        Returns:
            الوقت بالثواني
        """
        words = len(text.split())
        return (words / wpm) * 60

    @staticmethod
    def clean_text(text: str) -> str:
        """تنظيف النص من المسافات الزائدة."""
        return " ".join(text.split())

    # ════════════════════════════════════════════════════════════════
    #                    🔁 دوال Legacy (Deprecated)
    # ════════════════════════════════════════════════════════════════
    def render(self, *args, **kwargs):
        """⚠️ DEPRECATED: لم تعد ضرورية."""
        raise DeprecationWarning(
            "❌ render() لم تعد مدعومة!\n"
            "   Remotion يعرض الترجمات مباشرة من JSON\n"
            "   استخدم: build_subtitles_data(scenes)\n"
            "   ثم مرّر النتيجة لـ Remotion"
        )

    def _shape(self, text: str) -> str:
        """⚠️ DEPRECATED: غير ضروري في Remotion."""
        logger.warning(
            "⚠ _shape() غير ضروري في Remotion!\n"
            "   المتصفح يعالج العربية بشكل native"
        )
        return text  # إرجاع كما هو، بدون معالجة

    def _wrap_text(self, *args, **kwargs):
        """⚠️ DEPRECATED: CSS يعمل التفاف تلقائياً."""
        raise DeprecationWarning(
            "❌ _wrap_text() لم تعد ضرورية!\n"
            "   CSS يعمل التفاف النص تلقائياً عبر max-width"
        )


# ════════════════════════════════════════════════════════════════════════
#                    اختبار سريع
# ════════════════════════════════════════════════════════════════════════
if __name__ == "__main__":
    import json

    engine = SubtitleEngine()

    print("✓ SubtitleEngine (Remotion mode) جاهز")
    print(f"  Style: {engine.style_preset}")
    print(f"  Font Size: {engine.font_size}")
    print(f"  Font Family: {engine.font_family}")

    print("\n📦 Available styles:")
    for s in engine.list_available_styles():
        print(f"   • {s}")

    # اختبار بناء البيانات
    test_scenes = [
        {"text": "السلام عليكم ورحمة الله وبركاته", "duration": 3.0, "pause_after": 0.3},
        {"text": "هذا اختبار لمحرك الترجمات الجديد المتوافق مع Remotion", "duration": 5.0, "pause_after": 0.3},
        {"text": "اشترك الآن", "duration": 2.0, "pause_after": 0.0},
    ]

    print("\n📝 اختبار بناء الترجمات:")
    subtitles = engine.build_subtitles_data(test_scenes)
    print(json.dumps(subtitles, indent=2, ensure_ascii=False))

    print("\n🎨 إعدادات التصميم:")
    style = engine.get_style_config()
    print(json.dumps(style, indent=2, ensure_ascii=False))
