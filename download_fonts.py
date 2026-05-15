"""
🔤 Arabic Font Downloader v4 - Remotion Edition
═══════════════════════════════════════════════════════════════
يحمّل الخطوط العربية إلى:
  📁 remotion/public/fonts/  (للاستخدام في Remotion)
  📁 engine/assets/fonts/    (للتوافق الرجعي - اختياري)

التغييرات في v4:
  ✓ المسار الافتراضي تغيّر إلى remotion/public/fonts
  ✓ توليد ملف CSS تلقائياً لـ Remotion
  ✓ التركيز على Cairo (الأساسي)
  ✓ دعم Variable Fonts من Google Fonts
═══════════════════════════════════════════════════════════════
"""

import sys
import time
import argparse
import requests
from pathlib import Path
from typing import Optional, List


# ─── إعدادات عامة ────────────────────────────────────────────────────────
TIMEOUT = 30
MAX_RETRIES = 3
USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
MIN_FONT_SIZE = 10_000

HEADERS = {"User-Agent": USER_AGENT}

# ─── المسارات الافتراضية ────────────────────────────────────────────────
DEFAULT_REMOTION_FONTS = "remotion/public/fonts"
DEFAULT_LEGACY_FONTS = "engine/assets/fonts"


# ─── قائمة الخطوط (مرتبة حسب الأولوية لـ Remotion) ──────────────────
FONTS = {
    # ⭐ Cairo - الأساسي لـ Remotion (مهم جداً!)
    "Cairo-Regular.ttf": [
        "https://github.com/google/fonts/raw/main/ofl/cairo/static/Cairo-Regular.ttf",
    ],
    "Cairo-Bold.ttf": [
        "https://github.com/google/fonts/raw/main/ofl/cairo/static/Cairo-Bold.ttf",
    ],
    "Cairo-Black.ttf": [
        "https://github.com/google/fonts/raw/main/ofl/cairo/static/Cairo-Black.ttf",
    ],
    
    # 🌟 Cairo Variable - يحتوي كل الأوزان في ملف واحد
    "Cairo-VF.ttf": [
        "https://github.com/google/fonts/raw/main/ofl/cairo/Cairo%5Bslnt%2Cwght%5D.ttf",
        "https://github.com/google/fonts/raw/main/ofl/cairo/Cairo[slnt,wght].ttf",
    ],

    # 🎯 Tajawal - بديل ممتاز
    "Tajawal-ExtraBold.ttf": [
        "https://github.com/google/fonts/raw/main/ofl/tajawal/Tajawal-ExtraBold.ttf",
    ],
    "Tajawal-Bold.ttf": [
        "https://github.com/google/fonts/raw/main/ofl/tajawal/Tajawal-Bold.ttf",
    ],
    "Tajawal-Regular.ttf": [
        "https://github.com/google/fonts/raw/main/ofl/tajawal/Tajawal-Regular.ttf",
    ],

    # 💪 Almarai - بديل قوي
    "Almarai-ExtraBold.ttf": [
        "https://github.com/google/fonts/raw/main/ofl/almarai/Almarai-ExtraBold.ttf",
    ],
    "Almarai-Bold.ttf": [
        "https://github.com/google/fonts/raw/main/ofl/almarai/Almarai-Bold.ttf",
    ],
    "Almarai-Regular.ttf": [
        "https://github.com/google/fonts/raw/main/ofl/almarai/Almarai-Regular.ttf",
    ],

    # 📜 Amiri - للنصوص الأدبية
    "Amiri-Bold.ttf": [
        "https://github.com/google/fonts/raw/main/ofl/amiri/Amiri-Bold.ttf",
    ],
    "Amiri-Regular.ttf": [
        "https://github.com/google/fonts/raw/main/ofl/amiri/Amiri-Regular.ttf",
    ],
}

# ─── الخطوط الأساسية (يجب أن تنجح حتماً) ────────────────────────────
ESSENTIAL_FONTS = {
    "Cairo-Bold.ttf",  # ⭐ الأهم لـ Remotion
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


# ─── 🆕 توليد ملف CSS لـ Remotion ──────────────────────────────────
def generate_remotion_css(fonts_dir: Path) -> Optional[Path]:
    """
    توليد ملف CSS تلقائياً لتحميل الخطوط في Remotion.

    Args:
        fonts_dir: مجلد الخطوط

    Returns:
        مسار ملف CSS الناتج
    """
    css_path = fonts_dir.parent / "fonts.css"  # remotion/public/fonts.css

    available_fonts = list(fonts_dir.glob("*.ttf")) + list(fonts_dir.glob("*.otf"))
    if not available_fonts:
        log("  ⚠ لا توجد خطوط لتوليد CSS", Colors.WARN)
        return None

    log("\n📝 توليد ملف CSS لـ Remotion...", Colors.INFO)

    css_content = ["/* 🔤 Auto-generated Arabic Fonts CSS for Remotion */\n\n"]

    # تجميع حسب اسم الخط
    font_groups = {}
    for font_file in available_fonts:
        name = font_file.stem  # Cairo-Bold

        # استخراج اسم العائلة والوزن
        if "-" in name:
            family, weight = name.rsplit("-", 1)
        elif "VF" in name:
            family = name.replace("-VF", "")
            weight = "variable"
        else:
            family = name
            weight = "Regular"

        if family not in font_groups:
            font_groups[family] = []
        font_groups[family].append((weight, font_file.name))

    # توليد @font-face لكل خط
    weight_map = {
        "Thin": 100,
        "ExtraLight": 200,
        "Light": 300,
        "Regular": 400,
        "Medium": 500,
        "SemiBold": 600,
        "Bold": 700,
        "ExtraBold": 800,
        "Black": 900,
        "VF": "100 900",  # Variable
        "variable": "100 900",
    }

    for family, weights in font_groups.items():
        for weight_name, filename in weights:
            css_weight = weight_map.get(weight_name, 400)
            css_content.append(
                f"@font-face {{\n"
                f"  font-family: '{family}';\n"
                f"  src: url('/fonts/{filename}') format('truetype');\n"
                f"  font-weight: {css_weight};\n"
                f"  font-style: normal;\n"
                f"  font-display: swap;\n"
                f"}}\n\n"
            )

    try:
        css_path.write_text("".join(css_content), encoding="utf-8")
        log(f"  ✓ تم توليد: {css_path}", Colors.OK)
        log(f"  ℹ {len(font_groups)} عائلة | {len(available_fonts)} خط", Colors.INFO)
        return css_path
    except Exception as e:
        log(f"  ❌ فشل توليد CSS: {e}", Colors.ERR)
        return None


# ─── 🆕 تحديث load-fonts.ts في Remotion ──────────────────────────
def update_remotion_load_fonts(remotion_dir: Path) -> Optional[Path]:
    """
    تحديث ملف load-fonts.ts في Remotion ليستخدم الخطوط المحلية.

    Args:
        remotion_dir: مجلد Remotion

    Returns:
        مسار ملف load-fonts.ts
    """
    src_dir = remotion_dir / "src"
    if not src_dir.exists():
        return None

    load_fonts_path = src_dir / "load-fonts.ts"

    log("\n📝 تحديث load-fonts.ts...", Colors.INFO)

    content = '''import { continueRender, delayRender } from "remotion";

/**
 * تحميل خط Cairo من Google Fonts
 * (يُستخدم كـ fallback إذا فشل تحميل الخطوط المحلية)
 */
export const loadCairoFont = () => {
  const handle = delayRender("Loading Cairo font...");

  // 1. محاولة تحميل الخطوط المحلية أولاً
  const localStyle = document.createElement("link");
  localStyle.rel = "stylesheet";
  localStyle.href = "/fonts.css";
  document.head.appendChild(localStyle);

  // 2. تحميل من Google Fonts كـ fallback
  const googleStyle = document.createElement("link");
  googleStyle.rel = "stylesheet";
  googleStyle.href = 
    "https://fonts.googleapis.com/css2?family=Cairo:wght@400;700;900&display=swap";

  googleStyle.onload = () => {
    continueRender(handle);
  };

  googleStyle.onerror = () => {
    console.warn("Failed to load Cairo from Google Fonts");
    continueRender(handle);
  };

  document.head.appendChild(googleStyle);

  return handle;
};

/**
 * تحميل كل الخطوط العربية المتاحة
 */
export const loadAllArabicFonts = () => {
  const handle = delayRender("Loading all Arabic fonts...");

  const link = document.createElement("link");
  link.rel = "stylesheet";
  link.href = "/fonts.css";

  link.onload = () => {
    continueRender(handle);
  };

  link.onerror = () => {
    console.warn("Failed to load local Arabic fonts");
    continueRender(handle);
  };

  document.head.appendChild(link);

  return handle;
};
'''

    try:
        load_fonts_path.write_text(content, encoding="utf-8")
        log(f"  ✓ تم تحديث: {load_fonts_path}", Colors.OK)
        return load_fonts_path
    except Exception as e:
        log(f"  ❌ فشل التحديث: {e}", Colors.ERR)
        return None


# ─── الدالة الرئيسية ─────────────────────────────────────────────────────
def download_fonts(
    target: str = DEFAULT_REMOTION_FONTS,
    also_legacy: bool = False,
    generate_css: bool = True,
    update_loader: bool = True,
) -> bool:
    """
    تحميل جميع الخطوط العربية.

    Args:
        target: المجلد المستهدف
        also_legacy: تحميل أيضاً للمجلد القديم (engine/assets/fonts)
        generate_css: توليد ملف CSS لـ Remotion
        update_loader: تحديث ملف load-fonts.ts
    """
    fonts_dir = Path(target)
    fonts_dir.mkdir(parents=True, exist_ok=True)

    log("\n" + "═" * 60, Colors.INFO)
    log("  🔤 ARABIC FONTS DOWNLOADER v4", Colors.BOLD)
    log("  ⭐ Remotion Edition", Colors.OK)
    log("═" * 60, Colors.INFO)
    log(f"📂 المسار الأساسي: {fonts_dir.resolve()}", Colors.INFO)

    if also_legacy:
        log(f"📂 + مسار قديم: {Path(DEFAULT_LEGACY_FONTS).resolve()}", Colors.INFO)
    print()

    total = len(FONTS)
    success_count = 0
    failed_essentials = []

    for font_name, urls in FONTS.items():
        destination = fonts_dir / font_name

        if download_font(font_name, urls, destination):
            success_count += 1

            # نسخ للمجلد القديم إذا طُلب
            if also_legacy:
                legacy_path = Path(DEFAULT_LEGACY_FONTS) / font_name
                legacy_path.parent.mkdir(parents=True, exist_ok=True)
                try:
                    import shutil
                    shutil.copy2(destination, legacy_path)
                    log(f"    ✓ نُسخ للمجلد القديم", Colors.OK)
                except Exception as e:
                    log(f"    ⚠ فشل النسخ للقديم: {e}", Colors.WARN)
        else:
            if font_name in ESSENTIAL_FONTS:
                failed_essentials.append(font_name)
        print()

    # ── توليد CSS لـ Remotion ──────────────────────────────────────
    if generate_css and "remotion" in str(fonts_dir):
        generate_remotion_css(fonts_dir)

    # ── تحديث load-fonts.ts ────────────────────────────────────────
    if update_loader and "remotion" in str(fonts_dir):
        remotion_dir = fonts_dir.parent.parent  # remotion/public/fonts → remotion/
        update_remotion_load_fonts(remotion_dir)

    # ── الملخص ────────────────────────────────────────────────────
    total_files = (
        len(list(fonts_dir.glob("*.ttf")))
        + len(list(fonts_dir.glob("*.otf")))
    )

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
    
    if "remotion" in str(fonts_dir):
        log("\n  💡 الخطوة التالية:", Colors.INFO)
        log("     cd remotion && npm install", Colors.INFO)
        log("     npx remotion studio", Colors.INFO)
    
    log("═" * 60 + "\n", Colors.INFO)
    return True


# ─── نقطة الدخول ─────────────────────────────────────────────────────────
def main():
    parser = argparse.ArgumentParser(
        description="🔤 Arabic Font Downloader for Remotion",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "--target", type=str,
        default=DEFAULT_REMOTION_FONTS,
        help=f"المجلد المستهدف (افتراضي: {DEFAULT_REMOTION_FONTS})",
    )
    parser.add_argument(
        "--legacy", action="store_true",
        help=f"تحميل أيضاً للمجلد القديم ({DEFAULT_LEGACY_FONTS})",
    )
    parser.add_argument(
        "--no-css", action="store_true",
        help="عدم توليد ملف CSS لـ Remotion",
    )
    parser.add_argument(
        "--no-loader", action="store_true",
        help="عدم تحديث ملف load-fonts.ts",
    )
    parser.add_argument(
        "--legacy-only", action="store_true",
        help=f"تحميل للمجلد القديم فقط ({DEFAULT_LEGACY_FONTS})",
    )
    args = parser.parse_args()

    # تحديد المسار
    if args.legacy_only:
        target = DEFAULT_LEGACY_FONTS
        also_legacy = False
        generate_css = False
        update_loader = False
    else:
        target = args.target
        also_legacy = args.legacy
        generate_css = not args.no_css
        update_loader = not args.no_loader

    success = download_fonts(
        target=target,
        also_legacy=also_legacy,
        generate_css=generate_css,
        update_loader=update_loader,
    )

    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
