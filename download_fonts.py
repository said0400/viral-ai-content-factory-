"""
🔤 Arabic Font Downloader v5
═══════════════════════════════════════════════════════════════
يحمّل الخطوط العربية محلياً (اختياري)

⚠️ ملاحظة مهمة:
   إذا تستخدم @remotion/google-fonts (الموصى به)،
   لا تحتاج هذا السكريبت!
   
   Remotion يحمّل الخطوط تلقائياً من Google.

الاستخدام الموصى به:
   1. ⭐ @remotion/google-fonts (في package.json)
   2. هذا السكريبت كـ fallback إذا فشل التحميل

التحسينات v5:
  ✓ لا يكتب فوق load-fonts.ts المحسّن
  ✓ توضيح أن السكريبت اختياري
  ✓ التحقق من وجود @remotion/google-fonts
  ✓ Cache check ذكي
═══════════════════════════════════════════════════════════════
"""

from __future__ import annotations

import sys
import time
import json
import argparse
import shutil
import logging
from pathlib import Path
from dataclasses import dataclass
from enum import Enum
from typing import Optional

import requests

# ═══════════════════════════════════════════════════════════════
# Logger
# ═══════════════════════════════════════════════════════════════
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s | %(levelname)-7s | %(message)s',
)
logger = logging.getLogger(__name__)


# ═══════════════════════════════════════════════════════════════
# Constants
# ═══════════════════════════════════════════════════════════════
class Constants:
    TIMEOUT = 30
    MAX_RETRIES = 3
    MIN_FONT_SIZE = 8_000  # خفضنا للـ subset fonts
    CHUNK_SIZE = 8192
    USER_AGENT = (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36"
    )


HEADERS = {"User-Agent": Constants.USER_AGENT}


# ═══════════════════════════════════════════════════════════════
# Colors (للـ terminal)
# ═══════════════════════════════════════════════════════════════
class Colors:
    OK = "\033[92m"
    WARN = "\033[93m"
    ERR = "\033[91m"
    INFO = "\033[96m"
    BOLD = "\033[1m"
    RESET = "\033[0m"


def colored(text: str, color: str) -> str:
    """نص ملوّن."""
    return f"{color}{text}{Colors.RESET}"


# ═══════════════════════════════════════════════════════════════
# Dataclasses
# ═══════════════════════════════════════════════════════════════
@dataclass
class FontDefinition:
    """تعريف خط."""
    name: str
    family: str
    weight: str
    urls: list[str]
    essential: bool = False


@dataclass
class DownloadResult:
    """نتيجة تحميل."""
    success: bool
    font_name: str
    file_path: Optional[Path] = None
    file_size: int = 0
    cached: bool = False
    error: Optional[str] = None


# ═══════════════════════════════════════════════════════════════
# Default Paths
# ═══════════════════════════════════════════════════════════════
DEFAULT_REMOTION_FONTS = "remotion/public/fonts"
DEFAULT_LEGACY_FONTS = "engine/assets/fonts"


# ═══════════════════════════════════════════════════════════════
# Fonts Catalog
# ═══════════════════════════════════════════════════════════════
FONTS: list[FontDefinition] = [
    # ⭐ Cairo (الأساسي)
    FontDefinition(
        name="Cairo-Regular.ttf",
        family="Cairo",
        weight="400",
        urls=[
            "https://github.com/google/fonts/raw/main/ofl/cairo/static/Cairo-Regular.ttf",
        ],
    ),
    FontDefinition(
        name="Cairo-Bold.ttf",
        family="Cairo",
        weight="700",
        urls=[
            "https://github.com/google/fonts/raw/main/ofl/cairo/static/Cairo-Bold.ttf",
        ],
        essential=True,
    ),
    FontDefinition(
        name="Cairo-Black.ttf",
        family="Cairo",
        weight="900",
        urls=[
            "https://github.com/google/fonts/raw/main/ofl/cairo/static/Cairo-Black.ttf",
        ],
    ),
    
    # Tajawal
    FontDefinition(
        name="Tajawal-Regular.ttf",
        family="Tajawal",
        weight="400",
        urls=[
            "https://github.com/google/fonts/raw/main/ofl/tajawal/Tajawal-Regular.ttf",
        ],
    ),
    FontDefinition(
        name="Tajawal-Bold.ttf",
        family="Tajawal",
        weight="700",
        urls=[
            "https://github.com/google/fonts/raw/main/ofl/tajawal/Tajawal-Bold.ttf",
        ],
    ),
    FontDefinition(
        name="Tajawal-ExtraBold.ttf",
        family="Tajawal",
        weight="800",
        urls=[
            "https://github.com/google/fonts/raw/main/ofl/tajawal/Tajawal-ExtraBold.ttf",
        ],
    ),
    
    # Almarai
    FontDefinition(
        name="Almarai-Regular.ttf",
        family="Almarai",
        weight="400",
        urls=[
            "https://github.com/google/fonts/raw/main/ofl/almarai/Almarai-Regular.ttf",
        ],
    ),
    FontDefinition(
        name="Almarai-Bold.ttf",
        family="Almarai",
        weight="700",
        urls=[
            "https://github.com/google/fonts/raw/main/ofl/almarai/Almarai-Bold.ttf",
        ],
    ),
    FontDefinition(
        name="Almarai-ExtraBold.ttf",
        family="Almarai",
        weight="800",
        urls=[
            "https://github.com/google/fonts/raw/main/ofl/almarai/Almarai-ExtraBold.ttf",
        ],
    ),
]


# Weight name → CSS value
WEIGHT_MAP: dict[str, str] = {
    "Thin": "100",
    "ExtraLight": "200",
    "Light": "300",
    "Regular": "400",
    "Medium": "500",
    "SemiBold": "600",
    "Bold": "700",
    "ExtraBold": "800",
    "Black": "900",
}


# Valid font file signatures
VALID_FONT_SIGNATURES = (
    b"\x00\x01\x00\x00",  # TrueType
    b"OTTO",              # OpenType
    b"true",              # TrueType (Mac)
    b"typ1",              # PostScript
    b"wOFF",              # WOFF
    b"wOF2",              # WOFF2
)


# ═══════════════════════════════════════════════════════════════
# Validation
# ═══════════════════════════════════════════════════════════════
def is_valid_font(path: Path) -> bool:
    """التحقق من صحة ملف الخط."""
    try:
        if not path.exists():
            return False
        
        if path.stat().st_size < Constants.MIN_FONT_SIZE:
            return False
        
        with open(path, "rb") as f:
            header = f.read(4)
        
        return header in VALID_FONT_SIGNATURES
        
    except Exception:
        return False


# ═══════════════════════════════════════════════════════════════
# Download Logic
# ═══════════════════════════════════════════════════════════════
def download_url(
    url: str,
    destination: Path,
    retries: int = Constants.MAX_RETRIES,
) -> bool:
    """تحميل من URL مع retry."""
    for attempt in range(1, retries + 1):
        try:
            response = requests.get(
                url,
                headers=HEADERS,
                timeout=Constants.TIMEOUT,
                stream=True,
                allow_redirects=True,
            )
            response.raise_for_status()
            
            destination.parent.mkdir(parents=True, exist_ok=True)
            
            with open(destination, "wb") as f:
                for chunk in response.iter_content(chunk_size=Constants.CHUNK_SIZE):
                    if chunk:
                        f.write(chunk)
            
            if is_valid_font(destination):
                return True
            
            destination.unlink(missing_ok=True)
            return False
            
        except requests.exceptions.RequestException as e:
            if attempt < retries:
                wait = 2 ** attempt
                logger.warning(
                    f"      ⏳ Attempt {attempt}/{retries} failed, "
                    f"retrying in {wait}s..."
                )
                time.sleep(wait)
            else:
                logger.error(
                    f"      ❌ {type(e).__name__}: {str(e)[:80]}"
                )
        except Exception as e:
            logger.error(f"      ❌ Unexpected: {e}")
            break
    
    return False


def download_font(
    font: FontDefinition,
    destination: Path,
    force: bool = False,
) -> DownloadResult:
    """تحميل خط واحد."""
    # Cache check
    if not force and is_valid_font(destination):
        size = destination.stat().st_size
        logger.info(colored(f"  ✓ {font.name} (cached, {size:,} bytes)", Colors.OK))
        return DownloadResult(
            success=True,
            font_name=font.name,
            file_path=destination,
            file_size=size,
            cached=True,
        )
    
    logger.info(colored(f"  ↓ Downloading {font.name}...", Colors.INFO))
    
    # جرب URLs
    for i, url in enumerate(font.urls, 1):
        source = "primary" if i == 1 else f"backup #{i-1}"
        logger.debug(f"    [{source}] {url[:70]}...")
        
        if download_url(url, destination):
            size = destination.stat().st_size
            logger.info(
                colored(f"    ✓ Downloaded ({size / 1024:.1f} KB)", Colors.OK)
            )
            return DownloadResult(
                success=True,
                font_name=font.name,
                file_path=destination,
                file_size=size,
            )
    
    logger.error(colored(f"  ✗ Failed: {font.name}", Colors.ERR))
    return DownloadResult(
        success=False,
        font_name=font.name,
        error="All sources failed",
    )


# ═══════════════════════════════════════════════════════════════
# CSS Generation
# ═══════════════════════════════════════════════════════════════
def generate_css(fonts_dir: Path) -> Optional[Path]:
    """توليد ملف CSS."""
    css_path = fonts_dir.parent / "fonts.css"
    
    fonts = list(fonts_dir.glob("*.ttf")) + list(fonts_dir.glob("*.otf"))
    if not fonts:
        return None
    
    logger.info(colored("\n📝 Generating CSS...", Colors.INFO))
    
    # Group by family
    families: dict[str, list[tuple[str, str]]] = {}
    
    for font_file in fonts:
        name = font_file.stem
        
        if "-" in name:
            family, weight_name = name.rsplit("-", 1)
        else:
            family = name
            weight_name = "Regular"
        
        weight = WEIGHT_MAP.get(weight_name, "400")
        
        if family not in families:
            families[family] = []
        families[family].append((weight, font_file.name))
    
    # Build CSS
    lines = [
        "/* 🔤 Auto-generated Arabic Fonts CSS */",
        "/* DO NOT EDIT MANUALLY */",
        "",
    ]
    
    for family, font_list in families.items():
        for weight, filename in sorted(font_list, key=lambda x: x[0]):
            lines.extend([
                "@font-face {",
                f"  font-family: '{family}';",
                f"  src: url('/fonts/{filename}') format('truetype');",
                f"  font-weight: {weight};",
                f"  font-style: normal;",
                f"  font-display: swap;",
                "}",
                "",
            ])
    
    try:
        css_path.write_text("\n".join(lines), encoding="utf-8")
        logger.info(colored(f"  ✓ CSS saved: {css_path}", Colors.OK))
        logger.info(
            colored(
                f"  📊 {len(families)} families, {len(fonts)} files",
                Colors.INFO,
            )
        )
        return css_path
    except Exception as e:
        logger.error(colored(f"  ❌ CSS failed: {e}", Colors.ERR))
        return None


# ═══════════════════════════════════════════════════════════════
# Check Remotion Setup
# ═══════════════════════════════════════════════════════════════
def check_remotion_google_fonts(remotion_dir: Path) -> bool:
    """تحقق من وجود @remotion/google-fonts."""
    package_json = remotion_dir / "package.json"
    
    if not package_json.exists():
        return False
    
    try:
        with open(package_json, "r", encoding="utf-8") as f:
            data = json.load(f)
        
        deps = {
            **data.get("dependencies", {}),
            **data.get("devDependencies", {}),
        }
        
        return "@remotion/google-fonts" in deps
    except Exception:
        return False


# ═══════════════════════════════════════════════════════════════
# Main
# ═══════════════════════════════════════════════════════════════
def download_all_fonts(
    target: str = DEFAULT_REMOTION_FONTS,
    also_legacy: bool = False,
    generate_css_file: bool = True,
    force: bool = False,
) -> bool:
    """تحميل كل الخطوط."""
    fonts_dir = Path(target)
    fonts_dir.mkdir(parents=True, exist_ok=True)
    
    # ═══ Banner ═══
    print()
    logger.info(colored("═" * 60, Colors.INFO))
    logger.info(colored("  🔤 ARABIC FONTS DOWNLOADER v5", Colors.BOLD))
    logger.info(colored("═" * 60, Colors.INFO))
    logger.info(colored(f"📂 Target: {fonts_dir.resolve()}", Colors.INFO))
    
    # ═══ Warning عن @remotion/google-fonts ═══
    if "remotion" in str(fonts_dir):
        remotion_dir = fonts_dir.parent.parent
        if check_remotion_google_fonts(remotion_dir):
            logger.warning(
                colored(
                    "\n⚠️  Notice: @remotion/google-fonts is installed!\n"
                    "   You may not need local fonts.\n"
                    "   See: https://www.remotion.dev/docs/google-fonts",
                    Colors.WARN,
                )
            )
            response = input(
                colored(
                    "\n  Continue anyway? (y/N): ",
                    Colors.WARN,
                )
            )
            if response.lower() != 'y':
                logger.info("Cancelled.")
                return True
    
    if also_legacy:
        logger.info(
            colored(f"📂 + Legacy: {Path(DEFAULT_LEGACY_FONTS).resolve()}", Colors.INFO)
        )
    
    print()
    
    # ═══ Download ═══
    total = len(FONTS)
    results: list[DownloadResult] = []
    
    for font in FONTS:
        destination = fonts_dir / font.name
        result = download_font(font, destination, force=force)
        results.append(result)
        
        # Copy to legacy if needed
        if result.success and also_legacy:
            try:
                legacy_path = Path(DEFAULT_LEGACY_FONTS) / font.name
                legacy_path.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(destination, legacy_path)
                logger.info(colored(f"    ✓ Copied to legacy", Colors.OK))
            except Exception as e:
                logger.warning(colored(f"    ⚠ Legacy copy failed: {e}", Colors.WARN))
        
        print()
    
    # ═══ Generate CSS ═══
    if generate_css_file:
        generate_css(fonts_dir)
    
    # ═══ Summary ═══
    print()
    logger.info(colored("═" * 60, Colors.INFO))
    logger.info(colored("  📊 SUMMARY", Colors.BOLD))
    logger.info(colored("═" * 60, Colors.INFO))
    
    successful = sum(1 for r in results if r.success)
    cached = sum(1 for r in results if r.cached)
    failed = total - successful
    
    failed_essentials = [
        r.font_name for r in results
        if not r.success and any(f.name == r.font_name and f.essential for f in FONTS)
    ]
    
    logger.info(colored(f"  ✓ Successful: {successful}/{total}", Colors.OK))
    if cached > 0:
        logger.info(colored(f"  ⚡ Cached: {cached}", Colors.INFO))
    if failed > 0:
        logger.warning(colored(f"  ✗ Failed: {failed}", Colors.WARN))
    
    total_files = (
        len(list(fonts_dir.glob("*.ttf"))) +
        len(list(fonts_dir.glob("*.otf")))
    )
    logger.info(colored(f"  📦 Total in folder: {total_files}", Colors.INFO))
    
    if failed_essentials:
        logger.error(
            colored(
                f"\n  ❌ Essential fonts failed: {', '.join(failed_essentials)}",
                Colors.ERR,
            )
        )
        if total_files > 0:
            logger.warning(
                colored(
                    f"  ⚠ But {total_files} fonts available, may still work",
                    Colors.WARN,
                )
            )
    
    logger.info(colored("\n  ✅ Done!", Colors.OK))
    logger.info(colored("═" * 60, Colors.INFO))
    print()
    
    return total_files > 0


# ═══════════════════════════════════════════════════════════════
# CLI
# ═══════════════════════════════════════════════════════════════
def main():
    parser = argparse.ArgumentParser(
        description="🔤 Arabic Font Downloader",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python download_fonts.py
  python download_fonts.py --target remotion/public/fonts
  python download_fonts.py --legacy
  python download_fonts.py --force
  python download_fonts.py --no-css
        """,
    )
    
    parser.add_argument(
        "--target",
        type=str,
        default=DEFAULT_REMOTION_FONTS,
        help=f"Target directory (default: {DEFAULT_REMOTION_FONTS})",
    )
    parser.add_argument(
        "--legacy",
        action="store_true",
        help=f"Also copy to legacy dir ({DEFAULT_LEGACY_FONTS})",
    )
    parser.add_argument(
        "--no-css",
        action="store_true",
        help="Skip CSS generation",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Re-download even if cached",
    )
    parser.add_argument(
        "--legacy-only",
        action="store_true",
        help="Download to legacy dir only",
    )
    
    args = parser.parse_args()
    
    # Determine target
    if args.legacy_only:
        target = DEFAULT_LEGACY_FONTS
        also_legacy = False
        generate_css_file = False
    else:
        target = args.target
        also_legacy = args.legacy
        generate_css_file = not args.no_css
    
    success = download_all_fonts(
        target=target,
        also_legacy=also_legacy,
        generate_css_file=generate_css_file,
        force=args.force,
    )
    
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
