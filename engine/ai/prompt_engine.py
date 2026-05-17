"""
🎬 Value-Driven Prompt Engine v4.0
═══════════════════════════════════════════════════════════════
محرك يُنتج محتوى يقدم قيمة حقيقية للمشاهد

التركيز على:
  ✓ معلومة محددة وقابلة للتطبيق
  ✓ أرقام وحقائق صادمة
  ✓ نصائح عملية (Actionable)
  ✓ قواعد ومبادئ يمكن تذكرها
  ✓ أمثلة واقعية
  ✓ Step-by-step structure
═══════════════════════════════════════════════════════════════
"""

import random
from typing import Literal, Optional


class PromptEngine:
    """محرك Prompts يُنتج محتوى قيّم وقابل للتطبيق."""

    # ═════════════════════════════════════════════════════════════════
    # 🎯 إطارات المحتوى القيّم (Value Frameworks)
    # ═════════════════════════════════════════════════════════════════
    VALUE_FRAMEWORKS = {
        # 1️⃣ القائمة (Listicle)
        "listicle": {
            "name": "قائمة مرقّمة",
            "structure": "Hook → 3-5 نقاط مرقّمة → Summary → CTA",
            "examples": [
                "3 عادات صباحية تغيّر حياتك",
                "5 أخطاء تدمر علاقاتك",
                "7 قواعد للنجاح المهني",
            ],
        },
        
        # 2️⃣ المشكلة-الحل
        "problem_solution": {
            "name": "مشكلة وحل",
            "structure": "المشكلة → السبب → الحل → التطبيق",
            "examples": [
                "لماذا تشعر بالتعب دائماً؟ السبب وحلّه",
                "لماذا تخسر مالك؟ القاعدة الذهبية",
                "لماذا تفشل علاقاتك؟ الخطأ الخفي",
            ],
        },
        
        # 3️⃣ القاعدة المسماة
        "named_rule": {
            "name": "قاعدة مُسمّاة",
            "structure": "اسم القاعدة → الشرح → مثال → كيفية التطبيق",
            "examples": [
                "قاعدة 80/20 لإدارة وقتك",
                "قاعدة 5 ثوانٍ للتغلب على الكسل",
                "قاعدة 21 يوم لبناء العادات",
            ],
        },
        
        # 4️⃣ الحقيقة الصادمة
        "shocking_truth": {
            "name": "حقيقة صادمة",
            "structure": "الحقيقة → الدليل → التأثير → ماذا تفعل",
            "examples": [
                "البحث الذي غيّر مفهوم النوم",
                "السر الذي يخفيه عنك الأذكياء",
                "الإحصائية التي ستصدمك عن وقتك",
            ],
        },
        
        # 5️⃣ القصة التعليمية
        "story_lesson": {
            "name": "قصة بدرس",
            "structure": "القصة → الموقف → الدرس → التطبيق",
            "examples": [
                "قصة فاشل أصبح ملياردير",
                "ما تعلمته من خسارتي الأكبر",
                "قصة ستغيّر نظرتك للفشل",
            ],
        },
        
        # 6️⃣ المقارنة
        "comparison": {
            "name": "مقارنة قاتلة",
            "structure": "الأول → الثاني → الفرق الخفي → ما تختار",
            "examples": [
                "الأذكياء vs العاديون - الفرق",
                "الأغنياء vs الفقراء - 5 فروق",
                "الناجح vs الفاشل - عادة واحدة",
            ],
        },
        
        # 7️⃣ خطوات Step-by-Step
        "step_by_step": {
            "name": "خطوات عملية",
            "structure": "الهدف → الخطوة 1 → 2 → 3 → النتيجة",
            "examples": [
                "كيف توفر مليون في 5 سنوات",
                "5 خطوات لقراءة 50 كتاب سنوياً",
                "كيف تتعلم أي مهارة في 20 ساعة",
            ],
        },
        
        # 8️⃣ التحذير
        "warning": {
            "name": "تحذير مهم",
            "structure": "الخطر → العلامات → الأسباب → كيف تتجنبه",
            "examples": [
                "5 علامات أن صديقك يستغلك",
                "احذر هذه الأخطاء في 30",
                "علامات إنذار في علاقتك",
            ],
        },
    }

    # ═════════════════════════════════════════════════════════════════
    # 💎 أنواع المعلومات القيّمة
    # ═════════════════════════════════════════════════════════════════
    VALUE_TYPES = [
        "إحصائية صادمة (مثل: 95% من الناس...)",
        "بحث علمي (مثل: دراسة هارفارد أثبتت...)",
        "قاعدة عملية (مثل: قاعدة 5 ثوانٍ...)",
        "رقم محدد (مثل: تحتاج 21 يوم لـ...)",
        "مثال واقعي (مثل: ستيف جوبز كان...)",
        "نصيحة قابلة للتطبيق (مثل: ابدأ يومك بـ...)",
        "تشخيص (مثل: إذا شعرت بـ X، فأنت...)",
        "وصفة (مثل: 3 خطوات لـ...)",
        "خطأ شائع (مثل: 90% يخطئون في...)",
        "اختصار ذكي (مثل: قاعدة WIN: ...)",
    ]

    # ═════════════════════════════════════════════════════════════════
    # 🎯 Hooks تقدم قيمة (وليس مجرد إثارة)
    # ═════════════════════════════════════════════════════════════════
    VALUE_HOOKS = [
        # 📊 إحصائية
        "95% من الناس يجهلون هذه الحقيقة...",
        "دراسة على 10,000 شخص أثبتت...",
        "البيانات تكشف شيئاً مذهلاً...",
        
        # 🔬 علمي
        "أبحاث جديدة من جامعة هارفارد تكشف...",
        "علماء النفس اكتشفوا قاعدة بسيطة...",
        "الدماغ البشري يعمل بطريقة غريبة...",
        
        # ❓ سؤال يثير الفضول
        "هل سألت نفسك لماذا الأذكياء يفعلون X؟",
        "ما الفرق بين من ينجح ومن يفشل؟",
        "لماذا 99% من الأهداف تموت في يناير؟",
        
        # 💡 وعد بمعلومة
        "في الـ 60 ثانية القادمة... ستتعلم سراً",
        "سأكشف لك خطأً تفعله يومياً",
        "قاعدة واحدة ستوفر لك سنوات...",
        
        # 🎯 محدد جداً
        "3 عادات صباحية تستخدمها أنجح 1%",
        "5 جمل تجعل أي شخص يحبك",
        "7 إشارات أن وقتك ينفد",
        
        # 🚨 تحذير قيّم
        "إذا فعلت X في الصباح... أنت في خطر",
        "هذه الإشارة تعني أن جسدك يصرخ",
        "5 علامات أنك على وشك الانهيار",
    ]

    # ═════════════════════════════════════════════════════════════════
    # 📝 أمثلة قوية (Value-First Examples)
    # ═════════════════════════════════════════════════════════════════
    POWERFUL_EXAMPLES = [
        # قواعد محددة
        "قاعدة الدقيقتين: إذا كان الأمر يستغرق دقيقتين... افعله الآن.",
        "قاعدة 90/10: حياتك 10% أحداث... 90% ردة فعلك.",
        "قاعدة 5 ثوانٍ: عُدّ من 5... ثم تحرك. لا تفكّر.",
        
        # حقائق صادمة
        "تستهلك يومياً 35,000 قرار... معظمها بدون وعي.",
        "دماغك يحتاج 66 يوماً لبناء عادة جديدة.",
        "1% تحسّن يومي = 37x أفضل بعد سنة.",
        
        # نصائح محددة
        "اكتب 3 أهداف فقط لليوم... لا أكثر.",
        "اشرب 500ml ماء فور الاستيقاظ.",
        "ضع هاتفك في غرفة أخرى أثناء العمل.",
        
        # أرقام مدهشة
        "5 ساعات من النوم العميق > 8 ساعات متقطعة.",
        "20% من جهدك يحقق 80% من نتائجك.",
        "كل ساعة موبايل يومياً = 365 ساعة سنوياً.",
        
        # تشخيصات
        "تشعر بالضيق صباحاً؟ نومك متقطع.",
        "تنسى دائماً؟ دماغك مرهق من الإشعارات.",
        "تشعر بالوحدة؟ علاقاتك سطحية، ليست قليلة.",
    ]

    # ─── أنماط الأسلوب ─────────────────────────────────────────────
    MOOD_RULES = {
        "informative": "أسلوب معلوماتي مباشر يقدم القيمة فوراً.",
        "educational": "أسلوب تعليمي مع شرح واضح وأمثلة.",
        "scientific": "أسلوب علمي مع أبحاث وإحصائيات.",
        "practical": "أسلوب عملي مع خطوات قابلة للتطبيق.",
        "psychological": "أسلوب نفسي يفسّر السلوكيات.",
        "motivational": "أسلوب تحفيزي مدعوم بأدلة.",
        "philosophical": "أسلوب فلسفي عميق ومُلهم.",
        "story": "أسلوب قصصي بدرس مستفاد.",
    }

    # ─── أنواع المحتوى محدّثة ──────────────────────────────────────
    CONTENT_TYPES = {
        "motivational": {
            "description": "تحفيز مع نصائح عملية مدعومة بأدلة",
            "default_mood": "practical",
            "frameworks": ["named_rule", "step_by_step", "shocking_truth"],
        },
        "educational": {
            "description": "تعليم بمعلومة قيّمة جديدة",
            "default_mood": "scientific",
            "frameworks": ["listicle", "shocking_truth", "comparison"],
        },
        "story": {
            "description": "قصة بدرس قابل للتطبيق",
            "default_mood": "story",
            "frameworks": ["story_lesson", "warning"],
        },
        "quote": {
            "description": "حكمة مع شرح عملي",
            "default_mood": "philosophical",
            "frameworks": ["shocking_truth", "named_rule"],
        },
    }

    # ─── إعدادات المدة ─────────────────────────────────────────────
    DURATION_PRESETS = {
        30: {"scenes": (6, 8), "min_duration": 22, "max_duration": 30,
             "words_per_scene": (4, 8)},
        45: {"scenes": (8, 11), "min_duration": 35, "max_duration": 45,
             "words_per_scene": (4, 9)},
        60: {"scenes": (10, 14), "min_duration": 48, "max_duration": 60,
             "words_per_scene": (5, 10)},
    }

    # ════════════════════════════════════════════════════════════════
    #              🎯 Prompt السكربت القيّم
    # ════════════════════════════════════════════════════════════════
    def build_script_prompt(
        self,
        topic: str,
        mood: str = "practical",
        content_type: Literal[
            "motivational", "educational", "story", "quote"
        ] = "motivational",
        target_duration: int = 45,
    ) -> str:
        """بناء prompt يُنتج محتوى قيّم."""
        # إعدادات المدة
        duration_cfg = self.DURATION_PRESETS.get(
            target_duration, self.DURATION_PRESETS[45]
        )
        min_scenes, max_scenes = duration_cfg["scenes"]
        min_dur = duration_cfg["min_duration"]
        max_dur = duration_cfg["max_duration"]
        min_words, max_words = duration_cfg["words_per_scene"]

        # نوع المحتوى
        content_cfg = self.CONTENT_TYPES.get(
            content_type, self.CONTENT_TYPES["motivational"]
        )

        # 🆕 اختيار framework عشوائي مناسب للنوع
        framework_name = random.choice(content_cfg["frameworks"])
        framework = self.VALUE_FRAMEWORKS[framework_name]

        # نمط الأسلوب
        mood_instruction = self.MOOD_RULES.get(mood, self.MOOD_RULES["practical"])

        # 🆕 أمثلة قوية
        examples = random.sample(self.POWERFUL_EXAMPLES, 5)
        examples_str = "\n".join(f"  • {ex}" for ex in examples)

        # 🆕 أنواع المعلومات القيّمة
        value_types_sample = random.sample(self.VALUE_TYPES, 5)
        value_types_str = "\n".join(f"  • {vt}" for vt in value_types_sample)

        # 🆕 hooks قيّمة
        hooks_sample = random.sample(self.VALUE_HOOKS, 4)
        hooks_str = "\n".join(f"  • {h}" for h in hooks_sample)

        # seed لضمان التنويع
        seed = random.randint(10000, 99999)

        return f"""أنت خبير محتوى تعليمي عربي محترف، متخصص في صناعة فيديوهات Shorts تُقدم قيمة حقيقية للمشاهد.

[seed: {seed}]

═══════════════════════════════════════
🎯 المهمة الأساسية
═══════════════════════════════════════

اكتب سكربت فيديو **يعلّم المشاهد شيئاً مفيداً** عن:

📌 الموضوع: "{topic}"
🎭 النوع: {content_type}
🎨 الأسلوب: {mood} - {mood_instruction}
🏗️ الإطار: {framework['name']} - {framework['structure']}

═══════════════════════════════════════
💎 ⚠️ القاعدة الذهبية ⚠️
═══════════════════════════════════════

❌ **ممنوع:** كلام عام ووعظ بدون قيمة
✅ **مطلوب:** معلومة محددة + قابلة للتطبيق

كل مشهد يجب أن يحتوي **واحدة من هذه:**

{value_types_str}

═══════════════════════════════════════
🏗️ البنية المطلوبة (Framework)
═══════════════════════════════════════

استخدم بنية: **{framework['name']}**
{framework['structure']}

أمثلة على عناوين هذا الإطار:
{chr(10).join(f"  • {ex}" for ex in framework['examples'])}

═══════════════════════════════════════
📏 المواصفات الفنية
═══════════════════════════════════════

1️⃣ **اللغة:**
   ✓ عربية فصحى بسيطة وواضحة
   ✓ مصطلحات يفهمها العامة
   ✓ بدون تعقيد لغوي

2️⃣ **المدة:** {target_duration} ثانية بالضبط
   ✓ عدد الكلمات الإجمالي: {self._get_word_count(target_duration)} كلمة (مهم جداً!)
   ✓ كل مشهد: {min_words}-{max_words} كلمات

3️⃣ **عدد المشاهد:** {min_scenes}-{max_scenes} مشهد

4️⃣ **طول الجملة:** {min_words}-{max_words} كلمات

5️⃣ **الإيقاع:**
   ✓ "..." للتوقف الدراماتيكي (3-5 مرات)
   ✓ "!" للتأكيد (3-5 مرات)
   ✓ ":" قبل النقاط الرقمية

6️⃣ **البنية:**
   • Scene 1: HOOK + Promise (يعد بقيمة محددة)
   • Scenes 2-3: المعلومة الرئيسية + الدليل
   • Scenes 4-{max_scenes-1}: التفاصيل والأمثلة
   • Last Scene: ملخص + CTA يطلب تطبيق

═══════════════════════════════════════
✅ مطلوب بقوة (Must Have)
═══════════════════════════════════════

✓ **رقم محدد على الأقل** (مثل: 5 خطوات، 21 يوم، 80%)
✓ **مثال واقعي على الأقل** (شخصية، شركة، حالة)
✓ **نصيحة قابلة للتطبيق فوراً** (Actionable)
✓ **سبب علمي/منطقي** للنصائح
✓ **خاتمة تحفّز على التطبيق**

═══════════════════════════════════════
🚫 ممنوع تماماً
═══════════════════════════════════════

❌ كلام عام مثل "كن قوياً" بدون شرح كيف
❌ نصائح فضفاضة "اعمل بجد"
❌ وعظ مباشر "يجب عليك..."
❌ تكرار نفس الفكرة بصياغات مختلفة
❌ معلومات مكررة في كل فيديو
❌ نصائح لا يمكن تطبيقها فوراً

═══════════════════════════════════════
💡 أمثلة على المحتوى المطلوب
═══════════════════════════════════════

{examples_str}

═══════════════════════════════════════
🔥 Hooks قيّمة (للإلهام)
═══════════════════════════════════════

{hooks_str}

═══════════════════════════════════════
📊 مقارنة: محتوى ضعيف vs قيّم
═══════════════════════════════════════

❌ **ضعيف:**
"الطموح والنجاح مهمان
يجب أن تعمل بجد
لتحقيق أحلامك"

✅ **قيّم:**
"دراسة هارفارد على 1,000 ناجح
كشفت سراً واحداً مشتركاً:
يكتبون أهدافهم يومياً.
الذين يكتبون = 42% أكثر تحقيقاً.
ابدأ الآن... 3 أهداف فقط."

═══════════════════════════════════════
🎬 تعليمات تقنية لكل مشهد
═══════════════════════════════════════

لكل مشهد أضف:
• visual_prompt: وصف سينمائي بالإنجليزية
• camera_motion: slow_zoom / fast_push / cinematic_pan / static
• voice_tone: intense / calm / authoritative / curious / powerful
• transition: smooth_fade / cinematic_flash / cross_dissolve
• energy: 0.6-1.0
• music_intensity: 0.5-0.9

═══════════════════════════════════════
⚠️ قواعد JSON
═══════════════════════════════════════

✓ JSON صالح فقط
✓ بدون markdown أو ```json
✓ كل المشاهد فريدة
✓ التوقيتات منطقية

═══════════════════════════════════════
📋 صيغة JSON
═══════════════════════════════════════

{{
  "title": "عنوان قيّم محدد",
  "hook": "Hook يعد بقيمة محددة...",
  "mood": "{mood}",
  "content_type": "{content_type}",
  "framework": "{framework_name}",
  "duration_estimate": {(min_dur + max_dur) / 2:.1f},
  "voice_style": "clear authoritative arabic",
  "music_mood": "modern educational",
  "music_style": "subtle background",
  "color_style": "clean modern",
  "subtitle_style": "huge bold readable",
  "cta": "طبّق وأخبرنا بالنتيجة!",
  "hashtags": ["#تعلم", "#تطوير", "#shorts"],
  "key_value": "القيمة الأساسية في جملة واحدة",
  "actionable_tip": "النصيحة القابلة للتطبيق",
  "full_text": "النص الكامل المتصل",
  "scenes": [
    {{
      "id": 0,
      "type": "hook",
      "text": "النص الذي يعد بقيمة محددة...",
      "duration": 3.5,
      "pause_after": 0.4,
      "voice_tone": "curious",
      "camera_motion": "slow_zoom",
      "music_intensity": 0.7,
      "transition": "smooth_fade",
      "energy": 0.85,
      "visual_prompt": "professional educational scene, clean modern lighting, focused atmosphere, 9:16 vertical",
      "value_element": "نوع القيمة (إحصائية/قاعدة/مثال)"
    }}
  ]
}}

═══════════════════════════════════════
🎯 الآن اكتب السكربت
═══════════════════════════════════════

تذكّر: المشاهد يجب أن يقول في النهاية:
"تعلمت شيئاً مفيداً!"

ليس فقط:
"كان فيديو جميل"

اكتب الآن - JSON فقط."""

    # ════════════════════════════════════════════════════════════════
    #                    Prompts إضافية
    # ════════════════════════════════════════════════════════════════
    def build_hook_variants_prompt(
        self,
        topic: str,
        count: int = 5,
        mood: str = "practical",
    ) -> str:
        """توليد Hooks قيّمة."""
        return f"""أنشئ {count} Hooks عربية تقدم قيمة لفيديو عن: "{topic}"

القواعد:
✓ كل Hook يعد بمعلومة محددة
✓ يستخدم رقم أو إحصائية
✓ أقل من 8 كلمات
✓ يخلق فضول علمي/معلوماتي

أمثلة:
- "95% من الناس يجهلون هذا..."
- "دراسة هارفارد كشفت السر..."
- "3 خطوات تغيّر حياتك في..."

⚠️ JSON array فقط.
"""

    def build_title_prompt(self, topic: str, count: int = 10) -> str:
        """توليد عناوين قيّمة."""
        return f"""أنشئ {count} عناوين قيّمة عن: "{topic}"

القواعد:
✓ يحتوي رقم أو وعد محدد
✓ يخبر المشاهد بما سيتعلمه
✓ من 3 إلى 6 كلمات

أمثلة:
- "5 قواعد للنجاح المهني"
- "السر العلمي للنوم"
- "3 خطوات لتوفير المال"

⚠️ JSON array فقط.
"""

    def build_cta_prompt(self, topic: str, count: int = 10) -> str:
        """توليد CTA يطلب تطبيق."""
        return f"""أنشئ {count} عبارات CTA لفيديو عن: "{topic}"

القواعد:
✓ يطلب من المشاهد التطبيق
✓ يجبر على التفاعل
✓ من 3 إلى 7 كلمات

أمثلة:
- "طبّق غداً وأخبرنا!"
- "احفظ القاعدة قبل أن تنساها"
- "شارك من يحتاج هذه النصيحة"

⚠️ JSON array فقط.
"""

    def build_visual_prompt(self, scene_text: str, mood: str = "practical") -> str:
        """تحويل نص لوصف سينمائي."""
        return f"""حوّل النص العربي إلى وصف سينمائي بالإنجليزية:

📌 النص: "{scene_text}"
🎨 الأسلوب: {mood}

القواعد:
✓ professional, clean, modern
✓ vertical 9:16
✓ educational atmosphere
✓ specific lighting and angle

⚠️ جملة واحدة بالإنجليزية فقط.
"""

    def build_hashtags_prompt(self, topic: str, count: int = 10) -> str:
        """توليد هاشتاجات."""
        return f"""أنشئ {count} هاشتاجات لفيديو تعليمي عن: "{topic}"

✓ مزيج عربي + إنجليزي
✓ تتضمن: #fyp #foryou
✓ مرتبطة بالموضوع

⚠️ JSON array فقط.
"""

    # ════════════════════════════════════════════════════════════════
    #                    دوال مساعدة
    # ════════════════════════════════════════════════════════════════
    def get_mood_for_content(self, content_type: str) -> str:
        """الحصول على mood افتراضي."""
        return self.CONTENT_TYPES.get(
            content_type, self.CONTENT_TYPES["motivational"]
        )["default_mood"]

    def get_random_mood(self) -> str:
        """اختيار mood عشوائي."""
        return random.choice(list(self.MOOD_RULES.keys()))

    def get_random_framework(self, content_type: str = "motivational") -> dict:
        """اختيار framework عشوائي."""
        content_cfg = self.CONTENT_TYPES.get(
            content_type, self.CONTENT_TYPES["motivational"]
        )
        framework_name = random.choice(content_cfg["frameworks"])
        return self.VALUE_FRAMEWORKS[framework_name]

    def list_available_moods(self) -> list:
        return list(self.MOOD_RULES.keys())

    def list_content_types(self) -> list:
        return list(self.CONTENT_TYPES.keys())

    def list_frameworks(self) -> dict:
        return self.VALUE_FRAMEWORKS


# ════════════════════════════════════════════════════════════════════════
#                    اختبار سريع
# ════════════════════════════════════════════════════════════════════════
if __name__ == "__main__":
    engine = PromptEngine()
    
    print("✅ Value-Driven Prompt Engine v4.0 جاهز")
    print(f"\n📊 المحتوى:")
    print(f"   • Frameworks: {len(engine.VALUE_FRAMEWORKS)}")
    print(f"   • Content Types: {len(engine.CONTENT_TYPES)}")
    print(f"   • Value Hooks: {len(engine.VALUE_HOOKS)}")
    print(f"   • Powerful Examples: {len(engine.POWERFUL_EXAMPLES)}")
    
    print(f"\n🏗️ Frameworks المتاحة:")
    for name, framework in engine.VALUE_FRAMEWORKS.items():
        print(f"   • {name}: {framework['name']}")
    
    print(f"\n💡 مثال على Hook قيّم:")
    print(f"   {random.choice(engine.VALUE_HOOKS)}")
