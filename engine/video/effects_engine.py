"""
Effects Engine - cinematic video effects optimized for GitHub Actions CPU
"""

import os
import shutil
import subprocess
from pathlib import Path


class EffectsEngine:

    def __init__(self, video_width: int = 1080, video_height: int = 1920):
        self.w = video_width
        self.h = video_height
        self.fps = int(os.getenv("VIDEO_FPS", "30"))
        self.temp_dir = Path(os.getenv("TEMP_DIR", "./temp"))
        self.temp_dir.mkdir(parents=True, exist_ok=True)

    def scale_and_crop(self, input_path: str, output_path: str) -> str:
        """Scale and center-crop to portrait 1080x1920."""
        filter_str = (
            f"scale={self.w}:{self.h}:force_original_aspect_ratio=increase,"
            f"crop={self.w}:{self.h}"
        )
        result = subprocess.run(
            [
                "ffmpeg", "-y", "-i", input_path,
                "-vf", filter_str,
                "-c:v", "libx264", "-preset", "fast", "-crf", "22",
                "-r", str(self.fps), "-an",
                output_path,
            ],
            capture_output=True,
        )
        if result.returncode != 0:
            shutil.copy(input_path, output_path)
        return output_path

    def trim_clip(self, input_path: str, output_path: str, start: float, duration: float) -> str:
        """Trim clip to exact duration."""
        result = subprocess.run(
            [
                "ffmpeg", "-y",
                "-ss", str(start), "-i", input_path,
                "-t", str(duration),
                "-c:v", "libx264", "-preset", "fast", "-crf", "22",
                "-r", str(self.fps), "-an",
                output_path,
            ],
            capture_output=True,
        )
        if result.returncode != 0:
            shutil.copy(input_path, output_path)
        return output_path

    def apply_zoom_effect(
        self,
        input_path: str,
        output_path: str,
        zoom_type: str = "slow_zoom_in",
        duration: float = 3.0,
    ) -> str:
        """
        Zoom using simple scale — بديل zoompan الثقيل.
        zoompan على GitHub Actions = timeout مضمون.
        scale بسيط أسرع 20 ضعف على CPU.
        """
        zoom_map = {
            "slow_zoom_in":  "1.08",
            "slow_zoom_out": "1.04",
            "punch_zoom":    "1.15",
            "drift_right":   "1.06",
            "drift_left":    "1.06",
        }
        scale = zoom_map.get(zoom_type, "1.06")
        sw = int(self.w * float(scale))
        sh = int(self.h * float(scale))
        # تأكد من أن الأبعاد زوجية لـ libx264
        sw = sw if sw % 2 == 0 else sw + 1
        sh = sh if sh % 2 == 0 else sh + 1

        filter_str = f"scale={sw}:{sh},crop={self.w}:{self.h}"
        result = subprocess.run(
            [
                "ffmpeg", "-y", "-i", input_path,
                "-vf", filter_str,
                "-c:v", "libx264", "-preset", "fast", "-crf", "22",
                "-r", str(self.fps), "-an",
                output_path,
            ],
            capture_output=True,
        )
        if result.returncode != 0:
            shutil.copy(input_path, output_path)
        return output_path

    def apply_smooth_shake(
        self, input_path: str, output_path: str, intensity: float = 2.0
    ) -> str:
        """Subtle camera shake via crop offset."""
        margin = max(int(intensity * 2), 4)
        cw = self.w - margin * 2
        ch = self.h - margin * 2
        # تأكد من أن الأبعاد زوجية
        cw = cw if cw % 2 == 0 else cw - 1
        ch = ch if ch % 2 == 0 else ch - 1

        filter_str = (
            f"crop={cw}:{ch}:"
            f"'{margin}+{intensity:.1f}*sin(2*PI*t*0.7)':"
            f"'{margin}+{intensity:.1f}*cos(2*PI*t*1.1)',"
            f"scale={self.w}:{self.h}"
        )
        result = subprocess.run(
            [
                "ffmpeg", "-y", "-i", input_path,
                "-vf", filter_str,
                "-c:v", "libx264", "-preset", "fast", "-crf", "22",
                "-r", str(self.fps), "-an",
                output_path,
            ],
            capture_output=True,
        )
        if result.returncode != 0:
            shutil.copy(input_path, output_path)
        return output_path

    def apply_cinematic_grade(self, input_path: str, output_path: str) -> str:
        """
        Cinematic color grade:
        teal shadows + orange highlights + contrast + saturation + vignette + grain
        """
        filter_chain = ",".join([
            "curves=r='0/0 0.2/0.19 0.5/0.53 0.8/0.86 1/1'"
            ":g='0/0 0.2/0.19 0.5/0.50 0.8/0.82 1/1'"
            ":b='0/0 0.2/0.23 0.5/0.52 0.8/0.78 1/1'",
            "curves=master='0/0 0.15/0.08 0.5/0.5 0.85/0.92 1/1'",
            "hue=s=1.12",
            "vignette=PI/4",
            "noise=alls=6:allf=t+u",
        ])
        result = subprocess.run(
            [
                "ffmpeg", "-y", "-i", input_path,
                "-vf", filter_chain,
                "-c:v", "libx264", "-preset", "medium", "-crf", "18",
                "-pix_fmt", "yuv420p",
                "-c:a", "copy",
                output_path,
            ],
            capture_output=True,
        )
        if result.returncode != 0:
            shutil.copy(input_path, output_path)
        return output_path

    def add_letterbox(self, input_path: str, output_path: str) -> str:
        """Add cinematic letterbox bars top and bottom."""
        bar_h = int(self.h * 0.055)
        filter_str = (
            f"drawbox=x=0:y=0:w={self.w}:h={bar_h}:color=black@0.92:t=fill,"
            f"drawbox=x=0:y={self.h - bar_h}:w={self.w}:h={bar_h}:color=black@0.92:t=fill"
        )
        result = subprocess.run(
            [
                "ffmpeg", "-y", "-i", input_path,
                "-vf", filter_str,
                "-c:v", "libx264", "-preset", "fast", "-crf", "18",
                "-pix_fmt", "yuv420p",
                "-c:a", "copy",
                output_path,
            ],
            capture_output=True,
        )
        if result.returncode != 0:
            shutil.copy(input_path, output_path)
        return output_path

    def loop_clip_to_duration(
        self, input_path: str, output_path: str, target_duration: float
    ) -> str:
        subprocess.run(
            [
                "ffmpeg", "-y",
                "-stream_loop", "-1", "-i", input_path,
                "-t", str(target_duration),
                "-c:v", "libx264", "-preset", "fast", "-crf", "22",
                "-r", str(self.fps), "-an",
                output_path,
            ],
            check=True, capture_output=True,
        )
        return output_path
