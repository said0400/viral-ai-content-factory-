"""
🎬 Viral AI Content Factory — main.py
═══════════════════════════════════════════════════════════════════
مولّد فيديوهات Shorts عربية احترافية بالذكاء الاصطناعي

الميزات:
  ✓ Groq (أساسي) + Gemini (احتياطي) للسكربتات
  ✓ edge-tts (أساسي) + ElevenLabs (احتياطي) للصوت
  ✓ Pexels + Pixabay لمصادر الفيديو
  ✓ موسيقى خلفية + مؤثرات صوتية
  ✓ ترجمة عربية احترافية (RTL)
  ✓ نشر تلقائي على GitHub Releases
═══════════════════════════════════════════════════════════════════
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

# ─── الاستيرادات ──────────────────────────────────────────────────────────
from engine.ai.script_writer        import ScriptWriter
from engine.voice                   import create_tts_engine
from engine.voice.breathing_engine  import BreathingEngine
from engine.voice.audio_fx          import AudioFX
from engine.voice.music_engine      import MusicEngine
from engine.video.cinematic_editor  import CinematicEditor
from engine.video.subtitle_engine   import SubtitleEngine
from engine.render.ffmpeg_builder   import FFmpegBuilder


# ─── ألوان السجلات ────────────────────────────────────────────────────────
COLORS = {
    "info": "\033[97m",
    "ok":   "\033[92m",
    "warn": "\033[93m",
    "err":  "\033[91m",
    "cyan": "\033[96m",
    "bold": "\033[1m",
    "reset": "\033[0m",
}


def log(msg: str, kind: str = "info") -> None:
    """طباعة رسالة ملوّنة."""
    print(f"{COLORS.get(kind, '')}{msg}{COLORS['reset']}")


def banner() -> None:
    """عرض شعار البداية."""
    log("━" * 60, "cyan")
    log("  🎬  VIRAL AI CONTENT FACTORY", "bold")
    log("  Arabic Cinematic Shorts Generator v2.0", "info")
    log("━" * 60, "cyan")


# ─── فحص البيئة ───────────────────────────────────────────────────────────
def check_env() -> bool:
    """التحقق من وجود المفاتيح المطلوبة."""
    log("\n🔐 فحص متغيرات البيئة...", "cyan")
    
    ok = True
    
    # --- مطلوب ---
    if not os.getenv("GROQ_API_KEY"):
        log("  ✗ GROQ_API_KEY مفقود (مطلوب)", "err")
        ok = False
    else:
        log("  ✓ GROQ_API_KEY", "ok")

    # --- اختياري (احتياطي) ---
    if os.getenv("GEMINI_API_KEY"):
        log("  ✓ GEMINI_API_KEY (احتياطي)", "ok")
    else:
        log("  ⚠ GEMINI_API_KEY مفقود — لن يتوفر احتياطي للنصوص", "warn")

    # --- مصادر الفيديو ---
    if os.getenv("PEXELS_API_KEY"):
        log("  ✓ PEXELS_API_KEY", "ok")
    else:
        log("  ⚠ PEXELS_API_KEY مفقود", "warn")

    if os.getenv("PIXABAY_API_KEY"):
        log("  ✓ PIXABAY_API_KEY", "ok")
    else:
        log("  ⚠ PIXABAY_API_KEY مفقود", "warn")

    # --- ElevenLabs (احتياطي) ---
    if os.getenv("ELEVENLABS_API_KEY"):
        log("  ✓ ELEVENLABS_API_KEY (احتياطي للصوت)", "ok")
    else:
        log("  ℹ ElevenLabs غير مفعّل — سيُستخدم edge-tts (مجاني)", "info")

    return ok


# ─── إنشاء اسم ملف آمن ────────────────────────────────────────────────────
def safe_filename(topic: str, max_len: int = 25) -> str:
    """تحويل الموضوع إلى اسم ملف آمن."""
    safe = "".join(c for c in topic if c.isalnum() or c in " _-")
    safe = safe[:max_len].strip().replace(" ", "_")
    return safe or "video"


# ─── توليد الفيديو ────────────────────────────────────────────────────────
def generate_video(
    topic: str,
    output_dir: str,
    content_type: str = "motivational",
    duration: int = 45,
    quality: str = "high",
) -> str:
    """
    توليد فيديو Shorts كامل من البداية للنهاية.

    Args:
        topic: موضوع الفيديو
        output_dir: مجلد الإخراج
        content_type: نوع المحتوى (motivational/educational/story/quote)
        duration: المدة المستهدفة بالثواني
        quality: جودة التصدير (medium/high/ultra)

    Returns:
        مسار الفيديو الناتج
    """
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    safe = safe_filename(topic)
    out = str(Path(output_dir) / f"short_{safe}_{ts}.mp4")
    Path(output_dir).mkdir(parents=True, exist_ok=True)

    tmp = Path(os.getenv("TEMP_DIR", "./temp"))
    tmp.mkdir(parents=True, exist_ok=True)

    # ── تهيئة المحركات ────────────────────────────────────────────────
    log("\n⚙️  تهيئة المحركات...", "cyan")
    writer       = ScriptWriter()
    tts          = create_tts_engine()  # يختار تلقائياً (edge-tts / elevenlabs)
    breath       = BreathingEngine()
    fx           = AudioFX()
    music_engine = MusicEngine()
    editor       = CinematicEditor()
    renderer     = FFmpegBuilder()

    success = False

    try:
        # ── 1: السكربت ──────────────────────────────────────────────
        log("\n[1/6] 📝 توليد السكربت...", "cyan")
        script = writer.generate_script(
            topic=topic,
            content_type=content_type,
            target_duration=duration,
        )
        log(f"  ✓ {len(script['scenes'])} مشهد | ~{script['duration_estimate']:.0f}s", "ok")
        log(f"  ✓ Hook: {script['hook'][:60]}...", "info")

        # ── 2: الصوت ────────────────────────────────────────────────
        log("\n[2/6] 🎙️  توليد الصوت...", "cyan")
        raw_voice = str(tmp / "voice_raw.mp3")
        tts.generate_audio(script, raw_voice)

        breathed   = str(tmp / "voice_breath.mp3")
        proc_voice = str(tmp / "voice_processed.mp3")

        breath.add_breathing(raw_voice, breathed)
        fx.process_voice(breathed, proc_voice)

        audio_dur = fx.get_audio_duration(proc_voice)
        # استخدام مدة الصوت الفعلية (مع حد أقصى 60 ثانية لـ Shorts)
        script["duration_estimate"] = min(audio_dur + 1.5, 60.0)
        log(f"  ✓ مدة الصوت: {audio_dur:.1f}s", "ok")

        # ── 3: مزج الصوت ────────────────────────────────────────────
        log("\n[3/6] 🎵 مزج الصوت...", "cyan")
        final_audio = str(tmp / "final_audio.mp3")
        total_dur   = script["duration_estimate"]
        mood        = script.get("music_mood", "motivational")

        log(f"  🎼 Mood: {mood}", "info")

        if os.getenv("ENABLE_BACKGROUND_MUSIC", "true").lower() == "true":
            music_file = music_engine.get_music(mood, total_dur)
        else:
            music_file = None

        if music_file:
            proc_music = str(tmp / "music.mp3")
            music_vol = float(os.getenv("MUSIC_VOLUME", "0.15"))
            fx.process_music(music_file, proc_music, music_vol)

            # المؤثرات الصوتية
            sfx_dir = Path("engine/assets/sfx")
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
            log("  ✓ صوت فقط (بدون موسيقى)", "warn")

        # ── 4: الترجمة ──────────────────────────────────────────────
        log("\n[4/6] 📜 رسم الترجمة العربية...", "cyan")
        sub_engine = SubtitleEngine(
            int(os.getenv("VIDEO_WIDTH", "1080")),
            int(os.getenv("VIDEO_HEIGHT", "1920")),
        )
        subtitle_data = sub_engine.render_all_scenes(script)
        log(f"  ✓ {len(subtitle_data)} إطار ترجمة", "ok")

        # ── 5: تجميع الفيديو ────────────────────────────────────────
        log("\n[5/6] 🎬 تجميع الفيديو...", "cyan")
        assembled = str(tmp / "assembled.mp4")
        editor.build_video(
            script        = script,
            audio_path    = final_audio,
            subtitle_data = subtitle_data,
            output_path   = assembled,
        )
        log("  ✓ الفيديو مُجمَّع", "ok")

        # ── 6: التصدير النهائي ──────────────────────────────────────
        log("\n[6/6] 🚀 التصدير النهائي...", "cyan")
        renderer.render_final(
            input_video = assembled,
            output_path = out,
            quality     = quality,
            metadata    = {
                "title":       script.get("title", topic),
                "description": script.get("hook", ""),
                "comment":     f"Generated by AI Shorts Factory | {content_type}",
            },
        )

        # إنشاء صورة مصغرة
        try:
            thumb = out.replace(".mp4", "_thumb.jpg")
            renderer.create_thumbnail(out, thumb)
            log(f"  ✓ Thumbnail: {Path(thumb).name}", "ok")
        except Exception as e:
            log(f"  ⚠ فشل إنشاء الـ Thumbnail: {e}", "warn")

        # حفظ معلومات الفيديو
        try:
            info_file = out.replace(".mp4", "_info.txt")
            with open(info_file, "w", encoding="utf-8") as f:
                f.write(f"Title: {script.get('title', topic)}\n")
                f.write(f"Topic: {topic}\n")
                f.write(f"Type: {content_type}\n")
                f.write(f"Duration: {script['duration_estimate']:.1f}s\n")
                f.write(f"Hook: {script.get('hook', '')}\n")
                f.write(f"Generated: {ts}\n")
            log(f"  ✓ Info: {Path(info_file).name}", "ok")
        except Exception:
            pass

        # عرض حجم الملف
        try:
            size_mb = Path(out).stat().st_size / (1024 * 1024)
            log(f"  📦 حجم الفيديو: {size_mb:.2f} MB", "info")
        except Exception:
            pass

        success = True
        return out

    finally:
        if success:
            try:
                renderer.cleanup_temp()
                log("  🧹 تم تنظيف الملفات المؤقتة", "info")
            except Exception:
                pass
        else:
            log("  ⚠ الملفات المؤقتة محفوظة للتشخيص", "warn")


# ─── الدالة الرئيسية ──────────────────────────────────────────────────────
def main():
    parser = argparse.ArgumentParser(
        description="🎬 Viral AI Content Factory - Arabic Shorts Generator",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "--topic", type=str,
        default=os.getenv("DEFAULT_TOPIC", "الطموح والنجاح"),
        help="موضوع الفيديو",
    )
    parser.add_argument(
        "--type", type=str,
        choices=["motivational", "educational", "story", "quote"],
        default=os.getenv("CONTENT_TYPE", "motivational"),
        help="نوع المحتوى",
    )
    parser.add_argument(
        "--duration", type=int,
        choices=[30, 45, 60],
        default=int(os.getenv("VIDEO_TARGET_DURATION", "45")),
        help="المدة المستهدفة بالثواني",
    )
    parser.add_argument(
        "--quality", type=str,
        choices=["medium", "high", "ultra"],
        default=os.getenv("VIDEO_QUALITY", "high"),
        help="جودة التصدير",
    )
    parser.add_argument(
        "--output", type=str,
        default=os.getenv("OUTPUT_DIR", "./output"),
        help="مجلد الإخراج",
    )
    parser.add_argument(
        "--batch", type=str, nargs="+",
        help="توليد عدة فيديوهات (مواضيع متعددة)",
    )
    args = parser.parse_args()

    banner()

    if not check_env():
        log("\n❌ أضف المفاتيح المفقودة إلى GitHub Secrets ثم أعد المحاولة.", "err")
        sys.exit(1)

    topics = args.batch if args.batch else [args.topic]
    results = []

    for i, topic in enumerate(topics, 1):
        if len(topics) > 1:
            log(f"\n{'═' * 60}", "cyan")
            log(f"  🎬 فيديو {i}/{len(topics)}: {topic}", "bold")
            log(f"{'═' * 60}", "cyan")
        else:
            log(f"\n🎬 الموضوع: {topic}", "bold")
            log(f"📋 النوع: {args.type} | ⏱ المدة: {args.duration}s | ✨ الجودة: {args.quality}", "info")

        t0 = time.time()
        try:
            result = generate_video(
                topic=topic,
                output_dir=args.output,
                content_type=args.type,
                duration=args.duration,
                quality=args.quality,
            )
            elapsed = time.time() - t0
            log(f"\n✅ تم بنجاح في {elapsed:.0f}s", "ok")
            log(f"📁 {result}", "ok")
            results.append((topic, True, result))
        except KeyboardInterrupt:
            log("\n⚠ تم الإلغاء بواسطة المستخدم.", "warn")
            sys.exit(0)
        except Exception as e:
            log(f"\n❌ خطأ في توليد الفيديو: {e}", "err")
            traceback.print_exc()
            results.append((topic, False, str(e)))

    # ── ملخص نهائي ────────────────────────────────────────────────
    if len(topics) > 1:
        log(f"\n{'═' * 60}", "cyan")
        log("  📊 الملخص النهائي", "bold")
        log(f"{'═' * 60}", "cyan")
        for topic, ok, info in results:
            status = "✅" if ok else "❌"
            log(f"  {status} {topic}", "ok" if ok else "err")

    # خروج بكود خطأ إذا فشل أي فيديو
    if any(not ok for _, ok, _ in results):
        sys.exit(1)


if __name__ == "__main__":
    main()
