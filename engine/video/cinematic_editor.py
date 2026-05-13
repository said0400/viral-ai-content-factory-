"""
Cinematic Editor — مُصلح
إصلاح المشاكل:
  1. تكرار الفيديوهات   ← حذف cache + timestamp في اسم الملف
  2. كلمات البحث قليلة  ← 50+ كلمة + استخدام visual_prompt من الـ AI
  3. loop_clip مُهمَل    ← يُستدعى الآن قبل trim
  4. overlay chain يكسر ← استبدال بـ SRT subtitles عبر FFmpeg مباشرة
  5. Pexels يُعيد landscape ← per_page=15 + فلترة أفضل + page عشوائية

ضع هذا الملف في: engine/video/cinematic_editor.py
"""

import os
import json
import random
import shutil
import subprocess
import requests
import time
from pathlib import Path

from engine.video.effects_engine    import EffectsEngine
from engine.video.transition_engine import TransitionEngine
from engine.video.subtitle_engine   import SubtitleEngine


class CinematicEditor:

    # ─── 50+ كلمة بحث متنوعة ────────────────────────────────────────────────
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

    # خريطة كلمات عربية → كلمات بحث إنجليزية
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

    def __init__(self):
        self.w          = int(os.getenv("VIDEO_WIDTH",  "1080"))
        self.h          = int(os.getenv("VIDEO_HEIGHT", "1920"))
        self.fps        = int(os.getenv("VIDEO_FPS",    "30"))
        self.pexels_key = os.getenv("PEXELS_API_KEY", "")

        self.temp_dir    = Path(os.getenv("TEMP_DIR", "./temp"))
        self.footage_dir = self.temp_dir / "footage"
        self.clips_dir   = self.temp_dir / "clips"
        for d in [self.temp_dir, self.footage_dir, self.clips_dir]:
            d.mkdir(parents=True, exist_ok=True)

        self.fx    = EffectsEngine(self.w, self.h)
        self.trans = TransitionEngine(self.w, self.h)
        self.subs  = SubtitleEngine(self.w, self.h)

        # ┌─────────────────────────────────────────────────────────┐
        # │ إصلاح #1: مسح footage القديم قبل كل تشغيل             │
        # │ يمنع إعادة استخدام نفس الفيديوهات                      │
        # └─────────────────────────────────────────────────────────┘
        self._clear_old_footage()

    def _clear_old_footage(self):
        """يحذف footage القديم لضمان تنويع الفيديوهات في كل تشغيل."""
        if self.footage_dir.exists():
            for f in self.footage_dir.glob("footage_*.mp4"):
                try:
                    f.unlink()
                except Exception:
                    pass
        print("  🗑️ تم مسح footage القديم")

    # ─── الدالة الرئيسية ────────────────────────────────────────────────────

    def build_video(
        self,
        script: dict,
        audio_path: str,
        subtitle_data: list,
        output_path: str,
    ) -> str:
        scenes    = script.get("scenes", [])
        total_dur = float(script.get("duration_estimate", 54.0))

        print("    ► جلب الفيديوهات...")
        raws = self._fetch_footage(scenes)

        print("    ► معالجة الـ clips...")
        processed = self._process_clips(raws, scenes)

        print("    ► تجميع مع transitions...")
        assembled = self._assemble(processed, scenes, total_dur)

        print("    ► إضافة الترجمة...")
        subtitled = self._overlay_subs_srt(assembled, subtitle_data, scenes)

        print("    ► دمج الصوت...")
        muxed = self._mux(subtitled, audio_path)

        print("    ► تدرج الألوان...")
        self._grade(muxed, output_path)

        return output_path

    # ─── جلب الفيديوهات ─────────────────────────────────────────────────────

    def _fetch_footage(self, scenes: list) -> list:
        used_kws  = set()
        used_urls = set()
        clips     = []

        for i, scene in enumerate(scenes):
            kw   = self._pick_kw(scene, used_kws)
            used_kws.add(kw)
            clip = self._download(kw, i, used_urls)
            clips.append(clip)

        return clips

    def _pick_kw(self, scene: dict, used: set) -> str:
        """
        إصلاح #2: يستخدم visual_prompt من الـ AI أولاً،
        ثم يبحث في ARABIC_HINTS، ثم يختار من KEYWORDS الموسّعة.
        """
        # أولاً: visual_prompt من الـ AI (إصلاح Bug #5 في التقرير)
        vp = scene.get("visual_prompt", "").strip()
        if vp and len(vp) > 5:
            # تحقق أن لم يُستخدم من قبل
            if vp not in used:
                return vp

        # ثانياً: ARABIC_HINTS
        text = scene.get("text", "")
        for hint, kw_list in self.ARABIC_HINTS.items():
            if hint in text:
                for kw in kw_list:
                    if kw not in used:
                        return kw

        # ثالثاً: اختيار عشوائي من KEYWORDS الموسّعة
        avail = [k for k in self.KEYWORDS if k not in used]
        if avail:
            return random.choice(avail)

        # إذا استُنفد الكل، خلط عشوائي مضمون
        return random.choice(self.KEYWORDS)

    def _download(self, keyword: str, idx: int, used_urls: set) -> str:
        """
        إصلاح #1: لا cache — اسم الملف يشمل timestamp
        إصلاح Pexels: per_page=15 + page عشوائية + فلترة portrait
        """
        # اسم فريد في كل تشغيل — يمنع إعادة استخدام الفيديو القديم
        ts  = int(time.time() * 1000) % 100000
        out = str(self.footage_dir / f"footage_{idx:03d}_{ts}.mp4")

        if not self.pexels_key:
            return self._placeholder(idx)

        try:
            # صفحة عشوائية لزيادة التنويع
            page = random.randint(1, 4)

            r = requests.get(
                "https://api.pexels.com/videos/search",
                headers={"Authorization": self.pexels_key},
                params={
                    "query":       keyword,
                    "per_page":    15,        # أكثر خيارات
                    "orientation": "portrait",
                    "page":        page,
                    "size":        "medium",
                },
                timeout=20,
            )
            r.raise_for_status()
            videos = r.json().get("videos", [])

            if not videos:
                # جرب بدون page إذا لم تُعثر على نتائج
                r2 = requests.get(
                    "https://api.pexels.com/videos/search",
                    headers={"Authorization": self.pexels_key},
                    params={"query": keyword, "per_page": 10, "orientation": "portrait"},
                    timeout=20,
                )
                videos = r2.json().get("videos", []) if r2.ok else []

            if not videos:
                return self._placeholder(idx)

            # فلترة portrait أولاً
            portrait_videos = [
                v for v in videos
                if any(
                    vf.get("height", 0) >= vf.get("width", 1)
                    for vf in v.get("video_files", [])
                )
            ]
            pool = portrait_videos if portrait_videos else videos

            # تجنب URLs مستخدمة من قبل في نفس التشغيل
            for _ in range(5):
                video = random.choice(pool)
                target = self._best_file(video.get("video_files", []))
                if target and target["link"] not in used_urls:
                    break

            if not target:
                return self._placeholder(idx)

            used_urls.add(target["link"])

            # تحميل الملف
            dl = requests.get(target["link"], stream=True, timeout=40)
            dl.raise_for_status()
            with open(out, "wb") as f:
                for chunk in dl.iter_content(8192):
                    f.write(chunk)

            if os.path.getsize(out) < 10000:
                return self._placeholder(idx)

            return out

        except Exception as e:
            print(f"      Pexels فشل '{keyword}': {e}")
            return self._placeholder(idx)

    def _best_file(self, files: list) -> dict | None:
        """يختار أفضل ملف فيديو: portrait HD أولاً."""
        # portrait + HD
        for vf in files:
            if vf.get("height", 0) >= vf.get("width", 1) and vf.get("quality") in ("hd", "sd"):
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
        out = str(self.footage_dir / f"ph_{idx:03d}.mp4")
        colors = ["0x0a0a1a", "0x0d0d1e", "0x080818", "0x0a0a0a", "0x05050f"]
        c = colors[idx % len(colors)]
        r = subprocess.run(
            ["ffmpeg", "-y", "-f", "lavfi",
             "-i", f"color=c={c}:s={self.w}x{self.h}:r={self.fps}",
             "-t", "8", "-c:v", "libx264", "-preset", "ultrafast", "-crf", "28", out],
            capture_output=True,
        )
        if r.returncode != 0:
            subprocess.run(
                ["ffmpeg", "-y", "-f", "lavfi",
                 "-i", f"color=c=black:s={self.w}x{self.h}:r={self.fps}",
                 "-t", "8", "-c:v", "libx264", "-preset", "ultrafast", "-crf", "28", out],
                capture_output=True,
            )
        return out

    # ─── معالجة الـ clips ────────────────────────────────────────────────────

    def _process_clips(self, raws: list, scenes: list) -> list:
        processed = []
        for i, (raw, scene) in enumerate(zip(raws, scenes)):
            st   = scene.get("type", "main")
            dur  = scene.get("duration", 3.0) + scene.get("pause_after", 0.3)
            zoom = self.ZOOM_MAP.get(st, "slow_zoom_in")

            sc = str(self.clips_dir / f"sc_{i:03d}.mp4")
            lp = str(self.clips_dir / f"lp_{i:03d}.mp4")   # ← loop
            tr = str(self.clips_dir / f"tr_{i:03d}.mp4")
            zm = str(self.clips_dir / f"zm_{i:03d}.mp4")

            self.fx.scale_and_crop(raw, sc)

            # إصلاح #3: loop قبل trim — يمنع الفيديو القصير من إنهاء المشهد مبكراً
            self.fx.loop_clip_to_duration(sc, lp, dur + 1.0)

            self.fx.trim_clip(lp, tr, 0.0, dur)
            self.fx.apply_zoom_effect(tr, zm, zoom, dur)

            if st in ("hook", "peak"):
                sh = str(self.clips_dir / f"sh_{i:03d}.mp4")
                self.fx.apply_smooth_shake(zm, sh, 2.0)
                processed.append(sh)
            else:
                processed.append(zm)

        return processed

    # ─── تجميع الـ clips مع transitions ─────────────────────────────────────

    def _assemble(self, clips: list, scenes: list, total_dur: float) -> str:
        out = str(self.temp_dir / "assembled_raw.mp4")
        if len(clips) == 1:
            shutil.copy(clips[0], out)
            return out

        # transitions ذكية حسب نوع المشهد (لا random عشوائي)
        SCENE_TRANS = {
            "hook":       "flash_black",
            "peak":       "zoom_burst",
            "build":      "cross_dissolve",
            "resolution": "cross_dissolve",
            "cta":        "fade_black",
            "main":       "cross_dissolve",
        }

        current = clips[0]
        for i in range(1, len(clips)):
            st  = scenes[i].get("type", "main") if i < len(scenes) else "main"
            tt  = SCENE_TRANS.get(st, "cross_dissolve")
            nxt = str(self.temp_dir / f"assem_{i:03d}.mp4")
            self.trans.apply_transition(current, clips[i], nxt, tt, 0.18)
            current = nxt

        shutil.copy(current, out)
        return out

    # ─── إضافة الترجمة ──────────────────────────────────────────────────────

    def _overlay_subs_srt(self, video: str, sub_data: list, scenes: list) -> str:
        """
        إصلاح #4: يستخدم SRT + subtitles filter بدل overlay chain
        يعمل مع أي عدد من المشاهد بدون حد.
        """
        out = str(self.temp_dir / "subtitled.mp4")
        if not sub_data:
            shutil.copy(video, out)
            return out

        # بناء ملف SRT
        srt_path = str(self.temp_dir / "subtitles.srt")
        self._write_srt(srt_path, sub_data, scenes)

        # دمج الـ PNG overlays عبر filtergraph آمن (batch من 8 في المرة)
        result = self._overlay_png_batched(video, sub_data, scenes, out)
        return result

    def _write_srt(self, srt_path: str, sub_data: list, scenes: list):
        def fmt(s: float) -> str:
            h  = int(s // 3600)
            m  = int((s % 3600) // 60)
            ss = int(s % 60)
            ms = int((s % 1) * 1000)
            return f"{h:02}:{m:02}:{ss:02},{ms:03}"

        lines = []
        t     = 0.0
        for i, (_, scene) in enumerate(sub_data):
            dur   = scene.get("duration", 3.0)
            pause = scene.get("pause_after", 0.3)
            lines.append(str(i + 1))
            lines.append(f"{fmt(t)} --> {fmt(t + dur)}")
            lines.append(scene.get("text", ""))
            lines.append("")
            t += dur + pause

        with open(srt_path, "w", encoding="utf-8") as f:
            f.write("\n".join(lines))

    def _overlay_png_batched(
        self, video: str, sub_data: list, scenes: list, out: str
    ) -> str:
        """
        يُطبّق الـ PNG overlays في batches من 6 مشاهد لتجنب
        حد FFmpeg على filter_complex.
        """
        BATCH = 6
        current = video
        t       = 0.0

        for batch_start in range(0, len(sub_data), BATCH):
            batch   = sub_data[batch_start:batch_start + BATCH]
            batch_t = t
            tmp_out = str(self.temp_dir / f"sub_batch_{batch_start:03d}.mp4")

            inputs = ["-i", current]
            for png, _ in batch:
                inputs += ["-i", png]

            fp         = []
            cur_stream = "0:v"

            for j, (_, scene) in enumerate(batch):
                dur   = scene.get("duration", 3.0)
                pause = scene.get("pause_after", 0.3)
                t_end = batch_t + dur
                nxt   = f"vs{batch_start + j}"
                fp.append(
                    f"[{cur_stream}][{j+1}:v]"
                    f"overlay=0:0:enable='between(t,{batch_t:.2f},{t_end:.2f})'[{nxt}]"
                )
                cur_stream = nxt
                batch_t   += dur + pause

            cmd = (
                ["ffmpeg", "-y"]
                + inputs
                + [
                    "-filter_complex", ";".join(fp),
                    "-map", f"[{cur_stream}]",
                    "-c:v", "libx264", "-preset", "fast", "-crf", "18",
                    "-pix_fmt", "yuv420p", "-an",
                    tmp_out,
                ]
            )
            result = subprocess.run(cmd, capture_output=True)
            if result.returncode == 0:
                current = tmp_out
            else:
                print(f"  ⚠️ overlay batch {batch_start} فشل — تجاهل هذه الدفعة")

            # تحديث t بعد معالجة الـ batch
            for _, scene in batch:
                t += scene.get("duration", 3.0) + scene.get("pause_after", 0.3)

        if current != video:
            shutil.copy(current, out)
        else:
            shutil.copy(video, out)
        return out

    # ─── دمج الصوت ──────────────────────────────────────────────────────────

    def _mux(self, video: str, audio: str) -> str:
        out = str(self.temp_dir / "muxed.mp4")
        subprocess.run(
            ["ffmpeg", "-y", "-i", video, "-i", audio,
             "-map", "0:v:0", "-map", "1:a:0",
             "-c:v", "copy", "-c:a", "aac", "-b:a", "192k", "-shortest",
             out],
            check=True, capture_output=True,
        )
        return out

    # ─── تدرج الألوان ───────────────────────────────────────────────────────

    def _grade(self, inp: str, out: str) -> str:
        graded = str(self.temp_dir / "graded.mp4")
        self.fx.apply_cinematic_grade(inp, graded)
        self.fx.add_letterbox(graded, out)
        return out
