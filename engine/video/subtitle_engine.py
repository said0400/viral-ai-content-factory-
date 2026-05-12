"""
Subtitle Engine
Arabic RTL Safe
Pillow + arabic_reshaper + bidi
PNG Overlay Generator for FFmpeg
"""

import os
from pathlib import Path

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

from PIL import (
    Image,
    ImageDraw,
    ImageFilter,
    ImageFont,
)


class SubtitleEngine:

    FONT_PATHS = [

        # الأفضل أولاً
        "engine/assets/fonts/Cairo.ttf",

        "engine/assets/fonts/Tajawal-ExtraBold.ttf",

        "engine/assets/fonts/Changa.ttf",

        "engine/assets/fonts/NotoNaskhArabic.ttf",
    ]

    SYSTEM_FONTS = [

        "/usr/share/fonts/truetype/noto/NotoNaskhArabic-Regular.ttf",

        "/usr/share/fonts/truetype/noto/NotoSansArabic-Regular.ttf",

        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
    ]

    def __init__(
        self,
        video_width: int = 1080,
        video_height: int = 1920
    ):

        self.w = video_width
        self.h = video_height

        self.temp_dir = Path(
            os.getenv("TEMP_DIR", "./temp")
        )

        self.sub_dir = (
            self.temp_dir / "subtitles"
        )

        self.sub_dir.mkdir(
            parents=True,
            exist_ok=True
        )

        self.font_path = self._find_font()

        print(f"🔤 Using font: {self.font_path}")

        self.font_lg = self._load_font(
            self.font_path,
            84
        )

        self.font_md = self._load_font(
            self.font_path,
            68
        )

        self.font_sm = self._load_font(
            self.font_path,
            54
        )

    def _find_font(self):

        for path in (
            self.FONT_PATHS + self.SYSTEM_FONTS
        ):

            if os.path.exists(path):
                return path

        return None

    def _load_font(
        self,
        path,
        size
    ):

        try:

            if path and os.path.exists(path):

                return ImageFont.truetype(
                    path,
                    size
                )

        except Exception as e:

            print(f"⚠️ Font load error: {e}")

        print("⚠️ Using default Pillow font")

        return ImageFont.load_default()

    def reshape(
        self,
        text: str
    ) -> str:

        """
        إصلاح النص العربي:
        - ربط الحروف
        - RTL
        """

        try:

            result = text

            if RESHAPER_OK:
                result = arabic_reshaper.reshape(result)

            if BIDI_OK:
                result = get_display(result)

            return result

        except Exception as e:

            print(f"⚠️ Arabic reshape error: {e}")

            return text

    def render_all_scenes(
        self,
        script: dict
    ) -> list:

        results = []

        for i, scene in enumerate(
            script.get("scenes", [])
        ):

            png = self._render_png(
                scene,
                i
            )

            results.append(
                (png, scene)
            )

        return results

    def _render_png(
        self,
        scene: dict,
        idx: int
    ) -> str:

        text = scene.get(
            "text",
            ""
        )

        scene_type = scene.get(
            "type",
            "main"
        )

        emphasis = [

            e.get("word", "")

            for e in scene.get(
                "emphasis",
                []
            )
        ]

        output = str(
            self.sub_dir / f"sub_{idx:03d}.png"
        )

        cfg = self._style(scene_type)

        font = cfg["font"]

        text_color = cfg["text_color"]

        glow_color = cfg["glow_color"]

        ypos = cfg["y_pos"]

        stroke_width = cfg["stroke_w"]

        stroke_color = cfg["stroke_c"]

        shadow = cfg["shadow"]

        img = Image.new(
            "RGBA",
            (self.w, self.h),
            (0, 0, 0, 0)
        )

        draw = ImageDraw.Draw(img)

        # تقسيم النص قبل RTL
        raw_lines = self._wrap_arabic(
            text,
            font,
            int(self.w * 0.86)
        )

        # ثم إصلاح العربية
        display_lines = [

            self.reshape(line)

            for line in raw_lines
        ]

        line_height = font.size + 30

        total_height = (
            len(display_lines)
            * line_height
        )

        start_y = (
            int(self.h * ypos)
            - total_height // 2
        )

        for i, line in enumerate(display_lines):

            y = start_y + (
                i * line_height
            )

            bbox = draw.textbbox(
                (0, 0),
                line,
                font=font
            )

            width = bbox[2] - bbox[0]

            x = (
                self.w - width
            ) // 2

            # Glow
            self._glow(
                img,
                line,
                font,
                x,
                y,
                glow_color
            )

            # Shadow
            draw.text(
                (x + shadow, y + shadow),
                line,
                font=font,
                fill=(0, 0, 0, 180),
            )

            original_line = (
                raw_lines[i]
                if i < len(raw_lines)
                else ""
            )

            is_emphasis = any(

                word in original_line

                for word in emphasis
            )

            if is_emphasis:

                self._highlight(
                    draw,
                    line,
                    font,
                    x,
                    y
                )

            else:

                draw.text(

                    (x, y),

                    line,

                    font=font,

                    fill=text_color,

                    stroke_width=stroke_width,

                    stroke_fill=stroke_color,
                )

        img.save(
            output,
            "PNG"
        )

        return output

    def _wrap_arabic(
        self,
        text,
        font,
        max_width
    ):

        """
        تقسيم النص العربي
        بدون تقطيع الحروف
        """

        words = text.split()

        if not words:
            return [""]

        lines = []

        current = ""

        test_img = Image.new(
            "RGB",
            (10, 10)
        )

        test_draw = ImageDraw.Draw(test_img)

        for word in words:

            candidate = (
                f"{current} {word}"
            ).strip()

            shaped = candidate

            if RESHAPER_OK:
                shaped = arabic_reshaper.reshape(
                    shaped
                )

            if BIDI_OK:
                shaped = get_display(
                    shaped
                )

            bbox = test_draw.textbbox(
                (0, 0),
                shaped,
                font=font
            )

            width = bbox[2] - bbox[0]

            if width <= max_width:

                current = candidate

            else:

                if current:
                    lines.append(current)

                current = word

        if current:
            lines.append(current)

        return lines

    def _glow(
        self,
        img,
        text,
        font,
        x,
        y,
        color
    ):

        glow_layer = Image.new(
            "RGBA",
            img.size,
            (0, 0, 0, 0)
        )

        glow_draw = ImageDraw.Draw(
            glow_layer
        )

        r, g, b = color[:3]

        for offset in [3, 6, 9]:

            glow_draw.text(
                (x - offset, y),
                text,
                font=font,
                fill=(r, g, b, 30)
            )

            glow_draw.text(
                (x + offset, y),
                text,
                font=font,
                fill=(r, g, b, 30)
            )

            glow_draw.text(
                (x, y - offset),
                text,
                font=font,
                fill=(r, g, b, 30)
            )

            glow_draw.text(
                (x, y + offset),
                text,
                font=font,
                fill=(r, g, b, 30)
            )

        blurred = glow_layer.filter(
            ImageFilter.GaussianBlur(12)
        )

        img.alpha_composite(blurred)

    def _highlight(
        self,
        draw,
        text,
        font,
        x,
        y
    ):

        bbox = draw.textbbox(
            (x, y),
            text,
            font=font
        )

        padding = 10

        draw.rounded_rectangle(

            [

                bbox[0] - padding,
                bbox[1] - padding,

                bbox[2] + padding,
                bbox[3] + padding,
            ],

            radius=8,

            fill=(255, 200, 0, 210),
        )

        draw.text(

            (x, y),

            text,

            font=font,

            fill=(15, 15, 15, 255),

            stroke_width=1,

            stroke_fill=(0, 0, 0, 180),
        )

    def _style(
        self,
        t: str
    ) -> dict:

        base = {

            "hook": dict(

                font=self.font_lg,

                text_color=(255, 255, 255, 255),

                glow_color=(220, 30, 30),

                y_pos=0.44,

                stroke_w=3,

                stroke_c=(0, 0, 0, 255),

                shadow=4,
            ),

            "build": dict(

                font=self.font_md,

                text_color=(240, 240, 240, 255),

                glow_color=(80, 80, 220),

                y_pos=0.55,

                stroke_w=2,

                stroke_c=(0, 0, 0, 255),

                shadow=3,
            ),

            "peak": dict(

                font=self.font_lg,

                text_color=(255, 215, 0, 255),

                glow_color=(255, 180, 0),

                y_pos=0.50,

                stroke_w=3,

                stroke_c=(80, 40, 0, 255),

                shadow=5,
            ),

            "resolution": dict(

                font=self.font_md,

                text_color=(200, 230, 255, 255),

                glow_color=(40, 130, 255),

                y_pos=0.55,

                stroke_w=2,

                stroke_c=(0, 0, 0, 255),

                shadow=3,
            ),

            "cta": dict(

                font=self.font_md,

                text_color=(255, 255, 255, 255),

                glow_color=(255, 255, 255),

                y_pos=0.73,

                stroke_w=2,

                stroke_c=(0, 0, 0, 255),

                shadow=3,
            ),

            "main": dict(

                font=self.font_md,

                text_color=(255, 255, 255, 255),

                glow_color=(180, 180, 180),

                y_pos=0.55,

                stroke_w=2,

                stroke_c=(0, 0, 0, 255),

                shadow=3,
            ),
        }

        return base.get(
            t,
            base["main"]
        )
