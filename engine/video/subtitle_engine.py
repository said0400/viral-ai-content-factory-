"""
📜 Subtitle Engine v3 (Final Fixed)
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

    FONT_PATHS = [
        "engine/assets/fonts/Amiri-Bold.ttf",
        "engine/assets/fonts/NotoNaskhArabic-VF.ttf",
        "engine/assets/fonts/Cairo-VF.ttf",
        "engine/assets/fonts/Amiri-Regular.ttf",
        "engine/assets/fonts/Almarai-ExtraBold.ttf",
        "engine/assets/fonts/Almarai-Bold.ttf",
        "engine/assets/fonts/Tajawal-ExtraBold.ttf",
        "engine/assets/fonts/Tajawal-Bold.ttf",
        "engine/assets/fonts/Changa-VF.ttf",
        "engine/assets/fonts/Tajawal-Regular.ttf",
        "engine/assets/fonts/Almarai-Regular.ttf",
        "/usr/share/fonts/truetype/noto/NotoNaskhArabic-Bold.ttf",
        "/usr/share/fonts/truetype/noto/NotoNaskhArabic-Regular.ttf",
        "/usr/share/fonts/truetype/noto/NotoSansArabic-Bold.ttf",
        "/usr/share/fonts/truetype/noto/NotoSansArabic-Regular.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
    ]

    DEFAULT_SIZES = {"lg": 84, "md": 68, "sm": 54}

    def __init__(self, video_width=1080, video_height=1920):
        self.w = video_width
        self.h = video_height
        self.temp_dir = Path(os.getenv("TEMP_DIR", "./temp"))
        self.sub_dir = self.temp_dir / "subtitles"
        self.sub_dir.mkdir(parents=True, exist_ok=True)
        self.font_size_lg = int(os.getenv("SUBTITLE_SIZE_LG", "84"))
        self.font_size_md = int(os.getenv("SUBTITLE_SIZE_MD", "68"))
        self.font_size_sm = int(os.getenv("SUBTITLE_SIZE_SM", "54"))
        self.subtitle_style = os.getenv("SUBTITLE_STYLE", "cinematic")
        self.enable_background = os.getenv("SUBTITLE_BACKGROUND", "false").lower() == "true"
        self.enable_glow = os.getenv("SUBTITLE_GLOW", "true").lower() == "true"
        self.text_width_ratio = float(os.getenv("SUBTITLE_WIDTH_RATIO", "0.86"))
        self.font_path = self._find_font()
        if not self.font_path:
            raise RuntimeError("❌ لم يُعثر على خط عربي!")
        self._init_reshaper()
        self._load_fonts()
        logger.info(f"📜 Font: {Path(self.font_path).name}")

    def _init_reshaper(self):
        self.reshaper = None
        if RESHAPER_OK:
            try:
                config = {
                    'delete_harakat': False,
                    'support_ligatures': True,
                    'language': 'Arabic',
                }
                self.reshaper = arabic_reshaper.ArabicReshaper(configuration=config)
            except Exception:
                self.reshaper = None

    def _shape_arabic(self, text):
        if RESHAPER_OK:
            try:
                if self.reshaper:
                    text = self.reshaper.reshape(text)
                else:
                    text = arabic_reshaper.reshape(text)
            except Exception:
                pass
        if BIDI_OK:
            try:
                text = get_display(text)
            except Exception:
                pass
        return text

    def _find_font(self):
        for path in self.FONT_PATHS:
            if Path(path).exists():
                return path
        return None

    def _load_fonts(self):
        self.font_lg = ImageFont.truetype(self.font_path, self.font_size_lg)
        self.font_md = ImageFont.truetype(self.font_path, self.font_size_md)
        self.font_sm = ImageFont.truetype(self.font_path, self.font_size_sm)

    def render_all_scenes(self, script):
        scenes = script.get("scenes", [])
        if not scenes:
            return []
        results = []
        for i, scene in enumerate(scenes):
            try:
                png = self._render_png(scene, i)
                results.append((png, scene))
            except Exception as e:
                logger.error(f"❌ مشهد {i}: {e}")
        logger.info(f"✓ {len(results)}/{len(scenes)} ترجمة")
        return results

    def _render_png(self, scene, idx):
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
                    line, font=font, fill=(0, 0, 0, 180),
                )
            is_emphasis = any(w and w in text for w in emphasis_words)
            if is_emphasis:
                self._draw_highlighted(draw, line, font, x, y)
            else:
                draw.text(
                    (x, y), line, font=font,
                    fill=text_color,
                    stroke_width=stroke_width,
                    stroke_fill=stroke_color,
                )
        img.save(output, "PNG")
        return output

    def _wrap_arabic(self, text, font, max_width):
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
            test_text = " ".join(current_words + [word])
            shaped_test = self._shape_arabic(test_text)
            bbox = test_draw.textbbox((0, 0), shaped_test, font=font)
            test_width = bbox[2] - bbox[0]
            if current_words and test_width > max_width:
                raw_lines.append(" ".join(current_words))
                current_words = [word]
            else:
                current_words.append(word)
        if current_words:
            raw_lines.append(" ".join(current_words))
        display_lines = []
        for raw_line in raw_lines:
            display_lines.append(self._shape_arabic(raw_line))
        return display_lines if display_lines else [""]

    def _draw_glow(self, img, text, font, x, y, color):
        glow = Image.new("RGBA", img.size, (0, 0, 0, 0))
        gd = ImageDraw.Draw(glow)
        r, g, b = color[:3]
        for offset in [3, 6, 9]:
            for dx, dy in [(offset, 0), (-offset, 0), (0, offset), (0, -offset)]:
                gd.text((x + dx, y + dy), text, font=font, fill=(r, g, b, 30))
        blurred = glow.filter(ImageFilter.GaussianBlur(12))
        img.alpha_composite(blurred)

    def _draw_highlighted(self, draw, text, font, x, y):
        bbox = draw.textbbox((x, y), text, font=font)
        padding = 12
        draw.rounded_rectangle(
            [bbox[0] - padding, bbox[1] - padding,
             bbox[2] + padding, bbox[3] + padding],
            radius=10,
            fill=(255, 200, 0, 220),
        )
        draw.text(
            (x, y), text, font=font,
            fill=(15, 15, 15, 255),
            stroke_width=1,
            stroke_fill=(0, 0, 0, 180),
        )

    def _draw_background(self, draw, lines, font, start_y, line_height):
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

    def _get_style(self, scene_type, text=""):
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
                y_pos=0.44, stroke_w=3,
                stroke_c=(0, 0, 0, 255), shadow=4,
            ),
            "build": dict(
                font=font,
                text_color=(240, 240, 240, 255),
                glow_color=(80, 80, 220),
                y_pos=0.55, stroke_w=2,
                stroke_c=(0, 0, 0, 255), shadow=3,
            ),
            "peak": dict(
                font=font,
                text_color=(255, 215, 0, 255),
                glow_color=(255, 180, 0),
                y_pos=0.50, stroke_w=3,
                stroke_c=(80, 40, 0, 255), shadow=5,
            ),
            "resolution": dict(
                font=font,
                text_color=(200, 230, 255, 255),
                glow_color=(40, 130, 255),
                y_pos=0.55, stroke_w=2,
                stroke_c=(0, 0, 0, 255), shadow=3,
            ),
            "cta": dict(
                font=font,
                text_color=(255, 255, 255, 255),
                glow_color=(255, 255, 255),
                y_pos=0.73, stroke_w=2,
                stroke_c=(0, 0, 0, 255), shadow=3,
            ),
            "main": dict(
                font=font,
                text_color=(255, 255, 255, 255),
                glow_color=(180, 180, 180),
                y_pos=0.55, stroke_w=2,
                stroke_c=(0, 0, 0, 255), shadow=3,
            ),
        }
        return styles.get(scene_type, styles["main"])

    def render_text(self, text, output_path, scene_type="main"):
        scene = {"text": text, "type": scene_type, "emphasis": []}
        return self._render_png(scene, 0)

    def cleanup(self):
        try:
            for f in self.sub_dir.glob("*.png"):
                f.unlink(missing_ok=True)
        except Exception:
            pass
