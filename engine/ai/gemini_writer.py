"""
Groq AI Script Writer (Stable + Production Safe)
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
        "epic":         ["الطموح", "النجاح", "القوة", "البطولة", "الانتصار", "التحدي", "الإنجاز"],
        "emotional":    ["الحزن", "الألم", "الفقد", "الوحدة", "الذكريات", "البكاء", "العداب"],
        "motivational": ["التحفيز", "الإرادة", "الصبر", "الاستمرار", "المثابرة", "الهدف", "الإصرار"],
        "calm":         ["الهدوء", "التأمل", "الراحة", "السكينة", "الروح", "الله", "الإيمان"],
        "dramatic":     ["الخيانة", "الحقيقة", "الغضب", "الظلم", "الصدمة", "الخوف", "الكذب"],
        "romantic":     ["الحب", "العشق", "القلب", "الشوق", "الغرام", "الوفاء", "الحنين"],
        "dark":         ["الموت", "الفناء", "النهاية", "الغياب", "الظلام", "اليأس", "الضياع"],
        "intelligence": ["الذكاء", "العقل", "التفكير", "العلم", "المعرفة", "الفلسفة", "الحكمة"],
    }

    def __init__(self):
        api_key = os.getenv("GROQ_API_KEY")
        if not api_key:
            raise ValueError("GROQ_API_KEY not found in .env")
        self.client     = Groq(api_key=api_key)
        self.model_name = "llama-3.3-70b-versatile"
        self.prompt_engine = PromptEngine()

    def detect_mood(self, topic: str) -> str:
        for mood, keywords in self.MOOD_MAP.items():
            if any(kw in topic for kw in keywords):
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
                        "You are a strict JSON generator for video scripts. "
                        "Return ONLY valid complete JSON. No markdown. No truncation."
                    ),
                },
                {"role": "user", "content": prompt},
            ],
            temperature=0.7,
            max_tokens=3500,
            response_format={"type": "json_object"},
        )
        raw_content = response.choices[0].message.content
        script = self._parse_script(raw_content.strip(), topic)
        script["music_mood"] = self.detect_mood(topic)
        print(f"  🎵 Music mood: {script['music_mood']}")
        return script

    def _parse_script(self, raw: str, topic: str) -> dict:
        raw = re.sub(r"```json|```", "", raw).strip()
        try:
            data = json.loads(raw)
            if self._valid(data):
                return data
        except json.JSONDecodeError:
            pass
        try:
            start = raw.find("{")
            end   = raw.rfind("}") + 1
            if start != -1 and end > start:
                data = json.loads(raw[start:end])
                if self._valid(data):
                    return data
        except json.JSONDecodeError:
            pass
        return self._fallback_parse(raw, topic)

    def _fallback_parse(self, raw: str, topic: str) -> dict:
        lines = [ln.strip() for ln in raw.split("\n") if ln.strip() and len(ln.strip()) > 2]
        if not lines:
            lines = [f"الطموح يبدأ من {topic}"]
        scenes = []
        for i, line in enumerate(lines):
            words = len(line.split())
            scenes.append({
                "id":         i,
                "text":       line,
                "duration":   round(max(2.0, words * 0.5), 1),
                "emphasis":   self._detect_emphasis(line),
                "pause_after": 0.5 if i == 0 else 0.3,
                "type":       "hook" if i == 0 else "build",
            })
        total = min(sum(s["duration"] + s["pause_after"] for s in scenes), 58.0)
        return {
            "title":             topic,
            "hook":              lines[0],
            "scenes":            scenes,
            "cta":               lines[-1],
            "full_text":         "\n".join(lines),
            "duration_estimate": round(total, 1),
        }

    def _valid(self, data: dict) -> bool:
        required = ("title", "hook", "scenes", "cta", "full_text", "duration_estimate")
        if not all(k in data for k in required):
            return False
        if not isinstance(data["scenes"], list) or len(data["scenes"]) == 0:
            return False
        return True

    def _detect_emphasis(self, text: str) -> list:
        triggers = ["لن","لا","أبداً","دائماً","أنت","أنا","النجاح","الفشل",
                    "الألم","القوة","الحقيقة","الآن","اليوم","تذكر","افعل","توقف"]
        result = []
        for i, word in enumerate(text.split()):
            clean = re.sub(r"[^\w]", "", word)
            if any(t in clean for t in triggers):
                result.append({"word": word, "position": i})
        return result

    def generate_batch(self, topics: list) -> list:
        results = []
        for topic in topics:
            try:
                results.append(self.generate_script(topic))
            except Exception as e:
                print(f"❌ Error on '{topic}': {e}")
        return results
