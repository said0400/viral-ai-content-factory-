"""
🔊 SFX Manager v2.0 — مدير المؤثرات الصوتية المحلية
═══════════════════════════════════════════════════════════════
يستخدم المؤثرات المحلية في:
  engine/assets/sfx/[type]/

✓ 74+ مؤثر صوتي محلي
✓ Case-insensitive search
✓ ربط ذكي بأنواع المشاهد

ضع في: engine/voice/sfx_manager.py
═══════════════════════════════════════════════════════════════
"""

import os
import random
import logging
from pathlib import Path
from typing import Optional, List, Tuple, Dict

logger = logging.getLogger(__name__)


class SFXManager:
    """مدير المؤثرات الصوتية المحلية."""

    # ─── ربط أنواع المشاهد بـ SFX ──────────────────────────────
    SCENE_SFX_MAP = {
        "hook":       ["impact", "whoosh"],
        "peak":       ["impact", "drum"],
        "build":      ["whoosh", "swoosh"],
        "resolution": ["bell", "sparkle"],
        "cta":        ["click", "bell"],
        "main":       ["whoosh"],
        "intro":      ["impact", "drum"],
        "outro":      ["bell", "sparkle"],
    }

    # ─── مستويات الصوت ──────────────────────────────────────────
    VOLUME_MAP = {
        "hook":       0.45,
        "peak":       0.50,
        "build":      0.30,
        "resolution": 0.25,
        "cta":        0.35,
        "main":       0.25,
        "intro":      0.45,
        "outro":      0.25,
    }

    # ════════════════════════════════════════════════════════════════
    def __init__(self):
        """تهيئة المدير."""
        self.sfx_dir = Path(os.getenv("SFX_DIR", "engine/assets/sfx"))
        
        self.enabled = os.getenv("ENABLE_SFX", "true").lower() == "true"
        self.max_sfx = int(os.getenv("MAX_SFX_PER_VIDEO", "5"))
        self.default_volume = float(os.getenv("SFX_VOLUME", "0.35"))

        # اكتشف المكتبة المحلية
        self.library = self._scan_library()
        
        total = sum(len(files) for files in self.library.values())
        
        logger.info(f"🔊 SFXManager v2.0 | Enabled: {self.enabled} | Max: {self.max_sfx}")
        logger.info(f"   📂 المسار: {self.sfx_dir}")
        logger.info(f"   📚 إجمالي الملفات: {total}")
        
        if self.library:
            for sfx_type, files in sorted(self.library.items()):
                logger.info(f"      • {sfx_type}: {len(files)} ملف")

    # ════════════════════════════════════════════════════════════════
    #              مسح المكتبة المحلية
    # ════════════════════════════════════════════════════════════════
    def _scan_library(self) -> Dict[str, List[Path]]:
        """اكتشاف كل SFX المتاحة محلياً."""
        library = {}
        
        if not self.sfx_dir.exists():
            self.sfx_dir.mkdir(parents=True, exist_ok=True)
            return library
        
        for sfx_dir in self.sfx_dir.iterdir():
            if sfx_dir.is_dir():
                sfx_type = sfx_dir.name.lower()
                files = self._get_audio_files(sfx_dir)
                if files:
                    library[sfx_type] = files
        
        return library

    # ════════════════════════════════════════════════════════════════
    #              🎯 الدالة الرئيسية
    # ════════════════════════════════════════════════════════════════
    def get_sfx_for_scenes(
        self,
        scenes: List[Dict],
    ) -> List[Tuple[str, float, float]]:
        """توليد قائمة SFX جاهزة لجميع المشاهد."""
        if not self.enabled:
            logger.info("⏭ SFX معطّلة")
            return []
        
        if not scenes:
            return []
        
        if not self.library:
            logger.warning("⚠ لا توجد SFX محلية!")
            return []
        
        sfx_tracks = []
        cumulative_time = 0.0
        sfx_count = 0
        
        logger.info(f"🔊 توليد SFX لـ {len(scenes)} مشهد...")
        
        for i, scene in enumerate(scenes):
            if sfx_count >= self.max_sfx:
                break
            
            scene_type = scene.get("type", "main")
            
            sfx_path = self._get_sfx_for_type(scene_type)
            
            if sfx_path:
                volume = self.VOLUME_MAP.get(scene_type, self.default_volume)
                start_time = max(cumulative_time - 0.2, 0)
                
                sfx_tracks.append((sfx_path, start_time, volume))
                sfx_count += 1
                
                logger.info(
                    f"   ✓ Scene {i} ({scene_type}): "
                    f"{Path(sfx_path).name} @ {start_time:.1f}s"
                )
            
            duration = float(scene.get("duration", 3.0))
            pause = float(scene.get("pause_after", 0.3))
            cumulative_time += duration + pause
        
        logger.info(f"✓ تم تجهيز {len(sfx_tracks)} مؤثر صوتي")
        return sfx_tracks

    # ════════════════════════════════════════════════════════════════
    #              الحصول على SFX حسب النوع
    # ════════════════════════════════════════════════════════════════
    def _get_sfx_for_type(self, scene_type: str) -> Optional[str]:
        """احصل على SFX مناسب لنوع المشهد."""
        sfx_types = self.SCENE_SFX_MAP.get(scene_type, ["whoosh"])
        sfx_type = random.choice(sfx_types)
        
        # ابحث في المكتبة
        if sfx_type in self.library:
            files = self.library[sfx_type]
            if files:
                return str(random.choice(files))
        
        # جرّب أي نوع متاح
        for available_type, files in self.library.items():
            if files:
                return str(random.choice(files))
        
        return None

    # ════════════════════════════════════════════════════════════════
    #              دوال مساعدة
    # ════════════════════════════════════════════════════════════════
    @staticmethod
    def _get_audio_files(directory: Path) -> List[Path]:
        """الحصول على ملفات صوتية."""
        files = []
        for ext in ("*.mp3", "*.wav", "*.m4a", "*.ogg", "*.MP3", "*.WAV"):
            files.extend(directory.glob(ext))
        return sorted(files)

    def list_sfx_types(self) -> List[str]:
        return list(self.library.keys())

    def get_status(self) -> Dict:
        total = sum(len(files) for files in self.library.values())
        return {
            "sfx_dir": str(self.sfx_dir),
            "total_files": total,
            "types": {t: len(f) for t, f in self.library.items()},
            "enabled": self.enabled,
        }


if __name__ == "__main__":
    manager = SFXManager()
    status = manager.get_status()
    print(f"\n📊 SFX: {status['total_files']} ملف")
    print(f"📂 Types: {status['types']}")
