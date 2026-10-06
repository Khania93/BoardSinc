# core/guardar.py
"""
Funciones simples para guardar y cargar la flota en JSON.
No cambia la estructura de BarcoEstado; guarda la lista de dicts resultante de to_save_dict.
"""

import json
from typing import List, Dict, Any
from pathlib import Path

def guardar_partida(path: str, flota: List[Any]) -> bool:
    try:
        data = [getattr(b, "to_save_dict", lambda: dict(b))() for b in flota]
        p = Path(path)
        p.parent.mkdir(parents=True, exist_ok=True)
        with p.open("w", encoding="utf-8") as f:
            json.dump({"flota": data}, f, ensure_ascii=False, indent=2)
        return True
    except Exception:
        return False

def cargar_partida(path: str) -> List[Dict[str, Any]]:
    try:
        p = Path(path)
        if not p.exists():
            return []
        with p.open("r", encoding="utf-8") as f:
            obj = json.load(f)
        return obj.get("flota", [])
    except Exception:
        return []
