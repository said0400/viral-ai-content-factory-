"""
Cinematic Editor - full video assembly pipeline
"""

import os
import json
import random
import shutil
import subprocess
import requests
from pathlib import Path

from engine.video.effects_engine    import EffectsEngine
from engine.video.transition_engine import TransitionEngine
from engine.video.subtitle_engine   import SubtitleEngine


class CinematicEditor:

    KEYWORDS = [
        "dark cinematic motivational",
        "silhouette dramatic sunset",
        "urban night city lights",
        "fire flame dramatic",
        "mountain fog misty",
        "rain window dark",
        "bokeh city night",
        "person walking alone",
        "stars night sky",
        "smoke light dramatic",
        "ocean waves slow",
        "sunrise mountain golden",
        "empty road dramatic",
        "candle flame dark",
        "forest mist dark",
    ]

    ZOOM_MAP = {
        "hook":       "punch_zoom",
        "build":      "slow_zoom_in",
        "peak":       "punch_zoom",
        "resolution": "slow_zoom_out",
        "cta":        "drift_right",
        "main":       "slow_zoom_in",
    }

    def __init__(self):
        self.w   = int(os.getenv("VIDEO_WIDTH",  "1080"))
        self.h   = int(os.getenv("VIDEO_HEIGHT", "1920"))
        self.fps = int(os.getenv("VIDEO_FPS",    "30"))
        self.pexels_key = os.getenv("PEXELS_API_KEY", "")

        self.temp_dir    = Path(os.getenv("TEMP_DIR", "./temp"))
        self.footage_dir = self.temp_dir / "footage"
        self.clips_dir   = self.temp_dir / "clips"
        for d in [self.temp_dir, self.footage_dir, self.clips_dir]:
            d.mkdir(parents=True, exist_ok=True)

        self.fx    = EffectsEngine(self.w, self.h)
        self.trans = TransitionEngine(self.w, self.h)
        self.subs  = SubtitleEngine(self.w, self.h)

    # ── PUBLIC ──────────────────────────────────────────────────────────

    def build_video(
        self,
        script: dict,
        audio_path: str,
        subtitle_data: list,
        output_path: str,
    ) -> str:
        scenes       = script.get("scenes", [])
        total_dur    = float(script.get("duration_estimate", 54.0))

        print("    ► Fetching footage...")
        raws = self._fetch_footage(scenes)

        print("    ► Processing clips...")
        processed = self._process_clips(raws, scenes)

        print("    ► Assembling with transitions...")
        assembled = self._assemble(processed, scenes, total_dur)

        print("    ► Overlaying subtitles...")
        subtitled = self._overlay_subs(assembled, subtitle_data, scenes)

        print("    ► Muxing audio...")
        muxed = self._mux(subtitled, audio_path)

        print("    ► Color grade + letterbox...")
        self._grade(muxed, output_path)

        return output_path

    # ── FOOTAGE ─────────────────────────────────────────────────────────

    def _fetch_footage(self, scenes: list) -> list:
        used = set()
        clips = []
        for i, scene in enumerate(scenes):
            kw = self._pick_kw(scene, used)
            used.add(kw)
            clips.append(self._download(kw, i))
        return clips

    def _pick_kw(self, scene: dict, used: set) -> str:
        hints = {
            "ألم": "smoke light dramatic",
            "نجاح": "sunrise mountain golden",
            "وحيد": "person walking alone",
            "ليل": "urban night city lights",
            "نار": "fire flame dramatic",
            "أمل": "sunrise mountain golden",
            "مطر": "rain window dark",
            "قوة": "silhouette dramatic sunset",
            "سماء": "stars night sky",
            "طريق": "empty road dramatic",
        }
        text = scene.get("text", "")
        for hint, kw in hints.items():
            if hint in text and kw not in used:
                return kw
        avail = [k for k in self.KEYWORDS if k not in used]
        return random.choice(avail) if avail else random.choice(self.KEYWORDS)

    def _download(self, keyword: str, idx: int) -> str:
        out = str(self.footage_dir / f"footage_{idx:03d}.mp4")
        if os.path.exists(out) and os.path.getsize(out) > 10000:
            return out
        if not self.pexels_key:
            return self._placeholder(idx)
        try:
            r = requests.get(
                "https://api.pexels.com/videos/search",
                headers={"Authorization": self.pexels_key},
                params={"query": keyword, "per_page": 5, "orientation": "portrait"},
                timeout=15,
            )
            r.raise_for_status()
            videos = r.json().get("videos", [])
            if not videos:
                return self._placeholder(idx)

            video = random.choice(videos[:3])
            files = video.get("video_files", [])

            # اختار portrait أو أقرب
            target = None
            for vf in files:
                vw = vf.get("width", 0)
                vh = vf.get("height", 0)
                q  = vf.get("quality", "")
                if vh >= vw and q in ("hd", "sd"):
                    target = vf
                    break
            if not target:
                for vf in files:
                    if vf.get("quality") in ("hd", "sd"):
                        target = vf
                        break
            if not target and files:
                target = files[0]
            if not target:
                return self._placeholder(idx)

            dl = requests.get(target["link"], stream=True, timeout=30)
            dl.raise_for_status()
            with open(out, "wb") as f:
                for chunk in dl.iter_content(8192):
                    f.write(chunk)
            return out
        except Exception as e:
            print(f"      Pexels failed '{keyword}': {e}")
            return self._placeholder(idx)

    def _placeholder(self, idx: int) -> str:
        """Dark animated gradient placeholder."""
        out = str(self.footage_dir / f"ph_{idx:03d}.mp4")
        colors = ["0x0a0a1a", "0x0d0d1e", "0x080818", "0x0a0a0a", "0x05050f"]
        c = colors[idx % len(colors)]
        result = subprocess.run(
            [
                "ffmpeg", "-y",
                "-f", "lavfi",
                "-i", f"color=c={c}:s={self.w}x{self.h}:r={self.fps}",
                "-t", "6",
                "-c:v", "libx264", "-preset", "ultrafast", "-crf", "28",
                out,
            ],
            capture_output=True,
        )
        if result.returncode != 0 or not os.path.exists(out):
            subprocess.run(
                [
                    "ffmpeg", "-y",
                    "-f", "lavfi",
                    "-i", f"color=c=black:s={self.w}x{self.h}:r={self.fps}",
                    "-t", "6",
                    "-c:v", "libx264", "-preset", "ultrafast", "-crf", "28",
                    out,
                ],
                capture_output=True,
            )
        return out

    # ── CLIP PROCESSING ─────────────────────────────────────────────────

    def _process_clips(self, raws: list, scenes: list) -> list:
        processed = []
        for i, (raw, scene) in enumerate(zip(raws, scenes)):
            st   = scene.get("type", "main")
            dur  = scene.get("duration", 3.0) + scene.get("pause_after", 0.3)
            zoom = self.ZOOM_MAP.get(st, "slow_zoom_in")

            sc  = str(self.clips_dir / f"sc_{i:03d}.mp4")
            tr  = str(self.clips_dir / f"tr_{i:03d}.mp4")
            zm  = str(self.clips_dir / f"zm_{i:03d}.mp4")

            self.fx.scale_and_crop(raw, sc)
            self.fx.trim_clip(sc, tr, 0.0, dur)
            self.fx.apply_zoom_effect(tr, zm, zoom, dur)

            if st in ("hook", "peak"):
                sh = str(self.clips_dir / f"sh_{i:03d}.mp4")
                self.fx.apply_smooth_shake(zm, sh, 2.0)
                processed.append(sh)
            else:
                processed.append(zm)

        return processed

    # ── ASSEMBLY ────────────────────────────────────────────────────────

    def _assemble(self, clips: list, scenes: list, total_dur: float) -> str:
        out = str(self.temp_dir / "assembled.mp4")
        if len(clips) == 1:
            shutil.copy(clips[0], out)
            return out

        current = clips[0]
        for i in range(1, len(clips)):
            st = scenes[i].get("type", "main") if i < len(scenes) else "main"
            if st in ("hook", "peak"):
                tt = self.trans.get_random_transition(high_energy=True)
            elif st == "cta":
                tt = "fade_black"
            else:
                tt = self.trans.get_random_transition(high_energy=False)

            nxt = str(self.temp_dir / f"tr_{i:03d}.mp4")
            self.trans.apply_transition(current, clips[i], nxt, tt, 0.18)
            current = nxt

        shutil.copy(current, out)
        return out

    # ── SUBTITLE OVERLAY ────────────────────────────────────────────────

    def _overlay_subs(self, video: str, sub_data: list, scenes: list) -> str:
        out = str(self.temp_dir / "subtitled.mp4")
        if not sub_data:
            shutil.copy(video, out)
            return out

        inputs = ["-i", video]
        for png, _ in sub_data:
            inputs += ["-i", png]

        fp = []
        cur_stream = "0:v"
        t = 0.0

        for i, (_, scene) in enumerate(sub_data):
            dur   = scene.get("duration", 3.0)
            pause = scene.get("pause_after", 0.3)
            t_end = t + dur
            nxt   = f"vs{i}"
            fp.append(
                f"[{cur_stream}][{i+1}:v]"
                f"overlay=0:0:enable='between(t,{t:.2f},{t_end:.2f})'[{nxt}]"
            )
            cur_stream = nxt
            t += dur + pause

        cmd = (
            ["ffmpeg", "-y"]
            + inputs
            + [
                "-filter_complex", ";".join(fp),
                "-map", f"[{cur_stream}]",
                "-c:v", "libx264", "-preset", "medium", "-crf", "18",
                "-pix_fmt", "yuv420p", "-an",
                out,
            ]
        )
        result = subprocess.run(cmd, capture_output=True)
        if result.returncode != 0:
            shutil.copy(video, out)
        return out

    # ── AUDIO MUX ───────────────────────────────────────────────────────

    def _mux(self, video: str, audio: str) -> str:
        out = str(self.temp_dir / "muxed.mp4")
        subprocess.run(
            [
                "ffmpeg", "-y",
                "-i", video, "-i", audio,
                "-map", "0:v:0", "-map", "1:a:0",
                "-c:v", "copy", "-c:a", "aac", "-b:a", "192k",
                "-shortest",
                out,
            ],
            check=True, capture_output=True,
        )
        return out

    # ── FINAL GRADE ─────────────────────────────────────────────────────

    def _grade(self, inp: str, out: str) -> str:
        graded = str(self.temp_dir / "graded.mp4")
        self.fx.apply_cinematic_grade(inp, graded)
        self.fx.add_letterbox(graded, out)
        return out
