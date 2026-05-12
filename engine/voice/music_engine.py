"""
Music Engine — تحميل موسيقى تلقائية من YouTube حسب الـ mood
"""

import os
import subprocess
from pathlib import Path


class MusicEngine:

    MOOD_QUERIES = {
        "epic":         "epic cinematic background music no copyright royalty free",
        "emotional":    "emotional sad cinematic music no copyright royalty free",
        "motivational": "motivational inspiring background music no copyright royalty free",
        "calm":         "calm peaceful meditation background music no copyright royalty free",
        "dramatic":     "dramatic tense cinematic music no copyright royalty free",
        "romantic":     "romantic soft background music no copyright royalty free",
        "dark":         "dark mysterious cinematic music no copyright royalty free",
        "intelligence": "deep thinking focus background music no copyright royalty free",
    }

    def __init__(self):
        self.music_dir = Path("engine/assets/music")
        self.music_dir.mkdir(parents=True, exist_ok=True)

    def get_music(self, mood: str, duration: float) -> str | None:
        mood = mood if mood in self.MOOD_QUERIES else "motivational"

        # 1. ابحث في الكاش أولاً
        cached = self._find_cached(mood)
        if cached:
            print(f"  🎵 Using cached music [{mood}]: {Path(cached).name}")
            return cached

        # 2. حمّل من YouTube
        print(f"  🎵 Downloading [{mood}] music from YouTube...")
        downloaded = self._download(mood)
        if downloaded:
            print(f"  ✓ Music ready: {Path(downloaded).name}")
            return downloaded

        # 3. جرب أي ملف موسيقى موجود
        any_music = self._find_any()
        if any_music:
            print(f"  ⚠️ Using fallback music: {Path(any_music).name}")
            return any_music

        print("  ⚠️ No music available")
        return None

    def _find_cached(self, mood: str) -> str | None:
        # ابحث في مجلد الـ mood
        mood_dir = self.music_dir / mood
        if mood_dir.exists():
            files = list(mood_dir.glob("*.mp3")) + list(mood_dir.glob("*.wav"))
            if files:
                return str(files[0])
        # ابحث في المجلد الرئيسي بالاسم
        all_files = list(self.music_dir.glob("*.mp3")) + list(self.music_dir.glob("*.wav"))
        for f in all_files:
            if mood in f.name.lower():
                return str(f)
        return None

    def _find_any(self) -> str | None:
        files = list(self.music_dir.rglob("*.mp3")) + list(self.music_dir.rglob("*.wav"))
        return str(files[0]) if files else None

    def _download(self, mood: str) -> str | None:
        try:
            query   = self.MOOD_QUERIES[mood]
            outdir  = self.music_dir / mood
            outdir.mkdir(exist_ok=True)
            outfile = str(outdir / f"{mood}_music.mp3")

            result = subprocess.run([
                "yt-dlp",
                f"ytsearch1:{query}",
                "--extract-audio",
                "--audio-format", "mp3",
                "--audio-quality", "5",
                "--max-filesize", "15m",
                "--no-playlist",
                "-o", outfile,
                "--quiet",
                "--no-warnings",
            ], capture_output=True, timeout=90)

            if result.returncode == 0 and Path(outfile).exists():
                if Path(outfile).stat().st_size > 1000:
                    return outfile

        except subprocess.TimeoutExpired:
            print("  ⚠️ Music download timeout")
        except FileNotFoundError:
            print("  ⚠️ yt-dlp not installed — add to requirements.txt")
        except Exception as e:
            print(f"  ⚠️ Download error: {e}")

        return None
