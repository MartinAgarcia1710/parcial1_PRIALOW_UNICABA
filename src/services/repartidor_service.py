"""Reglas de negocio del ABM de repartidores."""

from src.exceptions import OperacionNoPermitidaError
from src.models.repartidor import Repartidor
from src.models.zona import TipoVehiculo, Zona
from src.repositories.repartidor_repository import RepartidorRepository
from src.repositories.reparto_repository import RepartoRepository


class RepartidorService:
    def __init__(self, repartidores: RepartidorRepository, repartos: RepartoRepository) -> None:
        self._repartidores = repartidores
        self._repartos = repartos

    def listar(self) -> list[Repartidor]:
        return self._repartidores.get_all()

    def obtener(self, repartidor_id: int) -> Repartidor:
        return self._repartidores.get_by_id(repartidor_id)

    def crear(self, nombre: str, telefono: str, zona: Zona, vehiculo: TipoVehiculo) -> Repartidor:
        return self._repartidores.add(Repartidor(nombre, telefono, zona, vehiculo))

    def modificar(self, repartidor: Repartidor) -> Repartidor:
        """Con repartos activos no se puede cambiar la zona ni el vehículo."""
        actual = self._repartidores.get_by_id(repartidor.id)
        cambia_operacion = (repartidor.zona != actual.zona or repartidor.vehiculo != actual.vehiculo)
        if cambia_operacion and self._repartos.get_by_repartidor(repartidor.id, solo_activos=True):
            raise OperacionNoPermitidaError(
                "El repartidor tiene repartos activos: no se puede cambiar su zona ni su vehículo."
            )
        validado = Repartidor(repartidor.nombre, repartidor.telefono,
                              repartidor.zona, repartidor.vehiculo, repartidor.id)
        return self._repartidores.update(validado)

    def eliminar(self, repartidor_id: int) -> None:
        self._repartidores.get_by_id(repartidor_id)
        if self._repartos.get_by_repartidor(repartidor_id):
            raise OperacionNoPermitidaError(
                "El repartidor tiene repartos registrados y no se puede eliminar."
            )
        self._repartidores.delete(repartidor_id)
