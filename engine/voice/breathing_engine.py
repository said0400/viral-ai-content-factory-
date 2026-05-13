"""
🫁 Breathing Engine — إضافة تنفس طبيعي للصوت
═══════════════════════════════════════════════════════════════
يضيف أصوات تنفس واقعية لجعل الصوت أكثر إنسانية:
  ✓ Inhale (شهيق) في البداية
  ✓ تنويع تلقائي لشدة وطول النفس
  ✓ يمكن تعطيله عبر BREATHING_ENABLED=false
  ✓ Fallback آمن عند الفشل

ضع في: engine/voice/breathing_engine.py
═══════════════════════════════════════════════════════════════
"""

import os
import random
import shutil
import logging
import subprocess
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)


class BreathingEngine:
    """محرك إضافة التنفس الطبيعي للصوت."""

    # ─── أنواع التنفس ─────────────────────────────────────────────
    BREATH_PRESETS = {
        "soft": {
            "duration":  0.35,
            "amplitude": 0.010,
            "lowpass":   650,
        },
        "normal": {
            "duration":  0.45,
            "amplitude": 0.014,
            "lowpass":   700,
        },
        "deep": {
            "duration":  0.65,
            "amplitude": 0.020,
            "lowpass":   600,
        },
        "intense": {
            "duration":  0.55,
            "amplitude": 0.025,
            "lowpass":   750,
        },
    }

    # ════════════════════════════════════════════════════════════════
    def __init__(self, enabled: Optional[bool] = None):
        """
        Args:
            enabled: تفعيل أو تعطيل التنفس (يُقرأ من .env إن لم يُحدد)
        """
        if enabled is None:
            enabled = os.getenv("BREATHING_ENABLED", "true").lower() == "true"

        self.enabled = enabled
        self.preset = os.getenv("BREATHING_PRESET", "normal")

        self.temp_dir = Path(os.getenv("TEMP_DIR", "./temp"))
        self.temp_dir.mkdir(parents=True, exist_ok=True)

        # مجلد فرعي للتنفس (لتنظيم أفضل)
        self.breath_dir = self.temp_dir / "breath"
        self.breath_dir.mkdir(exist_ok=True)

        if self.enabled:
            logger.info(f"🫁 BreathingEngine | Preset: {self.preset}")
        else:
            logger.info("🫁 BreathingEngine | Disabled")

    # ════════════════════════════════════════════════════════════════
    #                    الدالة الرئيسية
    # ════════════════════════════════════════════════════════════════
    def add_breathing(
        self,
        voice_path: str,
        output_path: str,
        preset: Optional[str] = None,
    ) -> str:
        """
        إضافة تنفس قبل الصوت.

        Args:
            voice_path: مسار الصوت الأصلي
            output_path: مسار الصوت الناتج
            preset: نوع التنفس (soft/normal/deep/intense)

        Returns:
            مسار الملف الصوتي الناتج
        """
        # إذا كان التنفس معطلاً → نسخ مباشر
        if not self.enabled:
            shutil.copy(voice_path, output_path)
            return output_path

        # التحقق من وجود الملف الأصلي
        if not Path(voice_path).exists():
            logger.error(f"❌ ملف الصوت غير موجود: {voice_path}")
            return voice_path

        preset = preset or self.preset
        if preset not in self.BREATH_PRESETS:
            logger.warning(f"⚠ Preset '{preset}' غير معروف، استخدام 'normal'")
            preset = "normal"

        try:
            # توليد ملف التنفس
            inhale_path = self._make_inhale(preset)

            if not inhale_path or not Path(inhale_path).exists():
                logger.warning("⚠ فشل توليد التنفس → نسخ بدون تنفس")
                shutil.copy(voice_path, output_path)
                return output_path

            # دمج التنفس مع الصوت
            success = self._concat_audio(inhale_path, voice_path, output_path)

            if success:
                logger.info(f"✓ تمت إضافة التنفس [{preset}]")
                return output_path
            else:
                logger.warning("⚠ فشل الدمج → نسخ بدون تنفس")
                shutil.copy(voice_path, output_path)
                return output_path

        except Exception as e:
            logger.error(f"❌ خطأ في إضافة التنفس: {e}")
            shutil.copy(voice_path, output_path)
            return output_path

    # ════════════════════════════════════════════════════════════════
    #                    توليد صوت التنفس
    # ════════════════════════════════════════════════════════════════
    def _make_inhale(self, preset: str = "normal") -> Optional[str]:
        """توليد ملف صوت التنفس."""
        cfg = self.BREATH_PRESETS[preset]

        # تنويع طفيف عشوائي لجعل كل تنفس مختلف قليلاً
        duration = cfg["duration"] + random.uniform(-0.05, 0.05)
        amplitude = cfg["amplitude"] + random.uniform(-0.002, 0.002)
        lowpass = cfg["lowpass"] + random.randint(-50, 50)

        # ملف فريد لكل تنفس (مع تنويع)
        seed = random.randint(1000, 9999)
        path = str(self.breath_dir / f"inhale_{preset}_{seed}.mp3")

        # حساب أوقات الـ fade
        fade_in = duration * 0.35
        fade_out_start = duration * 0.55
        fade_out = duration * 0.45

        try:
            result = subprocess.run(
                [
                    "ffmpeg", "-y",
                    "-f", "lavfi",
                    "-i", f"anoisesrc=color=pink:duration={duration}:amplitude={amplitude}",
                    "-af",
                    f"afade=t=in:st=0:d={fade_in:.3f},"
                    f"afade=t=out:st={fade_out_start:.3f}:d={fade_out:.3f},"
                    f"lowpass=f={lowpass}",
                    "-ar", "44100",
                    "-ac", "2",
                    "-c:a", "libmp3lame",
                    "-q:a", "4",
                    path,
                ],
                capture_output=True,
                timeout=15,
            )

            if result.returncode == 0 and Path(path).exists():
                return path

            logger.warning(f"⚠ FFmpeg فشل: {result.stderr.decode()[:150]}")

        except subprocess.TimeoutExpired:
            logger.warning("⚠ تجاوز الوقت في توليد التنفس")
        except Exception as e:
            logger.warning(f"⚠ فشل التوليد: {e}")

        # Fallback: ملف صمت قصير
        return self._make_silence(duration, path)

    # ════════════════════════════════════════════════════════════════
    #                    صمت احتياطي
    # ════════════════════════════════════════════════════════════════
    def _make_silence(self, duration: float, path: str) -> Optional[str]:
        """توليد صمت كبديل عند فشل التنفس."""
        try:
            result = subprocess.run(
                [
                    "ffmpeg", "-y",
                    "-f", "lavfi",
                    "-i", "anullsrc=r=44100:cl=stereo",
                    "-t", str(duration),
                    "-c:a", "libmp3lame",
                    "-q:a", "9",
                    path,
                ],
                capture_output=True,
                timeout=10,
            )
            if result.returncode == 0:
                return path
        except Exception as e:
            logger.error(f"❌ فشل توليد الصمت: {e}")
        return None

    # ════════════════════════════════════════════════════════════════
    #                    دمج الصوت
    # ════════════════════════════════════════════════════════════════
    def _concat_audio(
        self,
        first: str,
        second: str,
        output: str,
    ) -> bool:
        """دمج ملفين صوتيين باستخدام concat demuxer."""
        # ملف قائمة الدمج (فريد لكل عملية)
        concat_list = self.breath_dir / f"concat_{os.getpid()}_{random.randint(1000,9999)}.txt"

        try:
            with open(concat_list, "w", encoding="utf-8") as f:
                f.write(f"file '{Path(first).resolve()}'\n")
                f.write(f"file '{Path(second).resolve()}'\n")

            result = subprocess.run(
                [
                    "ffmpeg", "-y",
                    "-f", "concat",
                    "-safe", "0",
                    "-i", str(concat_list),
                    "-c:a", "libmp3lame",
                    "-q:a", "2",
                    "-ar", "44100",
                    output,
                ],
                capture_output=True,
                timeout=30,
            )

            return result.returncode == 0 and Path(output).exists()

        except Exception as e:
            logger.error(f"❌ فشل الدمج: {e}")
            return False
        finally:
            # تنظيف ملف القائمة
            try:
                concat_list.unlink(missing_ok=True)
            except Exception:
                pass

    # ════════════════════════════════════════════════════════════════
    #                    دوال إضافية
    # ════════════════════════════════════════════════════════════════
    def add_breathing_advanced(
        self,
        voice_path: str,
        output_path: str,
        intro_preset: str = "normal",
        outro_preset: str = "soft",
    ) -> str:
        """
        إضافة تنفس في البداية والنهاية (متقدم).

        Args:
            voice_path: مسار الصوت الأصلي
            output_path: مسار الصوت الناتج
            intro_preset: نوع تنفس البداية
            outro_preset: نوع تنفس النهاية
        """
        if not self.enabled:
            shutil.copy(voice_path, output_path)
            return output_path

        try:
            intro = self._make_inhale(intro_preset)
            outro = self._make_inhale(outro_preset)

            if not intro or not outro:
                return self.add_breathing(voice_path, output_path)

            # دمج الثلاثة
            concat_list = self.breath_dir / f"concat3_{os.getpid()}.txt"
            with open(concat_list, "w", encoding="utf-8") as f:
                f.write(f"file '{Path(intro).resolve()}'\n")
                f.write(f"file '{Path(voice_path).resolve()}'\n")
                f.write(f"file '{Path(outro).resolve()}'\n")

            result = subprocess.run(
                [
                    "ffmpeg", "-y",
                    "-f", "concat", "-safe", "0",
                    "-i", str(concat_list),
                    "-c:a", "libmp3lame", "-q:a", "2",
                    output_path,
                ],
                capture_output=True,
                timeout=30,
            )

            concat_list.unlink(missing_ok=True)

            if result.returncode == 0:
                logger.info(f"✓ تنفس متقدم [intro:{intro_preset}, outro:{outro_preset}]")
                return output_path

        except Exception as e:
            logger.error(f"❌ فشل التنفس المتقدم: {e}")

        # Fallback
        return self.add_breathing(voice_path, output_path, intro_preset)

    def cleanup(self) -> None:
        """تنظيف ملفات التنفس المؤقتة."""
        try:
            for f in self.breath_dir.glob("*.mp3"):
                f.unlink(missing_ok=True)
            for f in self.breath_dir.glob("*.txt"):
                f.unlink(missing_ok=True)
            logger.debug("🧹 تم تنظيف ملفات التنفس")
        except Exception as e:
            logger.warning(f"⚠ فشل التنظيف: {e}")

    @staticmethod
    def list_presets() -> list:
        """قائمة الـ presets المتاحة."""
        return list(BreathingEngine.BREATH_PRESETS.keys())


# ════════════════════════════════════════════════════════════════════════
#                    اختبار سريع
# ════════════════════════════════════════════════════════════════════════
if __name__ == "__main__":
    import sys

    if len(sys.argv) < 3:
        print("Usage: python breathing_engine.py <input.mp3> <output.mp3> [preset]")
        sys.exit(1)

    input_file = sys.argv[1]
    output_file = sys.argv[2]
    preset = sys.argv[3] if len(sys.argv) > 3 else "normal"

    engine = BreathingEngine()
    result = engine.add_breathing(input_file, output_file, preset)
    print(f"✓ تم: {result}")
