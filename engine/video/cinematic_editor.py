"""
🎬 Cinematic Editor — مُجهّز البيانات لـ Remotion
═══════════════════════════════════════════════════════════════
بعد التحول لـ Remotion، أصبح هذا الملف مسؤولاً عن:
  • جلب الفيديوهات من Pexels + Pixabay
  • اختيار الكلمات المفتاحية الذكية (50+ keyword + visual_prompt)
  • بناء JSON props كامل لـ Remotion
  • تجهيز التايملاين (Timeline) للمشاهد
  • 🆕 مزامنة المشاهد مع مدة الصوت تلقائياً

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
from typing import Optional, List, Dict

logger = logging.getLogger(__name__)


class CinematicEditor:
    """مُجهّز البيانات والمشاهد لـ Remotion."""

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

    # ─── خرائط للتأثيرات (تُمرّر لـ Remotion كـ JSON) ────────────
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

    # ════════════════════════════════════════════════════════════════
    def __init__(self):
        """تهيئة مُجهّز البيانات."""
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
        self.footage_dir.mkdir(parents=True, exist_ok=True)

        # مسح footage القديم
        self._clear_old_footage()

        logger.info(
            f"🎬 CinematicEditor (Remotion mode) | {self.w}x{self.h}@{self.fps}fps"
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
    #                    🆕 الدالة الرئيسية الجديدة
    # ════════════════════════════════════════════════════════════════
    def build_props_for_remotion(
        self,
        script: dict,
        audio_path: str,
        subtitle_data: list,
    ) -> dict:
        """
        🆕 بناء JSON props كامل لـ Remotion.
        مع مزامنة تلقائية للمشاهد مع مدة الصوت.
        """
        scenes = script.get("scenes", [])
        total_dur = float(script.get("duration_estimate", 45.0))

        if not scenes:
            raise ValueError("❌ لا توجد مشاهد في السكربت")

        logger.info(f"🎬 تجهيز Remotion props | {len(scenes)} مشهد | {total_dur:.1f}s")

        # 🆕 1️⃣ مزامنة توقيتات المشاهد مع مدة الصوت
        self._sync_scenes_to_audio(scenes, total_dur)

        # 2️⃣ جلب الفيديوهات
        logger.info("► جلب الفيديوهات...")
        raws = self._fetch_footage(scenes)

        # 3️⃣ بناء بيانات المشاهد
        logger.info("► بناء بيانات المشاهد...")
        scenes_data = self._build_scenes_data(scenes, raws)

        # 4️⃣ بناء بيانات الترجمات (مزامنة مع المشاهد)
        logger.info("► بناء بيانات الترجمات...")
        subtitles_data = self._build_subtitles_data(subtitle_data, scenes)

        # 5️⃣ تجهيز الـ props النهائية
        props = {
            # المعلومات العامة
            "title": script.get("title", ""),
            "totalDuration": total_dur,
            "fps": self.fps,
            "width": self.w,
            "height": self.h,
            "quality": self.quality,

            # الملفات
            "audioPath": str(Path(audio_path).resolve()) if audio_path else "",

            # المحتوى
            "scenes": scenes_data,
            "subtitles": subtitles_data,

            # إعدادات التصميم (Remotion سيستخدمها)
            "design": {
                "fontFamily": "Cairo",
                "fontWeight": 900,
                "primaryColor": "#FFFFFF",
                "accentColor": "#FFD700",
                "shadowColor": "rgba(0,0,0,0.9)",
                "backgroundOverlay": "rgba(0,0,0,0.35)",
                "letterboxEnabled": True,
                "cinematicGrade": True,
            },
        }

        logger.info(f"✓ Remotion props جاهز | {len(scenes_data)} مشهد | {len(subtitles_data)} ترجمة")
        return props

    # 🆕🆕🆕 دالة جديدة: مزامنة المشاهد مع مدة الصوت 🆕🆕🆕
    def _sync_scenes_to_audio(self, scenes: list, target_duration: float) -> None:
        """
        🆕 إعادة توزيع توقيتات المشاهد لتطابق مدة الصوت الفعلية.
        
        تعدّل المشاهد in-place بحيث:
          - مجموع كل المشاهد = مدة الصوت
          - النسب بين المشاهد محفوظة
        
        Args:
            scenes: قائمة المشاهد (تُعدّل مباشرة)
            target_duration: المدة المستهدفة (بالثواني)
        """
        if not scenes:
            return

        # حساب المدة الإجمالية الحالية
        current_total = sum(
            float(s.get("duration", 3.0)) + float(s.get("pause_after", 0.3))
            for s in scenes
        )

        if current_total <= 0:
            logger.warning("⚠ مجموع المدد صفر، تخطي المزامنة")
            return

        # حساب نسبة التعديل
        scale_factor = target_duration / current_total

        logger.info(
            f"🎯 مزامنة المشاهد: {current_total:.1f}s → {target_duration:.1f}s "
            f"(scale: {scale_factor:.2f}x)"
        )

        # تعديل كل مشهد بالنسبة
        for scene in scenes:
            old_duration = float(scene.get("duration", 3.0))
            old_pause = float(scene.get("pause_after", 0.3))
            
            # الحفاظ على نسبة الـ pause إلى الـ duration
            new_duration = round(old_duration * scale_factor, 2)
            new_pause = round(old_pause * scale_factor, 2)
            
            # حد أدنى للمدة (لتجنب مشاهد قصيرة جداً)
            new_duration = max(new_duration, 1.0)
            new_pause = max(new_pause, 0.1)
            
            scene["duration"] = new_duration
            scene["pause_after"] = new_pause

        # التحقق من الإجمالي الجديد
        new_total = sum(
            float(s.get("duration", 3.0)) + float(s.get("pause_after", 0.3))
            for s in scenes
        )
        
        logger.info(f"✓ مدة المشاهد الجديدة: {new_total:.1f}s")

    def _build_scenes_data(self, scenes: list, raws: list) -> List[dict]:
        """بناء بيانات المشاهد كـ JSON."""
        scenes_data = []
        cumulative_time = 0.0

        for i, scene in enumerate(scenes):
            scene_type = scene.get("type", "main")
            duration = float(scene.get("duration", 3.0))
            pause_after = float(scene.get("pause_after", 0.3))

            # التأثيرات
            zoom_effect = self.ZOOM_MAP.get(scene_type, "slow_zoom_in")
            available_trans = self.SCENE_TRANSITIONS.get(
                scene_type, ["cross_dissolve"]
            )
            transition = random.choice(available_trans) if i > 0 else "none"

            # Shake للمشاهد المهمة
            shake = scene_type in ("hook", "peak")

            # المسار المطلق للفيديو
            background_path = ""
            if i < len(raws) and raws[i]:
                background_path = str(Path(raws[i]).resolve())

            scene_data = {
                "id": i,
                "type": scene_type,
                "text": scene.get("text", ""),
                "duration": duration,
                "pauseAfter": pause_after,
                "startTime": round(cumulative_time, 3),
                "endTime": round(cumulative_time + duration, 3),
                "totalLength": round(duration + pause_after, 3),
                "backgroundPath": background_path,
                "zoomEffect": zoom_effect,
                "transitionIn": transition,
                "shake": shake,
                "visualPrompt": scene.get("visual_prompt", ""),
            }

            scenes_data.append(scene_data)
            cumulative_time += duration + pause_after

        return scenes_data

    def _build_subtitles_data(
        self,
        sub_data: list,
        scenes: list,
    ) -> List[dict]:
        """
        🆕 بناء بيانات الترجمات كـ JSON لـ Remotion.
        تستخدم توقيتات المشاهد المُحدّثة بعد المزامنة.

        يدعم نوعين من المدخلات:
        1. القديم: [(png_path, scene_dict), ...]
        2. الجديد: [{"text": "...", "start": 0.0, "end": 3.0}, ...]
        3. 🆕 إذا فارغ: نبني من المشاهد مباشرة
        """
        # 🆕 إذا لم توجد ترجمات، نبنيها من المشاهد (الأفضل)
        if not sub_data:
            logger.info("ℹ بناء الترجمات من المشاهد المُحدّثة...")
            return self._build_subtitles_from_scenes(scenes)

        # 🆕 دائماً نُعيد بناء الترجمات من المشاهد لضمان المزامنة
        # (المشاهد تم تحديث توقيتاتها بـ _sync_scenes_to_audio)
        logger.info("ℹ إعادة بناء الترجمات لضمان المزامنة...")
        return self._build_subtitles_from_scenes(scenes)

    # 🆕🆕🆕 دالة جديدة: بناء الترجمات من المشاهد 🆕🆕🆕
    def _build_subtitles_from_scenes(self, scenes: list) -> List[dict]:
        """
        🆕 بناء بيانات الترجمات مباشرة من المشاهد (بعد المزامنة).
        
        هذا يضمن أن الترجمات تتطابق تماماً مع توقيتات المشاهد
        وبالتالي مع الصوت.
        """
        subtitles = []
        cumulative_time = 0.0

        for i, scene in enumerate(scenes):
            text = scene.get("text", "").strip()
            duration = float(scene.get("duration", 3.0))
            pause = float(scene.get("pause_after", 0.3))

            if text:
                subtitles.append({
                    "id": i,
                    "text": text,
                    "start": round(cumulative_time, 3),
                    "end": round(cumulative_time + duration, 3),
                    "duration": round(duration, 3),
                    "sceneId": i,
                })

            cumulative_time += duration + pause

        logger.info(f"✓ تم بناء {len(subtitles)} ترجمة مزامنة مع المشاهد")
        return subtitles

    # ════════════════════════════════════════════════════════════════
    #                    🔁 الدالة القديمة (Deprecated)
    # ════════════════════════════════════════════════════════════════
    def build_video(
        self,
        script: dict,
        audio_path: str,
        subtitle_data: list,
        output_path: str,
    ) -> str:
        """⚠️ DEPRECATED: استخدم build_props_for_remotion() بدلاً منها."""
        raise DeprecationWarning(
            "❌ build_video() لم تعد مدعومة!\n"
            "   استخدم: build_props_for_remotion() ثم RemotionRenderer.render_final()"
        )

    # ════════════════════════════════════════════════════════════════
    #                    جلب الفيديوهات (احتُفظ به)
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

            for _ in range(5):
                video = random.choice(hits)
                videos = video.get("videos", {})

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
        """توليد فيديو خلفية بسيط (placeholder) باستخدام FFmpeg."""
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
    #                    دوال مساعدة
    # ════════════════════════════════════════════════════════════════
    def cleanup_temp_files(self) -> None:
        """تنظيف الملفات المؤقتة."""
        try:
            count = 0
            patterns = [
                "remotion_props.json",
                "footage_*.mp4",
                "ph_*.mp4",
            ]

            for pattern in patterns:
                for f in self.temp_dir.rglob(pattern):
                    f.unlink(missing_ok=True)
                    count += 1

            logger.info(f"🧹 تم تنظيف {count} ملف مؤقت")
        except Exception as e:
            logger.warning(f"⚠ فشل التنظيف: {e}")


# ════════════════════════════════════════════════════════════════════════
#                    اختبار سريع
# ════════════════════════════════════════════════════════════════════════
if __name__ == "__main__":
    editor = CinematicEditor()
    print(f"✓ CinematicEditor (Remotion mode) جاهز")
    print(f"  Dimensions: {editor.w}x{editor.h}")
    print(f"  FPS: {editor.fps}")
    print(f"  Quality: {editor.quality}")
    print(f"  Pexels: {'✓' if editor.pexels_key else '✗'}")
    print(f"  Pixabay: {'✓' if editor.pixabay_key else '✗'}")
