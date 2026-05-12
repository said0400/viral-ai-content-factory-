# download_fonts.py
# Arabic Font Downloader
# Uses verified working URLs

import urllib.request
from pathlib import Path


FONTS = {

    "Cairo.ttf":
        "https://raw.githubusercontent.com/google/fonts/main/ofl/cairo/Cairo%5Bslnt,wght%5D.ttf",

    "Tajawal-ExtraBold.ttf":
        "https://raw.githubusercontent.com/google/fonts/main/ofl/tajawal/Tajawal-ExtraBold.ttf",

    "Changa.ttf":
        "https://raw.githubusercontent.com/google/fonts/main/ofl/changa/Changa%5Bwght%5D.ttf",

    "NotoNaskhArabic.ttf":
        "https://raw.githubusercontent.com/google/fonts/main/ofl/notonaskharabic/NotoNaskhArabic%5Bwght%5D.ttf",
}


FALLBACK_FONTS = {

    "NotoNaskhArabic.ttf":
        "https://fonts.gstatic.com/s/notonaskharabic/v33/RrQPboN_4yJ0JmiMUW7sIGgvM8CXTHdUt3o9.ttf",

    "Tajawal-ExtraBold.ttf":
        "https://fonts.gstatic.com/s/tajawal/v6/Iura6YBj_oCad4k1nzSBC45I.ttf",
}


def is_valid_font(path: Path) -> bool:
    """
    التحقق من أن الملف خط حقيقي
    """

    try:

        if not path.exists():
            return False

        if path.stat().st_size < 10000:
            return False

        with open(path, "rb") as f:
            header = f.read(4)

        valid_headers = [
            b"\x00\x01\x00\x00",
            b"OTTO",
            b"true",
        ]

        return header in valid_headers

    except Exception:
        return False


def download_file(url: str, destination: Path) -> bool:

    try:

        urllib.request.urlretrieve(
            url,
            str(destination)
        )

        return is_valid_font(destination)

    except Exception as e:

        print(f"   ❌ {e}")

        return False


def download_fonts(
    target="engine/assets/fonts"
):

    fonts_dir = Path(target)

    fonts_dir.mkdir(
        parents=True,
        exist_ok=True
    )

    print("\n🔤 Downloading Arabic fonts...\n")

    success_count = 0

    for font_name, primary_url in FONTS.items():

        destination = fonts_dir / font_name

        if is_valid_font(destination):

            print(f"✓ {font_name} موجود بالفعل")

            success_count += 1

            continue

        print(f"↓ تحميل {font_name}...")

        success = False

        # الرابط الأساسي
        if download_file(
            primary_url,
            destination
        ):

            print(f"✓ تم تحميل {font_name}")

            success = True

        else:

            print("⚠️ فشل الرابط الأساسي")

        # الرابط الاحتياطي
        if not success and font_name in FALLBACK_FONTS:

            print(f"↓ محاولة الرابط البديل لـ {font_name}...")

            fallback_url = FALLBACK_FONTS[font_name]

            if download_file(
                fallback_url,
                destination
            ):

                print(f"✓ تم تحميل {font_name} من الرابط البديل")

                success = True

            else:

                print(f"✗ فشل تحميل {font_name}")

        if success:
            success_count += 1

    print("\n━━━━━━━━━━━━━━━━━━")

    total_fonts = len(
        list(fonts_dir.glob("*.ttf"))
    )

    print(f"✅ اكتمل التحميل")

    print(f"📦 الخطوط المحملة: {success_count}")

    print(f"📁 إجمالي ملفات الخطوط: {total_fonts}")

    print(f"📂 المسار: {fonts_dir.resolve()}")

    print("━━━━━━━━━━━━━━━━━━\n")


if __name__ == "__main__":

    download_fonts()
