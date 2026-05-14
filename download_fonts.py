"""
🔤 Arabic Font Downloader - Fixed v3 (Variable Fonts Support)
═══════════════════════════════════════════════════════════════
يستخدم Variable Fonts من Google Fonts (الموجودة فعلاً 2024)
═══════════════════════════════════════════════════════════════
"""

import sys
import time
import requests
from pathlib import Path
from typing import Optional


# ─── إعدادات عامة ────────────────────────────────────────────────────────
TIMEOUT = 30
MAX_RETRIES = 3
USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
MIN_FONT_SIZE = 10_000

HEADERS = {"User-Agent": USER_AGENT}


# ─── قائمة الخطوط (Variable Fonts الموجودة فعلاً) ───────────────────
FONTS = {
    # 🌟 Cairo Variable - يحتوي كل الأوزان في ملف واحد!
    "Cairo-VF.ttf": [
        "https://github.com/google/fonts/raw/main/ofl/cairo/Cairo%5Bslnt%2Cwght%5D.ttf",
        "https://github.com/google/fonts/raw/main/ofl/cairo/Cairo[slnt,wght].ttf",
    ],

    # 🎯 Tajawal - Static (يعمل دائماً)
    "Tajawal-ExtraBold.ttf": [
        "https://github.com/google/fonts/raw/main/ofl/tajawal/Tajawal-ExtraBold.ttf",
    ],
    "Tajawal-Bold.ttf": [
        "https://github.com/google/fonts/raw/main/ofl/tajawal/Tajawal-Bold.ttf",
    ],
    "Tajawal-Regular.ttf": [
        "https://github.com/google/fonts/raw/main/ofl/tajawal/Tajawal-Regular.ttf",
    ],

    # 💪 Almarai - Static (يعمل دائماً)
    "Almarai-ExtraBold.ttf": [
        "https://github.com/google/fonts/raw/main/ofl/almarai/Almarai-ExtraBold.ttf",
    ],
    "Almarai-Bold.ttf": [
        "https://github.com/google/fonts/raw/main/ofl/almarai/Almarai-Bold.ttf",
    ],
    "Almarai-Regular.ttf": [
        "https://github.com/google/fonts/raw/main/ofl/almarai/Almarai-Regular.ttf",
    ],

    # 📜 Amiri - Static (يعمل دائماً)
    "Amiri-Bold.ttf": [
        "https://github.com/google/fonts/raw/main/ofl/amiri/Amiri-Bold.ttf",
    ],
    "Amiri-Regular.ttf": [
        "https://github.com/google/fonts/raw/main/ofl/amiri/Amiri-Regular.ttf",
    ],

    # 🎨 Changa Variable
    "Changa-VF.ttf": [
        "https://github.com/google/fonts/raw/main/ofl/changa/Changa%5Bwght%5D.ttf",
        "https://github.com/google/fonts/raw/main/ofl/changa/Changa[wght].ttf",
    ],

    # ✍️ Noto Naskh Arabic Variable
    "NotoNaskhArabic-VF.ttf": [
        "https://github.com/google/fonts/raw/main/ofl/notonaskharabic/NotoNaskhArabic%5Bwght%5D.ttf",
        "https://github.com/google/fonts/raw/main/ofl/notonaskharabic/NotoNaskhArabic[wght].ttf",
    ],
}

# ─── الخطوط الأساسية ────────────────────────────────────────────────
# يكفي خط واحد ليعمل المشروع
ESSENTIAL_FONTS = {
    "Tajawal-ExtraBold.ttf",
}


# ─── ألوان الطباعة ────────────────────────────────────────────────────────
class Colors:
    OK = "\033[92m"
    WARN = "\033[93m"
    ERR = "\033[91m"
    INFO = "\033[96m"
    BOLD = "\033[1m"
    RESET = "\033[0m"


def log(msg: str, color: str = "") -> None:
    print(f"{color}{msg}{Colors.RESET}")


# ─── التحقق من صحة الخط ──────────────────────────────────────────────────
def is_valid_font(path: Path) -> bool:
    """التحقق من أن الملف خط TTF/OTF صالح."""
    try:
        if not path.exists() or path.stat().st_size < MIN_FONT_SIZE:
            return False

        with open(path, "rb") as f:
            header = f.read(4)

        valid_signatures = (
            b"\x00\x01\x00\x00",
            b"OTTO",
            b"true",
            b"typ1",
            b"wOFF",
            b"wOF2",
        )
        return header in valid_signatures
    except Exception:
        return False


# ─── تحميل ملف واحد مع إعادة المحاولة ──────────────────────────────────
def download_file(url: str, destination: Path, retries: int = MAX_RETRIES) -> bool:
    """تحميل ملف من URL مع retry تلقائي."""
    for attempt in range(1, retries + 1):
        try:
            response = requests.get(
                url,
                headers=HEADERS,
                timeout=TIMEOUT,
                stream=True,
                allow_redirects=True,
            )
            response.raise_for_status()

            destination.parent.mkdir(parents=True, exist_ok=True)
            with open(destination, "wb") as f:
                for chunk in response.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)

            if is_valid_font(destination):
                return True
            else:
                destination.unlink(missing_ok=True)
                return False

        except requests.exceptions.RequestException as e:
            if attempt < retries:
                log(f"      ⏳ محاولة {attempt}/{retries} فشلت، إعادة...", Colors.WARN)
                time.sleep(2 ** attempt)
            else:
                log(f"      ❌ {type(e).__name__}: {str(e)[:80]}", Colors.ERR)
        except Exception as e:
            log(f"      ❌ خطأ غير متوقع: {e}", Colors.ERR)
            break

    return False


# ─── تحميل خط واحد ───────────────────────────────────────────────────
def download_font(font_name: str, urls: list, destination: Path) -> bool:
    """محاولة تحميل خط من عدة مصادر."""
    if is_valid_font(destination):
        log(f"  ✓ {font_name} موجود بالفعل", Colors.OK)
        return True

    log(f"  ↓ تحميل {font_name}...", Colors.INFO)

    for i, url in enumerate(urls, 1):
        source_label = "أساسي" if i == 1 else f"بديل #{i-1}"
        log(f"    [{source_label}] {url[:70]}...", Colors.INFO)

        if download_file(url, destination):
            size_kb = destination.stat().st_size / 1024
            log(f"    ✓ تم التحميل ({size_kb:.1f} KB)", Colors.OK)
            return True

    log(f"  ✗ فشل تحميل {font_name} من جميع المصادر", Colors.ERR)
    return False


# ─── الدالة الرئيسية ─────────────────────────────────────────────────────
def download_fonts(target: str = "engine/assets/fonts") -> bool:
    """تحميل جميع الخطوط العربية."""
    fonts_dir = Path(target)
    fonts_dir.mkdir(parents=True, exist_ok=True)

    log("\n" + "═" * 60, Colors.INFO)
    log("  🔤 ARABIC FONTS DOWNLOADER v3", Colors.BOLD)
    log("═" * 60, Colors.INFO)
    log(f"📂 المسار: {fonts_dir.resolve()}\n", Colors.INFO)

    total = len(FONTS)
    success_count = 0
    failed_essentials = []

    for font_name, urls in FONTS.items():
        destination = fonts_dir / font_name
        if download_font(font_name, urls, destination):
            success_count += 1
        else:
            if font_name in ESSENTIAL_FONTS:
                failed_essentials.append(font_name)
        print()

    # ── الملخص ────────────────────────────────────────────────────
    total_files = len(list(fonts_dir.glob("*.ttf"))) + len(list(fonts_dir.glob("*.otf")))

    log("═" * 60, Colors.INFO)
    log("  📊 الملخص", Colors.BOLD)
    log("═" * 60, Colors.INFO)
    log(f"  ✓ تم تحميل: {success_count}/{total} خط", Colors.OK)
    log(f"  📦 إجمالي الخطوط في المجلد: {total_files}", Colors.INFO)
    log(f"  📂 {fonts_dir.resolve()}", Colors.INFO)

    if total_files == 0:
        log(f"\n  ❌ لا يوجد أي خط متاح!", Colors.ERR)
        log("═" * 60 + "\n", Colors.INFO)
        return False

    if failed_essentials:
        log(f"\n  ⚠ فشل تحميل: {', '.join(failed_essentials)}", Colors.WARN)
        log(f"  ✓ لكن يوجد {total_files} خط بديل، سيعمل المشروع", Colors.OK)

    log("\n  ✅ المشروع جاهز للعمل", Colors.OK)
    log("═" * 60 + "\n", Colors.INFO)
    return True


# ─── نقطة الدخول ─────────────────────────────────────────────────────────
if __name__ == "__main__":
    success = download_fonts()
    sys.exit(0 if success else 1)
