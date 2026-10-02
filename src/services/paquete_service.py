"""Reglas de negocio del ABM de paquetes."""

from src.exceptions import OperacionNoPermitidaError
from src.models.paquete import Paquete
from src.models.zona import Zona
from src.repositories.paquete_repository import PaqueteRepository
from src.repositories.reparto_repository import RepartoRepository


class PaqueteService:
    def __init__(self, paquetes: PaqueteRepository, repartos: RepartoRepository) -> None:
        self._paquetes = paquetes
        self._repartos = repartos

    def listar(self) -> list[Paquete]:
        return self._paquetes.get_all()

    def obtener(self, paquete_id: int) -> Paquete:
        return self._paquetes.get_by_id(paquete_id)

    def crear(self, descripcion: str, destinatario: str, direccion: str,
              zona: Zona, peso_kg: float, volumen_dm3: float) -> Paquete:
        paquete = Paquete(descripcion, destinatario, direccion, zona, peso_kg, volumen_dm3)
        return self._paquetes.add(paquete)

    def modificar(self, paquete: Paquete) -> Paquete:
        """Solo se puede modificar un paquete que no tenga un reparto vigente."""
        if self._repartos.get_vigente_de_paquete(paquete.id):
            raise OperacionNoPermitidaError(
                "El paquete tiene un reparto vigente; cancelalo antes de modificarlo."
            )
        # se vuelve a construir para que corran las validaciones de __post_init__
        validado = Paquete(paquete.descripcion, paquete.destinatario, paquete.direccion,
                           paquete.zona, paquete.peso_kg, paquete.volumen_dm3, paquete.id)
        return self._paquetes.update(validado)

    def eliminar(self, paquete_id: int) -> None:
        """No se borran paquetes con historial de repartos (integridad referencial)."""
        self._paquetes.get_by_id(paquete_id)  # valida existencia
        if self._repartos.get_by_paquete(paquete_id):
            raise OperacionNoPermitidaError(
                "El paquete tiene repartos registrados y no se puede eliminar."
            )
        self._paquetes.delete(paquete_id)
