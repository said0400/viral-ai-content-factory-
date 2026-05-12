# download_fonts.py

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

def download_fonts(target="engine/assets/fonts"):
    p = Path(target)
    p.mkdir(parents=True, exist_ok=True)

    for name, url in FONTS.items():
        dest = p / name
        if dest.exists() and dest.stat().st_size > 1000:
            print(f"✓ {name} موجود بالفعل")
            continue

        print(f"↓ تحميل {name}...")
        success = False

        try:
            urllib.request.urlretrieve(url, str(dest))
            if dest.exists() and dest.stat().st_size > 1000:
                print(f"✓ تم تحميل {name}")
                success = True
            else:
                print(f"✗ الملف غير صالح")
        except Exception as e:
            print(f"✗ فشل: {e}")

        if not success and name in FALLBACK_FONTS:
            try:
                print(f"↓ محاولة رابط بديل لـ {name}...")
                urllib.request.urlretrieve(FALLBACK_FONTS[name], str(dest))
                if dest.exists() and dest.stat().st_size > 1000:
                    print(f"✓ تم تحميل {name} من الرابط البديل")
            except Exception as e:
                print(f"✗ فشل البديل: {e}")

    total = len(list(p.glob("*.ttf")))
    print(f"\n✅ اكتمل التحميل ({total} خطوط)")

if __name__ == "__main__":
    download_fonts()
