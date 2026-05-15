"""
🎬 Ultimate Viral Prompt Engine v3.0
═══════════════════════════════════════════════════════════════
نظام Prompts متطور لتوليد فيديوهات Shorts عربية Viral احترافية
مع تقنيات Hooks متطورة + Pattern Interrupts + Curiosity Gaps

يستخدم:
  ✓ Hook Frameworks (AIDA, PAS, FAB)
  ✓ Open Loops & Curiosity Gaps
  ✓ Pattern Interrupts كل 3-5 ثواني
  ✓ Power Words عربية مدروسة
  ✓ Storytelling Structure احترافي
  ✓ Anti-Boring Tactics (منع الملل)
═══════════════════════════════════════════════════════════════
"""

import random
from typing import Literal, Optional


class PromptEngine:
    """محرك توليد Prompts احترافي للفيديوهات الفيروسية."""

    # ═════════════════════════════════════════════════════════════════
    # 🎯 Hooks الفيروسية (مُختبرة على ملايين المشاهدات)
    # ═════════════════════════════════════════════════════════════════
    VIRAL_HOOKS = [
        # 🔥 Pattern Interrupt
        "توقف!... ما تفعله الآن خطأ كبير.",
        "انتظر ثانية!... قبل أن تكمل التمرير.",
        "احذر!... هذا الفيديو سيغيّر طريقة تفكيرك.",
        
        # 💎 Curiosity Gap
        "99% من الناس لا يعرفون هذا...",
        "ما لن يخبرك به أحد عن النجاح...",
        "السر الذي يخفونه عنك منذ سنوات...",
        "اكتشفت شيئاً سيصدمك...",
        
        # ⚡ Bold Statement
        "كل ما تعرفه عن الحياة كذبة!",
        "أنت لست من تظن نفسك...",
        "العالم يعمل عكس ما تعتقد!",
        "النجاح ليس ما تظنه أبداً...",
        
        # 🎯 Personal Question
        "هل سألت نفسك يوماً... لماذا تفشل؟",
        "متى آخر مرة شعرت بالحياة الحقيقية؟",
        "ما الذي يمنعك من تحقيق أحلامك الآن؟",
        "هل تعرف لماذا الأذكياء يخسرون أحياناً؟",
        
        # 💔 Emotional Trigger
        "إذا كنت تشعر بهذا... فأنت في خطر!",
        "هذا الإحساس... قتل ملايين الأحلام.",
        "كل ليلة... يعيش هذا الشعور آلاف الناس.",
        
        # 🧠 Authority + Curiosity
        "علماء النفس اكتشفوا حقيقة صادمة...",
        "أبحاث جديدة تكشف ما كنت تجهله...",
        "خبراء النجاح يقولون شيئاً غريباً...",
        
        # ⏰ Urgency
        "إذا لم تفعل هذا اليوم... ستندم!",
        "الوقت ينفد... وأنت لا تدري!",
        "كل ثانية تمر... تخسر شيئاً ثميناً.",
        
        # 🎭 Story Hook
        "في يوم من الأيام... حدث شيء غيّر حياتي.",
        "كنت أعتقد أنني أعرف كل شيء... حتى ذلك اليوم.",
        "قابلت شخصاً... قال لي جملة لن أنساها.",
        
        # 🔮 Mystery
        "هناك سر... قليلون يعرفونه.",
        "الحقيقة المخفية وراء... كل شيء.",
        "ما لا يريدونك أن تعرفه...",
    ]

    # ═════════════════════════════════════════════════════════════════
    # 💎 Power Words عربية (تشد الانتباه)
    # ═════════════════════════════════════════════════════════════════
    POWER_WORDS = [
        # كلمات الصدمة
        "صادم", "خطير", "ممنوع", "سري", "مخفي",
        "محظور", "كارثي", "مدمر", "قاتل", "مرعب",
        
        # كلمات الفضول
        "اكتشف", "تعلّم", "افهم", "اعرف", "كشف",
        "حقيقة", "سر", "لغز", "غامض", "مجهول",
        
        # كلمات القوة
        "أقوى", "أعظم", "أفضل", "الأخطر", "الأعمق",
        "الحاسم", "النهائي", "الفاصل", "المصيري",
        
        # كلمات الإلحاح
        "الآن", "فوراً", "سريعاً", "قبل فوات الأوان",
        "اللحظة", "اليوم", "هذه الثانية",
        
        # كلمات عاطفية
        "ستندم", "ستبكي", "ستفقد", "ستخسر", "ستتذكر",
        "لن تنسى", "سيغيّر حياتك", "سيصدمك",
    ]

    # ═════════════════════════════════════════════════════════════════
    # 📊 أمثلة الأسلوب الفيروسي (مُحدّثة)
    # ═════════════════════════════════════════════════════════════════
    STYLE_EXAMPLES = [
        # Hooks قوية
        "توقف!... ما تفعله الآن... سيدمرك غداً.",
        "99% من الناس... يعيشون حياة لم يختاروها.",
        "اسمعني جيداً!... لا أحد سيأتي لإنقاذك.",
        "هل تعلم؟... 87% من الأحلام تموت بسبب جملة واحدة.",
        
        # Pattern Interrupts
        "انتظر... هذه ليست النهاية.",
        "لكن المفاجأة... لم تأتِ بعد!",
        "الآن... الجزء الذي سيصدمك.",
        
        # Curiosity Gaps
        "في النهاية... ستفهم لماذا.",
        "والسبب؟... سيغيّر نظرتك للحياة.",
        "ما حدث بعدها... لم يصدّقه أحد.",
        
        # Emotional Punches
        "كل ألم تتجاهله... يعود بقوة أكبر.",
        "الصمت الذي تعيشه... سيبتلعك يوماً.",
        "أنت لا تخسر... أنت تتعلم.",
        
        # Power Statements
        "الفرق بينك وبين الناجح؟... قرار واحد.",
        "أنت أقوى مما تظن... بعشر مرات.",
        "النجاح ليس صدفة... بل اختيار.",
        
        # Wisdom Quotes
        "اللحظة التي تستسلم فيها... هي اللحظة قبل الفوز مباشرة.",
        "الألم مؤقت... الندم أبدي.",
        "كل عظيم في التاريخ... كان مجنوناً في عينه!",
        
        # Closing Hooks (للنهاية)
        "تذكّر هذه الكلمات... ستحتاجها يوماً.",
        "شارك هذا... قبل أن يحذف!",
        "اكتب 'فهمت' إذا وصلتك الرسالة.",
    ]

    # ─── أنماط الأسلوب (Moods) محدّثة ───────────────────────────
    MOOD_RULES = {
        "dark": "أسلوب مظلم وعميق، يخاطب الجانب الخفي في النفس البشرية.",
        "emotional": "أسلوب عاطفي يلامس القلب ويجعل المشاهد يتفاعل بقوة.",
        "horror": "أسلوب مرعب يخلق توتراً نفسياً ويبقي المشاهد متيقظاً.",
        "motivation": "أسلوب تحفيزي شرس يدفع للحركة الفورية والتغيير.",
        "psychological": "أسلوب نفسي عميق يضرب المخاوف والآمال الداخلية.",
        "sad": "أسلوب حزين تأملي يجعل المشاهد يتوقف ويفكر.",
        "sigma": "أسلوب قوي وبارد وواثق، مثل الذئب المنفرد.",
        "viral": "أسلوب فيروسي حديث، يستخدم تقنيات TikTok و Reels.",
    }

    # ─── أنواع المحتوى محدّثة ──────────────────────────────────────
    CONTENT_TYPES = {
        "motivational": {
            "description": "محتوى تحفيزي قوي يصدم ويحرك",
            "default_mood": "motivation",
            "tone": "شرس ومُلهم",
            "hook_style": "challenge",  # تحدي
        },
        "educational": {
            "description": "معلومة قيّمة بطريقة جذابة",
            "default_mood": "psychological",
            "tone": "ذكي وواضح",
            "hook_style": "curiosity",  # فضول
        },
        "story": {
            "description": "قصة قصيرة بنهاية صادمة",
            "default_mood": "emotional",
            "tone": "سردي مشوّق",
            "hook_style": "narrative",  # قصصي
        },
        "quote": {
            "description": "اقتباس عميق مع تفسير قوي",
            "default_mood": "sigma",
            "tone": "تأملي عميق",
            "hook_style": "philosophical",  # فلسفي
        },
    }

    # ─── إعدادات المدة (محدّثة - أقصر = أكثر فيروسية) ─────────────
    DURATION_PRESETS = {
        30: {
            "scenes": (6, 8),
            "min_duration": 22,
            "max_duration": 30,
            "words_per_scene": (4, 8),
        },
        45: {
            "scenes": (8, 11),
            "min_duration": 35,
            "max_duration": 45,
            "words_per_scene": (4, 9),
        },
        60: {
            "scenes": (10, 14),
            "min_duration": 48,
            "max_duration": 60,
            "words_per_scene": (5, 10),
        },
    }

    # ════════════════════════════════════════════════════════════════
    #              🎯 Prompt السكربت الفيروسي
    # ════════════════════════════════════════════════════════════════
    def build_script_prompt(
        self,
        topic: str,
        mood: Literal[
            "dark", "emotional", "horror", "motivation",
            "psychological", "sad", "sigma", "viral"
        ] = "dark",
        content_type: Literal[
            "motivational", "educational", "story", "quote"
        ] = "motivational",
        target_duration: int = 45,
    ) -> str:
        """بناء prompt السكربت الفيروسي."""
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

        # نمط الأسلوب
        mood_instruction = self.MOOD_RULES.get(mood, self.MOOD_RULES["dark"])

        # أمثلة Hooks عشوائية
        hooks_sample = random.sample(self.VIRAL_HOOKS, 5)
        hooks_str = "\n".join(f"  • {h}" for h in hooks_sample)

        # أمثلة الأسلوب
        examples = random.sample(self.STYLE_EXAMPLES, 6)
        examples_str = "\n".join(f"  • {ex}" for ex in examples)

        # Power words
        power_words = random.sample(self.POWER_WORDS, 8)
        power_words_str = "، ".join(power_words)

        # seed لضمان التنويع
        seed = random.randint(10000, 99999)

        return f"""أنت أفضل كاتب سيناريو فيروسي عربي في العالم.
متخصص في صناعة محتوى يحقق ملايين المشاهدات على TikTok وReels.

[seed: {seed}]

═══════════════════════════════════════
🎯 المهمة الحرجة
═══════════════════════════════════════

اكتب سكربت فيديو Short عربي **فيروسي 100%** يُحقق:
  ✅ Retention عالي جداً (المشاهد يكمل حتى النهاية)
  ✅ يمنع التمرير في أول 3 ثوانٍ
  ✅ يخلق Hook قوي في كل 5 ثوانٍ (Pattern Interrupt)
  ✅ ينتهي بـ CTA يحث على المشاركة

📌 الموضوع: "{topic}"
🎭 نوع المحتوى: {content_type}
   الوصف: {content_cfg['description']}
   النبرة: {content_cfg['tone']}
🎨 الأسلوب: {mood}
   {mood_instruction}

═══════════════════════════════════════
🧠 سيكولوجية المحتوى الفيروسي
═══════════════════════════════════════

استخدم هذه التقنيات في السكربت:

1. **Hook قوي** (أول 3 ثوانٍ):
   - Pattern Interrupt → "توقف!" "انتظر!" "احذر!"
   - Curiosity Gap → "ما لن يخبرك به أحد..."
   - Bold Statement → "كل ما تعرفه كذبة!"
   - Personal Question → "هل سألت نفسك يوماً؟"

2. **Open Loops** (فجوات الفضول):
   - افتح سؤال في البداية
   - لا تجب عليه إلا في النهاية
   - مثل: "السر سأكشفه في النهاية..."

3. **Pattern Interrupts** كل 5 ثوانٍ:
   - "لكن..." "والمفاجأة..." "الأهم..."
   - "انتبه هنا..." "ركّز معي..."

4. **Power Words** عربية:
   {power_words_str}

5. **Emotional Triggers**:
   - الخوف من الفقدان (FOMO)
   - الفضول الشديد
   - الصدمة المعرفية
   - الإلهام الفوري

═══════════════════════════════════════
📏 المواصفات الفنية الإلزامية
═══════════════════════════════════════

1️⃣ **اللغة**:
   ✓ عربية فصحى بسيطة وقوية
   ✓ سهلة النطق وواضحة
   ✓ بدون تعقيد لغوي
   
2️⃣ **المدة**:
   ✓ بين {min_dur} و {max_dur} ثانية بالضبط
   
3️⃣ **عدد المشاهد**:
   ✓ من {min_scenes} إلى {max_scenes} مشهد فقط
   
4️⃣ **طول الجملة**:
   ✓ من {min_words} إلى {max_words} كلمات (مهم جداً!)
   ✓ جمل قصيرة = إيقاع سريع = retention عالي
   
5️⃣ **الإيقاع الصوتي**:
   ✓ استخدم "..." للتوقف الدراماتيكي (3-5 مرات)
   ✓ استخدم "!" للتأكيد والصدمة (3-7 مرات)
   ✓ نبرة متغيرة (لا رتابة)
   
6️⃣ **البنية الفيروسية**:
   ✓ Scene 1: HOOK قوي يصدم
   ✓ Scene 2-3: PROMISE (وعد بمعلومة قيّمة)
   ✓ Scene 4-{max_scenes-2}: BUILD-UP (بناء التوتر)
   ✓ Scene {max_scenes-1}: CLIMAX (الكشف)
   ✓ Scene الأخير: CTA قوي

═══════════════════════════════════════
🚫 ممنوع تماماً
═══════════════════════════════════════

❌ الوعظ المباشر والممل
❌ الجمل الطويلة (أكثر من {max_words} كلمات)
❌ التكرار والحشو
❌ بداية ضعيفة أو عادية
❌ نهاية بدون قوة
❌ الأسلوب الأكاديمي
❌ كلمات معقدة لا يفهمها العامة
❌ نسخ أمثلة الأسلوب حرفياً

═══════════════════════════════════════
✅ مطلوب بقوة
═══════════════════════════════════════

✓ Hook صادم في الثانية الأولى
✓ Pattern Interrupt كل مشهد
✓ Curiosity Gap مفتوح طوال الفيديو
✓ Power Words في كل مشهد
✓ Emotional Punch في النهاية
✓ CTA يجبر على التفاعل
✓ كلمات قابلة للاقتباس
✓ محتوى لا يُنسى

═══════════════════════════════════════
🔥 أمثلة Hooks فيروسية ناجحة
═══════════════════════════════════════

{hooks_str}

═══════════════════════════════════════
💡 أمثلة الأسلوب (للإلهام فقط - لا تكرّرها)
═══════════════════════════════════════

{examples_str}

═══════════════════════════════════════
🎬 تعليمات تقنية لكل مشهد
═══════════════════════════════════════

لكل مشهد أضف:
• visual_prompt: وصف سينمائي بالإنجليزية (مفصّل، مشاعر، إضاءة)
• camera_motion: slow_zoom / fast_push / cinematic_pan / static
• voice_tone: intense / cold / aggressive / sad / whisper / powerful
• transition: glitch_fade / fast_cut / cinematic_flash / smooth_fade
• energy: 0.7-1.0 (يجب أن تكون عالية لمنع الملل)
• music_intensity: 0.6-1.0

═══════════════════════════════════════
⚠️ قواعد JSON الصارمة
═══════════════════════════════════════

✓ أرجع JSON صالح فقط، لا شرح خارجه
✓ لا تستخدم ```json أو markdown
✓ كل المشاهد مختلفة تماماً
✓ التوقيتات منطقية ومتسلسلة
✓ النص قابل للنطق بسهولة

═══════════════════════════════════════
📋 صيغة JSON المطلوبة
═══════════════════════════════════════

{{
  "title": "عنوان فيروسي قوي (أقل من 6 كلمات)",
  "hook": "Hook صادم يوقف المشاهد فوراً...",
  "mood": "{mood}",
  "content_type": "{content_type}",
  "duration_estimate": {(min_dur + max_dur) / 2:.1f},
  "voice_style": "deep cinematic powerful arabic",
  "music_mood": "epic emotional cinematic",
  "music_style": "viral tiktok trending",
  "color_style": "high contrast cinematic dark",
  "subtitle_style": "huge bold modern viral",
  "cta": "شارك إذا فهمت!",
  "hashtags": ["#viral", "#تحفيز", "#shorts", "#fyp"],
  "full_text": "النص الكامل المتصل لكل المشاهد بدون توقف",
  "scenes": [
    {{
      "id": 0,
      "type": "hook",
      "text": "النص الفيروسي الصادم...",
      "duration": 3.0,
      "pause_after": 0.3,
      "voice_tone": "intense",
      "camera_motion": "fast_push",
      "music_intensity": 0.95,
      "transition": "glitch_fade",
      "energy": 0.98,
      "visual_prompt": "ultra dramatic dark scene, intense lighting, emotional shock, cinematic close-up, 9:16 vertical",
      "emphasis": [
        {{"word": "توقف", "position": 0}},
        {{"word": "خطأ", "position": 4}}
      ]
    }}
  ]
}}

═══════════════════════════════════════
🎯 الآن اكتب السكربت
═══════════════════════════════════════

تذكّر: كل ثانية يجب أن تخدم هدفاً.
كل كلمة يجب أن تشد المشاهد.
لا مكان للملل في {target_duration} ثانية!

اكتب الآن - JSON فقط، بدون أي شرح."""

    # ════════════════════════════════════════════════════════════════
    #                    🆕 Prompts إضافية محسّنة
    # ════════════════════════════════════════════════════════════════
    def build_hook_variants_prompt(
        self,
        topic: str,
        count: int = 5,
        mood: str = "dark",
    ) -> str:
        """توليد عدة Hooks فيروسية مختلفة."""
        return f"""أنشئ {count} Hooks عربية فيروسية شديدة القوة لفيديو عن: "{topic}"

🎨 الأسلوب: {mood}

القواعد الصارمة:
✓ أقل من 8 كلمات
✓ تستخدم Pattern Interrupt
✓ تخلق Curiosity Gap
✓ تستخدم Power Words
✓ تشد الانتباه في الثانية الأولى
✓ مناسبة لـ TikTok/Reels/Shorts
✓ غير مكررة وفريدة

أمثلة على الأسلوب المطلوب:
- "توقف!... هذا سيغيّر حياتك."
- "99% من الناس لا يعرفون..."
- "احذر!... قبل أن تكمل!"

⚠️ JSON array فقط، بدون شرح.
"""

    def build_title_prompt(self, topic: str, count: int = 10) -> str:
        """توليد عناوين Viral قوية."""
        return f"""أنشئ {count} عناوين عربية فيروسية قاتلة عن: "{topic}"

القواعد:
✓ من 3 إلى 6 كلمات فقط
✓ صادمة وغامضة
✓ تستخدم Power Words
✓ Clickbait احترافي
✓ مناسبة للـ thumbnail
✓ تدفع للنقر فوراً

أمثلة:
- "السر القاتل للنجاح"
- "ما لن يقولوه لك أبداً"
- "الحقيقة المخفية"

⚠️ JSON array فقط.
"""

    def build_cta_prompt(self, topic: str, count: int = 10) -> str:
        """توليد CTA فيروسية قوية."""
        return f"""أنشئ {count} عبارات CTA فيروسية لفيديو عن: "{topic}"

القواعد:
✓ من 3 إلى 7 كلمات
✓ تجبر على التفاعل
✓ تستخدم تقنيات الإقناع
✓ مناسبة للـ TikTok/Reels
✓ غير مكررة

أمثلة:
- "اكتب 'فهمت' لو وصلتك."
- "شارك قبل أن يُحذف!"
- "تابع... القادم أخطر!"
- "علّم صديقاً يحتاج هذا."

⚠️ JSON array فقط.
"""

    def build_visual_prompt(self, scene_text: str, mood: str = "dark") -> str:
        """تحويل نص لوصف سينمائي محسّن."""
        return f"""حوّل هذا النص العربي إلى وصف سينمائي عالي الجودة بالإنجليزية لتوليد الفيديو:

📌 النص: "{scene_text}"
🎨 الأسلوب: {mood}

القواعد:
✓ ultra cinematic, dramatic lighting
✓ vertical 9:16 aspect ratio (TikTok format)
✓ emotional atmosphere matching the text
✓ specific camera angle (close-up, wide, etc.)
✓ time of day & lighting mood
✓ color palette description
✓ professional film quality

⚠️ جملة واحدة احترافية بالإنجليزية فقط، بدون شرح.
"""

    def build_hashtags_prompt(self, topic: str, count: int = 15) -> str:
        """توليد هاشتاجات فيروسية."""
        return f"""أنشئ {count} هاشتاجات فيروسية لفيديو TikTok/Reels عن: "{topic}"

القواعد:
✓ مزيج عربي + إنجليزي
✓ هاشتاجات trending حالياً
✓ مناسبة للمحتوى التحفيزي/التعليمي
✓ تتضمن: #fyp #foryoupage #viral
✓ هاشتاجات specific بالموضوع

⚠️ JSON array فقط.

مثال:
["#fyp", "#viral", "#تحفيز", "#نجاح", "#shorts", "#motivation"]
"""

    # ═════════════════════════════════════════════════════════════════
    # 🆕 Prompts متقدمة جديدة
    # ═════════════════════════════════════════════════════════════════
    
    def build_storytelling_prompt(
        self,
        topic: str,
        target_duration: int = 60,
    ) -> str:
        """بناء سكربت قصة بنهاية صادمة."""
        return f"""اكتب قصة عربية فيروسية قصيرة عن: "{topic}"

البنية المطلوبة (Hero's Journey مصغّرة):
1. Setup (5 ثوانٍ) - تقديم الشخصية والوضع
2. Inciting Incident (10 ثوانٍ) - الحدث المثير
3. Rising Action (20 ثانية) - تصاعد الأحداث
4. Climax (15 ثانية) - الذروة الصادمة
5. Resolution (10 ثوانٍ) - الدرس والنهاية

القواعد:
✓ المدة: {target_duration} ثانية
✓ نهاية صادمة وغير متوقعة
✓ شخصيات حقيقية ومُحبّبة
✓ تفاصيل حسية (يرى، يسمع، يشعر)
✓ حوار قصير وقوي
✓ درس مخفي في النهاية

أرجع نفس صيغة JSON المعتادة للسكربت.
"""

    def build_educational_prompt(
        self,
        topic: str,
        target_duration: int = 60,
    ) -> str:
        """بناء سكربت تعليمي فيروسي."""
        return f"""اكتب فيديو تعليمي عربي فيروسي عن: "{topic}"

البنية:
1. Hook (3s) - حقيقة صادمة عن الموضوع
2. Promise (5s) - ما الذي سيتعلمه المشاهد
3. Content (40s) - 3-5 نقاط مدهشة بإيقاع سريع
4. Recap (5s) - ملخص سريع
5. CTA (5s) - حث على المشاركة/المتابعة

القواعد:
✓ معلومة جديدة كل 5-7 ثوانٍ
✓ استخدم أرقام صادمة
✓ أمثلة واقعية مفهومة
✓ بدون تعقيد علمي
✓ "هل تعلم؟" "اكتشف العلماء..."

أرجع نفس صيغة JSON المعتادة.
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

    def get_random_hook(self) -> str:
        """اختيار Hook فيروسي عشوائي."""
        return random.choice(self.VIRAL_HOOKS)

    def get_random_power_words(self, count: int = 5) -> list:
        """اختيار Power Words عشوائية."""
        return random.sample(
            self.POWER_WORDS,
            min(count, len(self.POWER_WORDS))
        )

    def list_available_moods(self) -> list:
        """قائمة الأنماط."""
        return list(self.MOOD_RULES.keys())

    def list_content_types(self) -> list:
        """قائمة أنواع المحتوى."""
        return list(self.CONTENT_TYPES.keys())

    def list_viral_hooks(self) -> list:
        """قائمة Hooks الفيروسية."""
        return self.VIRAL_HOOKS.copy()


# ════════════════════════════════════════════════════════════════════════
#                    اختبار سريع
# ════════════════════════════════════════════════════════════════════════
if __name__ == "__main__":
    engine = PromptEngine()
    
    print("✅ PromptEngine v3.0 جاهز")
    print(f"\n📊 المحتوى:")
    print(f"   • Moods: {len(engine.MOOD_RULES)}")
    print(f"   • Content Types: {len(engine.CONTENT_TYPES)}")
    print(f"   • Viral Hooks: {len(engine.VIRAL_HOOKS)}")
    print(f"   • Power Words: {len(engine.POWER_WORDS)}")
    print(f"   • Style Examples: {len(engine.STYLE_EXAMPLES)}")
    
    print(f"\n🎯 Hook عشوائي:")
    print(f"   {engine.get_random_hook()}")
    
    print(f"\n💎 Power Words:")
    print(f"   {', '.join(engine.get_random_power_words(5))}")
