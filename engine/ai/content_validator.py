"""
🎯 Content Validator — نظام التحقق الشامل من المحتوى
═══════════════════════════════════════════════════════════════
3 أنظمة تحقق متكاملة:

1. 📝 TextValidator: جودة النص والمحتوى
2. 🎙️ AudioValidator: تطابق الصوت مع النص
3. ⏱️ DurationController: ضبط المدة بدقة

═══════════════════════════════════════════════════════════════
"""

import os
import re
import logging
import subprocess
from pathlib import Path
from typing import Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)


# ════════════════════════════════════════════════════════════════════
# 📝 نظام 1: التحقق من جودة النص
# ════════════════════════════════════════════════════════════════════
class TextValidator:
    """
    التحقق من أن النص:
    ✓ يقدم قيمة حقيقية للمشاهد
    ✓ يشد الانتباه ويمنع التمرير
    ✓ فيه Hook + CTA
    ✓ طوله مناسب للمدة المطلوبة
    ✓ لا يوجد تكرار أو حشو
    """

    # ─── معايير الطول حسب المدة ────────────────────────────────
    DURATION_WORD_MAP = {
        30: {"min_words": 55, "max_words": 85, "min_scenes": 5, "max_scenes": 8},
        45: {"min_words": 85, "max_words": 130, "min_scenes": 7, "max_scenes": 12},
        60: {"min_words": 120, "max_words": 170, "min_scenes": 9, "max_scenes": 15},
    }

    # ─── كلمات القيمة (يجب أن يحتوي النص على بعضها) ───────────
    VALUE_INDICATORS = [
        # أرقام وإحصائيات
        r'\d+%', r'\d+\s*(ثانية|دقيقة|ساعة|يوم|أسبوع|شهر|سنة)',
        r'قاعدة', r'خطوة', r'نصيحة', r'سر',
        # كلمات القيمة
        'دراسة', 'بحث', 'علمي', 'اكتشف', 'تعلم', 'حقيقة',
        'طريقة', 'كيف', 'لماذا', 'السبب', 'الحل',
        'نتيجة', 'فائدة', 'تأثير', 'تغيير',
    ]

    # ─── كلمات الحشو (يجب تقليلها) ────────────────────────────
    FILLER_WORDS = [
        'جداً جداً', 'بشكل كبير جداً', 'في الحقيقة',
        'كما تعلمون', 'بالطبع', 'طبعاً',
    ]

    # ─── عناصر Hook القوي ──────────────────────────────────────
    HOOK_INDICATORS = [
        'توقف', 'انتظر', 'احذر', 'هل تعلم', 'هل سألت',
        '!', '?', '؟', '...', '%',
        'سر', 'حقيقة', 'خطأ', 'خطير',
    ]

    def validate_script(
        self,
        script: dict,
        target_duration: int = 45,
    ) -> Dict:
        """
        🎯 التحقق الشامل من السكربت.
        
        Returns:
            {
                "valid": True/False,
                "score": 0-100,
                "issues": [...],
                "suggestions": [...],
                "stats": {...}
            }
        """
        issues = []
        suggestions = []
        score = 100

        scenes = script.get("scenes", [])
        hook = script.get("hook", "")
        
        # استخراج النص الكامل
        all_texts = [s.get("text", "").strip() for s in scenes if s.get("text")]
        full_text = " ".join(all_texts)
        word_count = len(full_text.split())
        
        logger.info(f"📝 فحص النص: {word_count} كلمة، {len(scenes)} مشهد")

        # ═══════════════════════════════════════════════════════════
        # 1️⃣ فحص الطول
        # ═══════════════════════════════════════════════════════════
        duration_config = self.DURATION_WORD_MAP.get(
            target_duration, self.DURATION_WORD_MAP[45]
        )
        
        if word_count < duration_config["min_words"]:
            issues.append(
                f"❌ النص قصير جداً: {word_count} كلمة "
                f"(المطلوب: {duration_config['min_words']}-{duration_config['max_words']})"
            )
            score -= 30
        elif word_count > duration_config["max_words"]:
            issues.append(
                f"⚠ النص طويل: {word_count} كلمة "
                f"(المطلوب: {duration_config['min_words']}-{duration_config['max_words']})"
            )
            score -= 10

        # فحص عدد المشاهد
        if len(scenes) < duration_config["min_scenes"]:
            issues.append(
                f"⚠ مشاهد قليلة: {len(scenes)} "
                f"(المطلوب: {duration_config['min_scenes']}-{duration_config['max_scenes']})"
            )
            score -= 15

        # ═══════════════════════════════════════════════════════════
        # 2️⃣ فحص الـ Hook
        # ═══════════════════════════════════════════════════════════
        hook_text = scenes[0].get("text", "") if scenes else hook
        hook_score = self._check_hook_quality(hook_text)
        
        if hook_score < 3:
            issues.append("❌ الـ Hook ضعيف! لن يوقف المشاهد عن التمرير")
            suggestions.append("💡 ابدأ بسؤال صادم أو إحصائية أو تحذير")
            score -= 20

        # ═══════════════════════════════════════════════════════════
        # 3️⃣ فحص القيمة المقدمة
        # ═══════════════════════════════════════════════════════════
        value_count = self._count_value_indicators(full_text)
        
        if value_count < 2:
            issues.append("❌ النص لا يقدم قيمة كافية!")
            suggestions.append("💡 أضف أرقام، إحصائيات، نصائح عملية")
            score -= 25
        elif value_count < 4:
            suggestions.append("💡 يمكن إضافة المزيد من الأرقام والحقائق")
            score -= 5

        # ═══════════════════════════════════════════════════════════
        # 4️⃣ فحص التكرار
        # ═══════════════════════════════════════════════════════════
        repeated = self._check_repetition(all_texts)
        if repeated:
            issues.append(f"⚠ تكرار في النص: {', '.join(repeated[:3])}")
            score -= 10

        # ═══════════════════════════════════════════════════════════
        # 5️⃣ فحص الـ CTA
        # ═══════════════════════════════════════════════════════════
        last_scene = scenes[-1].get("text", "") if scenes else ""
        has_cta = any(word in last_scene for word in [
            'شارك', 'اشترك', 'تابع', 'اكتب', 'علّق', 'احفظ',
            'طبّق', 'ابدأ', 'جرّب', 'فعّل',
        ])
        
        if not has_cta:
            suggestions.append("💡 أضف CTA في نهاية الفيديو (شارك، اشترك، طبّق)")
            score -= 5

        # ═══════════════════════════════════════════════════════════
        # 6️⃣ فحص طول الجمل
        # ═══════════════════════════════════════════════════════════
        long_scenes = [
            i for i, s in enumerate(scenes)
            if len(s.get("text", "").split()) > 12
        ]
        if long_scenes:
            issues.append(
                f"⚠ جمل طويلة في المشاهد: {long_scenes[:3]} "
                f"(حد أقصى 10-12 كلمة)"
            )
            score -= 5

        # النتيجة
        score = max(0, min(100, score))
        valid = score >= 60

        result = {
            "valid": valid,
            "score": score,
            "issues": issues,
            "suggestions": suggestions,
            "stats": {
                "word_count": word_count,
                "scene_count": len(scenes),
                "target_duration": target_duration,
                "hook_score": hook_score,
                "value_indicators": value_count,
                "has_cta": has_cta,
            },
        }

        # طباعة النتيجة
        status = "✅ ممتاز" if score >= 80 else "⚠ مقبول" if score >= 60 else "❌ ضعيف"
        logger.info(f"📊 نتيجة فحص النص: {score}/100 ({status})")
        
        for issue in issues:
            logger.warning(f"   {issue}")
        for suggestion in suggestions:
            logger.info(f"   {suggestion}")

        return result

    def _check_hook_quality(self, hook_text: str) -> int:
        """فحص جودة الـ Hook (0-5)."""
        score = 0
        for indicator in self.HOOK_INDICATORS:
            if indicator in hook_text:
                score += 1
        
        if len(hook_text.split()) <= 10:
            score += 1
        
        return min(score, 5)

    def _count_value_indicators(self, text: str) -> int:
        """عدّ مؤشرات القيمة في النص."""
        count = 0
        for pattern in self.VALUE_INDICATORS:
            if re.search(pattern, text):
                count += 1
        return count

    def _check_repetition(self, texts: List[str]) -> List[str]:
        """فحص التكرار في النصوص."""
        repeated = []
        seen_phrases = set()
        
        for text in texts:
            words = text.split()
            for i in range(len(words) - 2):
                phrase = " ".join(words[i:i+3])
                if phrase in seen_phrases and len(phrase) > 10:
                    repeated.append(phrase)
                seen_phrases.add(phrase)
        
        return list(set(repeated))


# ════════════════════════════════════════════════════════════════════
# 🎙️ نظام 2: التحقق من تطابق الصوت مع النص
# ════════════════════════════════════════════════════════════════════
class AudioValidator:
    """
    التحقق من أن الصوت:
    ✓ يحتوي كل النص (لا فقدان)
    ✓ لا يوجد تكرار
    ✓ المدة متناسبة مع طول النص
    """

    # ─── معدل الكلمات في الدقيقة (عربي) ──────────────────────
    ARABIC_WPM_MIN = 120  # بطيء
    ARABIC_WPM_MAX = 180  # سريع
    ARABIC_WPM_NORMAL = 150  # طبيعي

    def validate_audio(
        self,
        audio_path: str,
        original_text: str,
        target_duration: int = 45,
    ) -> Dict:
        """
        🎯 التحقق من تطابق الصوت مع النص.
        """
        issues = []
        
        # قياس مدة الصوت
        audio_duration = self._get_duration(audio_path)
        word_count = len(original_text.split())
        
        if audio_duration <= 0:
            return {
                "valid": False,
                "issues": ["❌ فشل قياس مدة الصوت"],
                "audio_duration": 0,
                "expected_duration": 0,
            }

        # حساب المدة المتوقعة
        expected_min = (word_count / self.ARABIC_WPM_MAX) * 60
        expected_max = (word_count / self.ARABIC_WPM_MIN) * 60
        expected_normal = (word_count / self.ARABIC_WPM_NORMAL) * 60

        logger.info(
            f"🎙️ فحص الصوت: {audio_duration:.1f}s فعلي | "
            f"{expected_normal:.1f}s متوقع | {word_count} كلمة"
        )

        # ═══════════════════════════════════════════════════════════
        # فحص 1: هل الصوت قصير جداً (فقدان نص)
        # ═══════════════════════════════════════════════════════════
        if audio_duration < expected_min * 0.5:
            issues.append(
                f"❌ الصوت قصير جداً! ({audio_duration:.1f}s) "
                f"المتوقع: {expected_min:.1f}-{expected_max:.1f}s"
            )
            issues.append("🔧 الحل: النص لم يتحول كاملاً، يجب تقسيمه")
            
            return {
                "valid": False,
                "issues": issues,
                "audio_duration": audio_duration,
                "expected_duration": expected_normal,
                "word_count": word_count,
                "coverage_percent": round((audio_duration / expected_normal) * 100, 1),
                "action": "RETRY_WITH_CHUNKS",
            }

        # ═══════════════════════════════════════════════════════════
        # فحص 2: هل الصوت طويل جداً (تكرار محتمل)
        # ═══════════════════════════════════════════════════════════
        if audio_duration > expected_max * 1.5:
            issues.append(
                f"⚠ الصوت طويل جداً! ({audio_duration:.1f}s) "
                f"المتوقع: {expected_min:.1f}-{expected_max:.1f}s"
            )
            issues.append("🔧 قد يكون هناك تكرار في النص")

        # ═══════════════════════════════════════════════════════════
        # فحص 3: هل المدة ضمن النطاق المقبول
        # ═══════════════════════════════════════════════════════════
        coverage = (audio_duration / expected_normal) * 100
        
        valid = 50 <= coverage <= 150
        
        if valid:
            logger.info(f"   ✅ الصوت مكتمل ({coverage:.0f}% تغطية)")
        else:
            logger.warning(f"   ⚠ تغطية الصوت: {coverage:.0f}%")

        return {
            "valid": valid,
            "issues": issues,
            "audio_duration": round(audio_duration, 2),
            "expected_duration": round(expected_normal, 2),
            "word_count": word_count,
            "coverage_percent": round(coverage, 1),
            "action": "OK" if valid else "RETRY_WITH_CHUNKS",
        }

    def _get_duration(self, path: str) -> float:
        """قياس مدة الصوت."""
        try:
            result = subprocess.run(
                [
                    "ffprobe", "-v", "quiet",
                    "-show_entries", "format=duration",
                    "-of", "default=noprint_wrappers=1:nokey=1",
                    path,
                ],
                capture_output=True, text=True, timeout=30, check=True,
            )
            return float(result.stdout.strip())
        except Exception:
            return 0.0


# ════════════════════════════════════════════════════════════════════
# ⏱️ نظام 3: التحكم في المدة
# ════════════════════════════════════════════════════════════════════
class DurationController:
    """
    ضبط طول النص بدقة حسب المدة المطلوبة:
    ✓ 30 ثانية = 55-85 كلمة
    ✓ 45 ثانية = 85-130 كلمة
    ✓ 60 ثانية = 120-170 كلمة
    """

    DURATION_SPECS = {
        30: {
            "min_words": 55,
            "max_words": 85,
            "ideal_words": 70,
            "min_scenes": 5,
            "max_scenes": 8,
            "ideal_scenes": 6,
            "words_per_scene": (7, 12),
            "description": "قصير وسريع - TikTok style",
        },
        45: {
            "min_words": 85,
            "max_words": 130,
            "ideal_words": 105,
            "min_scenes": 7,
            "max_scenes": 12,
            "ideal_scenes": 9,
            "words_per_scene": (8, 14),
            "description": "متوسط - متوازن",
        },
        60: {
            "min_words": 120,
            "max_words": 170,
            "ideal_words": 145,
            "min_scenes": 9,
            "max_scenes": 15,
            "ideal_scenes": 12,
            "words_per_scene": (8, 14),
            "description": "طويل - تفصيلي",
        },
    }

    def get_specs(self, target_duration: int) -> Dict:
        """الحصول على مواصفات المدة المطلوبة."""
        return self.DURATION_SPECS.get(
            target_duration, self.DURATION_SPECS[45]
        )

    def validate_duration(
        self,
        script: dict,
        target_duration: int,
    ) -> Dict:
        """التحقق من تطابق النص مع المدة المطلوبة."""
        specs = self.get_specs(target_duration)
        
        scenes = script.get("scenes", [])
        all_texts = [s.get("text", "").strip() for s in scenes if s.get("text")]
        full_text = " ".join(all_texts)
        word_count = len(full_text.split())

        issues = []
        
        if word_count < specs["min_words"]:
            issues.append(
                f"❌ النص قصير لـ {target_duration}s: "
                f"{word_count} كلمة (المطلوب: {specs['min_words']}-{specs['max_words']})"
            )
        elif word_count > specs["max_words"]:
            issues.append(
                f"⚠ النص طويل لـ {target_duration}s: "
                f"{word_count} كلمة (المطلوب: {specs['min_words']}-{specs['max_words']})"
            )

        if len(scenes) < specs["min_scenes"]:
            issues.append(
                f"⚠ مشاهد قليلة: {len(scenes)} "
                f"(المطلوب: {specs['min_scenes']}-{specs['max_scenes']})"
            )

        valid = len(issues) == 0
        
        estimated_duration = (word_count / 150) * 60
        
        result = {
            "valid": valid,
            "issues": issues,
            "word_count": word_count,
            "scene_count": len(scenes),
            "target_duration": target_duration,
            "estimated_duration": round(estimated_duration, 1),
            "specs": specs,
        }

        status = "✅" if valid else "⚠"
        logger.info(
            f"⏱️ فحص المدة: {status} "
            f"{word_count} كلمة → ~{estimated_duration:.0f}s "
            f"(هدف: {target_duration}s)"
        )

        return result

    def get_duration_instruction(self, target_duration: int) -> str:
        """الحصول على تعليمات المدة للـ Prompt."""
        specs = self.get_specs(target_duration)
        
        return (
            f"⏱️ المدة المستهدفة: {target_duration} ثانية\n"
            f"📝 عدد الكلمات: {specs['min_words']}-{specs['max_words']} كلمة "
            f"(الأمثل: {specs['ideal_words']})\n"
            f"🎬 عدد المشاهد: {specs['min_scenes']}-{specs['max_scenes']} "
            f"(الأمثل: {specs['ideal_scenes']})\n"
            f"📏 كلمات لكل مشهد: {specs['words_per_scene'][0]}-{specs['words_per_scene'][1]}\n"
            f"📋 النوع: {specs['description']}"
        )


# ════════════════════════════════════════════════════════════════════
# 🎯 نظام التحقق الشامل
# ════════════════════════════════════════════════════════════════════
class ContentValidator:
    """النظام الشامل الذي يجمع كل أنظمة التحقق."""

    def __init__(self):
        self.text_validator = TextValidator()
        self.audio_validator = AudioValidator()
        self.duration_controller = DurationController()
        
        logger.info("🎯 ContentValidator جاهز (3 أنظمة تحقق)")

    def validate_script(self, script: dict, target_duration: int) -> Dict:
        """فحص السكربت قبل التوليد."""
        logger.info("=" * 50)
        logger.info("🎯 فحص شامل للسكربت...")
        logger.info("=" * 50)
        
        text_result = self.text_validator.validate_script(script, target_duration)
        duration_result = self.duration_controller.validate_duration(script, target_duration)
        
        overall_valid = text_result["valid"] and duration_result["valid"]
        overall_score = text_result["score"]
        
        all_issues = text_result["issues"] + duration_result["issues"]
        
        if overall_valid:
            logger.info(f"✅ السكربت جاهز! (Score: {overall_score}/100)")
        else:
            logger.warning(f"⚠ السكربت يحتاج تحسين (Score: {overall_score}/100)")
            for issue in all_issues:
                logger.warning(f"   {issue}")
        
        return {
            "valid": overall_valid,
            "score": overall_score,
            "text_result": text_result,
            "duration_result": duration_result,
            "all_issues": all_issues,
        }

    def validate_audio(
        self,
        audio_path: str,
        original_text: str,
        target_duration: int,
    ) -> Dict:
        """فحص الصوت بعد التوليد."""
        logger.info("=" * 50)
        logger.info("🎙️ فحص شامل للصوت...")
        logger.info("=" * 50)
        
        return self.audio_validator.validate_audio(
            audio_path, original_text, target_duration
        )

    def get_duration_specs(self, target_duration: int) -> Dict:
        """الحصول على مواصفات المدة."""
        return self.duration_controller.get_specs(target_duration)

    def get_duration_instruction(self, target_duration: int) -> str:
        """تعليمات المدة للـ Prompt."""
        return self.duration_controller.get_duration_instruction(target_duration)


# ════════════════════════════════════════════════════════════════════
#                    اختبار سريع
# ════════════════════════════════════════════════════════════════════
if __name__ == "__main__":
    validator = ContentValidator()
    
    # اختبار بسكربت تجريبي
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
    print(f"   Score: {result['score']}/100")
    print(f"   Valid: {result['valid']}")
    
    print("\n⏱️ مواصفات المدة:")
    for dur in [30, 45, 60]:
        specs = validator.get_duration_specs(dur)
        print(f"   {dur}s: {specs['min_words']}-{specs['max_words']} كلمة")
