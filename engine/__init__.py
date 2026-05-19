"""
🎬 Viral AI Content Factory v2.0
═══════════════════════════════════════════════════════════════
محرك توليد فيديوهات Shorts عربية احترافية بالذكاء الاصطناعي

📦 Modules:
  • ai      → توليد السكربتات (Groq + Gemini)
  • voice   → توليد ومعالجة الصوت (Edge + ElevenLabs + Gemini + Groq)
  • video   → تحرير الفيديو (cinematic, effects, subtitles)
  • render  → التصدير النهائي (Remotion + FFmpeg)

الاستخدام الأساسي:
    from engine import ContentFactory
    
    factory = ContentFactory()
    result = factory.generate(
        topic="الطموح والنجاح",
        target_duration=45,
    )

الاستخدام السريع:
    from engine import quick_generate
    
    video_path = quick_generate("الطموح والنجاح")

🌐 Repository: https://github.com/yourusername/viral-ai-factory
👤 Author: AI Shorts Generator
═══════════════════════════════════════════════════════════════
"""

from __future__ import annotations

import os
import sys
import logging
from pathlib import Path
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional, Callable, Any, TYPE_CHECKING

# ═══════════════════════════════════════════════════════════════════
# Metadata
# ═══════════════════════════════════════════════════════════════════
__version__ = "2.0.0"
__author__ = "AI Shorts Generator"
__license__ = "MIT"

PROJECT_NAME = "Viral AI Content Factory"
PROJECT_DESCRIPTION = "Arabic Cinematic Shorts Generator"


# ═══════════════════════════════════════════════════════════════════
# Logger Setup
# ═══════════════════════════════════════════════════════════════════
logger = logging.getLogger("engine")


def setup_logging(
    level: str = "INFO",
    format_str: Optional[str] = None,
    log_file: Optional[str] = None,
) -> None:
    """
    🎯 إعداد logging موحّد.
    
    Args:
        level: DEBUG / INFO / WARNING / ERROR
        format_str: تنسيق مخصص
        log_file: حفظ في ملف (اختياري)
    """
    log_format = format_str or (
        "%(asctime)s | %(levelname)-7s | %(name)s | %(message)s"
    )
    
    handlers = [logging.StreamHandler(sys.stdout)]
    
    if log_file:
        Path(log_file).parent.mkdir(parents=True, exist_ok=True)
        handlers.append(logging.FileHandler(log_file, encoding="utf-8"))
    
    logging.basicConfig(
        level=getattr(logging, level.upper()),
        format=log_format,
        handlers=handlers,
        force=True,  # override existing config
    )


# ═══════════════════════════════════════════════════════════════════
# Constants
# ═══════════════════════════════════════════════════════════════════
# Project Root
PROJECT_ROOT = Path(__file__).parent.parent.resolve()

# Engine paths
ENGINE_DIR = Path(__file__).parent.resolve()
ASSETS_DIR = ENGINE_DIR / "assets"
FONTS_DIR = ASSETS_DIR / "fonts"
MUSIC_DIR = ASSETS_DIR / "music"
SFX_DIR = ASSETS_DIR / "sfx"

# Default output directories
TEMP_DIR = Path(os.getenv("TEMP_DIR", PROJECT_ROOT / "temp")).resolve()
OUTPUT_DIR = Path(os.getenv("OUTPUT_DIR", PROJECT_ROOT / "output")).resolve()

# Remotion
REMOTION_DIR = Path(
    os.getenv("REMOTION_DIR", PROJECT_ROOT / "remotion")
).resolve()

# Video defaults
DEFAULT_WIDTH = 1080
DEFAULT_HEIGHT = 1920
DEFAULT_FPS = 30

# Duration options (مدعومة)
SUPPORTED_DURATIONS = (30, 45, 60)
DEFAULT_DURATION = 45


# ═══════════════════════════════════════════════════════════════════
# Enums
# ═══════════════════════════════════════════════════════════════════
class ContentType(str, Enum):
    """نوع المحتوى."""
    MOTIVATIONAL = "motivational"
    EDUCATIONAL = "educational"
    STORY = "story"
    QUOTE = "quote"


class GenerationStage(str, Enum):
    """مراحل التوليد."""
    SCRIPT = "script"
    VOICE = "voice"
    VIDEO = "video"
    RENDER = "render"
    COMPLETE = "complete"


# ═══════════════════════════════════════════════════════════════════
# Result Dataclass
# ═══════════════════════════════════════════════════════════════════
@dataclass
class GenerationResult:
    """نتيجة توليد الفيديو الكاملة."""
    success: bool
    output_path: str = ""
    topic: str = ""
    content_type: str = ""
    duration: float = 0.0
    
    # Stages results
    script_result: Optional[Any] = None  # ScriptWriter result
    voice_result: Optional[Any] = None    # TTSResult
    video_result: Optional[Any] = None    # CompletePropsResult
    render_result: Optional[Any] = None   # RenderResult
    
    # Stats
    total_time: float = 0.0
    file_size_mb: float = 0.0
    stage_failed: Optional[str] = None
    error: Optional[str] = None
    
    def summary(self) -> str:
        status = "✅" if self.success else "❌"
        lines = [
            f"\n{'=' * 60}",
            f"📊 Generation Result {status}",
            f"{'=' * 60}",
            f"    • Topic: {self.topic}",
            f"    • Type: {self.content_type}",
            f"    • Duration: {self.duration:.1f}s",
            f"    • Output: {self.output_path}",
            f"    • Size: {self.file_size_mb:.1f} MB",
            f"    • Total time: {self.total_time:.1f}s",
        ]
        
        if self.error:
            lines.append(f"    • Error: {self.error}")
        if self.stage_failed:
            lines.append(f"    • Failed at: {self.stage_failed}")
        
        return "\n".join(lines)


# ═══════════════════════════════════════════════════════════════════
# Environment Validation
# ═══════════════════════════════════════════════════════════════════
def check_environment() -> dict:
    """🔍 فحص شامل للبيئة."""
    from dotenv import load_dotenv
    load_dotenv()
    
    return {
        "python_version": sys.version.split()[0],
        "platform": sys.platform,
        "project_root": str(PROJECT_ROOT),
        "directories": {
            "engine": ENGINE_DIR.exists(),
            "assets": ASSETS_DIR.exists(),
            "music": MUSIC_DIR.exists(),
            "sfx": SFX_DIR.exists(),
            "temp": TEMP_DIR.exists(),
            "output": OUTPUT_DIR.exists(),
            "remotion": REMOTION_DIR.exists(),
        },
        "api_keys": {
            "GROQ_API_KEY": bool(os.getenv("GROQ_API_KEY")),
            "GEMINI_API_KEY": bool(os.getenv("GEMINI_API_KEY")),
            "ELEVENLABS_API_KEY": bool(os.getenv("ELEVENLABS_API_KEY")),
            "PEXELS_API_KEY": bool(os.getenv("PEXELS_API_KEY")),
            "PIXABAY_API_KEY": bool(os.getenv("PIXABAY_API_KEY")),
        },
    }


def check_requirements() -> dict:
    """فحص المكتبات المثبتة."""
    requirements_status = {}
    
    packages = [
        ("groq", "Groq AI"),
        ("google.genai", "Gemini AI"), # الاعتماد الحصري على حزمة 2026 المحدثة والمدعومة رسميًا
        ("edge_tts", "Edge TTS"),
        ("elevenlabs", "ElevenLabs"),
        ("faster_whisper", "Whisper"),
        ("pydub", "Audio mixing"),
        ("requests", "HTTP"),
        ("dotenv", "Env vars"),
    ]
    
    for pkg, name in packages:
        try:
            __import__(pkg)
            requirements_status[name] = True
        except ImportError:
            requirements_status[name] = False
    
    return requirements_status


def ensure_directories() -> None:
    """التأكد من وجود المجلدات الأساسية."""
    for dir_path in [TEMP_DIR, OUTPUT_DIR, ASSETS_DIR, MUSIC_DIR, SFX_DIR]:
        dir_path.mkdir(parents=True, exist_ok=True)


# ═══════════════════════════════════════════════════════════════════
# Content Factory (Main Orchestrator)
# ═══════════════════════════════════════════════════════════════════
class ContentFactory:
    """🎬 المصنع الشامل لتوليد الفيديوهات."""
    
    def __init__(
        self,
        ai_provider: str = "auto",
        tts_engine: str = "auto",
        renderer: str = "auto",
        cache_enabled: bool = True,
        log_level: str = "INFO",
    ):
        """
        Args:
            ai_provider: groq/gemini/auto
            tts_engine: edge/groq/gemini/elevenlabs/auto
            renderer: remotion/ffmpeg/auto
            cache_enabled: تفعيل caching في كل مكان
            log_level: مستوى الـ logging
        """
        # Setup logging
        setup_logging(level=log_level)
        
        # Ensure directories
        ensure_directories()
        
        # Settings
        self.ai_provider = ai_provider
        self.tts_engine_pref = tts_engine
        self.renderer_pref = renderer
        self.cache_enabled = cache_enabled
        
        # Lazy initialized
        self._script_writer = None
        self._tts_engine = None
        self._video_orchestrator = None
        self._render_orchestrator = None
        
        logger.info(f"🎬 ContentFactory v{__version__} initialized")
    
    # ═══════════════════════════════════════════════════════════════
    # Lazy Components
    # ═══════════════════════════════════════════════════════════════
    @property
    def script_writer(self):
        """ScriptWriter (lazy)."""
        if self._script_writer is None:
            from engine.ai import create_ai_writer
            self._script_writer = create_ai_writer(
                prefer=self.ai_provider,
                enable_fallback=True,
                enable_validation=True,
            )
        return self._script_writer
    
    @property
    def tts_engine(self):
        """TTS Engine (lazy)."""
        if self._tts_engine is None:
            from engine.video.voice import create_tts_engine
            self._tts_engine = create_tts_engine(prefer=self.tts_engine_pref)
        return self._tts_engine
    
    @property
    def video_orchestrator(self):
        """VideoOrchestrator (lazy)."""
        if self._video_orchestrator is None:
            from engine.video import VideoOrchestrator
            self._video_orchestrator = VideoOrchestrator(
                cache_enabled=self.cache_enabled,
            )
        return self._video_orchestrator
    
    @property
    def render_orchestrator(self):
        """RenderOrchestrator (lazy)."""
        if self._render_orchestrator is None:
            from engine.render import RenderOrchestrator
            self._render_orchestrator = RenderOrchestrator(
                prefer=self.renderer_pref,
                cache_enabled=self.cache_enabled,
            )
        return self._render_orchestrator
    
    # ═══════════════════════════════════════════════════════════════
    # Main API
    # ═══════════════════════════════════════════════════════════════
    def generate(
        self,
        topic: str,
        content_type: str = "motivational",
        target_duration: int = DEFAULT_DURATION,
        output_path: Optional[str] = None,
        quality: str = "high",
        progress_callback: Optional[Callable[[str, float], None]] = None,
    ) -> GenerationResult:
        """
        🎯 توليد فيديو كامل.
        
        Args:
            topic: الموضوع
            content_type: motivational/educational/story/quote
            target_duration: 30/45/60
            output_path: مسار الإخراج (auto إذا None)
            quality: draft/medium/high/ultra
            progress_callback: callback(stage, percent)
        
        Returns:
            GenerationResult
        """
        import time
        start_time = time.time()
        
        # Validation
        if target_duration not in SUPPORTED_DURATIONS:
            logger.warning(
                f"⚠ Duration {target_duration} غير مدعوم، "
                f"استخدام {DEFAULT_DURATION}"
            )
            target_duration = DEFAULT_DURATION
        
        # Output path
        if not output_path:
            safe_topic = "".join(
                c if c.isalnum() else "_" for c in topic[:30]
            )
            timestamp = int(time.time())
            output_path = str(
                OUTPUT_DIR / f"{safe_topic}_{timestamp}.mp4"
            )
        
        result = GenerationResult(
            success=False,
            topic=topic,
            content_type=content_type,
            duration=target_duration,
            output_path=output_path,
        )
        
        try:
            # ═══════ 1️⃣ Script ═══════
            logger.info(f"\n{'=' * 60}")
            logger.info(f"📝 [1/4] Generating script: '{topic}'")
            logger.info(f"{'=' * 60}")
            
            if progress_callback:
                progress_callback(GenerationStage.SCRIPT.value, 0.05)
            
            script = self.script_writer.generate_script(
                topic=topic,
                content_type=content_type,
                target_duration=target_duration,
            )
            result.script_result = script
            
            if progress_callback:
                progress_callback(GenerationStage.SCRIPT.value, 0.25)
            
            # ═══════ 2️⃣ Voice ═══════
            logger.info(f"\n{'=' * 60}")
            logger.info(f"🎙️ [2/4] Generating voice")
            logger.info(f"{'=' * 60}")
            
            audio_path = str(TEMP_DIR / f"voice_{int(time.time())}.mp3")
            voice_result = self.tts_engine.generate_audio(
                script=script,
                output_path=audio_path,
            )
            result.voice_result = voice_result
            
            if not voice_result.success:
                result.stage_failed = GenerationStage.VOICE.value
                result.error = voice_result.error or "Voice generation failed"
                result.total_time = time.time() - start_time
                return result
            
            if progress_callback:
                progress_callback(GenerationStage.VOICE.value, 0.5)
            
            # ═══════ 3️⃣ Video ═══════
            logger.info(f"\n{'=' * 60}")
            logger.info(f"🎬 [3/4] Building video props")
            logger.info(f"{'=' * 60}")
            
            video_result = self.video_orchestrator.build_props(
                script=script,
                audio_path=audio_path,
            )
            result.video_result = video_result
            
            if not video_result.success:
                result.stage_failed = GenerationStage.VIDEO.value
                result.error = video_result.error or "Video build failed"
                result.total_time = time.time() - start_time
                return result
            
            if progress_callback:
                progress_callback(GenerationStage.VIDEO.value, 0.7)
            
            # ═══════ 4️⃣ Render ═══════
            logger.info(f"\n{'=' * 60}")
            logger.info(f"🎞️ [4/4] Rendering final video")
            logger.info(f"{'=' * 60}")
            
            render_result = self.render_orchestrator.render(
                output_path=output_path,
                props=video_result.props,
                quality=quality,
            )
            result.render_result = render_result
            
            if not render_result.success:
                result.stage_failed = GenerationStage.RENDER.value
                result.error = render_result.error or "Render failed"
                result.total_time = time.time() - start_time
                return result
            
            if progress_callback:
                progress_callback(GenerationStage.COMPLETE.value, 1.0)
            
            # Success!
            result.success = True
            result.file_size_mb = render_result.file_size_mb
            result.total_time = time.time() - start_time
            
            logger.info(result.summary())
            
            return result
            
        except Exception as e:
            logger.error(f"❌ Generation failed: {e}", exc_info=True)
            result.error = str(e)
            result.total_time = time.time() - start_time
            return result
    
    def cleanup(self) -> None:
        """تنظيف الملفات المؤقتة."""
        try:
            for f in TEMP_DIR.rglob("*.mp3"):
                f.unlink(missing_ok=True)
            for f in TEMP_DIR.rglob("*.mp4"):
                f.unlink(missing_ok=True)
            logger.info("🧹 تم التنظيف")
        except Exception as e:
            logger.warning(f"⚠ Cleanup failed: {e}")


# ═══════════════════════════════════════════════════════════════════
# Convenience Functions
# ═══════════════════════════════════════════════════════════════════
def quick_generate(
    topic: str,
    content_type: str = "motivational",
    target_duration: int = DEFAULT_DURATION,
    quality: str = "high",
) -> str:
    """
    🚀 توليد سريع جداً.
    
    Examples:
        >>> from engine import quick_generate
        >>> video = quick_generate("الطموح والنجاح")
        >>> print(video)
        /path/to/output.mp4
    """
    factory = ContentFactory()
    result = factory.generate(
        topic=topic,
        content_type=content_type,
        target_duration=target_duration,
        quality=quality,
    )
    
    if not result.success:
        raise RuntimeError(f"Generation failed: {result.error}")
    
    return result.output_path


# ═══════════════════════════════════════════════════════════════════
# Diagnostic
# ═══════════════════════════════════════════════════════════════════
def print_status() -> None:
    """طباعة حالة المشروع الكاملة."""
    print("=" * 60)
    print(f"🎬 {PROJECT_NAME} v{__version__}")
    print("=" * 60)
    
    # Environment
    env = check_environment()
    
    print(f"\n🐍 Python: {env['python_version']}")
    print(f"💻 Platform: {env['platform']}")
    print(f"📂 Project: {env['project_root']}")
    
    # Directories
    print(f"\n📁 Directories:")
    for name, exists in env["directories"].items():
        status = "✅" if exists else "❌"
        print(f"   {status} {name}")
    
    # API Keys
    print(f"\n🔑 API Keys:")
    for key, available in env["api_keys"].items():
        status = "✅" if available else "❌"
        print(f"   {status} {key}")
    
    # Requirements
    print(f"\n📦 Requirements:")
    requirements = check_requirements()
    for name, installed in requirements.items():
        status = "✅" if installed else "❌"
        print(f"   {status} {name}")
    
    # Modules
    print(f"\n🧩 Modules:")
    modules = [
        ("engine.ai", "AI/Scripts"),
        ("engine.video.voice", "Voice/TTS"),
        ("engine.video", "Video"),
        ("engine.render", "Render"),
    ]
    for mod_path, name in modules:
        try:
            __import__(mod_path)
            print(f"   ✅ {name}")
        except ImportError as e:
            print(f"   ❌ {name}: {e}")
    
    print("=" * 60)


def get_info() -> dict:
    """معلومات المشروع."""
    return {
        "version": __version__,
        "name": PROJECT_NAME,
        "author": __author__,
        "license": __license__,
        "paths": {
            "root": str(PROJECT_ROOT),
            "engine": str(ENGINE_DIR),
            "temp": str(TEMP_DIR),
            "output": str(OUTPUT_DIR),
            "remotion": str(REMOTION_DIR),
        },
        "defaults": {
            "width": DEFAULT_WIDTH,
            "height": DEFAULT_HEIGHT,
            "fps": DEFAULT_FPS,
            "duration": DEFAULT_DURATION,
        },
        "supported_durations": list(SUPPORTED_DURATIONS),
        "environment": check_environment(),
        "requirements": check_requirements(),
    }


# ═══════════════════════════════════════════════════════════════════
# Lazy Top-Level Imports
# ═══════════════════════════════════════════════════════════════════
if TYPE_CHECKING:
    from engine.ai import ScriptWriter, ContentValidator
    from engine.video.voice import create_tts_engine
    from engine.video import VideoOrchestrator
    from engine.render import RenderOrchestrator


def __getattr__(name: str):
    """Lazy import للأشياء الأكثر استخداماً."""
    
    # AI
    if name == "ScriptWriter":
        from engine.ai import ScriptWriter
        return ScriptWriter
    
    if name == "ContentValidator":
        from engine.ai import ContentValidator
        return ContentValidator
    
    if name == "create_ai_writer":
        from engine.ai import create_ai_writer
        return create_ai_writer
    
    # Voice
    if name == "create_tts_engine":
        from engine.video.voice import create_tts_engine
        return create_tts_engine
    
    if name == "EdgeTTS":
        from engine.video.voice import EdgeTTS
        return EdgeTTS
    
    # Video
    if name == "VideoOrchestrator":
        from engine.video import VideoOrchestrator
        return VideoOrchestrator
    
    if name == "build_complete_props":
        from engine.video import build_complete_props
        return build_complete_props
    
    # Render
    if name == "RenderOrchestrator":
        from engine.render import RenderOrchestrator
        return RenderOrchestrator
    
    if name == "RemotionRenderer":
        from engine.render import RemotionRenderer
        return RemotionRenderer
    
    raise AttributeError(f"module 'engine' has no attribute '{name}'")


# ═══════════════════════════════════════════════════════════════════
# Public API
# ═══════════════════════════════════════════════════════════════════
__all__ = [
    # Metadata
    "__version__",
    "__author__",
    "__license__",
    "PROJECT_NAME",
    "PROJECT_DESCRIPTION",
    
    # Constants
    "PROJECT_ROOT",
    "ENGINE_DIR",
    "ASSETS_DIR",
    "FONTS_DIR",
    "MUSIC_DIR",
    "SFX_DIR",
    "TEMP_DIR",
    "OUTPUT_DIR",
    "REMOTION_DIR",
    "DEFAULT_WIDTH",
    "DEFAULT_HEIGHT",
    "DEFAULT_FPS",
    "DEFAULT_DURATION",
    "SUPPORTED_DURATIONS",
    
    # Enums
    "ContentType",
    "GenerationStage",
    
    # Dataclasses
    "GenerationResult",
    
    # Main classes
    "ContentFactory",
    
    # Lazy imports
    "ScriptWriter",
    "ContentValidator",
    "create_ai_writer",
    "create_tts_engine",
    "EdgeTTS",
    "VideoOrchestrator",
    "build_complete_props",
    "RenderOrchestrator",
    "RemotionRenderer",
    
    # Functions
    "quick_generate",
    "setup_logging",
    "check_environment",
    "check_requirements",
    "ensure_directories",
    "get_info",
    "print_status",
]


# ═══════════════════════════════════════════════════════════════════
# Initialization
# ═══════════════════════════════════════════════════════════════════
# تحميل .env إذا موجود
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

# ضمان وجود المجلدات
try:
    ensure_directories()
except Exception:
    pass


# ═══════════════════════════════════════════════════════════════════
# اختبار
# ═══════════════════════════════════════════════════════════════════
if __name__ == "__main__":
    print_status()
