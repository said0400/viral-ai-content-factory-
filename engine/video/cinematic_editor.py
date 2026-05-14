"""
🎬 Cinematic Editor — التحرير السينمائي للفيديو
═══════════════════════════════════════════════════════════════
محرك التحرير الرئيسي يجمع:
  • جلب الفيديوهات (Pexels + Pixabay)
  • معالجة الـ clips (scale, crop, zoom, shake)
  • تطبيق Transitions
  • إضافة الترجمة (SRT + PNG overlays)
  • دمج الصوت والتدرج اللوني

الإصلاحات:
  ✓ Pexels + Pixabay (بدلاً من Pexels فقط)
  ✓ مسح cache قبل كل تشغيل (تنويع الفيديوهات)
  ✓ 50+ كلمة بحث + visual_prompt من AI
  ✓ SRT + batched overlay (يحل مشكلة FFmpeg limit)
  ✓ Loop قبل Trim (يمنع المشاهد القصيرة)
  ✓ دعم quality من main.py

ضع في: engine/video/cinematic_editor.py
═══════════════════════════════════════════════════════════════
"""

import os
import time
import random
import shutil
import logging
import subprocess
import requests
from pathlib import Path
from typing import Optional, List, Dict, Tuple

from engine.video.effects_engine    import EffectsEngine
from engine.video.transition_engine import TransitionEngine
from engine.video.subtitle_engine   import SubtitleEngine

logger = logging.getLogger(__name__)


class CinematicEditor:
    """محرك التحرير السينمائي الرئيسي."""

    # ════════════════════════════════════════════════════════════════
    #                    قواميس البحث
    # ════════════════════════════════════════════════════════════════
    KEYWORDS = [
        # درامي / سينمائي
        "dark cinematic dramatic",
        "silhouette dramatic sunset",
        "cinematic night city",
        "dramatic sky clouds",
        "moody dark forest",
        "cinematic desert landscape",
        "dark rain dramatic",
        "dramatic lightning storm",
        "cinematic mountain fog",
        "dark ocean waves",
        # شخصيات
        "person walking alone",
        "man standing alone dramatic",
        "silhouette person sunset",
        "person thinking alone",
        "man running dramatic",
        "person looking window rain",
        "man praying dramatic light",
        "silhouette crowd dark",
        # طبيعة
        "fire flame dark dramatic",
        "smoke light cinematic",
        "stars milky way dark",
        "sunrise golden mountain",
        "waves ocean slow motion",
        "rain drops dark",
        "snow falling dark",
        "desert dunes sunset",
        "waterfall mist dramatic",
        "fog dark forest",
        # حضري
        "urban night bokeh",
        "city lights night",
        "empty road night",
        "abandoned building dark",
        "dark alley night",
        "bridge night cinematic",
        "train night dramatic",
        "rooftop city night",
        # مجردة / فلسفية
        "candle flame dark",
        "clock ticking dramatic",
        "book pages turning",
        "dark water reflection",
        "mirror reflection dramatic",
        "hands dramatic light",
        "eye close up dramatic",
        "shadow dramatic light",
        # حركة
        "slow motion dramatic",
        "epic slow motion",
        "cinematic slow motion nature",
        "dramatic slow motion water",
        "timelapse city night",
        "timelapse sky dramatic",
    ]

    ARABIC_HINTS = {
        "ألم":    ["dark rain dramatic", "person looking window rain"],
        "نجاح":   ["sunrise golden mountain", "person running dramatic"],
        "وحيد":   ["person walking alone", "silhouette person sunset"],
        "ليل":    ["urban night bokeh", "city lights night"],
        "نار":    ["fire flame dark dramatic", "smoke light cinematic"],
        "أمل":    ["sunrise golden mountain", "waterfall mist dramatic"],
        "مطر":    ["rain drops dark", "person looking window rain"],
        "قوة":    ["silhouette dramatic sunset", "man standing alone dramatic"],
        "سماء":   ["stars milky way dark", "dramatic sky clouds"],
        "طريق":   ["empty road night", "cinematic desert landscape"],
        "موت":    ["dark ocean waves", "candle flame dark"],
        "خوف":    ["dark alley night", "shadow dramatic light"],
        "حب":     ["candle flame dark", "hands dramatic light"],
        "حزن":    ["rain drops dark", "dark rain dramatic"],
        "صبر":    ["clock ticking dramatic", "person thinking alone"],
        "ظلام":   ["dark forest", "abandoned building dark"],
        "نور":    ["candle flame dark", "dramatic lightning storm"],
        "حرب":    ["dramatic lightning storm", "smoke light cinematic"],
        "سلام":   ["waterfall mist dramatic", "fog dark forest"],
        "عقل":    ["book pages turning", "dark water reflection"],
        "قلب":    ["hands dramatic light", "dark water reflection"],
        "وقت":    ["clock ticking dramatic", "timelapse city night"],
        "صمت":    ["fog dark forest", "empty road night"],
    }

    ZOOM_MAP = {
        "hook":       "punch_zoom",
        "build":      "slow_zoom_in",
        "peak":       "punch_zoom",
        "resolution": "slow_zoom_out",
        "cta":        "drift_right",
        "main":       "slow_zoom_in",
    }

    SCENE_TRANSITIONS = {
        "hook":       ["flash_black", "zoom_burst"],
        "peak":       ["zoom_burst", "flash_black"],
        "build":      ["cross_dissolve", "smooth_fade"],
        "resolution": ["cross_dissolve", "fade_black"],
        "cta":        ["fade_black", "smooth_fade"],
        "main":       ["cross_dissolve", "smooth_fade"],
    }

    # ─── إعدادات الجودة ───────────────────────────────────────────
    QUALITY_PRESETS = {
        "medium": {"crf": 23, "preset": "fast",      "audio_bitrate": "128k"},
        "high":   {"crf": 19, "preset": "medium",    "audio_bitrate": "192k"},
        "ultra":  {"crf": 17, "preset": "slow",      "audio_bitrate": "256k"},
    }

    # ════════════════════════════════════════════════════════════════
    def __init__(self):
        """تهيئة محرك التحرير."""
        self.w = int(os.getenv("VIDEO_WIDTH",  "1080"))
        self.h = int(os.getenv("VIDEO_HEIGHT", "1920"))
        self.fps = int(os.getenv("VIDEO_FPS",  "30"))
        self.quality = os.getenv("VIDEO_QUALITY", "high")

        # المفاتيح
        self.pexels_key = os.getenv("PEXELS_API_KEY", "")
        self.pixabay_key = os.getenv("PIXABAY_API_KEY", "")

        # المسارات
        self.temp_dir = Path(os.getenv("TEMP_DIR", "./temp"))
        self.footage_dir = self.temp_dir / "footage"
        self.clips_dir = self.temp_dir / "clips"
        for d in [self.temp_dir, self.footage_dir, self.clips_dir]:
            d.mkdir(parents=True, exist_ok=True)

        # المحركات الفرعية
        self.fx = EffectsEngine(self.w, self.h)
        self.trans = TransitionEngine(self.w, self.h)
        self.subs = SubtitleEngine(self.w, self.h)

        # مسح footage القديم
        self._clear_old_footage()

        logger.info(
            f"🎬 CinematicEditor | {self.w}x{self.h}@{self.fps}fps | "
            f"Quality: {self.quality}"
        )

    def _clear_old_footage(self) -> None:
        """مسح footage القديم لضمان تنويع الفيديوهات."""
        try:
            count = 0
            if self.footage_dir.exists():
                for f in self.footage_dir.glob("footage_*.mp4"):
                    f.unlink()
                    count += 1
                for f in self.footage_dir.glob("ph_*.mp4"):
                    f.unlink()
                    count += 1
            if count:
                logger.info(f"🗑️ تم مسح {count} ملف footage قديم")
        except Exception as e:
            logger.warning(f"⚠ فشل المسح: {e}")

    # ════════════════════════════════════════════════════════════════
    #                    الدالة الرئيسية
    # ════════════════════════════════════════════════════════════════
    def build_video(
        self,
        script: dict,
        audio_path: str,
        subtitle_data: list,
        output_path: str,
    ) -> str:
        """بناء الفيديو الكامل من السكربت."""
        scenes = script.get("scenes", [])
        total_dur = float(script.get("duration_estimate", 45.0))

        if not scenes:
            raise ValueError("❌ لا توجد مشاهد في السكربت")

        logger.info(f"🎬 بناء فيديو | {len(scenes)} مشهد | {total_dur:.1f}s")

        # 1️⃣ جلب الفيديوهات
        logger.info("► جلب الفيديوهات...")
        raws = self._fetch_footage(scenes)

        # 2️⃣ معالجة الـ clips
        logger.info("► معالجة الـ clips...")
        processed = self._process_clips(raws, scenes)

        # 3️⃣ تجميع مع transitions
        logger.info("► تجميع مع transitions...")
        assembled = self._assemble(processed, scenes, total_dur)

        # 4️⃣ إضافة الترجمة
        logger.info("► إضافة الترجمة...")
        subtitled = self._overlay_subs(assembled, subtitle_data, scenes)

        # 5️⃣ دمج الصوت
        logger.info("► دمج الصوت...")
        muxed = self._mux(subtitled, audio_path)

        # 6️⃣ التدرج اللوني النهائي
        logger.info("► تدرج الألوان...")
        self._grade(muxed, output_path)

        logger.info(f"✓ اكتمل الفيديو: {Path(output_path).name}")
        return output_path

    # ════════════════════════════════════════════════════════════════
    #                    جلب الفيديوهات
    # ════════════════════════════════════════════════════════════════
    def _fetch_footage(self, scenes: list) -> list:
        """جلب فيديوهات لكل مشهد."""
        used_kws = set()
        used_urls = set()
        clips = []

        for i, scene in enumerate(scenes):
            kw = self._pick_kw(scene, used_kws)
            used_kws.add(kw)
            clip = self._download(kw, i, used_urls)
            clips.append(clip)
            logger.debug(f"  [{i+1}/{len(scenes)}] {kw[:50]}")

        return clips

    def _pick_kw(self, scene: dict, used: set) -> str:
        """اختيار كلمة بحث ذكية للمشهد."""
        # 1. visual_prompt من AI (أولوية عالية)
        vp = scene.get("visual_prompt", "").strip()
        if vp and len(vp) > 5 and vp not in used:
            return vp

        # 2. ARABIC_HINTS
        text = scene.get("text", "")
        for hint, kw_list in self.ARABIC_HINTS.items():
            if hint in text:
                for kw in kw_list:
                    if kw not in used:
                        return kw

        # 3. KEYWORDS عشوائية
        avail = [k for k in self.KEYWORDS if k not in used]
        if avail:
            return random.choice(avail)

        # 4. أي كلمة (لو استُنفد كل شيء)
        return random.choice(self.KEYWORDS)

    def _download(self, keyword: str, idx: int, used_urls: set) -> str:
        """تحميل فيديو من Pexels أو Pixabay."""
        ts = int(time.time() * 1000) % 100000
        out = str(self.footage_dir / f"footage_{idx:03d}_{ts}.mp4")

        # 1️⃣ جرب Pexels أولاً
        if self.pexels_key:
            result = self._download_from_pexels(keyword, out, used_urls)
            if result:
                return result

        # 2️⃣ Pixabay كـ fallback
        if self.pixabay_key:
            result = self._download_from_pixabay(keyword, out, used_urls)
            if result:
                return result

        # 3️⃣ Placeholder
        logger.warning(f"⚠ لم يتم العثور على فيديو لـ '{keyword}' → placeholder")
        return self._placeholder(idx)

    def _download_from_pexels(
        self,
        keyword: str,
        out: str,
        used_urls: set,
    ) -> Optional[str]:
        """تحميل من Pexels."""
        try:
            page = random.randint(1, 4)
            r = requests.get(
                "https://api.pexels.com/videos/search",
                headers={"Authorization": self.pexels_key},
                params={
                    "query": keyword,
                    "per_page": 15,
                    "orientation": "portrait",
                    "page": page,
                    "size": "medium",
                },
                timeout=20,
            )

            if r.status_code != 200:
                logger.debug(f"Pexels HTTP {r.status_code}")
                return None

            videos = r.json().get("videos", [])

            if not videos:
                # محاولة بدون page
                r2 = requests.get(
                    "https://api.pexels.com/videos/search",
                    headers={"Authorization": self.pexels_key},
                    params={
                        "query": keyword,
                        "per_page": 10,
                        "orientation": "portrait",
                    },
                    timeout=20,
                )
                videos = r2.json().get("videos", []) if r2.ok else []

            if not videos:
                return None

            # فلترة portrait
            portrait_videos = [
                v for v in videos
                if any(
                    vf.get("height", 0) >= vf.get("width", 1)
                    for vf in v.get("video_files", [])
                )
            ]
            pool = portrait_videos if portrait_videos else videos

            # محاولة العثور على فيديو غير مستخدم
            target = None
            for _ in range(5):
                video = random.choice(pool)
                target = self._best_file(video.get("video_files", []))
                if target and target["link"] not in used_urls:
                    break

            if not target:
                return None

            used_urls.add(target["link"])
            return self._download_file(target["link"], out)

        except Exception as e:
            logger.debug(f"Pexels error: {e}")
            return None

    def _download_from_pixabay(
        self,
        keyword: str,
        out: str,
        used_urls: set,
    ) -> Optional[str]:
        """تحميل من Pixabay (احتياطي)."""
        try:
            r = requests.get(
                "https://pixabay.com/api/videos/",
                params={
                    "key": self.pixabay_key,
                    "q": keyword,
                    "video_type": "film",
                    "orientation": "vertical",
                    "per_page": 15,
                },
                timeout=20,
            )

            if r.status_code != 200:
                logger.debug(f"Pixabay HTTP {r.status_code}")
                return None

            hits = r.json().get("hits", [])
            if not hits:
                return None

            # محاولة العثور على فيديو غير مستخدم
            for _ in range(5):
                video = random.choice(hits)
                videos = video.get("videos", {})

                # اختر أفضل جودة
                for size in ("large", "medium", "small"):
                    if size in videos and videos[size].get("url"):
                        url = videos[size]["url"]
                        if url not in used_urls:
                            used_urls.add(url)
                            return self._download_file(url, out)

            return None

        except Exception as e:
            logger.debug(f"Pixabay error: {e}")
            return None

    def _download_file(self, url: str, out: str) -> Optional[str]:
        """تحميل ملف فيديو."""
        try:
            dl = requests.get(url, stream=True, timeout=40)
            dl.raise_for_status()

            with open(out, "wb") as f:
                for chunk in dl.iter_content(8192):
                    if chunk:
                        f.write(chunk)

            if Path(out).exists() and Path(out).stat().st_size > 10000:
                return out

            Path(out).unlink(missing_ok=True)
            return None

        except Exception as e:
            logger.debug(f"Download error: {e}")
            Path(out).unlink(missing_ok=True)
            return None

    def _best_file(self, files: list) -> Optional[dict]:
        """اختيار أفضل ملف فيديو."""
        # portrait + HD
        for vf in files:
            if (vf.get("height", 0) >= vf.get("width", 1)
                    and vf.get("quality") in ("hd", "sd")):
                return vf
        # أي portrait
        for vf in files:
            if vf.get("height", 0) >= vf.get("width", 1):
                return vf
        # أي HD
        for vf in files:
            if vf.get("quality") in ("hd", "sd"):
                return vf
        return files[0] if files else None

    def _placeholder(self, idx: int) -> str:
        """توليد فيديو خلفية بسيط (placeholder)."""
        out = str(self.footage_dir / f"ph_{idx:03d}.mp4")
        colors = ["0x0a0a1a", "0x0d0d1e", "0x080818", "0x0a0a0a", "0x05050f"]
        c = colors[idx % len(colors)]

        try:
            subprocess.run(
                ["ffmpeg", "-y", "-f", "lavfi",
                 "-i", f"color=c={c}:s={self.w}x{self.h}:r={self.fps}",
                 "-t", "8",
                 "-c:v", "libx264", "-preset", "ultrafast", "-crf", "28",
                 out],
                capture_output=True,
                timeout=30,
                check=True,
            )
        except Exception:
            # fallback أسود
            subprocess.run(
                ["ffmpeg", "-y", "-f", "lavfi",
                 "-i", f"color=c=black:s={self.w}x{self.h}:r={self.fps}",
                 "-t", "8",
                 "-c:v", "libx264", "-preset", "ultrafast", "-crf", "28",
                 out],
                capture_output=True,
                timeout=30,
            )
        return out
          # ════════════════════════════════════════════════════════════════
    #                    معالجة الـ Clips
    # ════════════════════════════════════════════════════════════════
    def _process_clips(self, raws: list, scenes: list) -> list:
        """معالجة كل clip: scale, loop, trim, zoom, shake."""
        processed = []

        for i, (raw, scene) in enumerate(zip(raws, scenes)):
            st = scene.get("type", "main")
            dur = scene.get("duration", 3.0) + scene.get("pause_after", 0.3)
            zoom = self.ZOOM_MAP.get(st, "slow_zoom_in")

            # مسارات الملفات الوسيطة
            sc = str(self.clips_dir / f"sc_{i:03d}.mp4")  # scaled
            lp = str(self.clips_dir / f"lp_{i:03d}.mp4")  # looped
            tr = str(self.clips_dir / f"tr_{i:03d}.mp4")  # trimmed
            zm = str(self.clips_dir / f"zm_{i:03d}.mp4")  # zoomed

            try:
                # 1. تحجيم وقص للأبعاد المطلوبة (1080x1920)
                self.fx.scale_and_crop(raw, sc)

                # 2. Loop قبل Trim (يضمن مدة كافية)
                self.fx.loop_clip_to_duration(sc, lp, dur + 1.0)

                # 3. Trim للمدة المطلوبة
                self.fx.trim_clip(lp, tr, 0.0, dur)

                # 4. تطبيق Zoom Effect
                self.fx.apply_zoom_effect(tr, zm, zoom, dur)

                # 5. Shake للمشاهد المهمة (hook, peak)
                if st in ("hook", "peak"):
                    sh = str(self.clips_dir / f"sh_{i:03d}.mp4")
                    self.fx.apply_smooth_shake(zm, sh, 2.0)
                    processed.append(sh)
                else:
                    processed.append(zm)

            except Exception as e:
                logger.warning(f"⚠ خطأ في معالجة clip {i}: {e}")
                # استخدم الـ raw كـ fallback
                processed.append(raw)

        return processed

    # ════════════════════════════════════════════════════════════════
    #                    تجميع الـ Clips مع Transitions
    # ════════════════════════════════════════════════════════════════
    def _assemble(self, clips: list, scenes: list, total_dur: float) -> str:
        """تجميع الـ clips مع تطبيق الانتقالات."""
        out = str(self.temp_dir / "assembled_raw.mp4")

        if not clips:
            raise ValueError("❌ لا توجد clips للتجميع")

        if len(clips) == 1:
            shutil.copy(clips[0], out)
            return out

        current = clips[0]
        for i in range(1, len(clips)):
            scene_type = scenes[i].get("type", "main") if i < len(scenes) else "main"

            # اختيار transition عشوائي من الأنواع المناسبة
            available_trans = self.SCENE_TRANSITIONS.get(
                scene_type,
                ["cross_dissolve"]
            )
            transition = random.choice(available_trans)

            nxt = str(self.temp_dir / f"assem_{i:03d}.mp4")

            try:
                self.trans.apply_transition(
                    current, clips[i], nxt, transition, 0.18
                )
                current = nxt
            except Exception as e:
                logger.warning(f"⚠ فشل transition {i}: {e}")
                # في حالة الفشل، استخدم الـ clip التالي مباشرة
                current = clips[i]

        shutil.copy(current, out)
        return out

    # ════════════════════════════════════════════════════════════════
    #                    إضافة الترجمة
    # ════════════════════════════════════════════════════════════════
    def _overlay_subs(self, video: str, sub_data: list, scenes: list) -> str:
        """إضافة الترجمة على الفيديو (PNG overlays)."""
        out = str(self.temp_dir / "subtitled.mp4")

        if not sub_data:
            logger.warning("⚠ لا توجد بيانات ترجمة")
            shutil.copy(video, out)
            return out

        # حفظ SRT للاستخدام المستقبلي (اختياري)
        srt_path = str(self.temp_dir / "subtitles.srt")
        try:
            self._write_srt(srt_path, sub_data, scenes)
        except Exception as e:
            logger.debug(f"تجاهل خطأ SRT: {e}")

        # تطبيق PNG overlays في batches
        return self._overlay_png_batched(video, sub_data, scenes, out)

    def _write_srt(self, srt_path: str, sub_data: list, scenes: list) -> None:
        """كتابة ملف SRT للترجمة."""
        def fmt_time(s: float) -> str:
            h = int(s // 3600)
            m = int((s % 3600) // 60)
            ss = int(s % 60)
            ms = int((s % 1) * 1000)
            return f"{h:02}:{m:02}:{ss:02},{ms:03}"

        lines = []
        t = 0.0

        for i, (_, scene) in enumerate(sub_data):
            dur = scene.get("duration", 3.0)
            pause = scene.get("pause_after", 0.3)

            lines.append(str(i + 1))
            lines.append(f"{fmt_time(t)} --> {fmt_time(t + dur)}")
            lines.append(scene.get("text", ""))
            lines.append("")
            t += dur + pause

        with open(srt_path, "w", encoding="utf-8") as f:
            f.write("\n".join(lines))

    def _overlay_png_batched(
        self,
        video: str,
        sub_data: list,
        scenes: list,
        out: str,
    ) -> str:
        """تطبيق PNG overlays في batches لتجنب FFmpeg limit."""
        BATCH_SIZE = 6
        current = video
        cumulative_time = 0.0

        # الحصول على إعدادات الجودة
        quality_cfg = self.QUALITY_PRESETS.get(
            self.quality, self.QUALITY_PRESETS["high"]
        )

        for batch_idx, batch_start in enumerate(range(0, len(sub_data), BATCH_SIZE)):
            batch = sub_data[batch_start:batch_start + BATCH_SIZE]
            batch_time = cumulative_time
            tmp_out = str(self.temp_dir / f"sub_batch_{batch_idx:03d}.mp4")

            # بناء inputs
            inputs = ["-i", current]
            for png, _ in batch:
                inputs += ["-i", png]

            # بناء filter chain
            filter_parts = []
            cur_stream = "0:v"

            for j, (_, scene) in enumerate(batch):
                dur = scene.get("duration", 3.0)
                pause = scene.get("pause_after", 0.3)
                t_end = batch_time + dur

                next_label = f"vs{batch_start + j}"
                filter_parts.append(
                    f"[{cur_stream}][{j+1}:v]"
                    f"overlay=0:0:enable='between(t,{batch_time:.2f},{t_end:.2f})'"
                    f"[{next_label}]"
                )
                cur_stream = next_label
                batch_time += dur + pause

            cmd = (
                ["ffmpeg", "-y", "-loglevel", "error"]
                + inputs
                + [
                    "-filter_complex", ";".join(filter_parts),
                    "-map", f"[{cur_stream}]",
                    "-c:v", "libx264",
                    "-preset", quality_cfg["preset"],
                    "-crf", str(quality_cfg["crf"]),
                    "-pix_fmt", "yuv420p",
                    "-an",
                    tmp_out,
                ]
            )

            try:
                result = subprocess.run(
                    cmd, capture_output=True, timeout=180
                )
                if result.returncode == 0 and Path(tmp_out).exists():
                    current = tmp_out
                else:
                    err = result.stderr.decode("utf-8", errors="ignore")[:200]
                    logger.warning(f"⚠ batch {batch_idx} فشل: {err}")
            except subprocess.TimeoutExpired:
                logger.warning(f"⚠ batch {batch_idx} timeout")
            except Exception as e:
                logger.warning(f"⚠ batch {batch_idx} error: {e}")

            # تحديث الوقت التراكمي
            for _, scene in batch:
                cumulative_time += (
                    scene.get("duration", 3.0) + scene.get("pause_after", 0.3)
                )

        # نسخ الناتج النهائي
        if current != video:
            shutil.copy(current, out)
        else:
            shutil.copy(video, out)

        return out

    # ════════════════════════════════════════════════════════════════
    #                    دمج الصوت
    # ════════════════════════════════════════════════════════════════
    def _mux(self, video: str, audio: str) -> str:
        """دمج الصوت مع الفيديو."""
        out = str(self.temp_dir / "muxed.mp4")
        quality_cfg = self.QUALITY_PRESETS.get(
            self.quality, self.QUALITY_PRESETS["high"]
        )

        try:
            subprocess.run(
                [
                    "ffmpeg", "-y", "-loglevel", "error",
                    "-i", video,
                    "-i", audio,
                    "-map", "0:v:0",
                    "-map", "1:a:0",
                    "-c:v", "copy",
                    "-c:a", "aac",
                    "-b:a", quality_cfg["audio_bitrate"],
                    "-shortest",
                    out,
                ],
                check=True,
                capture_output=True,
                timeout=120,
            )
        except subprocess.CalledProcessError as e:
            err = e.stderr.decode("utf-8", errors="ignore")[:200]
            logger.error(f"❌ فشل دمج الصوت: {err}")
            # محاولة re-encode بالفيديو
            self._mux_with_reencode(video, audio, out)

        return out

    def _mux_with_reencode(self, video: str, audio: str, out: str) -> str:
        """دمج مع re-encode (fallback عند فشل copy)."""
        quality_cfg = self.QUALITY_PRESETS.get(
            self.quality, self.QUALITY_PRESETS["high"]
        )

        try:
            subprocess.run(
                [
                    "ffmpeg", "-y", "-loglevel", "error",
                    "-i", video,
                    "-i", audio,
                    "-map", "0:v:0",
                    "-map", "1:a:0",
                    "-c:v", "libx264",
                    "-preset", quality_cfg["preset"],
                    "-crf", str(quality_cfg["crf"]),
                    "-c:a", "aac",
                    "-b:a", quality_cfg["audio_bitrate"],
                    "-shortest",
                    out,
                ],
                capture_output=True,
                timeout=300,
            )
        except Exception as e:
            logger.error(f"❌ فشل re-encode: {e}")
        return out

    # ════════════════════════════════════════════════════════════════
    #                    التدرج اللوني
    # ════════════════════════════════════════════════════════════════
    def _grade(self, inp: str, out: str) -> str:
        """تطبيق التدرج اللوني السينمائي + letterbox."""
        graded = str(self.temp_dir / "graded.mp4")

        try:
            self.fx.apply_cinematic_grade(inp, graded)
        except Exception as e:
            logger.warning(f"⚠ فشل التدرج اللوني: {e}")
            shutil.copy(inp, graded)

        try:
            self.fx.add_letterbox(graded, out)
        except Exception as e:
            logger.warning(f"⚠ فشل letterbox: {e}")
            shutil.copy(graded, out)

        return out

    # ════════════════════════════════════════════════════════════════
    #                    دوال مساعدة
    # ════════════════════════════════════════════════════════════════
    def cleanup_temp_files(self) -> None:
        """تنظيف الملفات المؤقتة."""
        try:
            count = 0
            patterns = [
                "assem_*.mp4", "sub_batch_*.mp4", "subtitles.srt",
                "muxed.mp4", "graded.mp4", "subtitled.mp4",
                "assembled_raw.mp4",
            ]

            for pattern in patterns:
                for f in self.temp_dir.glob(pattern):
                    f.unlink(missing_ok=True)
                    count += 1

            for f in self.clips_dir.glob("*.mp4"):
                f.unlink(missing_ok=True)
                count += 1

            logger.info(f"🧹 تم تنظيف {count} ملف مؤقت")
        except Exception as e:
            logger.warning(f"⚠ فشل التنظيف: {e}")

    def get_video_info(self, video_path: str) -> dict:
        """الحصول على معلومات الفيديو."""
        try:
            import json as json_lib
            result = subprocess.run(
                [
                    "ffprobe", "-v", "quiet",
                    "-print_format", "json",
                    "-show_format", "-show_streams",
                    video_path,
                ],
                capture_output=True,
                text=True,
                timeout=30,
                check=True,
            )
            data = json_lib.loads(result.stdout)

            video_stream = next(
                (s for s in data.get("streams", []) if s["codec_type"] == "video"),
                None,
            )

            return {
                "duration": float(data.get("format", {}).get("duration", 0)),
                "width": video_stream.get("width") if video_stream else 0,
                "height": video_stream.get("height") if video_stream else 0,
                "fps": eval(video_stream.get("avg_frame_rate", "0/1")) if video_stream else 0,
                "size_mb": Path(video_path).stat().st_size / (1024 * 1024),
            }
        except Exception as e:
            logger.error(f"❌ فشل قراءة معلومات الفيديو: {e}")
            return {}


# ════════════════════════════════════════════════════════════════════════
#                    اختبار سريع
# ════════════════════════════════════════════════════════════════════════
if __name__ == "__main__":
    editor = CinematicEditor()
    print(f"✓ CinematicEditor جاهز")
    print(f"  Dimensions: {editor.w}x{editor.h}")
    print(f"  FPS: {editor.fps}")
    print(f"  Quality: {editor.quality}")
    print(f"  Pexels: {'✓' if editor.pexels_key else '✗'}")
    print(f"  Pixabay: {'✓' if editor.pixabay_key else '✗'}")
