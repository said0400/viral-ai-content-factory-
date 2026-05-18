"""
🎬 Video Module v2.0 — تجهيز البيانات لـ Remotion
═══════════════════════════════════════════════════════════════
المحركات:
  • CinematicEditor   → جلب الفيديوهات + بناء props
  • SubtitleEngine    → بيانات الترجمات العربية
  • EffectsEngine     → إعدادات التأثيرات
  • TransitionEngine  → إعدادات الانتقالات

الاستخدام:
    from engine.video import build_complete_props
    
    result = build_complete_props(script, "audio.mp3")
    props = result.props
    
    # أو الـ orchestrator
    from engine.video import VideoOrchestrator
    
    orch = VideoOrchestrator()
    result = orch.build_props(script, "audio.mp3")
═══════════════════════════════════════════════════════════════
"""

from __future__ import annotations

import os
import time
import logging
from dataclasses import dataclass, field
from typing import Optional, Callable, TYPE_CHECKING, Any

logger = logging.getLogger(__name__)


# ═══════════════════════════════════════════════════════════════════
# Version
# ═══════════════════════════════════════════════════════════════════
__version__ = "2.0.0"


# ═══════════════════════════════════════════════════════════════════
# Eager Imports (الأساسيات)
# ═══════════════════════════════════════════════════════════════════
from engine.video.cinematic_editor import (
    CinematicEditor, CinematicResult, FootageResult,
)
from engine.video.subtitle_engine import (
    SubtitleEngine, SubtitleResult, Subtitle, WordTiming,
    StyleConfig, SubtitleStyle,
)


# ═══════════════════════════════════════════════════════════════════
# Lazy Imports (الاختيارية)
# ═══════════════════════════════════════════════════════════════════
if TYPE_CHECKING:
    from engine.video.effects_engine import (
        EffectsEngine, SceneEffects,
        ZoomConfig, ShakeConfig, GradeConfig,
    )
    from engine.video.transition_engine import (
        TransitionEngine, TransitionsResult,
        TransitionConfig, SceneTransition,
    )


def _lazy_import_effects():
    """استيراد EffectsEngine عند الحاجة."""
    try:
        from engine.video.effects_engine import (
            EffectsEngine, SceneEffects,
            ZoomConfig, ShakeConfig, GradeConfig,
        )
        return {
            "EffectsEngine": EffectsEngine,
            "SceneEffects": SceneEffects,
            "ZoomConfig": ZoomConfig,
            "ShakeConfig": ShakeConfig,
            "GradeConfig": GradeConfig,
        }, True
    except ImportError as e:
        logger.debug(f"EffectsEngine not available: {e}")
        return None, False


def _lazy_import_transitions():
    """استيراد TransitionEngine عند الحاجة."""
    try:
        from engine.video.transition_engine import (
            TransitionEngine, TransitionsResult,
            TransitionConfig, SceneTransition,
        )
        return {
            "TransitionEngine": TransitionEngine,
            "TransitionsResult": TransitionsResult,
            "TransitionConfig": TransitionConfig,
            "SceneTransition": SceneTransition,
        }, True
    except ImportError as e:
        logger.debug(f"TransitionEngine not available: {e}")
        return None, False


# ═══════════════════════════════════════════════════════════════════
# Dataclasses
# ═══════════════════════════════════════════════════════════════════
@dataclass
class VideoConfig:
    """إعدادات الفيديو."""
    width: int = 1080
    height: int = 1920
    fps: int = 30
    quality: str = "high"
    use_remotion: bool = True
    renderer: str = "remotion"
    
    @property
    def dimensions(self) -> tuple[int, int]:
        return (self.width, self.height)
    
    @classmethod
    def from_env(cls) -> "VideoConfig":
        """تحميل من env."""
        return cls(
            width=int(os.getenv("VIDEO_WIDTH", "1080")),
            height=int(os.getenv("VIDEO_HEIGHT", "1920")),
            fps=int(os.getenv("VIDEO_FPS", "30")),
            quality=os.getenv("VIDEO_QUALITY", "high"),
            use_remotion=os.getenv("USE_REMOTION", "true").lower() == "true",
            renderer=os.getenv("RENDERER", "remotion"),
        )
    
    def to_dict(self) -> dict:
        return {
            "width": self.width,
            "height": self.height,
            "fps": self.fps,
            "quality": self.quality,
            "useRemotion": self.use_remotion,
            "renderer": self.renderer,
        }


@dataclass
class CompletePropsResult:
    """نتيجة بناء كل البيانات."""
    success: bool
    props: dict = field(default_factory=dict)
    total_scenes: int = 0
    total_subtitles: int = 0
    total_transitions: int = 0
    has_effects: bool = False
    has_whisper: bool = False
    cinematic_result: Optional[CinematicResult] = None
    subtitle_result: Optional[SubtitleResult] = None
    processing_time: float = 0.0
    error: Optional[str] = None
    
    def summary(self) -> str:
        return (
            f"📊 Complete Props Result:\n"
            f"   • Status: {'✅' if self.success else '❌'}\n"
            f"   • Scenes: {self.total_scenes}\n"
            f"   • Subtitles: {self.total_subtitles} "
            f"({'Whisper' if self.has_whisper else 'Scenes'})\n"
            f"   • Transitions: {self.total_transitions}\n"
            f"   • Effects: {'✓' if self.has_effects else '✗'}\n"
            f"   • Time: {self.processing_time:.1f}s"
        )


# ═══════════════════════════════════════════════════════════════════
# Engine Availability
# ═══════════════════════════════════════════════════════════════════
def is_effects_available() -> bool:
    """فحص توفر EffectsEngine."""
    _, available = _lazy_import_effects()
    return available


def is_transitions_available() -> bool:
    """فحص توفر TransitionEngine."""
    _, available = _lazy_import_transitions()
    return available


def list_available_engines() -> dict:
    """قائمة المحركات وحالتها."""
    return {
        "cinematic_editor": {
            "available": True,
            "mode": "remotion",
            "description": "Build props + fetch footage",
        },
        "subtitle_engine": {
            "available": True,
            "mode": "remotion",
            "description": "Arabic subtitles (JSON)",
        },
        "effects_engine": {
            "available": is_effects_available(),
            "mode": "remotion",
            "description": "Effects configs (Zoom, Shake, Grade)",
        },
        "transition_engine": {
            "available": is_transitions_available(),
            "mode": "remotion",
            "description": "Transitions configs",
        },
    }


# ═══════════════════════════════════════════════════════════════════
# 🆕 Video Orchestrator
# ═══════════════════════════════════════════════════════════════════
class VideoOrchestrator:
    """منسّق شامل لكل محركات الفيديو."""
    
    def __init__(
        self,
        cache_enabled: bool = True,
        use_whisper: bool = True,
        scene_specific_styles: bool = True,
    ):
        """
        Args:
            cache_enabled: تفعيل caching
            use_whisper: استخدام Whisper للترجمات
            scene_specific_styles: styles مختلفة per scene
        """
        self.cache_enabled = cache_enabled
        self.use_whisper = use_whisper
        self.scene_specific_styles = scene_specific_styles
        
        # تهيئة المحركات
        self.editor = CinematicEditor(cache_enabled=cache_enabled)
        self.subtitle_engine = SubtitleEngine()
        
        # Lazy load المحركات الاختيارية
        self._effects_engine = None
        self._transition_engine = None
        
        logger.info(
            f"🎬 VideoOrchestrator v2.0 | "
            f"Cache: {cache_enabled} | "
            f"Whisper: {use_whisper}"
        )
    
    @property
    def effects_engine(self):
        """Lazy load EffectsEngine."""
        if self._effects_engine is None:
            classes, available = _lazy_import_effects()
            if available:
                self._effects_engine = classes["EffectsEngine"]()
        return self._effects_engine
    
    @property
    def transition_engine(self):
        """Lazy load TransitionEngine."""
        if self._transition_engine is None:
            classes, available = _lazy_import_transitions()
            if available:
                self._transition_engine = classes["TransitionEngine"]()
        return self._transition_engine
    
    def build_props(
        self,
        script: dict,
        audio_path: str,
        progress_callback: Optional[Callable[[float, str], None]] = None,
    ) -> CompletePropsResult:
        """
        🎯 بناء كل البيانات لـ Remotion.
        
        Args:
            script: السكربت
            audio_path: مسار الصوت
            progress_callback: callback للتقدم
        
        Returns:
            CompletePropsResult
        """
        start_time = time.time()
        
        # Validation
        scenes = script.get("scenes", [])
        if not scenes:
            return CompletePropsResult(
                success=False,
                error="No scenes in script",
            )
        
        mood = script.get("music_mood", "motivation")
        
        logger.info(
            f"🎬 Building props | "
            f"{len(scenes)} scenes | mood: {mood}"
        )
        
        if progress_callback:
            progress_callback(0.05, "Starting...")
        
        try:
            # 1️⃣ Cinematic Editor (يجلب الفيديوهات + Whisper)
            if progress_callback:
                progress_callback(0.1, "Building cinematic props...")
            
            cinematic_result = self.editor.build_props_for_remotion(
                script=script,
                audio_path=audio_path,
                progress_callback=lambda p, msg: (
                    progress_callback(0.1 + p * 0.5, msg)
                    if progress_callback else None
                ),
            )
            
            if not cinematic_result.success:
                return CompletePropsResult(
                    success=False,
                    error=cinematic_result.error,
                    processing_time=time.time() - start_time,
                )
            
            props = cinematic_result.props
            
            # 2️⃣ Subtitles (محسّن - يدعم Whisper)
            if progress_callback:
                progress_callback(0.65, "Building subtitles...")
            
            # تحقق إذا كانت subtitles من Whisper في props
            existing_subs = props.get("subtitles", [])
            has_whisper = (
                len(existing_subs) > 0 and
                props.get("design", {}).get("subtitleMode") == "tiktok"
            )
            
            if has_whisper:
                # استخدم Whisper subtitles
                subtitle_result = self.subtitle_engine.build_from_whisper(
                    whisper_chunks=existing_subs,
                    scene_specific_styles=self.scene_specific_styles,
                )
            else:
                # ابنِ من scenes
                subtitle_result = self.subtitle_engine.build_from_scenes(
                    scenes=scenes,
                    scene_specific_styles=self.scene_specific_styles,
                )
            
            # تحديث subtitles في props
            props["subtitles"] = [
                s.to_dict() for s in subtitle_result.subtitles
            ]
            props["subtitleStyle"] = self.subtitle_engine.get_style_config()
            
            # 3️⃣ Effects (اختياري)
            has_effects = False
            if self.effects_engine:
                if progress_callback:
                    progress_callback(0.8, "Adding effects...")
                
                # Global effects
                props["effects"] = self.effects_engine.get_global_effects(
                    mood=mood
                )
                
                # Per-scene effects
                all_effects = self.effects_engine.get_effects_for_all_scenes(
                    scenes=scenes,
                    mood=mood,
                )
                
                # تحديث كل scene
                for i, scene_data in enumerate(props.get("scenes", [])):
                    if i < len(all_effects):
                        scene_data["effectsConfig"] = all_effects[i].to_dict()
                
                has_effects = True
            
            # 4️⃣ Transitions (اختياري)
            transitions_count = 0
            if self.transition_engine:
                if progress_callback:
                    progress_callback(0.9, "Building transitions...")
                
                trans_result = self.transition_engine.build_for_scenes(
                    scenes=scenes,
                    mood=mood,
                )
                
                props["transitions"] = [
                    t.to_dict() for t in trans_result.transitions
                ]
                transitions_count = trans_result.total_count
            
            # 5️⃣ Meta info
            props["meta"] = {
                "totalScenes": len(scenes),
                "totalSubtitles": subtitle_result.total_count,
                "totalTransitions": transitions_count,
                "hasEffects": has_effects,
                "hasWhisper": has_whisper,
                "mood": mood,
                "engines": list_available_engines(),
                "version": __version__,
            }
            
            # النتيجة
            result = CompletePropsResult(
                success=True,
                props=props,
                total_scenes=len(scenes),
                total_subtitles=subtitle_result.total_count,
                total_transitions=transitions_count,
                has_effects=has_effects,
                has_whisper=has_whisper,
                cinematic_result=cinematic_result,
                subtitle_result=subtitle_result,
                processing_time=time.time() - start_time,
            )
            
            if progress_callback:
                progress_callback(1.0, "Done!")
            
            logger.info(result.summary())
            return result
            
        except Exception as e:
            logger.error(f"❌ Build failed: {e}", exc_info=True)
            return CompletePropsResult(
                success=False,
                error=str(e),
                processing_time=time.time() - start_time,
            )


# ═══════════════════════════════════════════════════════════════════
# Convenience Function (Backward Compatible)
# ═══════════════════════════════════════════════════════════════════
def build_complete_props(
    script: dict,
    audio_path: str,
    output_dir: Optional[str] = None,
    use_whisper: bool = True,
    scene_specific_styles: bool = True,
    progress_callback: Optional[Callable[[float, str], None]] = None,
) -> dict:
    """
    🎯 بناء كل البيانات (للتوافق الخلفي).
    
    Returns:
        dict (للتوافق - استخدم VideoOrchestrator للحصول على Result)
    """
    orchestrator = VideoOrchestrator(
        use_whisper=use_whisper,
        scene_specific_styles=scene_specific_styles,
    )
    
    result = orchestrator.build_props(
        script=script,
        audio_path=audio_path,
        progress_callback=progress_callback,
    )
    
    if not result.success:
        raise RuntimeError(f"Build failed: {result.error}")
    
    return result.props


# ═══════════════════════════════════════════════════════════════════
# Config Helpers (مع caching)
# ═══════════════════════════════════════════════════════════════════
_cached_config: Optional[VideoConfig] = None


def get_video_config() -> VideoConfig:
    """جلب إعدادات الفيديو (cached)."""
    global _cached_config
    if _cached_config is None:
        _cached_config = VideoConfig.from_env()
    return _cached_config


def reload_video_config() -> VideoConfig:
    """إعادة تحميل من env."""
    global _cached_config
    _cached_config = VideoConfig.from_env()
    return _cached_config


def get_default_dimensions() -> tuple[int, int]:
    """الأبعاد."""
    return get_video_config().dimensions


def get_default_fps() -> int:
    """FPS."""
    return get_video_config().fps


def get_default_quality() -> str:
    """الجودة."""
    return get_video_config().quality


# ═══════════════════════════════════════════════════════════════════
# Diagnostic
# ═══════════════════════════════════════════════════════════════════
def get_info() -> dict:
    """معلومات الموديول."""
    config = get_video_config()
    return {
        "version": __version__,
        "config": config.to_dict(),
        "engines": list_available_engines(),
    }


def print_status() -> None:
    """طباعة حالة الموديول."""
    info = get_info()
    
    print("=" * 60)
    print(f"🎬 Video Module v{info['version']}")
    print("=" * 60)
    
    config = info["config"]
    print(f"\n📐 Config:")
    print(f"   • Dimensions: {config['width']}x{config['height']}")
    print(f"   • FPS: {config['fps']}")
    print(f"   • Quality: {config['quality']}")
    print(f"   • Renderer: {config['renderer']}")
    
    print(f"\n📦 Engines:")
    for name, engine_info in info["engines"].items():
        status = "✅" if engine_info["available"] else "❌"
        print(f"   {status} {name:25s}")
        print(f"      → {engine_info['description']}")
    
    print("=" * 60)


# ═══════════════════════════════════════════════════════════════════
# Lazy Loading
# ═══════════════════════════════════════════════════════════════════
def __getattr__(name: str):
    """Lazy import للـ classes الاختيارية."""
    
    # Effects
    effects_classes, effects_ok = _lazy_import_effects()
    if effects_ok and effects_classes and name in effects_classes:
        return effects_classes[name]
    
    # Transitions
    transitions_classes, trans_ok = _lazy_import_transitions()
    if trans_ok and transitions_classes and name in transitions_classes:
        return transitions_classes[name]
    
    raise AttributeError(
        f"module 'engine.video' has no attribute '{name}'"
    )


# ═══════════════════════════════════════════════════════════════════
# Public API
# ═══════════════════════════════════════════════════════════════════
__all__ = [
    # Version
    "__version__",
    
    # Core engines
    "CinematicEditor",
    "CinematicResult",
    "FootageResult",
    
    "SubtitleEngine",
    "SubtitleResult",
    "Subtitle",
    "WordTiming",
    "StyleConfig",
    "SubtitleStyle",
    
    # Optional engines (lazy)
    "EffectsEngine",
    "SceneEffects",
    "ZoomConfig",
    "ShakeConfig",
    "GradeConfig",
    
    "TransitionEngine",
    "TransitionsResult",
    "TransitionConfig",
    "SceneTransition",
    
    # Orchestrator
    "VideoOrchestrator",
    "CompletePropsResult",
    "VideoConfig",
    
    # Functions
    "build_complete_props",
    
    # Helpers
    "list_available_engines",
    "is_effects_available",
    "is_transitions_available",
    "get_video_config",
    "reload_video_config",
    "get_default_dimensions",
    "get_default_fps",
    "get_default_quality",
    "get_info",
    "print_status",
]


# ═══════════════════════════════════════════════════════════════════
# اختبار
# ═══════════════════════════════════════════════════════════════════
if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s | %(levelname)s | %(message)s"
    )
    
    print_status()
    
    print("\n🧪 Testing imports...")
    print(f"   ✅ CinematicEditor: {CinematicEditor.__name__}")
    print(f"   ✅ SubtitleEngine: {SubtitleEngine.__name__}")
    
    if is_effects_available():
        from engine.video import EffectsEngine
        print(f"   ✅ EffectsEngine: {EffectsEngine.__name__}")
    
    if is_transitions_available():
        from engine.video import TransitionEngine
        print(f"   ✅ TransitionEngine: {TransitionEngine.__name__}")
    
    print("\n✅ All imports work!")
