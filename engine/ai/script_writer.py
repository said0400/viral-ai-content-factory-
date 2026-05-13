"""
AI Script Writer — يستخدم Groq/LLaMA لتوليد السكريبت
يُصلح: اسم الكلاس، GROQ_API_KEY، temperature عشوائية

ضع هذا الملف في: engine/ai/script_writer.py
واحذف: engine/ai/gemini_writer.py
ثم عدّل main.py: من GeminiWriter إلى ScriptWriter
"""

import re
import os
import json
import random

from groq import Groq
from dotenv import load_dotenv

from engine.ai.prompt_engine import PromptEngine

load_dotenv()


class ScriptWriter:
    """
    يولّد سكريبت عربي سينمائي باستخدام Groq LLaMA.
    - temperature عشوائية في كل تشغيل → نصوص مختلفة دائماً
    - يكتشف mood تلقائياً من الموضوع
    """

    MOOD_MAP = {
        "epic":         ["الطموح", "النجاح", "القوة", "البطولة", "الانتصار", "الإنجاز"],
        "emotional":    ["الحزن", "الألم", "الفقد", "الوحدة", "الذكريات", "العذاب"],
        "motivational": ["التحفيز", "الإرادة", "الصبر", "المثابرة", "الهدف", "الإصرار"],
        "calm":         ["الهدوء", "التأمل", "الراحة", "السكينة", "الإيمان", "الروح"],
        "dramatic":     ["الخيانة", "الحقيقة", "الغضب", "الظلم", "الصدمة", "الكذب"],
        "romantic":     ["الحب", "العشق", "القلب", "الشوق", "الغرام", "الحنين"],
        "dark":         ["الموت", "الفناء", "النهاية", "الغياب", "الظلام", "اليأس"],
        "intelligence": ["الذكاء", "العقل", "التفكير", "العلم", "الفلسفة", "الحكمة"],
    }

    def __init__(self):
        api_key = os.getenv("GROQ_API_KEY")
        if not api_key:
            raise ValueError("GROQ_API_KEY غير موجود في .env")

        self.client        = Groq(api_key=api_key)
        self.model_name    = "llama-3.3-70b-versatile"
        self.prompt_engine = PromptEngine()

    # ─── توليد السكريبت ─────────────────────────────────────────────────────

    def generate_script(self, topic: str) -> dict:
        mood   = self.detect_mood(topic)
        prompt = self.prompt_engine.build_script_prompt(topic, mood)

        # temperature عشوائية في كل تشغيل → نصوص مختلفة دائماً
        temp = round(random.uniform(0.72, 0.95), 2)
        print(f"  🤖 LLaMA | mood: {mood} | temp: {temp}")

        try:
            response = self.client.chat.completions.create(
                model=self.model_name,
                messages=[
                    {
                        "role": "system",
                        "content": (
                            "أنت مولّد JSON صارم لسكريبتات الفيديوهات العربية القصيرة. "
                            "أعد JSON صالحاً فقط. بدون markdown. بدون شرح."
                        ),
                    },
                    {"role": "user", "content": prompt},
                ],
                temperature=temp,
                max_tokens=3500,
                response_format={"type": "json_object"},
            )

            raw = response.choices[0].message.content.strip()
            script = self._parse(raw, topic)

        except Exception as e:
            print(f"  ⚠️ Groq API خطأ: {e}")
            script = self._fallback(topic)

        script["music_mood"] = mood
        print(f"  ✓ {len(script['scenes'])} مشهد | ~{script['duration_estimate']:.0f}s | mood: {mood}")
        return script

    # ─── كشف الـ mood ────────────────────────────────────────────────────────

    def detect_mood(self, topic: str) -> str:
        normalized = self._norm(topic)
        for mood, keywords in self.MOOD_MAP.items():
            for kw in keywords:
                if self._norm(kw) in normalized:
                    return mood
        return "motivational"

    # ─── parsing ─────────────────────────────────────────────────────────────

    def _parse(self, raw: str, topic: str) -> dict:
        raw = re.sub(r"```json|```", "", raw).strip()

        # محاولة 1: مباشرة
        try:
            data = json.loads(raw)
            if self._valid(data):
                return self._clean(data)
        except json.JSONDecodeError:
            pass

        # محاولة 2: استخراج أول { }
        try:
            s, e = raw.find("{"), raw.rfind("}") + 1
            if s != -1 and e > s:
                data = json.loads(raw[s:e])
                if self._valid(data):
                    return self._clean(data)
        except json.JSONDecodeError:
            pass

        return self._fallback(topic)

    def _valid(self, d: dict) -> bool:
        return (
            all(k in d for k in ("title", "hook", "scenes", "cta", "full_text", "duration_estimate"))
            and isinstance(d.get("scenes"), list)
            and len(d["scenes"]) > 0
        )

    def _clean(self, data: dict) -> dict:
        data["title"]     = self._norm_text(data.get("title", ""))
        data["hook"]      = self._norm_text(data.get("hook", ""))
        data["cta"]       = self._norm_text(data.get("cta", ""))
        data["full_text"] = self._norm_text(data.get("full_text", ""))

        cleaned = []
        for i, sc in enumerate(data.get("scenes", [])):
            text = self._norm_text(sc.get("text", ""))
            cleaned.append({
                "id":           sc.get("id", i),
                "text":         text,
                "duration":     float(sc.get("duration", 3.0)),
                "emphasis":     self._detect_emphasis(text),
                "pause_after":  float(sc.get("pause_after", 0.3)),
                "type":         sc.get("type", "main"),
                "voice_tone":   sc.get("voice_tone", "intense"),
                "camera_motion":sc.get("camera_motion", "slow_zoom"),
                "visual_prompt":sc.get("visual_prompt", ""),
                "energy":       float(sc.get("energy", 0.7)),
            })
        data["scenes"] = cleaned
        return data

    # ─── fallback ────────────────────────────────────────────────────────────

    def _fallback(self, topic: str) -> dict:
        """يُستخدم فقط عند فشل الـ API — يبني سكريبت بسيط من الموضوع."""
        print("  ⚠️ استخدام fallback script (الـ API فشل)")
        lines = [
            f"هل تعرف حقيقة {topic}؟",
            "الحقيقة التي لا يريدك أحد أن تعرفها...",
            "كل شيء يبدأ من لحظة واحدة.",
            "تلك اللحظة التي تقرر فيها أن تتغير.",
            "لا أحد سيأتي لإنقاذك.",
            "أنت وحدك من يصنع مصيرك.",
            "هذا هو الدرس الأهم في الحياة.",
            "احفظه جيداً.",
        ]
        scenes = [
            {
                "id": i, "text": ln,
                "duration": round(max(2.5, len(ln.split()) * 0.5), 1),
                "emphasis": self._detect_emphasis(ln),
                "pause_after": 0.7 if i == 0 else 0.35,
                "type": "hook" if i == 0 else ("cta" if i == len(lines)-1 else "build"),
                "voice_tone": "intense", "camera_motion": "slow_zoom",
                "visual_prompt": "cinematic dark dramatic arabic",
                "energy": 0.9 if i == 0 else 0.7,
            }
            for i, ln in enumerate(lines)
        ]
        total = min(sum(s["duration"] + s["pause_after"] for s in scenes), 58.0)
        return {
            "title": topic, "hook": lines[0],
            "scenes": scenes, "cta": lines[-1],
            "full_text": "\n".join(lines),
            "duration_estimate": round(total, 1),
        }

    # ─── مساعدات ─────────────────────────────────────────────────────────────

    def _norm(self, text: str) -> str:
        """تطبيع بسيط للمقارنة فقط (لا يُستخدم للعرض)."""
        for a, b in [("أ","ا"),("إ","ا"),("آ","ا"),("ة","ه"),("ى","ي")]:
            text = text.replace(a, b)
        return text.strip()

    def _norm_text(self, text: str) -> str:
        """تنظيف النص من الرموز غير المرئية والمسافات الزائدة."""
        if not isinstance(text, str):
            return ""
        for ch in ("\u200f", "\u200e", "\ufeff"):
            text = text.replace(ch, "")
        text = re.sub(r"[ـ]+", "", text)       # إزالة التطويل
        text = re.sub(r"\s+", " ", text)
        return text.strip()

    def _detect_emphasis(self, text: str) -> list:
        triggers = [
            "لن","لا","أبداً","دائماً","أنت","أنا",
            "النجاح","الفشل","الألم","القوة","الحقيقة",
            "الآن","اليوم","تذكر","افعل","توقف",
        ]
        result = []
        for i, word in enumerate(text.split()):
            clean = re.sub(r"[^\w\u0600-\u06FF]", "", word)
            if any(t in clean for t in triggers):
                result.append({"word": word, "position": i})
        return result

    # للتوافق مع الكود القديم الذي يستدعي GeminiWriter
    generate_batch = lambda self, topics: [self.generate_script(t) for t in topics]


# ─── توافق مع الكود القديم ──────────────────────────────────────────────────
# إذا كان هناك كود يستورد GeminiWriter، هذا يحله بدون تغيير كل الملفات
GeminiWriter = ScriptWriter
