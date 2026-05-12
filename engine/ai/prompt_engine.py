"""
Ultimate Cinematic Prompt Engine
Advanced Arabic Viral Shorts Prompt System
"""

import random
from typing import Literal


class PromptEngine:

    STYLE_EXAMPLES = [
        "في يوم من الأيام... ستفهم أن الراحة قتلتك ببطء.",
        "اسمعني جيداً!... لا أحد سيأتي لإنقاذك.",
        "الأشخاص الذين تجاهلوك... صنعوك أقوى.",
        "كل خوف تهرب منه... يكبر داخلك.",
        "الصمت الذي تعيشه الآن... سيبتلعك لاحقاً.",
        "أنت لا تحتاج الحظ... أنت تحتاج الحرب.",
        "في النهاية... الجميع يختفون.",
        "أنت تتألم الآن... وهذا ممتاز.",
        "لا تثق كثيراً... حتى بظلك.",
        "هذه ليست نهاية القصة... بل بدايتها.",
        "الفرق بينك وبينهم... أنك لم تستسلم.",
        "لا يهم كم سقطت... بل كم مرة قمت.",
        "أكثر الناس نجاحاً... عاشوا أصعب اللحظات.",
        "الألم الذي تشعر به الآن... هو ثمن النجاح غداً.",
        "لا أحد يعرف ما الذي تحمله... لكنك تعرف.",
        "الوقت لا يرحم... فلا تضيعه.",
        "كن صامتاً... ودع نجاحك يتكلم.",
        "الخوف شعور... والشجاعة قرار.",
        "أنت أقوى مما تظن... بكثير.",
        "العالم لا يتوقف لأحد... فتحرك."
    ]

    MOOD_RULES = {
        "dark":          "أسلوب مظلم وعميق وبارد عاطفياً.",
        "emotional":     "أسلوب عاطفي مؤثر نفسياً وإنسانياً.",
        "horror":        "أسلوب مرعب متوتر مليء بالغموض.",
        "motivation":    "أسلوب تحفيزي شرس وصادم.",
        "psychological": "أسلوب نفسي يضرب المخاوف الداخلية.",
        "sad":           "أسلوب حزين وتأملي عميق.",
        "sigma":         "أسلوب قوي وبارد وواثق.",
    }

    def build_script_prompt(
        self,
        topic: str,
        mood: Literal[
            "dark", "emotional", "horror",
            "motivation", "psychological", "sad", "sigma"
        ] = "dark"
    ) -> str:

        mood_instruction = self.MOOD_RULES.get(mood, self.MOOD_RULES["dark"])

        # اختر 5 أمثلة عشوائية كل مرة لضمان تنويع السيناريو
        examples = random.sample(self.STYLE_EXAMPLES, min(5, len(self.STYLE_EXAMPLES)))
        examples_str = "\n\n".join(examples)

        # رقم عشوائي لإجبار الـ LLM على توليد محتوى مختلف
        seed = random.randint(1000, 9999)

        return f"""
أنت مخرج سينمائي عالمي وكاتب Viral Arabic Shorts محترف.

[seed: {seed}]

مهمتك:
تحويل الموضوع التالي إلى فيديو عربي قصير شديد التأثير مناسب لـ:
TikTok / Reels / YouTube Shorts

الموضوع:
"{topic}"

نوع الأسلوب المطلوب:
{mood_instruction}

===================================
القواعد السينمائية الإلزامية
===================================

1. اللغة:
- العربية الفصحى البسيطة
- قوية ومؤثرة
- سهلة النطق صوتياً
- بإيقاع طبيعي بشري

2. مدة الفيديو:
- بين 50 و 58 ثانية

3. عدد المشاهد:
- من 12 إلى 16 مشهد

4. طول الجملة:
- من 3 إلى 9 كلمات فقط

5. الأداء الصوتي:
- استخدم "..." للتنفس والتوتر
- استخدم "!" للصدمة والانفعال
- اجعل الإيقاع سينمائياً وطبيعياً
- تجنب الجمل الصعبة على النطق

6. الهيكل:
- Hook قوي جداً بالبداية
- تصعيد تدريجي للتوتر
- نهاية تضرب المشاهد نفسياً
- CTA قصير وقوي

7. ممنوع:
- الوعظ المباشر
- الحشو
- الجمل الطويلة
- الأسلوب الروبوتي
- التكرار الممل
- تكرار نفس الأمثلة أدناه حرفياً

8. المطلوب:
- جمل قابلة للاقتباس
- تأثير نفسي قوي
- Retention عالي
- أسلوب Viral حديث
- تنوع في الإيقاع العاطفي
- محتوى مختلف تماماً عن أي فيديو سابق

===================================
أمثلة للأسلوب (لا تكررها حرفياً)
===================================

{examples_str}

===================================
تعليمات المشاهد
===================================

لكل مشهد أضف:

- visual_prompt: وصف سينمائي بالإنجليزية لمحركات توليد الفيديو
- camera_motion: slow_zoom / fast_push / handheld / cinematic_pan / drone_shot
- music_intensity: رقم بين 0 و 1
- voice_tone: whisper / cold / aggressive / sad / emotionless / intense
- transition: glitch_fade / fast_cut / blur_transition / cinematic_flash
- energy: رقم بين 0 و 1

===================================
مهم جداً
===================================

- لا تكتب أي شرح خارج JSON
- لا تستخدم markdown
- لا تستخدم ```json
- أرجع JSON صالح فقط
- كل مشهد يجب أن يكون مختلفاً
- اجعل النص مناسباً للأداء الصوتي البشري
- اجعل المحتوى مختلفاً وفريداً في كل مرة

===================================
صيغة JSON المطلوبة
===================================

{{
  "title": "عنوان قوي للفيديو",
  "hook": "أول جملة صادمة توقف المشاهد...",
  "mood": "{mood}",
  "duration_estimate": 55.0,
  "voice_style": "deep cinematic arabic male",
  "music_style": "dark ambient cinematic",
  "color_style": "dark contrast cinematic",
  "subtitle_style": "big bold cinematic subtitles",
  "cta": "تابع... فالقادم أخطر!",
  "full_text": "النص الكامل هنا",
  "scenes": [
    {{
      "id": 0,
      "type": "hook",
      "text": "النص السينمائي هنا...",
      "duration": 4.0,
      "pause_after": 0.8,
      "voice_tone": "intense",
      "camera_motion": "slow_zoom",
      "music_intensity": 0.9,
      "transition": "glitch_fade",
      "energy": 0.95,
      "visual_prompt": "dark cinematic arab man standing in rain dramatic lighting",
      "emphasis": [
        {{
          "word": "الخوف",
          "position": 2
        }}
      ]
    }}
  ]
}}

اكتب السكريبت الآن. تأكد أن المحتوى مختلف تماماً وفريد.
"""

    def build_hook_variants_prompt(self, topic: str, count: int = 5, mood: str = "dark") -> str:
        return f"""
أنشئ {count} Hooks عربية Viral شديدة القوة.

الموضوع: "{topic}"
الأسلوب: {mood}

القواعد:
- أقل من 8 كلمات
- صادمة جداً
- تثير الفضول فوراً
- قابلة للانتشار
- استخدم "..." و "!" بذكاء
- مناسبة لفيديوهات TikTok/Reels
- غير مكررة
- قوية نفسياً

مهم: أجب بـ JSON array فقط.

مثال:
["أنت لا تعرف الحقيقة...", "كل شيء بدأ تلك الليلة!"]
"""

    def build_title_prompt(self, topic: str) -> str:
        return f"""
أنشئ 10 عناوين عربية Viral قصيرة جداً عن: "{topic}"

القواعد:
- أقل من 6 كلمات
- قوية نفسياً
- غامضة وسينمائية
- قابلة للنقر
- غير مكررة

مهم: أجب بـ JSON array فقط.
"""

    def build_cta_prompt(self, topic: str) -> str:
        return f"""
أنشئ 10 عبارات CTA قصيرة وقوية لفيديو عن: "{topic}"

القواعد:
- قصيرة جداً
- تضرب المشاهد نفسياً
- تدفع للمتابعة أو التعليق
- أسلوب سينمائي Viral
- غير مكررة

مهم: أجب بـ JSON array فقط.
"""

    def build_visual_prompt(self, scene_text: str, mood: str = "dark") -> str:
        return f"""
حوّل الجملة التالية إلى وصف سينمائي احترافي لمحركات توليد الفيديو.

النص: "{scene_text}"
الأسلوب: {mood}

القواعد:
- cinematic realistic dramatic
- ultra detailed emotional atmosphere
- suitable for TikTok shorts

مهم: أجب بجملة واحدة فقط بالإنجليزية.
"""
