"""
Font Downloader - downloads Arabic Google Fonts
"""

import os
import urllib.request
from pathlib import Path

FONTS = {
    "Cairo-Black.ttf":
        "https://github.com/google/fonts/raw/main/ofl/cairo/static/Cairo-Black.ttf",
    "Tajawal-ExtraBold.ttf":
        "https://github.com/google/fonts/raw/main/ofl/tajawal/Tajawal-ExtraBold.ttf",
    "Changa-ExtraBold.ttf":
        "https://github.com/google/fonts/raw/main/ofl/changa/static/Changa-ExtraBold.ttf",
}


def download_fonts(target: str = "engine/assets/fonts") -> None:
    p = Path(target)
    p.mkdir(parents=True, exist_ok=True)
    for name, url in FONTS.items():
        dest = p / name
        if dest.exists():
            print(f"  ✓ {name}")
            continue
        print(f"  ↓ {name}...")
        try:
            urllib.request.urlretrieve(url, str(dest))
            print(f"  ✓ saved → {dest}")
        except Exception as e:
            print(f"  ✗ failed: {e}")
            print(f"    Download manually: {url}")


if __name__ == "__main__":
    download_fonts()
