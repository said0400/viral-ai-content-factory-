"""
Prompt Engine - builds Gemini prompts for cinematic Arabic viral scripts
"""


class PromptEngine:

    STYLE_EXAMPLES = [
        "في يوم من الأيام...\nستفهم أن الراحة كانت أكبر عدو لك.",
        "الناس الذين تخاف منهم...\nلا يفكرون فيك أصلاً.",
        "أنت لا تحتاج أحداً.\nأنت تحتاج نفسك فقط.",
        "الألم الذي تشعر به الآن...\nهو ثمن الشخص الذي ستصبحه غداً.",
        "لا أحد سينقذك.\nأنت فقط من يستطيع ذلك.",
    ]

    def build_script_prompt(self, topic: str) -> str:
        examples_str = "\n\n".join(self.STYLE_EXAMPLES)
        return f"""أنت كاتب محتوى عربي محترف متخصص في فيديوهات Viral سينمائية لـ TikTok وYouTube Shorts.

مهمتك: كتابة سكريبت احترافي عن موضوع: "{topic}"

القواعد الإلزامية:
1. اللغة: الفصحى البسيطة - واضحة وقوية
2. الأسلوب: Dark Cinematic Motivation - مظلم عميق واقعي
3. المدة المستهدفة: 50 إلى 58 ثانية
4. عدد الجمل: من 12 إلى 16 جملة قصيرة فقط
5. كل جملة: لا تزيد عن 8 كلمات
6. أول جملة: HOOK صادم يوقف المشاهد فوراً
7. آخر جملة: CTA قوي يدفع للمتابعة
8. استخدم ضمير المخاطب أنت دائماً
9. لا تستخدم أسلوب الوعظ المباشر
10. جمل قابلة للاقتباس ومؤثرة نفسياً

أمثلة الأسلوب المطلوب:
{examples_str}

أجب بصيغة JSON فقط بدون أي نص خارجها:

```json
{{
  "title": "عنوان الفيديو",
  "hook": "الجملة الأولى الصادمة",
  "scenes": [
    {{
      "id": 0,
      "text": "نص المشهد",
      "duration": 3.5,
      "emphasis": [],
      "pause_after": 0.5,
      "type": "hook"
    }},
    {{
      "id": 1,
      "text": "نص المشهد الثاني",
      "duration": 3.0,
      "emphasis": [],
      "pause_after": 0.3,
      "type": "build"
    }}
  ],
  "cta": "نص الـ CTA",
  "full_text": "النص الكامل سطراً بسطر",
  "duration_estimate": 54.0
}}
```

الموضوع: {topic}
اكتب السكريبت الآن:"""

    def build_hook_variants_prompt(self, topic: str, count: int = 5) -> str:
        return f"""أنشئ {count} hooks مختلفة وصادمة لفيديو عن: "{topic}"
كل hook: لا تتجاوز 8 كلمات، صادمة، تثير الفضول الشديد.
أجب بـ JSON array فقط:
["hook 1", "hook 2", "hook 3", "hook 4", "hook 5"]"""
