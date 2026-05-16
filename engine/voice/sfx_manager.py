"""
🔊 SFX Manager — مدير المؤثرات الصوتية للفيديو
═══════════════════════════════════════════════════════════════
يوفر:
  ✓ مكتبة SFX جاهزة (روابط مجانية مباشرة)
  ✓ تحميل تلقائي وحفظ محلي (cache)
  ✓ ربط ذكي بأنواع المشاهد (hook → impact, etc.)
  ✓ توليد قائمة SFX جاهزة لـ AudioFX.mix_audio_tracks

ضع في: engine/voice/sfx_manager.py
═══════════════════════════════════════════════════════════════
"""

import os
import random
import logging
import requests
from pathlib import Path
from typing import Optional, List, Tuple, Dict

logger = logging.getLogger(__name__)


class SFXManager:
    """مدير المؤثرات الصوتية."""

    # ═════════════════════════════════════════════════════════════════
    # 🔊 مكتبة SFX (روابط مباشرة من مصادر مجانية)
    # ═════════════════════════════════════════════════════════════════
    SFX_LIBRARY = {
        # 💥 Whoosh - للانتقالات والحركة
        "whoosh": [
            "https://cdn.pixabay.com/download/audio/2022/03/15/audio_a06ed10c11.mp3",
            "https://cdn.pixabay.com/download/audio/2021/08/09/audio_cb7e8e5f1f.mp3",
            "https://cdn.pixabay.com/download/audio/2022/10/17/audio_c8b8c4f1d4.mp3",
        ],
        
        # 💢 Impact - للذروة والـ hooks
        "impact": [
            "https://cdn.pixabay.com/download/audio/2022/08/04/audio_2dde668d05.mp3",
            "https://cdn.pixabay.com/download/audio/2021/08/09/audio_88447e769f.mp3",
            "https://cdn.pixabay.com/download/audio/2022/03/10/audio_ee06a7e5a7.mp3",
        ],
        
        # 🔔 Bell - للنقاط المهمة
        "bell": [
            "https://cdn.pixabay.com/download/audio/2022/03/15/audio_e6c0eb4f6c.mp3",
            "https://cdn.pixabay.com/download/audio/2022/10/17/audio_d0ad4d52a4.mp3",
        ],
        
        # ⚡ Glitch - للتأثيرات الحديثة
        "glitch": [
            "https://cdn.pixabay.com/download/audio/2022/03/15/audio_c8e9f1f2e8.mp3",
            "https://cdn.pixabay.com/download/audio/2022/01/18/audio_5e8e6c9c3e.mp3",
        ],
        
        # 🎯 Click - للـ CTA
        "click": [
            "https://cdn.pixabay.com/download/audio/2022/03/15/audio_8cb749c54f.mp3",
            "https://cdn.pixabay.com/download/audio/2022/03/24/audio_8e2dc02614.mp3",
        ],
        
        # 🌟 Sparkle - للعناصر الإيجابية
        "sparkle": [
            "https://cdn.pixabay.com/download/audio/2022/03/24/audio_2e3a1f9e0e.mp3",
            "https://cdn.pixabay.com/download/audio/2021/10/12/audio_1bbc5f8e8f.mp3",
        ],
        
        # 🥁 Drum - للإيقاع
        "drum": [
            "https://cdn.pixabay.com/download/audio/2022/03/15/audio_10b3e9c0e8.mp3",
        ],
        
        # 💨 Swoosh - بديل للـ whoosh
        "swoosh": [
            "https://cdn.pixabay.com/download/audio/2021/08/09/audio_88447e769f.mp3",
        ],
    }

    # ═════════════════════════════════════════════════════════════════
    # 🎯 ربط أنواع المشاهد بـ SFX المناسبة
    # ═════════════════════════════════════════════════════════════════
    SCENE_SFX_MAP = {
        "hook":       ["impact", "whoosh"],     # افتتاحية قوية
        "peak":       ["impact", "drum"],       # ذروة
        "build":      ["whoosh", "swoosh"],     # تصاعد
        "resolution": ["bell", "sparkle"],      # حل
        "cta":        ["click", "bell"],        # call to action
        "main":       ["whoosh"],               # عام
        "intro":      ["impact", "drum"],       # مقدمة
        "outro":      ["bell", "sparkle"],      # خاتمة
    }

    # ═════════════════════════════════════════════════════════════════
    # 🎚️ مستويات الصوت لكل نوع
    # ═════════════════════════════════════════════════════════════════
    VOLUME_MAP = {
        "hook":       0.45,  # عالي للـ hook
        "peak":       0.50,  # أعلى للذروة
        "build":      0.30,
        "resolution": 0.25,
        "cta":        0.35,
        "main":       0.25,
        "intro":      0.45,
        "outro":      0.25,
    }

    # ═════════════════════════════════════════════════════════════════
    def __init__(self):
        """تهيئة المدير."""
        self.sfx_dir = Path(os.getenv("SFX_DIR", "engine/assets/sfx"))
        self.sfx_dir.mkdir(parents=True, exist_ok=True)
        
        # إعدادات
        self.enabled = os.getenv("ENABLE_SFX", "true").lower() == "true"
        self.max_sfx = int(os.getenv("MAX_SFX_PER_VIDEO", "5"))
        self.default_volume = float(os.getenv("SFX_VOLUME", "0.35"))
        self.timeout = int(os.getenv("SFX_DOWNLOAD_TIMEOUT", "30"))
        
        # عداد المحاولات (لتجنب الإفراط)
        self._download_attempts: Dict[str, int] = {}
        
        logger.info(
            f"🔊 SFXManager | Enabled: {self.enabled} | "
            f"Max: {self.max_sfx} | Volume: {self.default_volume}"
        )

    # ═════════════════════════════════════════════════════════════════
    #              🎯 الدالة الرئيسية
    # ═════════════════════════════════════════════════════════════════
    def get_sfx_for_scenes(
        self,
        scenes: List[Dict],
    ) -> List[Tuple[str, float, float]]:
        """
        🎯 توليد قائمة SFX جاهزة لجميع المشاهد.
        
        Args:
            scenes: قائمة المشاهد من السكربت
            
        Returns:
            قائمة من (sfx_path, start_time, volume)
            جاهزة لـ AudioFX.mix_audio_tracks()
        """
        if not self.enabled:
            logger.info("⏭ SFX معطّلة")
            return []
        
        if not scenes:
            return []
        
        sfx_tracks = []
        cumulative_time = 0.0
        sfx_count = 0
        
        logger.info(f"🔊 توليد SFX لـ {len(scenes)} مشهد...")
        
        for i, scene in enumerate(scenes):
            # توقف عند الحد الأقصى
            if sfx_count >= self.max_sfx:
                break
            
            scene_type = scene.get("type", "main")
            
            # احصل على SFX مناسب
            sfx_path = self._get_sfx_for_type(scene_type)
            
            if sfx_path:
                # احسب مستوى الصوت
                volume = self.VOLUME_MAP.get(scene_type, self.default_volume)
                
                # ضع الـ SFX قبل المشهد بقليل (200ms)
                start_time = max(cumulative_time - 0.2, 0)
                
                sfx_tracks.append((sfx_path, start_time, volume))
                sfx_count += 1
                
                logger.info(
                    f"   ✓ Scene {i} ({scene_type}): "
                    f"{Path(sfx_path).name} @ {start_time:.1f}s (vol={volume})"
                )
            
            # احسب الوقت التراكمي
            duration = float(scene.get("duration", 3.0))
            pause = float(scene.get("pause_after", 0.3))
            cumulative_time += duration + pause
        
        logger.info(f"✓ تم تجهيز {len(sfx_tracks)} مؤثر صوتي")
        return sfx_tracks

    # ═════════════════════════════════════════════════════════════════
    #              🔊 الحصول على SFX حسب النوع
    # ═════════════════════════════════════════════════════════════════
    def _get_sfx_for_type(self, scene_type: str) -> Optional[str]:
        """احصل على SFX مناسب لنوع المشهد."""
        # 1. حدد أنواع SFX المناسبة
        sfx_types = self.SCENE_SFX_MAP.get(scene_type, ["whoosh"])
        sfx_type = random.choice(sfx_types)
        
        # 2. ابحث محلياً أولاً
        local = self._find_local_sfx(sfx_type)
        if local:
            return local
        
        # 3. حمّل من المكتبة
        return self._download_sfx(sfx_type)

    def _find_local_sfx(self, sfx_type: str) -> Optional[str]:
        """البحث عن SFX محلي."""
        # ابحث بأنماط مختلفة
        patterns = [
            f"{sfx_type}_*.mp3",
            f"{sfx_type}_*.wav",
            f"{sfx_type}.mp3",
            f"{sfx_type}.wav",
            f"*{sfx_type}*.mp3",
        ]
        
        for pattern in patterns:
            files = list(self.sfx_dir.glob(pattern))
            if files:
                return str(random.choice(files))
        
        return None

    def _download_sfx(self, sfx_type: str) -> Optional[str]:
        """تحميل SFX من المكتبة."""
        urls = self.SFX_LIBRARY.get(sfx_type, [])
        if not urls:
            return None
        
        # تجنب الإفراط في المحاولات
        attempts = self._download_attempts.get(sfx_type, 0)
        if attempts >= 3:
            return None
        
        url = random.choice(urls)
        filename = f"{sfx_type}_{random.randint(1000, 9999)}.mp3"
        local_path = self.sfx_dir / filename
        
        self._download_attempts[sfx_type] = attempts + 1
        
        try:
            logger.debug(f"   ⬇ تحميل {sfx_type}...")
            response = requests.get(url, stream=True, timeout=self.timeout)
            response.raise_for_status()
            
            with open(local_path, "wb") as f:
                for chunk in response.iter_content(8192):
                    if chunk:
                        f.write(chunk)
            
            if local_path.exists() and local_path.stat().st_size > 5000:
                logger.debug(f"   ✓ تم تحميل: {filename}")
                return str(local_path)
            else:
                local_path.unlink(missing_ok=True)
                return None
                
        except Exception as e:
            logger.debug(f"فشل تحميل {sfx_type}: {e}")
            local_path.unlink(missing_ok=True)
            return None

    # ═════════════════════════════════════════════════════════════════
    #              🛠️ دوال مساعدة
    # ═════════════════════════════════════════════════════════════════
    def list_sfx_types(self) -> List[str]:
        """قائمة أنواع SFX المتاحة."""
        return list(self.SFX_LIBRARY.keys())

    def get_cached_count(self) -> Dict[str, int]:
        """عدد الملفات المحفوظة."""
        result = {}
        for sfx_type in self.SFX_LIBRARY.keys():
            files = list(self.sfx_dir.glob(f"{sfx_type}_*.mp3"))
            result[sfx_type] = len(files)
        return result

    def preload_all(self) -> int:
        """تحميل مسبق لجميع SFX (تشغيل مرة واحدة)."""
        logger.info("⬇ تحميل مسبق لجميع SFX...")
        count = 0
        for sfx_type in self.SFX_LIBRARY.keys():
            if not self._find_local_sfx(sfx_type):
                if self._download_sfx(sfx_type):
                    count += 1
        logger.info(f"✓ تم تحميل {count} مؤثر صوتي")
        return count

    def clear_cache(self) -> int:
        """مسح كل SFX المحفوظة."""
        count = 0
        try:
            for f in self.sfx_dir.glob("*.mp3"):
                f.unlink()
                count += 1
            for f in self.sfx_dir.glob("*.wav"):
                f.unlink()
                count += 1
            logger.info(f"🧹 تم مسح {count} ملف SFX")
        except Exception as e:
            logger.warning(f"⚠ فشل المسح: {e}")
        return count


# ════════════════════════════════════════════════════════════════════════
#                    اختبار سريع
# ════════════════════════════════════════════════════════════════════════
if __name__ == "__main__":
    import sys
    
    manager = SFXManager()
    
    print(f"\n📦 أنواع SFX ({len(manager.list_sfx_types())}):")
    for sfx in manager.list_sfx_types():
        print(f"   • {sfx}: {len(manager.SFX_LIBRARY[sfx])} روابط")
    
    print(f"\n💾 الملفات المحفوظة:")
    for sfx_type, count in manager.get_cached_count().items():
        print(f"   {sfx_type}: {count}")
    
    # اختبار
    if len(sys.argv) > 1 and sys.argv[1] == "preload":
        print("\n⬇ تحميل مسبق...")
        manager.preload_all()
    
    elif len(sys.argv) > 1 and sys.argv[1] == "test":
        print("\n🧪 اختبار توليد SFX:")
        test_scenes = [
            {"type": "hook", "duration": 3, "pause_after": 0.3},
            {"type": "build", "duration": 3, "pause_after": 0.3},
            {"type": "peak", "duration": 4, "pause_after": 0.3},
            {"type": "resolution", "duration": 3, "pause_after": 0.3},
            {"type": "cta", "duration": 3, "pause_after": 0},
        ]
        sfx_list = manager.get_sfx_for_scenes(test_scenes)
        print(f"\n✅ النتيجة: {len(sfx_list)} مؤثر")
        for path, time, vol in sfx_list:
            print(f"   {Path(path).name} @ {time:.1f}s vol={vol}")
