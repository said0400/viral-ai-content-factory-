"""
🎬 Viral AI Content Factory — main.py (v2.3 - Pro Audio Edition)
═══════════════════════════════════════════════════════════════════
v2.3 الميزات:
  ✓ Audio-First Approach (لا انكسار، لا تكرار)
  ✓ SFXManager (مؤثرات صوتية ذكية)
  ✓ MusicEngine المحسّن (موسيقى Pixabay)
  ✓ AudioOptimizer (تحسين الصوت)
  ✓ Whisper subtitles (TikTok style)
  ✓ Remotion للتصدير

Pipeline:
  [1/6] السكربت
  [2/6] الصوت الخام
  [3/6] معالجة الصوت
  [4/6] قياس المدة الفعلية
  [5/6] مزج (صوت + موسيقى + SFX)
  [6/6] الفيديو
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
    print(f"{COLORS.get(kind, '')}{msg}{COLORS['reset']}")


def banner() -> None:
    log("━" * 60, "cyan")
    log("  🎬  VIRAL AI CONTENT FACTORY", "bold")
    log("  Arabic Cinematic Shorts Generator v2.3", "info")
    log("  ⭐ Pro Audio Edition (Music + SFX + Audio-First)", "ok")
    log("━" * 60, "cyan")


# ─── فحص البيئة ───────────────────────────────────────────────────────────
def check_env(use_remotion: bool = True) -> bool:
    """التحقق من وجود المفاتيح والأدوات المطلوبة."""
    log("\n🔐 فحص متغيرات البيئة...", "cyan")

    ok = True

    if not os.getenv("GROQ_API_KEY"):
        log("  ✗ GROQ_API_KEY مفقود (مطلوب)", "err")
        ok = False
    else:
        log("  ✓ GROQ_API_KEY", "ok")

    if os.getenv("GEMINI_API_KEY"):
        log("  ✓ GEMINI_API_KEY", "ok")
    else:
        log("  ⚠ GEMINI_API_KEY مفقود", "warn")

    if os.getenv("PEXELS_API_KEY"):
        log("  ✓ PEXELS_API_KEY", "ok")
    else:
        log("  ⚠ PEXELS_API_KEY مفقود", "warn")

    if os.getenv("PIXABAY_API_KEY"):
        log("  ✓ PIXABAY_API_KEY (للموسيقى)", "ok")
    else:
        log("  ⚠ PIXABAY_API_KEY مفقود (لن تعمل الموسيقى)", "warn")

    tts_engine = os.getenv("TTS_ENGINE", "edge").lower()
    log(f"  ℹ TTS Engine: {tts_engine}", "info")

    # 🆕 فحص SFX
    enable_sfx = os.getenv("ENABLE_SFX", "true").lower() == "true"
    log(f"  🔊 SFX: {'مفعّلة' if enable_sfx else 'معطّلة'}", "info")
    
    # 🆕 فحص Music
    enable_music = os.getenv("ENABLE_BACKGROUND_MUSIC", "true").lower() == "true"
    log(f"  🎵 الموسيقى الخلفية: {'مفعّلة' if enable_music else 'معطّلة'}", "info")

    log("\n🎬 فحص محرك التصدير...", "cyan")

    if use_remotion:
        try:
            result = subprocess.run(
                ["node", "--version"],
                capture_output=True, text=True, timeout=10,
            )
            if result.returncode == 0:
                log(f"  ✓ Node.js {result.stdout.strip()}", "ok")
            else:
                log("  ✗ Node.js غير مثبت", "err")
                ok = False
        except (FileNotFoundError, subprocess.TimeoutExpired):
            log("  ✗ Node.js غير مثبت", "err")
            ok = False

        remotion_dir = Path(os.getenv("REMOTION_DIR", "./remotion"))
        if remotion_dir.exists():
            log(f"  ✓ Remotion directory: {remotion_dir}", "ok")
            if (remotion_dir / "node_modules").exists():
                log("  ✓ Remotion installed", "ok")
            else:
                log("  ⚠ Remotion not installed!", "warn")
                ok = False
        else:
            log(f"  ✗ Remotion directory not found", "err")
            ok = False

        if REMOTION_AVAILABLE:
            log("  ✓ RemotionRenderer module loaded", "ok")
        else:
            log("  ✗ RemotionRenderer module failed", "err")
            ok = False

    try:
        result = subprocess.run(
            ["ffmpeg", "-version"],
            capture_output=True, text=True, timeout=10,
        )
        if result.returncode == 0:
            log("  ✓ FFmpeg", "ok")
    except (FileNotFoundError, subprocess.TimeoutExpired):
        log("  ⚠ FFmpeg غير مثبت", "warn")

    return ok


def safe_filename(topic: str, max_len: int = 25) -> str:
    """تحويل الموضوع إلى اسم ملف آمن."""
    safe = "".join(c for c in topic if c.isalnum() or c in " _-")
    safe = safe[:max_len].strip().replace(" ", "_")
    return safe or "video"


def get_audio_duration(audio_path: str) -> float:
    """🆕 قياس المدة الفعلية للصوت بدقة."""
    try:
        result = subprocess.run(
            [
                "ffprobe", "-v", "quiet",
                "-show_entries", "format=duration",
                "-of", "default=noprint_wrappers=1:nokey=1",
                audio_path,
            ],
            capture_output=True, text=True, timeout=30, check=True,
        )
        return float(result.stdout.strip())
    except Exception as e:
        log(f"  ⚠ فشل قياس مدة الصوت: {e}", "warn")
        return 0.0


# ═════════════════════════════════════════════════════════════════════════
# 🆕 توليد الفيديو (Pro Audio + Audio-First)
# ═════════════════════════════════════════════════════════════════════════
def generate_video(
    topic: str,
    output_dir: str,
    content_type: str = "motivational",
    duration: int = 45,
    quality: str = "high",
    use_remotion: bool = True,
) -> str:
    """
    🆕 توليد فيديو احترافي:
    
    1. السكربت
    2. الصوت + التحسين
    3. قياس المدة الفعلية
    4. مزج احترافي (Voice + Music + SFX)
    5. الفيديو
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

    # 🆕 تهيئة SFX Manager
    sfx_manager = None
    try:
        from engine.voice.sfx_manager import SFXManager
        sfx_manager = SFXManager()
        log("  ✓ SFX Manager جاهز", "ok")
    except ImportError:
        log("  ⚠ SFXManager غير متوفر", "warn")
    except Exception as e:
        log(f"  ⚠ فشل تهيئة SFX: {e}", "warn")

    if use_remotion and REMOTION_AVAILABLE:
        renderer = RemotionRenderer()
        log("  ✓ Renderer: Remotion (Arabic native)", "ok")
    elif FFMPEG_AVAILABLE:
        renderer = FFmpegBuilder()
        log("  ⚠ Renderer: FFmpeg (Legacy)", "warn")
    else:
        raise RuntimeError("❌ لا يوجد محرك تصدير متاح!")

    success = False

    try:
        # ═══════════════════════════════════════════════════════════════
        # [1/6] توليد السكربت
        # ═══════════════════════════════════════════════════════════════
        log("\n[1/6] 📝 توليد السكربت...", "cyan")
        script = writer.generate_script(
            topic=topic,
            content_type=content_type,
            target_duration=duration,
        )
        log(f"  ✓ {len(script['scenes'])} مشهد | متوقع: ~{script['duration_estimate']:.0f}s", "ok")
        log(f"  ✓ Hook: {script['hook'][:60]}...", "info")

        # ═══════════════════════════════════════════════════════════════
        # [2/6] توليد الصوت الخام (TTS)
        # ═══════════════════════════════════════════════════════════════
        log("\n[2/6] 🎙️  توليد الصوت الخام...", "cyan")
        raw_voice = str(tmp / "voice_raw.mp3")
        tts.generate_audio(script, raw_voice)
        
        raw_duration = get_audio_duration(raw_voice)
        log(f"  ✓ مدة الصوت الخام: {raw_duration:.1f}s", "ok")

        # ═══════════════════════════════════════════════════════════════
        # [3/6] معالجة + تحسين الصوت
        # ═══════════════════════════════════════════════════════════════
        log("\n[3/6] 🎵 معالجة وتحسين الصوت...", "cyan")
        
        breathed = str(tmp / "voice_breath.mp3")
        proc_voice = str(tmp / "voice_processed.mp3")
        optimized_voice = str(tmp / "voice_optimized.mp3")

        # 1. إضافة التنفس
        breath.add_breathing(raw_voice, breathed)
        
        # 2. معالجة الصوت
        fx.process_voice(breathed, proc_voice)
        
        # 3. التحسين النهائي
        try:
            from engine.voice.audio_optimizer import AudioOptimizer
            audio_opt = AudioOptimizer()
            audio_opt.optimize(proc_voice, optimized_voice)
            proc_voice = optimized_voice
            log("  ✓ تم تحسين الصوت", "ok")
        except ImportError:
            log("  ⚠ AudioOptimizer غير متوفر", "warn")
        except Exception as e:
            log(f"  ⚠ فشل تحسين الصوت: {e}", "warn")

        # ═══════════════════════════════════════════════════════════════
        # [4/6] قياس المدة الفعلية ⭐
        # ═══════════════════════════════════════════════════════════════
        log("\n[4/6] 📏 قياس المدة الفعلية للصوت...", "cyan")
        
        actual_audio_duration = get_audio_duration(proc_voice)
        
        if actual_audio_duration <= 0:
            raise RuntimeError("❌ فشل قياس مدة الصوت!")
        
        log(f"  ✓ المدة الخام: {raw_duration:.1f}s", "info")
        log(f"  ✓ المدة الفعلية بعد التحسين: {actual_audio_duration:.1f}s", "ok")
        log(f"  ✓ توفير: {raw_duration - actual_audio_duration:.1f}s", "ok")
        
        # تحديث script بالمدة الفعلية
        script["duration_estimate"] = actual_audio_duration
        script["actual_audio_duration"] = actual_audio_duration

        # ═══════════════════════════════════════════════════════════════
        # 🆕 [5/6] مزج احترافي (Voice + Music + SFX)
        # ═══════════════════════════════════════════════════════════════
        log("\n[5/6] 🎵 مزج الصوت النهائي (Pro Mix)...", "cyan")
        final_audio = str(tmp / "final_audio.mp3")
        mood = script.get("music_mood", "motivational")

        log(f"  🎼 Mood: {mood}", "info")

        # 🆕 1. الموسيقى الخلفية
        music_file = None
        if os.getenv("ENABLE_BACKGROUND_MUSIC", "true").lower() == "true":
            log("  🎵 البحث عن موسيقى مناسبة...", "info")
            music_file = music_engine.get_music(mood, actual_audio_duration)
            if music_file:
                log(f"  ✓ موسيقى: {Path(music_file).name}", "ok")
            else:
                log("  ⚠ لم يتم العثور على موسيقى", "warn")
        else:
            log("  ⏭ الموسيقى معطّلة", "info")

        # 🆕 2. المؤثرات الصوتية (SFX)
        sfx_tracks = []
        if sfx_manager and os.getenv("ENABLE_SFX", "true").lower() == "true":
            log("  🔊 تجهيز المؤثرات الصوتية...", "info")
            try:
                sfx_tracks = sfx_manager.get_sfx_for_scenes(script["scenes"])
                if sfx_tracks:
                    log(f"  ✓ تم تجهيز {len(sfx_tracks)} مؤثر صوتي", "ok")
                else:
                    log("  ⏭ بدون مؤثرات", "info")
            except Exception as e:
                log(f"  ⚠ فشل تجهيز SFX: {e}", "warn")
        else:
            log("  ⏭ SFX معطّلة", "info")

        # 🆕 3. المزج النهائي
        if music_file:
            proc_music = str(tmp / "music.mp3")
            music_vol = float(os.getenv("MUSIC_VOLUME", "0.15"))
            fx.process_music(music_file, proc_music, music_vol)

            # مزج كامل: Voice + Music + SFX
            log(f"  🎚️ مزج: Voice + Music ({len(sfx_tracks)} SFX)", "info")
            fx.mix_audio_tracks(
                voice_path=proc_voice,
                music_path=proc_music,
                sfx_tracks=sfx_tracks,
                output_path=final_audio,
                total_duration=actual_audio_duration,
            )
            log(f"  ✓ مزج كامل: Voice + Music + {len(sfx_tracks)} SFX", "ok")
        else:
            # بدون موسيقى - استخدم الصوت كما هو
            shutil.copy(proc_voice, final_audio)
            log("  ✓ صوت فقط (بدون موسيقى)", "warn")
        
        # قياس المدة النهائية
        final_duration = get_audio_duration(final_audio)
        log(f"  ✓ مدة الصوت النهائي: {final_duration:.1f}s", "ok")
        
        # تحديث script
        script["duration_estimate"] = final_duration
        script["actual_audio_duration"] = final_duration

        # ═══════════════════════════════════════════════════════════════
        # [6/6] بناء الفيديو على مدة الصوت بالضبط
        # ═══════════════════════════════════════════════════════════════
        log("\n[6/6] 🎬 بناء الفيديو على مدة الصوت...", "cyan")

        if use_remotion and isinstance(renderer, RemotionRenderer):
            props = build_complete_props(
                script=script,
                audio_path=final_audio,
                output_dir=output_dir,
            )
            
            # تأكيد المدة في props
            props["totalDuration"] = final_duration
            props["audioActualDuration"] = final_duration
            
            log(f"  ✓ {props['meta']['totalScenes']} مشهد", "ok")
            log(f"  ✓ {props['meta']['totalSubtitles']} ترجمة", "ok")
            log(f"  ✓ {props['meta']['totalTransitions']} انتقال", "ok")
            log(f"  ✓ مدة الفيديو: {final_duration:.1f}s (= مدة الصوت)", "ok")
        else:
            log("  ❌ Legacy mode غير مدعوم", "err")
            raise NotImplementedError("استخدم Remotion")

        # ═══════════════════════════════════════════════════════════════
        # 🚀 التصدير
        # ═══════════════════════════════════════════════════════════════
        log("\n🚀 التصدير النهائي...", "cyan")

        if use_remotion and isinstance(renderer, RemotionRenderer):
            renderer.render_final(
                props=props,
                output_path=out,
                quality=quality,
                metadata={
                    "title":       script.get("title", topic),
                    "description": script.get("hook", ""),
                    "comment":     f"Generated by AI Shorts Factory v2.3 | {content_type}",
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
                f.write(f"Duration: {final_duration:.1f}s\n")
                f.write(f"Hook: {script.get('hook', '')}\n")
                f.write(f"Generated: {ts}\n")
                f.write(f"Renderer: {'Remotion' if use_remotion else 'FFmpeg'}\n")
                f.write(f"TTS Engine: {os.getenv('TTS_ENGINE', 'edge')}\n")
                f.write(f"Audio Speed: {os.getenv('AUDIO_SPEED', '1.0')}x\n")
                f.write(f"\n=== Audio Pipeline ===\n")
                f.write(f"  Raw: {raw_duration:.1f}s\n")
                f.write(f"  Optimized: {actual_audio_duration:.1f}s\n")
                f.write(f"  Final: {final_duration:.1f}s\n")
                f.write(f"\n=== Audio Components ===\n")
                f.write(f"  Voice: ✓\n")
                f.write(f"  Music: {'✓ ' + Path(music_file).name if music_file else '✗'}\n")
                f.write(f"  SFX: {len(sfx_tracks)} effects\n")
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
        description="🎬 Viral AI Content Factory v2.3 - Pro Audio Edition",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("--topic", type=str, default=os.getenv("DEFAULT_TOPIC", "الطموح والنجاح"))
    parser.add_argument("--type", type=str, choices=["motivational", "educational", "story", "quote"],
                        default=os.getenv("CONTENT_TYPE", "motivational"))
    parser.add_argument("--duration", type=int, choices=[30, 45, 60],
                        default=int(os.getenv("VIDEO_TARGET_DURATION", "45")))
    parser.add_argument("--quality", type=str, choices=["medium", "high", "ultra"],
                        default=os.getenv("VIDEO_QUALITY", "high"))
    parser.add_argument("--output", type=str, default=os.getenv("OUTPUT_DIR", "./output"))
    parser.add_argument("--batch", type=str, nargs="+")
    parser.add_argument("--use-ffmpeg", action="store_true")
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()

    banner()

    use_remotion = not args.use_ffmpeg

    if args.use_ffmpeg:
        log("\n⚠ تم اختيار FFmpeg القديم", "warn")

    if not check_env(use_remotion=use_remotion):
        log("\n❌ أصلح المشاكل ثم أعد المحاولة.", "err")
        sys.exit(1)

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
                f"✨ الجودة: {args.quality}",
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
            log("\n⚠ تم الإلغاء.", "warn")
            sys.exit(0)
        except Exception as e:
            log(f"\n❌ خطأ: {e}", "err")
            traceback.print_exc()
            results.append((topic, False, str(e)))

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
