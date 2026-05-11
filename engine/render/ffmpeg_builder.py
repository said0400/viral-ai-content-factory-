"""
FFmpeg Builder - final render and encoding
"""

import os
import json
import shutil
import subprocess
from pathlib import Path


class FFmpegBuilder:

    PRESETS = {
        "tiktok":  {"crf": "18", "preset": "slow",     "ab": "192k", "ar": "44100"},
        "reels":   {"crf": "17", "preset": "slow",     "ab": "256k", "ar": "48000"},
        "preview": {"crf": "24", "preset": "veryfast", "ab": "128k", "ar": "44100"},
    }

    def __init__(self):
        self.w   = int(os.getenv("VIDEO_WIDTH",  "1080"))
        self.h   = int(os.getenv("VIDEO_HEIGHT", "1920"))
        self.fps = int(os.getenv("VIDEO_FPS",    "30"))
        self.temp_dir  = Path(os.getenv("TEMP_DIR",   "./temp"))
        self.out_dir   = Path(os.getenv("OUTPUT_DIR", "./output"))
        self.temp_dir.mkdir(parents=True, exist_ok=True)
        self.out_dir.mkdir(parents=True, exist_ok=True)
        self._check_ffmpeg()

    def _check_ffmpeg(self):
        try:
            r = subprocess.run(
                ["ffmpeg", "-version"],
                capture_output=True, text=True, check=True,
            )
            print(f"  ✓ {r.stdout.splitlines()[0]}")
        except (subprocess.CalledProcessError, FileNotFoundError):
            raise RuntimeError(
                "FFmpeg not found.\n"
                "  Ubuntu: sudo apt install ffmpeg\n"
                "  macOS:  brew install ffmpeg"
            )

    def render_final(
        self,
        input_video: str,
        output_path: str,
        preset: str = "tiktok",
        metadata: dict = None,
    ) -> str:
        s = self.PRESETS.get(preset, self.PRESETS["tiktok"])
        metadata = metadata or {}

        cmd = [
            "ffmpeg", "-y", "-i", input_video,
            "-c:v", "libx264",
            "-crf", s["crf"],
            "-preset", s["preset"],
            "-profile:v", "high",
            "-level:v", "4.1",
            "-pix_fmt", "yuv420p",
            "-r", str(self.fps),
            "-c:a", "aac",
            "-b:a", s["ab"],
            "-ar", s["ar"],
            "-movflags", "+faststart",
        ]
        if metadata.get("title"):
            cmd += ["-metadata", f"title={metadata['title']}"]
        if metadata.get("description"):
            cmd += ["-metadata", f"comment={metadata['description']}"]
        cmd.append(output_path)

        subprocess.run(cmd, check=True, capture_output=True)

        mb  = os.path.getsize(output_path) / 1024 / 1024
        dur = self.get_duration(output_path)
        print(f"  ✓ {output_path}")
        print(f"    {mb:.1f} MB | {dur:.1f}s | {self.w}x{self.h} | {self.fps}fps")
        return output_path

    def get_duration(self, path: str) -> float:
        r = subprocess.run(
            ["ffprobe", "-v", "quiet", "-print_format", "json", "-show_format", path],
            capture_output=True, text=True, check=True,
        )
        return float(json.loads(r.stdout)["format"]["duration"])

    def get_dimensions(self, path: str) -> tuple:
        r = subprocess.run(
            ["ffprobe", "-v", "quiet", "-print_format", "json", "-show_streams", path],
            capture_output=True, text=True, check=True,
        )
        for s in json.loads(r.stdout).get("streams", []):
            if s.get("codec_type") == "video":
                return int(s["width"]), int(s["height"])
        return self.w, self.h

    def create_thumbnail(self, video: str, output: str, ts: float = 1.5) -> str:
        subprocess.run(
            [
                "ffmpeg", "-y",
                "-ss", str(ts), "-i", video,
                "-vframes", "1", "-q:v", "2",
                output,
            ],
            check=True, capture_output=True,
        )
        return output

    def cleanup_temp(self) -> None:
        if self.temp_dir.exists():
            shutil.rmtree(self.temp_dir)
            self.temp_dir.mkdir(parents=True)
            print("  ✓ Temp cleaned.")
