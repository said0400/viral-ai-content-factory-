class SubtitleEngine:

    # ✅ استخدم خطوط ثابتة فقط (بدون VF)
    FONT_PATHS = [
        "engine/assets/fonts/NotoNaskhArabic-Bold.ttf",
        "engine/assets/fonts/Amiri-Bold.ttf",
        "engine/assets/fonts/Cairo-Bold.ttf",
        "engine/assets/fonts/Tajawal-Bold.ttf",
        "/usr/share/fonts/truetype/noto/NotoNaskhArabic-Bold.ttf",
        "/usr/share/fonts/truetype/noto/NotoSansArabic-Bold.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
    ]

    def __init__(self, video_width=1080, video_height=1920):
        self.w = video_width
        self.h = video_height

        self.temp_dir = Path(os.getenv("TEMP_DIR", "./temp"))
        self.sub_dir = self.temp_dir / "subtitles"
        self.sub_dir.mkdir(parents=True, exist_ok=True)

        self.font_size_lg = int(os.getenv("SUBTITLE_SIZE_LG", "84"))
        self.font_size_md = int(os.getenv("SUBTITLE_SIZE_MD", "68"))
        self.font_size_sm = int(os.getenv("SUBTITLE_SIZE_SM", "54"))

        self.enable_background = os.getenv("SUBTITLE_BACKGROUND", "false").lower() == "true"
        self.enable_glow = os.getenv("SUBTITLE_GLOW", "true").lower() == "true"
        self.text_width_ratio = float(os.getenv("SUBTITLE_WIDTH_RATIO", "0.86"))

        self.font_path = self._find_font()
        if not self.font_path:
            raise RuntimeError("❌ لم يُعثر على خط عربي!")

        self._init_reshaper()
        self._load_fonts()

        logger.info(f"📜 Using font: {Path(self.font_path).name}")

    # ---------------------------------------

    def _init_reshaper(self):
        self.reshaper = None
        if RESHAPER_OK:
            try:
                self.reshaper = arabic_reshaper.ArabicReshaper({
                    "delete_harakat": False,
                    "support_ligatures": True
                })
            except Exception:
                self.reshaper = None

    def _shape_arabic(self, text):
        if not text:
            return text

        if RESHAPER_OK:
            try:
                text = self.reshaper.reshape(text) if self.reshaper else arabic_reshaper.reshape(text)
            except Exception:
                pass

        if BIDI_OK:
            try:
                text = get_display(text)
            except Exception:
                pass

        return text

    # ---------------------------------------

    def _find_font(self):
        for path in self.FONT_PATHS:
            if Path(path).exists():
                return path
        return None

    def _load_fonts(self):
        self.font_lg = ImageFont.truetype(self.font_path, self.font_size_lg)
        self.font_md = ImageFont.truetype(self.font_path, self.font_size_md)
        self.font_sm = ImageFont.truetype(self.font_path, self.font_size_sm)

    # ---------------------------------------

    def _wrap_arabic(self, text, font, max_width):
        words = text.split()
        if not words:
            return [""]

        test_img = Image.new("RGB", (10, 10))
        test_draw = ImageDraw.Draw(test_img)

        lines = []
        current = []

        for word in words:
            trial = " ".join(current + [word])
            shaped = self._shape_arabic(trial)
            bbox = test_draw.textbbox((0, 0), shaped, font=font)
            width = bbox[2] - bbox[0]

            if current and width > max_width:
                lines.append(" ".join(current))
                current = [word]
            else:
                current.append(word)

        if current:
            lines.append(" ".join(current))

        # ✅ تشكيل مرة واحدة لكل سطر
        return [self._shape_arabic(line) for line in lines]

    # ---------------------------------------

    def _render_png(self, scene, idx):
        text = scene.get("text", "").strip()
        scene_type = scene.get("type", "main")

        output = str(self.sub_dir / f"sub_{idx:03d}.png")

        cfg = self._get_style(scene_type, text)
        font = cfg["font"]

        img = Image.new("RGBA", (self.w, self.h), (0, 0, 0, 0))
        draw = ImageDraw.Draw(img)

        max_width = int(self.w * self.text_width_ratio)
        lines = self._wrap_arabic(text, font, max_width)

        if not lines or not lines[0]:
            img.save(output)
            return output

        ascent, descent = font.getmetrics()
        line_height = ascent + descent + 20

        total_height = len(lines) * line_height
        start_y = int(self.h * cfg["y_pos"]) - total_height // 2

        for i, line in enumerate(lines):
            y = start_y + i * line_height

            bbox = draw.textbbox((0, 0), line, font=font)
            width = bbox[2] - bbox[0]
            x = (self.w - width) // 2

            if self.enable_glow:
                self._draw_glow(img, line, font, x, y, cfg["glow_color"])

            draw.text(
                (x, y),
                line,
                font=font,
                fill=cfg["text_color"],
                stroke_width=cfg["stroke_w"],
                stroke_fill=cfg["stroke_c"],
            )

        img.save(output)
        return output

    # ---------------------------------------

    def _draw_glow(self, img, text, font, x, y, color):
        glow = Image.new("RGBA", img.size, (0, 0, 0, 0))
        gd = ImageDraw.Draw(glow)

        r, g, b = color[:3]

        for dx in range(-4, 5, 2):
            for dy in range(-4, 5, 2):
                gd.text((x + dx, y + dy), text, font=font, fill=(r, g, b, 40))

        glow = glow.filter(ImageFilter.GaussianBlur(10))
        img.alpha_composite(glow)

    # ---------------------------------------

    def _get_style(self, scene_type, text=""):
        word_count = len(text.split()) if text else 0

        if scene_type in ("hook", "peak"):
            font = self.font_lg if word_count <= 6 else self.font_md
        elif word_count > 10:
            font = self.font_sm
        else:
            font = self.font_md

        return dict(
            font=font,
            text_color=(255, 255, 255, 255),
            glow_color=(255, 80, 80),
            y_pos=0.55,
            stroke_w=3,
            stroke_c=(0, 0, 0, 255),
        )
