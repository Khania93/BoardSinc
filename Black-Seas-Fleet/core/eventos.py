# core/eventos.py
from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Dict, Any

@dataclass
class Evento:
    timestamp: str
    tipo: str
    detalle: str
    meta: Dict[str, Any] = field(default_factory=dict)

class RegistroEventos:
    def __init__(self):
        self._eventos: List[Evento] = []

    def registrar(self, tipo: str, detalle: str, meta: Dict[str, Any] = None):
        ts = datetime.now().isoformat()
        ev = Evento(timestamp=ts, tipo=tipo, detalle=detalle, meta=meta or {})
        self._eventos.append(ev)

    def obtener_todos(self) -> List[Evento]:
        return list(self._eventos)

    def limpiar(self):
        self._eventos.clear()

    def exportar_a_json_estructura(self) -> List[Dict[str, Any]]:
        return [ {"timestamp": e.timestamp, "tipo": e.tipo, "detalle": e.detalle, "meta": e.meta} for e in self._eventos ]
