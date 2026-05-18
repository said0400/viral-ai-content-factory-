"""
🤖 AI Module — توليد السكربتات بالذكاء الاصطناعي
═══════════════════════════════════════════════════════════════
يدعم محركات متعددة مع fallback تلقائي:
  • Groq    (أساسي - مجاني وسريع جداً)
  • Gemini  (احتياطي - عند فشل Groq)

الاستخدام الأساسي:
    from engine.ai import ScriptWriter
    
    writer = ScriptWriter()
    script = writer.generate_script(topic="الطموح والنجاح")

الاستخدام المتقدم:
    from engine.ai import create_ai_writer, ContentValidator
    
    writer = create_ai_writer(prefer="auto")
    validator = ContentValidator()
═══════════════════════════════════════════════════════════════
"""

from __future__ import annotations

import os
import logging
from typing import Optional, Literal, TYPE_CHECKING

logger = logging.getLogger(__name__)

# ═══════════════════════════════════════════════════════════════════
# Version
# ═══════════════════════════════════════════════════════════════════
__version__ = "2.0.0"


# ═══════════════════════════════════════════════════════════════════
# Type Definitions
# ═══════════════════════════════════════════════════════════════════
ProviderPreference = Literal["auto", "groq", "gemini"]

if TYPE_CHECKING:
    # imports فقط للـ type hints (لا يتم تنفيذها)
    from engine.ai.base_writer import BaseAIWriter


# ═══════════════════════════════════════════════════════════════════
# Eager Imports (الأساسيات)
# ═══════════════════════════════════════════════════════════════════
from engine.ai.script_writer import ScriptWriter
from engine.ai.prompt_engine import PromptEngine
from engine.ai.content_validator import (
    ContentValidator,
    TextValidator,
    AudioValidator,
    DurationController,
    QualityLevel,
    ValidationAction,
)
from engine.ai.constants import ContentType, ProviderType


# ═══════════════════════════════════════════════════════════════════
# Lazy Imports (يُستورد عند الحاجة فقط)
# ═══════════════════════════════════════════════════════════════════
def _lazy_import_groq():
    """استيراد GroqWriter عند الحاجة فقط."""
    try:
        from engine.ai.groq_writer import GroqWriter
        return GroqWriter, True
    except ImportError as e:
        logger.debug(f"Groq not available: {e}")
        return None, False


def _lazy_import_gemini():
    """استيراد GeminiWriter عند الحاجة فقط."""
    try:
        from engine.ai.gemini_writer import GeminiWriter
        return GeminiWriter, True
    except ImportError as e:
        logger.debug(f"Gemini not available: {e}")
        return None, False


# ═══════════════════════════════════════════════════════════════════
# Availability Check
# ═══════════════════════════════════════════════════════════════════
def check_provider_available(provider: ProviderType) -> bool:
    """التحقق من توفر مزود معين."""
    if provider == "groq":
        if not os.getenv("GROQ_API_KEY"):
            return False
        _, available = _lazy_import_groq()
        return available
    
    elif provider == "gemini":
        if not os.getenv("GEMINI_API_KEY"):
            return False
        _, available = _lazy_import_gemini()
        return available
    
    return False


def get_available_providers() -> list[str]:
    """قائمة المزودات المتاحة."""
    providers = []
    if check_provider_available("groq"):
        providers.append("groq")
    if check_provider_available("gemini"):
        providers.append("gemini")
    return providers


# ═══════════════════════════════════════════════════════════════════
# Factory Function
# ═══════════════════════════════════════════════════════════════════
def create_ai_writer(
    prefer: ProviderPreference = "auto",
    enable_fallback: bool = True,
    enable_validation: bool = True,
    dry_run: bool = False,
) -> ScriptWriter:
    """
    إنشاء محرك توليد سكربتات ذكي.
    
    Args:
        prefer: المحرك المفضل
            - "auto"   → استخدام الـ orchestrator (Groq → Gemini)
            - "groq"   → Groq فقط (بدون fallback)
            - "gemini" → Gemini فقط (بدون fallback)
        enable_fallback: تفعيل التحويل للمزود البديل عند الفشل
        enable_validation: تفعيل فحص جودة المحتوى
        dry_run: وضع الاختبار (بدون API calls)
    
    Returns:
        ScriptWriter جاهز للاستخدام
    
    Raises:
        RuntimeError: إذا لم يتوفر أي مفتاح API
        ValueError: إذا كان الـ prefer غير صحيح
    
    Examples:
        >>> writer = create_ai_writer()  # تلقائي مع fallback
        >>> writer = create_ai_writer(prefer="groq")  # Groq فقط
        >>> writer = create_ai_writer(dry_run=True)  # للاختبار
    """
    available = get_available_providers()
    
    # ── حالة عدم وجود أي مزود ──
    if not available and not dry_run:
        raise RuntimeError(
            "❌ لا يوجد أي مزود AI متاح!\n"
            "   أضف أحد المفاتيح:\n"
            "   • GROQ_API_KEY (مجاني - https://console.groq.com)\n"
            "   • GEMINI_API_KEY (مجاني - https://aistudio.google.com)"
        )
    
    # ── prefer = "groq" ──
    if prefer == "groq":
        if not check_provider_available("groq") and not dry_run:
            raise RuntimeError(
                "❌ Groq غير متاح. "
                "أضف GROQ_API_KEY أو استخدم prefer='auto'"
            )
        return ScriptWriter(
            primary="groq",
            enable_fallback_provider=False,
            enable_validation=enable_validation,
            dry_run=dry_run,
        )
    
    # ── prefer = "gemini" ──
    if prefer == "gemini":
        if not check_provider_available("gemini") and not dry_run:
            raise RuntimeError(
                "❌ Gemini غير متاح. "
                "أضف GEMINI_API_KEY أو ثبّت google-generativeai"
            )
        return ScriptWriter(
            primary="gemini",
            enable_fallback_provider=False,
            enable_validation=enable_validation,
            dry_run=dry_run,
        )
    
    # ── prefer = "auto" ──
    if prefer == "auto":
        # حدد الأساسي حسب المتاح
        primary = "groq" if "groq" in available else "gemini"
        
        if not dry_run:
            logger.info(
                f"🤖 Auto mode | Primary: {primary} | "
                f"Available: {available}"
            )
        
        return ScriptWriter(
            primary=primary,
            enable_fallback_provider=enable_fallback,
            enable_validation=enable_validation,
            dry_run=dry_run,
        )
    
    raise ValueError(
        f"❌ prefer غير صحيح: '{prefer}'. "
        f"القيم المسموحة: 'auto', 'groq', 'gemini'"
    )


# ═══════════════════════════════════════════════════════════════════
# Convenience Functions
# ═══════════════════════════════════════════════════════════════════
def quick_generate(
    topic: str,
    content_type: ContentType = "motivational",
    target_duration: int = 45,
) -> dict:
    """
    توليد سريع بدون إعدادات.
    
    Examples:
        >>> from engine.ai import quick_generate
        >>> script = quick_generate("الطموح")
    """
    writer = create_ai_writer()
    return writer.generate_script(
        topic=topic,
        content_type=content_type,
        target_duration=target_duration,
    )


def get_info() -> dict:
    """معلومات عن الموديول."""
    return {
        "version": __version__,
        "available_providers": get_available_providers(),
        "groq_available": check_provider_available("groq"),
        "gemini_available": check_provider_available("gemini"),
    }


# ═══════════════════════════════════════════════════════════════════
# Lazy Property للـ GeminiWriter (للتوافق الخلفي)
# ═══════════════════════════════════════════════════════════════════
def __getattr__(name: str):
    """Lazy import للـ writers الفردية."""
    if name == "GeminiWriter":
        cls, available = _lazy_import_gemini()
        if not available:
            raise ImportError(
                "GeminiWriter غير متاح. "
                "ثبّت: pip install google-generativeai"
            )
        return cls
    
    if name == "GroqWriter":
        cls, available = _lazy_import_groq()
        if not available:
            raise ImportError(
                "GroqWriter غير متاح. "
                "ثبّت: pip install groq"
            )
        return cls
    
    if name == "BaseAIWriter":
        from engine.ai.base_writer import BaseAIWriter
        return BaseAIWriter
    
    raise AttributeError(f"module 'engine.ai' has no attribute '{name}'")


# ═══════════════════════════════════════════════════════════════════
# Public API
# ═══════════════════════════════════════════════════════════════════
__all__ = [
    # Version
    "__version__",
    
    # Main classes
    "ScriptWriter",
    "PromptEngine",
    "ContentValidator",
    
    # Validator components
    "TextValidator",
    "AudioValidator",
    "DurationController",
    "QualityLevel",
    "ValidationAction",
    
    # Lazy-loaded (متاحة عبر __getattr__)
    "GroqWriter",
    "GeminiWriter",
    "BaseAIWriter",
    
    # Types
    "ContentType",
    "ProviderType",
    "ProviderPreference",
    
    # Factory & Helpers
    "create_ai_writer",
    "check_provider_available",
    "get_available_providers",
    "quick_generate",
    "get_info",
]


# ═══════════════════════════════════════════════════════════════════
# Module Initialization Log
# ═══════════════════════════════════════════════════════════════════
def _log_module_status():
    """طباعة حالة الموديول عند الاستيراد (debug only)."""
    if logger.isEnabledFor(logging.DEBUG):
        available = get_available_providers()
        logger.debug(
            f"📦 engine.ai v{__version__} loaded | "
            f"Available: {available or 'NONE'}"
        )

_log_module_status()
