"""
Viral AI Content Factory
Autonomous Arabic Cinematic Short Video Generator
"""

import os
import sys
import time
import random
import shutil
import traceback
import argparse
from pathlib import Path
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

from engine.ai.gemini_writer        import GeminiWriter
from engine.voice.elevenlabs_tts    import ElevenLabsTTS
from engine.voice.breathing_engine  import BreathingEngine
from engine.voice.audio_fx          import AudioFX
from engine.video.cinematic_editor  import CinematicEditor
from engine.video.subtitle_engine   import SubtitleEngine
from engine.render.ffmpeg_builder   import FFmpegBuilder


def log(msg: str, kind: str = "info") -> None:
    colors = {
        "info":    "\033[97m",
        "ok":      "\033[92m",
        "warn":    "\033[93m",
        "err":     "\033[91m",
        "cyan":    "\033[96m",
        "bold":    "\033[1m",
    }
    print(f"{colors.get(kind, '')}{msg}\033[0m")


def banner() -> None:
    log("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━", "cyan")
    log("  🎬  VIRAL AI CONTENT FACTORY",              "bold")
    log("  Arabic Cinematic Short Video Generator",    "info")
    log("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━", "cyan")


def check_env() -> bool:
    ok = True
    if not os.getenv("GEMINI_API_KEY"):
        log("✗ GEMINI_API_KEY missing in .env", "err"); ok = False
    if not os.getenv("ELEVENLABS_API_KEY"):
        log("✗ ELEVENLABS_API_KEY missing in .env", "err"); ok = False
    if not os.getenv("PEXELS_API_KEY"):
        log("⚠ PEXELS_API_KEY missing — using placeholder footage", "warn")
    return ok


def generate_video(topic: str, output_dir: str, preset: str = "tiktok") -> str:
    ts   = datetime.now().strftime("%Y%m%d_%H%M%S")
    safe = "".join(c for c in topic if c.isalnum() or c in " _-")[:25].strip().replace(" ", "_")
    out  = str(Path(output_dir) / f"viral_{safe}_{ts}.mp4")
    Path(output_dir).mkdir(parents=True, exist_ok=True)

    tmp = Path(os.getenv("TEMP_DIR", "./temp"))
    tmp.mkdir(parents=True, exist_ok=True)

    writer   = GeminiWriter()
    tts      = ElevenLabsTTS()
    breath   = BreathingEngine()
    fx       = AudioFX()
    editor   = CinematicEditor()
    renderer = FFmpegBuilder()

    # ── 1: Script ────────────────────────────────────────────────────
    log("\n[1/6] Generating cinematic script...", "cyan")
    script = writer.generate_script(topic)
    log(f"  ✓ {len(script['scenes'])} scenes | ~{script['duration_estimate']:.0f}s", "ok")
    log(f"  Hook: {script['hook'][:55]}", "info")

    # ── 2: Voice ─────────────────────────────────────────────────────
    log("\n[2/6] Generating cinematic voice (ElevenLabs)...", "cyan")
    raw_voice = str(tmp / "voice_raw.mp3")
    tts.generate_audio(script, raw_voice)

    breathed = str(tmp / "voice_breath.mp3")
    breath.add_breathing(raw_voice, breathed)

    proc_voice = str(tmp / "voice_processed.mp3")
    fx.process_voice(breathed, proc_voice)

    audio_dur = fx.get_audio_duration(proc_voice)
    script["duration_estimate"] = min(audio_dur + 1.5, 58.0)
    log(f"  ✓ Voice: {audio_dur:.1f}s", "ok")

    # ── 3: Audio Mix ─────────────────────────────────────────────────
    log("\n[3/6] Mixing audio tracks...", "cyan")
    final_audio = str(tmp / "final_audio.mp3")
    total_dur   = script["duration_estimate"]

    music_dir   = Path("engine/assets/music")
    music_files = list(music_dir.glob("*.mp3")) + list(music_dir.glob("*.wav"))

    if music_files:
        music = str(random.choice(music_files))
        proc_music = str(tmp / "music.mp3")
        fx.process_music(music, proc_music, 0.20)

        sfx_dir   = Path("engine/assets/sfx")
        sfx_files = list(sfx_dir.glob("*.mp3")) + list(sfx_dir.glob("*.wav"))
        sfx_tracks = []
        if sfx_files:
            t = 0.0
            for scene in script["scenes"][:4]:
                sfx_tracks.append((str(random.choice(sfx_files)), t, 0.35))
                t += scene.get("duration", 3.0) + scene.get("pause_after", 0.3)

        fx.mix_audio_tracks(proc_voice, proc_music, sfx_tracks, final_audio, total_dur)
        log("  ✓ Voice + music + SFX mixed", "ok")
    else:
        shutil.copy(proc_voice, final_audio)
        log("  ✓ Voice only (add MP3s to engine/assets/music/ for music)", "warn")

    # ── 4: Subtitles ─────────────────────────────────────────────────
    log("\n[4/6] Rendering Arabic subtitles (PIL)...", "cyan")
    sub_engine   = SubtitleEngine(
        int(os.getenv("VIDEO_WIDTH", "1080")),
        int(os.getenv("VIDEO_HEIGHT", "1920")),
    )
    subtitle_data = sub_engine.render_all_scenes(script)
    log(f"  ✓ {len(subtitle_data)} PNG frames rendered", "ok")

    # ── 5: Video Assembly ────────────────────────────────────────────
    log("\n[5/6] Assembling cinematic video...", "cyan")
    assembled = str(tmp / "assembled.mp4")
    editor.build_video(
        script=script,
        audio_path=final_audio,
        subtitle_data=subtitle_data,
        output_path=assembled,
    )
    log("  ✓ Video assembled", "ok")

    # ── 6: Final Render ──────────────────────────────────────────────
    log("\n[6/6] Final render...", "cyan")
    renderer.render_final(
        input_video=assembled,
        output_path=out,
        preset=preset,
        metadata={
            "title":       script.get("title", topic),
            "description": script.get("hook", ""),
        },
    )

    thumb = out.replace(".mp4", "_thumb.jpg")
    try:
        renderer.create_thumbnail(out, thumb)
        log(f"  ✓ Thumbnail: {thumb}", "ok")
    except Exception:
        pass

    return out


def main():
    parser = argparse.ArgumentParser(description="Viral AI Content Factory")
    parser.add_argument("--topic",      type=str, default=os.getenv("DEFAULT_TOPIC", "الطموح والنجاح"))
    parser.add_argument("--output",     type=str, default=os.getenv("OUTPUT_DIR", "./output"))
    parser.add_argument("--preset",     type=str, choices=["tiktok","reels","preview"], default="tiktok")
    parser.add_argument("--no-cleanup", action="store_true")
    parser.add_argument("--batch",      type=str, nargs="+")
    args = parser.parse_args()

    banner()
    if not check_env():
        log("\nAdd missing keys to .env then retry.", "err")
        sys.exit(1)

    renderer = FFmpegBuilder()
    topics   = args.batch if args.batch else [args.topic]

    for i, topic in enumerate(topics, 1):
        if len(topics) > 1:
            log(f"\n━━━ Video {i}/{len(topics)}: {topic} ━━━", "cyan")
        else:
            log(f"\n🎬 Topic: {topic}", "bold")

        t0 = time.time()
        try:
            result = generate_video(topic, args.output, args.preset)
            log(f"\n✅ Done in {time.time()-t0:.0f}s → {result}", "ok")
        except KeyboardInterrupt:
            log("\n⚠ Cancelled.", "warn")
            sys.exit(0)
        except Exception as e:
            log(f"\n❌ Error: {e}", "err")
            traceback.print_exc()
        finally:
            if not args.no_cleanup:
                try:
                    renderer.cleanup_temp()
                except Exception:
                    pass


if __name__ == "__main__":
    main()
