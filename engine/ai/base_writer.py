"""
🤖 Base AI Writer
═══════════════════════════════════════════════════════════════
الكلاس الأساسي لجميع كتّاب AI

يحتوي على:
  ✓ Parsing & Validation منطق مشترك
  ✓ Text normalization
  ✓ Mood detection
  ✓ Fallback generation
  ✓ Stats tracking
  ✓ Rate limiting
═══════════════════════════════════════════════════════════════
"""

from __future__ import annotations

import re
import json
import time
import random
import logging
from abc import ABC, abstractmethod
from threading import Lock
from dataclasses import dataclass, field
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Optional, Any

from engine.ai.prompt_engine import PromptEngine
from engine.ai.constants import (
    ContentType,
    MOOD_KEYWORDS,
    EMPHASIS_TRIGGERS,
    FALLBACK_TEMPLATES,
    SCENE_COUNTS_BY_DURATION,
)

logger = logging.getLogger(__name__)


# ═══════════════════════════════════════════════════════════════════
# Usage Stats
# ═══════════════════════════════════════════════════════════════════
@dataclass
class WriterStats:
    """إحصائيات الاستخدام."""
    provider: str = ""
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
            f"📊 {self.provider} Usage:\n"
            f"   • Total: {self.total_requests}\n"
            f"   • Success: {self.successful_requests} ({self.success_rate:.1f}%)\n"
            f"   • Failed: {self.failed_requests}\n"
            f"   • Fallback: {self.fallback_used}\n"
            f"   • Tokens (est): ~{self.total_tokens_estimate}\n"
            f"   • By Model: {self.by_model}"
        )


# ═══════════════════════════════════════════════════════════════════
# Rate Limiter
# ═══════════════════════════════════════════════════════════════════
class RateLimiter:
    """منع تجاوز حدود API."""
    
    def __init__(self, max_calls_per_minute: int = 60):
        self.max_calls = max_calls_per_minute
        self.calls: list[float] = []
        self.lock = Lock()
    
    def wait_if_needed(self):
        with self.lock:
            now = time.time()
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
# Base Writer (Abstract)
# ═══════════════════════════════════════════════════════════════════
class BaseAIWriter(ABC):
    """الكلاس الأساسي لكتّاب AI."""
    
    PROVIDER_NAME: str = "base"
    
    def __init__(
        self,
        rate_limit: int = 60,
        dry_run: bool = False,
    ):
        self.dry_run = dry_run
        self.stats = WriterStats(provider=self.PROVIDER_NAME)
        self.rate_limiter = RateLimiter(rate_limit)
        self.prompt_engine = PromptEngine()
        
        if not dry_run:
            self._init_client()
    
    # ── Abstract Methods (يجب تطبيقها في الـ subclasses) ──
    @abstractmethod
    def _init_client(self) -> None:
        """تهيئة client الخاص بالمزود."""
        pass
    
    @abstractmethod
    def _call_api(
        self,
        prompt: str,
        model: str,
        temperature: float,
    ) -> str:
        """استدعاء API وإرجاع النص الخام."""
        pass
    
    @abstractmethod
    def _get_models_chain(self) -> list[str]:
        """قائمة الموديلات (بالترتيب)."""
        pass
    
    # ═══════════════════════════════════════════════════════════════
    # Public API (مشتركة)
    # ═══════════════════════════════════════════════════════════════
    def generate_script(
        self,
        topic: str,
        content_type: ContentType = "motivational",
        target_duration: int = 45,
        mood: Optional[str] = None,
    ) -> dict[str, Any]:
        """توليد سكربت كامل."""
        # Validation
        if not topic or not topic.strip():
            raise ValueError("الموضوع لا يمكن أن يكون فارغاً")
        topic = topic.strip()
        
        # Dry run
        if self.dry_run:
            return self._dry_run_script(topic, content_type, target_duration)
        
        # كشف mood
        if mood is None:
            mood = self.detect_mood(topic, content_type)
        
        # بناء prompt
        prompt = self.prompt_engine.build_script_prompt(
            topic=topic,
            mood=mood,
            content_type=content_type,
            target_duration=target_duration,
        )
        
        # توليد
        script = self._generate_with_retry(
            prompt, topic, target_duration, mood
        )
        
        # إضافة معلومات
        script.update({
            "music_mood": mood,
            "content_type": content_type,
            "target_duration": target_duration,
            "generated_by": script.get("generated_by", self.PROVIDER_NAME),
        })
        
        return script
    
    def generate_batch(
        self,
        topics: list[str],
        content_type: ContentType = "motivational",
        target_duration: int = 45,
        max_workers: int = 3,
    ) -> list[dict[str, Any]]:
        """توليد عدة سكربتات (parallel)."""
        if not topics:
            return []
        
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
                    logger.error(
                        f"❌ [{i}/{len(topics)}] فشل '{topic}': {e}"
                    )
                    results[idx] = self._fallback(topic, target_duration)
        
        return [r for r in results if r is not None]
    
    # ═══════════════════════════════════════════════════════════════
    # Retry Logic
    # ═══════════════════════════════════════════════════════════════
    def _generate_with_retry(
        self,
        prompt: str,
        topic: str,
        target_duration: int,
        mood: str,
        max_retries: int = 3,
        retry_delay: int = 2,
    ) -> dict[str, Any]:
        """محاولة التوليد مع retry."""
        last_error = None
        models = self._get_models_chain()
        
        for attempt in range(1, max_retries + 1):
            self.rate_limiter.wait_if_needed()
            
            temp = round(random.uniform(0.72, 0.95), 2)
            model_idx = min(attempt - 1, len(models) - 1)
            model = models[model_idx]
            
            logger.info(
                f"🤖 [{self.PROVIDER_NAME} {attempt}/{max_retries}] "
                f"{model} | temp={temp}"
            )
            
            try:
                raw = self._call_api(prompt, model, temp)
                
                if not raw:
                    raise ValueError(f"{self.PROVIDER_NAME} returned empty")
                
                script = self._parse(raw, topic, target_duration)
                
                if script and self._valid(script):
                    self.stats.record_success(
                        model=model,
                        tokens=len(prompt.split()) + len(raw.split())
                    )
                    logger.info(
                        f"✓ نجح {self.PROVIDER_NAME} | "
                        f"{len(script['scenes'])} مشهد"
                    )
                    return script
                
                logger.warning("⚠ سكربت غير صالح، إعادة المحاولة...")
                self.stats.record_failure()
                
            except Exception as e:
                last_error = e
                self.stats.record_failure()
                logger.warning(
                    f"⚠ فشلت محاولة {attempt}: {type(e).__name__}: {e}"
                )
                
                if attempt < max_retries:
                    time.sleep(retry_delay * attempt)
        
        logger.error(
            f"❌ فشلت كل محاولات {self.PROVIDER_NAME}: {last_error}"
        )
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
        """كشف الـ mood من الموضوع."""
        normalized = self._norm(topic)
        
        for mood, keywords in MOOD_KEYWORDS.items():
            for kw in keywords:
                if self._norm(kw) in normalized:
                    return mood
        
        return self.prompt_engine.get_mood_for_content(content_type)
    
    # ═══════════════════════════════════════════════════════════════
    # Parsing & Validation (مشتركة)
    # ═══════════════════════════════════════════════════════════════
    def _parse(
        self,
        raw: str,
        topic: str,
        target_duration: int,
    ) -> Optional[dict[str, Any]]:
        """تحليل JSON."""
        if not raw:
            return None
        
        raw = re.sub(r"```(?:json)?\s*", "", raw)
        raw = raw.replace("```", "").strip()
        
        # محاولة 1: مباشر
        try:
            data = json.loads(raw)
            if self._valid(data):
                return self._clean(data)
        except json.JSONDecodeError:
            pass
        
        # محاولة 2: استخراج
        try:
            start = raw.find("{")
            end = raw.rfind("}") + 1
            if start != -1 and end > start:
                data = json.loads(raw[start:end])
                if self._valid(data):
                    return self._clean(data)
        except json.JSONDecodeError:
            pass
        
        return None
    
    def _valid(self, d: dict) -> bool:
        """فحص بنية السكربت."""
        if not isinstance(d, dict):
            return False
        required = (
            "title", "hook", "scenes", "cta",
            "full_text", "duration_estimate"
        )
        if not all(k in d for k in required):
            return False
        scenes = d.get("scenes")
        return isinstance(scenes, list) and len(scenes) > 0
    
    def _clean(self, data: dict) -> dict:
        """تنظيف السكربت."""
        for key in ("title", "hook", "cta", "full_text"):
            data[key] = self._norm_text(data.get(key, ""))
        
        hashtags = data.get("hashtags", [])
        data["hashtags"] = (
            [str(h).strip() for h in hashtags if h]
            if isinstance(hashtags, list)
            else []
        )
        
        data["scenes"] = [
            self._clean_scene(sc, i)
            for i, sc in enumerate(data.get("scenes", []))
            if self._norm_text(sc.get("text", ""))
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
    # Fallback (مشترك)
    # ═══════════════════════════════════════════════════════════════
    def _fallback(
        self,
        topic: str,
        target_duration: int = 45,
        mood: str = "default",
    ) -> dict[str, Any]:
        """سكربت احتياطي."""
        logger.warning(
            f"⚠ استخدام {self.PROVIDER_NAME} fallback | mood={mood}"
        )
        
        target_scenes = SCENE_COUNTS_BY_DURATION.get(target_duration, 8)
        templates = FALLBACK_TEMPLATES.get(
            mood, FALLBACK_TEMPLATES["default"]
        )
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
            "generated_by": f"{self.PROVIDER_NAME}_fallback",
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
        """سكربت وهمي."""
        logger.info(f"🧪 DRY RUN: {topic}")
        return self._fallback(topic, target_duration, "default") | {
            "generated_by": f"{self.PROVIDER_NAME}_dry_run",
            "is_dry_run": True,
        }
    
    # ═══════════════════════════════════════════════════════════════
    # Utility Methods (Static)
    # ═══════════════════════════════════════════════════════════════
    @staticmethod
    def _norm(text: str) -> str:
        """تطبيع للمقارنة."""
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
        for ch in ("\u200f", "\u200e", "\ufeff"):
            text = text.replace(ch, "")
        text = re.sub(r"[ـ]+", "", text)
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
    # Stats
    # ═══════════════════════════════════════════════════════════════
    def get_stats(self) -> WriterStats:
        return self.stats
    
    def print_stats(self):
        print(self.stats.summary())
