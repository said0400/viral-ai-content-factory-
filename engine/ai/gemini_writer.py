"""
Groq AI Script Writer
"""

import re
import os
import json
from groq import Groq  # تغيير المكتبة هنا
from dotenv import load_dotenv
from engine.ai.prompt_engine import PromptEngine

load_dotenv()


class GeminiWriter: # حافظنا على اسم الكلاس كما هو لضمان عدم تعطل الاستدعاء في main.py

    def __init__(self):
        # تغيير المتغير ليقرأ من GROQ_API_KEY
        api_key = os.getenv("GROQ_API_KEY")
        if not api_key:
            raise ValueError("GROQ_API_KEY not found in .env")
        
        # تهيئة عميل Groq
        self.client = Groq(api_key=api_key)
        # استخدام موديل Llama 3 القوي والسريع
        self.model_name = "llama-3.3-70b-versatile"
        self.prompt_engine = PromptEngine()

    def generate_script(self, topic: str) -> dict:
        prompt = self.prompt_engine.build_script_prompt(topic)
        
        # استدعاء API الخاص بـ Groq
        response = self.client.chat.completions.create(
            model=self.model_name,
            messages=[
                {"role": "system", "content": "You are a professional video script writer that outputs JSON."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.9,
            max_tokens=2000,
            # تفعيل خاصية JSON Mode لضمان استجابة دقيقة
            response_format={"type": "json_object"}
        )
        
        raw_content = response.choices[0].message.content
        return self._parse_script(raw_content.strip(), topic)

    def _parse_script(self, raw: str, topic: str) -> dict:
        # محاولة 1: JSON block
        m = re.search(r"```json\s*(.*?)\s*```", raw, re.DOTALL)
        if m:
            try:
                data = json.loads(m.group(1))
                if self._valid(data):
                    return data
            except (json.JSONDecodeError, KeyError):
                pass

        # محاولة 2: raw JSON
        try:
            s = raw.find("{")
            e = raw.rfind("}") + 1
            if s != -1 and e > s:
                data = json.loads(raw[s:e])
                if self._valid(data):
                    return data
        except (json.JSONDecodeError, KeyError):
            pass

        # محاولة 3: parse نصي
        lines = [ln.strip() for ln in raw.split("\n")
                 if ln.strip() and len(ln.strip()) > 3]
        scene_types = (
            ["hook"]
            + ["build"] * max(len(lines) - 3, 0)
            + ["peak", "cta"]
        )
        scenes = []
        for i, line in enumerate(lines):
            wc = len(line.split())
            dur = max(1.5, wc * 0.75)
            st = scene_types[i] if i < len(scene_types) else "build"
            scenes.append({
                "id": i,
                "text": line,
                "duration": round(dur, 1),
                "emphasis": self._detect_emphasis(line),
                "pause_after": 0.5 if st == "hook" else 0.3,
                "type": st,
            })

        total = min(sum(s["duration"] + s["pause_after"] for s in scenes), 58.0)
        return {
            "title": topic,
            "hook": lines[0] if lines else "اسمع هذا جيداً...",
            "scenes": scenes,
            "cta": lines[-1] if len(lines) > 1 else "تابعنا لتغيير حياتك.",
            "full_text": "\n".join(lines),
            "duration_estimate": round(total, 1),
        }

    def _valid(self, data: dict) -> bool:
        return all(k in data for k in ("title", "hook", "scenes", "cta", "full_text", "duration_estimate"))

    def _detect_emphasis(self, text: str) -> list:
        triggers = [
            "لن", "لا", "أبداً", "دائماً", "أنت", "أنا",
            "النجاح", "الفشل", "الألم", "القوة", "الحقيقة",
            "الآن", "اليوم", "تذكر", "افعل", "توقف",
        ]
        result = []
        for i, word in enumerate(text.split()):
            clean = re.sub(r"[^\w]", "", word)
            if any(t in clean for t in triggers):
                result.append({"word": word, "position": i})
        return result

    def generate_batch(self, topics: list) -> list:
        scripts = []
        for topic in topics:
            try:
                scripts.append(self.generate_script(topic))
            except Exception as e:
                print(f"Error on '{topic}': {e}")
        return scripts
