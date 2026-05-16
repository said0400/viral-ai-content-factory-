"""
🎵 Music Engine v7.0 — مكتبة موسيقى محلية كاملة
═══════════════════════════════════════════════════════════════
يستخدم 133+ ملف موسيقى محلي من:
  engine/assets/music/[mood]/

المكتبة:
  ✓ motivation:  25 ملف
  ✓ cinematic:   32 ملف
  ✓ dark:        26 ملف
  ✓ emotional:   27 ملف
  ✓ educational: 23 ملف
  ─────────────────────────
  📊 الإجمالي:   133 ملف

الميزات:
  ✓ سريع جداً (لا تحميل من الإنترنت)
  ✓ نظام Mood ذكي مع aliases
  ✓ Random selection للتنويع
  ✓ Fallback لـ moods بديلة

ضع في: engine/voice/music_engine.py
═══════════════════════════════════════════════════════════════
"""

import os
import random
import logging
from pathlib import Path
from typing import Optional, List, Dict

logger = logging.getLogger(__name__)


class MusicEngine:
    """محرك الموسيقى - يستخدم المكتبة المحلية."""

    # ═════════════════════════════════════════════════════════════════
    # 🎯 خريطة Moods (تحويل moods مختلفة لـ 5 فئات)
    # ═════════════════════════════════════════════════════════════════
    MOOD_ALIASES = {
        # 🔥 تحفيزي → motivation
        "motivational": "motivation",
        "motivation": "motivation",
        "inspiring": "motivation",
        "uplifting": "motivation",
        "powerful": "motivation",
        "epic": "motivation",
        "energetic": "motivation",
        
        # 🎬 سينمائي → cinematic
        "cinematic": "cinematic",
        "dramatic": "cinematic",
        "trailer": "cinematic",
        "movie": "cinematic",
        
        # 🌑 مظلم → dark
        "dark": "dark",
        "mysterious": "dark",
        "horror": "dark",
        "suspense": "dark",
        "thriller": "dark",
        "sigma": "dark",
        "psychological": "dark",
        "scary": "dark",
        
        # 💔 عاطفي → emotional
        "emotional": "emotional",
        "sad": "emotional",
        "melancholic": "emotional",
        "thoughtful": "emotional",
        "deep": "emotional",
        "romantic": "emotional",
        "love": "emotional",
        
        # 📚 تعليمي → educational
        "educational": "educational",
        "scientific": "educational",
        "informative": "educational",
        "professional": "educational",
        "focus": "educational",
        "calm": "educational",
        "peaceful": "educational",
        "meditation": "educational",
        "ambient": "educational",
        "corporate": "educational",
        "documentary": "educational",
    }

    # ════════════════════════════════════════════════════════════════
    def __init__(self):
        """تهيئة محرك الموسيقى."""
        self.music_dir = Path(os.getenv("MUSIC_DIR", "engine/assets/music"))
        
        # 🆕 اكتشف المكتبة المحلية
        self.library = self._scan_library()
        
        # إحصائيات
        total = sum(len(files) for files in self.library.values())
        
        logger.info(f"🎵 MusicEngine v7.0 (Local Library)")
        logger.info(f"   📂 المسار: {self.music_dir}")
        logger.info(f"   📚 إجمالي الملفات: {total}")
        
        if self.library:
            logger.info("   📊 توزيع Moods:")
            for mood, files in sorted(self.library.items()):
                logger.info(f"      • {mood}: {len(files)} ملف")
        else:
            logger.warning("   ⚠ لا توجد موسيقى!")
            logger.warning(f"   ℹ تأكد من رفع الموسيقى في: {self.music_dir}/[mood]/")

    # ════════════════════════════════════════════════════════════════
    #              مسح المكتبة المحلية
    # ════════════════════════════════════════════════════════════════
    def _scan_library(self) -> Dict[str, List[Path]]:
        """🆕 اكتشاف كل الموسيقى المتاحة محلياً."""
        library = {}
        
        # إنشاء المجلد إذا لم يكن موجود
        if not self.music_dir.exists():
            self.music_dir.mkdir(parents=True, exist_ok=True)
            return library
        
        # مسح المجلدات الفرعية
        for mood_dir in self.music_dir.iterdir():
            if mood_dir.is_dir():
                mood = mood_dir.name.lower()
                files = self._get_audio_files(mood_dir)
                if files:
                    library[mood] = files
        
        return library

    # ════════════════════════════════════════════════════════════════
    #              🎯 الدالة الرئيسية
    # ════════════════════════════════════════════════════════════════
    def get_music(self, mood: str, duration: float) -> Optional[str]:
        """
        الحصول على موسيقى مناسبة من المكتبة المحلية.

        Args:
            mood: المزاج المطلوب
            duration: المدة المطلوبة بالثواني (للتوافق فقط)

        Returns:
            مسار ملف الموسيقى أو None
        """
        normalized_mood = self._normalize_mood(mood)
        
        logger.info(f"🎵 البحث عن موسيقى | mood: {mood} → {normalized_mood}")

        # 1️⃣ ابحث في mood المحدد
        if normalized_mood in self.library:
            files = self.library[normalized_mood]
            if files:
                selected = random.choice(files)
                logger.info(f"✓ اخترت: {selected.name}")
                return str(selected)

        # 2️⃣ جرّب moods بديلة (motivation أو cinematic كافتراضي قوي)
        logger.info(f"⚠ لا موسيقى لـ '{normalized_mood}', جاري البحث في mood بديل...")
        
        priority_alternatives = ["motivation", "cinematic", "educational", "emotional", "dark"]
        
        for alt_mood in priority_alternatives:
            if alt_mood in self.library and alt_mood != normalized_mood:
                files = self.library[alt_mood]
                if files:
                    selected = random.choice(files)
                    logger.info(f"✓ بديل من {alt_mood}: {selected.name}")
                    return str(selected)

        # 3️⃣ أي ملف متاح في أي mood
        all_files = []
        for files in self.library.values():
            all_files.extend(files)
        
        if all_files:
            selected = random.choice(all_files)
            logger.info(f"✓ fallback عشوائي: {selected.name}")
            return str(selected)

        # ❌ لا موسيقى أبداً
        logger.warning("⚠ لا توجد أي موسيقى في المكتبة!")
        logger.warning(f"   ℹ تأكد من رفع ملفات MP3 في: {self.music_dir}")
        return None

    # ════════════════════════════════════════════════════════════════
    #              دوال مساعدة
    # ════════════════════════════════════════════════════════════════
    def _normalize_mood(self, mood: str) -> str:
        """تحويل mood إلى نوع معروف."""
        mood_lower = mood.lower().strip()
        
        # ابحث في aliases
        normalized = self.MOOD_ALIASES.get(mood_lower)
        if normalized:
            return normalized
        
        # ابحث في المكتبة مباشرة
        if mood_lower in self.library:
            return mood_lower
        
        # افتراضي
        logger.debug(f"Mood '{mood}' → motivation (افتراضي)")
        return "motivation"

    @staticmethod
    def _get_audio_files(directory: Path) -> List[Path]:
        """الحصول على ملفات صوتية في مجلد."""
        files = []
        for ext in ("*.mp3", "*.wav", "*.m4a", "*.ogg", "*.aac"):
            files.extend(directory.glob(ext))
        return sorted(files)

    def list_available_moods(self) -> List[str]:
        """قائمة الـ moods المتاحة."""
        return list(self.library.keys())

    def get_status(self) -> Dict:
        """حالة المكتبة."""
        total = sum(len(files) for files in self.library.values())
        return {
            "music_dir": str(self.music_dir),
            "total_files": total,
            "moods": {mood: len(files) for mood, files in self.library.items()},
            "available": total > 0,
        }

    def get_random_music(self, mood: Optional[str] = None) -> Optional[str]:
        """
        اختيار موسيقى عشوائية.
        
        Args:
            mood: إذا حُدد، يختار من mood معين فقط
        """
        if mood:
            normalized = self._normalize_mood(mood)
            if normalized in self.library:
                files = self.library[normalized]
                if files:
                    return str(random.choice(files))
            return None
        
        # عشوائي من كل المكتبة
        all_files = []
        for files in self.library.values():
            all_files.extend(files)
        
        return str(random.choice(all_files)) if all_files else None

    def clear_cache(self) -> int:
        """⚠️ لا تستخدم - يحذف كل موسيقاك المحلية!"""
        logger.warning("⚠ clear_cache معطّل لحماية المكتبة المحلية")
        return 0


# ════════════════════════════════════════════════════════════════════════
#                    اختبار سريع
# ════════════════════════════════════════════════════════════════════════
if __name__ == "__main__":
    import sys

    engine = MusicEngine()
    
    print("\n📊 حالة المكتبة:")
    status = engine.get_status()
    print(f"   📂 المسار: {status['music_dir']}")
    print(f"   📦 إجمالي الملفات: {status['total_files']}")
    
    if status['moods']:
        print("\n   📂 توزيع Moods:")
        for mood, count in sorted(status['moods'].items()):
            print(f"      • {mood}: {count} ملف")
    
    if len(sys.argv) > 1:
        mood = sys.argv[1]
        print(f"\n🎵 اختبار: mood='{mood}'")
        music = engine.get_music(mood, 45.0)
        if music:
            print(f"✅ النتيجة: {music}")
        else:
            print("❌ لم يتم العثور على موسيقى")
    else:
        # اختبار سريع لكل mood
        print("\n🎵 اختبار كل Moods:")
        test_moods = ["motivational", "cinematic", "dark", "emotional", 
                     "educational", "scientific", "sigma"]
        for test_mood in test_moods:
            music = engine.get_music(test_mood, 45.0)
            if music:
                print(f"   ✓ {test_mood} → {Path(music).name}")
            else:
                print(f"   ✗ {test_mood} → فشل")
