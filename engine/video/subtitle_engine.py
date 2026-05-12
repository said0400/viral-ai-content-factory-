"""
Subtitle Engine
arabic_reshaper + bidi + Pillow → PNG overlays → FFmpeg
"""

import os

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

        def get_display(t):
            return t

from PIL import Image, ImageDraw, ImageFilter, ImageFont
from pathlib import Path


class SubtitleEngine:

    FONT_PATHS = [
        "engine/assets/fonts/Cairo-Black.ttf",
        "engine/assets/fonts/Cairo.ttf",
        "engine/assets/fonts/Tajawal-ExtraBold.ttf",
        "engine/assets/fonts/Changa.ttf",
        "engine/assets/fonts/NotoNaskhArabic.ttf",
        "engine/assets/fonts/NotoNaskhArabic-Bold.ttf",
    ]

    SYSTEM_FONTS = [
        "/usr/share/fonts/truetype/noto/NotoNaskhArabic-Bold.ttf",
        "/usr/share/fonts/truetype/noto/NotoSansArabic-Bold.ttf",
        "/usr/share/fonts/truetype/arabeyes/ae_AlBattar.ttf",
        "/usr/share/fonts/opentype/noto/NotoNaskhArabic-Regular.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
    ]

    def __init__(self, video_width: int = 1080, video_height: int = 1920):

        self.w = video_width
        self.h = video_height

        self.temp_dir = Path(os.getenv("TEMP_DIR", "./temp"))
        self.sub_dir = self.temp_dir / "subtitles"

        self.sub_dir.mkdir(parents=True, exist_ok=True)

        font_path = self._find_font()

        print(f"  🔤 Using font: {font_path}")

        # نفس المنطق الأصلي للأحجام
        self.font_lg = self._load_font(font_path, 84)
        self.font_md = self._load_font(font_path, 68)
        self.font_sm = self._load_font(font_path, 54)

    def _find_font(self) -> str | None:

        for p in self.FONT_PATHS + self.SYSTEM_FONTS:
            if os.path.exists(p):
                return p

        fonts_dir = Path("engine/assets/fonts")

        if fonts_dir.exists():
            ttfs = list(fonts_dir.glob("*.ttf"))

            if ttfs:
                return str(ttfs[0])

        for d in [
            "/usr/share/fonts/truetype",
            "/usr/share/fonts/opentype",
        ]:

            if Path(d).exists():

                found = list(Path(d).rglob("*.ttf"))

                if found:
                    return str(found[0])

        return None

    def _load_font(
        self,
        path: str | None,
        size: int
    ) -> ImageFont.FreeTypeFont:

        if path and os.path.exists(path):

            try:
                return ImageFont.truetype(path, size)

            except Exception as e:
                print(f"⚠️ Font load error: {e}")

        print("⚠️ Using default font")

        return ImageFont.load_default()

    def reshape(self, text: str) -> str:
        """
        إصلاح النص العربي:
        - ربط الحروف
        - تصحيح الاتجاه RTL
        """

        try:

            if RESHAPER_OK:
                text = arabic_reshaper.reshape(text)

            if BIDI_OK:
                text = get_display(text)

            return text

        except Exception as e:

            print(f"⚠️ Arabic reshape error: {e}")

            return text

    def render_all_scenes(self, script: dict) -> list:

        results = []

        for i, scene in enumerate(script.get("scenes", [])):

            png = self._render_png(scene, i)

            results.append((png, scene))

        return results

    def _render_png(self, scene: dict, idx: int) -> str:

        text = scene.get("text", "")
        s_type = scene.get("type", "main")

        emphasis = [
            e.get("word", "")
            for e in scene.get("emphasis", [])
        ]

        out = str(
            self.sub_dir / f"sub_{idx:03d}.png"
        )

        cfg = self._style(s_type)

        font = cfg["font"]
        tc = cfg["text_color"]
        gc = cfg["glow_color"]

        ypos = cfg["y_pos"]

        sw = cfg["stroke_w"]
        sc = cfg["stroke_c"]

        shd = cfg["shadow"]

        img = Image.new(
            "RGBA",
            (self.w, self.h),
            (0, 0, 0, 0)
        )

        draw = ImageDraw.Draw(img)

        # تقسيم النص العربي بشكل صحيح
        raw_lines = self._wrap_arabic(
            text,
            font,
            int(self.w * 0.86)
        )

        # إصلاح RTL بعد التقسيم
        display_lines = []

        for line in raw_lines:

            fixed_line = self.reshape(line)

            display_lines.append(fixed_line)

        lh = font.size + 30

        total_h = len(display_lines) * lh

        start_y = int(self.h * ypos) - total_h // 2

        for li, line in enumerate(display_lines):

            ly = start_y + li * lh

            bb = draw.textbbox(
                (0, 0),
                line,
                font=font
            )

            lw = bb[2] - bb[0]

            lx = (self.w - lw) // 2

            # Glow
            self._glow(
                img,
                line,
                font,
                lx,
                ly,
                gc
            )

            # Shadow
            draw.text(
                (lx + shd, ly + shd),
                line,
                font=font,
                fill=(0, 0, 0, 180),
            )

            orig_line = (
                raw_lines[li]
                if li < len(raw_lines)
                else ""
            )

            is_emp = any(
                w in orig_line
                for w in emphasis
                if w
            )

            if is_emp:

                self._highlight(
                    draw,
                    line,
                    font,
                    lx,
                    ly
                )

            else:

                draw.text(
                    (lx, ly),
                    line,
                    font=font,
                    fill=tc,
                    stroke_width=sw,
                    stroke_fill=sc,
                )

        img.save(out, "PNG")

        return out

    def _wrap_arabic(
        self,
        text: str,
        font,
        max_w: int
    ) -> list:

        """
        تقسيم النص العربي بدون تقطيع الحروف
        """

        words = text.split()

        if not words:
            return [""]

        lines = []

        current_line = ""

        dummy_img = Image.new("RGB", (10, 10))
        dummy_draw = ImageDraw.Draw(dummy_img)

        for word in words:

            test_line = f"{current_line} {word}".strip()

            shaped = test_line

            if RESHAPER_OK:
                shaped = arabic_reshaper.reshape(shaped)

            if BIDI_OK:
                shaped = get_display(shaped)

            bbox = dummy_draw.textbbox(
                (0, 0),
                shaped,
                font=font
            )

            width = bbox[2] - bbox[0]

            if width <= max_w:

                current_line = test_line

            else:

                if current_line:
                    lines.append(current_line)

                current_line = word

        if current_line:
            lines.append(current_line)

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

        glay = Image.new(
            "RGBA",
            img.size,
            (0, 0, 0, 0)
        )

        gd = ImageDraw.Draw(glay)

        r, g, b = color[:3]

        for off in [3, 6, 9]:

            gd.text(
                (x - off, y),
                text,
                font=font,
                fill=(r, g, b, 30)
            )

            gd.text(
                (x + off, y),
                text,
                font=font,
                fill=(r, g, b, 30)
            )

            gd.text(
                (x, y - off),
                text,
                font=font,
                fill=(r, g, b, 30)
            )

            gd.text(
                (x, y + off),
                text,
                font=font,
                fill=(r, g, b, 30)
            )

        img.alpha_composite(
            glay.filter(
                ImageFilter.GaussianBlur(12)
            )
        )

    def _highlight(
        self,
        draw,
        text,
        font,
        x,
        y
    ):

        bb = draw.textbbox(
            (x, y),
            text,
            font=font
        )

        pad = 10

        draw.rounded_rectangle(
            [
                bb[0] - pad,
                bb[1] - pad,
                bb[2] + pad,
                bb[3] + pad,
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

    def _style(self, t: str) -> dict:

        base = {

            "hook": dict(
                font=self.font_lg,
                text_color=(255, 255, 255, 255),
                glow_color=(220, 30, 30),
                y_pos=0.44,
                stroke_w=3,
                stroke_c=(0, 0, 0, 255),
                shadow=4
            ),

            "build": dict(
                font=self.font_md,
                text_color=(240, 240, 240, 255),
                glow_color=(80, 80, 220),
                y_pos=0.55,
                stroke_w=2,
                stroke_c=(0, 0, 0, 255),
                shadow=3
            ),

            "peak": dict(
                font=self.font_lg,
                text_color=(255, 215, 0, 255),
                glow_color=(255, 180, 0),
                y_pos=0.50,
                stroke_w=3,
                stroke_c=(80, 40, 0, 255),
                shadow=5
            ),

            "resolution": dict(
                font=self.font_md,
                text_color=(200, 230, 255, 255),
                glow_color=(40, 130, 255),
                y_pos=0.55,
                stroke_w=2,
                stroke_c=(0, 0, 0, 255),
                shadow=3
            ),

            "cta": dict(
                font=self.font_md,
                text_color=(255, 255, 255, 255),
                glow_color=(255, 255, 255),
                y_pos=0.73,
                stroke_w=2,
                stroke_c=(0, 0, 0, 255),
                shadow=3
            ),

            "main": dict(
                font=self.font_md,
                text_color=(255, 255, 255, 255),
                glow_color=(180, 180, 180),
                y_pos=0.55,
                stroke_w=2,
                stroke_c=(0, 0, 0, 255),
                shadow=3
            ),
        }

        return base.get(t, base["main"])
