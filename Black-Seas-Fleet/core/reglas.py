"""
Reglas y constantes del juego que pueden necesitarse en varios módulos.
"""

from typing import Dict

# Valores por defecto para modificadores de tripulación
TRIP_MOD_DEFAULT = {
    "INEXPERTO": 0.8,
    "REGULAR": 1.0,
    "VETERANO": 1.2,
}

# Máximo de mejoras por tamaño (coincide con core.utils pero se deja aquí para reglas específicas)
MAX_MEJORAS_POR_TAM = {"T": 0, "S": 1, "M": 2, "L": 3, "XL": 4}

# Reglas de incompatibilidades por nombre de mejora (extensible)
MEJORAS_INCOMPATIBLES = {
    "Sobreartillado": {"Carronadas Extra"},
    "Carronadas Extra": {"Sobreartillado"},
}

# Reglas de validación de flota
DEFAULT_PUNTOS_OBJETIVO = 2000

def validar_num_unidades_por_tipo(df_barcos, nombre: str, faccion: str = None) -> int:
    """
    Si se necesita validar el número máximo de unidades por tipo desde un DataFrame,
    esta función puede ser llamada por la UI. Devuelve el máximo (o 9999 si no se encuentra).
    """
    if df_barcos is None:
        return 9999
    cols = df_barcos.columns
    col_n = next((c for c in cols if "nom" in c.lower()), None)
    col_unidades = next((c for c in cols if "unidad" in c.lower() and "max" in c.lower()), None)
    if col_n is None:
        return 9999
    mask = df_barcos[col_n].astype(str).str.strip() == str(nombre).strip()
    if faccion:
        col_f = next((c for c in cols if "facc" in c.lower() or "facción" in c.lower()), None)
        if col_f:
            mask = mask & (df_barcos[col_f].astype(str).str.strip() == str(faccion).strip())
    filas = df_barcos[mask]
    if filas.empty:
        return 9999
    fila = filas.iloc[0]
    if col_unidades and col_unidades in fila.index:
        try:
            return int(fila[col_unidades])
        except Exception:
            try:
                return int(float(fila[col_unidades]))
            except Exception:
                return 9999
    return 9999
