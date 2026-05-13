"""
🎙️ Edge TTS Engine — المحرك الأساسي للصوت العربي
═══════════════════════════════════════════════════════════════
يستخدم Microsoft Edge TTS:
  ✓ مجاني 100% (بدون مفتاح API)
  ✓ جودة عالية جداً للعربية
  ✓ سرعة ممتازة
  ✓ بدون حدود على طول النص
  ✓ يدعم لهجات متعددة (سعودي، مصري، خليجي...)

ضع في: engine/voice/edge_tts_engine.py
═══════════════════════════════════════════════════════════════
"""

import os
import asyncio
import logging
import shutil
import subprocess
from pathlib import Path
from typing import Optional

import edge_tts
from dotenv import load_dotenv

load_dotenv()
logger = logging.getLogger(__name__)


# ─── الأصوات العربية المتاحة ────────────────────────────────────────────
ARABIC_VOICES = {
    # 🇸🇦 السعودية
    "ar-SA-HamedNeural":   {"gender": "male",   "lang": "ar-SA", "name": "حامد"},
    "ar-SA-ZariyahNeural": {"gender": "female", "lang": "ar-SA", "name": "زارية"},

    # 🇪🇬 مصر
    "ar-EG-ShakirNeural":  {"gender": "male",   "lang": "ar-EG", "name": "شاكر"},
    "ar-EG-SalmaNeural":   {"gender": "female", "lang": "ar-EG", "name": "سلمى"},

    # 🇦🇪 الإمارات
    "ar-AE-HamdanNeural":  {"gender": "male",   "lang": "ar-AE", "name": "حمدان"},
    "ar-AE-FatimaNeural":  {"gender": "female", "lang": "ar-AE", "name": "فاطمة"},

    # 🇯🇴 الأردن
    "ar-JO-TaimNeural":    {"gender": "male",   "lang": "ar-JO", "name": "تيم"},
    "ar-JO-SanaNeural":    {"gender": "female", "lang": "ar-JO", "name": "سناء"},

    # 🇶🇦 قطر
    "ar-QA-AmalNeural":    {"gender": "female", "lang": "ar-QA", "name": "أمل"},
}

# ─── خريطة المزاج → الصوت ──────────────────────────────────────────────
MOOD_VOICE_MAP = {
    "motivation":    "ar-SA-HamedNeural",     # ذكر قوي
    "dark":          "ar-SA-HamedNeural",     # ذكر عميق
    "sigma":         "ar-SA-HamedNeural",     # ذكر بارد
    "psychological": "ar-SA-HamedNeural",     # ذكر هادئ
    "horror":        "ar-EG-ShakirNeural",    # ذكر متوتر
    "emotional":     "ar-SA-ZariyahNeural",   # أنثى عاطفية
    "sad":           "ar-EG-SalmaNeural",     # أنثى حزينة
    "romantic":      "ar-EG-SalmaNeural",     # أنثى حالمة
}

# ─── خريطة النبرة → معدل السرعة ───────────────────────────────────────
TONE_RATE_MAP = {
    "whisper":      "-15%",
    "calm":         "-10%",
    "cold":         "-5%",
    "emotionless":  "+0%",
    "sad":          "-10%",
    "intense":      "+5%",
    "aggressive":   "+10%",
}


class EdgeTTS:
    """محرك Edge TTS العربي - مجاني وعالي الجودة."""

    def __init__(self, default_voice: Optional[str] = None):
        """
        Args:
            default_voice: الصوت الافتراضي (إن لم يُحدد → يُقرأ من .env)
        """
        self.default_voice = default_voice or os.getenv(
            "TTS_VOICE", "ar-SA-HamedNeural"
        )
        self.default_rate = os.getenv("TTS_RATE", "+0%")
        self.default_pitch = os.getenv("TTS_PITCH", "+0Hz")

        self.temp_dir = Path(os.getenv("TEMP_DIR", "./temp"))
        self.temp_dir.mkdir(parents=True, exist_ok=True)

        # التحقق من صحة الصوت
        if self.default_voice not in ARABIC_VOICES:
            logger.warning(
                f"⚠ الصوت '{self.default_voice}' غير معروف، "
                f"استخدام ar-SA-HamedNeural"
            )
            self.default_voice = "ar-SA-HamedNeural"

        logger.info(f"✓ EdgeTTS initialized | Voice: {self.default_voice}")

    # ════════════════════════════════════════════════════════════════
    #                    الدالة الرئيسية
    # ════════════════════════════════════════════════════════════════
    def generate_audio(self, script: dict, output_path: str) -> str:
        """
        توليد صوت كامل من السكربت.

        Args:
            script: السكربت من ScriptWriter
            output_path: مسار حفظ الملف الصوتي (.mp3)

        Returns:
            مسار الملف الصوتي الناتج
        """
        mood = script.get("music_mood", "motivation")
        voice = self._select_voice(script, mood)

        logger.info(f"🎙️ Edge TTS | Voice: {voice} | Mood: {mood}")

        # بناء النص الكامل من المشاهد
        full_text = self._build_full_text(script)

        if not full_text.strip():
            logger.error("❌ النص فارغ!")
            return self._silence(output_path)

        logger.info(f"📝 طول النص: {len(full_text)} حرف")

        # توليد الصوت
        try:
            asyncio.run(self._generate_async(full_text, voice, output_path))

            if Path(output_path).exists() and Path(output_path).stat().st_size > 1000:
                logger.info(f"✓ تم توليد الصوت: {Path(output_path).name}")
                return output_path
            else:
                raise RuntimeError("الملف الناتج فارغ أو صغير جداً")

        except Exception as e:
            logger.error(f"❌ فشل Edge TTS: {e}")
            # محاولة بصوت بديل
            return self._fallback_voice(full_text, output_path)

    # ════════════════════════════════════════════════════════════════
    #                    التوليد الفعلي (Async)
    # ════════════════════════════════════════════════════════════════
    async def _generate_async(
        self,
        text: str,
        voice: str,
        output_path: str,
        rate: Optional[str] = None,
        pitch: Optional[str] = None,
    ) -> None:
        """التوليد الفعلي عبر edge-tts."""
        rate = rate or self.default_rate
        pitch = pitch or self.default_pitch

        communicate = edge_tts.Communicate(
            text=text,
            voice=voice,
            rate=rate,
            pitch=pitch,
        )
        await communicate.save(output_path)

    # ════════════════════════════════════════════════════════════════
    #                    اختيار الصوت
    # ════════════════════════════════════════════════════════════════
    def _select_voice(self, script: dict, mood: str) -> str:
        """اختيار الصوت المناسب حسب المزاج."""
        # 1. إذا حُدد voice في السكربت
        if "voice" in script and script["voice"] in ARABIC_VOICES:
            return script["voice"]

        # 2. إذا حُدد عبر متغير البيئة
        env_voice = os.getenv("TTS_VOICE")
        if env_voice and env_voice in ARABIC_VOICES:
            return env_voice

        # 3. اختيار حسب المزاج
        return MOOD_VOICE_MAP.get(mood, self.default_voice)

    # ════════════════════════════════════════════════════════════════
    #                    بناء النص الكامل
    # ════════════════════════════════════════════════════════════════
    def _build_full_text(self, script: dict) -> str:
        """تجميع النص الكامل من المشاهد مع فواصل مناسبة."""
        parts = []

        for scene in script.get("scenes", []):
            text = scene.get("text", "").strip()
            pause = float(scene.get("pause_after", 0.3))

            if not text:
                continue

            # إضافة النص
            parts.append(text)

            # إضافة فاصل حسب طول الوقفة
            if pause >= 0.8:
                parts.append("... ")  # وقفة طويلة
            elif pause >= 0.5:
                parts.append(".. ")   # وقفة متوسطة
            elif pause >= 0.3:
                parts.append(", ")    # وقفة قصيرة
            else:
                parts.append(" ")

        # إضافة CTA
        cta = script.get("cta", "").strip()
        if cta:
            parts.append("... ")
            parts.append(cta)

        return " ".join(parts).strip()

    # ════════════════════════════════════════════════════════════════
    #                    Fallback Voices
    # ════════════════════════════════════════════════════════════════
    def _fallback_voice(self, text: str, output_path: str) -> str:
        """جرب أصوات بديلة عند فشل الصوت الأساسي."""
        fallback_voices = [
            "ar-SA-HamedNeural",
            "ar-EG-ShakirNeural",
            "ar-SA-ZariyahNeural",
        ]

        for voice in fallback_voices:
            if voice == self.default_voice:
                continue

            logger.warning(f"⏳ محاولة بصوت بديل: {voice}")
            try:
                asyncio.run(self._generate_async(text, voice, output_path))
                if Path(output_path).exists() and Path(output_path).stat().st_size > 1000:
                    logger.info(f"✓ نجح الصوت البديل: {voice}")
                    return output_path
            except Exception as e:
                logger.warning(f"⚠ فشل الصوت البديل {voice}: {e}")

        logger.error("❌ فشلت كل الأصوات → صمت")
        return self._silence(output_path)

    # ════════════════════════════════════════════════════════════════
    #                    صمت احتياطي
    # ════════════════════════════════════════════════════════════════
    def _silence(self, output_path: str, duration: int = 30) -> str:
        """توليد ملف صمت كآخر احتياطي."""
        try:
            subprocess.run(
                [
                    "ffmpeg", "-y", "-f", "lavfi",
                    "-i", f"anullsrc=r=44100:cl=stereo",
                    "-t", str(duration),
                    "-c:a", "libmp3lame", "-b:a", "128k",
                    output_path,
                ],
                capture_output=True,
                check=True,
            )
        except Exception as e:
            logger.error(f"❌ فشل توليد الصمت: {e}")
        return output_path

    # ════════════════════════════════════════════════════════════════
    #                    دوال مساعدة
    # ════════════════════════════════════════════════════════════════
    @staticmethod
    def list_voices() -> dict:
        """قائمة الأصوات العربية المتاحة."""
        return ARABIC_VOICES

    @staticmethod
    def get_voice_info(voice_name: str) -> Optional[dict]:
        """معلومات صوت معين."""
        return ARABIC_VOICES.get(voice_name)

    def generate_for_text(
        self,
        text: str,
        output_path: str,
        voice: Optional[str] = None,
        rate: Optional[str] = None,
        pitch: Optional[str] = None,
    ) -> str:
        """
        توليد صوت لنص بسيط (بدون سكربت كامل).

        مفيد للاختبار أو للنصوص القصيرة.
        """
        voice = voice or self.default_voice
        try:
            asyncio.run(self._generate_async(text, voice, output_path, rate, pitch))
            return output_path
        except Exception as e:
            logger.error(f"❌ فشل التوليد: {e}")
            return self._silence(output_path)


# ════════════════════════════════════════════════════════════════════════
#                    اختبار سريع
# ════════════════════════════════════════════════════════════════════════
if __name__ == "__main__":
    import json

    tts = EdgeTTS()
    test_script = {
        "scenes": [
            {"text": "مرحباً بكم في عالم الإبداع.", "pause_after": 0.5},
            {"text": "هنا تبدأ القصة.", "pause_after": 0.8},
        ],
        "cta": "تابعونا للمزيد!",
        "music_mood": "motivation",
    }
    output = tts.generate_audio(test_script, "test_output.mp3")
    print(f"✓ تم: {output}")
