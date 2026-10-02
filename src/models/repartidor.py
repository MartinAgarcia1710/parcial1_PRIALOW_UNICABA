"""Modelo Repartidor."""

from dataclasses import dataclass
from typing import Self

from src.exceptions import ValidacionError
from src.models.entidad import Entidad
from src.models.paquete import Paquete
from src.models.zona import TipoVehiculo, Zona


@dataclass
class Repartidor(Entidad):
    nombre: str
    telefono: str
    zona: Zona
    vehiculo: TipoVehiculo
    id: int = 0

    def __post_init__(self) -> None:
        self.nombre = self.nombre.strip()
        self.telefono = self.telefono.strip()
        if not self.nombre:
            raise ValidacionError("El nombre no puede estar vacío.")
        if not self.telefono:
            raise ValidacionError("El teléfono no puede estar vacío.")

    @property
    def capacidad_peso_kg(self) -> float:
        return self.vehiculo.capacidad_peso_kg

    @property
    def capacidad_volumen_dm3(self) -> float:
        return self.vehiculo.capacidad_volumen_dm3

    def puede_cargar(self, paquete: Paquete, peso_actual: float, volumen_actual: float) -> bool:
        """Indica si el paquete entra sumándolo a la carga que ya tiene asignada.

        `peso_actual` y `volumen_actual` son la carga de los repartos activos
        (pendientes o en camino); la calcula el servicio de asignación.
        """
        return (
            peso_actual + paquete.peso_kg <= self.capacidad_peso_kg
            and volumen_actual + paquete.volumen_dm3 <= self.capacidad_volumen_dm3
        )

    @classmethod
    def campos(cls) -> list[str]:
        return ["id", "nombre", "telefono", "zona", "vehiculo"]

    def to_dict(self) -> dict[str, str]:
        return {
            "id": str(self.id),
            "nombre": self.nombre,
            "telefono": self.telefono,
            "zona": self.zona.value,
            "vehiculo": self.vehiculo.value,
        }

    @classmethod
    def from_dict(cls, fila: dict[str, str]) -> Self:
        return cls(
            id=int(fila["id"]),
            nombre=fila["nombre"],
            telefono=fila["telefono"],
            zona=Zona(fila["zona"]),
            vehiculo=TipoVehiculo(fila["vehiculo"]),
        )
