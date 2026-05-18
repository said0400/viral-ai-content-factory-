"""
🎵 Music Engine v8.0 — Pro
═══════════════════════════════════════════════════════════════
مكتبة موسيقى محلية ذكية مع:
  ✓ Metadata caching
  ✓ Smart selection (لا تكرار)
  ✓ Energy-aware
  ✓ Duration matching
  ✓ History tracking
  ✓ Auto-extend short tracks

التحسينات v8.0:
  ✓ MusicTrack dataclass
  ✓ Metadata caching (BPM, duration)
  ✓ Smart selection (avoid recent)
  ✓ Energy matching
  ✓ Duration-aware
  ✓ History tracking
═══════════════════════════════════════════════════════════════
"""

from __future__ import annotations

import os
import json
import random
import hashlib
import logging
from pathlib import Path
from enum import Enum
from dataclasses import dataclass, field, asdict
from collections import deque
from typing import Optional
from threading import Lock

from engine.video.voice.ffmpeg_utils import (
    get_audio_duration, get_audio_info,
)

logger = logging.getLogger(__name__)


# ═══════════════════════════════════════════════════════════════════
# Enums
# ═══════════════════════════════════════════════════════════════════
class EnergyLevel(str, Enum):
    """مستوى الطاقة."""
    LOW = "low"          # 0.0 - 0.4
    MEDIUM = "medium"    # 0.4 - 0.7
    HIGH = "high"        # 0.7 - 1.0
    
    @classmethod
    def from_value(cls, value: float) -> "EnergyLevel":
        if value < 0.4:
            return cls.LOW
        elif value < 0.7:
            return cls.MEDIUM
        return cls.HIGH


# ═══════════════════════════════════════════════════════════════════
# Dataclasses
# ═══════════════════════════════════════════════════════════════════
@dataclass
class MusicTrack:
    """معلومات مسار موسيقي."""
    path: str
    name: str
    mood: str
    duration: float = 0.0
    file_size: int = 0
    
    # Metadata (اختياري)
    bpm: Optional[float] = None
    energy: Optional[float] = None
    
    @property
    def filename(self) -> str:
        return Path(self.path).name
    
    @property
    def energy_level(self) -> EnergyLevel:
        if self.energy is None:
            return EnergyLevel.MEDIUM
        return EnergyLevel.from_value(self.energy)
    
    def matches_duration(self, target: float, tolerance: float = 0.3) -> bool:
        """هل الموسيقى مناسبة للمدة؟"""
        if self.duration == 0:
            return True
        # نقبل ±30% أو أطول
        return self.duration >= target * (1 - tolerance)
    
    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class MusicResult:
    """نتيجة اختيار الموسيقى."""
    success: bool
    track: Optional[MusicTrack] = None
    fallback_used: bool = False
    requested_mood: str = ""
    actual_mood: str = ""
    selection_reason: str = ""
    
    @property
    def path(self) -> Optional[str]:
        return self.track.path if self.track else None
    
    def summary(self) -> str:
        if not self.success or not self.track:
            return f"❌ No music found for '{self.requested_mood}'"
        
        return (
            f"🎵 Music selected:\n"
            f"   • File: {self.track.filename}\n"
            f"   • Mood: {self.requested_mood} → {self.actual_mood}\n"
            f"   • Duration: {self.track.duration:.1f}s\n"
            f"   • Energy: {self.track.energy_level.value}\n"
            f"   • Reason: {self.selection_reason}\n"
            f"   • Fallback: {self.fallback_used}"
        )


# ═══════════════════════════════════════════════════════════════════
# Constants
# ═══════════════════════════════════════════════════════════════════
class MusicConstants:
    """ثوابت."""
    
    # امتدادات مدعومة
    AUDIO_EXTENSIONS = ("*.mp3", "*.wav", "*.m4a", "*.ogg", "*.aac", "*.flac")
    
    # حدود
    HISTORY_SIZE = 5  # عدد الاختيارات الأخيرة (لتجنب التكرار)
    
    # Fallback priority
    PRIORITY_FALLBACKS = [
        "motivation", "cinematic", "educational", "emotional", "dark"
    ]
    
    # Cache
    METADATA_CACHE_VERSION = "v2"


# ═══════════════════════════════════════════════════════════════════
# Mood Aliases
# ═══════════════════════════════════════════════════════════════════
MOOD_ALIASES: dict[str, str] = {
    # 🔥 motivation
    "motivational": "motivation",
    "motivation": "motivation",
    "inspiring": "motivation",
    "uplifting": "motivation",
    "powerful": "motivation",
    "epic": "motivation",
    "energetic": "motivation",
    "sigma_grindset": "motivation",
    
    # 🎬 cinematic
    "cinematic": "cinematic",
    "dramatic": "cinematic",
    "trailer": "cinematic",
    "movie": "cinematic",
    "epic_cinematic": "cinematic",
    
    # 🌑 dark
    "dark": "dark",
    "mysterious": "dark",
    "horror": "dark",
    "suspense": "dark",
    "thriller": "dark",
    "sigma": "dark",
    "psychological": "dark",
    "scary": "dark",
    "creepy": "dark",
    
    # 💔 emotional
    "emotional": "emotional",
    "sad": "emotional",
    "melancholic": "emotional",
    "thoughtful": "emotional",
    "deep": "emotional",
    "romantic": "emotional",
    "love": "emotional",
    "nostalgic": "emotional",
    
    # 📚 educational
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
    "practical": "educational",
}


# ═══════════════════════════════════════════════════════════════════
# Helpers
# ═══════════════════════════════════════════════════════════════════
def normalize_mood(mood: str) -> str:
    """تطبيع الـ mood."""
    if not mood:
        return "motivation"
    
    mood_lower = mood.lower().strip()
    return MOOD_ALIASES.get(mood_lower, mood_lower)


def get_file_signature(path: Path) -> str:
    """إنشاء signature للملف (للـ caching)."""
    try:
        stat = path.stat()
        content = f"{path.name}|{stat.st_size}|{stat.st_mtime}"
        return hashlib.md5(content.encode()).hexdigest()[:12]
    except Exception:
        return ""


# ═══════════════════════════════════════════════════════════════════
# Main Class
# ═══════════════════════════════════════════════════════════════════
class MusicEngine:
    """محرك الموسيقى v8.0."""
    
    def __init__(
        self,
        music_dir: Optional[str] = None,
        load_metadata: bool = True,
        history_size: int = MusicConstants.HISTORY_SIZE,
        cache_enabled: bool = True,
    ):
        """
        Args:
            music_dir: مجلد الموسيقى
            load_metadata: تحميل metadata (duration, etc.)
            history_size: عدد الاختيارات الأخيرة (لتجنب التكرار)
            cache_enabled: تفعيل caching للـ metadata
        """
        self.music_dir = Path(
            music_dir or os.getenv("MUSIC_DIR", "engine/assets/music")
        )
        
        # Cache setup
        self.cache_enabled = cache_enabled
        if cache_enabled:
            self.cache_dir = Path(
                os.getenv("TEMP_DIR", "./temp")
            ) / "music_metadata_cache"
            self.cache_dir.mkdir(parents=True, exist_ok=True)
            self.cache_file = self.cache_dir / "library_metadata.json"
        else:
            self.cache_dir = None
            self.cache_file = None
        
        # History (لتجنب التكرار)
        self.history: deque[str] = deque(maxlen=history_size)
        
        # Thread safety
        self._lock = Lock()
        
        # تحميل المكتبة
        self.library: dict[str, list[MusicTrack]] = {}
        self._scan_library(load_metadata=load_metadata)
        
        # إحصائيات
        total = sum(len(tracks) for tracks in self.library.values())
        
        logger.info(f"🎵 MusicEngine v8.0")
        logger.info(f"   📂 المسار: {self.music_dir}")
        logger.info(f"   📚 الملفات: {total}")
        
        if self.library:
            for mood, tracks in sorted(self.library.items()):
                logger.info(f"      • {mood}: {len(tracks)} ملف")
    
    # ═══════════════════════════════════════════════════════════════
    # Library Scanning
    # ═══════════════════════════════════════════════════════════════
    def _scan_library(self, load_metadata: bool = True) -> None:
        """مسح المكتبة المحلية."""
        if not self.music_dir.exists():
            self.music_dir.mkdir(parents=True, exist_ok=True)
            logger.warning(f"⚠ تم إنشاء مجلد فارغ: {self.music_dir}")
            return
        
        # تحميل metadata من cache
        cached_metadata = self._load_metadata_cache() if load_metadata else {}
        
        # مسح المجلدات
        for mood_dir in self.music_dir.iterdir():
            if not mood_dir.is_dir():
                continue
            
            mood = mood_dir.name.lower()
            tracks = []
            
            for ext in MusicConstants.AUDIO_EXTENSIONS:
                for file_path in sorted(mood_dir.glob(ext)):
                    track = self._build_track(
                        file_path,
                        mood,
                        cached_metadata,
                        load_metadata,
                    )
                    if track:
                        tracks.append(track)
            
            if tracks:
                self.library[mood] = tracks
        
        # حفظ cache محدّث
        if load_metadata and cached_metadata is not None:
            self._save_metadata_cache()
    
    def _build_track(
        self,
        path: Path,
        mood: str,
        cached_metadata: dict,
        load_metadata: bool,
    ) -> Optional[MusicTrack]:
        """بناء MusicTrack من ملف."""
        try:
            signature = get_file_signature(path)
            
            # تحقق من الكاش
            cache_key = f"{path.name}_{signature}"
            
            if cache_key in cached_metadata:
                meta = cached_metadata[cache_key]
                return MusicTrack(
                    path=str(path),
                    name=path.stem,
                    mood=mood,
                    duration=meta.get("duration", 0),
                    file_size=meta.get("file_size", 0),
                    bpm=meta.get("bpm"),
                    energy=meta.get("energy"),
                )
            
            # توليد metadata جديد
            duration = 0.0
            if load_metadata:
                duration = get_audio_duration(str(path))
            
            track = MusicTrack(
                path=str(path),
                name=path.stem,
                mood=mood,
                duration=duration,
                file_size=path.stat().st_size,
            )
            
            # حفظ في الكاش
            if load_metadata:
                cached_metadata[cache_key] = {
                    "duration": track.duration,
                    "file_size": track.file_size,
                }
            
            return track
            
        except Exception as e:
            logger.warning(f"⚠ فشل قراءة {path.name}: {e}")
            return None
    
    # ═══════════════════════════════════════════════════════════════
    # Metadata Caching
    # ═══════════════════════════════════════════════════════════════
    def _load_metadata_cache(self) -> dict:
        """تحميل cache."""
        if not self.cache_enabled or not self.cache_file or not self.cache_file.exists():
            return {}
        
        try:
            with open(self.cache_file, "r", encoding="utf-8") as f:
                data = json.load(f)
            
            # تحقق من version
            if data.get("version") != MusicConstants.METADATA_CACHE_VERSION:
                return {}
            
            return data.get("tracks", {})
            
        except Exception as e:
            logger.debug(f"Cache load failed: {e}")
            return {}
    
    def _save_metadata_cache(self) -> None:
        """حفظ cache."""
        if not self.cache_enabled or not self.cache_file:
            return
        
        try:
            # جمع كل الـ tracks
            all_tracks = {}
            for tracks in self.library.values():
                for track in tracks:
                    signature = get_file_signature(Path(track.path))
                    cache_key = f"{Path(track.path).name}_{signature}"
                    all_tracks[cache_key] = {
                        "duration": track.duration,
                        "file_size": track.file_size,
                        "bpm": track.bpm,
                        "energy": track.energy,
                    }
            
            with open(self.cache_file, "w", encoding="utf-8") as f:
                json.dump({
                    "version": MusicConstants.METADATA_CACHE_VERSION,
                    "tracks": all_tracks,
                }, f, indent=2, ensure_ascii=False)
            
        except Exception as e:
            logger.warning(f"⚠ Cache save failed: {e}")
    
    # ═══════════════════════════════════════════════════════════════
    # Main API
    # ═══════════════════════════════════════════════════════════════
    def get_music(
        self,
        mood: str,
        duration: float = 45.0,
        energy: Optional[float] = None,
        avoid_recent: bool = True,
    ) -> MusicResult:
        """
        🎯 الحصول على موسيقى مناسبة.
        
        Args:
            mood: المزاج المطلوب
            duration: المدة المستهدفة
            energy: مستوى الطاقة (0.0-1.0)
            avoid_recent: تجنب الموسيقى المستخدمة مؤخراً
        """
        result = MusicResult(
            success=False,
            requested_mood=mood,
        )
        
        normalized_mood = normalize_mood(mood)
        result.actual_mood = normalized_mood
        
        logger.info(
            f"🎵 البحث | mood: {mood} → {normalized_mood} | "
            f"duration: {duration}s"
        )
        
        # 1️⃣ ابحث في الـ mood الأساسي
        track = self._select_track(
            normalized_mood,
            duration,
            energy,
            avoid_recent,
        )
        
        if track:
            result.success = True
            result.track = track
            result.selection_reason = f"matched_{normalized_mood}"
            self._add_to_history(track.path)
            logger.info(f"✓ {track.filename}")
            return result
        
        # 2️⃣ جرب الـ fallbacks
        logger.info(f"⚠ لا موسيقى مناسبة لـ '{normalized_mood}'، محاولة بديل...")
        
        for alt_mood in MusicConstants.PRIORITY_FALLBACKS:
            if alt_mood == normalized_mood:
                continue
            
            track = self._select_track(
                alt_mood,
                duration,
                energy,
                avoid_recent,
            )
            
            if track:
                result.success = True
                result.track = track
                result.fallback_used = True
                result.selection_reason = f"fallback_{alt_mood}"
                self._add_to_history(track.path)
                logger.info(f"✓ بديل من {alt_mood}: {track.filename}")
                return result
        
        # 3️⃣ أي شيء متاح
        all_tracks = self._get_all_tracks()
        if all_tracks:
            # تجاهل recent لو ضروري
            available = [
                t for t in all_tracks
                if not avoid_recent or t.path not in self.history
            ]
            if not available:
                available = all_tracks
            
            track = random.choice(available)
            result.success = True
            result.track = track
            result.fallback_used = True
            result.selection_reason = "random_any"
            self._add_to_history(track.path)
            logger.info(f"✓ random: {track.filename}")
            return result
        
        # ❌ لا موسيقى أبداً
        logger.warning("⚠ لا توجد موسيقى في المكتبة!")
        logger.warning(f"   ℹ أضف ملفات في: {self.music_dir}/[mood]/")
        return result
    
    # ═══════════════════════════════════════════════════════════════
    # Smart Selection
    # ═══════════════════════════════════════════════════════════════
    def _select_track(
        self,
        mood: str,
        duration: float,
        energy: Optional[float],
        avoid_recent: bool,
    ) -> Optional[MusicTrack]:
        """اختيار ذكي للموسيقى."""
        if mood not in self.library:
            return None
        
        tracks = self.library[mood]
        if not tracks:
            return None
        
        # 1. فلترة: المدة المناسبة
        suitable = [t for t in tracks if t.matches_duration(duration)]
        
        if not suitable:
            # لو لا مناسبة بالمدة، خذ الأطول
            suitable = sorted(tracks, key=lambda t: t.duration, reverse=True)[:5]
        
        # 2. فلترة: تجنب recent
        if avoid_recent and len(suitable) > 1:
            non_recent = [t for t in suitable if t.path not in self.history]
            if non_recent:
                suitable = non_recent
        
        # 3. فلترة: مطابقة الطاقة (إذا متاح)
        if energy is not None:
            target_level = EnergyLevel.from_value(energy)
            
            with_energy = [
                t for t in suitable
                if t.energy is not None and t.energy_level == target_level
            ]
            
            if with_energy:
                suitable = with_energy
        
        # 4. اختيار عشوائي من المناسب
        return random.choice(suitable) if suitable else None
    
    # ═══════════════════════════════════════════════════════════════
    # History
    # ═══════════════════════════════════════════════════════════════
    def _add_to_history(self, path: str) -> None:
        """إضافة للـ history."""
        with self._lock:
            self.history.append(path)
    
    def get_history(self) -> list[str]:
        """الحصول على history."""
        return list(self.history)
    
    def clear_history(self) -> None:
        """مسح history."""
        with self._lock:
            self.history.clear()
    
    # ═══════════════════════════════════════════════════════════════
    # Utility
    # ═══════════════════════════════════════════════════════════════
    def _get_all_tracks(self) -> list[MusicTrack]:
        """كل المسارات."""
        all_tracks = []
        for tracks in self.library.values():
            all_tracks.extend(tracks)
        return all_tracks
    
    def list_available_moods(self) -> list[str]:
        """قائمة الـ moods."""
        return list(self.library.keys())
    
    def get_tracks_for_mood(self, mood: str) -> list[MusicTrack]:
        """قائمة المسارات لـ mood."""
        normalized = normalize_mood(mood)
        return self.library.get(normalized, [])
    
    def get_random_music(
        self,
        mood: Optional[str] = None,
        duration: float = 45.0,
    ) -> Optional[str]:
        """اختيار عشوائي بسيط (للتوافق الخلفي)."""
        if mood:
            result = self.get_music(mood, duration)
            return result.path
        
        all_tracks = self._get_all_tracks()
        if not all_tracks:
            return None
        return random.choice(all_tracks).path
    
    def get_status(self) -> dict:
        """حالة المكتبة."""
        total = sum(len(tracks) for tracks in self.library.values())
        total_duration = sum(
            t.duration for tracks in self.library.values()
            for t in tracks
        )
        
        return {
            "music_dir": str(self.music_dir),
            "total_files": total,
            "total_duration_minutes": round(total_duration / 60, 1),
            "moods": {
                mood: {
                    "count": len(tracks),
                    "total_duration_minutes": round(
                        sum(t.duration for t in tracks) / 60, 1
                    ),
                }
                for mood, tracks in self.library.items()
            },
            "available": total > 0,
            "cache_enabled": self.cache_enabled,
            "history_size": len(self.history),
        }
    
    def rescan_library(self, load_metadata: bool = True) -> int:
        """إعادة مسح المكتبة."""
        self.library.clear()
        self._scan_library(load_metadata=load_metadata)
        return sum(len(tracks) for tracks in self.library.values())
    
    def clear_metadata_cache(self) -> bool:
        """مسح metadata cache (ليس الموسيقى!)."""
        if not self.cache_enabled or not self.cache_file:
            return False
        
        try:
            if self.cache_file.exists():
                self.cache_file.unlink()
                logger.info("🗑 metadata cache cleared")
                return True
        except Exception as e:
            logger.warning(f"⚠ Cache clear failed: {e}")
        return False


# ═══════════════════════════════════════════════════════════════════
# اختبار
# ═══════════════════════════════════════════════════════════════════
if __name__ == "__main__":
    import sys
    
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s | %(levelname)s | %(message)s"
    )
    
    print("=" * 60)
    print("🎵 Music Engine v8.0 Test")
    print("=" * 60)
    
    engine = MusicEngine(load_metadata=True)
    
    print("\n📊 Status:")
    status = engine.get_status()
    print(f"   📂 Path: {status['music_dir']}")
    print(f"   📦 Files: {status['total_files']}")
    print(f"   ⏱ Total: {status['total_duration_minutes']:.1f} min")
    
    if status['moods']:
        print("\n   By mood:")
        for mood, info in sorted(status['moods'].items()):
            print(
                f"      • {mood}: {info['count']} files "
                f"({info['total_duration_minutes']:.1f} min)"
            )
    
    if len(sys.argv) > 1:
        mood = sys.argv[1]
        duration = float(sys.argv[2]) if len(sys.argv) > 2 else 45.0
        
        print(f"\n🎵 Test: mood='{mood}', duration={duration}s")
        result = engine.get_music(mood, duration)
        print()
        print(result.summary())
    else:
        # اختبار شامل
        print("\n🎵 Testing all moods:")
        test_moods = [
            "motivational", "cinematic", "dark",
            "emotional", "educational", "scientific",
            "sigma", "calm", "horror",
        ]
        
        for test_mood in test_moods:
            result = engine.get_music(test_mood, duration=45.0)
            if result.success:
                print(
                    f"   ✓ {test_mood:15} → "
                    f"{result.track.filename:40} "
                    f"({result.track.duration:.1f}s)"
                )
            else:
                print(f"   ✗ {test_mood:15} → No music")
        
        print(f"\n📜 History: {len(engine.get_history())} tracks")
