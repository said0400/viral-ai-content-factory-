"""
📜 Subtitle Engine — الترجمة العربية الاحترافية (Fixed v3)
═══════════════════════════════════════════════════════════════
✓ يستخدم Amiri كخط أساسي (أفضل دعم للاتصال العربي)
✓ Reshaper config محسّن للاتصال
✓ Pillow text shaping صحيح
═══════════════════════════════════════════════════════════════
"""

import os
import logging
from pathlib import Path
from typing import Optional, List, Tuple

logger = logging.getLogger(__name__)

try:
    import arabic_reshaper
    RESHAPER_OK = True
except ImportError:
    RESHAPER_OK = False
    logger.warning("⚠ arabic_reshaper غير مثبت")

try:
    from bidi.algorithm import get_display
    BIDI_OK = True
except ImportError:
    try:
        from python_bidi.algorithm import get_display
        BIDI_OK = True
    except ImportError:
        BIDI_OK = False
        logger.warning("⚠ python-bidi غير مثبت")

        def get_display(text):
            return text

from PIL import Image, ImageDraw, ImageFilter, ImageFont


class SubtitleEngine:
    """محرك الترجمة العربية الاحترافية."""

    # ⭐ ترتيب جديد: أفضل خطوط للاتصال أولاً
    FONT_PATHS = [
        # 🥇 الأفضل للاتصال العربي
        "engine/assets/fonts/Amiri-Bold.ttf",
        "engine/assets/fonts/NotoNaskhArabic-VF.ttf",
        "engine/assets/fonts/Cairo-VF.ttf",
        # 🥈 جيد لكن أقل
        "engine/assets/fonts/Amiri-Regular.ttf",
        "engine/assets/fonts/Almarai-ExtraBold.ttf",
        "engine/assets/fonts/Almarai-Bold.ttf",
        "engine/assets/fonts/Tajawal-ExtraBold.ttf",
        "engine/assets/fonts/Tajawal-Bold.ttf",
        "engine/assets/fonts/Changa-VF.ttf",
        # خطوط Regular
        "engine/assets/fonts/Tajawal-Regular.ttf",
        "engine/assets/fonts/Almarai-Regular.ttf",
        # خطوط النظام (Linux)
        "/usr/share/fonts/truetype/noto/NotoNaskhArabic-Bold.ttf",
        "/usr/share/fonts/truetype/noto/NotoNaskhArabic-Regular.ttf",
        "/usr/share/fonts/truetype/noto/NotoSansArabic-Bold.ttf",
        "/usr/share/fonts/truetype/noto/NotoSansArabic-Regular.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
    ]

    DEFAULT_SIZES = {
        "lg": 84,
        "md": 68,
        "sm": 54,
    }

    def __init__(self, video_width: int = 1080, video_height: int = 1920):
        self.w = video_width
        self.h = video_height

        self.temp_dir = Path(os.getenv("TEMP_DIR", "./temp"))
        self.sub_dir = self.temp_dir / "subtitles"
        self.sub_dir.mkdir(parents=True, exist_ok=True)

        self.font_size_lg = int(os.getenv("SUBTITLE_SIZE_LG", str(self.DEFAULT_SIZES["lg"])))
        self.font_size_md = int(os.getenv("SUBTITLE_SIZE_MD", str(self.DEFAULT_SIZES["md"])))
        self.font_size_sm = int(os.getenv("SUBTITLE_SIZE_SM", str(self.DEFAULT_SIZES["sm"])))

        self.subtitle_style = os.getenv("SUBTITLE_STYLE", "cinematic")
        self.enable_background = os.getenv("SUBTITLE_BACKGROUND", "false").lower() == "true"
        self.enable_glow = os.getenv("SUBTITLE_GLOW", "true").lower() == "true"
        self.text_width_ratio = float(os.getenv("SUBTITLE_WIDTH_RATIO", "0.86"))

        self.font_path = self._find_font()
        if not self.font_path:
            raise RuntimeError(
                "❌ لم يُعثر على خط عربي!\n"
                "   1. شغّل: python download_fonts.py"
            )

        self._init_reshaper()
        self._load_fonts()
        logger.info(f"📜 SubtitleEngine | Font: {Path(self.font_path).name}")

    def _init_reshaper(self):
        """تهيئة reshaper محسّن للاتصال العربي."""
        self.reshaper = None
        if RESHAPER_OK:
            try:
                configuration = {
                    'delete_harakat': False,
                    'support_ligatures': True,
                    'language': 'Arabic',
                    'shift_harakat_position': False,
                    'use_unshaped_instead_of_isolated': False,
                }
                self.reshaper = arabic_reshaper.ArabicReshaper(
                    configuration=configuration
                )
                logger.info("✓ Arabic reshaper initialized with ligatures")
            except Exception as e:
                logger.warning(f"⚠ فشل إنشاء reshaper مخصص: {e}")
                self.reshaper = None

    def _reshape_text(self, text: str) -> str:
        """تطبيق reshape على النص العربي."""
        if not RESHAPER_OK:
            return text
        try:
            if self.reshaper:
                return self.reshaper.reshape(text)
            else:
                return arabic_reshaper.reshape(text)
        except Exception as e:
            logger.debug(f"reshape failed: {e}")
            return text

    def _bidi_text(self, text: str) -> str:
        """تطبيق bidi على النص العربي."""
        if not BIDI_OK:
            return text
        try:
            return get_display(text)
        except Exception as e:
            logger.debug(f"bidi failed: {e}")
            return text

    def _shape_arabic(self, text: str) -> str:
        """معالجة كاملة للنص العربي (reshape + bidi)."""
        text = self._reshape_text(text)
        text = self._bidi_text(text)
        return text

    def _find_font(self) -> Optional[str]:
        for path in self.FONT_PATHS:
            if Path(path).exists():
                return path
        return None

    def _load_fonts(self) -> None:
        try:
            self.font_lg = ImageFont.truetype(self.font_path, self.font_size_lg)
            self.font_md = ImageFont.truetype(self.font_path, self.font_size_md)
            self.font_sm = ImageFont.truetype(self.font_path, self.font_size_sm)
        except Exception as e:
            raise RuntimeError(f"❌ فشل تحميل الخط {self.font_path}: {e}")

    def render_all_scenes(self, script: dict) -> List[Tuple[str, dict]]:
        scenes = script.get("scenes", [])

        if not scenes:
            logger.warning("⚠ لا توجد مشاهد")
            return []

        results = []
        for i, scene in enumerate(scenes):
            try:
                png = self._render_png(scene, i)
                results.append((png, scene))
            except Exception as e:
                logger.error(f"❌ فشل رسم المشهد {i}: {e}")

        logger.info(f"✓ تم رسم {len(results)}/{len(scenes)} ترجمة")
        return results

    def _render_png(self, scene: dict, idx: int) -> str:
        text = scene.get("text", "").strip()
        scene_type = scene.get("type", "main")
        emphasis_words = [e.get("word", "") for e in scene.get("emphasis", [])]

        output = str(self.sub_dir / f"sub_{idx:03d}.png")

        cfg = self._get_style(scene_type, text)
        font = cfg["font"]
        text_color = cfg["text_color"]
        glow_color = cfg["glow_color"]
        ypos = cfg["y_pos"]
        stroke_width = cfg["stroke_w"]
        stroke_color = cfg["stroke_c"]
        shadow_offset = cfg["shadow"]

        img = Image.new("RGBA", (self.w, self.h), (0, 0, 0, 0))
        draw = ImageDraw.Draw(img)

        max_width = int(self.w * self.text_width_ratio)
        display_lines = self._wrap_arabic(text, font, max_width)

        if not display_lines or not display_lines[0]:
            img.save(output, "PNG")
            return output

        line_height = font.size + 30
        total_height = len(display_lines) * line_height
        start_y = int(self.h * ypos) - total_height // 2

        if self.enable_background:
            self._draw_background(draw, display_lines, font, start_y, line_height)

        for i, line in enumerate(display_lines):
            y = start_y + i * line_height

            bbox = draw.textbbox((0, 0), line, font=font)
            width = bbox[2] - bbox[0]
            x = (self.w - width) // 2

            if self.enable_glow:
                self._draw_glow(img, line, font, x, y, glow_color)

            if shadow_offset > 0:
                draw.text(
                    (x + shadow_offset, y + shadow_offset),
                    line,
                    font=font,
                    fill=(0, 0, 0, 180),
                )

            is_emphasis = self._line_has_emphasis(line, text, emphasis_words)

            if is_emphasis:
                self._draw_highlighted(draw, line, font, x, y)
            else:
                draw.text(
                    (x, y),
                    line,
                    font=font,
                    fill=text_color,
                    stroke_width=stroke_width,
                    stroke_fill=stroke_color,
                )

        img.save(output, "PNG")
        return output

    def _wrap_arabic(
        self,
        text: str,
        font: ImageFont.FreeTypeFont,
        max_width: int,
    ) -> List[str]:
        """
        تقسيم النص العربي على أسطر بشكل صحيح:
          1. تقسيم النص إلى أسطر بناءً على العرض
          2. تطبيق reshape + bidi على كل سطر كاملاً
        """
        if not text or not text.strip():
            return [""]

        words = text.split()
        if not words:
            return [""]

        test_img = Image.new("RGB", (10, 10))
        test_draw = ImageDraw.Draw(test_img)

        raw_lines = []
        current_words = []

        for word in words:
            test_words = current_words + [word]
            test_text = " ".join(test_words)

            shaped_test = self._shape_arabic(test_text)
            test_width = self._text_width(test_draw, shaped_test, font)

            if current_words and test_width > max_width:
                raw_lines.append(" ".join(current_words))
                current_words = [word]
            else:
                current_words.append(word)

        if current_words:
            raw_lines.append(" ".join(current_words))

        # ⭐ معالجة كل سطر كاملاً (الحل الصحيح للاتصال)
        display_lines = []
        for raw_line in raw_lines:
            shaped_line = self._shape_arabic(raw_line)
            display_lines.append(shaped_line)

        return display_lines if display_lines else [""]

    def _text_width(
        self,
        draw: ImageDraw.Draw,
        text: str,
        font: ImageFont.FreeTypeFont,
    ) -> int:
        bbox = draw.textbbox((0, 0), text, font=font)
        return bbox[2] - bbox[0]

    def _line_has_emphasis(
        self,
        line: str,
        original_text: str,
        emphasis_words: List[str],
    ) -> bool:
        return any(word and word in original_text for word in emphasis_words)

    def _draw_glow(
        self,
        img: Image.Image,
        text: str,
        font: ImageFont.FreeTypeFont,
        x: int,
        y: int,
        color: tuple,
    ) -> None:
        glow = Image.new("RGBA", img.size, (0, 0, 0, 0))
        gd = ImageDraw.Draw(glow)
        r, g, b = color[:3]

        for offset in [3, 6, 9]:
            for dx, dy in [(offset, 0), (-offset, 0), (0, offset), (0, -offset)]:
                gd.text(
                    (x + dx, y + dy),
                    text,
                    font=font,
                    fill=(r, g, b, 30),
                )

        blurred = glow.filter(ImageFilter.GaussianBlur(12))
        img.alpha_composite(blurred)

    def _draw_highlighted(
        self,
        draw: ImageDraw.Draw,
        text: str,
        font: ImageFont.FreeTypeFont,
        x: int,
        y: int,
    ) -> None:
        bbox = draw.textbbox((x, y), text, font=font)
        padding = 12

        draw.rounded_rectangle(
            [
                bbox[0] - padding,
                bbox[1] - padding,
                bbox[2] + padding,
                bbox[3] + padding,
            ],
            radius=10,
            fill=(255, 200, 0, 220),
        )

        draw.text(
            (x, y),
            text,
            font=font,
            fill=(15, 15, 15, 255),
            stroke_width=1,
            stroke_fill=(0, 0, 0, 180),
        )

    def _draw_background(
        self,
        draw: ImageDraw.Draw,
        lines: List[str],
        font: ImageFont.FreeTypeFont,
        start_y: int,
        line_height: int,
    ) -> None:
        max_width = 0
        for line in lines:
            bbox = draw.textbbox((0, 0), line, font=font)
            width = bbox[2] - bbox[0]
            max_width = max(max_width, width)

        total_height = len(lines) * line_height
        padding = 30

        x1 = (self.w - max_width) // 2 - padding
        y1 = start_y - padding
        x2 = (self.w + max_width) // 2 + padding
        y2 = start_y + total_height + padding

        draw.rounded_rectangle(
            [x1, y1, x2, y2],
            radius=15,
            fill=(0, 0, 0, 140),
        )

    def _get_style(self, scene_type: str, text: str = "") -> dict:
        word_count = len(text.split()) if text else 0

        if scene_type in ("hook", "peak"):
            font = self.font_lg if word_count <= 6 else self.font_md
        elif word_count > 10:
            font = self.font_sm
        else:
            font = self.font_md

        styles = {
            "hook": dict(
                font=font,
                text_color=(255, 255, 255, 255),
                glow_color=(220, 30, 30),
                y_pos=0.44,
                stroke_w=3,
                stroke_c=(0, 0, 0, 255),
                shadow=4,
            ),
            "build": dict(
                font=font,
                text_color=(240, 240, 240, 255),
                glow_color=(80, 80, 220),
                y_pos=0.55,
                stroke_w=2,
                stroke_c=(0, 0, 0, 255),
                shadow=3,
            ),
            "peak": dict(
                font=font,
                text_color=(255, 215, 0, 255),
                glow_color=(255
