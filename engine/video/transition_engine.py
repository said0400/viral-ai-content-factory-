"""
Transition Engine - xfade transitions with FPS normalization
"""

import os
import json
import random
import shutil
import subprocess
from pathlib import Path


class TransitionEngine:

    ENERGY_HIGH = ["fadeblack", "zoomin", "pixelize", "wipeleft"]
    ENERGY_LOW  = ["fade", "wipeleft", "wiperight", "slideup"]
    ALL         = ENERGY_HIGH + ENERGY_LOW

    def __init__(self, video_width: int = 1080, video_height: int = 1920):
        self.w = video_width
        self.h = video_height
        self.fps = int(os.getenv("VIDEO_FPS", "30"))
        self.temp_dir = Path(os.getenv("TEMP_DIR", "./temp"))
        self.temp_dir.mkdir(parents=True, exist_ok=True)

    def apply_transition(
        self,
        clip_a: str,
        clip_b: str,
        output_path: str,
        transition_type: str = "auto",
        duration: float = 0.2,
    ) -> str:
        """xfade transition مع FPS normalization للتوافق."""
        pid = os.getpid()
        na = str(self.temp_dir / f"na_{pid}_{random.randint(1000,9999)}.mp4")
        nb = str(self.temp_dir / f"nb_{pid}_{random.randint(1000,9999)}.mp4")

        self._normalize(clip_a, na)
        self._normalize(clip_b, nb)

        xfade = self._pick_xfade(transition_type)
        dur_a = self._get_duration(na)
        offset = max(dur_a - duration - 0.01, 0.0)

        result = subprocess.run(
            [
                "ffmpeg", "-y",
                "-i", na, "-i", nb,
                "-filter_complex",
                (
                    f"[0:v][1:v]xfade="
                    f"transition={xfade}:"
                    f"duration={duration:.2f}:"
                    f"offset={offset:.3f}[outv]"
                ),
                "-map", "[outv]",
                "-c:v", "libx264", "-preset", "fast", "-crf", "20",
                "-pix_fmt", "yuv420p", "-an",
                output_path,
            ],
            capture_output=True,
        )
        if result.returncode != 0:
            self._concat(na, nb, output_path)
        return output_path

    def _normalize(self, input_path: str, output_path: str) -> str:
        """Force same FPS و pixel format لتجنب xfade errors."""
        result = subprocess.run(
            [
                "ffmpeg", "-y", "-i", input_path,
                "-vf", f"fps={self.fps},scale={self.w}:{self.h}:force_original_aspect_ratio=decrease,pad={self.w}:{self.h}:(ow-iw)/2:(oh-ih)/2",
                "-c:v", "libx264", "-preset", "ultrafast", "-crf", "23",
                "-pix_fmt", "yuv420p", "-an",
                output_path,
            ],
            capture_output=True,
        )
        if result.returncode != 0:
            shutil.copy(input_path, output_path)
        return output_path

    def _pick_xfade(self, t: str) -> str:
        mapping = {
            "auto":          lambda: random.choice(self.ALL),
            "flash_white":   lambda: "fadewhite",
            "flash_black":   lambda: "fadeblack",
            "glitch":        lambda: "pixelize",
            "zoom_burst":    lambda: "zoomin",
            "whip_right":    lambda: "wipeleft",
            "whip_left":     lambda: "wiperight",
            "fade_black":    lambda: "fadeblack",
            "cross_dissolve":lambda: "fade",
            "push_up":       lambda: "slideup",
            "push_down":     lambda: "slidedown",
        }
        fn = mapping.get(t)
        if fn:
            return fn()
        return random.choice(self.ALL)

    def _get_duration(self, path: str) -> float:
        try:
            r = subprocess.run(
                ["ffprobe", "-v", "quiet", "-print_format", "json", "-show_format", path],
                capture_output=True, text=True, check=True,
            )
            return float(json.loads(r.stdout)["format"]["duration"])
        except Exception:
            return 3.0

    def _concat(self, a: str, b: str, output_path: str) -> str:
        lst = self.temp_dir / f"cat_{os.getpid()}.txt"
        with open(lst, "w") as f:
            f.write(f"file '{os.path.abspath(a)}'\n")
            f.write(f"file '{os.path.abspath(b)}'\n")
        subprocess.run(
            [
                "ffmpeg", "-y",
                "-f", "concat", "-safe", "0", "-i", str(lst),
                "-c:v", "libx264", "-preset", "fast", "-crf", "22",
                "-pix_fmt", "yuv420p", "-an",
                output_path,
            ],
            capture_output=True,
        )
        return output_path

    def get_random_transition(self, high_energy: bool = False) -> str:
        return random.choice(self.ENERGY_HIGH if high_energy else self.ENERGY_LOW)
