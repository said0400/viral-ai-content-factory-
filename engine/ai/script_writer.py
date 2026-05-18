"""
🎯 Script Writer — Smart Orchestrator
═══════════════════════════════════════════════════════════════
المنسّق الذكي الذي يستخدم Groq كأساسي و Gemini كاحتياطي

التدفق:
  1. محاولة Groq (السريع)
  2. عند الفشل → التحويل لـ Gemini
  3. عند الفشل → Fallback ذكي
  4. التحقق من المحتوى عبر ContentValidator
═══════════════════════════════════════════════════════════════
"""

from __future__ import annotations

import logging
from typing import Optional, Any

from engine.ai.constants import ContentType, ProviderType
from engine.ai.groq_writer import GroqWriter
from engine.ai.gemini_writer import GeminiWriter
from engine.ai.content_validator import ContentValidator, FullValidationResult

logger = logging.getLogger(__name__)


class ScriptWriter:
    """منسّق ذكي للسكربتات مع fallback متعدد المستويات."""
    
    def __init__(
        self,
        primary: ProviderType = "groq",
        enable_fallback_provider: bool = True,
        enable_validation: bool = True,
        validation_min_score: int = 60,
        dry_run: bool = False,
    ):
        """
        تهيئة الـ orchestrator.
        
        Args:
            primary: المزود الأساسي ("groq" أو "gemini")
            enable_fallback_provider: تفعيل التحويل للمزود الآخر عند الفشل
            enable_validation: تفعيل فحص جودة المحتوى
            validation_min_score: الحد الأدنى للنتيجة المقبولة
            dry_run: وضع الاختبار
        """
        self.primary = primary
        self.enable_fallback = enable_fallback_provider
        self.enable_validation = enable_validation
        self.min_score = validation_min_score
        self.dry_run = dry_run
        
        # تهيئة الكتّاب
        self.writers: dict[str, Any] = {}
        self._init_writers()
        
        # تهيئة الـ validator
        self.validator = ContentValidator() if enable_validation else None
        
        logger.info(
            f"🎯 ScriptWriter ready | "
            f"Primary: {primary} | "
            f"Fallback: {enable_fallback_provider} | "
            f"Validation: {enable_validation}"
        )
    
    def _init_writers(self):
        """تهيئة الكتّاب المتاحين."""
        # Primary
        try:
            if self.primary == "groq":
                self.writers["groq"] = GroqWriter(dry_run=self.dry_run)
            elif self.primary == "gemini":
                self.writers["gemini"] = GeminiWriter(dry_run=self.dry_run)
        except Exception as e:
            logger.error(f"❌ فشل تهيئة {self.primary}: {e}")
        
        # Fallback provider
        if self.enable_fallback:
            try:
                if self.primary == "groq" and "gemini" not in self.writers:
                    self.writers["gemini"] = GeminiWriter(dry_run=self.dry_run)
                elif self.primary == "gemini" and "groq" not in self.writers:
                    self.writers["groq"] = GroqWriter(dry_run=self.dry_run)
            except Exception as e:
                logger.warning(f"⚠ فشل تهيئة fallback provider: {e}")
        
        if not self.writers:
            raise RuntimeError("❌ لم يتم تهيئة أي writer!")
    
    # ═══════════════════════════════════════════════════════════════
    # Public API
    # ═══════════════════════════════════════════════════════════════
    def generate_script(
        self,
        topic: str,
        content_type: ContentType = "motivational",
        target_duration: int = 45,
        mood: Optional[str] = None,
    ) -> dict[str, Any]:
        """
        توليد سكربت مع fallback متعدد المستويات.
        
        التدفق:
        1. جرب الـ primary provider
        2. إذا فشل → جرب الـ fallback provider
        3. إذا فشل الكل → استخدم fallback script
        4. فحص الجودة (إذا مفعّل)
        """
        # ── الترتيب: primary أولاً ──
        providers_order = [self.primary]
        for p in self.writers.keys():
            if p != self.primary:
                providers_order.append(p)
        
        last_script = None
        
        for provider in providers_order:
            if provider not in self.writers:
                continue
            
            writer = self.writers[provider]
            logger.info(f"🚀 محاولة التوليد عبر: {provider}")
            
            try:
                script = writer.generate_script(
                    topic=topic,
                    content_type=content_type,
                    target_duration=target_duration,
                    mood=mood,
                )
                
                last_script = script
                
                # فحص الجودة
                if self.enable_validation:
                    validation = self.validator.validate_script(
                        script, target_duration
                    )
                    
                    # إذا fallback من المزود → لا داعي للتحقق
                    if script.get("is_fallback"):
                        logger.info("ℹ Skipping validation for fallback")
                        continue
                    
                    # إذا الجودة منخفضة → جرب التالي
                    if validation.score < self.min_score:
                        logger.warning(
                            f"⚠ {provider} script score {validation.score} "
                            f"< {self.min_score}. جاري المحاولة بالتالي..."
                        )
                        continue
                    
                    # نجاح
                    script["validation"] = validation.to_dict()
                    logger.info(
                        f"✅ تم التوليد بنجاح! "
                        f"Provider: {provider} | "
                        f"Score: {validation.score}/100"
                    )
                    return script
                else:
                    # بدون فحص → اقبل أول نجاح
                    return script
                    
            except Exception as e:
                logger.error(f"❌ فشل {provider}: {e}")
                continue
        
        # كل الـ providers فشلوا → استخدم آخر سكربت أو fallback
        if last_script:
            logger.warning("⚠ استخدام آخر سكربت متاح رغم انخفاض الجودة")
            return last_script
        
        # حالة كارثية: حتى fallback فشل
        logger.error("❌ فشل التوليد تماماً!")
        first_writer = next(iter(self.writers.values()))
        return first_writer._fallback(topic, target_duration)
    
    def generate_batch(
        self,
        topics: list[str],
        content_type: ContentType = "motivational",
        target_duration: int = 45,
    ) -> list[dict[str, Any]]:
        """توليد batch."""
        results = []
        for i, topic in enumerate(topics, 1):
            logger.info(f"📝 [{i}/{len(topics)}] {topic}")
            try:
                script = self.generate_script(
                    topic=topic,
                    content_type=content_type,
                    target_duration=target_duration,
                )
                results.append(script)
            except Exception as e:
                logger.error(f"❌ فشل '{topic}': {e}")
        return results
    
    # ═══════════════════════════════════════════════════════════════
    # Stats
    # ═══════════════════════════════════════════════════════════════
    def print_all_stats(self):
        """طباعة إحصائيات جميع الكتّاب."""
        print("=" * 60)
        print("📊 Overall Statistics")
        print("=" * 60)
        for name, writer in self.writers.items():
            print()
            writer.print_stats()


# ═══════════════════════════════════════════════════════════════════
# اختبار سريع
# ═══════════════════════════════════════════════════════════════════
if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s | %(levelname)s | %(message)s"
    )
    
    writer = ScriptWriter(
        primary="groq",
        enable_fallback_provider=True,
        enable_validation=True,
        dry_run=True,  # للاختبار
    )
    
    script = writer.generate_script(
        topic="كيف تتعلم بسرعة",
        content_type="educational",
        target_duration=45,
    )
    
    print(f"\n✅ Script generated:")
    print(f"   Title: {script['title']}")
    print(f"   Scenes: {len(script['scenes'])}")
    print(f"   Generated by: {script['generated_by']}")
    
    writer.print_all_stats()
