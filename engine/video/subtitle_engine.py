"""
Subtitle Engine
arabic_reshaper + bidi + Pillow → PNG overlays → FFmpeg
لا drawtext مطلقاً لأنه يكسر العربية
"""

import os
import re

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
        "engine/assets/fonts/Tajawal-ExtraBold.ttf",
        "engine/assets/fonts/Changa-ExtraBold.ttf",
        "engine/assets/fonts/NotoNaskhArabic-Bold.ttf",
    ]
    SYSTEM_FONTS = [
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
        "/usr/share/fonts/truetype/freefont/FreeSansBold.ttf",
        "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
        "/usr/share/fonts/truetype/noto/NotoSans-Bold.ttf",
    ]

    def __init__(self, video_width: int = 1080, video_height: int = 1920):
        self.w = video_width
        self.h = video_height
        self.temp_dir = Path(os.getenv("TEMP_DIR", "./temp"))
        self.sub_dir = self.temp_dir / "subtitles"
        self.sub_dir.mkdir(parents=True, exist_ok=True)
        self.font_lg = self._load_font(84)
        self.font_md = self._load_font(68)
        self.font_sm = self._load_font(54)

    def _load_font(self, size: int) -> ImageFont.FreeTypeFont:
        for p in self.FONT_PATHS + self.SYSTEM_FONTS:
            if os.path.exists(p):
                try:
                    return ImageFont.truetype(p, size)
                except Exception:
                    continue
        try:
            return ImageFont.load_default(size=size)
        except Exception:
            return ImageFont.load_default()

    def reshape(self, text: str) -> str:
        try:
            if RESHAPER_OK:
                text = arabic_reshaper.reshape(text)
            return get_display(text)
        except Exception:
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
        emphasis = [e.get("word", "") for e in scene.get("emphasis", [])]
        out = str(self.sub_dir / f"sub_{idx:03d}.png")

        cfg = self._style(s_type)
        font = cfg["font"]
        tc   = cfg["text_color"]
        gc   = cfg["glow_color"]
        ypos = cfg["y_pos"]
        sw   = cfg["stroke_w"]
        sc   = cfg["stroke_c"]
        shd  = cfg["shadow"]

        img  = Image.new("RGBA", (self.w, self.h), (0, 0, 0, 0))
        draw = ImageDraw.Draw(img)

        display = self.reshape(text)
        lines   = self._wrap(display, font, int(self.w * 0.86))

        lh = font.size + 20
        total_h = len(lines) * lh
        start_y = int(self.h * ypos) - total_h // 2

        for li, line in enumerate(lines):
            ly = start_y + li * lh
            bb = draw.textbbox((0, 0), line, font=font)
            lw = bb[2] - bb[0]
            lx = (self.w - lw) // 2

            self._glow(img, line, font, lx, ly, gc)
            draw.text((lx + shd, ly + shd), line, font=font, fill=(0, 0, 0, 160))

            is_emp = any(self.reshape(w) in line for w in emphasis if w)
            if is_emp:
                self._highlight(draw, line, font, lx, ly)
            else:
                draw.text(
                    (lx, ly), line, font=font, fill=tc,
                    stroke_width=sw, stroke_fill=sc,
                )

        img.save(out, "PNG")
        return out

    def _glow(self, img, text, font, x, y, color):
        glay = Image.new("RGBA", img.size, (0, 0, 0, 0))
        gd   = ImageDraw.Draw(glay)
        r, g, b = color[:3]
        for off in [3, 6, 9]:
            gd.text((x - off, y), text, font=font, fill=(r, g, b, 30))
            gd.text((x + off, y), text, font=font, fill=(r, g, b, 30))
            gd.text((x, y - off), text, font=font, fill=(r, g, b, 30))
            gd.text((x, y + off), text, font=font, fill=(r, g, b, 30))
        img.alpha_composite(glay.filter(ImageFilter.GaussianBlur(12)))

    def _highlight(self, draw, text, font, x, y):
        bb  = draw.textbbox((x, y), text, font=font)
        pad = 10
        draw.rounded_rectangle(
            [bb[0]-pad, bb[1]-pad, bb[2]+pad, bb[3]+pad],
            radius=8, fill=(255, 200, 0, 210),
        )
        draw.text((x, y), text, font=font, fill=(15, 15, 15, 255),
                  stroke_width=1, stroke_fill=(0, 0, 0, 180))

    def _wrap(self, text: str, font, max_w: int) -> list:
        words = text.split()
        if not words:
            return [""]
        dummy = Image.new("RGB", (1, 1))
        dd    = ImageDraw.Draw(dummy)
        lines, cur = [], []
        for word in words:
            test = " ".join(cur + [word])
            bb = dd.textbbox((0, 0), test, font=font)
            if bb[2] - bb[0] <= max_w:
                cur.append(word)
            else:
                if cur:
                    lines.append(" ".join(cur))
                cur = [word]
        if cur:
            lines.append(" ".join(cur))
        return lines

    def _style(self, t: str) -> dict:
        base = {
            "hook":       dict(font=self.font_lg, text_color=(255,255,255,255), glow_color=(220,30,30),   y_pos=0.44, stroke_w=3, stroke_c=(0,0,0,255),     shadow=4),
            "build":      dict(font=self.font_md, text_color=(240,240,240,255), glow_color=(80,80,220),   y_pos=0.55, stroke_w=2, stroke_c=(0,0,0,255),     shadow=3),
            "peak":       dict(font=self.font_lg, text_color=(255,215,0,255),   glow_color=(255,180,0),   y_pos=0.50, stroke_w=3, stroke_c=(80,40,0,255),   shadow=5),
            "resolution": dict(font=self.font_md, text_color=(200,230,255,255), glow_color=(40,130,255),  y_pos=0.55, stroke_w=2, stroke_c=(0,0,0,255),     shadow=3),
            "cta":        dict(font=self.font_md, text_color=(255,255,255,255), glow_color=(255,255,255), y_pos=0.73, stroke_w=2, stroke_c=(0,0,0,255),     shadow=3),
            "main":       dict(font=self.font_md, text_color=(255,255,255,255), glow_color=(180,180,180), y_pos=0.55, stroke_w=2, stroke_c=(0,0,0,255),     shadow=3),
        }
        return base.get(t, base["main"])
