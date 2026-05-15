"""
🎬 Remotion Renderer — مع نسخ الـ assets لـ public/
"""

import os
import json
import shutil
import logging
import subprocess
from pathlib import Path
from typing import Optional, Dict, List

from .video_utils import VideoUtils

logger = logging.getLogger(__name__)


class RemotionRenderer:
    """محرك التصدير النهائي باستخدام Remotion."""

    QUALITY_PRESETS = {
        "medium": {
            "crf": "23",
            "jpeg_quality": "80",
            "concurrency": "2",
            "audio_bitrate": "128k",
        },
        "high": {
            "crf": "19",
            "jpeg_quality": "90",
            "concurrency": "2",
            "audio_bitrate": "192k",
        },
        "ultra": {
            "crf": "17",
            "jpeg_quality": "95",
            "concurrency": "4",
            "audio_bitrate": "256k",
        },
    }

    LEGACY_PRESETS = {
        "tiktok": "high",
        "reels": "ultra",
        "shorts": "high",
        "preview": "medium",
    }

    PLATFORM_LIMITS = {
        "youtube_shorts": 256,
        "tiktok": 287,
        "instagram": 650,
        "twitter": 512,
    }

    DEFAULT_TIMEOUT = 600

    def __init__(self):
        self.w = int(os.getenv("VIDEO_WIDTH", "1080"))
        self.h = int(os.getenv("VIDEO_HEIGHT", "1920"))
        self.fps = int(os.getenv("VIDEO_FPS", "30"))

        self.temp_dir = Path(os.getenv("TEMP_DIR", "./temp")).resolve()
        self.out_dir = Path(os.getenv("OUTPUT_DIR", "./output")).resolve()
        self.temp_dir.mkdir(parents=True, exist_ok=True)
        self.out_dir.mkdir(parents=True, exist_ok=True)

        self.remotion_dir = Path(
            os.getenv("REMOTION_DIR", Path(__file__).parent.parent.parent / "remotion")
        ).resolve()

        self.composition_id = os.getenv("REMOTION_COMPOSITION", "ShortsVideo")
        self.utils = VideoUtils(width=self.w, height=self.h, fps=self.fps)

        self._check_node()
        self._check_remotion()

        logger.info(f"🎬 RemotionRenderer | {self.w}x{self.h}@{self.fps}fps")
        logger.info(f"   📁 Remotion dir: {self.remotion_dir}")
        logger.info(f"   📁 Temp dir: {self.temp_dir}")

    def _check_node(self) -> None:
        try:
            result = subprocess.run(
                ["node", "--version"],
                capture_output=True, text=True, timeout=10, check=True,
            )
            logger.info(f"✓ Node.js {result.stdout.strip()}")
        except (subprocess.CalledProcessError, FileNotFoundError):
            raise RuntimeError("❌ Node.js غير مثبت!")

    def _check_remotion(self) -> None:
        if not self.remotion_dir.exists():
            raise RuntimeError(f"❌ مجلد Remotion غير موجود: {self.remotion_dir}")
        if not (self.remotion_dir / "node_modules").exists():
            raise RuntimeError(f"❌ Remotion غير مُثبّت!")
        logger.info("✓ Remotion installed")

    def render_final(
        self,
        props: Dict,
        output_path: str,
        quality: str = "high",
        composition_id: Optional[str] = None,
        metadata: Optional[Dict] = None,
        preset: Optional[str] = None,
    ) -> str:
        """التصدير النهائي للفيديو."""
        if preset and quality == "high":
            quality = self.LEGACY_PRESETS.get(preset, "high")

        cfg = self.QUALITY_PRESETS.get(quality, self.QUALITY_PRESETS["high"])
        comp_id = composition_id or self.composition_id

        output_path = str(Path(output_path).resolve())
        Path(output_path).parent.mkdir(parents=True, exist_ok=True)

        logger.info(f"🚀 التصدير بـ Remotion [{quality}] | Composition: {comp_id}")

        # 1) فحص Props
        self._validate_props(props)

        # 2) 🆕 نسخ الملفات لـ public
        props = self._copy_assets_to_public(props)

        # 3) كتابة props
        props_file = self._write_props(props)

        try:
            # 4) تشغيل Remotion
            self._run_remotion(comp_id, output_path, props_file, cfg)

            # 5) إضافة Metadata
            if metadata:
                self._add_metadata(output_path, metadata)

            # 6) التحقق
            if not Path(output_path).exists():
                raise RuntimeError("❌ ملف الإخراج لم يُنشأ")

            # 7) عرض المعلومات
            self._print_output_info(output_path)

            return output_path

        finally:
            logger.info(f"📝 Props file kept: {props_file}")
            self._cleanup_public_assets()

    def _validate_props(self, props: Dict) -> None:
        """التحقق من صحة الـ props."""
        logger.info("🔍 Validating props...")

        required_fields = ["scenes", "totalDuration", "fps", "width", "height"]
        for field in required_fields:
            if field not in props:
                raise ValueError(f"❌ Missing required field: {field}")

        scenes = props.get("scenes", [])
        if not scenes:
            raise ValueError("❌ No scenes provided!")

        logger.info(f"   ✓ {len(scenes)} scenes")

        for i, scene in enumerate(scenes):
            bg_path = scene.get("backgroundPath", "")
            if bg_path:
                if not Path(bg_path).exists():
                    logger.warning(f"   ⚠ Scene {i} video not found: {bg_path}")
                else:
                    size_kb = Path(bg_path).stat().st_size / 1024
                    logger.info(f"   ✓ Scene {i} video: {size_kb:.1f} KB")

        audio_path = props.get("audioPath", "")
        if audio_path and Path(audio_path).exists():
            size_kb = Path(audio_path).stat().st_size / 1024
            logger.info(f"   ✓ Audio: {size_kb:.1f} KB")

        logger.info(f"   ✓ Duration: {props.get('totalDuration')}s")
        logger.info("✅ Props validation passed!")

    # 🆕 نسخ الملفات لـ remotion/public/
    def _copy_assets_to_public(self, props: Dict) -> Dict:
        """نسخ الـ assets إلى remotion/public/ وتحديث المسارات."""
        logger.info("📦 Copying assets to remotion/public/...")

        public_dir = self.remotion_dir / "public"
        public_dir.mkdir(exist_ok=True)

        public_footage = public_dir / "footage"
        public_audio = public_dir / "audio"
        public_footage.mkdir(exist_ok=True)
        public_audio.mkdir(exist_ok=True)

        # نسخ الصوت
        audio_path = props.get("audioPath", "")
        if audio_path and Path(audio_path).exists():
            audio_filename = Path(audio_path).name
            new_audio_path = public_audio / audio_filename
            shutil.copy2(audio_path, new_audio_path)
            props["audioPath"] = f"audio/{audio_filename}"
            logger.info(f"   ✓ Audio: {audio_filename}")
        elif audio_path:
            logger.warning(f"   ⚠ Audio not found: {audio_path}")

        # نسخ الفيديوهات
        copied = 0
        for scene in props.get("scenes", []):
            bg_path = scene.get("backgroundPath", "")
            if bg_path and Path(bg_path).exists():
                video_filename = Path(bg_path).name
                new_video_path = public_footage / video_filename
                shutil.copy2(bg_path, new_video_path)
                scene["backgroundPath"] = f"footage/{video_filename}"
                copied += 1

        logger.info(f"   ✓ Videos: {copied} copied")
        return props

    def _cleanup_public_assets(self) -> None:
        """تنظيف الـ assets المنسوخة."""
        try:
            public_dir = self.remotion_dir / "public"
            for subdir in ["footage", "audio"]:
                target = public_dir / subdir
                if target.exists():
                    shutil.rmtree(target, ignore_errors=True)
            logger.info("🧹 Cleaned up public assets")
        except Exception as e:
            logger.warning(f"⚠ فشل تنظيف public/: {e}")

    def _write_props(self, props: Dict) -> str:
        """كتابة props إلى ملف JSON."""
        props_file = self.temp_dir / "remotion_props.json"
        with open(props_file, "w", encoding="utf-8") as f:
            json.dump(props, f, ensure_ascii=False, indent=2)
        absolute_path = str(props_file.resolve())
        size_kb = props_file.stat().st_size / 1024
        logger.info(f"📝 Props written: {absolute_path} ({size_kb:.1f} KB)")
        return absolute_path

    def _run_remotion(
        self, composition_id: str, output_path: str, props_file: str, cfg: dict
    ) -> None:
        """تشغيل Remotion."""
        props_file = str(Path(props_file).resolve())
        output_path = str(Path(output_path).resolve())

        if not Path(props_file).exists():
            raise FileNotFoundError(f"❌ Props file not found: {props_file}")

        cmd = [
            "npx", "remotion", "render",
            "src/index.ts",
            composition_id,
            output_path,
            "--props", props_file,
            "--concurrency", cfg["concurrency"],
            "--jpeg-quality", cfg["jpeg_quality"],
            "--crf", cfg["crf"],
            "--codec", "h264",
            "--pixel-format", "yuv420p",
            "--log", "verbose",
            "--timeout", "60000",  # 🆕 60 ثانية بدلاً من 30
        ]

        logger.info("=" * 60)
        logger.info(f"🎬 Running Remotion render...")
        logger.info(f"   📋 Composition: {composition_id}")
        logger.info(f"   📁 Working dir: {self.remotion_dir}")
        logger.info(f"   📤 Output: {output_path}")
        logger.info("=" * 60)

        try:
            result = subprocess.run(
                cmd,
                cwd=str(self.remotion_dir),
                timeout=self.DEFAULT_TIMEOUT,
            )

            if result.returncode != 0:
                raise RuntimeError(
                    f"❌ Remotion failed (exit code: {result.returncode})"
                )

            logger.info("✅ Remotion render completed!")

        except subprocess.TimeoutExpired:
            raise RuntimeError(f"❌ Remotion timeout ({self.DEFAULT_TIMEOUT}s)")

    def _add_metadata(self, video_path: str, metadata: Dict) -> None:
        """إضافة metadata."""
        if not metadata:
            return

        temp_output = video_path.replace(".mp4", "_meta.mp4")
        cmd = ["ffmpeg", "-y", "-loglevel", "error", "-i", video_path, "-c", "copy"]
        cmd.extend(self._build_metadata_args(metadata))
        cmd.append(temp_output)

        try:
            subprocess.run(cmd, check=True, capture_output=True, timeout=120)
            shutil.move(temp_output, video_path)
            logger.info("✓ Metadata added")
        except Exception as e:
            logger.warning(f"⚠ فشل إضافة metadata: {e}")
            Path(temp_output).unlink(missing_ok=True)

    def _build_metadata_args(self, metadata: Dict) -> List[str]:
        """بناء معاملات Metadata."""
        args = []
        field_map = {
            "title": "title", "description": "comment", "comment": "comment",
            "author": "author", "artist": "artist", "album": "album",
            "year": "date", "genre": "genre",
        }
        for key, ffmpeg_key in field_map.items():
            value = metadata.get(key)
            if value:
                value = str(value).replace('"', "'")[:200]
                args.extend(["-metadata", f"{ffmpeg_key}={value}"])
        return args

    def _print_output_info(self, path: str) -> None:
        """عرض معلومات الفيديو."""
        try:
            size_mb = Path(path).stat().st_size / (1024 * 1024)
            duration = self.utils.get_duration(path)
            w, h = self.utils.get_dimensions(path)
            logger.info(f"✓ {Path(path).name}")
            logger.info(f"  📦 {size_mb:.1f} MB | ⏱ {duration:.1f}s | 📐 {w}x{h}")
        except Exception as e:
            logger.warning(f"⚠ فشل قراءة المعلومات: {e}")

    def create_thumbnail(self, video, output, timestamp=1.5, resize=True):
        return self.utils.create_thumbnail(video, output, timestamp, resize)

    def create_multiple_thumbnails(self, video, output_dir, count=3):
        return self.utils.create_multiple_thumbnails(video, output_dir, count)

    def get_duration(self, path):
        return self.utils.get_duration(path)

    def get_dimensions(self, path):
        return self.utils.get_dimensions(path)

    def get_video_info(self, path):
        return self.utils.get_video_info(path)

    def validate_for_platform(self, video_path, platform="youtube_shorts"):
        return self.utils.validate_for_platform(video_path, platform)

    def cleanup_temp(self, keep_subdirs=False):
        """تنظيف الملفات المؤقتة."""
        try:
            if not self.temp_dir.exists():
                return
            shutil.rmtree(self.temp_dir, ignore_errors=True)
            self.temp_dir.mkdir(parents=True, exist_ok=True)
            logger.info("🧹 تم تنظيف الملفات المؤقتة")
        except Exception as e:
            logger.warning(f"⚠ فشل التنظيف: {e}")

    def cleanup_specific(self, patterns):
        count = 0
        try:
            for pattern in patterns:
                for f in self.temp_dir.rglob(pattern):
                    if f.is_file():
                        f.unlink(missing_ok=True)
                        count += 1
        except Exception:
            pass
        return count
