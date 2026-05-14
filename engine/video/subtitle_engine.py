"""
📜 Subtitle Engine — الترجمة العربية الاحترافية (Fixed v2)
═══════════════════════════════════════════════════════════════
محرك ترجمة متقدم يدعم:
  ✓ العربية الكاملة (RTL + reshape + bidi)
  ✓ 6 أنماط مختلفة (hook/build/peak/resolution/cta/main)
  ✓ Glow + Shadow + Highlight سينمائي
  ✓ تخصيص كامل من .env
  ✓ Auto-sizing حسب طول النص
  ✓ Fallback ذكي للخطوط
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

    FONT_PATHS = [
        "engine/assets/fonts/Tajawal-ExtraBold.ttf",
        "engine/assets/fonts/Tajawal-Bold.ttf",
        "engine/assets/fonts/Almarai-ExtraBold.ttf",
        "engine/assets/fonts/Almarai-Bold.ttf",
        "engine/assets/fonts/Amiri-Bold.ttf",
        "engine/assets/fonts/Cairo-VF.ttf",
        "engine/assets/fonts/Changa-VF.ttf",
        "engine/assets/fonts/NotoNaskhArabic-VF.ttf",
        "engine/assets/fonts/Tajawal-Regular.ttf",
        "engine/assets/fonts/Almarai-Regular.ttf",
        "engine/assets/fonts/Amiri-Regular.ttf",
        "engine/assets/fonts/Cairo-Bold.ttf",
        "engine/assets/fonts/Cairo.ttf",
        "engine/assets/fonts/Tajawal.ttf",
        "engine/assets/fonts/Changa.ttf",
        "engine/assets/fonts/NotoNaskhArabic.ttf",
        "/usr/share/fonts/truetype/noto/NotoNaskhArabic-Bold.ttf",
        "/usr/share/fonts/truetype/noto/NotoNaskhArabic-Regular.ttf",
        "/usr/share/fonts/truetype/noto/NotoSansArabic-Bold.ttf",
        "/usr/share/fonts/truetype/noto/NotoSansArabic-Regular.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
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
                "   1. شغّل: python download_fonts.py\n"
                "   2. أو ثبّت: apt install fonts-noto-core"
            )

        self._load_fonts()
        logger.info(f"📜 SubtitleEngine | Font: {Path(self.font_path).name}")

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
          1. تقسيم النص إلى أسطر بناءً على العرض (قبل reshape)
          2. تطبيق reshape + bidi على كل سطر كاملاً (ليس كلمة بكلمة)
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

            shaped_test = test_text
            if RESHAPER_OK:
                try:
                    shaped_test = arabic_reshaper.reshape(test_text)
                except Exception:
                    pass
            if BIDI_OK:
                try:
                    shaped_test = get_display(shaped_test)
                except Exception:
                    pass

            test_width = self._text_width(test_draw, shaped_test, font)

            if current_words and test_width > max_width:
                raw_lines.append(" ".join(current_words))
                current_words = [word]
            else:
                current_words.append(word)

        if current_words:
            raw_lines.append(" ".join(current_words))

        display_lines = []
        for raw_line in raw_lines:
            shaped_line = raw_line
            if RESHAPER_OK:
                try:
                    shaped_line = arabic_reshaper.reshape(raw_line)
                except Exception as e:
                    logger.debug(f"reshape failed: {e}")
            if BIDI_OK:
                try:
                    shaped_line = get_display(shaped_line)
                except Exception as e:
                    logger.debug(f"bidi failed: {e}")
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
                glow_color=(255, 180, 0),
                y_pos=0.50,
                stroke_w=3,
                stroke_c=(80, 40, 0, 255),
                shadow=5,
            ),
            "resolution": dict(
                font=font,
                text_color=(200, 230, 255, 255),
                glow_color=(40, 130, 255),
                y_pos=0.55,
                stroke_w=2,
                stroke_c=(0, 0, 0, 255),
                shadow=3,
            ),
            "cta": dict(
                font=font,
                text_color=(255, 255, 255, 255),
                glow_color=(255, 255, 255),
                y_pos=0.73,
                stroke_w=2,
                stroke_c=(0, 0, 0, 255),
                shadow=3,
            ),
            "main": dict(
                font=font,
                text_color=(255, 255, 255, 255),
                glow_color=(180, 180, 180),
                y_pos=0.55,
                stroke_w=2,
                stroke_c=(0, 0, 0, 255),
                shadow=3,
            ),
        }

        return styles.get(scene_type, styles["main"])

    def render_text(
        self,
        text: str,
        output_path: str,
        scene_type: str = "main",
    ) -> str:
        scene = {
            "text": text,
            "type": scene_type,
            "emphasis": [],
        }
        return self._render_png(scene, 0)

    def cleanup(self) -> None:
        try:
            count = 0
            for f in self.sub_dir.glob("*.png"):
                f.unlink(missing_ok=True)
                count += 1
            if count:
                logger.info(f"🧹 تم تنظيف {count} ملف ترجمة")
        except Exception as e:
            logger.warning(f"⚠ فشل التنظيف: {e}")
