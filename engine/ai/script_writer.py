"""
🤖 AI Script Writer
═══════════════════════════════════════════════════════════════
يولّد سكربتات عربية سينمائية باستخدام:
  • Groq LLaMA (أساسي - سريع ومجاني)
  • Gemini    (احتياطي - عند فشل Groq)

الميزات:
  ✓ Temperature عشوائية → نصوص فريدة
  ✓ كشف Mood تلقائي حسب الموضوع
  ✓ دعم 4 أنواع محتوى (motivational, educational, story, quote)
  ✓ مدد ديناميكية (30, 45, 60 ثانية)
  ✓ Retry تلقائي + Fallback ذكي
═══════════════════════════════════════════════════════════════
"""

import re
import os
import json
import time
import random
import logging
from typing import Optional, List, Dict, Any

from groq import Groq
from dotenv import load_dotenv

from engine.ai.prompt_engine import PromptEngine

load_dotenv()
logger = logging.getLogger(__name__)


class ScriptWriter:
    """مولّد سكربتات Shorts عربية احترافية."""

    # ─── خريطة الأمزجة (متوافقة مع PromptEngine) ───────────────────
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

    # ─── الموديلات المتاحة (بالترتيب: الأسرع → الأقوى) ──────────
    GROQ_MODELS = [
        "llama-3.3-70b-versatile",   # الأقوى
        "llama-3.1-70b-versatile",   # احتياطي 1
        "llama-3.1-8b-instant",      # احتياطي 2 (سريع جداً)
    ]

    MAX_RETRIES = 3
    RETRY_DELAY = 2

    # ════════════════════════════════════════════════════════════════
    def __init__(self, provider: str = "groq"):
        """
        Args:
            provider: المزوّد ("groq" حالياً، "gemini" مستقبلاً)
        """
        self.provider = provider
        self.prompt_engine = PromptEngine()

        if provider == "groq":
            self._init_groq()
        else:
            raise ValueError(f"Provider '{provider}' غير مدعوم")

    def _init_groq(self) -> None:
        """تهيئة Groq client."""
        api_key = os.getenv("GROQ_API_KEY")
        if not api_key:
            raise ValueError("❌ GROQ_API_KEY غير موجود في البيئة")

        self.client = Groq(api_key=api_key)
        self.model_name = self.GROQ_MODELS[0]
        logger.info(f"✓ Groq initialized | Model: {self.model_name}")

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
        توليد سكربت كامل.

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
        """محاولة توليد السكربت مع إعادة المحاولة عند الفشل."""
        last_error = None

        for attempt in range(1, self.MAX_RETRIES + 1):
            # temperature عشوائية كل محاولة
            temp = round(random.uniform(0.72, 0.95), 2)

            # تجربة موديلات مختلفة عند الفشل
            model_idx = min(attempt - 1, len(self.GROQ_MODELS) - 1)
            model = self.GROQ_MODELS[model_idx]

            logger.info(f"🤖 [محاولة {attempt}/{self.MAX_RETRIES}] {model} | temp={temp}")

            try:
                response = self.client.chat.completions.create(
                    model=model,
                    messages=[
                        {
                            "role": "system",
                            "content": (
                                "أنت مولّد JSON صارم لسكربتات الفيديوهات العربية القصيرة. "
                                "أعد JSON صالحاً فقط. بدون markdown. بدون شرح."
                            ),
                        },
                        {"role": "user", "content": prompt},
                    ],
                    temperature=temp,
                    max_tokens=4000,
                    response_format={"type": "json_object"},
                )

                raw = response.choices[0].message.content.strip()
                script = self._parse(raw, topic, target_duration)

                if script and self._valid(script):
                    logger.info(f"✓ نجح التوليد | {len(script['scenes'])} مشهد")
                    return script

                logger.warning("⚠ السكربت غير صالح، إعادة المحاولة...")

            except Exception as e:
                last_error = e
                logger.warning(f"⚠ فشلت المحاولة {attempt}: {e}")
                if attempt < self.MAX_RETRIES:
                    time.sleep(self.RETRY_DELAY * attempt)

        # فشل كل المحاولات → استخدم fallback
        logger.error(f"❌ فشلت كل محاولات Groq: {last_error}")
        return self._fallback(topic, target_duration)

    # ════════════════════════════════════════════════════════════════
    #                    كشف الـ Mood
    # ════════════════════════════════════════════════════════════════
    def detect_mood(self, topic: str, content_type: str = "motivational") -> str:
        """كشف الـ mood المناسب من الموضوع ونوع المحتوى."""
        normalized = self._norm(topic)

        # البحث في خريطة الأمزجة
        for mood, keywords in self.MOOD_MAP.items():
            for kw in keywords:
                if self._norm(kw) in normalized:
                    return mood

        # إذا لم يُعثر → استخدم المزاج الافتراضي لنوع المحتوى
        return self.prompt_engine.get_mood_for_content(content_type)

    # ════════════════════════════════════════════════════════════════
    #                    Parsing & Validation
    # ════════════════════════════════════════════════════════════════
    def _parse(self, raw: str, topic: str, target_duration: int) -> Optional[Dict[str, Any]]:
        """تحليل JSON من رد LLM."""
        # إزالة markdown code blocks
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
        # تنظيف النصوص الأساسية
        data["title"] = self._norm_text(data.get("title", ""))
        data["hook"] = self._norm_text(data.get("hook", ""))
        data["cta"] = self._norm_text(data.get("cta", ""))
        data["full_text"] = self._norm_text(data.get("full_text", ""))

        # هاشتاجات (إن وُجدت)
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
                "id":            sc.get("id", i),
                "text":          text,
                "duration":      float(sc.get("duration", 3.0)),
                "pause_after":   float(sc.get("pause_after", 0.3)),
                "type":          sc.get("type", "main"),
                "voice_tone":    sc.get("voice_tone", "intense"),
                "camera_motion": sc.get("camera_motion", "slow_zoom"),
                "music_intensity": float(sc.get("music_intensity", 0.7)),
                "transition":    sc.get("transition", "smooth_fade"),
                "energy":        float(sc.get("energy", 0.7)),
                "visual_prompt": sc.get("visual_prompt", ""),
                "emphasis":      sc.get("emphasis") or self._detect_emphasis(text),
            })

        data["scenes"] = cleaned_scenes
        return data

    # ════════════════════════════════════════════════════════════════
    #                    Fallback ذكي
    # ════════════════════════════════════════════════════════════════
    def _fallback(self, topic: str, target_duration: int = 45) -> Dict[str, Any]:
        """سكربت احتياطي عند فشل API - يتكيف مع الموضوع والمدة."""
        logger.warning("⚠ استخدام fallback script")

        # عدد الجمل حسب المدة
        scene_counts = {30: 6, 45: 8, 60: 10}
        target_scenes = scene_counts.get(target_duration, 8)

        # قوالب متنوعة للجمل
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

        # اختيار عشوائي للتنويع
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

        total_dur = sum(s["duration"] + s["pause_after"] for s in scenes)
        total_dur = min(total_dur, target_duration)

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
        """تنظيف النص من الرموز غير المرئية."""
        if not isinstance(text, str):
            return ""
        for ch in ("\u200f", "\u200e", "\ufeff"):
            text = text.replace(ch, "")
        text = re.sub(r"[ـ]+", "", text)       # إزالة التطويل
        text = re.sub(r"\s+", " ", text)
        return text.strip()

    @staticmethod
    def _detect_emphasis(text: str) -> List[Dict]:
        """كشف الكلمات المهمة للتأكيد البصري/الصوتي."""
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
            logger.info(f"📝 [{i}/{len(topics)}] {topic}")
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
