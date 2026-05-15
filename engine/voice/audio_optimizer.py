"""
🎵 Audio Optimizer — تحسين الصوت لـ Viral Content
═══════════════════════════════════════════════════════════════
يحسّن الصوت بـ:
  ✓ إزالة الفراغات والصمت الطويل
  ✓ تسريع الصوت بنسبة قابلة للتعديل
  ✓ تطبيع الصوت (Normalize)
  ✓ تحسين الجودة (EQ + Compression)
  ✓ إزالة الضوضاء

ضع في: engine/voice/audio_optimizer.py
═══════════════════════════════════════════════════════════════
"""

import os
import logging
import subprocess
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)


class AudioOptimizer:
    """محسّن الصوت للمحتوى الفيروسي."""

    # ═════════════════════════════════════════════════════════════════
    #                    إعدادات افتراضية
    # ═════════════════════════════════════════════════════════════════
    
    # 🎯 سرعة الصوت (1.0 = طبيعي)
    DEFAULT_SPEED = 1.1  # 10% أسرع - مثالي لـ TikTok
    
    # 🔇 حد الصمت بالـ dB (أصغر = أكثر حساسية)
    SILENCE_THRESHOLD_DB = -35
    
    # ⏱️ أدنى مدة للصمت ليُحذف (بالثواني)
    MIN_SILENCE_DURATION = 0.4  # نصف ثانية
    
    # 🎵 مدة الصمت المسموح بها (للحفاظ على الإيقاع الطبيعي)
    KEEP_SILENCE_DURATION = 0.15  # 150ms
    
    # ═════════════════════════════════════════════════════════════════
    def __init__(self):
        """تهيئة المحسّن."""
        self.speed = float(os.getenv("AUDIO_SPEED", self.DEFAULT_SPEED))
        self.silence_threshold = float(
            os.getenv("SILENCE_THRESHOLD_DB", self.SILENCE_THRESHOLD_DB)
        )
        self.min_silence_duration = float(
            os.getenv("MIN_SILENCE_DURATION", self.MIN_SILENCE_DURATION)
        )
        self.keep_silence = float(
            os.getenv("KEEP_SILENCE_DURATION", self.KEEP_SILENCE_DURATION)
        )
        
        # الميزات (يمكن تعطيلها)
        self.remove_silence = os.getenv(
            "REMOVE_SILENCE", "true"
        ).lower() == "true"
        self.speed_up = os.getenv(
            "SPEED_UP_AUDIO", "true"
        ).lower() == "true"
        self.normalize = os.getenv(
            "NORMALIZE_AUDIO", "true"
        ).lower() == "true"
        self.enhance = os.getenv(
            "ENHANCE_AUDIO", "true"
        ).lower() == "true"
        
        logger.info(
            f"🎵 AudioOptimizer | Speed: {self.speed}x | "
            f"Remove silence: {self.remove_silence} | "
            f"Normalize: {self.normalize}"
        )

    # ═════════════════════════════════════════════════════════════════
    #                    🎯 الدالة الرئيسية
    # ═════════════════════════════════════════════════════════════════
    def optimize(
        self,
        input_path: str,
        output_path: str,
        speed: Optional[float] = None,
    ) -> str:
        """
        🎯 تحسين الصوت بكل المعالجات.
        
        Args:
            input_path: مسار الصوت الأصلي
            output_path: مسار الصوت المُحسّن
            speed: سرعة مخصصة (اختياري)
        
        Returns:
            مسار الصوت المُحسّن
        """
        if not Path(input_path).exists():
            raise FileNotFoundError(f"❌ ملف الصوت غير موجود: {input_path}")
        
        actual_speed = speed if speed is not None else self.speed
        
        logger.info(f"🎵 تحسين الصوت: {Path(input_path).name}")
        logger.info(f"   ⚡ Speed: {actual_speed}x")
        
        # المسارات المؤقتة
        temp_dir = Path(input_path).parent
        temp_files = []
        current = input_path
        
        try:
            # 1️⃣ إزالة الفراغات
            if self.remove_silence:
                temp_silence = str(temp_dir / "_temp_no_silence.mp3")
                temp_files.append(temp_silence)
                self._remove_silence(current, temp_silence)
                current = temp_silence
            
            # 2️⃣ تسريع الصوت
            if self.speed_up and actual_speed != 1.0:
                temp_speed = str(temp_dir / "_temp_speed.mp3")
                temp_files.append(temp_speed)
                self._change_speed(current, temp_speed, actual_speed)
                current = temp_speed
            
            # 3️⃣ تطبيع الصوت
            if self.normalize:
                temp_norm = str(temp_dir / "_temp_norm.mp3")
                temp_files.append(temp_norm)
                self._normalize_audio(current, temp_norm)
                current = temp_norm
            
            # 4️⃣ تحسين الجودة
            if self.enhance:
                temp_enhanced = str(temp_dir / "_temp_enhanced.mp3")
                temp_files.append(temp_enhanced)
                self._enhance_audio(current, temp_enhanced)
                current = temp_enhanced
            
            # 5️⃣ نسخ النتيجة النهائية
            import shutil
            shutil.copy(current, output_path)
            
            # عرض الإحصائيات
            self._print_stats(input_path, output_path)
            
            return output_path
            
        finally:
            # تنظيف الملفات المؤقتة
            for f in temp_files:
                try:
                    Path(f).unlink(missing_ok=True)
                except Exception:
                    pass

    # ═════════════════════════════════════════════════════════════════
    #                    🔇 إزالة الفراغات
    # ═════════════════════════════════════════════════════════════════
    def _remove_silence(self, input_path: str, output_path: str) -> None:
        """إزالة الصمت الطويل من الصوت."""
        logger.info("   🔇 إزالة الفراغات...")
        
        # silenceremove filter من FFmpeg
        # stop_periods=-1: يحذف كل فترات الصمت
        # stop_duration: أدنى مدة للصمت ليُحذف
        # stop_threshold: حد الصمت بالـ dB
        silence_filter = (
            f"silenceremove="
            f"start_periods=1:start_duration=0:start_threshold={self.silence_threshold}dB:"
            f"stop_periods=-1:stop_duration={self.min_silence_duration}:"
            f"stop_threshold={self.silence_threshold}dB:"
            f"detection=peak"
        )
        
        cmd = [
            "ffmpeg", "-y", "-loglevel", "error",
            "-i", input_path,
            "-af", silence_filter,
            "-c:a", "libmp3lame",
            "-b:a", "192k",
            "-ar", "44100",
            output_path,
        ]
        
        try:
            result = subprocess.run(
                cmd, capture_output=True, timeout=120, check=False
            )
            if result.returncode != 0:
                err = result.stderr.decode("utf-8", errors="ignore")[:300]
                logger.warning(f"⚠ فشل إزالة الصمت: {err}")
                # نسخ الملف كما هو
                import shutil
                shutil.copy(input_path, output_path)
        except Exception as e:
            logger.warning(f"⚠ خطأ في إزالة الصمت: {e}")
            import shutil
            shutil.copy(input_path, output_path)

    # ═════════════════════════════════════════════════════════════════
    #                    ⚡ تسريع الصوت
    # ═════════════════════════════════════════════════════════════════
    def _change_speed(
        self,
        input_path: str,
        output_path: str,
        speed: float,
    ) -> None:
        """تغيير سرعة الصوت بدون تغيير الـ pitch."""
        logger.info(f"   ⚡ تسريع الصوت: {speed}x")
        
        # atempo filter (يحافظ على الـ pitch)
        # يقبل قيم بين 0.5 و 2.0
        # للقيم خارج هذا المدى، نستخدم filters متعددة
        if 0.5 <= speed <= 2.0:
            tempo_filter = f"atempo={speed}"
        elif speed > 2.0:
            tempo_filter = "atempo=2.0,atempo=" + str(speed / 2.0)
        else:  # speed < 0.5
            tempo_filter = "atempo=0.5,atempo=" + str(speed / 0.5)
        
        cmd = [
            "ffmpeg", "-y", "-loglevel", "error",
            "-i", input_path,
            "-af", tempo_filter,
            "-c:a", "libmp3lame",
            "-b:a", "192k",
            "-ar", "44100",
            output_path,
        ]
        
        try:
            subprocess.run(cmd, check=True, capture_output=True, timeout=120)
        except subprocess.CalledProcessError as e:
            err = e.stderr.decode("utf-8", errors="ignore")[:300]
            logger.warning(f"⚠ فشل التسريع: {err}")
            import shutil
            shutil.copy(input_path, output_path)

    # ═════════════════════════════════════════════════════════════════
    #                    🎚️ تطبيع الصوت
    # ═════════════════════════════════════════════════════════════════
    def _normalize_audio(self, input_path: str, output_path: str) -> None:
        """تطبيع مستوى الصوت (Loudness Normalization)."""
        logger.info("   🎚️ تطبيع الصوت...")
        
        # loudnorm filter (EBU R128)
        # I=-16: متوسط الـ loudness (مناسب للـ podcast/voice)
        # TP=-1.5: peak limiter
        # LRA=11: loudness range
        normalize_filter = "loudnorm=I=-16:TP=-1.5:LRA=11"
        
        cmd = [
            "ffmpeg", "-y", "-loglevel", "error",
            "-i", input_path,
            "-af", normalize_filter,
            "-c:a", "libmp3lame",
            "-b:a", "192k",
            "-ar", "44100",
            output_path,
        ]
        
        try:
            subprocess.run(cmd, check=True, capture_output=True, timeout=120)
        except subprocess.CalledProcessError as e:
            err = e.stderr.decode("utf-8", errors="ignore")[:300]
            logger.warning(f"⚠ فشل التطبيع: {err}")
            import shutil
            shutil.copy(input_path, output_path)

    # ═════════════════════════════════════════════════════════════════
    #                    🎤 تحسين الجودة
    # ═════════════════════════════════════════════════════════════════
    def _enhance_audio(self, input_path: str, output_path: str) -> None:
        """تحسين جودة الصوت (EQ + Compression + De-noise)."""
        logger.info("   🎤 تحسين الجودة...")
        
        # سلسلة فلاتر:
        # 1. highpass: إزالة الترددات المنخفضة جداً (rumble)
        # 2. lowpass: إزالة الترددات العالية جداً (hiss)
        # 3. compand: ضغط ديناميكي (يجعل الصوت أكثر وضوحاً)
        # 4. equalizer: تعزيز ترددات الصوت البشري
        enhance_filter = (
            "highpass=f=80,"               # إزالة الـ rumble
            "lowpass=f=12000,"              # إزالة الـ hiss
            "compand=attacks=0.05:decays=0.5:points=-90/-90|-60/-60|-30/-15|0/-5,"  # compression
            "equalizer=f=200:width_type=q:width=1:g=2,"   # تعزيز low-mid
            "equalizer=f=3000:width_type=q:width=1:g=3,"  # تعزيز clarity
            "equalizer=f=8000:width_type=q:width=1:g=1"   # تعزيز presence
        )
        
        cmd = [
            "ffmpeg", "-y", "-loglevel", "error",
            "-i", input_path,
            "-af", enhance_filter,
            "-c:a", "libmp3lame",
            "-b:a", "192k",
            "-ar", "44100",
            output_path,
        ]
        
        try:
            subprocess.run(cmd, check=True, capture_output=True, timeout=120)
        except subprocess.CalledProcessError as e:
            err = e.stderr.decode("utf-8", errors="ignore")[:300]
            logger.warning(f"⚠ فشل التحسين: {err}")
            import shutil
            shutil.copy(input_path, output_path)

    # ═════════════════════════════════════════════════════════════════
    #                    📊 إحصائيات
    # ═════════════════════════════════════════════════════════════════
    def _print_stats(self, original: str, optimized: str) -> None:
        """طباعة إحصائيات التحسين."""
        try:
            original_dur = self._get_duration(original)
            optimized_dur = self._get_duration(optimized)
            
            saved_seconds = original_dur - optimized_dur
            saved_percent = (saved_seconds / original_dur * 100) if original_dur > 0 else 0
            
            original_size = Path(original).stat().st_size / 1024
            optimized_size = Path(optimized).stat().st_size / 1024
            
            logger.info("   📊 الإحصائيات:")
            logger.info(f"      ⏱ المدة: {original_dur:.1f}s → {optimized_dur:.1f}s")
            
            if saved_seconds > 0:
                logger.info(
                    f"      ✂️ تم توفير: {saved_seconds:.1f}s ({saved_percent:.1f}%)"
                )
            
            logger.info(
                f"      📦 الحجم: {original_size:.1f} KB → {optimized_size:.1f} KB"
            )
            
        except Exception as e:
            logger.debug(f"فشل عرض الإحصائيات: {e}")

    def _get_duration(self, path: str) -> float:
        """الحصول على مدة الصوت."""
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
        except Exception:
            return 0.0


# ════════════════════════════════════════════════════════════════════════
#                    اختبار سريع
# ════════════════════════════════════════════════════════════════════════
if __name__ == "__main__":
    import sys
    
    if len(sys.argv) < 3:
        print("Usage: python audio_optimizer.py <input.mp3> <output.mp3> [speed]")
        sys.exit(1)
    
    input_file = sys.argv[1]
    output_file = sys.argv[2]
    speed = float(sys.argv[3]) if len(sys.argv) > 3 else 1.1
    
    optimizer = AudioOptimizer()
    optimizer.optimize(input_file, output_file, speed=speed)
    
    print(f"✅ تم! الصوت المُحسّن: {output_file}")
