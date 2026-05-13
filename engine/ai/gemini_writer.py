"""
🤖 Gemini Script Writer (احتياطي)
═══════════════════════════════════════════════════════════════
يولّد سكربتات عربية باستخدام Google Gemini AI

يُستخدم كـ fallback عند فشل Groq.

الميزات:
  ✓ يدعم Gemini 1.5 Flash (سريع ومجاني)
  ✓ يدعم Gemini 1.5 Pro (احتياطي - أقوى)
  ✓ Temperature عشوائية → نصوص فريدة
  ✓ متوافق 100% مع ScriptWriter في الـ interface
═══════════════════════════════════════════════════════════════
"""

import re
import os
import json
import time
import random
import logging
from typing import Optional, List, Dict, Any

from dotenv import load_dotenv

from engine.ai.prompt_engine import PromptEngine

load_dotenv()
logger = logging.getLogger(__name__)

# استيراد آمن لـ Gemini
try:
    import google.generativeai as genai
    _GEMINI_AVAILABLE = True
except ImportError:
    genai = None
    _GEMINI_AVAILABLE = False
    logger.warning("⚠ google-generativeai غير مثبتة. شغّل: pip install google-generativeai")


class GeminiWriter:
    """مولّد سكربتات احتياطي باستخدام Google Gemini."""

    # ─── خريطة الأمزجة (متطابقة مع ScriptWriter) ───────────────────
    MOOD_MAP = {
        "motivation": [
            "الطموح", "النجاح", "القوة", "البطولة", "الانتصار", "الإنجاز",
            "التحفيز", "الإرادة", "الصبر", "المثابرة", "الهدف", "الإصرار",
        ],
        "emotional": [
            "الحزن", "الألم", "الفقد", "الوحدة", "الذكريات", "العذاب",
            "الحب", "العشق", "القلب", "الشوق", "الغرام", "الحنين",
        ],
        "psychological": [
            "الذكاء", "العقل", "التفكير", "العلم", "الفلسفة", "الحكمة",
            "النفس", "الوعي", "الإدراك",
        ],
        "dark": [
            "الموت", "الفناء", "النهاية", "الغياب", "الظلام", "اليأس",
            "الخوف", "القلق",
        ],
        "horror": [
            "الرعب", "الكابوس", "الجريمة", "الشر", "الوحش",
        ],
        "sad": [
            "الكآبة", "الأسى", "الحسرة", "الندم",
        ],
        "sigma": [
            "القوة", "الذئب", "الوحدة", "الانضباط", "الصمت",
            "الخيانة", "الحقيقة", "الغضب", "الظلم", "الكذب",
        ],
    }

    # ─── الموديلات المتاحة (بالترتيب) ──────────────────────────────
    GEMINI_MODELS = [
        "gemini-1.5-flash",      # الأسرع - مجاني
        "gemini-1.5-flash-8b",   # احتياطي 1
        "gemini-1.5-pro",        # احتياطي 2 - الأقوى
    ]

    MAX_RETRIES = 3
    RETRY_DELAY = 2

    # ════════════════════════════════════════════════════════════════
    def __init__(self):
        """تهيئة Gemini client."""
        if not _GEMINI_AVAILABLE:
            raise ImportError(
                "❌ مكتبة google-generativeai غير مثبتة.\n"
                "   ثبّتها بـ: pip install google-generativeai"
            )

        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
            raise ValueError("❌ GEMINI_API_KEY غير موجود في البيئة")

        genai.configure(api_key=api_key)
        self.model_name = self.GEMINI_MODELS[0]
        self.prompt_engine = PromptEngine()
        logger.info(f"✓ Gemini initialized | Model: {self.model_name}")

    # ════════════════════════════════════════════════════════════════
    #                    التوليد الرئيسي
    # ════════════════════════════════════════════════════════════════
    def generate_script(
        self,
        topic: str,
        content_type: str = "motivational",
        target_duration: int = 45,
        mood: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        توليد سكربت كامل عبر Gemini.

        Args:
            topic: موضوع الفيديو
            content_type: نوع المحتوى (motivational/educational/story/quote)
            target_duration: المدة المستهدفة (30/45/60)
            mood: نمط الأسلوب (اختياري - يُكتشف تلقائياً)

        Returns:
            dict يحتوي على السكربت الكامل
        """
        # ── كشف الـ mood تلقائياً ────────────────────────────
        if mood is None:
            mood = self.detect_mood(topic, content_type)

        # ── بناء الـ prompt ──────────────────────────────────
        prompt = self.prompt_engine.build_script_prompt(
            topic=topic,
            mood=mood,
            content_type=content_type,
            target_duration=target_duration,
        )

        # ── توليد السكربت مع retry ──────────────────────────
        script = self._generate_with_retry(prompt, topic, target_duration)

        # ── إضافة معلومات إضافية ────────────────────────────
        script["music_mood"] = mood
        script["content_type"] = content_type
        script["target_duration"] = target_duration
        script["generated_by"] = "gemini"

        return script

    # ════════════════════════════════════════════════════════════════
    #                    التوليد مع Retry
    # ════════════════════════════════════════════════════════════════
    def _generate_with_retry(
        self,
        prompt: str,
        topic: str,
        target_duration: int,
    ) -> Dict[str, Any]:
        """محاولة توليد السكربت مع إعادة المحاولة."""
        last_error = None

        system_instruction = (
            "أنت مولّد JSON صارم لسكربتات الفيديوهات العربية القصيرة. "
            "أعد JSON صالحاً فقط. بدون markdown. بدون شرح. بدون ```."
        )

        for attempt in range(1, self.MAX_RETRIES + 1):
            # temperature عشوائية كل محاولة
            temp = round(random.uniform(0.72, 0.95), 2)

            # تجربة موديلات مختلفة عند الفشل
            model_idx = min(attempt - 1, len(self.GEMINI_MODELS) - 1)
            model_name = self.GEMINI_MODELS[model_idx]

            logger.info(f"🤖 [Gemini محاولة {attempt}/{self.MAX_RETRIES}] {model_name} | temp={temp}")

            try:
                # إعداد الموديل
                model = genai.GenerativeModel(
                    model_name=model_name,
                    system_instruction=system_instruction,
                    generation_config={
                        "temperature": temp,
                        "max_output_tokens": 4000,
                        "response_mime_type": "application/json",
                    },
                )

                # إعدادات السلامة (مفتوحة للمحتوى الفني)
                safety_settings = [
                    {"category": "HARM_CATEGORY_HARASSMENT", "threshold": "BLOCK_ONLY_HIGH"},
                    {"category": "HARM_CATEGORY_HATE_SPEECH", "threshold": "BLOCK_ONLY_HIGH"},
                    {"category": "HARM_CATEGORY_SEXUALLY_EXPLICIT", "threshold": "BLOCK_ONLY_HIGH"},
                    {"category": "HARM_CATEGORY_DANGEROUS_CONTENT", "threshold": "BLOCK_ONLY_HIGH"},
                ]

                response = model.generate_content(
                    prompt,
                    safety_settings=safety_settings,
                )

                if not response.text:
                    raise ValueError("Gemini returned empty response")

                raw = response.text.strip()
                script = self._parse(raw, topic, target_duration)

                if script and self._valid(script):
                    logger.info(f"✓ نجح Gemini | {len(script['scenes'])} مشهد")
                    return script

                logger.warning("⚠ سكربت Gemini غير صالح، إعادة المحاولة...")

            except Exception as e:
                last_error = e
                logger.warning(f"⚠ فشلت محاولة Gemini {attempt}: {e}")
                if attempt < self.MAX_RETRIES:
                    time.sleep(self.RETRY_DELAY * attempt)

        # فشل كل المحاولات → استخدم fallback
        logger.error(f"❌ فشلت كل محاولات Gemini: {last_error}")
        return self._fallback(topic, target_duration)

    # ════════════════════════════════════════════════════════════════
    #                    كشف الـ Mood
    # ════════════════════════════════════════════════════════════════
    def detect_mood(self, topic: str, content_type: str = "motivational") -> str:
        """كشف الـ mood المناسب من الموضوع."""
        normalized = self._norm(topic)

        for mood, keywords in self.MOOD_MAP.items():
            for kw in keywords:
                if self._norm(kw) in normalized:
                    return mood

        return self.prompt_engine.get_mood_for_content(content_type)

    # ════════════════════════════════════════════════════════════════
    #                    Parsing & Validation
    # ════════════════════════════════════════════════════════════════
    def _parse(self, raw: str, topic: str, target_duration: int) -> Optional[Dict[str, Any]]:
        """تحليل JSON من رد Gemini."""
        raw = re.sub(r"```(?:json)?", "", raw).strip()

        # محاولة 1: parsing مباشر
        try:
            data = json.loads(raw)
            if self._valid(data):
                return self._clean(data)
        except json.JSONDecodeError:
            pass

        # محاولة 2: استخراج أول JSON object
        try:
            start = raw.find("{")
            end = raw.rfind("}") + 1
            if start != -1 and end > start:
                data = json.loads(raw[start:end])
                if self._valid(data):
                    return self._clean(data)
        except json.JSONDecodeError:
            pass

        return None

    def _valid(self, d: Dict) -> bool:
        """التحقق من صحة بنية السكربت."""
        required = ("title", "hook", "scenes", "cta", "full_text", "duration_estimate")
        return (
            all(k in d for k in required)
            and isinstance(d.get("scenes"), list)
            and len(d["scenes"]) > 0
        )

    def _clean(self, data: Dict) -> Dict:
        """تنظيف وتطبيع بيانات السكربت."""
        data["title"] = self._norm_text(data.get("title", ""))
        data["hook"] = self._norm_text(data.get("hook", ""))
        data["cta"] = self._norm_text(data.get("cta", ""))
        data["full_text"] = self._norm_text(data.get("full_text", ""))

        # هاشتاجات
        hashtags = data.get("hashtags", [])
        if isinstance(hashtags, list):
            data["hashtags"] = [str(h).strip() for h in hashtags if h]
        else:
            data["hashtags"] = []

        # تنظيف المشاهد
        cleaned_scenes = []
        for i, sc in enumerate(data.get("scenes", [])):
            text = self._norm_text(sc.get("text", ""))
            if not text:
                continue

            cleaned_scenes.append({
                "id":              sc.get("id", i),
                "text":            text,
                "duration":        float(sc.get("duration", 3.0)),
                "pause_after":     float(sc.get("pause_after", 0.3)),
                "type":            sc.get("type", "main"),
                "voice_tone":      sc.get("voice_tone", "intense"),
                "camera_motion":   sc.get("camera_motion", "slow_zoom"),
                "music_intensity": float(sc.get("music_intensity", 0.7)),
                "transition":      sc.get("transition", "smooth_fade"),
                "energy":          float(sc.get("energy", 0.7)),
                "visual_prompt":   sc.get("visual_prompt", ""),
                "emphasis":        sc.get("emphasis") or self._detect_emphasis(text),
            })

        data["scenes"] = cleaned_scenes
        return data

    # ════════════════════════════════════════════════════════════════
    #                    Fallback ذكي
    # ════════════════════════════════════════════════════════════════
    def _fallback(self, topic: str, target_duration: int = 45) -> Dict[str, Any]:
        """سكربت احتياطي عند فشل Gemini."""
        logger.warning("⚠ استخدام Gemini fallback script")

        scene_counts = {30: 6, 45: 8, 60: 10}
        target_scenes = scene_counts.get(target_duration, 8)

        templates = [
            f"هل تعرف الحقيقة عن {topic}؟",
            f"الحقيقة التي يخفونها عن {topic}...",
            "كل شيء يبدأ من لحظة واحدة.",
            "تلك اللحظة التي تقرر فيها أن تتغير.",
            "لا أحد سيأتي لإنقاذك.",
            "أنت وحدك من يصنع مصيرك.",
            f"{topic} ليس مجرد كلمة...",
            "بل هو قرار يغيّر حياتك.",
            "هذا هو الدرس الأهم.",
            "احفظه جيداً... فقد يغيّر كل شيء.",
            "لن أكرر هذه الكلمات.",
            "تابع... فالقادم أعمق.",
        ]

        selected = random.sample(templates, min(target_scenes, len(templates)))

        scenes = []
        for i, text in enumerate(selected):
            scene_type = "hook" if i == 0 else ("cta" if i == len(selected) - 1 else "build")
            scenes.append({
                "id": i,
                "text": text,
                "duration": round(max(2.5, len(text.split()) * 0.5), 1),
                "pause_after": 0.7 if i == 0 else 0.35,
                "type": scene_type,
                "voice_tone": "intense" if i == 0 else "cold",
                "camera_motion": "slow_zoom",
                "music_intensity": 0.8 if i == 0 else 0.6,
                "transition": "smooth_fade",
                "energy": 0.95 if i == 0 else 0.7,
                "visual_prompt": f"cinematic dark dramatic scene about {topic}",
                "emphasis": self._detect_emphasis(text),
            })

        total_dur = min(
            sum(s["duration"] + s["pause_after"] for s in scenes),
            target_duration,
        )

        return {
            "title": topic,
            "hook": selected[0],
            "scenes": scenes,
            "cta": selected[-1],
            "full_text": "\n".join(selected),
            "duration_estimate": round(total_dur, 1),
            "mood": "motivation",
            "hashtags": [],
            "is_fallback": True,
            "generated_by": "gemini_fallback",
        }

    # ════════════════════════════════════════════════════════════════
    #                    دوال مساعدة
    # ════════════════════════════════════════════════════════════════
    @staticmethod
    def _norm(text: str) -> str:
        """تطبيع للمقارنة فقط."""
        for a, b in [("أ", "ا"), ("إ", "ا"), ("آ", "ا"), ("ة", "ه"), ("ى", "ي")]:
            text = text.replace(a, b)
        return text.strip()

    @staticmethod
    def _norm_text(text: str) -> str:
        """تنظيف النص."""
        if not isinstance(text, str):
            return ""
        for ch in ("\u200f", "\u200e", "\ufeff"):
            text = text.replace(ch, "")
        text = re.sub(r"[ـ]+", "", text)
        text = re.sub(r"\s+", " ", text)
        return text.strip()

    @staticmethod
    def _detect_emphasis(text: str) -> List[Dict]:
        """كشف الكلمات المهمة."""
        triggers = {
            "لن", "لا", "أبداً", "دائماً", "أنت", "أنا",
            "النجاح", "الفشل", "الألم", "القوة", "الحقيقة",
            "الآن", "اليوم", "تذكر", "افعل", "توقف",
            "الموت", "الحياة", "الحب", "الخوف", "الأمل",
        }
        result = []
        for i, word in enumerate(text.split()):
            clean = re.sub(r"[^\w\u0600-\u06FF]", "", word)
            if any(t in clean for t in triggers):
                result.append({"word": word, "position": i})
        return result

    # ════════════════════════════════════════════════════════════════
    #                    Batch Generation
    # ════════════════════════════════════════════════════════════════
    def generate_batch(
        self,
        topics: List[str],
        content_type: str = "motivational",
        target_duration: int = 45,
    ) -> List[Dict[str, Any]]:
        """توليد عدة سكربتات دفعة واحدة."""
        results = []
        for i, topic in enumerate(topics, 1):
            logger.info(f"📝 [Gemini {i}/{len(topics)}] {topic}")
            try:
                script = self.generate_script(
                    topic=topic,
                    content_type=content_type,
                    target_duration=target_duration,
                )
                results.append(script)
            except Exception as e:
                logger.error(f"❌ فشل توليد '{topic}': {e}")
                results.append(self._fallback(topic, target_duration))
        return results
