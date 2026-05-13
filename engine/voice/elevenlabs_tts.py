"""
🎙️ ElevenLabs TTS Engine — احتياطي عالي الجودة
═══════════════════════════════════════════════════════════════
محرك TTS احترافي يستخدم ElevenLabs API:
  ✓ جودة صوت ممتازة (الأفضل عالمياً)
  ✓ يدعم العربية بـ eleven_multilingual_v2
  ✓ تحكم كامل بإعدادات الصوت
  ✓ Retry تلقائي عند الفشل
  ⚠ مدفوع (10K حرف مجاني/شهر)

ضع في: engine/voice/elevenlabs_tts.py
═══════════════════════════════════════════════════════════════
"""

import os
import time
import logging
import subprocess
import requests
from pathlib import Path
from typing import Optional

from dotenv import load_dotenv

load_dotenv()
logger = logging.getLogger(__name__)


class ElevenLabsTTS:
    """محرك ElevenLabs TTS عالي الجودة."""

    BASE_URL = "https://api.elevenlabs.io/v1"

    # موديلات تدعم العربية
    ARABIC_MODELS = [
        "eleven_multilingual_v2",   # الأفضل للعربية
        "eleven_turbo_v2_5",        # سريع + يدعم العربية
        "eleven_flash_v2_5",        # الأسرع
    ]

    # أصوات افتراضية تعمل مع العربية (Voice IDs عامة)
    DEFAULT_ARABIC_VOICES = {
        "male_deep":   "pNInz6obpgDQGcFmaJgB",   # Adam
        "male_strong": "ErXwobaYiN019PkySvjV",   # Antoni
        "female_warm": "EXAVITQu4vr4xnSDxMaL",   # Bella
        "female_calm": "21m00Tcm4TlvDq8ikWAM",   # Rachel
    }

    MAX_RETRIES = 3
    RETRY_DELAY = 2

    # ════════════════════════════════════════════════════════════════
    def __init__(self):
        """تهيئة ElevenLabs."""
        self.api_key = os.getenv("ELEVENLABS_API_KEY")
        if not self.api_key:
            raise ValueError(
                "❌ ELEVENLABS_API_KEY غير موجود في البيئة\n"
                "   احصل عليه من: https://elevenlabs.io/app/settings/api-keys"
            )

        # الصوت الافتراضي
        self.voice_id = (
            os.getenv("ELEVENLABS_VOICE_ID")
            or self.DEFAULT_ARABIC_VOICES["male_deep"]
        )

        # الموديل
        self.model_id = os.getenv(
            "ELEVENLABS_MODEL", "eleven_multilingual_v2"
        )

        # إعدادات الصوت
        self.stability = float(os.getenv("ELEVENLABS_STABILITY", "0.5"))
        self.similarity = float(os.getenv("ELEVENLABS_SIMILARITY", "0.75"))
        self.style = float(os.getenv("ELEVENLABS_STYLE", "0.5"))
        self.use_speaker_boost = (
            os.getenv("ELEVENLABS_SPEAKER_BOOST", "true").lower() == "true"
        )

        self.headers = {
            "xi-api-key": self.api_key,
            "Content-Type": "application/json",
            "Accept": "audio/mpeg",
        }

        self.temp_dir = Path(os.getenv("TEMP_DIR", "./temp"))
        self.temp_dir.mkdir(parents=True, exist_ok=True)

        logger.info(
            f"✓ ElevenLabs initialized | "
            f"Voice: {self.voice_id[:8]}... | Model: {self.model_id}"
        )

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
        text = self._build_full_text(script)

        if not text.strip():
            logger.error("❌ النص فارغ!")
            return self._silence(output_path)

        logger.info(f"🎙️ ElevenLabs | Text: {len(text)} chars")

        # محاولة التوليد مع retry
        audio_data = self._generate_with_retry(text)

        if audio_data and len(audio_data) > 1000:
            with open(output_path, "wb") as f:
                f.write(audio_data)
            logger.info(f"✓ تم توليد الصوت ({len(audio_data) / 1024:.1f} KB)")
            return output_path
        else:
            logger.error("❌ فشل التوليد → صمت احتياطي")
            return self._silence(output_path)

    # ════════════════════════════════════════════════════════════════
    #                    التوليد مع Retry
    # ════════════════════════════════════════════════════════════════
    def _generate_with_retry(self, text: str) -> Optional[bytes]:
        """محاولة التوليد مع إعادة المحاولة."""
        last_error = None

        for attempt in range(1, self.MAX_RETRIES + 1):
            # تجربة موديلات مختلفة عند الفشل
            model_idx = min(attempt - 1, len(self.ARABIC_MODELS) - 1)
            model = self.ARABIC_MODELS[model_idx]

            logger.info(f"🤖 [محاولة {attempt}/{self.MAX_RETRIES}] {model}")

            try:
                audio = self._call_api(text, model)
                if audio and len(audio) > 1000:
                    return audio
            except Exception as e:
                last_error = e
                logger.warning(f"⚠ فشلت المحاولة {attempt}: {e}")
                if attempt < self.MAX_RETRIES:
                    time.sleep(self.RETRY_DELAY * attempt)

        logger.error(f"❌ فشلت كل المحاولات: {last_error}")
        return None

    # ════════════════════════════════════════════════════════════════
    #                    استدعاء الـ API
    # ════════════════════════════════════════════════════════════════
    def _call_api(self, text: str, model: str) -> Optional[bytes]:
        """استدعاء ElevenLabs API."""
        url = f"{self.BASE_URL}/text-to-speech/{self.voice_id}"

        payload = {
            "text": text,
            "model_id": model,
            "voice_settings": {
                "stability":         self.stability,
                "similarity_boost":  self.similarity,
                "style":             self.style,
                "use_speaker_boost": self.use_speaker_boost,
            },
        }

        response = requests.post(
            url,
            json=payload,
            headers=self.headers,
            timeout=120,
        )

        if response.status_code == 200:
            return response.content
        elif response.status_code == 401:
            raise RuntimeError("❌ مفتاح ElevenLabs غير صحيح")
        elif response.status_code == 422:
            raise RuntimeError(f"❌ بيانات غير صالحة: {response.text[:200]}")
        elif response.status_code == 429:
            raise RuntimeError("❌ تجاوزت الحد المسموح (Rate Limit)")
        else:
            raise RuntimeError(
                f"HTTP {response.status_code}: {response.text[:200]}"
            )

    # ════════════════════════════════════════════════════════════════
    #                    بناء النص الكامل
    # ════════════════════════════════════════════════════════════════
    def _build_full_text(self, script: dict) -> str:
        """تجميع النص الكامل من المشاهد مع علامات وقفات."""
        parts = []

        for scene in script.get("scenes", []):
            text = scene.get("text", "").strip()
            pause = float(scene.get("pause_after", 0.3))

            if not text:
                continue

            parts.append(text)

            # ElevenLabs يدعم <break time="1s"/> في النص
            if pause >= 0.8:
                parts.append('<break time="1s"/>')
            elif pause >= 0.5:
                parts.append('<break time="0.6s"/>')
            elif pause >= 0.3:
                parts.append('<break time="0.3s"/>')

        # إضافة CTA
        cta = script.get("cta", "").strip()
        if cta:
            parts.append('<break time="1s"/>')
            parts.append(cta)

        return " ".join(parts).strip()

    # ════════════════════════════════════════════════════════════════
    #                    صمت احتياطي
    # ════════════════════════════════════════════════════════════════
    def _silence(self, output_path: str, duration: int = 30) -> str:
        """توليد ملف صمت كآخر احتياطي."""
        try:
            subprocess.run(
                [
                    "ffmpeg", "-y", "-f", "lavfi",
                    "-i", "anullsrc=r=44100:cl=stereo",
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
    def list_voices(self) -> list:
        """جلب قائمة الأصوات المتاحة في حسابك."""
        try:
            response = requests.get(
                f"{self.BASE_URL}/voices",
                headers={"xi-api-key": self.api_key},
                timeout=30,
            )
            if response.status_code == 200:
                return response.json().get("voices", [])
        except Exception as e:
            logger.error(f"❌ فشل جلب الأصوات: {e}")
        return []

    def get_user_info(self) -> dict:
        """معلومات الحساب (الحد المتبقي، إلخ)."""
        try:
            response = requests.get(
                f"{self.BASE_URL}/user",
                headers={"xi-api-key": self.api_key},
                timeout=30,
            )
            if response.status_code == 200:
                return response.json()
        except Exception as e:
            logger.error(f"❌ فشل جلب معلومات المستخدم: {e}")
        return {}

    def get_remaining_chars(self) -> Optional[int]:
        """الأحرف المتبقية في الاشتراك."""
        info = self.get_user_info()
        try:
            sub = info.get("subscription", {})
            limit = sub.get("character_limit", 0)
            used = sub.get("character_count", 0)
            return limit - used
        except Exception:
            return None

    def generate_for_text(
        self,
        text: str,
        output_path: str,
        voice_id: Optional[str] = None,
    ) -> str:
        """توليد صوت لنص بسيط."""
        if voice_id:
            original_voice = self.voice_id
            self.voice_id = voice_id

        try:
            audio = self._generate_with_retry(text)
            if audio:
                with open(output_path, "wb") as f:
                    f.write(audio)
                return output_path
        finally:
            if voice_id:
                self.voice_id = original_voice

        return self._silence(output_path)


# ════════════════════════════════════════════════════════════════════════
#                    اختبار سريع
# ════════════════════════════════════════════════════════════════════════
if __name__ == "__main__":
    tts = ElevenLabsTTS()
    
    # عرض معلومات الحساب
    remaining = tts.get_remaining_chars()
    if remaining is not None:
        print(f"📊 الأحرف المتبقية: {remaining:,}")
    
    # اختبار
    test_script = {
        "scenes": [
            {"text": "مرحباً بكم في عالم الإبداع.", "pause_after": 0.5},
            {"text": "هنا تبدأ القصة.", "pause_after": 0.8},
        ],
        "cta": "تابعونا للمزيد!",
    }
    output = tts.generate_audio(test_script, "test_elevenlabs.mp3")
    print(f"✓ تم: {output}")
