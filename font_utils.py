"""
ROIN WORLD FZE — DejaVuSans Font Utility
=========================================
Provides Cyrillic-capable font registration for fpdf2.
All PDF generators that need Russian text import from here.
"""

import os
import urllib.request

BASE_DIR    = os.path.dirname(os.path.abspath(__file__))
FONT_PATH   = os.path.join(BASE_DIR, "DejaVuSans.ttf")
FONT_BOLD   = os.path.join(BASE_DIR, "DejaVuSans-Bold.ttf")
FONT_ITALIC = os.path.join(BASE_DIR, "DejaVuSans-Oblique.ttf")

_FONT_URLS = {
    FONT_PATH:   "https://cdn.jsdelivr.net/npm/dejavu-fonts-ttf@2.37.3/ttf/DejaVuSans.ttf",
    FONT_BOLD:   "https://cdn.jsdelivr.net/npm/dejavu-fonts-ttf@2.37.3/ttf/DejaVuSans-Bold.ttf",
    FONT_ITALIC: "https://cdn.jsdelivr.net/npm/dejavu-fonts-ttf@2.37.3/ttf/DejaVuSans-Oblique.ttf",
}


def ensure_fonts() -> bool:
    """Download DejaVu fonts if not present. Returns True if all fonts available."""
    for path, url in _FONT_URLS.items():
        if not os.path.exists(path):
            try:
                urllib.request.urlretrieve(url, path)
            except Exception as e:
                print(f"[font_utils] Could not download {os.path.basename(path)}: {e}")
                return False
    return True


def add_dejavu(pdf) -> bool:
    """
    Register DejaVu font family with an fpdf2 PDF instance.
    Supports Unicode including Cyrillic, Arabic script, etc.
    Returns True on success, False if fonts unavailable.
    """
    if not all(os.path.exists(p) for p in [FONT_PATH, FONT_BOLD, FONT_ITALIC]):
        if not ensure_fonts():
            return False
    try:
        pdf.add_font("DejaVu",  "",  FONT_PATH)
        pdf.add_font("DejaVu",  "B", FONT_BOLD)
        pdf.add_font("DejaVu",  "I", FONT_ITALIC)
        return True
    except Exception as e:
        print(f"[font_utils] add_font failed: {e}")
        return False


def fonts_available() -> bool:
    return all(os.path.exists(p) for p in [FONT_PATH, FONT_BOLD, FONT_ITALIC])
