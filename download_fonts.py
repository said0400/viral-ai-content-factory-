# download_fonts.py

"""
Font Downloader - downloads Arabic Google Fonts
"""

import os
import urllib.request
from pathlib import Path

FONTS = {
    "Cairo-Black.ttf":
        "https://github.com/googlefonts/cairo/raw/main/fonts/ttf/Cairo-Black.ttf",
    "Tajawal-ExtraBold.ttf":
        "https://github.com/google/fonts/raw/main/ofl/tajawal/Tajawal-ExtraBold.ttf",
    "Changa-ExtraBold.ttf":
        "https://github.com/googlefonts/changa/raw/main/fonts/ttf/Changa-ExtraBold.ttf",
    "NotoNaskhArabic-Bold.ttf":
        "https://github.com/google/fonts/raw/main/ofl/notonaskharabic/NotoNaskhArabic-Bold.ttf",
}

FALLBACK_FONTS = {
    "Cairo-Black.ttf":
        "https://fonts.gstatic.com/s/cairo/v28/SLXgc1nY6HkvalIkTpu0xg.ttf",
    "NotoNaskhArabic-Bold.ttf":
        "https://fonts.gstatic.com/s/notonaskharabic/v33/RrQPboN_4yJ0JmiMUW7sIGgvM8CXTHdUt3o9.ttf",
}


def download_fonts(target: str = "engine/assets/fonts") -> None:
    p = Path(target)
    p.mkdir(parents=True, exist_ok=True)

    for name, url in FONTS.items():
        dest = p / name
        if dest.exists() and dest.stat().st_size > 1000:
            print(f"  ✓ {name} (cached)")
            continue

        print(f"  ↓ {name}...")
        success = False

        try:
            urllib.request.urlretrieve(url, str(dest))
            if dest.stat().st_size > 1000:
                print(f"  ✓ saved → {dest}")
                success = True
        except Exception as e:
            print(f"  ✗ primary failed: {e}")

        if not success and name in FALLBACK_FONTS:
            try:
                print(f"  ↓ trying fallback for {name}...")
                urllib.request.urlretrieve(FALLBACK_FONTS[name], str(dest))
                if dest.stat().st_size > 1000:
                    print(f"  ✓ fallback saved → {dest}")
                    success = True
            except Exception as e:
                print(f"  ✗ fallback failed: {e}")

        if not success:
            print(f"  ✗ {name} FAILED")

    fonts = list(p.glob("*.ttf"))
    arabic_ok = any(
        f.name in ("Cairo-Black.ttf", "NotoNaskhArabic-Bold.ttf", "Tajawal-ExtraBold.ttf")
        for f in fonts
    )
    if arabic_ok:
        print(f"\n  ✅ Arabic fonts ready ({len(fonts)} fonts total)")
    else:
        print(f"\n  ⚠️ WARNING: No Arabic font found!")


if __name__ == "__main__":
    download_fonts()
