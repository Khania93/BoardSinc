# ui/widgets.py
"""
Widgets visuales reutilizables para Black Seas

Exporta:
- NavalStyle
- ImageCache
- StyledButton, StyledLabel, StyledPanel
- crop_and_scale_bg_for_size
- BG_FICHA path and PIL_AVAILABLE flag

Diseñado para no provocar importaciones circulares con el resto de la UI.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Optional, Dict

import tkinter as tk

logger = logging.getLogger(__name__)
logger.addHandler(logging.NullHandler())

# PIL optional
try:
    from PIL import Image, ImageTk
    PIL_AVAILABLE = True
except Exception:
    PIL_AVAILABLE = False
    Image = None
    ImageTk = None

# Project asset paths (relative to package root)
PROJECT_ROOT = Path(__file__).resolve().parent.parent
ASSETS_DIR = PROJECT_ROOT / "assets"
FONDOS_DIR = ASSETS_DIR / "fondos"
BG_FICHA = FONDOS_DIR / "bg_ficha.png"

# -------------------------
# Estilo reutilizable
# -------------------------
class NavalStyle:
    NAVAL_BG_FALLBACK = "#efe6d8"
    TEXT = "#efe9df"
    ACCENT = "#c9a66b"
    BTN_BG = "#0b2a2a"
    BTN_ACTIVE = "#123737"

    TITLE = ("Garamond", 14, "bold")
    LABEL = ("Garamond", 10, "bold")
    NORMAL = ("Garamond", 11)

    PAD_SMALL = 6
    PAD_MED = 12
    PAD_LARGE = 18

    @staticmethod
    def style_button(btn: tk.Button):
        try:
            btn.configure(bg=NavalStyle.BTN_BG, fg=NavalStyle.TEXT, bd=0, relief="flat",
                          activebackground=NavalStyle.BTN_ACTIVE, font=NavalStyle.LABEL, highlightthickness=0)
        except Exception:
            pass

    @staticmethod
    def style_label(lbl: tk.Label, title: bool = False):
        try:
            fg = NavalStyle.ACCENT if title else NavalStyle.TEXT
            font = NavalStyle.LABEL if title else NavalStyle.NORMAL
            lbl.configure(fg=fg, font=font, bd=0, highlightthickness=0)
        except Exception:
            pass

# -------------------------
# Image utilities (cache)
# -------------------------
class ImageCache:
    def __init__(self):
        self._cache: Dict[str, "ImageTk.PhotoImage"] = {}
        self._pil_cache: Dict[str, "Image.Image"] = {}

    def load_pil(self, path: Path):
        if not PIL_AVAILABLE:
            return None
        key = str(path)
        if key in self._pil_cache:
            return self._pil_cache[key]
        try:
            if not Path(path).exists():
                return None
            img = Image.open(str(path)).convert("RGBA")
            self._pil_cache[key] = img
            return img
        except Exception:
            logger.exception("Error cargando PIL image %s", path)
            return None

    def store_photo(self, key: str, photo: "ImageTk.PhotoImage"):
        self._cache[key] = photo

    def get_photo(self, key: str) -> Optional["ImageTk.PhotoImage"]:
        return self._cache.get(key)

    def clear(self):
        self._cache.clear()
        self._pil_cache.clear()

# -------------------------
# Background cropping helper
# -------------------------
def crop_and_scale_bg_for_size(pil_bg, w: int, h: int) -> Optional["ImageTk.PhotoImage"]:
    if not PIL_AVAILABLE or pil_bg is None:
        return None
    try:
        pw, ph = pil_bg.size
        scale = max(w / pw, h / ph)
        target = (max(1, int(pw * scale)), max(1, int(ph * scale)))
        img = pil_bg.resize(target, Image.LANCZOS)
        tw, th = img.size
        left = max(0, (tw - w) // 2)
        top = max(0, (th - h) // 2)
        cropped = img.crop((left, top, left + w, top + h))
        return ImageTk.PhotoImage(cropped)
    except Exception:
        logger.exception("Error crop_and_scale_bg_for_size")
        return None

# -------------------------
# Styled widgets
# -------------------------
class StyledButton(tk.Button):
    def __init__(self, parent, text: str, command=None, **kwargs):
        super().__init__(parent, text=text, command=command, **kwargs)
        NavalStyle.style_button(self)
        try:
            self.configure(highlightthickness=0)
        except Exception:
            pass

class StyledLabel(tk.Label):
    def __init__(self, parent, text: str = "", title: bool = False, textvariable=None, **kwargs):
        super().__init__(parent, text=text, textvariable=textvariable, **kwargs)
        NavalStyle.style_label(self, title=title)

class StyledPanel(tk.Frame):
    """
    Panel decorativo que puede recibir un recorte del fondo como Label interno.
    Evita pasar parámetros desconocidos a la superclase (corrige errores -pil_bg).
    Mantiene su propio bg_label y usa ImageCache para cachear PhotoImages.
    """
    def __init__(self, parent, image_cache: ImageCache, pil_bg=None, key: str = "panel", **kwargs):
        # Remove visual-only kwargs that must not be forwarded to tk.Frame
        kwargs = dict(kwargs)  # copy
        kwargs.pop("pil_bg", None)
        kwargs.pop("padding", None)
        kwargs.pop("style", None)
        super().__init__(parent, bd=0, **kwargs)
        self._image_cache = image_cache
        self._pil_bg = pil_bg
        self._bg_key_base = key
        self._bg_label: Optional[tk.Label] = None
        try:
            self.configure(bg=NavalStyle.NAVAL_BG_FALLBACK)
        except Exception:
            pass

    def apply_background(self):
        if not PIL_AVAILABLE or self._pil_bg is None:
            try:
                self.configure(bg=NavalStyle.NAVAL_BG_FALLBACK)
            except Exception:
                pass
            return
        fw = max(1, self.winfo_width())
        fh = max(1, self.winfo_height())
        if fw <= 1 or fh <= 1:
            return
        cache_key = f"{self._bg_key_base}:{fw}x{fh}"
        photo = self._image_cache.get_photo(cache_key)
        if photo is None:
            photo = crop_and_scale_bg_for_size(self._pil_bg, fw, fh)
            if photo is None:
                return
            self._image_cache.store_photo(cache_key, photo)
        if self._bg_label and isinstance(self._bg_label, tk.Label):
            try:
                self._bg_label.configure(image=photo)
                self._bg_label.image_ref = photo
            except Exception:
                pass
        else:
            try:
                self._bg_label = tk.Label(self, image=photo, bd=0)
                self._bg_label.image_ref = photo
                self._bg_label.place(x=0, y=0, relwidth=1, relheight=1)
                self._bg_label.lower()
            except Exception:
                pass
        # ensure children are above bg_label
        try:
            for child in self.winfo_children():
                if child is self._bg_label:
                    continue
                child.lift()
        except Exception:
            pass

# Default cache instance
_default_image_cache = ImageCache()

def get_default_cache() -> ImageCache:
    return _default_image_cache

def load_bg_pil():
    return _default_image_cache.load_pil(BG_FICHA)

# Public API
__all__ = [
    "NavalStyle", "ImageCache", "StyledButton", "StyledLabel", "StyledPanel",
    "crop_and_scale_bg_for_size", "BG_FICHA", "PIL_AVAILABLE",
    "get_default_cache", "load_bg_pil", "Image", "ImageTk"
]
