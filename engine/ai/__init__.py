"""
🤖 AI Module — توليد السكربتات بالذكاء الاصطناعي
═══════════════════════════════════════════════════════════════
يدعم محركين:
  • Groq    (أساسي - مجاني وسريع جداً)
  • Gemini  (احتياطي - عند فشل Groq)

الاستخدام:
    from engine.ai import ScriptWriter
    
    writer = ScriptWriter()
    script = writer.generate_script(topic="الطموح والنجاح")
═══════════════════════════════════════════════════════════════
"""

import os
import logging
from typing import Optional

logger = logging.getLogger(__name__)

# ─── الاستيرادات ──────────────────────────────────────────────────────────
from engine.ai.script_writer import ScriptWriter
from engine.ai.prompt_engine import PromptEngine

# Gemini اختياري - يتم استيراده عند الحاجة فقط
try:
    from engine.ai.gemini_writer import GeminiWriter
    _GEMINI_AVAILABLE = True
except ImportError as e:
    GeminiWriter = None
    _GEMINI_AVAILABLE = False
    logger.debug(f"Gemini not available: {e}")


# ─── دالة المصنع (Factory) ──────────────────────────────────────────────
def create_ai_writer(prefer: str = "auto") -> ScriptWriter:
    """
    إنشاء محرك توليد سكربتات بناءً على المتاح.

    Args:
        prefer: المحرك المفضل
            - "auto"   → اختيار تلقائي (Groq → Gemini)
            - "groq"   → Groq فقط
            - "gemini" → Gemini فقط

    Returns:
        كائن ScriptWriter جاهز للاستخدام

    Raises:
        RuntimeError: إذا لم يتوفر أي مفتاح API
    """
    has_groq = bool(os.getenv("GROQ_API_KEY"))
    has_gemini = bool(os.getenv("GEMINI_API_KEY")) and _GEMINI_AVAILABLE

    if prefer == "groq":
        if not has_groq:
            raise RuntimeError("❌ GROQ_API_KEY مفقود")
        return ScriptWriter(provider="groq")

    if prefer == "gemini":
        if not has_gemini:
            raise RuntimeError("❌ GEMINI_API_KEY مفقود أو مكتبة google-generativeai غير مثبتة")
        return GeminiWriter()

    # auto mode
    if has_groq:
        logger.info("🤖 استخدام Groq (أساسي)")
        return ScriptWriter(provider="groq")
    elif has_gemini:
        logger.info("🤖 استخدام Gemini (احتياطي)")
        return GeminiWriter()
    else:
        raise RuntimeError(
            "❌ لا يوجد أي مفتاح AI متاح!\n"
            "   أضف GROQ_API_KEY أو GEMINI_API_KEY إلى GitHub Secrets"
        )


# ─── ما يتم تصديره ──────────────────────────────────────────────────────
__all__ = [
    "ScriptWriter",
    "PromptEngine",
    "GeminiWriter",
    "create_ai_writer",
]
