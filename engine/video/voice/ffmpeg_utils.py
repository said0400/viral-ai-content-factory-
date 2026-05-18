"""
🔧 FFmpeg Utilities — أدوات مشتركة
═══════════════════════════════════════════════════════════════
دوال مشتركة بين كل محركات الصوت/الفيديو
═══════════════════════════════════════════════════════════════
"""

from __future__ import annotations

import json
import shutil
import logging
import subprocess
from pathlib import Path
from dataclasses import dataclass
from typing import Optional

logger = logging.getLogger(__name__)


# ═══════════════════════════════════════════════════════════════════
# Constants
# ═══════════════════════════════════════════════════════════════════
class FFmpegConstants:
    """ثوابت FFmpeg."""
    
    DEFAULT_SAMPLE_RATE = 44100
    DEFAULT_CHANNELS = 2
    DEFAULT_BITRATE = "192k"
    DEFAULT_TIMEOUT = 180
    
    MIN_FILE_SIZE = 1000  # bytes


# ═══════════════════════════════════════════════════════════════════
# Result Dataclass
# ═══════════════════════════════════════════════════════════════════
@dataclass
class FFmpegResult:
    """نتيجة تشغيل FFmpeg."""
    success: bool
    output_path: str
    duration: float = 0.0
    file_size: int = 0
    error: Optional[str] = None
    elapsed_seconds: float = 0.0


# ═══════════════════════════════════════════════════════════════════
# Detection
# ═══════════════════════════════════════════════════════════════════
def check_ffmpeg_available() -> bool:
    """التحقق من FFmpeg."""
    return shutil.which("ffmpeg") is not None


def check_ffprobe_available() -> bool:
    """التحقق من FFprobe."""
    return shutil.which("ffprobe") is not None


def ensure_ffmpeg() -> None:
    """يرمي خطأ إذا FFmpeg غير متاح."""
    if not check_ffmpeg_available():
        raise RuntimeError(
            "❌ FFmpeg غير مثبت!\n"
            "   تثبيت: https://ffmpeg.org/download.html"
        )


# ═══════════════════════════════════════════════════════════════════
# Audio Info
# ═══════════════════════════════════════════════════════════════════
def get_audio_duration(path: str) -> float:
    """مدة الصوت بالثواني."""
    if not Path(path).exists():
        return 0.0
    
    if not check_ffprobe_available():
        logger.warning("⚠ ffprobe غير متاح")
        return 0.0
    
    try:
        result = subprocess.run(
            [
                "ffprobe", "-v", "quiet",
                "-show_entries", "format=duration",
                "-of", "default=noprint_wrappers=1:nokey=1",
                path,
            ],
            capture_output=True,
            text=True,
            timeout=30,
            check=True,
        )
        return float(result.stdout.strip())
    except Exception as e:
        logger.debug(f"Duration check failed: {e}")
        return 0.0


def get_audio_info(path: str) -> dict:
    """معلومات شاملة للملف الصوتي."""
    if not Path(path).exists() or not check_ffprobe_available():
        return {}
    
    try:
        result = subprocess.run(
            [
                "ffprobe", "-v", "quiet",
                "-print_format", "json",
                "-show_format",
                "-show_streams",
                path,
            ],
            capture_output=True,
            text=True,
            timeout=30,
            check=True,
        )
        return json.loads(result.stdout)
    except Exception as e:
        logger.debug(f"Audio info failed: {e}")
        return {}


# ═══════════════════════════════════════════════════════════════════
# FFmpeg Runner
# ═══════════════════════════════════════════════════════════════════
def run_ffmpeg(
    args: list[str],
    output_path: str,
    description: str = "FFmpeg",
    audio_config: bool = True,
    sample_rate: Optional[int] = None,
    channels: Optional[int] = None,
    bitrate: Optional[str] = None,
    timeout: Optional[int] = None,
) -> FFmpegResult:
    """
    تشغيل FFmpeg مع معالجة كاملة.
    
    Args:
        args: arguments قبل output_path
        output_path: مسار الإخراج
        description: وصف للـ logging
        audio_config: إضافة إعدادات صوتية تلقائية
        sample_rate, channels, bitrate: إعدادات صوتية
        timeout: timeout بالثواني
    
    Returns:
        FFmpegResult
    """
    import time
    start = time.time()
    
    # ضمان وجود مجلد output
    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    
    # بناء الأمر
    cmd = ["ffmpeg", "-y", "-loglevel", "error"] + args
    
    if audio_config:
        cmd.extend([
            "-ar", str(sample_rate or FFmpegConstants.DEFAULT_SAMPLE_RATE),
            "-ac", str(channels or FFmpegConstants.DEFAULT_CHANNELS),
            "-b:a", bitrate or FFmpegConstants.DEFAULT_BITRATE,
        ])
    
    cmd.append(output_path)
    
    # تشغيل
    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            timeout=timeout or FFmpegConstants.DEFAULT_TIMEOUT,
        )
        
        elapsed = time.time() - start
        
        if result.returncode == 0:
            output_file = Path(output_path)
            file_size = output_file.stat().st_size if output_file.exists() else 0
            
            if file_size < FFmpegConstants.MIN_FILE_SIZE:
                return FFmpegResult(
                    success=False,
                    output_path=output_path,
                    elapsed_seconds=elapsed,
                    error="Output file too small",
                )
            
            return FFmpegResult(
                success=True,
                output_path=output_path,
                duration=get_audio_duration(output_path),
                file_size=file_size,
                elapsed_seconds=elapsed,
            )
        else:
            err = result.stderr.decode("utf-8", errors="ignore")[:300]
            logger.warning(f"⚠ {description}: {err}")
            return FFmpegResult(
                success=False,
                output_path=output_path,
                elapsed_seconds=elapsed,
                error=err,
            )
            
    except subprocess.TimeoutExpired:
        return FFmpegResult(
            success=False,
            output_path=output_path,
            elapsed_seconds=time.time() - start,
            error="Timeout",
        )
    except Exception as e:
        return FFmpegResult(
            success=False,
            output_path=output_path,
            elapsed_seconds=time.time() - start,
            error=str(e),
        )


# ═══════════════════════════════════════════════════════════════════
# Safe Copy
# ═══════════════════════════════════════════════════════════════════
def safe_copy(src: str, dst: str) -> bool:
    """نسخ آمن."""
    try:
        Path(dst).parent.mkdir(parents=True, exist_ok=True)
        if Path(src).exists():
            shutil.copy(src, dst)
            return True
    except Exception as e:
        logger.error(f"❌ Copy failed: {e}")
    return False


# ═══════════════════════════════════════════════════════════════════
# Silence Generator
# ═══════════════════════════════════════════════════════════════════
def generate_silence(
    duration: float,
    output_path: str,
    sample_rate: int = 44100,
) -> FFmpegResult:
    """توليد ملف صمت."""
    return run_ffmpeg(
        [
            "-f", "lavfi",
            "-i", f"anullsrc=r={sample_rate}:cl=stereo",
            "-t", str(duration),
        ],
        output_path,
        description=f"Silence ({duration}s)",
        sample_rate=sample_rate,
    )
