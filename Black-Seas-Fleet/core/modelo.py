# core/modelo.py
"""
Modelo Barco: almacena únicamente estado dinámico y referencia al registro del Excel.
No duplica datos permanentes.
"""

from dataclasses import dataclass, field, asdict
from typing import Optional, List, Dict, Any

@dataclass
class BarcoEstado:
    """
    Representa la instancia de un barco en la partida.
    - referencia_id: valor que identifica el registro en la hoja BARCOS (puede ser nombre o id)
    - id_interno: id generado en la sesión para distinguir instancias
    - id_custom: identificador personalizado por el usuario
    - estado: 'ACTIVO'|'CAPTURADO'|'RENDIDO' etc.
    - vida_actual: entero
    - tripulacion_actual: texto o número
    - mejoras_instaladas: lista de nombres (strings) de mejoras; las definiciones se leen desde Excel
    - oficial_ref: identificador del oficial (nombre o id) — se mantiene como referencia
    - danos_activos: lista de dicts con {'nombre': <nombre daño>, 'estado': <estado>}
    - disparos: contador o estructura de disparos por zona/tipo (opcional)
    - observaciones: texto libre
    """
    referencia_id: Any
    id_interno: int
    id_custom: str = ""
    estado: str = "ACTIVO"
    vida_actual: int = 0
    tripulacion_actual: Optional[str] = None
    mejoras_instaladas: List[str] = field(default_factory=list)
    oficial_ref: Optional[Any] = None
    danos_activos: List[Dict[str, Any]] = field(default_factory=list)
    disparos: Dict[str, Any] = field(default_factory=dict)
    observaciones: str = ""

    def to_save_dict(self) -> Dict[str, Any]:
        # Estructura mínima para guardar partida
        return {
            "referencia_id": self.referencia_id,
            "id_interno": self.id_interno,
            "id_custom": self.id_custom,
            "estado": self.estado,
            "vida_actual": self.vida_actual,
            "tripulacion_actual": self.tripulacion_actual,
            "mejoras_instaladas": list(self.mejoras_instaladas),
            "oficial_ref": self.oficial_ref,
            "danos_activos": list(self.danos_activos),
            "disparos": dict(self.disparos),
            "observaciones": self.observaciones,
        }

    @classmethod
    def from_save_dict(cls, data: Dict[str, Any]) -> "BarcoEstado":
        return cls(
            referencia_id=data.get("referencia_id"),
            id_interno=int(data.get("id_interno", 0)),
            id_custom=data.get("id_custom", ""),
            estado=data.get("estado", "ACTIVO"),
            vida_actual=int(data.get("vida_actual", 0)),
            tripulacion_actual=data.get("tripulacion_actual"),
            mejoras_instaladas=list(data.get("mejoras_instaladas", []) or []),
            oficial_ref=data.get("oficial_ref"),
            danos_activos=list(data.get("danos_activos", []) or []),
            disparos=dict(data.get("disparos", {}) or {}),
            observaciones=data.get("observaciones", "") or "",
        )
