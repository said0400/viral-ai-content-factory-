"""
Music Engine — تحميل موسيقى تلقائية من YouTube حسب الـ mood
"""

import os
import subprocess
from pathlib import Path


class MusicEngine:

    # كلمات بحث YouTube لكل mood
    MOOD_QUERIES = {
        "epic":         "epic cinematic background music no copyright",
        "emotional":    "emotional sad cinematic music no copyright",
        "motivational": "motivational inspiring background music no copyright",
        "calm":         "calm peaceful arabic background music no copyright",
        "dramatic":     "dramatic tense cinematic music no copyright",
        "romantic":     "romantic arabic background music no copyright",
        "dark":         "dark mysterious cinematic music no copyright",
    }

    def __init__(self):
        self.music_dir = Path("engine/assets/music")
        self.music_dir.mkdir(parents=True, exist_ok=True)

    def get_music(self, mood: str, duration: float) -> str | None:
        """
        يبحث عن موسيقى محفوظة أولاً، ثم يحمل من YouTube إذا لم توجد
        """
        mood = mood if mood in self.MOOD_QUERIES else "motivational"

        # 1. ابحث في الملفات المحفوظة
        cached = self._find_cached(mood)
        if cached:
            print(f"  🎵 Using cached music: {cached}")
            return cached

        # 2. حمّل من YouTube
        print(f"  🎵 Downloading {mood} music from YouTube...")
        result = self._download(mood)
        if result:
            print(f"  ✓ Music downloaded: {result}")
            return result

        print("  ⚠️ No music available")
        return None

    def _find_cached(self, mood: str) -> str | None:
        """يبحث عن ملف موسيقى محفوظ لهذا الـ mood"""
        mood_dir = self.music_dir / mood
        if mood_dir.exists():
            files = list(mood_dir.glob("*.mp3")) + list(mood_dir.glob("*.wav"))
            if files:
                return str(files[0])

        # ابحث في المجلد العام
        all_files = list(self.music_dir.glob("*.mp3")) + list(self.music_dir.glob("*.wav"))
        mood_files = [f for f in all_files if mood in f.name.lower()]
        if mood_files:
            return str(mood_files[0])

        return None

    def _download(self, mood: str) -> str | None:
        """يحمل موسيقى من YouTube بـ yt-dlp"""
        try:
            query  = self.MOOD_QUERIES[mood]
            outdir = self.music_dir / mood
            outdir.mkdir(exist_ok=True)
            outfile = str(outdir / f"{mood}_music.mp3")

            result = subprocess.run([
                "yt-dlp",
                f"ytsearch1:{query}",          # أول نتيجة فقط
                "--extract-audio",
                "--audio-format", "mp3",
                "--audio-quality", "5",        # جودة متوسطة (سريع)
                "--max-filesize", "10m",        # حد 10MB
                "--no-playlist",
                "-o", outfile,
                "--quiet",
            ], capture_output=True, timeout=60)

            if result.returncode == 0 and Path(outfile).exists():
                return outfile

        except Exception as e:
            print(f"  ⚠️ yt-dlp error: {e}")

        return None
