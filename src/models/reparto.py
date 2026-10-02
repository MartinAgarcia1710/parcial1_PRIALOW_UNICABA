"""Modelo Reparto: vincula UN paquete con UN repartidor.

Decisión de diseño: un reparto por paquete (relación 1 a 1 paquete-reparto,
N a 1 reparto-repartidor). Así el CSV queda normalizado, sin listas de IDs
dentro de una celda, y cada envío tiene su propio estado, costo y clima.
"""

from dataclasses import dataclass
from datetime import datetime
from typing import Self

from src.models.entidad import Entidad
from src.models.zona import EstadoReparto, Zona

FORMATO_FECHA = "%Y-%m-%d %H:%M"


@dataclass
class Reparto(Entidad):
    paquete_id: int
    repartidor_id: int
    zona: Zona
    fecha: datetime
    costo_base: float
    recargo_pct: float
    clima: str
    estado: EstadoReparto = EstadoReparto.PENDIENTE
    id: int = 0

    @property
    def costo_total(self) -> float:
        return round(self.costo_base * (1 + self.recargo_pct / 100), 2)

    @classmethod
    def campos(cls) -> list[str]:
        return [
            "id", "paquete_id", "repartidor_id", "zona", "fecha",
            "costo_base", "recargo_pct", "costo_total", "clima", "estado",
        ]

    def to_dict(self) -> dict[str, str]:
        return {
            "id": str(self.id),
            "paquete_id": str(self.paquete_id),
            "repartidor_id": str(self.repartidor_id),
            "zona": self.zona.value,
            "fecha": self.fecha.strftime(FORMATO_FECHA),
            "costo_base": f"{self.costo_base:.2f}",
            "recargo_pct": f"{self.recargo_pct:.1f}",
            "costo_total": f"{self.costo_total:.2f}",  # se guarda para facilitar el análisis en pandas
            "clima": self.clima,
            "estado": self.estado.value,
        }

    @classmethod
    def from_dict(cls, fila: dict[str, str]) -> Self:
        return cls(
            id=int(fila["id"]),
            paquete_id=int(fila["paquete_id"]),
            repartidor_id=int(fila["repartidor_id"]),
            zona=Zona(fila["zona"]),
            fecha=datetime.strptime(fila["fecha"], FORMATO_FECHA),
            costo_base=float(fila["costo_base"]),
            recargo_pct=float(fila["recargo_pct"]),
            clima=fila["clima"],
            estado=EstadoReparto(fila["estado"]),
        )
