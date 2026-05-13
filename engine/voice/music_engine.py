"""
🎵 Music Engine — تحميل الموسيقى الخلفية تلقائياً
═══════════════════════════════════════════════════════════════
يدعم مصادر متعددة بترتيب الأولوية:
  1. Cache المحلي (إذا توفر)
  2. Pixabay Music API (مجاني + قانوني) 🌟
  3. YouTube (احتياطي - قد يفشل في الـ Cloud)

الميزات:
  ✓ يطابق Mood من ScriptWriter (motivation, dark, sigma...)
  ✓ Caching ذكي لتجنب إعادة التحميل
  ✓ يقص الموسيقى حسب المدة المطلوبة
  ✓ Fallback متعدد المستويات

ضع في: engine/voice/music_engine.py
═══════════════════════════════════════════════════════════════
"""

import os
import random
import logging
import subprocess
import requests
from pathlib import Path
from typing import Optional, List

logger = logging.getLogger(__name__)


class MusicEngine:
    """محرك الموسيقى الخلفية."""

    # ─── Pixabay Music API ───────────────────────────────────────
    PIXABAY_API = "https://pixabay.com/api/music/"

    # ─── خريطة Moods → استعلامات البحث ──────────────────────────
    # متطابق مع ScriptWriter & PromptEngine
    MOOD_QUERIES = {
        "motivation":    ["motivational", "inspiring", "epic", "uplifting"],
        "emotional":     ["emotional", "sad", "cinematic"],
        "dark":          ["dark", "mysterious", "suspense", "horror"],
        "horror":        ["horror", "scary", "tension", "thriller"],
        "sad":           ["sad", "melancholic", "emotional", "piano"],
        "sigma":         ["epic", "dark", "powerful", "trap"],
        "psychological": ["ambient", "thoughtful", "mysterious", "deep"],

        # legacy aliases (للتوافق)
        "epic":          ["epic", "cinematic", "trailer"],
        "calm":          ["calm", "peaceful", "meditation"],
        "dramatic":      ["dramatic", "tense", "cinematic"],
        "romantic":      ["romantic", "soft", "love"],
        "intelligence":  ["focus", "thinking", "deep"],
    }

    # ─── YouTube fallback queries ────────────────────────────────
    YOUTUBE_QUERIES = {
        mood: f"{words[0]} cinematic background music no copyright"
        for mood, words in MOOD_QUERIES.items()
    }

    # ════════════════════════════════════════════════════════════════
    def __init__(self):
        """تهيئة محرك الموسيقى."""
        self.music_dir = Path(os.getenv("MUSIC_DIR", "engine/assets/music"))
        self.music_dir.mkdir(parents=True, exist_ok=True)

        self.pixabay_key = os.getenv("PIXABAY_API_KEY")
        self.enable_youtube_fallback = (
            os.getenv("ENABLE_YOUTUBE_MUSIC", "true").lower() == "true"
        )

        self.timeout = int(os.getenv("MUSIC_DOWNLOAD_TIMEOUT", "60"))

        if self.pixabay_key:
            logger.info("🎵 MusicEngine | Pixabay enabled ✓")
        else:
            logger.warning("⚠ MusicEngine | PIXABAY_API_KEY غير موجود")

    # ════════════════════════════════════════════════════════════════
    #                    الدالة الرئيسية
    # ════════════════════════════════════════════════════════════════
    def get_music(self, mood: str, duration: float) -> Optional[str]:
        """
        الحصول على موسيقى مناسبة للمزاج والمدة.

        Args:
            mood: المزاج (motivation, dark, sigma...)
            duration: المدة المطلوبة بالثواني

        Returns:
            مسار ملف الموسيقى أو None
        """
        # تطبيع الـ mood
        if mood not in self.MOOD_QUERIES:
            logger.warning(f"⚠ Mood '{mood}' غير معروف، استخدام 'motivation'")
            mood = "motivation"

        # 1️⃣ البحث في الكاش
        cached = self._find_cached(mood)
        if cached:
            logger.info(f"🎵 موسيقى مخزّنة [{mood}]: {Path(cached).name}")
            return cached

        # 2️⃣ Pixabay (الأساسي)
        if self.pixabay_key:
            logger.info(f"🎵 تحميل من Pixabay [{mood}]...")
            downloaded = self._download_from_pixabay(mood, duration)
            if downloaded:
                logger.info(f"✓ Pixabay: {Path(downloaded).name}")
                return downloaded
            logger.warning("⚠ فشل Pixabay")

        # 3️⃣ YouTube (احتياطي - قد يفشل في الـ Cloud)
        if self.enable_youtube_fallback:
            logger.info(f"🎵 محاولة YouTube [{mood}]...")
            downloaded = self._download_from_youtube(mood)
            if downloaded:
                logger.info(f"✓ YouTube: {Path(downloaded).name}")
                return downloaded
            logger.warning("⚠ فشل YouTube")

        # 4️⃣ أي موسيقى موجودة (fallback أخير)
        any_music = self._find_any()
        if any_music:
            logger.info(f"🎵 fallback: {Path(any_music).name}")
            return any_music

        logger.warning("⚠ لا توجد موسيقى متاحة")
        return None

    # ════════════════════════════════════════════════════════════════
    #                    Pixabay (الأساسي)
    # ════════════════════════════════════════════════════════════════
    def _download_from_pixabay(
        self,
        mood: str,
        target_duration: float,
    ) -> Optional[str]:
        """تحميل موسيقى من Pixabay API."""
        if not self.pixabay_key:
            return None

        # الحصول على قائمة كلمات البحث
        keywords = self.MOOD_QUERIES.get(mood, ["motivation"])
        query = random.choice(keywords)

        try:
            params = {
                "key": self.pixabay_key,
                "q": query,
                "category": "music",
                "per_page": 20,
                "safesearch": "true",
            }

            response = requests.get(
                self.PIXABAY_API,
                params=params,
                timeout=30,
            )

            if response.status_code != 200:
                logger.warning(f"⚠ Pixabay HTTP {response.status_code}")
                return None

            data = response.json()
            hits = data.get("hits", [])

            if not hits:
                logger.warning(f"⚠ لا توجد نتائج لـ '{query}'")
                return None

            # اختر موسيقى مناسبة للمدة (±50% من المطلوب)
            min_dur = target_duration * 0.8
            max_dur = target_duration * 5  # نسمح بأطول للسماح بالقص

            suitable = [
                h for h in hits
                if min_dur <= h.get("duration", 0) <= max_dur
            ]

            # إذا لم يجد مناسبة، استخدم أي شيء
            track = random.choice(suitable) if suitable else random.choice(hits)

            # تحميل الملف
            audio_url = track.get("audio") or track.get("url")
            if not audio_url:
                logger.warning("⚠ لا يوجد رابط صوت")
                return None

            track_id = track.get("id", random.randint(1000, 9999))
            output_path = self.music_dir / mood / f"{mood}_{track_id}.mp3"
            output_path.parent.mkdir(exist_ok=True)

            return self._download_file(audio_url, output_path)

        except requests.exceptions.RequestException as e:
            logger.error(f"❌ خطأ شبكة Pixabay: {e}")
        except Exception as e:
            logger.error(f"❌ خطأ Pixabay: {e}")

        return None

    def _download_file(self, url: str, output_path: Path) -> Optional[str]:
        """تحميل ملف من URL مع streaming."""
        try:
            response = requests.get(url, stream=True, timeout=self.timeout)
            response.raise_for_status()

            with open(output_path, "wb") as f:
                for chunk in response.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)

            if output_path.exists() and output_path.stat().st_size > 10000:
                return str(output_path)

            logger.warning("⚠ الملف صغير جداً")
            output_path.unlink(missing_ok=True)

        except Exception as e:
            logger.error(f"❌ فشل التحميل: {e}")
            output_path.unlink(missing_ok=True)

        return None

    # ════════════════════════════════════════════════════════════════
    #                    YouTube (احتياطي)
    # ════════════════════════════════════════════════════════════════
    def _download_from_youtube(self, mood: str) -> Optional[str]:
        """تحميل موسيقى من YouTube عبر yt-dlp (احتياطي)."""
        try:
            query = self.YOUTUBE_QUERIES.get(mood, self.YOUTUBE_QUERIES["motivation"])
            outdir = self.music_dir / mood
            outdir.mkdir(exist_ok=True)
            outfile = str(outdir / f"{mood}_yt_%(id)s.mp3")

            result = subprocess.run(
                [
                    "yt-dlp",
                    f"ytsearch1:{query}",
                    "--extract-audio",
                    "--audio-format", "mp3",
                    "--audio-quality", "5",
                    "--max-filesize", "15m",
                    "--no-playlist",
                    "--match-filter", "duration < 600",  # أقل من 10 دقائق
                    "-o", outfile,
                    "--quiet",
                    "--no-warnings",
                ],
                capture_output=True,
                timeout=self.timeout,
            )

            if result.returncode == 0:
                # ابحث عن الملف الذي تم تحميله
                downloaded = list(outdir.glob(f"{mood}_yt_*.mp3"))
                if downloaded:
                    file_path = str(downloaded[-1])
                    if Path(file_path).stat().st_size > 10000:
                        return file_path

        except subprocess.TimeoutExpired:
            logger.warning("⚠ Timeout في تحميل YouTube")
        except FileNotFoundError:
            logger.warning("⚠ yt-dlp غير مثبت")
        except Exception as e:
            logger.error(f"❌ خطأ YouTube: {e}")

        return None

    # ════════════════════════════════════════════════════════════════
    #                    Caching
    # ════════════════════════════════════════════════════════════════
    def _find_cached(self, mood: str) -> Optional[str]:
        """البحث في الموسيقى المخزّنة."""
        # 1. مجلد الـ mood
        mood_dir = self.music_dir / mood
        if mood_dir.exists():
            files = self._get_audio_files(mood_dir)
            if files:
                # اختيار عشوائي للتنويع
                return str(random.choice(files))

        # 2. البحث بالاسم في المجلد الرئيسي
        all_files = self._get_audio_files(self.music_dir)
        matching = [f for f in all_files if mood in f.name.lower()]
        if matching:
            return str(random.choice(matching))

        return None

    def _find_any(self) -> Optional[str]:
        """العثور على أي موسيقى متاحة."""
        all_files = []
        for ext in ("*.mp3", "*.wav", "*.m4a", "*.ogg"):
            all_files.extend(self.music_dir.rglob(ext))

        return str(random.choice(all_files)) if all_files else None

    @staticmethod
    def _get_audio_files(directory: Path) -> List[Path]:
        """الحصول على ملفات صوتية في مجلد."""
        files = []
        for ext in ("*.mp3", "*.wav", "*.m4a", "*.ogg"):
            files.extend(directory.glob(ext))
        return files

    # ════════════════════════════════════════════════════════════════
    #                    دوال إضافية
    # ════════════════════════════════════════════════════════════════
    def list_available_moods(self) -> List[str]:
        """قائمة الـ moods المتاحة."""
        return list(self.MOOD_QUERIES.keys())

    def get_cached_count(self) -> dict:
        """عدد الملفات المخزنة لكل mood."""
        result = {}
        for mood in self.MOOD_QUERIES.keys():
            mood_dir = self.music_dir / mood
            if mood_dir.exists():
                result[mood] = len(self._get_audio_files(mood_dir))
            else:
                result[mood] = 0
        return result

    def clear_cache(self, mood: Optional[str] = None) -> int:
        """مسح الكاش (لـ mood محدد أو الكل)."""
        count = 0
        try:
            if mood:
                mood_dir = self.music_dir / mood
                if mood_dir.exists():
                    for f in self._get_audio_files(mood_dir):
                        f.unlink()
                        count += 1
            else:
                for f in self._get_audio_files(self.music_dir):
                    f.unlink()
                    count += 1
                for sub in self.music_dir.iterdir():
                    if sub.is_dir():
                        for f in self._get_audio_files(sub):
                            f.unlink()
                            count += 1
            logger.info(f"🧹 تم مسح {count} ملف")
        except Exception as e:
            logger.error(f"❌ فشل مسح الكاش: {e}")
        return count


# ════════════════════════════════════════════════════════════════════════
#                    اختبار سريع
# ════════════════════════════════════════════════════════════════════════
if __name__ == "__main__":
    import sys

    engine = MusicEngine()
    
    # عرض الكاش
    cache = engine.get_cached_count()
    print("📊 Cache status:")
    for mood, count in cache.items():
        print(f"  {mood}: {count} files")

    # تحميل تجريبي
    mood = sys.argv[1] if len(sys.argv) > 1 else "motivation"
    duration = float(sys.argv[2]) if len(sys.argv) > 2 else 45.0

    print(f"\n🎵 Getting music for mood='{mood}', duration={duration}s")
    music = engine.get_music(mood, duration)
    print(f"✓ Result: {music}")
