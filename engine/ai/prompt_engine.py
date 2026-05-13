"""
🎬 Ultimate Cinematic Prompt Engine
═══════════════════════════════════════════════════════════════
نظام Prompts متطور لتوليد فيديوهات Shorts عربية Viral
يدعم:
  • 7 أنماط (moods) سينمائية
  • 4 أنواع محتوى (motivational, educational, story, quote)
  • مدد مرنة (30, 45, 60 ثانية)
  • تنويع تلقائي عبر random + seed
═══════════════════════════════════════════════════════════════
"""

import random
from typing import Literal, Optional


class PromptEngine:
    """محرك توليد Prompts احترافي للفيديوهات العربية."""

    # ─── أمثلة الأسلوب (للتدريب على النمط) ─────────────────────────
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
        "العالم لا يتوقف لأحد... فتحرك.",
    ]

    # ─── أنماط الأسلوب (Moods) ─────────────────────────────────────
    MOOD_RULES = {
        "dark":          "أسلوب مظلم وعميق وبارد عاطفياً.",
        "emotional":     "أسلوب عاطفي مؤثر نفسياً وإنسانياً.",
        "horror":        "أسلوب مرعب متوتر مليء بالغموض.",
        "motivation":    "أسلوب تحفيزي شرس وصادم.",
        "psychological": "أسلوب نفسي يضرب المخاوف الداخلية.",
        "sad":           "أسلوب حزين وتأملي عميق.",
        "sigma":         "أسلوب قوي وبارد وواثق.",
    }

    # ─── أنواع المحتوى ─────────────────────────────────────────────
    CONTENT_TYPES = {
        "motivational": {
            "description": "محتوى تحفيزي يدفع للتغيير والإنجاز",
            "default_mood": "motivation",
            "tone": "قوي ومحفز",
        },
        "educational": {
            "description": "محتوى تعليمي يقدم معلومة قيّمة",
            "default_mood": "psychological",
            "tone": "هادئ وواضح",
        },
        "story": {
            "description": "قصة قصيرة مؤثرة بنهاية صادمة",
            "default_mood": "emotional",
            "tone": "سردي مشوّق",
        },
        "quote": {
            "description": "اقتباس عميق مع شرح فلسفي",
            "default_mood": "sigma",
            "tone": "تأملي عميق",
        },
    }

    # ─── إعدادات المدة ─────────────────────────────────────────────
    DURATION_PRESETS = {
        30: {"scenes": (8, 10),  "min_duration": 25, "max_duration": 32},
        45: {"scenes": (10, 14), "min_duration": 38, "max_duration": 47},
        60: {"scenes": (12, 16), "min_duration": 50, "max_duration": 58},
    }

    # ════════════════════════════════════════════════════════════════
    #                    Prompt: السكربت الكامل
    # ════════════════════════════════════════════════════════════════
    def build_script_prompt(
        self,
        topic: str,
        mood: Literal[
            "dark", "emotional", "horror",
            "motivation", "psychological", "sad", "sigma"
        ] = "dark",
        content_type: Literal[
            "motivational", "educational", "story", "quote"
        ] = "motivational",
        target_duration: int = 45,
    ) -> str:
        """
        بناء prompt السكربت الكامل.

        Args:
            topic: موضوع الفيديو
            mood: النمط العاطفي
            content_type: نوع المحتوى
            target_duration: المدة المستهدفة (30/45/60)
        """
        # ── إعدادات المدة ───────────────────────────────────────
        duration_cfg = self.DURATION_PRESETS.get(
            target_duration,
            self.DURATION_PRESETS[45]
        )
        min_scenes, max_scenes = duration_cfg["scenes"]
        min_dur = duration_cfg["min_duration"]
        max_dur = duration_cfg["max_duration"]

        # ── نوع المحتوى ─────────────────────────────────────────
        content_cfg = self.CONTENT_TYPES.get(
            content_type,
            self.CONTENT_TYPES["motivational"]
        )
        content_desc = content_cfg["description"]
        content_tone = content_cfg["tone"]

        # ── نمط الأسلوب ─────────────────────────────────────────
        mood_instruction = self.MOOD_RULES.get(mood, self.MOOD_RULES["dark"])

        # ── أمثلة عشوائية ───────────────────────────────────────
        examples = random.sample(
            self.STYLE_EXAMPLES,
            min(5, len(self.STYLE_EXAMPLES))
        )
        examples_str = "\n\n".join(f"• {ex}" for ex in examples)

        # ── seed لضمان تنويع المحتوى ────────────────────────────
        seed = random.randint(10000, 99999)

        return f"""أنت مخرج سينمائي عالمي وكاتب Viral Arabic Shorts محترف.

[seed: {seed}]

═══════════════════════════════════════
🎯 المهمة
═══════════════════════════════════════
تحويل الموضوع التالي إلى فيديو عربي قصير شديد التأثير
مناسب لـ: TikTok / Instagram Reels / YouTube Shorts

📌 الموضوع: "{topic}"
🎭 نوع المحتوى: {content_type} ({content_desc})
🎨 الأسلوب: {mood} - {mood_instruction}
🗣️ النبرة: {content_tone}

═══════════════════════════════════════
📏 المواصفات الإلزامية
═══════════════════════════════════════

1️⃣ اللغة:
   • العربية الفصحى البسيطة
   • قوية ومؤثرة وسهلة النطق
   • بإيقاع طبيعي بشري

2️⃣ المدة:
   • بين {min_dur} و {max_dur} ثانية

3️⃣ عدد المشاهد:
   • من {min_scenes} إلى {max_scenes} مشهد

4️⃣ طول الجملة:
   • من 3 إلى 9 كلمات فقط

5️⃣ الأداء الصوتي:
   • استخدم "..." للتنفس والتوتر
   • استخدم "!" للصدمة والانفعال
   • إيقاع سينمائي طبيعي

6️⃣ الهيكل:
   • Hook قوي جداً في البداية (أول 3 ثوانٍ)
   • تصعيد تدريجي للتوتر
   • نهاية تضرب المشاهد نفسياً
   • CTA قصير وقوي

═══════════════════════════════════════
🚫 ممنوع
═══════════════════════════════════════
• الوعظ المباشر
• الحشو والتكرار
• الجمل الطويلة
• الأسلوب الروبوتي
• تكرار الأمثلة أدناه حرفياً

═══════════════════════════════════════
✅ مطلوب
═══════════════════════════════════════
• جمل قابلة للاقتباس
• تأثير نفسي قوي
• Retention عالي
• محتوى مختلف تماماً عن أي فيديو سابق

═══════════════════════════════════════
💡 أمثلة الأسلوب (لا تكررها حرفياً)
═══════════════════════════════════════

{examples_str}

═══════════════════════════════════════
🎬 تعليمات المشاهد
═══════════════════════════════════════
لكل مشهد أضف:
• visual_prompt: وصف سينمائي بالإنجليزية لمحركات توليد الفيديو
• camera_motion: slow_zoom / fast_push / handheld / cinematic_pan / drone_shot / static
• music_intensity: رقم بين 0 و 1
• voice_tone: whisper / cold / aggressive / sad / emotionless / intense / calm
• transition: glitch_fade / fast_cut / blur_transition / cinematic_flash / smooth_fade
• energy: رقم بين 0 و 1

═══════════════════════════════════════
⚠️ مهم جداً
═══════════════════════════════════════
• لا تكتب أي شرح خارج JSON
• لا تستخدم markdown أو ```json
• أرجع JSON صالح فقط
• كل مشهد يجب أن يكون مختلفاً
• اجعل المحتوى فريداً في كل مرة

═══════════════════════════════════════
📋 صيغة JSON المطلوبة
═══════════════════════════════════════

{{
  "title": "عنوان قوي للفيديو",
  "hook": "أول جملة صادمة توقف المشاهد...",
  "mood": "{mood}",
  "content_type": "{content_type}",
  "duration_estimate": {(min_dur + max_dur) / 2:.1f},
  "voice_style": "deep cinematic arabic",
  "music_mood": "dark cinematic ambient",
  "music_style": "epic emotional",
  "color_style": "dark contrast cinematic",
  "subtitle_style": "big bold cinematic",
  "cta": "تابع... فالقادم أخطر!",
  "hashtags": ["#تحفيز", "#نجاح", "#shorts"],
  "full_text": "النص الكامل المتصل لكل المشاهد",
  "scenes": [
    {{
      "id": 0,
      "type": "hook",
      "text": "النص السينمائي هنا...",
      "duration": 3.5,
      "pause_after": 0.6,
      "voice_tone": "intense",
      "camera_motion": "slow_zoom",
      "music_intensity": 0.9,
      "transition": "glitch_fade",
      "energy": 0.95,
      "visual_prompt": "dark cinematic scene, dramatic lighting, emotional atmosphere",
      "emphasis": [
        {{"word": "الخوف", "position": 2}}
      ]
    }}
  ]
}}

اكتب السكربت الآن. تأكد أن المحتوى مختلف تماماً وفريد."""

    # ════════════════════════════════════════════════════════════════
    #                    Prompts إضافية
    # ════════════════════════════════════════════════════════════════
    def build_hook_variants_prompt(
        self,
        topic: str,
        count: int = 5,
        mood: str = "dark"
    ) -> str:
        """توليد عدة Hooks مختلفة لنفس الموضوع."""
        return f"""أنشئ {count} Hooks عربية Viral شديدة القوة.

📌 الموضوع: "{topic}"
🎨 الأسلوب: {mood}

القواعد:
• أقل من 8 كلمات
• صادمة جداً
• تثير الفضول فوراً
• استخدم "..." و "!" بذكاء
• مناسبة لـ TikTok/Reels
• غير مكررة وقوية نفسياً

⚠️ مهم: أجب بـ JSON array فقط.

مثال:
["أنت لا تعرف الحقيقة...", "كل شيء بدأ تلك الليلة!"]
"""

    def build_title_prompt(self, topic: str, count: int = 10) -> str:
        """توليد عناوين Viral للفيديو."""
        return f"""أنشئ {count} عناوين عربية Viral قصيرة جداً عن: "{topic}"

القواعد:
• أقل من 6 كلمات
• قوية نفسياً
• غامضة وسينمائية
• قابلة للنقر (Clickbait احترافي)
• غير مكررة

⚠️ مهم: أجب بـ JSON array فقط.
"""

    def build_cta_prompt(self, topic: str, count: int = 10) -> str:
        """توليد عبارات CTA قوية."""
        return f"""أنشئ {count} عبارات CTA قصيرة وقوية لفيديو عن: "{topic}"

القواعد:
• قصيرة جداً (3-7 كلمات)
• تضرب المشاهد نفسياً
• تدفع للمتابعة أو التعليق
• أسلوب سينمائي Viral
• غير مكررة

⚠️ مهم: أجب بـ JSON array فقط.
"""

    def build_visual_prompt(self, scene_text: str, mood: str = "dark") -> str:
        """تحويل نص عربي إلى وصف سينمائي بالإنجليزية."""
        return f"""حوّل الجملة التالية إلى وصف سينمائي احترافي لمحركات توليد الفيديو/الصور.

📌 النص: "{scene_text}"
🎨 الأسلوب: {mood}

القواعد:
• cinematic, realistic, dramatic
• ultra detailed, emotional atmosphere
• suitable for vertical TikTok shorts (9:16)
• mention lighting, mood, camera angle

⚠️ مهم: أجب بجملة واحدة فقط بالإنجليزية.
"""

    def build_hashtags_prompt(self, topic: str, count: int = 10) -> str:
        """توليد هاشتاجات للنشر."""
        return f"""أنشئ {count} هاشتاجات عربية وإنجليزية Viral لفيديو عن: "{topic}"

القواعد:
• مزيج عربي + إنجليزي
• شائعة ومنتشرة
• مرتبطة بالموضوع
• مناسبة لـ TikTok/Reels/Shorts

⚠️ مهم: أجب بـ JSON array فقط.

مثال:
["#تحفيز", "#نجاح", "#motivation", "#shorts"]
"""

    # ════════════════════════════════════════════════════════════════
    #                    دوال مساعدة
    # ════════════════════════════════════════════════════════════════
    def get_mood_for_content(self, content_type: str) -> str:
        """الحصول على mood افتراضي مناسب لنوع المحتوى."""
        return self.CONTENT_TYPES.get(
            content_type,
            self.CONTENT_TYPES["motivational"]
        )["default_mood"]

    def get_random_mood(self) -> str:
        """اختيار mood عشوائي."""
        return random.choice(list(self.MOOD_RULES.keys()))

    def list_available_moods(self) -> list:
        """قائمة الأنماط المتاحة."""
        return list(self.MOOD_RULES.keys())

    def list_content_types(self) -> list:
        """قائمة أنواع المحتوى المتاحة."""
        return list(self.CONTENT_TYPES.keys())
