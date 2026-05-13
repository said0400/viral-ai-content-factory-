"""
Effects Engine — مُصلح
إصلاح: الـ zoom كان ثابتاً (scale واحد)
الآن يستخدم zoompan للحركة التدريجية الحقيقية
مع fallback سريع لـ GitHub Actions CPU

ضع هذا الملف في: engine/video/effects_engine.py
"""

import os
import shutil
import subprocess
from pathlib import Path


class EffectsEngine:

    def __init__(self, video_width: int = 1080, video_height: int = 1920):
        self.w       = video_width
        self.h       = video_height
        self.fps     = int(os.getenv("VIDEO_FPS", "30"))
        self.temp_dir = Path(os.getenv("TEMP_DIR", "./temp"))
        self.temp_dir.mkdir(parents=True, exist_ok=True)

    # ─── scale + crop إلى portrait ──────────────────────────────────────────

    def scale_and_crop(self, input_path: str, output_path: str) -> str:
        filter_str = (
            f"scale={self.w}:{self.h}:force_original_aspect_ratio=increase,"
            f"crop={self.w}:{self.h}"
        )
        r = subprocess.run(
            ["ffmpeg", "-y", "-i", input_path,
             "-vf", filter_str,
             "-c:v", "libx264", "-preset", "fast", "-crf", "22",
             "-r", str(self.fps), "-an", output_path],
            capture_output=True,
        )
        if r.returncode != 0:
            shutil.copy(input_path, output_path)
        return output_path

    # ─── trim دقيق ──────────────────────────────────────────────────────────

    def trim_clip(self, input_path: str, output_path: str,
                  start: float, duration: float) -> str:
        r = subprocess.run(
            ["ffmpeg", "-y",
             "-ss", str(start), "-i", input_path,
             "-t", str(duration),
             "-c:v", "libx264", "-preset", "fast", "-crf", "22",
             "-r", str(self.fps), "-an", output_path],
            capture_output=True,
        )
        if r.returncode != 0:
            shutil.copy(input_path, output_path)
        return output_path

    # ─── zoom متحرك حقيقي ───────────────────────────────────────────────────

    def apply_zoom_effect(
        self, input_path: str, output_path: str,
        zoom_type: str = "slow_zoom_in", duration: float = 3.0,
    ) -> str:
        """
        إصلاح: الآن حركة تدريجية حقيقية بدل scale ثابت.
        يستخدم zoompan لـ slow_zoom.
        للأنواع السريعة يبقى scale (أسرع على CPU).
        """
        # أنواع الـ zoom
        if zoom_type == "slow_zoom_in":
            return self._zoompan(input_path, output_path, duration,
                                 z_start=1.0, z_end=1.12, x_expr="iw/2-(iw/zoom/2)", y_expr="ih/2-(ih/zoom/2)")

        elif zoom_type == "slow_zoom_out":
            return self._zoompan(input_path, output_path, duration,
                                 z_start=1.12, z_end=1.0, x_expr="iw/2-(iw/zoom/2)", y_expr="ih/2-(ih/zoom/2)")

        elif zoom_type == "drift_right":
            return self._zoompan(input_path, output_path, duration,
                                 z_start=1.06, z_end=1.06,
                                 x_expr="(iw-iw/zoom)*on/duration",
                                 y_expr="ih/2-(ih/zoom/2)")

        elif zoom_type == "drift_left":
            return self._zoompan(input_path, output_path, duration,
                                 z_start=1.06, z_end=1.06,
                                 x_expr="(iw-iw/zoom)*(1-on/duration)",
                                 y_expr="ih/2-(ih/zoom/2)")

        elif zoom_type == "punch_zoom":
            # scale سريع — مناسب لـ hook و peak
            return self._static_scale(input_path, output_path, 1.15)

        else:
            return self._static_scale(input_path, output_path, 1.06)

    def _zoompan(self, inp: str, out: str, duration: float,
                 z_start: float, z_end: float,
                 x_expr: str, y_expr: str) -> str:
        """
        zoompan يُنتج حركة تدريجية حقيقية frame by frame.
        duration بالثواني → عدد الـ frames = duration * fps
        """
        n_frames = max(int(duration * self.fps), 1)

        # معادلة الـ zoom التدريجي
        z_delta = z_end - z_start
        z_expr  = f"{z_start}+{z_delta:.4f}*on/{n_frames}" if z_delta != 0 else str(z_start)

        filter_str = (
            f"zoompan=z='{z_expr}':"
            f"x='{x_expr}':y='{y_expr}':"
            f"d={n_frames}:s={self.w}x{self.h}:fps={self.fps},"
            f"trim=frames={n_frames},"
            f"setpts=PTS-STARTPTS"
        )

        r = subprocess.run(
            ["ffmpeg", "-y", "-i", inp,
             "-vf", filter_str,
             "-c:v", "libx264", "-preset", "fast", "-crf", "22",
             "-r", str(self.fps), "-an", out],
            capture_output=True,
        )
        if r.returncode != 0:
            # fallback إلى scale ثابت إذا فشل zoompan
            return self._static_scale(inp, out, (z_start + z_end) / 2)
        return out

    def _static_scale(self, inp: str, out: str, scale: float) -> str:
        sw = int(self.w * scale)
        sh = int(self.h * scale)
        sw = sw if sw % 2 == 0 else sw + 1
        sh = sh if sh % 2 == 0 else sh + 1

        r = subprocess.run(
            ["ffmpeg", "-y", "-i", inp,
             "-vf", f"scale={sw}:{sh},crop={self.w}:{self.h}",
             "-c:v", "libx264", "-preset", "fast", "-crf", "22",
             "-r", str(self.fps), "-an", out],
            capture_output=True,
        )
        if r.returncode != 0:
            shutil.copy(inp, out)
        return out

    # ─── camera shake ────────────────────────────────────────────────────────

    def apply_smooth_shake(self, input_path: str, output_path: str,
                           intensity: float = 2.0) -> str:
        margin = max(int(intensity * 2), 4)
        cw = (self.w - margin * 2)
        ch = (self.h - margin * 2)
        cw = cw if cw % 2 == 0 else cw - 1
        ch = ch if ch % 2 == 0 else ch - 1

        filter_str = (
            f"crop={cw}:{ch}:"
            f"'{margin}+{intensity:.1f}*sin(2*PI*t*0.7)':"
            f"'{margin}+{intensity:.1f}*cos(2*PI*t*1.1)',"
            f"scale={self.w}:{self.h}"
        )
        r = subprocess.run(
            ["ffmpeg", "-y", "-i", input_path,
             "-vf", filter_str,
             "-c:v", "libx264", "-preset", "fast", "-crf", "22",
             "-r", str(self.fps), "-an", output_path],
            capture_output=True,
        )
        if r.returncode != 0:
            shutil.copy(input_path, output_path)
        return output_path

    # ─── loop لملء المدة ─────────────────────────────────────────────────────

    def loop_clip_to_duration(self, input_path: str, output_path: str,
                               target_duration: float) -> str:
        """
        إصلاح #3: يُستدعى الآن قبل trim في _process_clips.
        يمنع freeze frame عندما يكون الـ footage أقصر من مدة المشهد.
        """
        r = subprocess.run(
            ["ffmpeg", "-y",
             "-stream_loop", "-1", "-i", input_path,
             "-t", str(target_duration),
             "-c:v", "libx264", "-preset", "fast", "-crf", "22",
             "-r", str(self.fps), "-an", output_path],
            capture_output=True,
        )
        if r.returncode != 0:
            shutil.copy(input_path, output_path)
        return output_path

    # ─── cinematic grade ─────────────────────────────────────────────────────

    def apply_cinematic_grade(self, input_path: str, output_path: str) -> str:
        filter_chain = ",".join([
            "curves=r='0/0 0.2/0.19 0.5/0.53 0.8/0.86 1/1'"
            ":g='0/0 0.2/0.19 0.5/0.50 0.8/0.82 1/1'"
            ":b='0/0 0.2/0.23 0.5/0.52 0.8/0.78 1/1'",
            "curves=master='0/0 0.15/0.08 0.5/0.5 0.85/0.92 1/1'",
            "hue=s=1.12",
            "vignette=PI/4",
            "noise=alls=6:allf=t+u",
        ])
        r = subprocess.run(
            ["ffmpeg", "-y", "-i", input_path,
             "-vf", filter_chain,
             "-c:v", "libx264", "-preset", "medium", "-crf", "18",
             "-pix_fmt", "yuv420p", "-c:a", "copy", output_path],
            capture_output=True,
        )
        if r.returncode != 0:
            shutil.copy(input_path, output_path)
        return output_path

    # ─── letterbox ───────────────────────────────────────────────────────────

    def add_letterbox(self, input_path: str, output_path: str) -> str:
        bar_h = int(self.h * 0.055)
        filter_str = (
            f"drawbox=x=0:y=0:w={self.w}:h={bar_h}:color=black@0.92:t=fill,"
            f"drawbox=x=0:y={self.h-bar_h}:w={self.w}:h={bar_h}:color=black@0.92:t=fill"
        )
        r = subprocess.run(
            ["ffmpeg", "-y", "-i", input_path,
             "-vf", filter_str,
             "-c:v", "libx264", "-preset", "fast", "-crf", "18",
             "-pix_fmt", "yuv420p", "-c:a", "copy", output_path],
            capture_output=True,
        )
        if r.returncode != 0:
            shutil.copy(input_path, output_path)
        return output_path
