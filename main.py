"""
🎬 Viral AI Content Factory — main.py (v2.1 - Optimized Edition)
═══════════════════════════════════════════════════════════════════
مولّد فيديوهات Shorts عربية احترافية بالذكاء الاصطناعي

التغييرات في v2.1:
  ✓ إضافة AudioOptimizer (إزالة فراغات + تسريع)
  ✓ Whisper subtitles (TikTok style)
  ✓ Gemini TTS (احترافي)
  ✓ Viral Prompt Engine v3.0
  ✓ Remotion للتصدير

الميزات:
  ✓ Groq + Gemini للسكربتات
  ✓ Edge-TTS / ElevenLabs / Gemini للصوت
  ✓ Pexels + Pixabay للفيديو
  ✓ موسيقى خلفية + مؤثرات
  ✓ ترجمة عربية احترافية
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
import subprocess
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

# 🆕 المحركات الجديدة (Remotion mode)
from engine.video                   import build_complete_props
from engine.render                  import (
    RemotionRenderer,
    FFmpegBuilder,
    REMOTION_AVAILABLE,
    FFMPEG_AVAILABLE,
)


# ─── ألوان السجلات ────────────────────────────────────────────────────────
COLORS = {
    "info":  "\033[97m",
    "ok":    "\033[92m",
    "warn":  "\033[93m",
    "err":   "\033[91m",
    "cyan":  "\033[96m",
    "bold":  "\033[1m",
    "reset": "\033[0m",
}


def log(msg: str, kind: str = "info") -> None:
    """طباعة رسالة ملوّنة."""
    print(f"{COLORS.get(kind, '')}{msg}{COLORS['reset']}")


def banner() -> None:
    """عرض شعار البداية."""
    log("━" * 60, "cyan")
    log("  🎬  VIRAL AI CONTENT FACTORY", "bold")
    log("  Arabic Cinematic Shorts Generator v2.1", "info")
    log("  ⭐ Remotion + Whisper + Audio Optimizer", "ok")
    log("━" * 60, "cyan")


# ─── فحص البيئة ───────────────────────────────────────────────────────────
def check_env(use_remotion: bool = True) -> bool:
    """التحقق من وجود المفاتيح والأدوات المطلوبة."""
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

    # --- TTS Engines ---
    tts_engine = os.getenv("TTS_ENGINE", "edge").lower()
    log(f"  ℹ TTS Engine: {tts_engine}", "info")
    
    if tts_engine == "elevenlabs" and os.getenv("ELEVENLABS_API_KEY"):
        log("  ✓ ELEVENLABS_API_KEY", "ok")
    elif tts_engine == "gemini" and os.getenv("GEMINI_API_KEY"):
        log("  ✓ Gemini TTS متاح", "ok")
    elif tts_engine == "edge":
        log("  ✓ Edge TTS (مجاني)", "ok")

    # --- 🆕 فحص Remotion ---
    log("\n🎬 فحص محرك التصدير...", "cyan")

    if use_remotion:
        # فحص Node.js
        try:
            result = subprocess.run(
                ["node", "--version"],
                capture_output=True,
                text=True,
                timeout=10,
            )
            if result.returncode == 0:
                log(f"  ✓ Node.js {result.stdout.strip()}", "ok")
            else:
                log("  ✗ Node.js غير مثبت", "err")
                ok = False
        except (FileNotFoundError, subprocess.TimeoutExpired):
            log("  ✗ Node.js غير مثبت", "err")
            log("    ℹ حمّل من: https://nodejs.org/", "info")
            ok = False

        # فحص مجلد Remotion
        remotion_dir = Path(os.getenv("REMOTION_DIR", "./remotion"))
        if remotion_dir.exists():
            log(f"  ✓ Remotion directory: {remotion_dir}", "ok")

            if (remotion_dir / "node_modules").exists():
                log("  ✓ Remotion installed", "ok")
            else:
                log("  ⚠ Remotion not installed!", "warn")
                log(f"    شغّل: cd {remotion_dir} && npm install", "info")
                ok = False
        else:
            log(f"  ✗ Remotion directory not found: {remotion_dir}", "err")
            ok = False

        if REMOTION_AVAILABLE:
            log("  ✓ RemotionRenderer module loaded", "ok")
        else:
            log("  ✗ RemotionRenderer module failed to load", "err")
            ok = False

    # --- FFmpeg ---
    try:
        result = subprocess.run(
            ["ffmpeg", "-version"],
            capture_output=True,
            text=True,
            timeout=10,
        )
        if result.returncode == 0:
            log("  ✓ FFmpeg", "ok")
        else:
            log("  ⚠ FFmpeg غير متاح", "warn")
    except (FileNotFoundError, subprocess.TimeoutExpired):
        log("  ⚠ FFmpeg غير مثبت", "warn")

    return ok


# ─── إنشاء اسم ملف آمن ────────────────────────────────────────────────────
def safe_filename(topic: str, max_len: int = 25) -> str:
    """تحويل الموضوع إلى اسم ملف آمن."""
    safe = "".join(c for c in topic if c.isalnum() or c in " _-")
    safe = safe[:max_len].strip().replace(" ", "_")
    return safe or "video"


# ─── 🆕 توليد الفيديو ────────────────────────────────────────────────────
def generate_video(
    topic: str,
    output_dir: str,
    content_type: str = "motivational",
    duration: int = 45,
    quality: str = "high",
    use_remotion: bool = True,
) -> str:
    """
    توليد فيديو Shorts كامل من البداية للنهاية.

    Args:
        topic: موضوع الفيديو
        output_dir: مجلد الإخراج
        content_type: نوع المحتوى
        duration: المدة المستهدفة بالثواني
        quality: جودة التصدير
        use_remotion: استخدام Remotion (افتراضي)

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
    tts          = create_tts_engine()
    breath       = BreathingEngine()
    fx           = AudioFX()
    music_engine = MusicEngine()

    # 🆕 اختيار المحرك (Remotion أو FFmpeg legacy)
    if use_remotion and REMOTION_AVAILABLE:
        renderer = RemotionRenderer()
        log("  ✓ Renderer: Remotion (Arabic native)", "ok")
    elif FFMPEG_AVAILABLE:
        renderer = FFmpegBuilder()
        log("  ⚠ Renderer: FFmpeg (Legacy mode)", "warn")
    else:
        raise RuntimeError("❌ لا يوجد محرك تصدير متاح!")

    success = False

    try:
        # ── 1: السكربت ──────────────────────────────────────────────
        log("\n[1/5] 📝 توليد السكربت...", "cyan")
        script = writer.generate_script(
            topic=topic,
            content_type=content_type,
            target_duration=duration,
        )
        log(f"  ✓ {len(script['scenes'])} مشهد | ~{script['duration_estimate']:.0f}s", "ok")
        log(f"  ✓ Hook: {script['hook'][:60]}...", "info")

        # ── 2: الصوت + التحسين ──────────────────────────────────────
        log("\n[2/5] 🎙️  توليد الصوت...", "cyan")
        raw_voice = str(tmp / "voice_raw.mp3")
        tts.generate_audio(script, raw_voice)

        breathed = str(tmp / "voice_breath.mp3")
        proc_voice = str(tmp / "voice_processed.mp3")
        optimized_voice = str(tmp / "voice_optimized.mp3")

        breath.add_breathing(raw_voice, breathed)
        fx.process_voice(breathed, proc_voice)

        # 🆕 تحسين الصوت (إزالة فراغات + تسريع + تطبيع)
        log("  🎵 تحسين الصوت (إزالة فراغات + تسريع)...", "cyan")
        try:
            from engine.voice.audio_optimizer import AudioOptimizer
            audio_opt = AudioOptimizer()
            audio_opt.optimize(proc_voice, optimized_voice)
            proc_voice = optimized_voice  # استخدم النسخة المحسّنة
            log("  ✓ تم تحسين الصوت", "ok")
        except ImportError:
            log("  ⚠ AudioOptimizer غير متوفر، استخدام الصوت الأصلي", "warn")
        except Exception as e:
            log(f"  ⚠ فشل تحسين الصوت: {e}", "warn")

        # تحديث مدة الصوت بعد التحسين
        audio_dur = fx.get_audio_duration(proc_voice)
        script["duration_estimate"] = min(audio_dur + 1.5, 60.0)
        log(f"  ✓ مدة الصوت النهائية: {audio_dur:.1f}s", "ok")

        # ── 3: مزج الصوت ────────────────────────────────────────────
        log("\n[3/5] 🎵 مزج الصوت...", "cyan")
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

        # ── 4: 🆕 بناء props شامل لـ Remotion ───────────────────────
        log("\n[4/5] 🎬 بناء props لـ Remotion...", "cyan")

        if use_remotion and isinstance(renderer, RemotionRenderer):
            props = build_complete_props(
                script=script,
                audio_path=final_audio,
                output_dir=output_dir,
            )
            log(f"  ✓ {props['meta']['totalScenes']} مشهد", "ok")
            log(f"  ✓ {props['meta']['totalSubtitles']} ترجمة", "ok")
            log(f"  ✓ {props['meta']['totalTransitions']} انتقال", "ok")
        else:
            log("  ❌ Legacy mode غير مدعوم بعد التحويل", "err")
            raise NotImplementedError(
                "Legacy FFmpeg mode تم إيقافه. استخدم Remotion."
            )

        # ── 5: 🆕 التصدير بـ Remotion ──────────────────────────────
        log("\n[5/5] 🚀 التصدير النهائي...", "cyan")

        if use_remotion and isinstance(renderer, RemotionRenderer):
            renderer.render_final(
                props=props,
                output_path=out,
                quality=quality,
                metadata={
                    "title":       script.get("title", topic),
                    "description": script.get("hook", ""),
                    "comment":     f"Generated by AI Shorts Factory v2.1 | {content_type}",
                },
            )

        log(f"  ✓ الفيديو جاهز", "ok")

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
                f.write(f"Renderer: {'Remotion' if use_remotion else 'FFmpeg'}\n")
                f.write(f"TTS Engine: {os.getenv('TTS_ENGINE', 'edge')}\n")
                f.write(f"Audio Speed: {os.getenv('AUDIO_SPEED', '1.0')}x\n")
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
        description="🎬 Viral AI Content Factory v2.1 - Optimized Edition",
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
    parser.add_argument(
        "--use-ffmpeg", action="store_true",
        help="استخدام FFmpeg القديم بدلاً من Remotion (Legacy)",
    )
    parser.add_argument(
        "--check", action="store_true",
        help="فحص البيئة فقط بدون توليد فيديو",
    )
    args = parser.parse_args()

    banner()

    use_remotion = not args.use_ffmpeg

    if args.use_ffmpeg:
        log("\n⚠ تم اختيار FFmpeg القديم (Legacy mode)", "warn")
        log("  ℹ قد لا يعمل بعد التحويل", "warn")

    # فحص البيئة
    if not check_env(use_remotion=use_remotion):
        log("\n❌ أصلح المشاكل المذكورة أعلاه ثم أعد المحاولة.", "err")
        sys.exit(1)

    # وضع الفحص فقط
    if args.check:
        log("\n✅ كل شيء جاهز للعمل!", "ok")
        sys.exit(0)

    topics = args.batch if args.batch else [args.topic]
    results = []

    for i, topic in enumerate(topics, 1):
        if len(topics) > 1:
            log(f"\n{'═' * 60}", "cyan")
            log(f"  🎬 فيديو {i}/{len(topics)}: {topic}", "bold")
            log(f"{'═' * 60}", "cyan")
        else:
            log(f"\n🎬 الموضوع: {topic}", "bold")
            log(
                f"📋 النوع: {args.type} | "
                f"⏱ المدة: {args.duration}s | "
                f"✨ الجودة: {args.quality} | "
                f"🎬 Renderer: {'Remotion' if use_remotion else 'FFmpeg'}",
                "info",
            )

        t0 = time.time()
        try:
            result = generate_video(
                topic=topic,
                output_dir=args.output,
                content_type=args.type,
                duration=args.duration,
                quality=args.quality,
                use_remotion=use_remotion,
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

    if any(not ok for _, ok, _ in results):
        sys.exit(1)


if __name__ == "__main__":
    main()
