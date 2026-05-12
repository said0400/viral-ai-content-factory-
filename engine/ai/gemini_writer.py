"""
Groq AI Script Writer
Stable + Production Safe
Arabic Optimized
"""

import re
import os
import json

from groq import Groq
from dotenv import load_dotenv

from engine.ai.prompt_engine import PromptEngine

load_dotenv()


class GeminiWriter:

    MOOD_MAP = {
        "epic": [
            "الطموح",
            "النجاح",
            "القوة",
            "البطولة",
            "الانتصار",
            "التحدي",
            "الإنجاز",
        ],

        "emotional": [
            "الحزن",
            "الألم",
            "الفقد",
            "الوحدة",
            "الذكريات",
            "البكاء",
            "العذاب",
        ],

        "motivational": [
            "التحفيز",
            "الإرادة",
            "الصبر",
            "الاستمرار",
            "المثابرة",
            "الهدف",
            "الإصرار",
        ],

        "calm": [
            "الهدوء",
            "التأمل",
            "الراحة",
            "السكينة",
            "الروح",
            "الله",
            "الإيمان",
        ],

        "dramatic": [
            "الخيانة",
            "الحقيقة",
            "الغضب",
            "الظلم",
            "الصدمة",
            "الخوف",
            "الكذب",
        ],

        "romantic": [
            "الحب",
            "العشق",
            "القلب",
            "الشوق",
            "الغرام",
            "الوفاء",
            "الحنين",
        ],

        "dark": [
            "الموت",
            "الفناء",
            "النهاية",
            "الغياب",
            "الظلام",
            "اليأس",
            "الضياع",
        ],

        "intelligence": [
            "الذكاء",
            "العقل",
            "التفكير",
            "العلم",
            "المعرفة",
            "الفلسفة",
            "الحكمة",
        ],
    }

    def __init__(self):

        api_key = os.getenv("GROQ_API_KEY")

        if not api_key:
            raise ValueError("GROQ_API_KEY not found in .env")

        self.client = Groq(api_key=api_key)

        self.model_name = "llama-3.3-70b-versatile"

        self.prompt_engine = PromptEngine()

    def detect_mood(self, topic: str) -> str:

        normalized_topic = self._normalize_arabic(topic)

        for mood, keywords in self.MOOD_MAP.items():

            for kw in keywords:

                if self._normalize_arabic(kw) in normalized_topic:
                    return mood

        return "motivational"

    def generate_script(self, topic: str) -> dict:

        prompt = self.prompt_engine.build_script_prompt(topic)

        response = self.client.chat.completions.create(

            model=self.model_name,

            messages=[

                {
                    "role": "system",

                    "content": (
                        "You are a strict JSON generator for Arabic short-form video scripts. "
                        "Return ONLY valid complete JSON. "
                        "No markdown. "
                        "No explanations. "
                        "No truncation. "
                        "Arabic text must remain natural and clean."
                    ),
                },

                {
                    "role": "user",
                    "content": prompt,
                },
            ],

            temperature=0.7,

            max_tokens=3500,

            response_format={
                "type": "json_object"
            },
        )

        raw_content = response.choices[0].message.content.strip()

        script = self._parse_script(
            raw_content,
            topic
        )

        script["music_mood"] = self.detect_mood(topic)

        print(f"  🎵 Music mood: {script['music_mood']}")

        return script

    def _parse_script(
        self,
        raw: str,
        topic: str
    ) -> dict:

        # تنظيف markdown
        raw = re.sub(
            r"```json|```",
            "",
            raw
        ).strip()

        # المحاولة الأولى
        try:

            data = json.loads(raw)

            if self._valid(data):
                return self._clean_script(data)

        except json.JSONDecodeError:
            pass

        # استخراج JSON من النص
        try:

            start = raw.find("{")

            end = raw.rfind("}") + 1

            if start != -1 and end > start:

                extracted = raw[start:end]

                data = json.loads(extracted)

                if self._valid(data):
                    return self._clean_script(data)

        except json.JSONDecodeError:
            pass

        # fallback
        return self._fallback_parse(
            raw,
            topic
        )

    def _fallback_parse(
        self,
        raw: str,
        topic: str
    ) -> dict:

        lines = [

            ln.strip()

            for ln in raw.split("\n")

            if ln.strip() and len(ln.strip()) > 2
        ]

        if not lines:

            lines = [
                f"الطموح يبدأ من {topic}"
            ]

        scenes = []

        for i, line in enumerate(lines):

            clean_line = self._clean_text(line)

            words = len(clean_line.split())

            scenes.append({

                "id": i,

                "text": clean_line,

                "duration": round(
                    max(2.0, words * 0.5),
                    1
                ),

                "emphasis": self._detect_emphasis(clean_line),

                "pause_after": (
                    0.5 if i == 0 else 0.3
                ),

                "type": (
                    "hook" if i == 0 else "build"
                ),
            })

        total = min(

            sum(
                s["duration"] + s["pause_after"]
                for s in scenes
            ),

            58.0
        )

        return {

            "title": self._clean_text(topic),

            "hook": self._clean_text(lines[0]),

            "scenes": scenes,

            "cta": self._clean_text(lines[-1]),

            "full_text": "\n".join(
                self._clean_text(x)
                for x in lines
            ),

            "duration_estimate": round(total, 1),
        }

    def _valid(self, data: dict) -> bool:

        required = (

            "title",
            "hook",
            "scenes",
            "cta",
            "full_text",
            "duration_estimate",
        )

        if not all(k in data for k in required):
            return False

        if not isinstance(data["scenes"], list):
            return False

        if len(data["scenes"]) == 0:
            return False

        return True

    def _clean_script(self, data: dict) -> dict:

        data["title"] = self._clean_text(
            data.get("title", "")
        )

        data["hook"] = self._clean_text(
            data.get("hook", "")
        )

        data["cta"] = self._clean_text(
            data.get("cta", "")
        )

        data["full_text"] = self._clean_text(
            data.get("full_text", "")
        )

        cleaned_scenes = []

        for i, scene in enumerate(data.get("scenes", [])):

            text = self._clean_text(
                scene.get("text", "")
            )

            cleaned_scenes.append({

                "id": scene.get("id", i),

                "text": text,

                "duration": float(
                    scene.get("duration", 3.0)
                ),

                "emphasis": self._detect_emphasis(text),

                "pause_after": float(
                    scene.get("pause_after", 0.3)
                ),

                "type": scene.get(
                    "type",
                    "main"
                ),
            })

        data["scenes"] = cleaned_scenes

        return data

    def _clean_text(self, text: str) -> str:

        if not isinstance(text, str):
            return ""

        # إزالة الأحرف الغريبة
        text = text.replace("\u200f", "")
        text = text.replace("\u200e", "")
        text = text.replace("\ufeff", "")

        # إزالة المسافات المكررة
        text = re.sub(r"\s+", " ", text)

        return text.strip()

    def _normalize_arabic(self, text: str) -> str:

        text = self._clean_text(text)

        replacements = {

            "أ": "ا",
            "إ": "ا",
            "آ": "ا",

            "ة": "ه",

            "ى": "ي",
        }

        for old, new in replacements.items():
            text = text.replace(old, new)

        return text

    def _detect_emphasis(self, text: str) -> list:

        triggers = [

            "لن",
            "لا",
            "أبداً",
            "دائماً",
            "أنت",
            "أنا",
            "النجاح",
            "الفشل",
            "الألم",
            "القوة",
            "الحقيقة",
            "الآن",
            "اليوم",
            "تذكر",
            "افعل",
            "توقف",
        ]

        result = []

        for i, word in enumerate(text.split()):

            clean = re.sub(
                r"[^\w\u0600-\u06FF]",
                "",
                word
            )

            if any(t in clean for t in triggers):

                result.append({

                    "word": word,

                    "position": i,
                })

        return result

    def generate_batch(
        self,
        topics: list
    ) -> list:

        results = []

        for topic in topics:

            try:

                results.append(
                    self.generate_script(topic)
                )

            except Exception as e:

                print(
                    f"❌ Error on '{topic}': {e}"
                )

        return results
