# core/utils.py
"""
Utilidades y constantes del proyecto (castellano).
"""
import tkinter as tk
import unicodedata
from pathlib import Path
from typing import Dict, Any, List

EXCEL_FILE = Path("data") / "Black_Seas.xlsx"

SHEET_BARCOS = ["BARCOS", "Barcos", "barcos"]
SHEET_MEJORAS = ["MEJORAS", "Mejoras", "mejoras"]
SHEET_OFICIALES = ["OFICIALES DE RENOMBRE", "OFICIALES", "Oficiales", "oficiales"]

PUNTOS_COL = "PUNTOS DE BARCO"
COL_FACCION = "Facción"
COL_TIPO = "TIPO"
COL_NOMBRE = "NOMBRE"
COL_TAMANO = "TAMAÑO"
COL_TRIP_STD = "TIPO DE TRIPULACION ESTANDARD"

COL_MEJORA_NOMBRE = "Nombre"
COL_MEJORA_COSTE = "Puntos"
COL_MEJORA_DESC = "Descripción"

MAX_MEJORAS_POR_TAM = {"T": 0, "S": 1, "M": 2, "L": 3, "XL": 4}

TRIP_MOD = {"INEXPERTO": 0.8, "REGULAR": 1.0, "VETERANO": 1.2}

NAVAL_BG = "#0b2f3a"
NAVAL_PANEL = "#123f48"
NAVAL_ACCENT = "#c9a66b"
NAVAL_TEXT = "#f4f1ea"
FONT_TITLE = ("Garamond", 13, "bold")
FONT_NORMAL = ("Garamond", 11)


def center_window(win: tk.Toplevel | tk.Tk, w: int, h: int):
    win.update_idletasks()
    sw = win.winfo_screenwidth()
    sh = win.winfo_screenheight()
    x = int((sw - w) / 2)
    y = int((sh - h) / 2)
    win.geometry(f"{w}x{h}+{x}+{y}")


def _norm(s: str) -> str:
    if s is None:
        return ""
    s = str(s).strip()
    s = unicodedata.normalize("NFKD", s)
    s = "".join(ch for ch in s if not unicodedata.combining(ch))
    return s


def is_renombre(nombre: str, tipo: str) -> bool:
    """
    Un barco es de renombre cuando NOMBRE es distinto de TIPO (normalizado).
    """
    n = _norm(str(nombre or "")).strip().upper()
    t = _norm(str(tipo or "")).strip().upper()
    if not n or not t:
        return False
    return n != t


def _normalize_mejora_name(name: str) -> str:
    if not name:
        return ""
    return _norm(str(name)).strip().lower()


def apply_mejoras_bonificaciones(barco: Dict[str, Any]) -> None:
    """
    Aplica bonificaciones de mejoras al dict 'barco' in-place.
    Implementa: 'robusto', 'carronadas extra', 'sobreartillado'.
    """
    try:
        mejoras = barco.get("MEJORAS_LIST", []) or []
        nombres: List[str] = []
        for m in mejoras:
            if isinstance(m, dict):
                nombres.append(m.get("Nombre", "") or m.get("nombre", "") or "")
            else:
                nombres.append(str(m or ""))
        nombres = [_normalize_mejora_name(n) for n in nombres if n]

        barco.setdefault("VIDA_TOTAL", int(barco.get("VIDA_TOTAL", 0) or 0))
        barco.setdefault("VIDA_ACTUAL", int(barco.get("VIDA_ACTUAL", barco.get("VIDA_TOTAL", 0)) or 0))
        barco.setdefault("CARRONADAS_BABOR", int(barco.get("CARRONADAS_BABOR", 0) or 0))
        barco.setdefault("CARRONADAS_ESTRIBOR", int(barco.get("CARRONADAS_ESTRIBOR", 0) or 0))
        barco.setdefault("CANON_PESADO_BABOR", int(barco.get("CANON_PESADO_BABOR", 0) or 0))
        barco.setdefault("CANON_LIGERO_BABOR", int(barco.get("CANON_LIGERO_BABOR", 0) or 0))
        barco.setdefault("CANON_PESADO_ESTRIBOR", int(barco.get("CANON_PESADO_ESTRIBOR", 0) or 0))
        barco.setdefault("CANON_LIGERO_ESTRIBOR", int(barco.get("CANON_LIGERO_ESTRIBOR", 0) or 0))

        for nombre in nombres:
            if not nombre:
                continue
            if nombre == "robusto":
                barco["VIDA_TOTAL"] += 20
                barco["VIDA_ACTUAL"] += 20
                continue
            if nombre in ("carronadas extra", "carronadasextra", "carronadas_extra"):
                barco["CARRONADAS_BABOR"] += 1
                barco["CARRONADAS_ESTRIBOR"] += 1
                continue
            if nombre in ("sobreartillado", "sobre-artillado", "sobre artillado"):
                barco["CANON_PESADO_BABOR"] += 1
                barco["CANON_LIGERO_BABOR"] += 1
                barco["CANON_PESADO_ESTRIBOR"] += 1
                barco["CANON_LIGERO_ESTRIBOR"] += 1
                continue
            nn = nombre.replace("á", "a").replace("é", "e").replace("í", "i").replace("ó", "o").replace("ú", "u")
            if nn == "robusto":
                barco["VIDA_TOTAL"] += 20
                barco["VIDA_ACTUAL"] += 20
            elif nn == "carronadas extra":
                barco["CARRONADAS_BABOR"] += 1
                barco["CARRONADAS_ESTRIBOR"] += 1
            elif nn == "sobreartillado":
                barco["CANON_PESADO_BABOR"] += 1
                barco["CANON_LIGERO_BABOR"] += 1
                barco["CANON_PESADO_ESTRIBOR"] += 1
                barco["CANON_LIGERO_ESTRIBOR"] += 1
    except Exception:
        try:
            import logging
            logging.getLogger(__name__).exception("Error aplicando bonificaciones de mejoras")
        except Exception:
            pass
