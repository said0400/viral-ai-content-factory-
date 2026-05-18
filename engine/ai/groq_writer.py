"""
🤖 Groq Writer (يرث من BaseAIWriter)
═══════════════════════════════════════════════════════════════
يستخدم Groq LLaMA - سريع ومجاني
═══════════════════════════════════════════════════════════════
"""

from __future__ import annotations

import os
import logging
from dotenv import load_dotenv

from engine.ai.base_writer import BaseAIWriter
from engine.ai.constants import SYSTEM_PROMPT_STRICT, DEFAULT_MAX_TOKENS

load_dotenv()
logger = logging.getLogger(__name__)

try:
    from groq import Groq
    _GROQ_AVAILABLE = True
except ImportError:
    Groq = None
    _GROQ_AVAILABLE = False


class GroqWriter(BaseAIWriter):
    """كاتب Groq - الأساسي."""
    
    PROVIDER_NAME = "groq"
    
    GROQ_MODELS = [
        "llama-3.3-70b-versatile",
        "llama-3.1-70b-versatile",
        "llama-3.1-8b-instant",
    ]
    
    def __init__(
        self,
        api_key: str | None = None,
        rate_limit: int = 30,  # Groq free tier
        dry_run: bool = False,
    ):
        self._api_key = api_key or os.getenv("GROQ_API_KEY")
        super().__init__(rate_limit=rate_limit, dry_run=dry_run)
    
    def _init_client(self) -> None:
        """تهيئة Groq client."""
        if not _GROQ_AVAILABLE:
            raise ImportError(
                "❌ groq غير مثبتة. pip install groq"
            )
        
        if not self._api_key:
            raise ValueError("❌ GROQ_API_KEY غير موجود")
        
        self.client = Groq(api_key=self._api_key)
        logger.info(f"✓ Groq initialized | Models: {self.GROQ_MODELS}")
    
    def _get_models_chain(self) -> list[str]:
        return self.GROQ_MODELS
    
    def _call_api(
        self,
        prompt: str,
        model: str,
        temperature: float,
    ) -> str:
        """استدعاء Groq API."""
        response = self.client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT_STRICT},
                {"role": "user", "content": prompt},
            ],
            temperature=temperature,
            max_tokens=DEFAULT_MAX_TOKENS,
            response_format={"type": "json_object"},
        )
        return response.choices[0].message.content.strip()
