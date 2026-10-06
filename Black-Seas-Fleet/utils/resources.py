# utils/resources.py
"""
Utilities to resolve resource paths both in development and when packaged with PyInstaller.
"""

from __future__ import annotations
import sys
import os
from typing import Optional

def resource_path(relative_path: str) -> str:
    """
    Devuelve la ruta absoluta a un recurso, compatible con PyInstaller.
    - relative_path: ruta relativa dentro del proyecto (ej: "data/mi_datos.xlsx", "assets/bg.png")
    """
    if getattr(sys, "frozen", False):
        # PyInstaller crea un atributo sys._MEIPASS con la ruta temporal
        base_path = getattr(sys, "_MEIPASS", os.path.abspath("."))
    else:
        base_path = os.path.abspath(".")
    return os.path.join(base_path, relative_path)

def ensure_exists(path: str) -> None:
    """
    Lanza FileNotFoundError si el recurso no existe.
    """
    if not os.path.exists(path):
        raise FileNotFoundError(f"Archivo no encontrado: {path}")
