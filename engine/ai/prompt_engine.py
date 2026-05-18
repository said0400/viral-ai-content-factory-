"""
🎬 Value-Driven Prompt Engine v4.1
═══════════════════════════════════════════════════════════════
محرك يُنتج محتوى يقدم قيمة حقيقية للمشاهد

التحسينات في v4.1:
  ✓ إصلاح الكود المعطوب
  ✓ إضافة validation كامل
  ✓ تحسين type hints
  ✓ إضافة logging
  ✓ تنظيف الكود
  ✓ إضافة constants منفصلة
  ✓ تحسين الأداء
═══════════════════════════════════════════════════════════════
"""

from __future__ import annotations

import logging
import random
from dataclasses import dataclass, field
from typing import Literal, Optional

# ═══════════════════════════════════════════════════════════════════
# Logger Setup
# ═══════════════════════════════════════════════════════════════════
logger = logging.getLogger(__name__)


# ═══════════════════════════════════════════════════════════════════
# Type Definitions
# ═══════════════════════════════════════════════════════════════════
ContentType = Literal["motivational", "educational", "story", "quote"]
MoodType = Literal[
    "informative", "educational", "scientific", "practical",
    "psychological", "motivational", "philosophical", "story"
]
DurationType = Literal[30, 45, 60]


# ═══════════════════════════════════════════════════════════════════
# Data Classes (للوضوح والـ type safety)
# ═══════════════════════════════════════════════════════════════════
@dataclass(frozen=True)
class Framework:
    """إطار محتوى."""
    name: str
    structure: str
    examples: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class DurationConfig:
    """إعدادات المدة الزمنية."""
    min_scenes: int
    max_scenes: int
    min_duration: int
    max_duration: int
    min_words_per_scene: int
    max_words_per_scene: int
    
    @property
    def avg_duration(self) -> float:
        return (self.min_duration + self.max_duration) / 2
    
    @property
    def total_words_range(self) -> tuple[int, int]:
        return (
            self.min_words_per_scene * self.min_scenes,
            self.max_words_per_scene * self.max_scenes
        )


# ═══════════════════════════════════════════════════════════════════
# Constants (منفصلة لسهولة الصيانة)
# ═══════════════════════════════════════════════════════════════════
class PromptConstants:
    """الثوابت الخاصة بالـ Prompts."""
    
    SEPARATOR = "═" * 39
    
    # عدد العناصر العشوائية في كل prompt
    POWERFUL_EXAMPLES_COUNT = 5
    VALUE_TYPES_COUNT = 5
    HOOKS_COUNT = 4
    
    # حدود seed
    SEED_MIN = 10000
    SEED_MAX = 99999


# ═══════════════════════════════════════════════════════════════════
# Main Engine
# ═══════════════════════════════════════════════════════════════════
class PromptEngine:
    """محرك Prompts يُنتج محتوى قيّم وقابل للتطبيق."""

    # ─── إطارات المحتوى القيّم ─────────────────────────────────────
    VALUE_FRAMEWORKS: dict[str, Framework] = {
        "listicle": Framework(
            name="قائمة مرقّمة",
            structure="Hook → 3-5 نقاط مرقّمة → Summary → CTA",
            examples=[
                "3 عادات صباحية تغيّر حياتك",
                "5 أخطاء تدمر علاقاتك",
                "7 قواعد للنجاح المهني",
            ],
        ),
        "problem_solution": Framework(
            name="مشكلة وحل",
            structure="المشكلة → السبب → الحل → التطبيق",
            examples=[
                "لماذا تشعر بالتعب دائماً؟ السبب وحلّه",
                "لماذا تخسر مالك؟ القاعدة الذهبية",
                "لماذا تفشل علاقاتك؟ الخطأ الخفي",
            ],
        ),
        "named_rule": Framework(
            name="قاعدة مُسمّاة",
            structure="اسم القاعدة → الشرح → مثال → كيفية التطبيق",
            examples=[
                "قاعدة 80/20 لإدارة وقتك",
                "قاعدة 5 ثوانٍ للتغلب على الكسل",
                "قاعدة 21 يوم لبناء العادات",
            ],
        ),
        "shocking_truth": Framework(
            name="حقيقة صادمة",
            structure="الحقيقة → الدليل → التأثير → ماذا تفعل",
            examples=[
                "البحث الذي غيّر مفهوم النوم",
                "السر الذي يخفيه عنك الأذكياء",
                "الإحصائية التي ستصدمك عن وقتك",
            ],
        ),
        "story_lesson": Framework(
            name="قصة بدرس",
            structure="القصة → الموقف → الدرس → التطبيق",
            examples=[
                "قصة فاشل أصبح ملياردير",
                "ما تعلمته من خسارتي الأكبر",
                "قصة ستغيّر نظرتك للفشل",
            ],
        ),
        "comparison": Framework(
            name="مقارنة قاتلة",
            structure="الأول → الثاني → الفرق الخفي → ما تختار",
            examples=[
                "الأذكياء vs العاديون - الفرق",
                "الأغنياء vs الفقراء - 5 فروق",
                "الناجح vs الفاشل - عادة واحدة",
            ],
        ),
        "step_by_step": Framework(
            name="خطوات عملية",
            structure="الهدف → الخطوة 1 → 2 → 3 → النتيجة",
            examples=[
                "كيف توفر مليون في 5 سنوات",
                "5 خطوات لقراءة 50 كتاب سنوياً",
                "كيف تتعلم أي مهارة في 20 ساعة",
            ],
        ),
        "warning": Framework(
            name="تحذير مهم",
            structure="الخطر → العلامات → الأسباب → كيف تتجنبه",
            examples=[
                "5 علامات أن صديقك يستغلك",
                "احذر هذه الأخطاء في 30",
                "علامات إنذار في علاقتك",
            ],
        ),
    }

    # ─── أنواع المعلومات القيّمة ───────────────────────────────────
    VALUE_TYPES: tuple[str, ...] = (
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
    )

    # ─── Hooks قيّمة ────────────────────────────────────────────────
    VALUE_HOOKS: tuple[str, ...] = (
        # إحصائية
        "95% من الناس يجهلون هذه الحقيقة...",
        "دراسة على 10,000 شخص أثبتت...",
        "البيانات تكشف شيئاً مذهلاً...",
        # علمي
        "أبحاث جديدة من جامعة هارفارد تكشف...",
        "علماء النفس اكتشفوا قاعدة بسيطة...",
        "الدماغ البشري يعمل بطريقة غريبة...",
        # سؤال
        "هل سألت نفسك لماذا الأذكياء يفعلون X؟",
        "ما الفرق بين من ينجح ومن يفشل؟",
        "لماذا 99% من الأهداف تموت في يناير؟",
        # وعد
        "في الـ 60 ثانية القادمة... ستتعلم سراً",
        "سأكشف لك خطأً تفعله يومياً",
        "قاعدة واحدة ستوفر لك سنوات...",
        # محدد
        "3 عادات صباحية تستخدمها أنجح 1%",
        "5 جمل تجعل أي شخص يحبك",
        "7 إشارات أن وقتك ينفد",
        # تحذير
        "إذا فعلت X في الصباح... أنت في خطر",
        "هذه الإشارة تعني أن جسدك يصرخ",
        "5 علامات أنك على وشك الانهيار",
    )

    # ─── أمثلة قوية ─────────────────────────────────────────────────
    POWERFUL_EXAMPLES: tuple[str, ...] = (
        "قاعدة الدقيقتين: إذا كان الأمر يستغرق دقيقتين... افعله الآن.",
        "قاعدة 90/10: حياتك 10% أحداث... 90% ردة فعلك.",
        "قاعدة 5 ثوانٍ: عُدّ من 5... ثم تحرك. لا تفكّر.",
        "تستهلك يومياً 35,000 قرار... معظمها بدون وعي.",
        "دماغك يحتاج 66 يوماً لبناء عادة جديدة.",
        "1% تحسّن يومي = 37x أفضل بعد سنة.",
        "اكتب 3 أهداف فقط لليوم... لا أكثر.",
        "اشرب 500ml ماء فور الاستيقاظ.",
        "ضع هاتفك في غرفة أخرى أثناء العمل.",
        "5 ساعات من النوم العميق > 8 ساعات متقطعة.",
        "20% من جهدك يحقق 80% من نتائجك.",
        "كل ساعة موبايل يومياً = 365 ساعة سنوياً.",
        "تشعر بالضيق صباحاً؟ نومك متقطع.",
        "تنسى دائماً؟ دماغك مرهق من الإشعارات.",
        "تشعر بالوحدة؟ علاقاتك سطحية، ليست قليلة.",
    )

    # ─── أنماط الأسلوب ─────────────────────────────────────────────
    MOOD_RULES: dict[str, str] = {
        "informative": "أسلوب معلوماتي مباشر يقدم القيمة فوراً.",
        "educational": "أسلوب تعليمي مع شرح واضح وأمثلة.",
        "scientific": "أسلوب علمي مع أبحاث وإحصائيات.",
        "practical": "أسلوب عملي مع خطوات قابلة للتطبيق.",
        "psychological": "أسلوب نفسي يفسّر السلوكيات.",
        "motivational": "أسلوب تحفيزي مدعوم بأدلة.",
        "philosophical": "أسلوب فلسفي عميق ومُلهم.",
        "story": "أسلوب قصصي بدرس مستفاد.",
    }

    # ─── أنواع المحتوى ─────────────────────────────────────────────
    CONTENT_TYPES: dict[str, dict] = {
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
    DURATION_PRESETS: dict[int, DurationConfig] = {
        30: DurationConfig(6, 8, 22, 30, 4, 8),
        45: DurationConfig(8, 11, 35, 45, 4, 9),
        60: DurationConfig(10, 14, 48, 60, 5, 10),
    }
    
    DEFAULT_DURATION = 45

    # ═══════════════════════════════════════════════════════════════
    # Initialization
    # ═══════════════════════════════════════════════════════════════
    def __init__(self, seed: Optional[int] = None):
        """
        تهيئة المحرك.
        
        Args:
            seed: قيمة عشوائية ثابتة للاختبارات (اختياري)
        """
        if seed is not None:
            random.seed(seed)
            logger.info(f"PromptEngine initialized with seed={seed}")
        else:
            logger.info("PromptEngine initialized")

    # ═══════════════════════════════════════════════════════════════
    # Validation Methods
    # ═══════════════════════════════════════════════════════════════
    def _validate_topic(self, topic: str) -> str:
        """التحقق من صحة الموضوع."""
        if not topic or not topic.strip():
            raise ValueError("الموضوع لا يمكن أن يكون فارغاً")
        
        topic = topic.strip()
        if len(topic) < 3:
            raise ValueError("الموضوع قصير جداً (الحد الأدنى 3 أحرف)")
        if len(topic) > 200:
            raise ValueError("الموضوع طويل جداً (الحد الأقصى 200 حرف)")
        
        return topic

    def _validate_duration(self, duration: int) -> int:
        """التحقق من صحة المدة."""
        if duration not in self.DURATION_PRESETS:
            available = list(self.DURATION_PRESETS.keys())
            logger.warning(
                f"المدة {duration} غير مدعومة. "
                f"المتاح: {available}. استخدام {self.DEFAULT_DURATION}"
            )
            return self.DEFAULT_DURATION
        return duration

    def _validate_mood(self, mood: str) -> str:
        """التحقق من صحة الـ mood."""
        if mood not in self.MOOD_RULES:
            logger.warning(f"Mood '{mood}' غير معروف. استخدام 'practical'")
            return "practical"
        return mood

    def _validate_content_type(self, content_type: str) -> str:
        """التحقق من صحة نوع المحتوى."""
        if content_type not in self.CONTENT_TYPES:
            logger.warning(
                f"Content type '{content_type}' غير معروف. "
                f"استخدام 'motivational'"
            )
            return "motivational"
        return content_type

    # ═══════════════════════════════════════════════════════════════
    # Helper Methods
    # ═══════════════════════════════════════════════════════════════
    def _format_bullet_list(self, items: list[str], indent: str = "  ") -> str:
        """تنسيق قائمة كنقاط."""
        return "\n".join(f"{indent}• {item}" for item in items)

    def _get_random_sample(self, source: tuple, count: int) -> list:
        """اختيار عناصر عشوائية بأمان."""
        actual_count = min(count, len(source))
        return random.sample(source, actual_count)

    # ═══════════════════════════════════════════════════════════════
    # Main Prompt Builder
    # ═══════════════════════════════════════════════════════════════
    def build_script_prompt(
        self,
        topic: str,
        mood: str = "practical",
        content_type: ContentType = "motivational",
        target_duration: int = 45,
    ) -> str:
        """
        بناء prompt لإنتاج سكربت فيديو قيّم.
        
        Args:
            topic: موضوع الفيديو
            mood: أسلوب المحتوى
            content_type: نوع المحتوى
            target_duration: المدة المستهدفة (30/45/60)
        
        Returns:
            نص الـ prompt جاهز للإرسال للـ AI
        
        Raises:
            ValueError: إذا كان الموضوع فارغاً أو غير صالح
        """
        # ── Validation ──
        topic = self._validate_topic(topic)
        target_duration = self._validate_duration(target_duration)
        mood = self._validate_mood(mood)
        content_type = self._validate_content_type(content_type)
        
        logger.debug(
            f"Building prompt: topic='{topic[:30]}...', "
            f"mood={mood}, type={content_type}, duration={target_duration}s"
        )

        # ── إعدادات المدة ──
        duration_cfg = self.DURATION_PRESETS[target_duration]
        min_total_words, max_total_words = duration_cfg.total_words_range
        total_words_range = f"{min_total_words}-{max_total_words}"

        # ── اختيار framework ──
        content_cfg = self.CONTENT_TYPES[content_type]
        framework_name = random.choice(content_cfg["frameworks"])
        framework = self.VALUE_FRAMEWORKS[framework_name]

        # ── تجميع العناصر ──
        mood_instruction = self.MOOD_RULES[mood]
        examples_str = self._format_bullet_list(
            self._get_random_sample(
                self.POWERFUL_EXAMPLES,
                PromptConstants.POWERFUL_EXAMPLES_COUNT
            )
        )
        value_types_str = self._format_bullet_list(
            self._get_random_sample(
                self.VALUE_TYPES,
                PromptConstants.VALUE_TYPES_COUNT
            )
        )
        hooks_str = self._format_bullet_list(
            self._get_random_sample(
                self.VALUE_HOOKS,
                PromptConstants.HOOKS_COUNT
            )
        )
        framework_examples_str = self._format_bullet_list(framework.examples)
        
        # seed للتنويع
        seed = random.randint(
            PromptConstants.SEED_MIN,
            PromptConstants.SEED_MAX
        )

        # ── بناء الـ prompt ──
        return self._construct_prompt(
            topic=topic,
            mood=mood,
            mood_instruction=mood_instruction,
            content_type=content_type,
            framework=framework,
            framework_name=framework_name,
            framework_examples_str=framework_examples_str,
            duration_cfg=duration_cfg,
            target_duration=target_duration,
            total_words_range=total_words_range,
            min_total_words=min_total_words,
            max_total_words=max_total_words,
            examples_str=examples_str,
            value_types_str=value_types_str,
            hooks_str=hooks_str,
            seed=seed,
        )

    def _construct_prompt(
        self,
        topic: str,
        mood: str,
        mood_instruction: str,
        content_type: str,
        framework: Framework,
        framework_name: str,
        framework_examples_str: str,
        duration_cfg: DurationConfig,
        target_duration: int,
        total_words_range: str,
        min_total_words: int,
        max_total_words: int,
        examples_str: str,
        value_types_str: str,
        hooks_str: str,
        seed: int,
    ) -> str:
        """بناء النص الكامل للـ prompt (منفصل لسهولة الصيانة)."""
        
        return f"""أنت خبير محتوى تعليمي عربي محترف، متخصص في صناعة فيديوهات Shorts تُقدم قيمة حقيقية للمشاهد.

[seed: {seed}]

{PromptConstants.SEPARATOR}
🎯 المهمة الأساسية
{PromptConstants.SEPARATOR}

اكتب سكربت فيديو **يعلّم المشاهد شيئاً مفيداً** عن:

📌 الموضوع: "{topic}"
🎭 النوع: {content_type}
🎨 الأسلوب: {mood} - {mood_instruction}
🏗️ الإطار: {framework.name} - {framework.structure}

{PromptConstants.SEPARATOR}
💎 ⚠️ القاعدة الذهبية ⚠️
{PromptConstants.SEPARATOR}

❌ **ممنوع:** كلام عام ووعظ بدون قيمة
✅ **مطلوب:** معلومة محددة + قابلة للتطبيق

كل مشهد يجب أن يحتوي **واحدة من هذه:**

{value_types_str}

{PromptConstants.SEPARATOR}
🏗️ البنية المطلوبة (Framework)
{PromptConstants.SEPARATOR}

استخدم بنية: **{framework.name}**
{framework.structure}

أمثلة على عناوين هذا الإطار:
{framework_examples_str}

{PromptConstants.SEPARATOR}
📏 المواصفات الفنية
{PromptConstants.SEPARATOR}

1️⃣ **اللغة:**
   ✓ عربية فصحى بسيطة وواضحة
   ✓ مصطلحات يفهمها العامة
   ✓ بدون تعقيد لغوي

2️⃣ **المدة:** {target_duration} ثانية بالضبط
   ✓ عدد الكلمات الإجمالي: {total_words_range} كلمة (مهم جداً!)
   ✓ كل مشهد: {duration_cfg.min_words_per_scene}-{duration_cfg.max_words_per_scene} كلمات

3️⃣ **عدد المشاهد:** {duration_cfg.min_scenes}-{duration_cfg.max_scenes} مشهد

4️⃣ **الإيقاع:**
   ✓ "..." للتوقف الدراماتيكي (3-5 مرات)
   ✓ "!" للتأكيد (3-5 مرات)
   ✓ ":" قبل النقاط الرقمية

5️⃣ **البنية:**
   • Scene 1: HOOK + Promise (يعد بقيمة محددة)
   • Scenes 2-3: المعلومة الرئيسية + الدليل
   • Scenes 4-{duration_cfg.max_scenes-1}: التفاصيل والأمثلة
   • Last Scene: ملخص + CTA يطلب تطبيق

{PromptConstants.SEPARATOR}
⚠️⚠️⚠️ تحذير صارم عن عدد الكلمات ⚠️⚠️⚠️
{PromptConstants.SEPARATOR}

يجب أن يحتوي النص الكامل (full_text) على {total_words_range} كلمة بالضبط!

حساب تقريبي:
- كل ثانية = ~2.5 كلمة
- {target_duration} ثانية = {total_words_range} كلمة

❌ أقل من {min_total_words} كلمة = الفيديو قصير جداً!
❌ أكثر من {max_total_words} كلمة = الفيديو طويل جداً!

{PromptConstants.SEPARATOR}
✅ مطلوب بقوة (Must Have)
{PromptConstants.SEPARATOR}

✓ **رقم محدد على الأقل** (مثل: 5 خطوات، 21 يوم، 80%)
✓ **مثال واقعي على الأقل** (شخصية، شركة، حالة)
✓ **نصيحة قابلة للتطبيق فوراً** (Actionable)
✓ **سبب علمي/منطقي** للنصائح
✓ **خاتمة تحفّز على التطبيق**

{PromptConstants.SEPARATOR}
🚫 ممنوع تماماً
{PromptConstants.SEPARATOR}

❌ كلام عام مثل "كن قوياً" بدون شرح كيف
❌ نصائح فضفاضة "اعمل بجد"
❌ وعظ مباشر "يجب عليك..."
❌ تكرار نفس الفكرة بصياغات مختلفة
❌ معلومات مكررة في كل فيديو
❌ نصائح لا يمكن تطبيقها فوراً

{PromptConstants.SEPARATOR}
💡 أمثلة على المحتوى المطلوب
{PromptConstants.SEPARATOR}

{examples_str}

{PromptConstants.SEPARATOR}
🔥 Hooks قيّمة (للإلهام)
{PromptConstants.SEPARATOR}

{hooks_str}

{PromptConstants.SEPARATOR}
📊 مقارنة: محتوى ضعيف vs قيّم
{PromptConstants.SEPARATOR}

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

{PromptConstants.SEPARATOR}
🎬 تعليمات تقنية لكل مشهد
{PromptConstants.SEPARATOR}

لكل مشهد أضف:
• visual_prompt: وصف سينمائي بالإنجليزية
• camera_motion: slow_zoom / fast_push / cinematic_pan / static
• voice_tone: intense / calm / authoritative / curious / powerful
• transition: smooth_fade / cinematic_flash / cross_dissolve
• energy: 0.6-1.0
• music_intensity: 0.5-0.9

{PromptConstants.SEPARATOR}
⚠️ قواعد JSON
{PromptConstants.SEPARATOR}

✓ JSON صالح فقط
✓ بدون markdown أو ```json
✓ كل المشاهد فريدة
✓ التوقيتات منطقية

{PromptConstants.SEPARATOR}
📋 صيغة JSON
{PromptConstants.SEPARATOR}

{{
  "title": "عنوان قيّم محدد",
  "hook": "Hook يعد بقيمة محددة...",
  "mood": "{mood}",
  "content_type": "{content_type}",
  "framework": "{framework_name}",
  "duration_estimate": {duration_cfg.avg_duration:.1f},
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

{PromptConstants.SEPARATOR}
🎯 الآن اكتب السكربت
{PromptConstants.SEPARATOR}

تذكّر: المشاهد يجب أن يقول في النهاية:
"تعلمت شيئاً مفيداً!"

ليس فقط:
"كان فيديو جميل"

اكتب الآن - JSON فقط."""

    # ═══════════════════════════════════════════════════════════════
    # Additional Prompts
    # ═══════════════════════════════════════════════════════════════
    def build_hook_variants_prompt(
        self,
        topic: str,
        count: int = 5,
        mood: str = "practical",
    ) -> str:
        """توليد Hooks قيّمة متعددة."""
        topic = self._validate_topic(topic)
        count = max(1, min(count, 20))  # حد بين 1-20
        
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
        topic = self._validate_topic(topic)
        count = max(1, min(count, 30))
        
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
        topic = self._validate_topic(topic)
        count = max(1, min(count, 30))
        
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

    def build_visual_prompt(
        self,
        scene_text: str,
        mood: str = "practical"
    ) -> str:
        """تحويل نص لوصف سينمائي."""
        if not scene_text or not scene_text.strip():
            raise ValueError("نص المشهد لا يمكن أن يكون فارغاً")
        
        mood = self._validate_mood(mood)
        
        return f"""حوّل النص العربي إلى وصف سينمائي بالإنجليزية:

📌 النص: "{scene_text.strip()}"
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
        topic = self._validate_topic(topic)
        count = max(1, min(count, 30))
        
        return f"""أنشئ {count} هاشتاجات لفيديو تعليمي عن: "{topic}"

✓ مزيج عربي + إنجليزي
✓ تتضمن: #fyp #foryou
✓ مرتبطة بالموضوع

⚠️ JSON array فقط.
"""

    # ═══════════════════════════════════════════════════════════════
    # Public Utility Methods
    # ═══════════════════════════════════════════════════════════════
    def get_mood_for_content(self, content_type: str) -> str:
        """الحصول على mood افتراضي للنوع."""
        content_type = self._validate_content_type(content_type)
        return self.CONTENT_TYPES[content_type]["default_mood"]

    def get_random_mood(self) -> str:
        """اختيار mood عشوائي."""
        return random.choice(list(self.MOOD_RULES.keys()))

    def get_random_framework(
        self,
        content_type: str = "motivational"
    ) -> Framework:
        """اختيار framework عشوائي مناسب للنوع."""
        content_type = self._validate_content_type(content_type)
        content_cfg = self.CONTENT_TYPES[content_type]
        framework_name = random.choice(content_cfg["frameworks"])
        return self.VALUE_FRAMEWORKS[framework_name]

    def list_available_moods(self) -> list[str]:
        """قائمة الـ moods المتاحة."""
        return list(self.MOOD_RULES.keys())

    def list_content_types(self) -> list[str]:
        """قائمة أنواع المحتوى المتاحة."""
        return list(self.CONTENT_TYPES.keys())

    def list_frameworks(self) -> dict[str, Framework]:
        """قائمة جميع الـ frameworks."""
        return self.VALUE_FRAMEWORKS.copy()
    
    def get_duration_info(self, duration: int) -> Optional[DurationConfig]:
        """الحصول على معلومات مدة معينة."""
        return self.DURATION_PRESETS.get(duration)


# ═══════════════════════════════════════════════════════════════════
# اختبار سريع
# ═══════════════════════════════════════════════════════════════════
if __name__ == "__main__":
    # إعداد logging للاختبار
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s | %(levelname)s | %(message)s"
    )
    
    engine = PromptEngine()
    
    print("✅ Value-Driven Prompt Engine v4.1 جاهز")
    print(f"\n📊 المحتوى:")
    print(f"   • Frameworks: {len(engine.VALUE_FRAMEWORKS)}")
    print(f"   • Content Types: {len(engine.CONTENT_TYPES)}")
    print(f"   • Value Hooks: {len(engine.VALUE_HOOKS)}")
    print(f"   • Powerful Examples: {len(engine.POWERFUL_EXAMPLES)}")
    print(f"   • Duration Presets: {list(engine.DURATION_PRESETS.keys())}")
    
    print(f"\n🏗️ Frameworks المتاحة:")
    for name, framework in engine.VALUE_FRAMEWORKS.items():
        print(f"   • {name}: {framework.name}")
    
    print(f"\n💡 مثال على Hook قيّم:")
    print(f"   {random.choice(engine.VALUE_HOOKS)}")
    
    # اختبار بناء prompt
    print(f"\n🧪 اختبار بناء prompt...")
    try:
        prompt = engine.build_script_prompt(
            topic="كيف تتعلم بسرعة",
            mood="scientific",
            content_type="educational",
            target_duration=45,
        )
        print(f"   ✅ تم بناء prompt بنجاح ({len(prompt)} حرف)")
    except Exception as e:
        print(f"   ❌ فشل: {e}")
    
    # اختبار validation
    print(f"\n🧪 اختبار validation...")
    try:
        engine.build_script_prompt(topic="")
    except ValueError as e:
        print(f"   ✅ Validation يعمل: {e}")
