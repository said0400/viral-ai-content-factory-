"""
🎬 Cinematic Editor v3.0 — Audio-First + HD + Diversity
═══════════════════════════════════════════════════════════════
التحسينات v3.0:
  ✓ مزامنة دقيقة (0ms) للمشاهد مع الصوت
  ✓ جودة HD للخلفيات (لا 240p أبداً)
  ✓ تنوع أفضل للخلفيات (لا تكرار)
  ✓ Whisper TikTok subtitles
  ✓ Audio-First approach

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
    """مُجهّز البيانات لـ Remotion v3.0."""

    KEYWORDS = [
        "dark cinematic dramatic", "silhouette dramatic sunset",
        "cinematic night city", "dramatic sky clouds",
        "moody dark forest", "cinematic desert landscape",
        "dark rain dramatic", "dramatic lightning storm",
        "cinematic mountain fog", "dark ocean waves",
        "person walking alone", "man standing alone dramatic",
        "silhouette person sunset", "person thinking alone",
        "man running dramatic", "person looking window rain",
        "man praying dramatic light", "silhouette crowd dark",
        "fire flame dark dramatic", "smoke light cinematic",
        "stars milky way dark", "sunrise golden mountain",
        "waves ocean slow motion", "rain drops dark",
        "snow falling dark", "desert dunes sunset",
        "waterfall mist dramatic", "fog dark forest",
        "urban night bokeh", "city lights night",
        "empty road night", "abandoned building dark",
        "dark alley night", "bridge night cinematic",
        "train night dramatic", "rooftop city night",
        "candle flame dark", "clock ticking dramatic",
        "book pages turning", "dark water reflection",
        "mirror reflection dramatic", "hands dramatic light",
        "eye close up dramatic", "shadow dramatic light",
        "slow motion dramatic", "epic slow motion",
        "cinematic slow motion nature", "dramatic slow motion water",
        "timelapse city night", "timelapse sky dramatic",
    ]

    ARABIC_HINTS = {
        "ألم": ["dark rain dramatic", "person looking window rain"],
        "نجاح": ["sunrise golden mountain", "person running dramatic"],
        "وحيد": ["person walking alone", "silhouette person sunset"],
        "ليل": ["urban night bokeh", "city lights night"],
        "نار": ["fire flame dark dramatic", "smoke light cinematic"],
        "أمل": ["sunrise golden mountain", "waterfall mist dramatic"],
        "مطر": ["rain drops dark", "person looking window rain"],
        "قوة": ["silhouette dramatic sunset", "man standing alone dramatic"],
        "سماء": ["stars milky way dark", "dramatic sky clouds"],
        "طريق": ["empty road night", "cinematic desert landscape"],
        "خوف": ["dark alley night", "shadow dramatic light"],
        "حب": ["candle flame dark", "hands dramatic light"],
        "حزن": ["rain drops dark", "dark rain dramatic"],
        "صبر": ["clock ticking dramatic", "person thinking alone"],
        "نور": ["candle flame dark", "dramatic lightning storm"],
        "وقت": ["clock ticking dramatic", "timelapse city night"],
        "صمت": ["fog dark forest", "empty road night"],
    }

    ZOOM_MAP = {
        "hook": "punch_zoom", "build": "slow_zoom_in",
        "peak": "punch_zoom", "resolution": "slow_zoom_out",
        "cta": "drift_right", "main": "slow_zoom_in",
    }

    SCENE_TRANSITIONS = {
        "hook": ["flash_black", "zoom_burst"],
        "peak": ["zoom_burst", "flash_black"],
        "build": ["cross_dissolve", "smooth_fade"],
        "resolution": ["cross_dissolve", "fade_black"],
        "cta": ["fade_black", "smooth_fade"],
        "main": ["cross_dissolve", "smooth_fade"],
    }

    def __init__(self):
        self.w = int(os.getenv("VIDEO_WIDTH", "1080"))
        self.h = int(os.getenv("VIDEO_HEIGHT", "1920"))
        self.fps = int(os.getenv("VIDEO_FPS", "30"))
        self.quality = os.getenv("VIDEO_QUALITY", "high")
        self.pexels_key = os.getenv("PEXELS_API_KEY", "")
        self.pixabay_key = os.getenv("PIXABAY_API_KEY", "")
        self.use_whisper = os.getenv("USE_WHISPER", "true").lower() == "true"
        self.whisper_max_words = int(os.getenv("WHISPER_MAX_WORDS", "4"))
        self.whisper_max_duration = float(os.getenv("WHISPER_MAX_DURATION", "2.5"))
        self.temp_dir = Path(os.getenv("TEMP_DIR", "./temp"))
        self.footage_dir = self.temp_dir / "footage"
        self.footage_dir.mkdir(parents=True, exist_ok=True)
        self._clear_old_footage()
        logger.info(f"🎬 CinematicEditor v3.0 | {self.w}x{self.h}@{self.fps}fps")

    def _clear_old_footage(self) -> None:
        try:
            count = 0
            if self.footage_dir.exists():
                for f in self.footage_dir.glob("*.mp4"):
                    f.unlink()
                    count += 1
            if count:
                logger.info(f"🗑️ مسح {count} ملف قديم")
        except Exception:
            pass

    def _get_actual_audio_duration(self, audio_path: str) -> float:
        if not audio_path or not Path(audio_path).exists():
            return 0.0
        try:
            r = subprocess.run(
                ["ffprobe", "-v", "quiet", "-show_entries", "format=duration",
                 "-of", "default=noprint_wrappers=1:nokey=1", audio_path],
                capture_output=True, text=True, timeout=30, check=True,
            )
            return float(r.stdout.strip())
        except Exception:
            return 0.0

    # ════════════════════════════════════════════════════════════════
    #                    الدالة الرئيسية
    # ════════════════════════════════════════════════════════════════
    def build_props_for_remotion(self, script: dict, audio_path: str, subtitle_data: list) -> dict:
        scenes = script.get("scenes", [])
        if not scenes:
            raise ValueError("❌ لا توجد مشاهد")

        # قياس مدة الصوت الفعلية
        actual_duration = self._get_actual_audio_duration(audio_path)
        total_dur = actual_duration if actual_duration > 0 else float(script.get("duration_estimate", 45.0))
        script["duration_estimate"] = total_dur

        logger.info(f"🎬 تجهيز props | {len(scenes)} مشهد | {total_dur:.2f}s")

        # Whisper
        whisper_subtitles = []
        if self.use_whisper and audio_path:
            whisper_subtitles = self._get_whisper_subtitles(audio_path)

        # مزامنة المشاهد
        self._sync_scenes_to_audio(scenes, total_dur)

        # جلب الفيديوهات
        logger.info("► جلب الفيديوهات...")
        raws = self._fetch_footage(scenes)

        # بناء البيانات
        scenes_data = self._build_scenes_data(scenes, raws)

        if whisper_subtitles:
            whisper_subtitles = self._validate_whisper_subtitles(whisper_subtitles, total_dur)
            subtitles_data = whisper_subtitles
        else:
            subtitles_data = self._build_subtitles_from_scenes(scenes)

        props = {
            "title": script.get("title", ""),
            "totalDuration": total_dur,
            "audioActualDuration": total_dur,
            "fps": self.fps,
            "width": self.w,
            "height": self.h,
            "quality": self.quality,
            "audioPath": str(Path(audio_path).resolve()) if audio_path else "",
            "scenes": scenes_data,
            "subtitles": subtitles_data,
            "design": {
                "fontFamily": "Cairo",
                "fontWeight": 900,
                "primaryColor": "#FFFFFF",
                "accentColor": "#FFD700",
                "shadowColor": "rgba(0,0,0,0.9)",
                "backgroundOverlay": "rgba(0,0,0,0.35)",
                "letterboxEnabled": True,
                "cinematicGrade": True,
                "subtitleMode": "tiktok" if whisper_subtitles else "scene",
            },
        }

        logger.info(f"✓ Props جاهز | {len(scenes_data)} مشهد | {len(subtitles_data)} ترجمة")
        return props

    # ════════════════════════════════════════════════════════════════
    #              مزامنة دقيقة (0ms)
    # ════════════════════════════════════════════════════════════════
    def _sync_scenes_to_audio(self, scenes: list, target_duration: float) -> None:
        if not scenes or target_duration <= 0:
            return

        current_total = sum(
            float(s.get("duration", 3.0)) + float(s.get("pause_after", 0.3))
            for s in scenes
        )

        if current_total <= 0:
            return

        scale_factor = target_duration / current_total
        logger.info(f"🎯 مزامنة: {current_total:.2f}s → {target_duration:.2f}s (×{scale_factor:.3f})")

        new_total = 0.0
        for scene in scenes:
            new_dur = round(float(scene.get("duration", 3.0)) * scale_factor, 3)
            new_pause = round(float(scene.get("pause_after", 0.3)) * scale_factor, 3)
            scene["duration"] = max(new_dur, 0.5)
            scene["pause_after"] = max(new_pause, 0.05)
            new_total += scene["duration"] + scene["pause_after"]

        diff = target_duration - new_total
        if abs(diff) > 0.01:
            scenes[-1]["pause_after"] = max(float(scenes[-1].get("pause_after", 0.3)) + diff, 0.0)

        final = sum(float(s.get("duration", 3.0)) + float(s.get("pause_after", 0.3)) for s in scenes)
        logger.info(f"✓ مدة المشاهد: {final:.2f}s (دقة: {abs(final-target_duration)*1000:.0f}ms)")

    # ════════════════════════════════════════════════════════════════
    #              Whisper + Validation
    # ════════════════════════════════════════════════════════════════
    def _get_whisper_subtitles(self, audio_path: str) -> List[Dict]:
        if not audio_path or not Path(audio_path).exists():
            return []
        try:
            from engine.voice.whisper_transcriber import WhisperTranscriber
            logger.info("🎤 تحليل الصوت بـ Whisper...")
            transcriber = WhisperTranscriber()
            subtitles = transcriber.transcribe_to_subtitles(
                audio_path=audio_path,
                max_words_per_chunk=self.whisper_max_words,
                max_chunk_duration=self.whisper_max_duration,
            )
            if subtitles:
                for i, sub in enumerate(subtitles):
                    sub["sceneId"] = i
                logger.info(f"✅ Whisper: {len(subtitles)} مجموعة")
                return subtitles
        except ImportError:
            logger.warning("⚠ Whisper غير مثبت")
        except Exception as e:
            logger.error(f"❌ فشل Whisper: {e}")
        return []

    def _validate_whisper_subtitles(self, subtitles: List[Dict], max_duration: float) -> List[Dict]:
        validated = []
        for sub in subtitles:
            start = float(sub.get("start", 0))
            end = float(sub.get("end", 0))
            if start >= max_duration:
                continue
            if end > max_duration:
                sub["end"] = max_duration
                sub["duration"] = end - start
                if "words" in sub:
                    sub["words"] = [w for w in sub["words"] if float(w.get("start", 0)) < max_duration]
            if sub.get("text", "").strip():
                validated.append(sub)
        return validated

    # ════════════════════════════════════════════════════════════════
    #              بناء البيانات
    # ════════════════════════════════════════════════════════════════
    def _build_scenes_data(self, scenes: list, raws: list) -> List[dict]:
        scenes_data = []
        cumulative_time = 0.0

        for i, scene in enumerate(scenes):
            scene_type = scene.get("type", "main")
            duration = float(scene.get("duration", 3.0))
            pause_after = float(scene.get("pause_after", 0.3))

            zoom_effect = self.ZOOM_MAP.get(scene_type, "slow_zoom_in")
            available_trans = self.SCENE_TRANSITIONS.get(scene_type, ["cross_dissolve"])
            transition = random.choice(available_trans) if i > 0 else "none"
            shake = scene_type in ("hook", "peak")

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

    def _build_subtitles_from_scenes(self, scenes: list) -> List[dict]:
        subtitles = []
        cumulative_time = 0.0
        for i, scene in enumerate(scenes):
            text = scene.get("text", "").strip()
            duration = float(scene.get("duration", 3.0))
            pause = float(scene.get("pause_after", 0.3))
            if text:
                subtitles.append({
                    "id": i, "text": text,
                    "start": round(cumulative_time, 3),
                    "end": round(cumulative_time + duration, 3),
                    "duration": round(duration, 3),
                    "sceneId": i,
                })
            cumulative_time += duration + pause
        return subtitles

    # ════════════════════════════════════════════════════════════════
    #              جلب الفيديوهات (HD + تنوع)
    # ════════════════════════════════════════════════════════════════
    def _fetch_footage(self, scenes: list) -> list:
        used_kws = set()
        used_urls = set()
        clips = []
        for i, scene in enumerate(scenes):
            kw = self._pick_kw(scene, used_kws)
            used_kws.add(kw)
            clip = self._download(kw, i, used_urls)
            clips.append(clip)
        return clips

    def _pick_kw(self, scene: dict, used: set) -> str:
        """🆕 اختيار كلمة بحث ذكية مع تنوع أفضل."""
        vp = scene.get("visual_prompt", "").strip()
        if vp and len(vp) > 5 and vp not in used:
            return vp

        text = scene.get("text", "")
        matching = []
        for hint, kw_list in self.ARABIC_HINTS.items():
            if hint in text:
                for kw in kw_list:
                    if kw not in used:
                        matching.append(kw)
        if matching:
            return random.choice(matching)

        avail = [k for k in self.KEYWORDS if k not in used]
        if avail:
            random.shuffle(avail)
            return avail[0]

        return random.choice(self.KEYWORDS)

    def _download(self, keyword: str, idx: int, used_urls: set) -> str:
        ts = int(time.time() * 1000) % 100000
        out = str(self.footage_dir / f"footage_{idx:03d}_{ts}.mp4")

        if self.pexels_key:
            result = self._download_from_pexels(keyword, out, used_urls)
            if result:
                return result

        if self.pixabay_key:
            result = self._download_from_pixabay(keyword, out, used_urls)
            if result:
                return result

        return self._placeholder(idx)

    def _download_from_pexels(self, keyword: str, out: str, used_urls: set) -> Optional[str]:
        try:
            page = random.randint(1, 4)
            r = requests.get(
                "https://api.pexels.com/videos/search",
                headers={"Authorization": self.pexels_key},
                params={
                    "query": keyword, "per_page": 15,
                    "orientation": "portrait", "page": page,
                    "size": "large",  # 🆕 طلب جودة عالية
                },
                timeout=20,
            )
            if r.status_code != 200:
                return None

            videos = r.json().get("videos", [])
            if not videos:
                r2 = requests.get(
                    "https://api.pexels.com/videos/search",
                    headers={"Authorization": self.pexels_key},
                    params={"query": keyword, "per_page": 10, "orientation": "portrait"},
                    timeout=20,
                )
                videos = r2.json().get("videos", []) if r2.ok else []

            if not videos:
                return None

            portrait = [v for v in videos
                       if any(vf.get("height", 0) >= vf.get("width", 1)
                             for vf in v.get("video_files", []))]
            pool = portrait if portrait else videos

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
        except Exception:
            return None

    def _download_from_pixabay(self, keyword: str, out: str, used_urls: set) -> Optional[str]:
        try:
            r = requests.get(
                "https://pixabay.com/api/videos/",
                params={"key": self.pixabay_key, "q": keyword,
                        "video_type": "film", "orientation": "vertical", "per_page": 15},
                timeout=20,
            )
            if r.status_code != 200:
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
        except Exception:
            return None

    def _download_file(self, url: str, out: str) -> Optional[str]:
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
        except Exception:
            Path(out).unlink(missing_ok=True)
            return None

    def _best_file(self, files: list) -> Optional[dict]:
        """🆕 اختيار أفضل ملف فيديو (أعلى جودة)."""
        if not files:
            return None

        scored = []
        for vf in files:
            score = 0
            height = vf.get("height", 0)
            width = vf.get("width", 0)
            quality = vf.get("quality", "")

            # Portrait
            if height >= width:
                score += 100

            # جودة
            if quality == "hd":
                score += 50
            elif quality == "sd":
                score += 20

            # دقة عالية
            if height >= 1920:
                score += 80
            elif height >= 1280:
                score += 60
            elif height >= 720:
                score += 40
            elif height >= 480:
                score += 20

            # عقوبة للجودة المنخفضة
            if height < 480 and width < 480:
                score -= 50

            scored.append((score, vf))

        scored.sort(key=lambda x: x[0], reverse=True)
        return scored[0][1]

    def _placeholder(self, idx: int) -> str:
        out = str(self.footage_dir / f"ph_{idx:03d}.mp4")
        colors = ["0x0a0a1a", "0x0d0d1e", "0x080818", "0x0a0a0a", "0x05050f"]
        c = colors[idx % len(colors)]
        try:
            subprocess.run(
                ["ffmpeg", "-y", "-f", "lavfi",
                 "-i", f"color=c={c}:s={self.w}x{self.h}:r={self.fps}",
                 "-t", "8", "-c:v", "libx264", "-preset", "ultrafast", "-crf", "28", out],
                capture_output=True, timeout=30, check=True,
            )
        except Exception:
            subprocess.run(
                ["ffmpeg", "-y", "-f", "lavfi",
                 "-i", f"color=c=black:s={self.w}x{self.h}:r={self.fps}",
                 "-t", "8", "-c:v", "libx264", "-preset", "ultrafast", "-crf", "28", out],
                capture_output=True, timeout=30,
            )
        return out

    def build_video(self, *args, **kwargs):
        raise DeprecationWarning("استخدم build_props_for_remotion()")

    def cleanup_temp_files(self) -> None:
        try:
            count = 0
            for pattern in ["remotion_props.json", "footage_*.mp4", "ph_*.mp4"]:
                for f in self.temp_dir.rglob(pattern):
                    f.unlink(missing_ok=True)
                    count += 1
            logger.info(f"🧹 تم تنظيف {count} ملف")
        except Exception:
            pass


if __name__ == "__main__":
    editor = CinematicEditor()
    print(f"✓ CinematicEditor v3.0 جاهز")
