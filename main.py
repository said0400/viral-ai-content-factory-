"""
Viral AI Content Factory — main.py مُصلح
التغييرات:
  - GeminiWriter  → ScriptWriter (engine/ai/script_writer.py)
  - ElevenLabsTTS → GroqTTS      (engine/voice/groq_tts.py)
  - check_env: يتحقق من GROQ_API_KEY فقط (لا ElevenLabs لا Gemini)
  - cleanup: يحدث فقط عند النجاح (لا يحذف debug files عند الخطأ)
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

# ─── الاستيرادات المُصلحة ─────────────────────────────────────────────────
from engine.ai.script_writer        import ScriptWriter      # ← كان GeminiWriter
from engine.voice.groq_tts          import GroqTTS           # ← يستبدل ElevenLabs
from engine.voice.breathing_engine  import BreathingEngine
from engine.voice.audio_fx          import AudioFX
from engine.voice.music_engine      import MusicEngine
from engine.video.cinematic_editor  import CinematicEditor
from engine.video.subtitle_engine   import SubtitleEngine
from engine.render.ffmpeg_builder   import FFmpegBuilder


# ─── logging ─────────────────────────────────────────────────────────────────

def log(msg: str, kind: str = "info") -> None:
    colors = {
        "info": "\033[97m", "ok":   "\033[92m",
        "warn": "\033[93m", "err":  "\033[91m",
        "cyan": "\033[96m", "bold": "\033[1m",
    }
    print(f"{colors.get(kind, '')}{msg}\033[0m")


def banner() -> None:
    log("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━", "cyan")
    log("  🎬  VIRAL AI CONTENT FACTORY",              "bold")
    log("  Arabic Cinematic Short Video Generator",    "info")
    log("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━", "cyan")


def check_env() -> bool:
    """
    إصلاح: يتحقق من GROQ_API_KEY فقط — لا ElevenLabs لا Gemini.
    """
    ok = True
    if not os.getenv("GROQ_API_KEY"):
        log("✗ GROQ_API_KEY مفقود في .env", "err")
        ok = False
    if not os.getenv("PEXELS_API_KEY"):
        log("⚠ PEXELS_API_KEY مفقود — سيُستخدم placeholder footage", "warn")
    return ok


# ─── توليد الفيديو ───────────────────────────────────────────────────────────

def generate_video(topic: str, output_dir: str, preset: str = "tiktok") -> str:
    ts   = datetime.now().strftime("%Y%m%d_%H%M%S")
    safe = "".join(c for c in topic if c.isalnum() or c in " _-")[:25].strip().replace(" ", "_")
    out  = str(Path(output_dir) / f"viral_{safe}_{ts}.mp4")
    Path(output_dir).mkdir(parents=True, exist_ok=True)

    tmp = Path(os.getenv("TEMP_DIR", "./temp"))
    tmp.mkdir(parents=True, exist_ok=True)

    # تهيئة الـ engines
    writer       = ScriptWriter()     # ← مُصلح
    tts          = GroqTTS()          # ← مُصلح
    breath       = BreathingEngine()
    fx           = AudioFX()
    music_engine = MusicEngine()
    editor       = CinematicEditor()
    renderer     = FFmpegBuilder()

    success = False  # ← للتحكم في cleanup

    try:
        # ── 1: Script ────────────────────────────────────────────────────
        log("\n[1/6] توليد السكريبت...", "cyan")
        script = writer.generate_script(topic)
        log(f"  ✓ {len(script['scenes'])} مشهد | ~{script['duration_estimate']:.0f}s", "ok")
        log(f"  Hook: {script['hook'][:60]}", "info")

        # ── 2: Voice ─────────────────────────────────────────────────────
        log("\n[2/6] توليد الصوت (Groq TTS)...", "cyan")
        raw_voice = str(tmp / "voice_raw.mp3")
        tts.generate_audio(script, raw_voice)

        breathed   = str(tmp / "voice_breath.mp3")
        proc_voice = str(tmp / "voice_processed.mp3")

        breath.add_breathing(raw_voice, breathed)
        fx.process_voice(breathed, proc_voice)

        audio_dur = fx.get_audio_duration(proc_voice)
        script["duration_estimate"] = min(audio_dur + 1.5, 58.0)
        log(f"  ✓ مدة الصوت: {audio_dur:.1f}s", "ok")

        # ── 3: Audio Mix ─────────────────────────────────────────────────
        log("\n[3/6] مزج الصوت...", "cyan")
        final_audio = str(tmp / "final_audio.mp3")
        total_dur   = script["duration_estimate"]
        mood        = script.get("music_mood", "motivational")

        log(f"  🎵 Mood: {mood}", "info")
        music_file = music_engine.get_music(mood, total_dur)

        if music_file:
            proc_music = str(tmp / "music.mp3")
            fx.process_music(music_file, proc_music, 0.20)

            sfx_dir    = Path("engine/assets/sfx")
            sfx_tracks = []
            if sfx_dir.exists():
                sfx_files = list(sfx_dir.glob("*.mp3")) + list(sfx_dir.glob("*.wav"))
                if sfx_files:
                    t = 0.0
                    for scene in script["scenes"][:4]:
                        sfx_tracks.append((str(random.choice(sfx_files)), t, 0.35))
                        t += scene.get("duration", 3.0) + scene.get("pause_after", 0.3)

            fx.mix_audio_tracks(proc_voice, proc_music, sfx_tracks, final_audio, total_dur)
            log(f"  ✓ صوت + موسيقى [{mood}]", "ok")
        else:
            shutil.copy(proc_voice, final_audio)
            log("  ✓ صوت فقط (لا توجد موسيقى)", "warn")

        # ── 4: Subtitles ─────────────────────────────────────────────────
        log("\n[4/6] رسم الترجمة العربية...", "cyan")
        sub_engine    = SubtitleEngine(
            int(os.getenv("VIDEO_WIDTH",  "1080")),
            int(os.getenv("VIDEO_HEIGHT", "1920")),
        )
        subtitle_data = sub_engine.render_all_scenes(script)
        log(f"  ✓ {len(subtitle_data)} PNG frame", "ok")

        # ── 5: Video Assembly ────────────────────────────────────────────
        log("\n[5/6] تجميع الفيديو...", "cyan")
        assembled = str(tmp / "assembled.mp4")
        editor.build_video(
            script        = script,
            audio_path    = final_audio,
            subtitle_data = subtitle_data,
            output_path   = assembled,
        )
        log("  ✓ الفيديو مُجمَّع", "ok")

        # ── 6: Final Render ──────────────────────────────────────────────
        log("\n[6/6] الـ render النهائي...", "cyan")
        renderer.render_final(
            input_video = assembled,
            output_path = out,
            preset      = preset,
            metadata    = {
                "title":       script.get("title", topic),
                "description": script.get("hook", ""),
            },
        )

        try:
            thumb = out.replace(".mp4", "_thumb.jpg")
            renderer.create_thumbnail(out, thumb)
            log(f"  ✓ Thumbnail: {thumb}", "ok")
        except Exception:
            pass

        success = True
        return out

    finally:
        # إصلاح: cleanup فقط عند النجاح
        # عند الخطأ تبقى الملفات للـ debugging
        if success:
            try:
                renderer.cleanup_temp()
            except Exception:
                pass
        else:
            log("  ⚠️ temp files محفوظة للـ debugging", "warn")


# ─── main ─────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="Viral AI Content Factory")
    parser.add_argument("--topic",      type=str,
                        default=os.getenv("DEFAULT_TOPIC", "الطموح والنجاح"))
    parser.add_argument("--output",     type=str,
                        default=os.getenv("OUTPUT_DIR", "./output"))
    parser.add_argument("--preset",     type=str,
                        choices=["tiktok", "reels", "preview"],
                        default="tiktok")
    parser.add_argument("--no-cleanup", action="store_true")
    parser.add_argument("--batch",      type=str, nargs="+")
    args = parser.parse_args()

    banner()

    if not check_env():
        log("\nأضف المفاتيح المفقودة إلى .env ثم أعد المحاولة.", "err")
        sys.exit(1)

    topics = args.batch if args.batch else [args.topic]

    for i, topic in enumerate(topics, 1):
        if len(topics) > 1:
            log(f"\n━━━ فيديو {i}/{len(topics)}: {topic} ━━━", "cyan")
        else:
            log(f"\n🎬 الموضوع: {topic}", "bold")

        t0 = time.time()
        try:
            result = generate_video(topic, args.output, args.preset)
            log(f"\n✅ تم في {time.time()-t0:.0f}s → {result}", "ok")
        except KeyboardInterrupt:
            log("\n⚠ تم الإلغاء.", "warn")
            sys.exit(0)
        except Exception as e:
            log(f"\n❌ خطأ: {e}", "err")
            traceback.print_exc()


if __name__ == "__main__":
    main()
