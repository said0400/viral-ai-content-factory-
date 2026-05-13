"""
🎬 Viral AI Content Factory
═══════════════════════════════════════════════════════════════
محرك توليد فيديوهات Shorts عربية احترافية بالذكاء الاصطناعي

📦 Modules:
  • ai      → توليد السكربتات (Groq + Gemini)
  • voice   → توليد ومعالجة الصوت (edge-tts + ElevenLabs)
  • video   → تحرير الفيديو (مونتاج، تأثيرات، انتقالات، ترجمة)
  • render  → التصدير النهائي (FFmpeg)

🌐 Repository: https://github.com/yourusername/viral-ai-factory
👤 Author: AI Shorts Generator
📅 Version: 2.0.0
═══════════════════════════════════════════════════════════════
"""

__version__ = "2.0.0"
__author__ = "AI Shorts Generator"
__license__ = "MIT"

# معلومات سريعة عن المشروع
PROJECT_NAME = "Viral AI Content Factory"
PROJECT_DESCRIPTION = "Arabic Cinematic Shorts Generator"

# الأبعاد القياسية لـ YouTube Shorts / TikTok / Reels
DEFAULT_WIDTH = 1080
DEFAULT_HEIGHT = 1920
DEFAULT_FPS = 30
DEFAULT_DURATION = 45  # ثانية

# المسارات الافتراضية
ASSETS_DIR = "engine/assets"
FONTS_DIR = f"{ASSETS_DIR}/fonts"
MUSIC_DIR = f"{ASSETS_DIR}/music"
SFX_DIR = f"{ASSETS_DIR}/sfx"

__all__ = [
    "__version__",
    "__author__",
    "PROJECT_NAME",
    "DEFAULT_WIDTH",
    "DEFAULT_HEIGHT",
    "DEFAULT_FPS",
    "DEFAULT_DURATION",
    "ASSETS_DIR",
    "FONTS_DIR",
    "MUSIC_DIR",
    "SFX_DIR",
]
