"""
🤖 Gemini Script Writer v2.1 (احتياطي)
═══════════════════════════════════════════════════════════════
يولّد سكربتات عربية باستخدام Google Gemini AI

التحسينات في v2.1:
  ✓ تحديث الموديلات للأحدث (gemini-2.0-flash)
  ✓ Timeout management
  ✓ Rate limiting
  ✓ Usage tracking
  ✓ Cached configurations
  ✓ Parallel batch processing
  ✓ Type-safe enums
  ✓ Better fallback variety
  ✓ Dry run mode للاختبار
═══════════════════════════════════════════════════════════════
"""

from __future__ import annotations

import os
import re
import json
import time
import random
import logging
from enum import Enum
from dataclasses import dataclass, field
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Optional, Literal, Any
from threading import Lock

from dotenv import load_dotenv

from engine.ai.prompt_engine import PromptEngine

load_dotenv()
logger = logging.getLogger(__name__)

# ═══════════════════════════════════════════════════════════════════
# استيراد آمن لـ Gemini
# ═══════════════════════════════════════════════════════════════════
try:
    import google.generativeai as genai
    _GEMINI_AVAILABLE = True
except ImportError:
    genai = None
    _GEMINI_AVAILABLE = False
    logger.warning(
        "⚠ google-generativeai غير مثبتة. "
        "شغّل: pip install google-generativeai"
    )


# ═══════════════════════════════════════════════════════════════════
# Type Definitions
# ═══════════════════════════════════════════════════════════════════
ContentType = Literal["motivational", "educational", "story", "quote"]


class GeminiModel(str, Enum):
    """الموديلات المتاحة من Gemini (محدّثة 2025)."""
    # ✅ FIXED: الموديلات الجديدة
    FLASH_2 = "gemini-2.0-flash"
    FLASH_LITE_2 = "gemini-2.0-flash-lite"
    FLASH_EXP = "gemini-2.0-flash-exp"
    PRO_15 = "gemini-1.5-pro-latest"  # احتياطي
    FLASH_15 = "gemini-1.5-flash-latest"  # احتياطي
    
    @classmethod
    def fallback_chain(cls) -> list["GeminiModel"]:
        """سلسلة الـ fallback مرتبة (الأحدث أولاً)."""
        return [
            cls.FLASH_2,        # ⭐ الأفضل والأسرع
            cls.FLASH_LITE_2,   # سريع
            cls.FLASH_EXP,      # تجريبي
            cls.FLASH_15,       # احتياطي
            cls.PRO_15,         # احتياطي أخير
        ]


# ═══════════════════════════════════════════════════════════════════
# Usage Tracker (تتبع الاستخدام)
# ═══════════════════════════════════════════════════════════════════
@dataclass
class UsageStats:
    """إحصائيات استخدام Gemini."""
    total_requests: int = 0
    successful_requests: int = 0
    failed_requests: int = 0
    fallback_used: int = 0
    total_tokens_estimate: int = 0
    by_model: dict[str, int] = field(default_factory=dict)
    
    def record_success(self, model: str, tokens: int = 0):
        self.total_requests += 1
        self.successful_requests += 1
        self.total_tokens_estimate += tokens
        self.by_model[model] = self.by_model.get(model, 0) + 1
    
    def record_failure(self):
        self.total_requests += 1
        self.failed_requests += 1
    
    def record_fallback(self):
        self.fallback_used += 1
    
    @property
    def success_rate(self) -> float:
        if self.total_requests == 0:
            return 0.0
        return (self.successful_requests / self.total_requests) * 100
    
    def summary(self) -> str:
        return (
            f"📊 Gemini Usage:\n"
            f"   • Total: {self.total_requests}\n"
            f"   • Success: {self.successful_requests} ({self.success_rate:.1f}%)\n"
            f"   • Failed: {self.failed_requests}\n"
            f"   • Fallback: {self.fallback_used}\n"
            f"   • Tokens (est): ~{self.total_tokens_estimate}\n"
            f"   • By Model: {self.by_model}"
        )


# ═══════════════════════════════════════════════════════════════════
# Rate Limiter البسيط
# ═══════════════════════════════════════════════════════════════════
class RateLimiter:
    """منع تجاوز حدود API."""
    
    def __init__(self, max_calls_per_minute: int = 60):
        self.max_calls = max_calls_per_minute
        self.calls: list[float] = []
        self.lock = Lock()
    
    def wait_if_needed(self):
        """انتظر إذا تجاوزت الحد."""
        with self.lock:
            now = time.time()
            # احذف الـ calls الأقدم من دقيقة
            self.calls = [t for t in self.calls if now - t < 60]
            
            if len(self.calls) >= self.max_calls:
                wait_time = 60 - (now - self.calls[0]) + 0.5
                if wait_time > 0:
                    logger.warning(
                        f"⏳ Rate limit reached. Waiting {wait_time:.1f}s..."
                    )
                    time.sleep(wait_time)
                    self.calls = []
            
            self.calls.append(now)


# ═══════════════════════════════════════════════════════════════════
# Constants
# ═══════════════════════════════════════════════════════════════════
class GeminiConstants:
    """ثوابت Gemini."""
    
    MAX_RETRIES = 3
    RETRY_DELAY_BASE = 2  # ثواني
    MAX_OUTPUT_TOKENS = 4000
    TIMEOUT_SECONDS = 60
    
    TEMP_MIN = 0.72
    TEMP_MAX = 0.95
    
    RATE_LIMIT_PER_MINUTE = 15  # Gemini free tier
    
    SYSTEM_INSTRUCTION = (
        "أنت مولّد JSON صارم لسكربتات الفيديوهات العربية القصيرة. "
        "أعد JSON صالحاً فقط. بدون markdown. بدون شرح. بدون ```."
    )
    
    SAFETY_SETTINGS = [
        {"category": "HARM_CATEGORY_HARASSMENT", "threshold": "BLOCK_ONLY_HIGH"},
        {"category": "HARM_CATEGORY_HATE_SPEECH", "threshold": "BLOCK_ONLY_HIGH"},
        {"category": "HARM_CATEGORY_SEXUALLY_EXPLICIT", "threshold": "BLOCK_ONLY_HIGH"},
        {"category": "HARM_CATEGORY_DANGEROUS_CONTENT", "threshold": "BLOCK_ONLY_HIGH"},
    ]


# ═══════════════════════════════════════════════════════════════════
# Mood Constants
# ═══════════════════════════════════════════════════════════════════
MOOD_KEYWORDS: dict[str, tuple[str, ...]] = {
    "motivation": (
        "الطموح", "النجاح", "القوة", "البطولة", "الانتصار", "الإنجاز",
        "التحفيز", "الإرادة", "الصبر", "المثابرة", "الهدف", "الإصرار",
    ),
    "emotional": (
        "الحزن", "الألم", "الفقد", "الوحدة", "الذكريات", "العذاب",
        "الحب", "العشق", "القلب", "الشوق", "الغرام", "الحنين",
    ),
    "psychological": (
        "الذكاء", "العقل", "التفكير", "العلم", "الفلسفة", "الحكمة",
        "النفس", "الوعي", "الإدراك",
    ),
    "dark": (
        "الموت", "الفناء", "النهاية", "الغياب", "الظلام", "اليأس",
        "الخوف", "القلق",
    ),
    "horror": ("الرعب", "الكابوس", "الجريمة", "الشر", "الوحش"),
    "sad": ("الكآبة", "الأسى", "الحسرة", "الندم"),
    "sigma": (
        "القوة", "الذئب", "الوحدة", "الانضباط", "الصمت",
        "الخيانة", "الحقيقة", "الغضب", "الظلم", "الكذب",
    ),
}

# كلمات للتأكيد (Emphasis Detection)
EMPHASIS_TRIGGERS: frozenset[str] = frozenset({
    "لن", "لا", "أبداً", "دائماً", "أنت", "أنا",
    "النجاح", "الفشل", "الألم", "القوة", "الحقيقة",
    "الآن", "اليوم", "تذكر", "افعل", "توقف",
    "الموت", "الحياة", "الحب", "الخوف", "الأمل",
})


# ═══════════════════════════════════════════════════════════════════
# Fallback Templates (متنوعة حسب الـ mood)
# ═══════════════════════════════════════════════════════════════════
FALLBACK_TEMPLATES: dict[str, list[str]] = {
    "default": [
        "هل تعرف الحقيقة عن {topic}؟",
        "الحقيقة التي يخفونها عن {topic}...",
        "كل شيء يبدأ من لحظة واحدة.",
        "تلك اللحظة التي تقرر فيها أن تتغير.",
        "لا أحد سيأتي لإنقاذك.",
        "أنت وحدك من يصنع مصيرك.",
        "{topic} ليس مجرد كلمة...",
        "بل هو قرار يغيّر حياتك.",
        "هذا هو الدرس الأهم.",
        "احفظه جيداً... فقد يغيّر كل شيء.",
        "لن أكرر هذه الكلمات.",
        "تابع... فالقادم أعمق.",
    ],
    "motivation": [
        "{topic} يبدأ من قرار واحد.",
        "كل ناجح بدأ من نقطة الصفر.",
        "الفرق بينك وبين النجاح... خطوة واحدة.",
        "لا تنتظر اللحظة المثالية.",
        "ابدأ الآن... ولو بخطوة صغيرة.",
        "الكسل عدوك الأكبر.",
        "تذكر: 1% يومياً = 37x سنوياً.",
        "النجاح ليس صدفة... بل قرار.",
        "اعمل بصمت... ودع نجاحك يتكلم.",
        "كل يوم بدون تقدم... هو يوم خسارة.",
    ],
    "emotional": [
        "هل شعرت يوماً بألم {topic}؟",
        "هذا الألم يعرفه فقط من جرّبه.",
        "الجرح يلتئم... لكن الذكرى تبقى.",
        "أحياناً... الصمت يقول كل شيء.",
        "تعلمت أن أبتسم رغم الألم.",
        "القلب الذي يحب... هو الذي يتألم.",
        "الوقت يداوي... لكنه لا ينسي.",
        "كل دمعة... لها قصة.",
        "تذكر: أنت أقوى مما تعتقد.",
        "ستمر... كما مرّ غيرها.",
    ],
}


# ═══════════════════════════════════════════════════════════════════
# Main Class
# ═══════════════════════════════════════════════════════════════════
class GeminiWriter:
    """مولّد سكربتات احتياطي باستخدام Google Gemini."""

    def __init__(
        self,
        api_key: Optional[str] = None,
        rate_limit: int = GeminiConstants.RATE_LIMIT_PER_MINUTE,
        dry_run: bool = False,
    ):
        """
        تهيئة Gemini client.
        
        Args:
            api_key: مفتاح API (اختياري - يُقرأ من البيئة)
            rate_limit: عدد الطلبات المسموحة بالدقيقة
            dry_run: تشغيل وهمي بدون استدعاء API (للاختبار)
        """
        self.dry_run = dry_run
        self.stats = UsageStats()
        self.rate_limiter = RateLimiter(rate_limit)
        self._models_cache: dict[str, Any] = {}
        
        if dry_run:
            logger.info("🧪 GeminiWriter في وضع DRY RUN")
            self.prompt_engine = PromptEngine()
            return
        
        # ── Validation ──
        if not _GEMINI_AVAILABLE:
            raise ImportError(
                "❌ مكتبة google-generativeai غير مثبتة.\n"
                "   ثبّتها بـ: pip install google-generativeai"
            )

        api_key = api_key or os.getenv("GEMINI_API_KEY")
        if not api_key:
            raise ValueError(
                "❌ GEMINI_API_KEY غير موجود.\n"
                "   أضفه في .env أو مرّره للـ constructor"
            )

        genai.configure(api_key=api_key)
        self.prompt_engine = PromptEngine()
        logger.info(
            f"✓ Gemini initialized | "
            f"Models: {[m.value for m in GeminiModel.fallback_chain()]}"
        )

    # ═══════════════════════════════════════════════════════════════
    # Model Management
    # ═══════════════════════════════════════════════════════════════
    def _get_model(
        self,
        model_name: str,
        temperature: float,
    ) -> Any:
        """الحصول على model instance (مع caching)."""
        cache_key = f"{model_name}_{temperature}"
        
        if cache_key not in self._models_cache:
            self._models_cache[cache_key] = genai.GenerativeModel(
                model_name=model_name,
                system_instruction=GeminiConstants.SYSTEM_INSTRUCTION,
                generation_config={
                    "temperature": temperature,
                    "max_output_tokens": GeminiConstants.MAX_OUTPUT_TOKENS,
                    "response_mime_type": "application/json",
                },
            )
        
        return self._models_cache[cache_key]

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
        توليد سكربت كامل عبر Gemini.
        
        Args:
            topic: موضوع الفيديو
            content_type: نوع المحتوى
            target_duration: المدة المستهدفة (30/45/60)
            mood: نمط الأسلوب (اختياري)
        
        Returns:
            dict يحتوي على السكربت الكامل
        
        Raises:
            ValueError: إذا كان الموضوع فارغاً
        """
        # ── Validation ──
        if not topic or not topic.strip():
            raise ValueError("الموضوع لا يمكن أن يكون فارغاً")
        
        topic = topic.strip()
        
        # ── Dry run mode ──
        if self.dry_run:
            return self._dry_run_script(topic, content_type, target_duration)
        
        # ── كشف الـ mood ──
        if mood is None:
            mood = self.detect_mood(topic, content_type)
        
        # ── بناء الـ prompt ──
        prompt = self.prompt_engine.build_script_prompt(
            topic=topic,
            mood=mood,
            content_type=content_type,
            target_duration=target_duration,
        )
        
        # ── توليد ──
        script = self._generate_with_retry(prompt, topic, target_duration, mood)
        
        # ── معلومات إضافية ──
        script.update({
            "music_mood": mood,
            "content_type": content_type,
            "target_duration": target_duration,
            "generated_by": script.get("generated_by", "gemini"),
        })
        
        return script

    def generate_batch(
        self,
        topics: list[str],
        content_type: ContentType = "motivational",
        target_duration: int = 45,
        max_workers: int = 3,
    ) -> list[dict[str, Any]]:
        """
        توليد عدة سكربتات (مع parallel processing).
        
        Args:
            topics: قائمة المواضيع
            content_type: نوع المحتوى
            target_duration: المدة
            max_workers: عدد الـ threads المتزامنة
        
        Returns:
            قائمة بالسكربتات
        """
        if not topics:
            return []
        
        # parallel processing
        results: list[Optional[dict]] = [None] * len(topics)
        
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            future_to_idx = {
                executor.submit(
                    self.generate_script,
                    topic, content_type, target_duration
                ): i
                for i, topic in enumerate(topics)
            }
            
            for i, future in enumerate(as_completed(future_to_idx), 1):
                idx = future_to_idx[future]
                topic = topics[idx]
                
                try:
                    results[idx] = future.result()
                    logger.info(f"✓ [{i}/{len(topics)}] {topic[:40]}")
                except Exception as e:
                    logger.error(f"❌ [{i}/{len(topics)}] فشل '{topic}': {e}")
                    results[idx] = self._fallback(topic, target_duration)
        
        return [r for r in results if r is not None]

    # ═══════════════════════════════════════════════════════════════
    # Internal: Generation Logic
    # ═══════════════════════════════════════════════════════════════
    def _generate_with_retry(
        self,
        prompt: str,
        topic: str,
        target_duration: int,
        mood: str,
    ) -> dict[str, Any]:
        """محاولة توليد السكربت مع إعادة المحاولة."""
        last_error = None
        fallback_chain = GeminiModel.fallback_chain()
        
        # ✅ MAX_RETRIES أصبح يساوي عدد الموديلات المتاحة
        max_attempts = min(GeminiConstants.MAX_RETRIES, len(fallback_chain))
        
        for attempt in range(1, max_attempts + 1):
            # rate limiting
            self.rate_limiter.wait_if_needed()
            
            # temperature عشوائية
            temp = round(
                random.uniform(GeminiConstants.TEMP_MIN, GeminiConstants.TEMP_MAX),
                2
            )
            
            # موديل مختلف لكل محاولة
            model_idx = min(attempt - 1, len(fallback_chain) - 1)
            model_name = fallback_chain[model_idx].value
            
            logger.info(
                f"🤖 [Gemini {attempt}/{max_attempts}] "
                f"{model_name} | temp={temp}"
            )
            
            try:
                model = self._get_model(model_name, temp)
                
                response = model.generate_content(
                    prompt,
                    safety_settings=GeminiConstants.SAFETY_SETTINGS,
                    request_options={"timeout": GeminiConstants.TIMEOUT_SECONDS},
                )
                
                if not response or not response.text:
                    raise ValueError("Gemini returned empty response")
                
                raw = response.text.strip()
                script = self._parse(raw, topic, target_duration)
                
                if script and self._valid(script):
                    self.stats.record_success(
                        model=model_name,
                        tokens=len(prompt.split()) + len(raw.split())
                    )
                    logger.info(
                        f"✓ نجح Gemini | {len(script['scenes'])} مشهد"
                    )
                    return script
                
                logger.warning("⚠ سكربت Gemini غير صالح، إعادة المحاولة...")
                self.stats.record_failure()
                
            except Exception as e:
                last_error = e
                self.stats.record_failure()
                logger.warning(f"⚠ فشلت محاولة {attempt}: {type(e).__name__}: {e}")
                
                if attempt < max_attempts:
                    sleep_time = GeminiConstants.RETRY_DELAY_BASE * attempt
                    logger.debug(f"   انتظار {sleep_time}s...")
                    time.sleep(sleep_time)
        
        # فشل كل المحاولات
        logger.error(f"❌ فشلت كل محاولات Gemini: {last_error}")
        self.stats.record_fallback()
        return self._fallback(topic, target_duration, mood)

    # ═══════════════════════════════════════════════════════════════
    # Mood Detection
    # ═══════════════════════════════════════════════════════════════
    def detect_mood(
        self,
        topic: str,
        content_type: str = "motivational"
    ) -> str:
        """كشف الـ mood المناسب من الموضوع."""
        normalized = self._norm(topic)
        
        for mood, keywords in MOOD_KEYWORDS.items():
            for kw in keywords:
                if self._norm(kw) in normalized:
                    logger.debug(f"Detected mood '{mood}' from keyword '{kw}'")
                    return mood
        
        return self.prompt_engine.get_mood_for_content(content_type)

    # ═══════════════════════════════════════════════════════════════
    # Parsing & Validation
    # ═══════════════════════════════════════════════════════════════
    def _parse(
        self,
        raw: str,
        topic: str,
        target_duration: int,
    ) -> Optional[dict[str, Any]]:
        """تحليل JSON من رد Gemini."""
        if not raw:
            return None
        
        # إزالة markdown
        raw = re.sub(r"```(?:json)?\s*", "", raw)
        raw = raw.replace("```", "").strip()
        
        # محاولة 1: parsing مباشر
        try:
            data = json.loads(raw)
            if self._valid(data):
                return self._clean(data)
        except json.JSONDecodeError as e:
            logger.debug(f"Direct parse failed: {e}")
        
        # محاولة 2: استخراج JSON object
        try:
            start = raw.find("{")
            end = raw.rfind("}") + 1
            if start != -1 and end > start:
                data = json.loads(raw[start:end])
                if self._valid(data):
                    return self._clean(data)
        except json.JSONDecodeError as e:
            logger.debug(f"Extracted parse failed: {e}")
        
        logger.warning("❌ فشل parsing رد Gemini")
        return None

    def _valid(self, d: dict) -> bool:
        """التحقق من صحة بنية السكربت."""
        if not isinstance(d, dict):
            return False
        
        required = ("title", "hook", "scenes", "cta", "full_text", "duration_estimate")
        if not all(k in d for k in required):
            missing = [k for k in required if k not in d]
            logger.debug(f"Missing keys: {missing}")
            return False
        
        scenes = d.get("scenes")
        if not isinstance(scenes, list) or len(scenes) == 0:
            return False
        
        return True

    def _clean(self, data: dict) -> dict:
        """تنظيف وتطبيع بيانات السكربت."""
        # تنظيف النصوص الأساسية
        for key in ("title", "hook", "cta", "full_text"):
            data[key] = self._norm_text(data.get(key, ""))
        
        # هاشتاجات
        hashtags = data.get("hashtags", [])
        data["hashtags"] = (
            [str(h).strip() for h in hashtags if h]
            if isinstance(hashtags, list)
            else []
        )
        
        # المشاهد
        data["scenes"] = [
            self._clean_scene(sc, i)
            for i, sc in enumerate(data.get("scenes", []))
            if self._norm_text(sc.get("text", ""))  # تجاهل الفارغ
        ]
        
        return data

    def _clean_scene(self, sc: dict, idx: int) -> dict:
        """تنظيف مشهد واحد."""
        text = self._norm_text(sc.get("text", ""))
        
        return {
            "id":              sc.get("id", idx),
            "text":            text,
            "duration":        self._safe_float(sc.get("duration"), 3.0),
            "pause_after":     self._safe_float(sc.get("pause_after"), 0.3),
            "type":            sc.get("type", "main"),
            "voice_tone":      sc.get("voice_tone", "intense"),
            "camera_motion":   sc.get("camera_motion", "slow_zoom"),
            "music_intensity": self._safe_float(sc.get("music_intensity"), 0.7),
            "transition":      sc.get("transition", "smooth_fade"),
            "energy":          self._safe_float(sc.get("energy"), 0.7),
            "visual_prompt":   sc.get("visual_prompt", ""),
            "emphasis":        sc.get("emphasis") or self._detect_emphasis(text),
        }

    # ═══════════════════════════════════════════════════════════════
    # Fallback System
    # ═══════════════════════════════════════════════════════════════
    def _fallback(
        self,
        topic: str,
        target_duration: int = 45,
        mood: str = "default",
    ) -> dict[str, Any]:
        """سكربت احتياطي عند فشل Gemini."""
        logger.warning(f"⚠ استخدام Gemini fallback | mood={mood}")
        
        scene_counts = {30: 6, 45: 8, 60: 10}
        target_scenes = scene_counts.get(target_duration, 8)
        
        # اختيار templates حسب الـ mood
        templates = FALLBACK_TEMPLATES.get(mood, FALLBACK_TEMPLATES["default"])
        formatted = [t.format(topic=topic) for t in templates]
        
        # اختيار عشوائي مع ضمان البداية والنهاية
        if len(formatted) > target_scenes:
            middle = random.sample(
                formatted[1:-1],
                min(target_scenes - 2, len(formatted) - 2)
            )
            selected = [formatted[0]] + middle + [formatted[-1]]
        else:
            selected = formatted[:target_scenes]
        
        scenes = [
            self._build_fallback_scene(text, i, len(selected), topic)
            for i, text in enumerate(selected)
        ]
        
        total_dur = min(
            sum(s["duration"] + s["pause_after"] for s in scenes),
            target_duration,
        )
        
        return {
            "title": topic,
            "hook": selected[0],
            "scenes": scenes,
            "cta": selected[-1],
            "full_text": "\n".join(selected),
            "duration_estimate": round(total_dur, 1),
            "mood": mood,
            "music_mood": mood,
            "hashtags": [],
            "is_fallback": True,
            "generated_by": "gemini_fallback",
        }

    def _build_fallback_scene(
        self,
        text: str,
        idx: int,
        total: int,
        topic: str,
    ) -> dict:
        """بناء مشهد fallback."""
        is_first = idx == 0
        is_last = idx == total - 1
        
        scene_type = "hook" if is_first else ("cta" if is_last else "build")
        
        return {
            "id": idx,
            "text": text,
            "duration": round(max(2.5, len(text.split()) * 0.5), 1),
            "pause_after": 0.7 if is_first else 0.35,
            "type": scene_type,
            "voice_tone": "intense" if is_first else "cold",
            "camera_motion": "slow_zoom",
            "music_intensity": 0.8 if is_first else 0.6,
            "transition": "smooth_fade",
            "energy": 0.95 if is_first else 0.7,
            "visual_prompt": f"cinematic dark dramatic scene about {topic}",
            "emphasis": self._detect_emphasis(text),
        }

    def _dry_run_script(
        self,
        topic: str,
        content_type: str,
        target_duration: int,
    ) -> dict[str, Any]:
        """سكربت وهمي للاختبار."""
        logger.info(f"🧪 DRY RUN script for: {topic}")
        return self._fallback(topic, target_duration, "default") | {
            "generated_by": "dry_run",
            "is_dry_run": True,
        }

    # ═══════════════════════════════════════════════════════════════
    # Utility Methods (Static)
    # ═══════════════════════════════════════════════════════════════
    @staticmethod
    def _norm(text: str) -> str:
        """تطبيع النص للمقارنة."""
        replacements = (
            ("أ", "ا"), ("إ", "ا"), ("آ", "ا"),
            ("ة", "ه"), ("ى", "ي"),
        )
        for old, new in replacements:
            text = text.replace(old, new)
        return text.strip()

    @staticmethod
    def _norm_text(text: str) -> str:
        """تنظيف النص."""
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

    @staticmethod
    def _safe_float(value: Any, default: float) -> float:
        """تحويل آمن لـ float."""
        try:
            return float(value) if value is not None else default
        except (ValueError, TypeError):
            return default

    @staticmethod
    def _detect_emphasis(text: str) -> list[dict]:
        """كشف الكلمات المهمة."""
        result = []
        for i, word in enumerate(text.split()):
            clean = re.sub(r"[^\w\u0600-\u06FF]", "", word)
            if any(t in clean for t in EMPHASIS_TRIGGERS):
                result.append({"word": word, "position": i})
        return result

    # ═══════════════════════════════════════════════════════════════
    # Statistics
    # ═══════════════════════════════════════════════════════════════
    def get_stats(self) -> UsageStats:
        """الحصول على إحصائيات الاستخدام."""
        return self.stats

    def print_stats(self):
        """طباعة الإحصائيات."""
        print(self.stats.summary())


# ═══════════════════════════════════════════════════════════════════
# اختبار سريع
# ═══════════════════════════════════════════════════════════════════
if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s | %(levelname)s | %(message)s"
    )
    
    print("=" * 60)
    print("🧪 Testing GeminiWriter v2.1 (DRY RUN)")
    print("=" * 60)
    
    # اختبار dry run (بدون API)
    writer = GeminiWriter(dry_run=True)
    
    # اختبار توليد واحد
    script = writer.generate_script(
        topic="كيف تتعلم بسرعة",
        content_type="educational",
        target_duration=45,
    )
    
    print(f"\n✅ Script generated:")
    print(f"   Title: {script['title']}")
    print(f"   Scenes: {len(script['scenes'])}")
    print(f"   Duration: {script['duration_estimate']}s")
    print(f"   Fallback: {script.get('is_fallback', False)}")
    
    # اختبار batch
    print(f"\n🧪 Testing batch generation...")
    scripts = writer.generate_batch(
        topics=["النجاح", "الفشل", "التطوير"],
        content_type="motivational",
    )
    print(f"   Generated: {len(scripts)} scripts")
    
    # طباعة الإحصائيات
    print()
    writer.print_stats()
