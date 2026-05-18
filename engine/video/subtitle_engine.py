"""
📝 Subtitle Engine v2.0 — Pro
═══════════════════════════════════════════════════════════════
مولّد بيانات الترجمات لـ Remotion

التحسينات v2.0:
  ✓ يدعم Whisper subtitles
  ✓ Style presets مع dataclasses
  ✓ Scene-aware styles
  ✓ توزيع دقيق للمدة
  ✓ Result dataclass
  ✓ Validation
═══════════════════════════════════════════════════════════════
"""

from __future__ import annotations

import os
import logging
import warnings
from enum import Enum
from dataclasses import dataclass, field, asdict
from typing import Optional, Union, Any

logger = logging.getLogger(__name__)


# ═══════════════════════════════════════════════════════════════════
# Enums
# ═══════════════════════════════════════════════════════════════════
class SubtitleStyle(str, Enum):
    """أنماط تصميم الترجمات."""
    CINEMATIC = "cinematic"
    MODERN = "modern"
    HIGHLIGHT = "highlight"
    MINIMAL = "minimal"
    BOLD = "bold"
    KARAOKE = "karaoke"


class SubtitlePosition(str, Enum):
    """مكان الترجمة."""
    TOP = "top"
    CENTER = "center"
    BOTTOM = "bottom"


# ═══════════════════════════════════════════════════════════════════
# Dataclasses
# ═══════════════════════════════════════════════════════════════════
@dataclass
class WordTiming:
    """توقيت كلمة."""
    text: str
    start: float
    end: float
    
    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class Subtitle:
    """ترجمة واحدة."""
    id: int
    text: str
    start: float
    end: float
    duration: float
    scene_id: int = 0
    words: list[WordTiming] = field(default_factory=list)
    style_override: Optional[str] = None
    
    def to_dict(self) -> dict:
        d = {
            "id": self.id,
            "text": self.text,
            "start": self.start,
            "end": self.end,
            "duration": self.duration,
            "sceneId": self.scene_id,
        }
        if self.words:
            d["words"] = [w.to_dict() for w in self.words]
        if self.style_override:
            d["styleOverride"] = self.style_override
        return d


@dataclass(frozen=True)
class StyleConfig:
    """إعدادات التصميم."""
    name: str
    font_size: int = 78
    font_weight: int = 900
    color: str = "#FFFFFF"
    background_color: str = "rgba(0,0,0,0.0)"
    text_shadow: str = "0 4px 20px rgba(0,0,0,0.95)"
    stroke_width: int = 2
    stroke_color: str = "#000000"
    glow_enabled: bool = True
    glow_color: str = "rgba(255,255,255,0.6)"
    glow_blur: int = 8
    padding: str = "0 60px"
    line_height: float = 1.4
    letter_spacing: str = "0em"
    border_radius: int = 0
    position: str = "bottom"
    position_offset: float = 0.78
    
    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "fontSize": self.font_size,
            "fontWeight": self.font_weight,
            "color": self.color,
            "backgroundColor": self.background_color,
            "textShadow": self.text_shadow,
            "stroke": {
                "width": self.stroke_width,
                "color": self.stroke_color,
            },
            "glow": {
                "enabled": self.glow_enabled,
                "color": self.glow_color,
                "blur": self.glow_blur,
            },
            "padding": self.padding,
            "lineHeight": self.line_height,
            "letterSpacing": self.letter_spacing,
            "borderRadius": self.border_radius,
            "position": self.position,
            "positionOffset": self.position_offset,
        }


@dataclass
class SubtitleResult:
    """نتيجة بناء الترجمات."""
    success: bool
    subtitles: list[Subtitle] = field(default_factory=list)
    style: Optional[StyleConfig] = None
    total_count: int = 0
    total_duration: float = 0.0
    avg_chars_per_subtitle: float = 0.0
    has_word_timings: bool = False
    source: str = "scenes"  # scenes / whisper
    error: Optional[str] = None
    
    def to_dict(self) -> dict:
        return {
            "subtitles": [s.to_dict() for s in self.subtitles],
            "style": self.style.to_dict() if self.style else None,
            "totalCount": self.total_count,
            "totalDuration": self.total_duration,
            "hasWordTimings": self.has_word_timings,
            "source": self.source,
        }
    
    def summary(self) -> str:
        return (
            f"📊 Subtitle Result:\n"
            f"   • Status: {'✅' if self.success else '❌'}\n"
            f"   • Count: {self.total_count}\n"
            f"   • Source: {self.source}\n"
            f"   • Duration: {self.total_duration:.1f}s\n"
            f"   • Style: {self.style.name if self.style else 'none'}\n"
            f"   • Word timings: {self.has_word_timings}"
        )


# ═══════════════════════════════════════════════════════════════════
# Style Presets
# ═══════════════════════════════════════════════════════════════════
STYLE_PRESETS: dict[str, StyleConfig] = {
    "cinematic": StyleConfig(
        name="cinematic",
        font_size=78, font_weight=900,
        color="#FFFFFF",
        text_shadow="0 4px 20px rgba(0,0,0,0.95), 0 0 40px rgba(0,0,0,0.8)",
        stroke_width=2, stroke_color="#000000",
        glow_enabled=True, glow_color="rgba(255,255,255,0.6)", glow_blur=8,
        padding="0 60px", line_height=1.4,
        position="bottom", position_offset=0.78,
    ),
    
    "modern": StyleConfig(
        name="modern",
        font_size=70, font_weight=700,
        color="#FFFFFF",
        background_color="rgba(0,0,0,0.55)",
        text_shadow="0 2px 8px rgba(0,0,0,0.9)",
        border_radius=16,
        padding="20px 40px", line_height=1.5,
        position="bottom", position_offset=0.85,
    ),
    
    "highlight": StyleConfig(
        name="highlight",
        font_size=85, font_weight=900,
        color="#FFD700",
        text_shadow="0 6px 25px rgba(0,0,0,0.95), 0 0 50px rgba(255,215,0,0.4)",
        stroke_width=3, stroke_color="#000000",
        padding="0 60px", line_height=1.3,
        position="center", position_offset=0.5,
    ),
    
    "minimal": StyleConfig(
        name="minimal",
        font_size=60, font_weight=600,
        color="#FFFFFF",
        text_shadow="0 2px 6px rgba(0,0,0,0.8)",
        padding="0 40px", line_height=1.5,
        position="bottom", position_offset=0.88,
    ),
    
    "bold": StyleConfig(
        name="bold",
        font_size=90, font_weight=900,
        color="#FFFFFF",
        background_color="rgba(0,0,0,0.7)",
        text_shadow="0 4px 12px rgba(0,0,0,0.9)",
        stroke_width=3, stroke_color="#000000",
        border_radius=12,
        padding="24px 48px", line_height=1.3,
        position="center", position_offset=0.5,
    ),
    
    "karaoke": StyleConfig(
        name="karaoke",
        font_size=72, font_weight=800,
        color="#FFFFFF",
        text_shadow="0 4px 15px rgba(0,0,0,0.95)",
        stroke_width=2, stroke_color="#000000",
        glow_enabled=True, glow_color="rgba(255,215,0,0.4)", glow_blur=10,
        padding="0 60px", line_height=1.4,
        position="bottom", position_offset=0.78,
    ),
}


# ═══════════════════════════════════════════════════════════════════
# Mappings
# ═══════════════════════════════════════════════════════════════════
# Scene type → Style override
SCENE_STYLE_MAP: dict[str, str] = {
    "hook":       "highlight",   # عنوان جذاب
    "peak":       "bold",        # لحظة قوية
    "cta":        "highlight",   # دعوة للعمل
    "intro":      "cinematic",
    "build":      "cinematic",
    "main":       "cinematic",
    "resolution": "cinematic",
    "outro":      "cinematic",
}


# ═══════════════════════════════════════════════════════════════════
# Constants
# ═══════════════════════════════════════════════════════════════════
class SubtitleConstants:
    """ثوابت."""
    
    DEFAULT_FONT_PRIMARY = "Cairo"
    DEFAULT_FONT_FALLBACKS = (
        "Tajawal", "Almarai", "Noto Sans Arabic", "sans-serif"
    )
    
    # Text splitting
    MAX_CHARS_PER_LINE = 35       # حرف
    MAX_WORDS_PER_CHUNK = 8       # كلمة
    MAX_CHUNK_DURATION = 3.5      # ثانية
    MIN_CHUNK_DURATION = 1.0      # ثانية
    
    # Word timing
    MIN_WORD_DURATION = 0.15
    
    # Reading speed (للتقدير)
    ARABIC_WPM = 150


# ═══════════════════════════════════════════════════════════════════
# Helpers
# ═══════════════════════════════════════════════════════════════════
def count_arabic_chars(text: str) -> int:
    """عدّ الحروف (للعربية والإنجليزية معاً)."""
    return len(text)


def build_font_family(
    primary: str = SubtitleConstants.DEFAULT_FONT_PRIMARY,
    fallbacks: tuple = SubtitleConstants.DEFAULT_FONT_FALLBACKS,
) -> str:
    """بناء font-family CSS."""
    quoted_fallbacks = ", ".join(f"'{f}'" for f in fallbacks)
    return f"'{primary}', {quoted_fallbacks}"


# ═══════════════════════════════════════════════════════════════════
# Main Class
# ═══════════════════════════════════════════════════════════════════
class SubtitleEngine:
    """مولّد بيانات الترجمات v2.0."""
    
    def __init__(
        self,
        width: int = 1080,
        height: int = 1920,
        default_style: str = "cinematic",
        font_size: Optional[int] = None,
        font_family: Optional[str] = None,
        enable_word_timings: bool = False,
    ):
        """
        Args:
            width, height: أبعاد الفيديو
            default_style: الـ style الافتراضي
            font_size: حجم الخط
            font_family: نوع الخط
            enable_word_timings: تفعيل توقيتات الكلمات (karaoke)
        """
        self.w = width
        self.h = height
        
        # Settings (مع env override)
        self.font_size = int(
            font_size or os.getenv("SUBTITLE_SIZE", "78")
        )
        self.font_family = (
            font_family or
            os.getenv("SUBTITLE_FONT", SubtitleConstants.DEFAULT_FONT_PRIMARY)
        )
        self.default_style = os.getenv("SUBTITLE_STYLE", default_style)
        self.enable_word_timings = (
            enable_word_timings or
            os.getenv("ENABLE_WORD_TIMINGS", "false").lower() == "true"
        )
        
        logger.info(
            f"📝 SubtitleEngine v2.0 | "
            f"Style: {self.default_style} | Size: {self.font_size}"
        )
    
    # ═══════════════════════════════════════════════════════════════
    # Validation
    # ═══════════════════════════════════════════════════════════════
    def _validate_style(self, style: str) -> str:
        if style not in STYLE_PRESETS:
            logger.warning(f"⚠ Style '{style}' غير معروف، استخدام 'cinematic'")
            return "cinematic"
        return style
    
    # ═══════════════════════════════════════════════════════════════
    # Main API (من scenes)
    # ═══════════════════════════════════════════════════════════════
    def build_from_scenes(
        self,
        scenes: list[dict],
        split_long_text: bool = True,
        scene_specific_styles: bool = False,
    ) -> SubtitleResult:
        """
        🎯 بناء ترجمات من scenes.
        
        Args:
            scenes: قائمة المشاهد
            split_long_text: تقسيم النصوص الطويلة
            scene_specific_styles: استخدام style مختلف لكل scene type
        """
        if not scenes:
            return SubtitleResult(
                success=False,
                error="No scenes provided",
            )
        
        subtitles: list[Subtitle] = []
        cumulative_time = 0.0
        sub_id = 0
        
        for scene_idx, scene in enumerate(scenes):
            text = scene.get("text", "").strip()
            duration = float(scene.get("duration", 3.0))
            pause = float(scene.get("pause_after", 0.3))
            scene_type = scene.get("type", "main")
            
            if not text:
                cumulative_time += duration + pause
                continue
            
            # تقسيم النصوص الطويلة
            if split_long_text and self._is_long_text(text):
                chunks = self._split_text(text, duration)
            else:
                chunks = [(text, duration)]
            
            # Style override
            style_override = (
                SCENE_STYLE_MAP.get(scene_type)
                if scene_specific_styles
                else None
            )
            
            # بناء subtitles
            chunk_start = cumulative_time
            for chunk_text, chunk_duration in chunks:
                subtitle = Subtitle(
                    id=sub_id,
                    text=chunk_text,
                    start=round(chunk_start, 3),
                    end=round(chunk_start + chunk_duration, 3),
                    duration=round(chunk_duration, 3),
                    scene_id=scene_idx,
                    style_override=style_override,
                )
                
                # Word timings
                if self.enable_word_timings:
                    subtitle.words = self._build_word_timings(
                        chunk_text, chunk_start, chunk_duration
                    )
                
                subtitles.append(subtitle)
                chunk_start += chunk_duration
                sub_id += 1
            
            cumulative_time += duration + pause
        
        # بناء النتيجة
        style = self._get_style_config(self.default_style)
        total_chars = sum(len(s.text) for s in subtitles)
        
        result = SubtitleResult(
            success=True,
            subtitles=subtitles,
            style=style,
            total_count=len(subtitles),
            total_duration=cumulative_time,
            avg_chars_per_subtitle=(
                total_chars / len(subtitles) if subtitles else 0
            ),
            has_word_timings=self.enable_word_timings,
            source="scenes",
        )
        
        logger.info(
            f"✓ {result.total_count} subtitles من {len(scenes)} scenes "
            f"({result.total_duration:.1f}s)"
        )
        return result
    
    # ═══════════════════════════════════════════════════════════════
    # 🆕 API من Whisper
    # ═══════════════════════════════════════════════════════════════
    def build_from_whisper(
        self,
        whisper_chunks: list[Union[dict, Any]],
        scene_specific_styles: bool = False,
    ) -> SubtitleResult:
        """
        🎯 بناء ترجمات من Whisper output.
        
        Args:
            whisper_chunks: من WhisperTranscriber (dicts أو SubtitleChunk objects)
            scene_specific_styles: استخدام style مختلف لكل scene
        """
        if not whisper_chunks:
            return SubtitleResult(
                success=False,
                error="No whisper chunks",
            )
        
        subtitles: list[Subtitle] = []
        
        for i, chunk in enumerate(whisper_chunks):
            # دعم dict و dataclass
            if isinstance(chunk, dict):
                text = chunk.get("text", "").strip()
                start = float(chunk.get("start", 0))
                end = float(chunk.get("end", 0))
                scene_id = chunk.get("sceneId", chunk.get("scene_id", i))
                words_data = chunk.get("words", [])
            else:
                # SubtitleChunk dataclass
                text = chunk.text.strip()
                start = chunk.start
                end = chunk.end
                scene_id = i
                words_data = chunk.words if hasattr(chunk, "words") else []
            
            if not text:
                continue
            
            # Style override (للـ scene الأول)
            style_override = None
            if scene_specific_styles and i == 0:
                style_override = "highlight"
            
            # بناء word timings
            words = []
            for w in words_data:
                if isinstance(w, dict):
                    words.append(WordTiming(
                        text=w.get("word", w.get("text", "")),
                        start=float(w.get("start", 0)),
                        end=float(w.get("end", 0)),
                    ))
                else:
                    # WordTiming dataclass
                    words.append(WordTiming(
                        text=w.word if hasattr(w, "word") else str(w),
                        start=w.start,
                        end=w.end,
                    ))
            
            subtitle = Subtitle(
                id=i,
                text=text,
                start=round(start, 3),
                end=round(end, 3),
                duration=round(end - start, 3),
                scene_id=scene_id,
                words=words,
                style_override=style_override,
            )
            
            subtitles.append(subtitle)
        
        # النتيجة
        style = self._get_style_config(self.default_style)
        total_duration = (
            max(s.end for s in subtitles) if subtitles else 0
        )
        total_chars = sum(len(s.text) for s in subtitles)
        has_words = any(s.words for s in subtitles)
        
        result = SubtitleResult(
            success=True,
            subtitles=subtitles,
            style=style,
            total_count=len(subtitles),
            total_duration=total_duration,
            avg_chars_per_subtitle=(
                total_chars / len(subtitles) if subtitles else 0
            ),
            has_word_timings=has_words,
            source="whisper",
        )
        
        logger.info(
            f"✓ {result.total_count} subtitles من Whisper "
            f"({result.total_duration:.1f}s)"
        )
        return result
    
    # ═══════════════════════════════════════════════════════════════
    # Text Splitting
    # ═══════════════════════════════════════════════════════════════
    def _is_long_text(self, text: str) -> bool:
        """فحص إذا النص طويل."""
        words = len(text.split())
        return (
            words > SubtitleConstants.MAX_WORDS_PER_CHUNK or
            len(text) > SubtitleConstants.MAX_CHARS_PER_LINE * 2
        )
    
    def _split_text(
        self,
        text: str,
        total_duration: float,
    ) -> list[tuple[str, float]]:
        """تقسيم نص مع توزيع دقيق للمدة."""
        words = text.split()
        if not words:
            return [(text, total_duration)]
        
        # تقسيم لـ chunks
        chunks_text = []
        current_chunk = []
        current_length = 0
        max_chars = SubtitleConstants.MAX_CHARS_PER_LINE * 2
        
        for word in words:
            word_length = len(word) + 1
            
            if (len(current_chunk) >= SubtitleConstants.MAX_WORDS_PER_CHUNK or
                current_length + word_length > max_chars):
                if current_chunk:
                    chunks_text.append(" ".join(current_chunk))
                current_chunk = [word]
                current_length = word_length
            else:
                current_chunk.append(word)
                current_length += word_length
        
        if current_chunk:
            chunks_text.append(" ".join(current_chunk))
        
        # 🆕 توزيع دقيق للمدة (يحافظ على total_duration)
        return self._distribute_duration(chunks_text, total_duration)
    
    def _distribute_duration(
        self,
        chunks_text: list[str],
        total_duration: float,
    ) -> list[tuple[str, float]]:
        """توزيع دقيق للمدة على chunks."""
        if not chunks_text:
            return []
        
        if len(chunks_text) == 1:
            return [(chunks_text[0], total_duration)]
        
        # توزيع حسب طول كل chunk
        total_chars = sum(len(c) for c in chunks_text)
        
        if total_chars == 0:
            # تقسيم متساوي
            equal_duration = total_duration / len(chunks_text)
            return [(c, equal_duration) for c in chunks_text]
        
        # توزيع نسبي
        raw_durations = [
            (len(c) / total_chars) * total_duration
            for c in chunks_text
        ]
        
        # تطبيق الحدود مع تصحيح
        durations = []
        excess = 0.0
        
        for dur in raw_durations:
            if dur < SubtitleConstants.MIN_CHUNK_DURATION:
                excess += SubtitleConstants.MIN_CHUNK_DURATION - dur
                durations.append(SubtitleConstants.MIN_CHUNK_DURATION)
            elif dur > SubtitleConstants.MAX_CHUNK_DURATION:
                excess -= dur - SubtitleConstants.MAX_CHUNK_DURATION
                durations.append(SubtitleConstants.MAX_CHUNK_DURATION)
            else:
                durations.append(dur)
        
        # توزيع الفائض/النقص على chunks متوسطة
        if abs(excess) > 0.01:
            adjustable = [
                i for i, d in enumerate(durations)
                if (SubtitleConstants.MIN_CHUNK_DURATION < d <
                    SubtitleConstants.MAX_CHUNK_DURATION)
            ]
            
            if adjustable:
                adjustment_per = excess / len(adjustable)
                for i in adjustable:
                    durations[i] = max(
                        SubtitleConstants.MIN_CHUNK_DURATION,
                        min(
                            SubtitleConstants.MAX_CHUNK_DURATION,
                            durations[i] + adjustment_per,
                        )
                    )
        
        return list(zip(chunks_text, durations))
    
    # ═══════════════════════════════════════════════════════════════
    # Word Timings (Karaoke)
    # ═══════════════════════════════════════════════════════════════
    def _build_word_timings(
        self,
        text: str,
        start_time: float,
        duration: float,
    ) -> list[WordTiming]:
        """بناء توقيتات كلمة بكلمة."""
        words = text.split()
        if not words:
            return []
        
        total_chars = sum(len(w) for w in words)
        if total_chars == 0:
            return []
        
        timings = []
        current_time = start_time
        
        for word in words:
            ratio = len(word) / total_chars
            word_duration = max(
                SubtitleConstants.MIN_WORD_DURATION,
                duration * ratio,
            )
            
            timings.append(WordTiming(
                text=word,
                start=round(current_time, 3),
                end=round(current_time + word_duration, 3),
            ))
            current_time += word_duration
        
        return timings
    
    # ═══════════════════════════════════════════════════════════════
    # Style Configs
    # ═══════════════════════════════════════════════════════════════
    def _get_style_config(self, preset: str) -> StyleConfig:
        """جلب style config (مع override)."""
        preset = self._validate_style(preset)
        base = STYLE_PRESETS[preset]
        
        # تطبيق font_size من الإعدادات
        if self.font_size != base.font_size:
            return StyleConfig(
                **{**asdict(base), "font_size": self.font_size}
            )
        
        return base
    
    def get_style_config(self, preset: Optional[str] = None) -> dict:
        """🆕 جلب style config للـ Remotion."""
        preset = preset or self.default_style
        config = self._get_style_config(preset)
        
        result = config.to_dict()
        result["fontFamily"] = build_font_family(self.font_family)
        result["direction"] = "rtl"
        result["textAlign"] = "center"
        
        return result
    
    # ═══════════════════════════════════════════════════════════════
    # Full Props (للـ Remotion)
    # ═══════════════════════════════════════════════════════════════
    def get_full_props(
        self,
        scenes: Optional[list[dict]] = None,
        whisper_chunks: Optional[list] = None,
        style_preset: Optional[str] = None,
        scene_specific_styles: bool = False,
    ) -> dict:
        """
        🎯 بناء كل props للـ Remotion.
        
        Args:
            scenes: المشاهد (إذا لم يكن هناك whisper)
            whisper_chunks: من Whisper (الأولوية)
            style_preset: نمط التصميم
            scene_specific_styles: styles مختلفة per scene
        """
        # الأولوية: Whisper
        if whisper_chunks:
            result = self.build_from_whisper(
                whisper_chunks,
                scene_specific_styles=scene_specific_styles,
            )
        elif scenes:
            result = self.build_from_scenes(
                scenes,
                scene_specific_styles=scene_specific_styles,
            )
        else:
            return {
                "subtitles": [],
                "style": self.get_style_config(),
                "totalCount": 0,
            }
        
        # Override style إذا محدد
        if style_preset:
            style_config = self._get_style_config(style_preset)
            result.style = style_config
        
        # تحويل لـ dict مع style الكامل
        output = result.to_dict()
        output["style"] = self.get_style_config(
            style_preset or self.default_style
        )
        
        return output
    
    # ═══════════════════════════════════════════════════════════════
    # Utility
    # ═══════════════════════════════════════════════════════════════
    @staticmethod
    def list_available_styles() -> list[str]:
        return list(STYLE_PRESETS.keys())
    
    @staticmethod
    def get_style_info(name: str) -> Optional[StyleConfig]:
        return STYLE_PRESETS.get(name)
    
    @staticmethod
    def estimate_reading_time(
        text: str,
        wpm: int = SubtitleConstants.ARABIC_WPM,
    ) -> float:
        """تقدير وقت القراءة."""
        words = len(text.split())
        return (words / wpm) * 60
    
    @staticmethod
    def clean_text(text: str) -> str:
        """تنظيف النص."""
        return " ".join(text.split())
    
    # ═══════════════════════════════════════════════════════════════
    # Backward Compatibility
    # ═══════════════════════════════════════════════════════════════
    def build_subtitles_data(
        self,
        scenes: list[dict],
        split_long_text: bool = True,
    ) -> list[dict]:
        """متوافق مع v1 - يُرجع list of dicts."""
        result = self.build_from_scenes(scenes, split_long_text)
        return [s.to_dict() for s in result.subtitles]
    
    def get_full_subtitle_props(
        self,
        scenes: list[dict],
        style_preset: Optional[str] = None,
    ) -> dict:
        """متوافق مع v1."""
        return self.get_full_props(
            scenes=scenes,
            style_preset=style_preset,
        )
    
    # ═══════════════════════════════════════════════════════════════
    # Deprecated
    # ═══════════════════════════════════════════════════════════════
    def render(self, *args, **kwargs):
        warnings.warn(
            "render() deprecated. Use Remotion components.",
            DeprecationWarning,
            stacklevel=2,
        )
        raise RuntimeError("Not supported in Remotion mode")


# ═══════════════════════════════════════════════════════════════════
# اختبار
# ═══════════════════════════════════════════════════════════════════
if __name__ == "__main__":
    import json
    
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s | %(levelname)s | %(message)s"
    )
    
    print("=" * 60)
    print("📝 Subtitle Engine v2.0")
    print("=" * 60)
    
    engine = SubtitleEngine(enable_word_timings=True)
    
    print(f"\n📋 Settings:")
    print(f"   • Style: {engine.default_style}")
    print(f"   • Font size: {engine.font_size}")
    print(f"   • Font family: {engine.font_family}")
    print(f"   • Word timings: {engine.enable_word_timings}")
    
    print(f"\n🎨 Available styles: {engine.list_available_styles()}")
    
    # اختبار من scenes
    test_scenes = [
        {
            "text": "السلام عليكم ورحمة الله",
            "duration": 3.0,
            "pause_after": 0.3,
            "type": "hook",
        },
        {
            "text": "هذا اختبار لمحرك الترجمات الجديد المتوافق مع Remotion",
            "duration": 5.0,
            "pause_after": 0.3,
            "type": "main",
        },
        {
            "text": "اشترك الآن",
            "duration": 2.0,
            "pause_after": 0.0,
            "type": "cta",
        },
    ]
    
    print("\n🧪 من scenes:")
    result = engine.build_from_scenes(
        test_scenes,
        scene_specific_styles=True,
    )
    print(result.summary())
    
    print("\n📝 Sample subtitle:")
    if result.subtitles:
        first = result.subtitles[0]
        print(json.dumps(first.to_dict(), indent=2, ensure_ascii=False))
    
    # اختبار من Whisper
    print("\n🎤 من Whisper:")
    whisper_chunks = [
        {
            "id": 0,
            "text": "مرحباً",
            "start": 0.0,
            "end": 1.0,
            "duration": 1.0,
            "words": [
                {"word": "مرحباً", "start": 0.0, "end": 1.0},
            ],
        },
        {
            "id": 1,
            "text": "كيف الحال",
            "start": 1.2,
            "end": 2.5,
            "duration": 1.3,
            "words": [
                {"word": "كيف", "start": 1.2, "end": 1.7},
                {"word": "الحال", "start": 1.8, "end": 2.5},
            ],
        },
    ]
    
    result = engine.build_from_whisper(whisper_chunks)
    print(result.summary())
