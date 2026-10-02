"""Modelo Paquete."""

from dataclasses import dataclass
from typing import Self

from src.exceptions import ValidacionError
from src.models.entidad import Entidad
from src.models.zona import Zona


@dataclass
class Paquete(Entidad):
    descripcion: str
    destinatario: str
    direccion: str
    zona: Zona
    peso_kg: float
    volumen_dm3: float
    id: int = 0

    def __post_init__(self) -> None:
        self.descripcion = self.descripcion.strip()
        self.destinatario = self.destinatario.strip()
        self.direccion = self.direccion.strip()
        if not self.descripcion:
            raise ValidacionError("La descripción no puede estar vacía.")
        if not self.destinatario:
            raise ValidacionError("El destinatario no puede estar vacío.")
        if not self.direccion:
            raise ValidacionError("La dirección no puede estar vacía.")
        if self.peso_kg <= 0:
            raise ValidacionError("El peso debe ser mayor a 0 kg.")
        if self.volumen_dm3 <= 0:
            raise ValidacionError("El volumen debe ser mayor a 0 dm³.")

    @classmethod
    def campos(cls) -> list[str]:
        return ["id", "descripcion", "destinatario", "direccion", "zona", "peso_kg", "volumen_dm3"]

    def to_dict(self) -> dict[str, str]:
        return {
            "id": str(self.id),
            "descripcion": self.descripcion,
            "destinatario": self.destinatario,
            "direccion": self.direccion,
            "zona": self.zona.value,
            "peso_kg": f"{self.peso_kg:.2f}",
            "volumen_dm3": f"{self.volumen_dm3:.2f}",
        }

    @classmethod
    def from_dict(cls, fila: dict[str, str]) -> Self:
        return cls(
            id=int(fila["id"]),
            descripcion=fila["descripcion"],
            destinatario=fila["destinatario"],
            direccion=fila["direccion"],
            zona=Zona(fila["zona"]),
            peso_kg=float(fila["peso_kg"]),
            volumen_dm3=float(fila["volumen_dm3"]),
        )
