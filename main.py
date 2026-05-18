"""
🎬 Viral AI Content Factory — main.py v4.0
═══════════════════════════════════════════════════════════════════
استخدام ContentFactory الموحّد + Quality-First

التحسينات v4.0:
  ✓ يستخدم engine.ContentFactory (لا تكرار)
  ✓ Quality validation تلقائي
  ✓ Progress callback
  ✓ Better CLI
  ✓ JSON info files
  ✓ Batch mode محسّن
═══════════════════════════════════════════════════════════════════
"""

from __future__ import annotations

import os
import sys
import time
import json
import argparse
import traceback
from pathlib import Path
from datetime import datetime
from typing import Optional

from dotenv import load_dotenv

# تحميل .env قبل أي import آخر
load_dotenv()

# ═══════════════════════════════════════════════════════════════════
# Engine imports
# ═══════════════════════════════════════════════════════════════════
from engine import (
    ContentFactory,
    GenerationResult,
    GenerationStage,
    SUPPORTED_DURATIONS,
    check_environment,
    check_requirements,
    print_status,
    setup_logging,
    PROJECT_NAME,
    __version__,
)


# ═══════════════════════════════════════════════════════════════════
# Colors
# ═══════════════════════════════════════════════════════════════════
COLORS = {
    "info": "\033[97m",
    "ok": "\033[92m",
    "warn": "\033[93m",
    "err": "\033[91m",
    "cyan": "\033[96m",
    "bold": "\033[1m",
    "dim": "\033[2m",
    "reset": "\033[0m",
}


def log(msg: str, kind: str = "info") -> None:
    """طباعة ملوّنة."""
    color = COLORS.get(kind, "")
    print(f"{color}{msg}{COLORS['reset']}")


def banner() -> None:
    """شعار البرنامج."""
    log("━" * 60, "cyan")
    log(f"  🎬  {PROJECT_NAME}", "bold")
    log(f"  v{__version__} - Quality-First Edition", "info")
    log(f"  ⭐ Auto-Validation + Smart Retry", "ok")
    log("━" * 60, "cyan")


# ═══════════════════════════════════════════════════════════════════
# Environment Check
# ═══════════════════════════════════════════════════════════════════
def check_environment_full() -> bool:
    """فحص شامل للبيئة."""
    log("\n🔐 فحص البيئة...", "cyan")
    
    env = check_environment()
    api_keys = env["api_keys"]
    
    # API Keys
    required_keys = ["GROQ_API_KEY"]
    optional_keys = ["GEMINI_API_KEY", "PEXELS_API_KEY", "PIXABAY_API_KEY", "ELEVENLABS_API_KEY"]
    
    all_ok = True
    
    for key in required_keys:
        if api_keys.get(key):
            log(f"  ✓ {key}", "ok")
        else:
            log(f"  ✗ {key} (REQUIRED)", "err")
            all_ok = False
    
    for key in optional_keys:
        if api_keys.get(key):
            log(f"  ✓ {key}", "ok")
        else:
            log(f"  ⚠ {key} (optional)", "warn")
    
    # Requirements
    log("\n📦 فحص المكتبات...", "cyan")
    requirements = check_requirements()
    
    critical = ["Groq AI", "Edge TTS"]
    for req in critical:
        if requirements.get(req):
            log(f"  ✓ {req}", "ok")
        else:
            log(f"  ✗ {req}", "err")
            all_ok = False
    
    return all_ok


# ═══════════════════════════════════════════════════════════════════
# Progress Callback
# ═══════════════════════════════════════════════════════════════════
def create_progress_callback(verbose: bool = True):
    """إنشاء callback للتقدم."""
    if not verbose:
        return None
    
    last_stage = ""
    
    def callback(stage: str, percent: float):
        nonlocal last_stage
        
        # Stage emojis
        stage_emojis = {
            GenerationStage.SCRIPT.value: "📝",
            GenerationStage.VOICE.value: "🎙️",
            GenerationStage.VIDEO.value: "🎬",
            GenerationStage.RENDER.value: "🎞️",
            GenerationStage.COMPLETE.value: "✅",
        }
        
        emoji = stage_emojis.get(stage, "⏳")
        
        if stage != last_stage:
            log(f"\n{emoji} {stage.upper()}", "cyan")
            last_stage = stage
        
        # Progress bar
        bar_length = 30
        filled = int(bar_length * percent)
        bar = "█" * filled + "░" * (bar_length - filled)
        
        # Print on same line
        sys.stdout.write(
            f"\r  [{bar}] {percent*100:5.1f}%"
        )
        sys.stdout.flush()
        
        if percent >= 1.0:
            print()  # newline
    
    return callback


# ═══════════════════════════════════════════════════════════════════
# Result Saver
# ═══════════════════════════════════════════════════════════════════
def save_result_info(
    result: GenerationResult,
    output_dir: str,
) -> Optional[str]:
    """حفظ معلومات النتيجة كـ JSON."""
    if not result.success or not result.output_path:
        return None
    
    try:
        video_path = Path(result.output_path)
        info_path = video_path.with_suffix(".info.json")
        
        info = {
            "topic": result.topic,
            "content_type": result.content_type,
            "duration": result.duration,
            "output_path": str(video_path),
            "file_size_mb": result.file_size_mb,
            "total_time_seconds": result.total_time,
            "generated_at": datetime.now().isoformat(),
            "version": __version__,
        }
        
        # إضافة تفاصيل من النتائج
        if result.script_result:
            script = result.script_result
            info["script"] = {
                "title": script.get("title", ""),
                "hook": script.get("hook", ""),
                "scenes_count": len(script.get("scenes", [])),
                "mood": script.get("music_mood", ""),
            }
            
            # Validation score
            if "validation" in script:
                info["script"]["quality_score"] = script["validation"].get("score", 0)
        
        if result.voice_result:
            info["voice"] = {
                "provider": result.voice_result.voice_used,
                "duration": result.voice_result.duration_estimate,
                "file_size": result.voice_result.file_size,
                "cached": result.voice_result.cached,
            }
        
        if result.render_result:
            info["render"] = {
                "quality": result.render_result.quality,
                "resolution": f"{result.render_result.width}x{result.render_result.height}",
                "elapsed": result.render_result.elapsed_seconds,
            }
        
        # حفظ
        with open(info_path, "w", encoding="utf-8") as f:
            json.dump(info, f, indent=2, ensure_ascii=False)
        
        return str(info_path)
        
    except Exception as e:
        log(f"  ⚠ Failed to save info: {e}", "warn")
        return None


def create_thumbnail(video_path: str) -> Optional[str]:
    """إنشاء thumbnail."""
    try:
        from engine.render import VideoUtils
        utils = VideoUtils()
        
        thumb_path = Path(video_path).with_suffix(".thumb.jpg")
        result = utils.create_thumbnail(
            video_path,
            str(thumb_path),
            timestamp=1.5,
        )
        
        if result.success:
            return str(thumb_path)
    except Exception:
        pass
    
    return None


# ═══════════════════════════════════════════════════════════════════
# Generate Single Video
# ═══════════════════════════════════════════════════════════════════
def generate_single_video(
    factory: ContentFactory,
    topic: str,
    content_type: str,
    duration: int,
    quality: str,
    output_dir: str,
    verbose: bool = True,
) -> GenerationResult:
    """توليد فيديو واحد."""
    log(f"\n🎬 الموضوع: {topic}", "bold")
    log(
        f"📋 النوع: {content_type} | "
        f"⏱ المدة: {duration}s | "
        f"✨ الجودة: {quality}",
        "info",
    )
    
    start_time = time.time()
    
    # Generate
    result = factory.generate(
        topic=topic,
        content_type=content_type,
        target_duration=duration,
        quality=quality,
        progress_callback=create_progress_callback(verbose),
    )
    
    elapsed = time.time() - start_time
    
    # Display result
    if result.success:
        log(f"\n✅ تم بنجاح في {elapsed:.0f}s", "ok")
        log(f"📁 {result.output_path}", "ok")
        log(f"📦 {result.file_size_mb:.1f} MB", "info")
        log(f"⏱ {result.duration:.1f}s", "info")
        
        # Save info & thumbnail
        info_path = save_result_info(result, output_dir)
        if info_path:
            log(f"📄 {Path(info_path).name}", "dim")
        
        thumb_path = create_thumbnail(result.output_path)
        if thumb_path:
            log(f"🖼  {Path(thumb_path).name}", "dim")
    else:
        log(f"\n❌ فشل التوليد", "err")
        log(f"   Stage failed: {result.stage_failed}", "err")
        log(f"   Error: {result.error}", "err")
    
    return result


# ═══════════════════════════════════════════════════════════════════
# Batch Mode
# ═══════════════════════════════════════════════════════════════════
def generate_batch(
    factory: ContentFactory,
    topics: list[str],
    content_type: str,
    duration: int,
    quality: str,
    output_dir: str,
) -> list[GenerationResult]:
    """توليد batch من الفيديوهات."""
    results: list[GenerationResult] = []
    total = len(topics)
    
    log(f"\n📦 Batch mode: {total} videos", "bold")
    log(f"   Type: {content_type} | Duration: {duration}s\n", "info")
    
    for i, topic in enumerate(topics, 1):
        log(f"\n{'═' * 60}", "cyan")
        log(f"  🎬 [{i}/{total}] {topic}", "bold")
        log(f"{'═' * 60}", "cyan")
        
        try:
            result = generate_single_video(
                factory=factory,
                topic=topic,
                content_type=content_type,
                duration=duration,
                quality=quality,
                output_dir=output_dir,
                verbose=True,
            )
            results.append(result)
        except KeyboardInterrupt:
            log("\n⚠ تم الإلغاء بواسطة المستخدم", "warn")
            break
        except Exception as e:
            log(f"\n❌ خطأ غير متوقع: {e}", "err")
            traceback.print_exc()
            
            # Add failed result
            failed_result = GenerationResult(
                success=False,
                topic=topic,
                error=str(e),
            )
            results.append(failed_result)
    
    return results


def print_batch_summary(results: list[GenerationResult]) -> None:
    """طباعة ملخص الـ batch."""
    log(f"\n{'═' * 60}", "cyan")
    log("  📊 BATCH SUMMARY", "bold")
    log(f"{'═' * 60}", "cyan")
    
    successful = sum(1 for r in results if r.success)
    failed = len(results) - successful
    total_time = sum(r.total_time for r in results)
    
    log(f"\n  ✅ Successful: {successful}/{len(results)}", "ok")
    if failed > 0:
        log(f"  ❌ Failed: {failed}/{len(results)}", "err")
    log(f"  ⏱ Total time: {total_time:.0f}s", "info")
    log(f"  📊 Avg time: {total_time/len(results):.0f}s/video", "info")
    
    log("\n  📋 Details:", "info")
    for i, result in enumerate(results, 1):
        status = "✅" if result.success else "❌"
        time_str = f"{result.total_time:.0f}s"
        log(
            f"  {status} [{i}] {result.topic[:40]:40s} ({time_str})",
            "ok" if result.success else "err",
        )
    
    log(f"\n{'═' * 60}", "cyan")


# ═══════════════════════════════════════════════════════════════════
# CLI
# ═══════════════════════════════════════════════════════════════════
def parse_args():
    """تحليل arguments."""
    parser = argparse.ArgumentParser(
        description=f"🎬 {PROJECT_NAME} v{__version__}",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # توليد فيديو واحد
  python main.py --topic "الطموح والنجاح"
  
  # تخصيص النوع والمدة
  python main.py --topic "كيف تتعلم" --type educational --duration 60
  
  # جودة عالية
  python main.py --topic "النجاح" --quality ultra
  
  # Batch mode
  python main.py --batch "موضوع 1" "موضوع 2" "موضوع 3"
  
  # فقط فحص البيئة
  python main.py --check
  
  # طباعة حالة كاملة
  python main.py --status
        """,
    )
    
    # Topic & Type
    parser.add_argument(
        "--topic",
        type=str,
        default=os.getenv("DEFAULT_TOPIC", "الطموح والنجاح"),
        help="موضوع الفيديو",
    )
    
    parser.add_argument(
        "--type",
        type=str,
        choices=["motivational", "educational", "story", "quote"],
        default=os.getenv("CONTENT_TYPE", "motivational"),
        help="نوع المحتوى",
    )
    
    parser.add_argument(
        "--duration",
        type=int,
        choices=list(SUPPORTED_DURATIONS),
        default=int(os.getenv("VIDEO_TARGET_DURATION", "45")),
        help="المدة بالثواني",
    )
    
    parser.add_argument(
        "--quality",
        type=str,
        choices=["draft", "medium", "high", "ultra"],
        default=os.getenv("VIDEO_QUALITY", "high"),
        help="جودة التصدير",
    )
    
    parser.add_argument(
        "--output",
        type=str,
        default=os.getenv("OUTPUT_DIR", "./output"),
        help="مجلد الإخراج",
    )
    
    # Providers
    parser.add_argument(
        "--ai-provider",
        type=str,
        choices=["auto", "groq", "gemini"],
        default="auto",
        help="مزود AI",
    )
    
    parser.add_argument(
        "--tts-engine",
        type=str,
        choices=["auto", "edge", "groq", "gemini", "elevenlabs"],
        default=os.getenv("TTS_ENGINE", "auto"),
        help="محرك TTS",
    )
    
    # Batch
    parser.add_argument(
        "--batch",
        type=str,
        nargs="+",
        help="Batch mode - عدة مواضيع",
    )
    
    # Flags
    parser.add_argument(
        "--check",
        action="store_true",
        help="فحص البيئة فقط",
    )
    
    parser.add_argument(
        "--status",
        action="store_true",
        help="طباعة حالة كاملة",
    )
    
    parser.add_argument(
        "--quiet",
        action="store_true",
        help="عرض أقل",
    )
    
    parser.add_argument(
        "--log-file",
        type=str,
        help="حفظ السجلات في ملف",
    )
    
    parser.add_argument(
        "--cleanup",
        action="store_true",
        help="تنظيف ملفات temp بعد الانتهاء",
    )
    
    return parser.parse_args()


# ═══════════════════════════════════════════════════════════════════
# Main
# ═══════════════════════════════════════════════════════════════════
def main():
    """الدالة الرئيسية."""
    args = parse_args()
    
    # Setup logging
    setup_logging(
        level="WARNING" if args.quiet else "INFO",
        log_file=args.log_file,
    )
    
    # Banner
    banner()
    
    # Status mode
    if args.status:
        print_status()
        sys.exit(0)
    
    # Environment check
    if not check_environment_full():
        log("\n❌ أصلح المشاكل أعلاه ثم أعد المحاولة", "err")
        sys.exit(1)
    
    # Check mode
    if args.check:
        log("\n✅ كل شيء جاهز!", "ok")
        sys.exit(0)
    
    # Initialize factory
    log("\n⚙️  تهيئة المصنع...", "cyan")
    try:
        factory = ContentFactory(
            ai_provider=args.ai_provider,
            tts_engine=args.tts_engine,
            cache_enabled=True,
            log_level="WARNING" if args.quiet else "INFO",
        )
        log("  ✓ Factory جاهز", "ok")
    except Exception as e:
        log(f"\n❌ فشل تهيئة المصنع: {e}", "err")
        traceback.print_exc()
        sys.exit(1)
    
    # Generate
    try:
        if args.batch:
            # Batch mode
            results = generate_batch(
                factory=factory,
                topics=args.batch,
                content_type=args.type,
                duration=args.duration,
                quality=args.quality,
                output_dir=args.output,
            )
            print_batch_summary(results)
            
            # Exit with error if any failed
            if any(not r.success for r in results):
                sys.exit(1)
        else:
            # Single mode
            result = generate_single_video(
                factory=factory,
                topic=args.topic,
                content_type=args.type,
                duration=args.duration,
                quality=args.quality,
                output_dir=args.output,
                verbose=not args.quiet,
            )
            
            if not result.success:
                sys.exit(1)
        
        # Cleanup
        if args.cleanup:
            log("\n🧹 تنظيف...", "cyan")
            factory.cleanup()
            log("  ✓ تم التنظيف", "ok")
        
    except KeyboardInterrupt:
        log("\n\n⚠ تم الإلغاء", "warn")
        sys.exit(130)
    except Exception as e:
        log(f"\n❌ خطأ: {e}", "err")
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
