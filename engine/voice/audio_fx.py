"""
Audio FX Engine - cinematic voice processing and audio mixing
"""

import os
import json
import shutil
import subprocess
from pathlib import Path


class AudioFX:

    def __init__(self):
        self.temp_dir = Path(os.getenv("TEMP_DIR", "./temp"))
        self.temp_dir.mkdir(parents=True, exist_ok=True)

    def process_voice(self, voice_path: str, output_path: str) -> str:
        filter_chain = ",".join([
            "equalizer=f=200:width_type=o:width=2:g=3",
            "equalizer=f=3000:width_type=o:width=2:g=1",
            "equalizer=f=8000:width_type=o:width=2:g=-1",
            "compand=attacks=0.02:decays=0.15:points=-90/-90|-60/-30|-30/-15|-10/-8|0/-6:gain=4:volume=-90:delay=0.05",
            "aecho=0.8:0.7:40|50:0.25|0.15",
            "bass=g=3:f=80:width_type=o:width=0.8",
            "loudnorm=I=-14:TP=-2:LRA=7",
        ])
        result = subprocess.run(
            [
                "ffmpeg", "-y", "-i", voice_path,
                "-af", filter_chain,
                "-ar", "44100", "-ac", "2", "-b:a", "192k",
                output_path,
            ],
            capture_output=True,
        )
        if result.returncode != 0:
            result2 = subprocess.run(
                [
                    "ffmpeg", "-y", "-i", voice_path,
                    "-af", "loudnorm=I=-14:TP=-2:LRA=7",
                    "-ar", "44100", "-ac", "2", "-b:a", "192k",
                    output_path,
                ],
                capture_output=True,
            )
            if result2.returncode != 0:
                shutil.copy(voice_path, output_path)
        return output_path

    def process_music(self, music_path: str, output_path: str, volume: float = 0.20) -> str:
        subprocess.run(
            [
                "ffmpeg", "-y", "-i", music_path,
                "-af", f"volume={volume},afade=t=in:st=0:d=2,afade=t=out:st=-3:d=3",
                "-ar", "44100", "-ac", "2",
                output_path,
            ],
            check=True, capture_output=True,
        )
        return output_path

    def mix_audio_tracks(
        self,
        voice_path: str,
        music_path: str,
        sfx_tracks: list,
        output_path: str,
        total_duration: float,
    ) -> str:
        """
        sfx_tracks: list of (path, start_seconds, volume)
        size=2000000000 رقم صحيح — FFmpeg يرفض 2e+09
        """
        safe_dur = max(float(total_duration), 1.0)
        fade_start = max(safe_dur - 3.0, 0.1)

        inputs = ["-i", voice_path, "-i", music_path]
        for sfx_path, _, _ in sfx_tracks:
            inputs += ["-i", sfx_path]

        fp = []
        fp.append("[0:a]volume=1.0[voice]")
        fp.append(
            f"[1:a]aloop=loop=-1:size=2000000000,"
            f"atrim=duration={safe_dur:.1f},"
            f"volume=0.20,"
            f"afade=t=in:st=0:d=2,"
            f"afade=t=out:st={fade_start:.1f}:d=3[music]"
        )

        sfx_labels = []
        for i, (_, start_t, vol) in enumerate(sfx_tracks):
            d_ms = int(start_t * 1000)
            lbl = f"sfx{i}"
            fp.append(f"[{i + 2}:a]adelay={d_ms}|{d_ms},volume={vol}[{lbl}]")
            sfx_labels.append(f"[{lbl}]")

        all_in = "[voice][music]" + "".join(sfx_labels)
        n = 2 + len(sfx_tracks)
        fp.append(f"{all_in}amix=inputs={n}:duration=first:normalize=0[out]")

        cmd = (
            ["ffmpeg", "-y"]
            + inputs
            + [
                "-filter_complex", ";".join(fp),
                "-map", "[out]",
                "-ar", "44100", "-ac", "2", "-b:a", "192k",
                output_path,
            ]
        )
        result = subprocess.run(cmd, capture_output=True)
        if result.returncode != 0:
            # fallback: voice + music فقط
            result2 = subprocess.run(
                [
                    "ffmpeg", "-y",
                    "-i", voice_path, "-i", music_path,
                    "-filter_complex",
                    f"[1:a]aloop=loop=-1:size=2000000000,"
                    f"atrim=duration={safe_dur:.1f},"
                    f"volume=0.20[m];"
                    f"[0:a][m]amix=inputs=2:duration=first:normalize=0[out]",
                    "-map", "[out]",
                    "-ar", "44100", "-ac", "2", "-b:a", "192k",
                    output_path,
                ],
                capture_output=True,
            )
            if result2.returncode != 0:
                shutil.copy(voice_path, output_path)
        return output_path

    def get_audio_duration(self, path: str) -> float:
        r = subprocess.run(
            ["ffprobe", "-v", "quiet", "-print_format", "json", "-show_format", path],
            capture_output=True, text=True, check=True,
        )
        return float(json.loads(r.stdout)["format"]["duration"])

    def add_silence(self, duration: float, output_path: str) -> str:
        subprocess.run(
            [
                "ffmpeg", "-y",
                "-f", "lavfi", "-i", "anullsrc=r=44100:cl=stereo",
                "-t", str(duration), "-b:a", "128k",
                output_path,
            ],
            check=True, capture_output=True,
        )
        return output_path
