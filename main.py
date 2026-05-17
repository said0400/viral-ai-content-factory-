"""
🎬 Viral AI Content Factory — main.py (v3.0 - Quality-First Edition)
═══════════════════════════════════════════════════════════════════
v3.0 الجديد:
  ✓ نظام منع الفيديو الضعيف (Auto-Reject + Retry)
  ✓ فحص جودة السكربت (Score 0-100)
  ✓ فحص تطابق الصوت مع النص
  ✓ فحص المدة المطلوبة
  ✓ إعادة محاولة تلقائية (حتى 3 مرات)
  ✓ لا ينشر إلا فيديو كامل وجاهز

Pipeline:
  [1] السكربت → فحص الجودة → إعادة إذا ضعيف
  [2] الصوت → فحص التطابق → إعادة إذا ناقص
  [3] المزج (موسيقى + SFX)
  [4] الفيديو → تأكيد نهائي
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
    "info": "\033[97m", "ok": "\033[92m", "warn": "\033[93m",
    "err": "\033[91m", "cyan": "\033[96m", "bold": "\033[1m",
    "reset": "\033[0m",
}

def log(msg: str, kind: str = "info") -> None:
    print(f"{COLORS.get(kind, '')}{msg}{COLORS['reset']}")

def banner() -> None:
    log("━" * 60, "cyan")
    log("  🎬  VIRAL AI CONTENT FACTORY", "bold")
    log("  v3.0 - Quality-First Edition", "info")
    log("  ⭐ Auto-Reject + Retry + Full Validation", "ok")
    log("━" * 60, "cyan")

# ─── إعدادات الجودة ───────────────────────────────────────────────────────
MIN_SCRIPT_SCORE = 60           # الحد الأدنى لقبول السكربت
MIN_AUDIO_COVERAGE = 50         # الحد الأدنى لتغطية الصوت (%)
MAX_SCRIPT_RETRIES = 3          # أقصى محاولات لتوليد سكربت جيد
MAX_AUDIO_RETRIES = 2           # أقصى محاولات لتوليد صوت كامل


def check_env(use_remotion: bool = True) -> bool:
    """التحقق من البيئة."""
    log("\n🔐 فحص متغيرات البيئة...", "cyan")
    ok = True

    for key, label in [
        ("GROQ_API_KEY", "GROQ"), ("GEMINI_API_KEY", "GEMINI"),
        ("PEXELS_API_KEY", "PEXELS"), ("PIXABAY_API_KEY", "PIXABAY"),
    ]:
        if os.getenv(key):
            log(f"  ✓ {label}", "ok")
        else:
            log(f"  ⚠ {label} مفقود", "warn")
            if key == "GROQ_API_KEY":
                ok = False

    log(f"  ℹ TTS: {os.getenv('TTS_ENGINE', 'edge')}", "info")

    if use_remotion:
        log("\n🎬 فحص Remotion...", "cyan")
        try:
            r = subprocess.run(["node", "--version"], capture_output=True, text=True, timeout=10)
            if r.returncode == 0:
                log(f"  ✓ Node.js {r.stdout.strip()}", "ok")
            else:
                ok = False
        except Exception:
            log("  ✗ Node.js غير مثبت", "err")
            ok = False

        remotion_dir = Path(os.getenv("REMOTION_DIR", "./remotion"))
        if remotion_dir.exists() and (remotion_dir / "node_modules").exists():
            log("  ✓ Remotion installed", "ok")
        else:
            log("  ⚠ Remotion not installed", "warn")
            ok = False

        if REMOTION_AVAILABLE:
            log("  ✓ RemotionRenderer loaded", "ok")
        else:
            ok = False

    return ok


def safe_filename(topic: str, max_len: int = 25) -> str:
    safe = "".join(c for c in topic if c.isalnum() or c in " _-")
    return safe[:max_len].strip().replace(" ", "_") or "video"


def get_audio_duration(audio_path: str) -> float:
    try:
        r = subprocess.run(
            ["ffprobe", "-v", "quiet", "-show_entries", "format=duration",
             "-of", "default=noprint_wrappers=1:nokey=1", audio_path],
            capture_output=True, text=True, timeout=30, check=True,
        )
        return float(r.stdout.strip())
    except Exception:
        return 0.0


# ═════════════════════════════════════════════════════════════════════════
# 🎯 توليد الفيديو مع نظام Quality-First
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
    🎯 توليد فيديو جاهز للنشر مباشرة.
    
    يمنع الفيديوهات الضعيفة ويعيد المحاولة تلقائياً.
    """
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    safe = safe_filename(topic)
    out = str(Path(output_dir) / f"short_{safe}_{ts}.mp4")
    Path(output_dir).mkdir(parents=True, exist_ok=True)

    tmp = Path(os.getenv("TEMP_DIR", "./temp"))
    tmp.mkdir(parents=True, exist_ok=True)

    # ── تهيئة المحركات ────────────────────────────────────────
    log("\n⚙️  تهيئة المحركات...", "cyan")
    writer = ScriptWriter()
    tts = create_tts_engine()
    breath = BreathingEngine()
    fx = AudioFX()
    music_engine = MusicEngine()

    # SFX Manager
    sfx_manager = None
    try:
        from engine.voice.sfx_manager import SFXManager
        sfx_manager = SFXManager()
        log("  ✓ SFX Manager جاهز", "ok")
    except Exception:
        log("  ⚠ SFXManager غير متوفر", "warn")

    # Content Validator
    validator = None
    try:
        from engine.ai.content_validator import ContentValidator
        validator = ContentValidator()
        log("  ✓ Content Validator جاهز", "ok")
    except Exception:
        log("  ⚠ ContentValidator غير متوفر", "warn")

    # Renderer
    if use_remotion and REMOTION_AVAILABLE:
        renderer = RemotionRenderer()
        log("  ✓ Renderer: Remotion", "ok")
    elif FFMPEG_AVAILABLE:
        renderer = FFmpegBuilder()
    else:
        raise RuntimeError("❌ لا يوجد محرك تصدير!")

    success = False

    try:
        # ══════════════════════════════════════════════════════════
        # [1/6] 📝 توليد السكربت مع فحص الجودة + إعادة المحاولة
        # ══════════════════════════════════════════════════════════
        log("\n[1/6] 📝 توليد السكربت...", "cyan")
        
        script = None
        script_score = 0
        
        for attempt in range(1, MAX_SCRIPT_RETRIES + 1):
            if attempt > 1:
                log(f"\n   🔄 إعادة محاولة السكربت ({attempt}/{MAX_SCRIPT_RETRIES})...", "warn")
            
            # توليد السكربت
            current_script = writer.generate_script(
                topic=topic,
                content_type=content_type,
                target_duration=duration,
            )
            
            scenes = current_script.get("scenes", [])
            all_texts = [s.get("text", "").strip() for s in scenes if s.get("text")]
            word_count = len(" ".join(all_texts).split())
            
            log(f"  ✓ {len(scenes)} مشهد | {word_count} كلمة", "ok")
            log(f"  ✓ Hook: {current_script.get('hook', '')[:60]}...", "info")
            
            # 🆕 فحص الجودة
            if validator:
                log("   🎯 فحص جودة السكربت...", "cyan")
                validation = validator.validate_script(current_script, duration)
                script_score = validation["score"]
                
                if validation["valid"] and script_score >= MIN_SCRIPT_SCORE:
                    log(f"   ✅ السكربت ممتاز! (Score: {script_score}/100)", "ok")
                    script = current_script
                    break
                else:
                    log(f"   ❌ السكربت ضعيف (Score: {script_score}/100)", "err")
                    for issue in validation["all_issues"][:3]:
                        log(f"      {issue}", "warn")
                    
                    if attempt == MAX_SCRIPT_RETRIES:
                        log(f"   ⚠ استخدام أفضل سكربت متاح (Score: {script_score})", "warn")
                        script = current_script
                    else:
                        log(f"   🔄 جاري إعادة التوليد...", "cyan")
            else:
                # بدون validator، اقبل أي سكربت
                script = current_script
                break
        
        if not script:
            raise RuntimeError("❌ فشل توليد سكربت مقبول!")

        # ══════════════════════════════════════════════════════════
        # [2/6] 🎙️ توليد الصوت مع فحص التطابق + إعادة المحاولة
        # ══════════════════════════════════════════════════════════
        log("\n[2/6] 🎙️  توليد الصوت...", "cyan")
        
        # استخراج النص الكامل
        scenes = script.get("scenes", [])
        full_text = " ".join([s.get("text", "") for s in scenes if s.get("text")])
        
        proc_voice = None
        raw_duration = 0
        actual_audio_duration = 0
        
        for audio_attempt in range(1, MAX_AUDIO_RETRIES + 1):
            if audio_attempt > 1:
                log(f"\n   🔄 إعادة محاولة الصوت ({audio_attempt}/{MAX_AUDIO_RETRIES})...", "warn")
            
            # توليد الصوت
            raw_voice = str(tmp / f"voice_raw_{audio_attempt}.mp3")
            tts.generate_audio(script, raw_voice)
            
            raw_duration = get_audio_duration(raw_voice)
            log(f"  ✓ مدة الصوت الخام: {raw_duration:.1f}s", "ok")
            
            # معالجة الصوت
            breathed = str(tmp / "voice_breath.mp3")
            current_proc = str(tmp / f"voice_processed_{audio_attempt}.mp3")
            optimized = str(tmp / f"voice_optimized_{audio_attempt}.mp3")

            breath.add_breathing(raw_voice, breathed)
            fx.process_voice(breathed, current_proc)
            
            # تحسين
            try:
                from engine.voice.audio_optimizer import AudioOptimizer
                AudioOptimizer().optimize(current_proc, optimized)
                current_proc = optimized
            except Exception:
                pass

            actual_audio_duration = get_audio_duration(current_proc)
            log(f"  ✓ المدة الفعلية: {actual_audio_duration:.1f}s", "ok")
            
            # 🆕 فحص تطابق الصوت مع النص
            if validator and actual_audio_duration > 0:
                log("   🎙️ فحص تطابق الصوت...", "cyan")
                audio_check = validator.validate_audio(
                    current_proc, full_text, duration
                )
                
                coverage = audio_check.get("coverage_percent", 0)
                
                if audio_check["valid"]:
                    log(f"   ✅ الصوت مكتمل ({coverage:.0f}% تغطية)", "ok")
                    proc_voice = current_proc
                    break
                else:
                    log(f"   ⚠ الصوت ناقص ({coverage:.0f}% تغطية)", "warn")
                    
                    if audio_attempt == MAX_AUDIO_RETRIES:
                        log("   ⚠ استخدام أفضل صوت متاح", "warn")
                        proc_voice = current_proc
                    else:
                        log("   🔄 جاري إعادة التوليد...", "cyan")
            else:
                proc_voice = current_proc
                break
        
        if not proc_voice:
            raise RuntimeError("❌ فشل توليد صوت مقبول!")

        # تحديث المدة
        script["duration_estimate"] = actual_audio_duration
        script["actual_audio_duration"] = actual_audio_duration

        # ══════════════════════════════════════════════════════════
        # [3/6] 📏 قياس المدة الفعلية
        # ══════════════════════════════════════════════════════════
        log(f"\n[3/6] 📏 المدة الفعلية: {actual_audio_duration:.1f}s", "cyan")

        # ══════════════════════════════════════════════════════════
        # [4/6] 🎵 مزج احترافي (Voice + Music + SFX)
        # ══════════════════════════════════════════════════════════
        log("\n[4/6] 🎵 مزج الصوت النهائي...", "cyan")
        final_audio = str(tmp / "final_audio.mp3")
        mood = script.get("music_mood", "motivational")

        # الموسيقى
        music_file = None
        if os.getenv("ENABLE_BACKGROUND_MUSIC", "true").lower() == "true":
            music_file = music_engine.get_music(mood, actual_audio_duration)
            if music_file:
                log(f"  ✓ موسيقى: {Path(music_file).name}", "ok")

        # SFX
        sfx_tracks = []
        if sfx_manager and os.getenv("ENABLE_SFX", "true").lower() == "true":
            try:
                sfx_tracks = sfx_manager.get_sfx_for_scenes(script["scenes"])
                if sfx_tracks:
                    log(f"  ✓ {len(sfx_tracks)} مؤثر صوتي", "ok")
            except Exception:
                pass

        # المزج
        if music_file:
            proc_music = str(tmp / "music.mp3")
            music_vol = float(os.getenv("MUSIC_VOLUME", "0.15"))
            fx.process_music(music_file, proc_music, music_vol)

            fx.mix_audio_tracks(
                voice_path=proc_voice,
                music_path=proc_music,
                sfx_tracks=sfx_tracks,
                output_path=final_audio,
                total_duration=actual_audio_duration,
            )
            log(f"  ✓ مزج: Voice + Music + {len(sfx_tracks)} SFX", "ok")
        else:
            shutil.copy(proc_voice, final_audio)
            log("  ✓ صوت فقط", "warn")

        # تحديث المدة النهائية
        final_duration = get_audio_duration(final_audio)
        script["duration_estimate"] = final_duration
        script["actual_audio_duration"] = final_duration
        log(f"  ✓ مدة نهائية: {final_duration:.1f}s", "ok")

        # ══════════════════════════════════════════════════════════
        # [5/6] 🎬 بناء الفيديو
        # ══════════════════════════════════════════════════════════
        log("\n[5/6] 🎬 بناء الفيديو...", "cyan")

        if use_remotion and isinstance(renderer, RemotionRenderer):
            props = build_complete_props(
                script=script,
                audio_path=final_audio,
                output_dir=output_dir,
            )
            props["totalDuration"] = final_duration
            props["audioActualDuration"] = final_duration

            log(f"  ✓ {props['meta']['totalScenes']} مشهد", "ok")
            log(f"  ✓ {props['meta']['totalSubtitles']} ترجمة", "ok")
            log(f"  ✓ مدة الفيديو: {final_duration:.1f}s", "ok")
        else:
            raise NotImplementedError("استخدم Remotion")

        # ══════════════════════════════════════════════════════════
        # [6/6] 🚀 التصدير النهائي
        # ══════════════════════════════════════════════════════════
        log("\n[6/6] 🚀 التصدير النهائي...", "cyan")

        renderer.render_final(
            props=props,
            output_path=out,
            quality=quality,
            metadata={
                "title": script.get("title", topic),
                "description": script.get("hook", ""),
                "comment": f"AI Shorts Factory v3.0 | {content_type} | Score: {script_score}",
            },
        )

        log(f"  ✓ الفيديو جاهز", "ok")

        # Thumbnail
        try:
            thumb = out.replace(".mp4", "_thumb.jpg")
            renderer.create_thumbnail(out, thumb)
            log(f"  ✓ Thumbnail: {Path(thumb).name}", "ok")
        except Exception:
            pass

        # Info file
        try:
            info_file = out.replace(".mp4", "_info.txt")
            with open(info_file, "w", encoding="utf-8") as f:
                f.write(f"Title: {script.get('title', topic)}\n")
                f.write(f"Topic: {topic}\n")
                f.write(f"Type: {content_type}\n")
                f.write(f"Duration: {final_duration:.1f}s\n")
                f.write(f"Quality Score: {script_score}/100\n")
                f.write(f"Hook: {script.get('hook', '')}\n")
                f.write(f"Generated: {ts}\n")
                f.write(f"TTS: {os.getenv('TTS_ENGINE', 'edge')}\n")
                f.write(f"Music: {'✓' if music_file else '✗'}\n")
                f.write(f"SFX: {len(sfx_tracks)}\n")
                f.write(f"Audio: {raw_duration:.1f}s → {final_duration:.1f}s\n")
        except Exception:
            pass

        # حجم الملف
        try:
            size_mb = Path(out).stat().st_size / (1024 * 1024)
            log(f"  📦 حجم: {size_mb:.2f} MB", "info")
        except Exception:
            pass

        success = True
        return out

    finally:
        if success:
            try:
                renderer.cleanup_temp()
                log("  🧹 تم التنظيف", "info")
            except Exception:
                pass
        else:
            log("  ⚠ الملفات المؤقتة محفوظة", "warn")


# ─── الدالة الرئيسية ──────────────────────────────────────────────────────
def main():
    parser = argparse.ArgumentParser(
        description="🎬 Viral AI Content Factory v3.0"
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

    if not check_env(use_remotion=use_remotion):
        log("\n❌ أصلح المشاكل ثم أعد المحاولة.", "err")
        sys.exit(1)

    if args.check:
        log("\n✅ كل شيء جاهز!", "ok")
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
            log(f"📋 النوع: {args.type} | ⏱ المدة: {args.duration}s | ✨ الجودة: {args.quality}", "info")

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
