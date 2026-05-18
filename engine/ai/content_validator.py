"""
🎯 Content Validator v2.0 — نظام التحقق الشامل من المحتوى
═══════════════════════════════════════════════════════════════
3 أنظمة تحقق متكاملة:

1. 📝 TextValidator: جودة النص والمحتوى
2. 🎙️ AudioValidator: تطابق الصوت مع النص
3. ⏱️ DurationController: ضبط المدة بدقة

التحسينات في v2.0:
  ✓ Dataclasses للنتائج (type-safe)
  ✓ Scoring weights قابلة للتخصيص
  ✓ Banned words detection
  ✓ Export to JSON/HTML
  ✓ FFprobe fallback
  ✓ تنظيف النص قبل الفحص
  ✓ كشف CTA أذكى (regex)
  ✓ Hook detection محسّن
═══════════════════════════════════════════════════════════════
"""

from __future__ import annotations

import re
import json
import shutil
import logging
import subprocess
from pathlib import Path
from enum import Enum
from dataclasses import dataclass, field, asdict
from typing import Optional, Any

logger = logging.getLogger(__name__)


# ═══════════════════════════════════════════════════════════════════
# Enums & Types
# ═══════════════════════════════════════════════════════════════════
class ValidationAction(str, Enum):
    """الإجراءات المقترحة بعد الفحص."""
    OK = "OK"
    RETRY_WITH_CHUNKS = "RETRY_WITH_CHUNKS"
    REGENERATE = "REGENERATE"
    MANUAL_REVIEW = "MANUAL_REVIEW"


class QualityLevel(str, Enum):
    """مستوى الجودة."""
    EXCELLENT = "excellent"  # 80+
    GOOD = "good"           # 60-79
    POOR = "poor"           # < 60
    
    @classmethod
    def from_score(cls, score: float) -> "QualityLevel":
        if score >= 80:
            return cls.EXCELLENT
        elif score >= 60:
            return cls.GOOD
        return cls.POOR
    
    @property
    def emoji(self) -> str:
        return {
            self.EXCELLENT: "✅ ممتاز",
            self.GOOD: "⚠ مقبول",
            self.POOR: "❌ ضعيف",
        }[self]


# ═══════════════════════════════════════════════════════════════════
# Result Dataclasses
# ═══════════════════════════════════════════════════════════════════
@dataclass
class ValidationStats:
    """إحصائيات الفحص."""
    word_count: int = 0
    scene_count: int = 0
    target_duration: int = 0
    hook_score: int = 0
    value_indicators: int = 0
    has_cta: bool = False
    avg_words_per_scene: float = 0.0
    estimated_duration: float = 0.0


@dataclass
class TextValidationResult:
    """نتيجة فحص النص."""
    valid: bool
    score: int
    issues: list[str] = field(default_factory=list)
    suggestions: list[str] = field(default_factory=list)
    stats: ValidationStats = field(default_factory=ValidationStats)
    quality: QualityLevel = QualityLevel.POOR
    
    def to_dict(self) -> dict:
        d = asdict(self)
        d["quality"] = self.quality.value
        return d


@dataclass
class AudioValidationResult:
    """نتيجة فحص الصوت."""
    valid: bool
    issues: list[str] = field(default_factory=list)
    audio_duration: float = 0.0
    expected_duration: float = 0.0
    word_count: int = 0
    coverage_percent: float = 0.0
    action: ValidationAction = ValidationAction.OK
    
    def to_dict(self) -> dict:
        d = asdict(self)
        d["action"] = self.action.value
        return d


@dataclass
class DurationValidationResult:
    """نتيجة فحص المدة."""
    valid: bool
    issues: list[str] = field(default_factory=list)
    word_count: int = 0
    scene_count: int = 0
    target_duration: int = 0
    estimated_duration: float = 0.0
    specs: dict = field(default_factory=dict)


@dataclass
class FullValidationResult:
    """نتيجة الفحص الشامل."""
    valid: bool
    score: int
    quality: QualityLevel
    text_result: TextValidationResult
    duration_result: DurationValidationResult
    all_issues: list[str] = field(default_factory=list)
    
    def to_dict(self) -> dict:
        return {
            "valid": self.valid,
            "score": self.score,
            "quality": self.quality.value,
            "text_result": self.text_result.to_dict(),
            "duration_result": asdict(self.duration_result),
            "all_issues": self.all_issues,
        }
    
    def to_json(self, indent: int = 2) -> str:
        return json.dumps(self.to_dict(), indent=indent, ensure_ascii=False)


# ═══════════════════════════════════════════════════════════════════
# Configuration (قابل للتخصيص)
# ═══════════════════════════════════════════════════════════════════
@dataclass
class ScoringWeights:
    """أوزان التقييم (قابلة للتخصيص)."""
    text_too_short: int = 30
    text_too_long: int = 10
    few_scenes: int = 15
    weak_hook: int = 20
    no_value: int = 25
    low_value: int = 5
    repetition: int = 10
    no_cta: int = 5
    long_sentences: int = 5
    banned_words: int = 30


# ═══════════════════════════════════════════════════════════════════
# Constants
# ═══════════════════════════════════════════════════════════════════
class ValidatorConstants:
    """الثوابت."""
    
    # معدلات الكلام بالعربية
    ARABIC_WPM_MIN = 120
    ARABIC_WPM_MAX = 180
    ARABIC_WPM_NORMAL = 150
    
    # حدود الجودة
    MIN_PASSING_SCORE = 60
    MAX_SCENE_WORDS = 12
    
    # حدود الصوت
    AUDIO_MIN_COVERAGE = 50  # %
    AUDIO_MAX_COVERAGE = 150  # %
    
    # FFprobe
    FFPROBE_TIMEOUT = 30


# ─── معايير الطول حسب المدة ─────────────────────────────────────
DURATION_SPECS: dict[int, dict] = {
    30: {
        "min_words": 25, "max_words": 85, "ideal_words": 70,
        "min_scenes": 5, "max_scenes": 8, "ideal_scenes": 6,
        "words_per_scene": (7, 12),
        "description": "قصير وسريع - TikTok style",
    },
    45: {
        "min_words": 40, "max_words": 130, "ideal_words": 105,
        "min_scenes": 7, "max_scenes": 12, "ideal_scenes": 9,
        "words_per_scene": (8, 14),
        "description": "متوسط - متوازن",
    },
    60: {
        "min_words": 50, "max_words": 170, "ideal_words": 145,
        "min_scenes": 9, "max_scenes": 15, "ideal_scenes": 12,
        "words_per_scene": (8, 14),
        "description": "طويل - تفصيلي",
    },
}

# ─── مؤشرات القيمة (regex patterns + keywords) ───────────────────
VALUE_REGEX_PATTERNS: tuple[str, ...] = (
    r'\d+%',
    r'\d+\s*(ثانية|دقيقة|ساعة|يوم|أسبوع|شهر|سنة)',
    r'\d+x',  # مثل: 10x
    r'\d+/\d+',  # مثل: 80/20
)

VALUE_KEYWORDS: frozenset[str] = frozenset({
    'قاعدة', 'خطوة', 'نصيحة', 'سر',
    'دراسة', 'بحث', 'علمي', 'اكتشف', 'تعلم', 'حقيقة',
    'طريقة', 'كيف', 'لماذا', 'السبب', 'الحل',
    'نتيجة', 'فائدة', 'تأثير', 'تغيير',
})

# ─── كلمات الـ Hook القوي ────────────────────────────────────────
HOOK_KEYWORDS: frozenset[str] = frozenset({
    'توقف', 'انتظر', 'احذر', 'هل تعلم', 'هل سألت',
    'سر', 'حقيقة', 'خطأ', 'خطير', 'صادم', 'مذهل',
})

HOOK_PUNCTUATION: tuple[str, ...] = ('!', '?', '؟', '...', '%')

# ─── كلمات CTA حقيقية ────────────────────────────────────────────
CTA_PATTERNS: tuple[str, ...] = (
    r'\bشارك\b', r'\bاشترك\b', r'\bتابع\b', r'\bتابعنا\b',
    r'\bعلّق\b', r'\bعلق\b', r'\bاكتب\b',
    r'\bاحفظ\b', r'\bطبّق\b', r'\bطبق\b',
    r'\bجرّب\b', r'\bجرب\b', r'\bفعّل\b',
    r'\bأخبرنا\b',
)

# ─── كلمات الحشو ─────────────────────────────────────────────────
FILLER_PHRASES: tuple[str, ...] = (
    'جداً جداً', 'بشكل كبير جداً', 'في الحقيقة',
    'كما تعلمون', 'بالطبع', 'طبعاً',
)

# ─── كلمات ممنوعة (يمكن توسيعها) ─────────────────────────────────
BANNED_WORDS: frozenset[str] = frozenset({
    # كلمات تسيء للمحتوى التعليمي
    # يمكنك إضافة المزيد حسب حاجتك
})


# ═══════════════════════════════════════════════════════════════════
# Helper Functions
# ═══════════════════════════════════════════════════════════════════
def clean_text(text: str) -> str:
    """تنظيف النص قبل الفحص."""
    if not isinstance(text, str):
        return ""
    
    # إزالة BOM و RTL/LTR markers
    for ch in ("\u200f", "\u200e", "\ufeff"):
        text = text.replace(ch, "")
    
    # إزالة tatweel
    text = re.sub(r"[ـ]+", "", text)
    # توحيد المسافات
    text = re.sub(r"\s+", " ", text)
    
    return text.strip()


def count_words(text: str) -> int:
    """عدّ الكلمات بشكل صحيح."""
    if not text:
        return 0
    return len(clean_text(text).split())


def check_ffprobe_available() -> bool:
    """التحقق من توفر ffprobe."""
    return shutil.which("ffprobe") is not None


# ════════════════════════════════════════════════════════════════════
# 📝 نظام 1: التحقق من جودة النص
# ════════════════════════════════════════════════════════════════════
class TextValidator:
    """التحقق من جودة النص."""

    def __init__(self, weights: Optional[ScoringWeights] = None):
        self.weights = weights or ScoringWeights()

    def validate(
        self,
        script: dict,
        target_duration: int = 45,
    ) -> TextValidationResult:
        """الفحص الشامل للنص."""
        scenes = script.get("scenes", [])
        hook_text_from_script = clean_text(script.get("hook", ""))
        
        # استخراج النصوص المنظفة
        all_texts = [
            clean_text(s.get("text", ""))
            for s in scenes
            if s.get("text")
        ]
        all_texts = [t for t in all_texts if t]
        full_text = " ".join(all_texts)
        word_count = count_words(full_text)
        scene_count = len(scenes)
        
        logger.info(
            f"📝 فحص النص: {word_count} كلمة، {scene_count} مشهد"
        )
        
        # ── إعداد النتيجة ──
        result = TextValidationResult(
            valid=False,
            score=100,
            stats=ValidationStats(
                word_count=word_count,
                scene_count=scene_count,
                target_duration=target_duration,
                avg_words_per_scene=(
                    word_count / scene_count if scene_count else 0
                ),
                estimated_duration=(word_count / 150) * 60,
            ),
        )
        
        # تشغيل الفحوصات
        specs = DURATION_SPECS.get(target_duration, DURATION_SPECS[45])
        
        self._check_length(result, word_count, scene_count, specs)
        self._check_hook(result, all_texts, hook_text_from_script)
        self._check_value(result, full_text)
        self._check_repetition(result, all_texts)
        self._check_cta(result, all_texts)
        self._check_sentence_length(result, scenes)
        self._check_banned_words(result, full_text)
        
        # حساب النتيجة النهائية
        result.score = max(0, min(100, result.score))
        result.quality = QualityLevel.from_score(result.score)
        result.valid = result.score >= ValidatorConstants.MIN_PASSING_SCORE
        
        # طباعة النتيجة
        logger.info(
            f"📊 نتيجة فحص النص: {result.score}/100 "
            f"({result.quality.emoji})"
        )
        for issue in result.issues:
            logger.warning(f"   {issue}")
        for suggestion in result.suggestions:
            logger.info(f"   {suggestion}")
        
        return result

    # ── فحوصات فردية ──
    def _check_length(
        self,
        result: TextValidationResult,
        word_count: int,
        scene_count: int,
        specs: dict,
    ):
        """فحص الطول."""
        if word_count < specs["min_words"]:
            result.issues.append(
                f"❌ النص قصير جداً: {word_count} كلمة "
                f"(المطلوب: {specs['min_words']}-{specs['max_words']})"
            )
            result.score -= self.weights.text_too_short
        elif word_count > specs["max_words"]:
            result.issues.append(
                f"⚠ النص طويل: {word_count} كلمة "
                f"(المطلوب: {specs['min_words']}-{specs['max_words']})"
            )
            result.score -= self.weights.text_too_long
        
        if scene_count < specs["min_scenes"]:
            result.issues.append(
                f"⚠ مشاهد قليلة: {scene_count} "
                f"(المطلوب: {specs['min_scenes']}-{specs['max_scenes']})"
            )
            result.score -= self.weights.few_scenes

    def _check_hook(
        self,
        result: TextValidationResult,
        all_texts: list[str],
        fallback_hook: str,
    ):
        """فحص الـ Hook."""
        hook_text = all_texts[0] if all_texts else fallback_hook
        hook_score = self._calculate_hook_score(hook_text)
        result.stats.hook_score = hook_score
        
        if hook_score < 3:
            result.issues.append("❌ الـ Hook ضعيف! لن يوقف المشاهد عن التمرير")
            result.suggestions.append(
                "💡 ابدأ بسؤال صادم أو إحصائية أو تحذير"
            )
            result.score -= self.weights.weak_hook

    def _calculate_hook_score(self, hook_text: str) -> int:
        """حساب نقاط الـ Hook (0-5)."""
        if not hook_text:
            return 0
        
        score = 0
        text_lower = hook_text.lower()
        
        # كلمات الـ Hook
        for keyword in HOOK_KEYWORDS:
            if keyword in text_lower:
                score += 1
                break  # نقطة واحدة فقط للكلمات
        
        # علامات الترقيم
        for punct in HOOK_PUNCTUATION:
            if punct in hook_text:
                score += 1
                break
        
        # أرقام أو إحصائيات
        if re.search(r'\d+', hook_text):
            score += 1
        
        # طول مناسب
        if len(hook_text.split()) <= 10:
            score += 1
        
        # سؤال
        if any(q in hook_text for q in ['؟', '?', 'هل', 'لماذا', 'كيف']):
            score += 1
        
        return min(score, 5)

    def _check_value(self, result: TextValidationResult, full_text: str):
        """فحص القيمة المقدمة."""
        value_count = self._count_value_indicators(full_text)
        result.stats.value_indicators = value_count
        
        if value_count < 2:
            result.issues.append("❌ النص لا يقدم قيمة كافية!")
            result.suggestions.append(
                "💡 أضف أرقام، إحصائيات، نصائح عملية"
            )
            result.score -= self.weights.no_value
        elif value_count < 4:
            result.suggestions.append(
                "💡 يمكن إضافة المزيد من الأرقام والحقائق"
            )
            result.score -= self.weights.low_value

    def _count_value_indicators(self, text: str) -> int:
        """عدّ مؤشرات القيمة."""
        count = 0
        
        # Regex patterns
        for pattern in VALUE_REGEX_PATTERNS:
            if re.search(pattern, text):
                count += 1
        
        # Keywords (أسرع من regex)
        for keyword in VALUE_KEYWORDS:
            if keyword in text:
                count += 1
        
        return count

    def _check_repetition(
        self,
        result: TextValidationResult,
        texts: list[str],
    ):
        """فحص التكرار."""
        repeated = self._find_repeated_phrases(texts)
        if repeated:
            result.issues.append(
                f"⚠ تكرار في النص: {', '.join(list(repeated)[:3])}"
            )
            result.score -= self.weights.repetition

    def _find_repeated_phrases(
        self,
        texts: list[str],
        min_length: int = 3,
        min_chars: int = 10,
    ) -> set[str]:
        """البحث عن العبارات المكررة."""
        all_phrases: dict[str, int] = {}
        
        for text in texts:
            words = text.split()
            for i in range(len(words) - min_length + 1):
                phrase = " ".join(words[i:i + min_length])
                if len(phrase) > min_chars:
                    all_phrases[phrase] = all_phrases.get(phrase, 0) + 1
        
        return {p for p, count in all_phrases.items() if count > 1}

    def _check_cta(
        self,
        result: TextValidationResult,
        all_texts: list[str],
    ):
        """فحص الـ CTA (في آخر مشهدين)."""
        if not all_texts:
            return
        
        # فحص آخر مشهدين
        last_texts = " ".join(all_texts[-2:])
        has_cta = any(
            re.search(pattern, last_texts)
            for pattern in CTA_PATTERNS
        )
        result.stats.has_cta = has_cta
        
        if not has_cta:
            result.suggestions.append(
                "💡 أضف CTA في نهاية الفيديو (شارك، اشترك، طبّق)"
            )
            result.score -= self.weights.no_cta

    def _check_sentence_length(
        self,
        result: TextValidationResult,
        scenes: list,
    ):
        """فحص طول الجمل."""
        long_scenes = [
            i for i, s in enumerate(scenes)
            if count_words(s.get("text", "")) > ValidatorConstants.MAX_SCENE_WORDS
        ]
        
        if long_scenes:
            result.issues.append(
                f"⚠ جمل طويلة في المشاهد: {long_scenes[:3]} "
                f"(حد أقصى {ValidatorConstants.MAX_SCENE_WORDS} كلمة)"
            )
            result.score -= self.weights.long_sentences

    def _check_banned_words(
        self,
        result: TextValidationResult,
        full_text: str,
    ):
        """فحص الكلمات الممنوعة."""
        if not BANNED_WORDS:
            return
        
        text_lower = full_text.lower()
        found = [w for w in BANNED_WORDS if w in text_lower]
        
        if found:
            result.issues.append(
                f"❌ كلمات ممنوعة: {', '.join(found[:3])}"
            )
            result.score -= self.weights.banned_words


# ════════════════════════════════════════════════════════════════════
# 🎙️ نظام 2: التحقق من تطابق الصوت
# ════════════════════════════════════════════════════════════════════
class AudioValidator:
    """التحقق من تطابق الصوت مع النص."""

    def __init__(self):
        self._ffprobe_available = check_ffprobe_available()
        if not self._ffprobe_available:
            logger.warning(
                "⚠ ffprobe غير مثبت. "
                "فحص الصوت سيكون غير دقيق."
            )

    def validate(
        self,
        audio_path: str,
        original_text: str,
        target_duration: int = 45,
    ) -> AudioValidationResult:
        """التحقق من الصوت."""
        result = AudioValidationResult(
            valid=False,
            word_count=count_words(original_text),
        )
        
        # ── فحص وجود الملف ──
        if not Path(audio_path).exists():
            result.issues.append(f"❌ ملف الصوت غير موجود: {audio_path}")
            result.action = ValidationAction.REGENERATE
            return result
        
        # ── قياس المدة ──
        audio_duration = self._get_duration(audio_path)
        result.audio_duration = round(audio_duration, 2)
        
        if audio_duration <= 0:
            result.issues.append("❌ فشل قياس مدة الصوت")
            result.action = ValidationAction.REGENERATE
            return result
        
        # ── حساب المدة المتوقعة ──
        expected_min = (result.word_count / ValidatorConstants.ARABIC_WPM_MAX) * 60
        expected_max = (result.word_count / ValidatorConstants.ARABIC_WPM_MIN) * 60
        expected_normal = (result.word_count / ValidatorConstants.ARABIC_WPM_NORMAL) * 60
        
        result.expected_duration = round(expected_normal, 2)
        
        logger.info(
            f"🎙️ فحص الصوت: {audio_duration:.1f}s فعلي | "
            f"{expected_normal:.1f}s متوقع | {result.word_count} كلمة"
        )
        
        # ── فحوصات ──
        # قصير جداً (فقدان نص)
        if audio_duration < expected_min * 0.5:
            result.issues.append(
                f"❌ الصوت قصير جداً! ({audio_duration:.1f}s) "
                f"المتوقع: {expected_min:.1f}-{expected_max:.1f}s"
            )
            result.issues.append("🔧 الحل: النص لم يتحول كاملاً، يجب تقسيمه")
            result.action = ValidationAction.RETRY_WITH_CHUNKS
        
        # طويل جداً (تكرار)
        elif audio_duration > expected_max * 1.5:
            result.issues.append(
                f"⚠ الصوت طويل جداً! ({audio_duration:.1f}s) "
                f"المتوقع: {expected_min:.1f}-{expected_max:.1f}s"
            )
            result.issues.append("🔧 قد يكون هناك تكرار في النص")
            result.action = ValidationAction.REGENERATE
        
        # ── حساب التغطية ──
        coverage = (audio_duration / expected_normal) * 100
        result.coverage_percent = round(coverage, 1)
        result.valid = (
            ValidatorConstants.AUDIO_MIN_COVERAGE
            <= coverage
            <= ValidatorConstants.AUDIO_MAX_COVERAGE
        )
        
        if result.valid:
            result.action = ValidationAction.OK
            logger.info(f"   ✅ الصوت مكتمل ({coverage:.0f}% تغطية)")
        else:
            logger.warning(f"   ⚠ تغطية الصوت: {coverage:.0f}%")
        
        return result

    def _get_duration(self, path: str) -> float:
        """قياس مدة الصوت."""
        if not self._ffprobe_available:
            return 0.0
        
        try:
            result = subprocess.run(
                [
                    "ffprobe", "-v", "quiet",
                    "-show_entries", "format=duration",
                    "-of", "default=noprint_wrappers=1:nokey=1",
                    path,
                ],
                capture_output=True,
                text=True,
                timeout=ValidatorConstants.FFPROBE_TIMEOUT,
                check=True,
            )
            return float(result.stdout.strip())
        except subprocess.TimeoutExpired:
            logger.error(f"⏱ FFprobe timeout for: {path}")
            return 0.0
        except (subprocess.CalledProcessError, ValueError) as e:
            logger.error(f"❌ FFprobe error: {e}")
            return 0.0


# ════════════════════════════════════════════════════════════════════
# ⏱️ نظام 3: التحكم في المدة
# ════════════════════════════════════════════════════════════════════
class DurationController:
    """ضبط طول النص بدقة حسب المدة."""

    def get_specs(self, target_duration: int) -> dict:
        """الحصول على المواصفات."""
        return DURATION_SPECS.get(target_duration, DURATION_SPECS[45])

    def validate(
        self,
        script: dict,
        target_duration: int,
    ) -> DurationValidationResult:
        """فحص المدة."""
        specs = self.get_specs(target_duration)
        
        scenes = script.get("scenes", [])
        all_texts = [
            clean_text(s.get("text", ""))
            for s in scenes
            if s.get("text")
        ]
        full_text = " ".join(t for t in all_texts if t)
        word_count = count_words(full_text)
        
        result = DurationValidationResult(
            valid=True,
            word_count=word_count,
            scene_count=len(scenes),
            target_duration=target_duration,
            estimated_duration=round((word_count / 150) * 60, 1),
            specs=specs,
        )
        
        # فحص الطول
        if word_count < specs["min_words"]:
            result.issues.append(
                f"❌ النص قصير لـ {target_duration}s: "
                f"{word_count} كلمة "
                f"(المطلوب: {specs['min_words']}-{specs['max_words']})"
            )
            result.valid = False
        elif word_count > specs["max_words"]:
            result.issues.append(
                f"⚠ النص طويل لـ {target_duration}s: "
                f"{word_count} كلمة "
                f"(المطلوب: {specs['min_words']}-{specs['max_words']})"
            )
            result.valid = False
        
        if len(scenes) < specs["min_scenes"]:
            result.issues.append(
                f"⚠ مشاهد قليلة: {len(scenes)} "
                f"(المطلوب: {specs['min_scenes']}-{specs['max_scenes']})"
            )
            result.valid = False
        
        status = "✅" if result.valid else "⚠"
        logger.info(
            f"⏱️ فحص المدة: {status} "
            f"{word_count} كلمة → ~{result.estimated_duration:.0f}s "
            f"(هدف: {target_duration}s)"
        )
        
        return result

    def get_duration_instruction(self, target_duration: int) -> str:
        """تعليمات المدة للـ Prompt."""
        specs = self.get_specs(target_duration)
        wps_min, wps_max = specs["words_per_scene"]
        
        return (
            f"⏱️ المدة المستهدفة: {target_duration} ثانية\n"
            f"📝 عدد الكلمات: {specs['min_words']}-{specs['max_words']} كلمة "
            f"(الأمثل: {specs['ideal_words']})\n"
            f"🎬 عدد المشاهد: {specs['min_scenes']}-{specs['max_scenes']} "
            f"(الأمثل: {specs['ideal_scenes']})\n"
            f"📏 كلمات لكل مشهد: {wps_min}-{wps_max}\n"
            f"📋 النوع: {specs['description']}"
        )


# ════════════════════════════════════════════════════════════════════
# 🎯 النظام الشامل
# ════════════════════════════════════════════════════════════════════
class ContentValidator:
    """النظام الشامل."""

    def __init__(self, weights: Optional[ScoringWeights] = None):
        self.text_validator = TextValidator(weights)
        self.audio_validator = AudioValidator()
        self.duration_controller = DurationController()
        
        logger.info("🎯 ContentValidator v2.0 جاهز")

    def validate_script(
        self,
        script: dict,
        target_duration: int,
    ) -> FullValidationResult:
        """فحص شامل للسكربت."""
        logger.info("=" * 50)
        logger.info("🎯 فحص شامل للسكربت...")
        logger.info("=" * 50)
        
        text_result = self.text_validator.validate(script, target_duration)
        duration_result = self.duration_controller.validate(script, target_duration)
        
        overall_valid = text_result.valid and duration_result.valid
        all_issues = text_result.issues + duration_result.issues
        
        full_result = FullValidationResult(
            valid=overall_valid,
            score=text_result.score,
            quality=text_result.quality,
            text_result=text_result,
            duration_result=duration_result,
            all_issues=all_issues,
        )
        
        if overall_valid:
            logger.info(
                f"✅ السكربت جاهز! (Score: {full_result.score}/100)"
            )
        else:
            logger.warning(
                f"⚠ السكربت يحتاج تحسين (Score: {full_result.score}/100)"
            )
            for issue in all_issues:
                logger.warning(f"   {issue}")
        
        return full_result

    def validate_audio(
        self,
        audio_path: str,
        original_text: str,
        target_duration: int,
    ) -> AudioValidationResult:
        """فحص الصوت."""
        logger.info("=" * 50)
        logger.info("🎙️ فحص شامل للصوت...")
        logger.info("=" * 50)
        
        return self.audio_validator.validate(
            audio_path, original_text, target_duration
        )

    def get_duration_specs(self, target_duration: int) -> dict:
        return self.duration_controller.get_specs(target_duration)

    def get_duration_instruction(self, target_duration: int) -> str:
        return self.duration_controller.get_duration_instruction(target_duration)

    # ── Export Methods ──
    def export_report(
        self,
        result: FullValidationResult,
        output_path: str,
        format: str = "json",
    ):
        """حفظ التقرير."""
        output = Path(output_path)
        output.parent.mkdir(parents=True, exist_ok=True)
        
        if format == "json":
            output.write_text(result.to_json(), encoding="utf-8")
        elif format == "html":
            output.write_text(self._to_html(result), encoding="utf-8")
        else:
            raise ValueError(f"Unsupported format: {format}")
        
        logger.info(f"📄 Report saved: {output}")

    def _to_html(self, result: FullValidationResult) -> str:
        """تحويل النتيجة لـ HTML."""
        color = {
            QualityLevel.EXCELLENT: "#22c55e",
            QualityLevel.GOOD: "#eab308",
            QualityLevel.POOR: "#ef4444",
        }[result.quality]
        
        issues_html = "".join(
            f"<li>{issue}</li>" for issue in result.all_issues
        ) or "<li>لا توجد مشاكل ✅</li>"
        
        return f"""<!DOCTYPE html>
<html dir="rtl" lang="ar">
<head>
<meta charset="UTF-8">
<title>Content Validation Report</title>
<style>
  body {{ font-family: Arial; padding: 2rem; background: #f5f5f5; }}
  .card {{ background: white; padding: 2rem; border-radius: 1rem;
          box-shadow: 0 4px 6px rgba(0,0,0,0.1); max-width: 800px; margin: 0 auto; }}
  .score {{ font-size: 4rem; font-weight: bold; color: {color}; }}
  h1 {{ color: #333; }}
  ul {{ line-height: 2; }}
</style>
</head>
<body>
<div class="card">
  <h1>🎯 تقرير فحص المحتوى</h1>
  <div class="score">{result.score}/100</div>
  <p><strong>الجودة:</strong> {result.quality.emoji}</p>
  <p><strong>الكلمات:</strong> {result.text_result.stats.word_count}</p>
  <p><strong>المشاهد:</strong> {result.text_result.stats.scene_count}</p>
  <h2>📋 المشاكل والاقتراحات:</h2>
  <ul>{issues_html}</ul>
</div>
</body>
</html>"""


# ════════════════════════════════════════════════════════════════════
# اختبار سريع
# ════════════════════════════════════════════════════════════════════
if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s | %(levelname)s | %(message)s"
    )
    
    validator = ContentValidator()
    
    test_script = {
        "hook": "توقف! 95% من الناس يفشلون لهذا السبب...",
        "scenes": [
            {"text": "توقف! 95% من الناس يفشلون لهذا السبب..."},
            {"text": "السر الذي يخفيه عنك الناجحون بسيط جداً."},
            {"text": "دراسة من هارفارد على 1000 ناجح كشفت قاعدة واحدة."},
            {"text": "كل من حقق نجاحاً عظيماً... كان يكتب أهدافه يومياً."},
            {"text": "الذين يكتبون = 42% أكثر تحقيقاً للأهداف."},
            {"text": "ابدأ اليوم... 3 أهداف فقط على ورقة."},
            {"text": "بعد 21 يوم ستلاحظ الفرق."},
            {"text": "شارك هذا الفيديو مع من يحتاجه!"},
        ],
    }
    
    print("\n📝 فحص النص (30 ثانية):")
    result = validator.validate_script(test_script, 30)
    print(f"   Score: {result.score}/100")
    print(f"   Valid: {result.valid}")
    print(f"   Quality: {result.quality.emoji}")
    
    print("\n⏱️ مواصفات المدة:")
    for dur in [30, 45, 60]:
        specs = validator.get_duration_specs(dur)
        print(f"   {dur}s: {specs['min_words']}-{specs['max_words']} كلمة")
    
    # حفظ التقرير
    print("\n💾 حفظ التقرير...")
    validator.export_report(result, "validation_report.json", "json")
    validator.export_report(result, "validation_report.html", "html")
