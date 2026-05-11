"""
Breathing Engine - adds subtle inhale before voice
"""

import os
import shutil
import subprocess
from pathlib import Path


class BreathingEngine:

    def __init__(self):
        self.temp_dir = Path(os.getenv("TEMP_DIR", "./temp"))
        self.temp_dir.mkdir(parents=True, exist_ok=True)

    def add_breathing(self, voice_path: str, output_path: str) -> str:
        inhale = self._make_inhale()
        concat_list = self.temp_dir / f"breath_{os.getpid()}.txt"
        with open(concat_list, "w") as f:
            f.write(f"file '{os.path.abspath(inhale)}'\n")
            f.write(f"file '{os.path.abspath(voice_path)}'\n")
        result = subprocess.run(
            [
                "ffmpeg", "-y",
                "-f", "concat", "-safe", "0",
                "-i", str(concat_list),
                "-c:a", "libmp3lame", "-q:a", "2",
                output_path,
            ],
            capture_output=True,
        )
        if result.returncode != 0:
            shutil.copy(voice_path, output_path)
        return output_path

    def _make_inhale(self) -> str:
        path = str(self.temp_dir / "inhale.mp3")
        if os.path.exists(path):
            return path
        result = subprocess.run(
            [
                "ffmpeg", "-y",
                "-f", "lavfi",
                "-i", "anoisesrc=color=pink:duration=0.4:amplitude=0.012",
                "-af", "afade=t=in:st=0:d=0.15,afade=t=out:st=0.25:d=0.15,lowpass=f=700",
                "-ar", "44100", "-ac", "2",
                path,
            ],
            capture_output=True,
        )
        if result.returncode != 0:
            # fallback: silence
            subprocess.run(
                [
                    "ffmpeg", "-y",
                    "-f", "lavfi",
                    "-i", "anullsrc=r=44100:cl=stereo",
                    "-t", "0.4",
                    path,
                ],
                capture_output=True,
            )
        return path
