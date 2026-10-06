# core/calculos.py
"""
Funciones de cálculo de costes y utilidades para Black Seas.
Mantener simples y compatibles con la UI.
"""

from typing import List, Dict, Any
import math

def _round_up_to_10(n: float) -> int:
    try:
        return int(math.ceil(float(n) / 10.0) * 10)
    except Exception:
        return int(n)

def calcular_coste_barco(base_points: int, trip_mod: float, mejoras_defs: List[Dict[str, Any]], oficial_def: Dict[str, Any] | None, capturado: bool = False) -> int:
    """
    Calcula el coste final de un barco:
    - Si capturado -> 0
    - total = round_up( base_points * trip_mod + sum(mejoras) + puntos_oficial )
    """
    try:
        if capturado:
            return 0
        base_after = float(base_points) * float(trip_mod)
        mejoras_total = 0
        for m in mejoras_defs or []:
            try:
                mejoras_total += int(float(m.get("COSTE") or m.get("PUNTOS") or m.get("Puntos") or 0))
            except Exception:
                continue
        puntos_oficial = 0
        if oficial_def and isinstance(oficial_def, dict):
            try:
                puntos_oficial = int(float(oficial_def.get("Puntos") or oficial_def.get("PUNTOS") or 0))
            except Exception:
                puntos_oficial = 0
        total = base_after + mejoras_total + puntos_oficial
        return _round_up_to_10(total)
    except Exception:
        return 0
