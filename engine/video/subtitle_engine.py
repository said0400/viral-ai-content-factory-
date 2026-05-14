import os
import logging
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont, ImageFilter

logger = logging.getLogger(__name__)

# Arabic shaping
try:
    import arabic_reshaper
    from bidi.algorithm import get_display
    ARABIC_OK = True
except Exception:
    ARABIC_OK = False


class SubtitleEngine:

    FONT_PATHS = [
        "engine/assets/fonts/Amiri-Bold.ttf",
        "/usr/share/fonts/truetype/noto/NotoNaskhArabic-Bold.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
    ]

    def __init__(self, width=1080, height=1920):
        self.w = width
        self.h = height

        self.temp_dir = Path("./temp/subtitles")
        self.temp_dir.mkdir(parents=True, exist_ok=True)

        self.font_size = int(os.getenv("SUBTITLE_SIZE", "78"))
        self.text_width_ratio = 0.86
        self.enable_glow = True
        self.enable_shadow = True

        self.font_path = self._find_font()
        if not self.font_path:
            raise RuntimeError("❌ لم يتم العثور على خط عربي")

        self.font = ImageFont.truetype(self.font_path, self.font_size)

        if ARABIC_OK:
            self.reshaper = arabic_reshaper.ArabicReshaper({
                "delete_harakat": False,
                "support_ligatures": True,
            })
        else:
            self.reshaper = None

        logger.info(f"✅ SubtitleEngine v4 Loaded | Font: {Path(self.font_path).name}")

    # ----------------------------------------------------
    # FONT
    # ----------------------------------------------------
    def _find_font(self):
        for path in self.FONT_PATHS:
            if Path(path).exists():
                return path
        return None

    # ----------------------------------------------------
    # ARABIC SHAPING (مرة واحدة فقط)
    # ----------------------------------------------------
    def _shape(self, text):
        if not ARABIC_OK:
            return text

        try:
            text = self.reshaper.reshape(text)
            text = get_display(text)
        except Exception:
            pass

        return text

    # ----------------------------------------------------
    # WRAP (بدون تشكيل أثناء القياس)
    # ----------------------------------------------------
    def _wrap_text(self, text, max_width):
        words = text.split()
        lines = []
        current = ""

        test_img = Image.new("RGB", (10, 10))
        test_draw = ImageDraw.Draw(test_img)

        for word in words:
            test_line = (current + " " + word).strip()

            bbox = test_draw.textbbox((0, 0), test_line, font=self.font)
            width = bbox[2] - bbox[0]

            if width <= max_width:
                current = test_line
            else:
                if current:
                    lines.append(current)
                current = word

        if current:
            lines.append(current)

        # ✅ التشكيل يتم هنا فقط بعد التقسيم
        shaped_lines = [self._shape(line) for line in lines]

        return shaped_lines

    # ----------------------------------------------------
    # RENDER PNG
    # ----------------------------------------------------
    def render(self, text, index=0):

        output = str(self.temp_dir / f"sub_{index:03d}.png")

        img = Image.new("RGBA", (self.w, self.h), (0, 0, 0, 0))
        draw = ImageDraw.Draw(img)

        max_width = int(self.w * self.text_width_ratio)
        lines = self._wrap_text(text, max_width)

        line_height = self.font.size + 25
        total_height = len(lines) * line_height
        start_y = int(self.h * 0.78) - total_height // 2

        for i, line in enumerate(lines):

            y = start_y + i * line_height

            bbox = draw.textbbox((0, 0), line, font=self.font)
            width = bbox[2] - bbox[0]
            x = (self.w - width) // 2

            # Glow
            if self.enable_glow:
                glow_layer = Image.new("RGBA", (self.w, self.h), (0, 0, 0, 0))
                glow_draw = ImageDraw.Draw(glow_layer)

                glow_draw.text(
                    (x, y),
                    line,
                    font=self.font,
                    fill=(255, 255, 255, 180)
                )

                glow_layer = glow_layer.filter(ImageFilter.GaussianBlur(8))
                img = Image.alpha_composite(img, glow_layer)

            # Shadow
            if self.enable_shadow:
                draw.text(
                    (x + 4, y + 4),
                    line,
                    font=self.font,
                    fill=(0, 0, 0, 180)
                )

            # Main text
            draw.text(
                (x, y),
                line,
                font=self.font,
                fill=(255, 255, 255, 255),
                stroke_width=2,
                stroke_fill=(0, 0, 0)
            )

        img.save(output, "PNG")

        return output
