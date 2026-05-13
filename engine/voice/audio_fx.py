"""
🎚️ Audio FX Engine — معالجة ومزج الصوت السينمائي
═══════════════════════════════════════════════════════════════
محرك معالجة صوتي احترافي يوفر:
  ✓ Voice Processing سينمائي (EQ, Compressor, Echo, Bass, Loudnorm)
  ✓ Music Processing مع fade in/out ذكي
  ✓ Audio Mixing متعدد المسارات (Voice + Music + SFX)
  ✓ Loudness Normalization (-14 LUFS - معيار YouTube/TikTok)
  ✓ Fallback ذكي + Logging كامل

ضع في: engine/voice/audio_fx.py
═══════════════════════════════════════════════════════════════
"""

import os
import json
import shutil
import logging
import subprocess
from pathlib import Path
from typing import Optional, List, Tuple

logger = logging.getLogger(__name__)


class AudioFX:
    """محرك معالجة الصوت السينمائي."""

    # ─── إعدادات افتراضية ─────────────────────────────────────────
    DEFAULT_SAMPLE_RATE = 44100
    DEFAULT_CHANNELS = 2
    DEFAULT_BITRATE = "192k"
    DEFAULT_TIMEOUT = 120  # ثانية

    # ─── معايير Loudness للمنصات ──────────────────────────────────
    LOUDNESS_PRESETS = {
        "youtube":  {"I": -14, "TP": -1.0, "LRA": 7},
        "tiktok":   {"I": -14, "TP": -1.0, "LRA": 7},
        "instagram":{"I": -14, "TP": -1.0, "LRA": 7},
        "spotify":  {"I": -14, "TP": -1.0, "LRA": 7},
        "podcast":  {"I": -16, "TP": -1.5, "LRA": 11},
    }

    # ════════════════════════════════════════════════════════════════
    def __init__(self):
        """تهيئة محرك معالجة الصوت."""
        self.temp_dir = Path(os.getenv("TEMP_DIR", "./temp"))
        self.temp_dir.mkdir(parents=True, exist_ok=True)

        # إعدادات قابلة للتخصيص
        self.loudness_preset = os.getenv("LOUDNESS_PRESET", "youtube")
        self.voice_volume = float(os.getenv("VOICE_VOLUME", "1.0"))
        self.music_volume = float(os.getenv("MUSIC_VOLUME", "0.15"))
        self.echo_enabled = os.getenv("VOICE_ECHO_ENABLED", "true").lower() == "true"

        logger.info(
            f"🎚️ AudioFX | Loudness: {self.loudness_preset} | "
            f"Voice: {self.voice_volume} | Music: {self.music_volume}"
        )

    # ════════════════════════════════════════════════════════════════
    #                    معالجة الصوت
    # ════════════════════════════════════════════════════════════════
    def process_voice(self, voice_path: str, output_path: str) -> str:
        """
        معالجة صوتية احترافية للصوت البشري.

        تطبيق:
          • EQ (تعزيز عذوبة الصوت)
          • Compression (إيقاع متوازن)
          • Echo خفيف (عمق سينمائي)
          • Bass Boost (دفء)
          • Loudness Normalization (-14 LUFS)
        """
        if not self._validate_input(voice_path):
            return self._safe_copy(voice_path, output_path)

        # بناء filter chain
        filters = self._build_voice_filters()

        if self._run_ffmpeg(
            ["-i", voice_path, "-af", filters],
            output_path,
            description="Voice processing",
        ):
            logger.info(f"✓ تمت معالجة الصوت")
            return output_path

        # Fallback 1: loudnorm فقط
        logger.warning("⚠ فشل المعالجة الكاملة، محاولة loudnorm فقط...")
        if self._run_ffmpeg(
            ["-i", voice_path, "-af", "loudnorm=I=-14:TP=-1:LRA=7"],
            output_path,
            description="Voice loudnorm only",
        ):
            return output_path

        # Fallback 2: نسخ مع تحويل بسيط
        logger.warning("⚠ فشل loudnorm، نسخ بسيط")
        return self._safe_copy(voice_path, output_path)

    def _build_voice_filters(self) -> str:
        """بناء سلسلة filters للصوت البشري."""
        preset = self.LOUDNESS_PRESETS.get(self.loudness_preset, self.LOUDNESS_PRESETS["youtube"])

        filters = [
            # EQ: تعزيز الوسط (الوضوح) وتقليل الحدة
            "equalizer=f=200:width_type=o:width=2:g=3",
            "equalizer=f=3000:width_type=o:width=2:g=1",
            "equalizer=f=8000:width_type=o:width=2:g=-1",

            # Compressor: ضبط الإيقاع
            "compand=attacks=0.02:decays=0.15:"
            "points=-90/-90|-60/-30|-30/-15|-10/-8|0/-6:gain=4:volume=-90:delay=0.05",
        ]

        # Echo اختياري (خفيف)
        if self.echo_enabled:
            filters.append("aecho=0.6:0.5:35|45:0.18|0.10")

        # Bass Boost
        filters.append("bass=g=3:f=80:width_type=o:width=0.8")

        # Loudness Normalization
        filters.append(
            f"loudnorm=I={preset['I']}:TP={preset['TP']}:LRA={preset['LRA']}"
        )

        return ",".join(filters)

    # ════════════════════════════════════════════════════════════════
    #                    معالجة الموسيقى
    # ════════════════════════════════════════════════════════════════
    def process_music(
        self,
        music_path: str,
        output_path: str,
        volume: float = 0.20,
        fade_in: float = 2.0,
        fade_out: float = 3.0,
    ) -> str:
        """
        معالجة الموسيقى الخلفية مع fade in/out ذكي.

        Args:
            music_path: مسار الموسيقى
            output_path: مسار الإخراج
            volume: مستوى الصوت (0.0 - 1.0)
            fade_in: مدة الـ fade in بالثواني
            fade_out: مدة الـ fade out بالثواني
        """
        if not self._validate_input(music_path):
            return self._safe_copy(music_path, output_path)

        # احصل على مدة الموسيقى أولاً لحساب fade_out بدقة
        duration = self.get_audio_duration(music_path)

        if duration <= 0:
            return self._safe_copy(music_path, output_path)

        # حساب وقت بداية الـ fade out
        fade_out_start = max(duration - fade_out, 0.1)

        filters = (
            f"volume={volume},"
            f"afade=t=in:st=0:d={fade_in},"
            f"afade=t=out:st={fade_out_start:.2f}:d={fade_out}"
        )

        if self._run_ffmpeg(
            ["-i", music_path, "-af", filters],
            output_path,
            description="Music processing",
        ):
            logger.info(f"✓ تمت معالجة الموسيقى (volume={volume})")
            return output_path

        return self._safe_copy(music_path, output_path)

    # ════════════════════════════════════════════════════════════════
    #                    مزج الصوت متعدد المسارات
    # ════════════════════════════════════════════════════════════════
    def mix_audio_tracks(
        self,
        voice_path: str,
        music_path: str,
        sfx_tracks: List[Tuple[str, float, float]],
        output_path: str,
        total_duration: float,
        music_volume: Optional[float] = None,
    ) -> str:
        """
        مزج الصوت + الموسيقى + المؤثرات الصوتية.

        Args:
            voice_path: مسار الصوت
            music_path: مسار الموسيقى
            sfx_tracks: قائمة من (path, start_seconds, volume)
            output_path: مسار الإخراج
            total_duration: المدة الكاملة بالثواني
            music_volume: مستوى الموسيقى (يستخدم الافتراضي إن لم يحدد)
        """
        # التحقق من المدخلات
        if not self._validate_input(voice_path):
            logger.error("❌ ملف الصوت غير موجود")
            return self._safe_copy(voice_path, output_path)

        if not self._validate_input(music_path):
            logger.warning("⚠ ملف الموسيقى غير موجود، نسخ الصوت فقط")
            return self._safe_copy(voice_path, output_path)

        music_vol = music_volume if music_volume is not None else self.music_volume
        safe_dur = max(float(total_duration), 1.0)
        fade_start = max(safe_dur - 3.0, 0.1)

        # تصفية SFX الموجودة فعلياً
        valid_sfx = [
            (path, start, vol)
            for path, start, vol in sfx_tracks
            if Path(path).exists() and start < safe_dur
        ]

        # بناء inputs
        inputs = ["-i", voice_path, "-i", music_path]
        for sfx_path, _, _ in valid_sfx:
            inputs += ["-i", sfx_path]

        # بناء filter chain
        filter_parts = []

        # 1. Voice
        filter_parts.append(f"[0:a]volume={self.voice_volume}[voice]")

        # 2. Music (مع loop وfade)
        filter_parts.append(
            f"[1:a]aloop=loop=-1:size=2147483647,"
            f"atrim=duration={safe_dur:.2f},"
            f"volume={music_vol},"
            f"afade=t=in:st=0:d=2,"
            f"afade=t=out:st={fade_start:.2f}:d=3[music]"
        )

        # 3. SFX
        sfx_labels = []
        for i, (_, start_t, vol) in enumerate(valid_sfx):
            delay_ms = int(start_t * 1000)
            label = f"sfx{i}"
            filter_parts.append(
                f"[{i + 2}:a]adelay={delay_ms}|{delay_ms},"
                f"volume={vol}[{label}]"
            )
            sfx_labels.append(f"[{label}]")

        # 4. Final mix
        all_inputs = "[voice][music]" + "".join(sfx_labels)
        total_inputs = 2 + len(valid_sfx)
        filter_parts.append(
            f"{all_inputs}amix=inputs={total_inputs}:"
            f"duration=first:normalize=0[out]"
        )

        cmd_args = (
            inputs
            + [
                "-filter_complex", ";".join(filter_parts),
                "-map", "[out]",
            ]
        )

        if self._run_ffmpeg(
            cmd_args,
            output_path,
            description=f"Audio mix (voice + music + {len(valid_sfx)} SFX)",
        ):
            logger.info(f"✓ تم المزج الكامل")
            return output_path

        # Fallback 1: voice + music فقط (بدون SFX)
        logger.warning("⚠ فشل المزج الكامل، محاولة voice + music فقط...")
        if self._mix_voice_music_only(voice_path, music_path, output_path, safe_dur, music_vol):
            return output_path

        # Fallback 2: نسخ الصوت فقط
        logger.warning("⚠ فشل المزج، نسخ الصوت فقط")
        return self._safe_copy(voice_path, output_path)

    def _mix_voice_music_only(
        self,
        voice_path: str,
        music_path: str,
        output_path: str,
        duration: float,
        music_volume: float,
    ) -> bool:
        """مزج الصوت والموسيقى فقط (fallback)."""
        filters = (
            f"[1:a]aloop=loop=-1:size=2147483647,"
            f"atrim=duration={duration:.2f},"
            f"volume={music_volume}[m];"
            f"[0:a][m]amix=inputs=2:duration=first:normalize=0[out]"
        )

        return self._run_ffmpeg(
            [
                "-i", voice_path,
                "-i", music_path,
                "-filter_complex", filters,
                "-map", "[out]",
            ],
            output_path,
            description="Voice + Music mix",
        )

    # ════════════════════════════════════════════════════════════════
    #                    الحصول على مدة الصوت
    # ════════════════════════════════════════════════════════════════
    def get_audio_duration(self, path: str) -> float:
        """الحصول على مدة الملف الصوتي بالثواني."""
        if not Path(path).exists():
            logger.error(f"❌ الملف غير موجود: {path}")
            return 0.0

        try:
            result = subprocess.run(
                [
                    "ffprobe", "-v", "quiet",
                    "-print_format", "json",
                    "-show_format",
                    path,
                ],
                capture_output=True,
                text=True,
                timeout=30,
                check=True,
            )
            data = json.loads(result.stdout)
            return float(data["format"]["duration"])
        except (subprocess.SubprocessError, json.JSONDecodeError, KeyError) as e:
            logger.error(f"❌ فشل قراءة المدة: {e}")
            return 0.0

    # ════════════════════════════════════════════════════════════════
    #                    صمت
    # ════════════════════════════════════════════════════════════════
    def add_silence(self, duration: float, output_path: str) -> str:
        """توليد ملف صمت بمدة محددة."""
        if self._run_ffmpeg(
            [
                "-f", "lavfi",
                "-i", "anullsrc=r=44100:cl=stereo",
                "-t", str(duration),
            ],
            output_path,
            description=f"Silence ({duration}s)",
        ):
            return output_path
        return output_path

    # ════════════════════════════════════════════════════════════════
    #                    دوال إضافية
    # ════════════════════════════════════════════════════════════════
    def change_speed(
        self,
        input_path: str,
        output_path: str,
        speed: float = 1.0,
    ) -> str:
        """
        تغيير سرعة الصوت بدون تغيير النبرة.

        Args:
            speed: 0.5 = نصف السرعة، 2.0 = ضعف السرعة
        """
        # atempo يقبل بين 0.5 و 2.0 فقط
        if 0.5 <= speed <= 2.0:
            filters = f"atempo={speed}"
        elif speed < 0.5:
            filters = f"atempo=0.5,atempo={speed/0.5}"
        else:
            filters = f"atempo=2.0,atempo={speed/2.0}"

        if self._run_ffmpeg(
            ["-i", input_path, "-af", filters],
            output_path,
            description=f"Speed change to {speed}x",
        ):
            return output_path
        return self._safe_copy(input_path, output_path)

    def normalize(
        self,
        input_path: str,
        output_path: str,
        preset: Optional[str] = None,
    ) -> str:
        """تطبيق Loudness Normalization فقط."""
        preset_name = preset or self.loudness_preset
        cfg = self.LOUDNESS_PRESETS.get(preset_name, self.LOUDNESS_PRESETS["youtube"])

        filters = f"loudnorm=I={cfg['I']}:TP={cfg['TP']}:LRA={cfg['LRA']}"

        if self._run_ffmpeg(
            ["-i", input_path, "-af", filters],
            output_path,
            description=f"Normalize ({preset_name})",
        ):
            return output_path
        return self._safe_copy(input_path, output_path)

    def trim_audio(
        self,
        input_path: str,
        output_path: str,
        start: float = 0,
        duration: Optional[float] = None,
    ) -> str:
        """قص جزء من الصوت."""
        args = ["-ss", str(start), "-i", input_path]
        if duration:
            args += ["-t", str(duration)]
        args += ["-c", "copy"]

        if self._run_ffmpeg_raw(args, output_path, description="Trim audio"):
            return output_path
        return self._safe_copy(input_path, output_path)

    # ════════════════════════════════════════════════════════════════
    #                    دوال مساعدة داخلية
    # ════════════════════════════════════════════════════════════════
    def _validate_input(self, path: str) -> bool:
        """التحقق من وجود الملف."""
        if not Path(path).exists():
            logger.error(f"❌ الملف غير موجود: {path}")
            return False
        if Path(path).stat().st_size < 100:
            logger.error(f"❌ الملف فارغ أو تالف: {path}")
            return False
        return True

    def _run_ffmpeg(
        self,
        args: List[str],
        output_path: str,
        description: str = "FFmpeg",
        sample_rate: Optional[int] = None,
        channels: Optional[int] = None,
        bitrate: Optional[str] = None,
    ) -> bool:
        """تشغيل FFmpeg مع إعدادات صوتية موحدة."""
        sr = sample_rate or self.DEFAULT_SAMPLE_RATE
        ch = channels or self.DEFAULT_CHANNELS
        br = bitrate or self.DEFAULT_BITRATE

        cmd = (
            ["ffmpeg", "-y", "-loglevel", "error"]
            + args
            + [
                "-ar", str(sr),
                "-ac", str(ch),
                "-b:a", br,
                output_path,
            ]
        )

        return self._execute(cmd, description)

    def _run_ffmpeg_raw(
        self,
        args: List[str],
        output_path: str,
        description: str = "FFmpeg",
    ) -> bool:
        """تشغيل FFmpeg بدون إعدادات صوتية إضافية."""
        cmd = ["ffmpeg", "-y", "-loglevel", "error"] + args + [output_path]
        return self._execute(cmd, description)

    def _execute(self, cmd: List[str], description: str) -> bool:
        """تنفيذ أمر FFmpeg مع معالجة الأخطاء."""
        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                timeout=self.DEFAULT_TIMEOUT,
            )
            if result.returncode == 0:
                return True
            else:
                err = result.stderr.decode("utf-8", errors="ignore")[:300]
                logger.warning(f"⚠ {description} failed: {err}")
                return False
        except subprocess.TimeoutExpired:
            logger.error(f"❌ {description} timeout")
            return False
        except Exception as e:
            logger.error(f"❌ {description} error: {e}")
            return False

    def _safe_copy(self, src: str, dst: str) -> str:
        """نسخ آمن مع التحقق من وجود الملف."""
        try:
            if Path(src).exists():
                shutil.copy(src, dst)
        except Exception as e:
            logger.error(f"❌ فشل النسخ: {e}")
        return dst


# ════════════════════════════════════════════════════════════════════════
#                    اختبار سريع
# ════════════════════════════════════════════════════════════════════════
if __name__ == "__main__":
    import sys

    if len(sys.argv) < 3:
        print("Usage: python audio_fx.py <input.mp3> <output.mp3>")
        sys.exit(1)

    fx = AudioFX()
    duration = fx.get_audio_duration(sys.argv[1])
    print(f"📊 Duration: {duration:.2f}s")

    result = fx.process_voice(sys.argv[1], sys.argv[2])
    print(f"✓ Processed: {result}")
