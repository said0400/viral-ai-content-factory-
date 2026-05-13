"""
Subtitle Engine — مُصلح
إصلاح المشاكل الثلاث:
  1. الكتابة العربية المقلوبة    ← reshape + bidi على النص الكامل أولاً ثم التقسيم
  2. الحروف المتقطعة             ← قياس العرض بعد الـ reshape وليس قبله
  3. الخط الافتراضي المكسور      ← فحص الخط قبل البدء مع fallback واضح

ضع هذا الملف في: engine/video/subtitle_engine.py
"""

import os
from pathlib import Path

try:
    import arabic_reshaper
    RESHAPER_OK = True
except ImportError:
    RESHAPER_OK = False
    print("⚠️ arabic_reshaper غير مثبت: pip install arabic-reshaper")

try:
    from bidi.algorithm import get_display
    BIDI_OK = True
except ImportError:
    try:
        from python_bidi.algorithm import get_display
        BIDI_OK = True
    except ImportError:
        BIDI_OK = False
        def get_display(text):
            return text

from PIL import Image, ImageDraw, ImageFilter, ImageFont


class SubtitleEngine:

    # أولويات الخطوط — من الأفضل للأسوأ
    FONT_PATHS = [
        "engine/assets/fonts/Cairo.ttf",
        "engine/assets/fonts/Tajawal-ExtraBold.ttf",
        "engine/assets/fonts/Changa.ttf",
        "engine/assets/fonts/NotoNaskhArabic.ttf",
        "/usr/share/fonts/truetype/noto/NotoNaskhArabic-Regular.ttf",
        "/usr/share/fonts/truetype/noto/NotoSansArabic-Regular.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
    ]

    def __init__(self, video_width: int = 1080, video_height: int = 1920):
        self.w = video_width
        self.h = video_height

        self.temp_dir = Path(os.getenv("TEMP_DIR", "./temp"))
        self.sub_dir  = self.temp_dir / "subtitles"
        self.sub_dir.mkdir(parents=True, exist_ok=True)

        # فحص مسبق للخط — نرفض الخط الافتراضي لأنه لا يدعم العربية
        self.font_path = self._find_font()
        if not self.font_path:
            raise RuntimeError(
                "❌ لم يُعثر على خط عربي!\n"
                "حمّل Cairo.ttf وضعه في engine/assets/fonts/\n"
                "أو شغّل: apt install fonts-noto-core"
            )

        print(f"🔤 خط مُحمَّل: {self.font_path}")

        # تحميل أحجام الخطوط مسبقاً
        self.font_lg = ImageFont.truetype(self.font_path, 84)
        self.font_md = ImageFont.truetype(self.font_path, 68)
        self.font_sm = ImageFont.truetype(self.font_path, 54)

    # ─── إيجاد الخط ─────────────────────────────────────────────────────────

    def _find_font(self) -> str | None:
        for path in self.FONT_PATHS:
            if os.path.exists(path):
                return path
        return None

    # ─── الدالة الرئيسية ────────────────────────────────────────────────────

    def render_all_scenes(self, script: dict) -> list:
        results = []
        for i, scene in enumerate(script.get("scenes", [])):
            png = self._render_png(scene, i)
            results.append((png, scene))
        return results

    # ─── رسم مشهد واحد ──────────────────────────────────────────────────────

    def _render_png(self, scene: dict, idx: int) -> str:
        text       = scene.get("text", "")
        scene_type = scene.get("type", "main")
        emphasis   = [e.get("word", "") for e in scene.get("emphasis", [])]
        output     = str(self.sub_dir / f"sub_{idx:03d}.png")
        cfg        = self._style(scene_type)

        font         = cfg["font"]
        text_color   = cfg["text_color"]
        glow_color   = cfg["glow_color"]
        ypos         = cfg["y_pos"]
        stroke_width = cfg["stroke_w"]
        stroke_color = cfg["stroke_c"]
        shadow       = cfg["shadow"]

        img  = Image.new("RGBA", (self.w, self.h), (0, 0, 0, 0))
        draw = ImageDraw.Draw(img)

        # ╔═══════════════════════════════════════════════════════════╗
        # ║  الإصلاح الجوهري للعربية:                               ║
        # ║  reshape + bidi على النص الكامل أولاً،                  ║
        # ║  ثم التقسيم على النص المُعالَج                           ║
        # ╚═══════════════════════════════════════════════════════════╝
        display_lines = self._wrap_arabic_fixed(text, font, int(self.w * 0.86))

        line_height  = font.size + 30
        total_height = len(display_lines) * line_height
        start_y      = int(self.h * ypos) - total_height // 2

        for i, line in enumerate(display_lines):
            y = start_y + i * line_height

            bbox  = draw.textbbox((0, 0), line, font=font)
            width = bbox[2] - bbox[0]
            x     = (self.w - width) // 2

            # Glow
            self._glow(img, line, font, x, y, glow_color)

            # Shadow
            draw.text((x + shadow, y + shadow), line,
                      font=font, fill=(0, 0, 0, 180))

            # فحص emphasis — نبحث في النص الأصلي غير المعالَج
            is_emphasis = any(word in text for word in emphasis)

            if is_emphasis:
                self._highlight(draw, line, font, x, y)
            else:
                draw.text((x, y), line, font=font,
                          fill=text_color,
                          stroke_width=stroke_width,
                          stroke_fill=stroke_color)

        img.save(output, "PNG")
        return output

    # ─── الدالة المُصلَحة لتقسيم النص العربي ───────────────────────────────

    def _wrap_arabic_fixed(self, text: str, font, max_width: int) -> list:
        """
        الترتيب الصحيح:
          1. reshape الكلمة + bidi               ← شكل الحروف صحيح
          2. قياس العرض بعد المعالجة             ← تقسيم دقيق
          3. بناء الأسطر من الكلمات المُعالَجة   ← لا تقطيع

        ملاحظة: نعالج كل كلمة على حدة ثم نضمّها في أسطر.
        هذا يحافظ على اتصال الحروف داخل كل كلمة.
        """
        if not text.strip():
            return [""]

        words = text.split()
        if not words:
            return [""]

        # معالجة كل كلمة منفردة
        shaped_words = []
        for word in words:
            sw = word
            if RESHAPER_OK:
                sw = arabic_reshaper.reshape(sw)
            if BIDI_OK:
                sw = get_display(sw)
            shaped_words.append(sw)

        # قياس العرض وتجميع الأسطر
        test_img  = Image.new("RGB", (10, 10))
        test_draw = ImageDraw.Draw(test_img)

        lines         = []
        current_words = []
        current_width = 0
        space_width   = self._text_width(test_draw, " ", font)

        for shaped_word in shaped_words:
            word_width = self._text_width(test_draw, shaped_word, font)
            needed = word_width + (space_width if current_words else 0)

            if current_words and current_width + needed > max_width:
                # احفظ السطر الحالي (مع عكس ترتيب الكلمات للـ RTL)
                lines.append(" ".join(reversed(current_words)))
                current_words = [shaped_word]
                current_width = word_width
            else:
                current_words.append(shaped_word)
                current_width += needed

        if current_words:
            lines.append(" ".join(reversed(current_words)))

        return lines if lines else [""]

    def _text_width(self, draw: ImageDraw.Draw, text: str, font) -> int:
        bbox = draw.textbbox((0, 0), text, font=font)
        return bbox[2] - bbox[0]

    # ─── glow و highlight ───────────────────────────────────────────────────

    def _glow(self, img, text, font, x, y, color):
        glow = Image.new("RGBA", img.size, (0, 0, 0, 0))
        gd   = ImageDraw.Draw(glow)
        r, g, b = color[:3]
        for offset in [3, 6, 9]:
            for dx, dy in [(offset,0),(-offset,0),(0,offset),(0,-offset)]:
                gd.text((x + dx, y + dy), text, font=font, fill=(r, g, b, 30))
        img.alpha_composite(glow.filter(ImageFilter.GaussianBlur(12)))

    def _highlight(self, draw, text, font, x, y):
        bbox    = draw.textbbox((x, y), text, font=font)
        padding = 10
        draw.rounded_rectangle(
            [bbox[0]-padding, bbox[1]-padding, bbox[2]+padding, bbox[3]+padding],
            radius=8, fill=(255, 200, 0, 210),
        )
        draw.text((x, y), text, font=font,
                  fill=(15, 15, 15, 255),
                  stroke_width=1, stroke_fill=(0, 0, 0, 180))

    # ─── أنماط المشاهد ──────────────────────────────────────────────────────

    def _style(self, t: str) -> dict:
        styles = {
            "hook": dict(
                font=self.font_lg, text_color=(255,255,255,255),
                glow_color=(220,30,30), y_pos=0.44,
                stroke_w=3, stroke_c=(0,0,0,255), shadow=4,
            ),
            "build": dict(
                font=self.font_md, text_color=(240,240,240,255),
                glow_color=(80,80,220), y_pos=0.55,
                stroke_w=2, stroke_c=(0,0,0,255), shadow=3,
            ),
            "peak": dict(
                font=self.font_lg, text_color=(255,215,0,255),
                glow_color=(255,180,0), y_pos=0.50,
                stroke_w=3, stroke_c=(80,40,0,255), shadow=5,
            ),
            "resolution": dict(
                font=self.font_md, text_color=(200,230,255,255),
                glow_color=(40,130,255), y_pos=0.55,
                stroke_w=2, stroke_c=(0,0,0,255), shadow=3,
            ),
            "cta": dict(
                font=self.font_md, text_color=(255,255,255,255),
                glow_color=(255,255,255), y_pos=0.73,
                stroke_w=2, stroke_c=(0,0,0,255), shadow=3,
            ),
            "main": dict(
                font=self.font_md, text_color=(255,255,255,255),
                glow_color=(180,180,180), y_pos=0.55,
                stroke_w=2, stroke_c=(0,0,0,255), shadow=3,
            ),
        }
        return styles.get(t, styles["main"])
