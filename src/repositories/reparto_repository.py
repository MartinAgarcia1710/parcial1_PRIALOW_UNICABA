from pathlib import Path

from src.config import DATA_DIR
from src.models.reparto import Reparto
from src.models.zona import EstadoReparto
from src.repositories.base_repository import BaseRepository


class RepartoRepository(BaseRepository[Reparto]):
    def __init__(self, data_dir: Path = DATA_DIR) -> None:
        super().__init__(Reparto, "repartos.csv", "reparto", data_dir)

    def get_by_repartidor(self, repartidor_id: int, solo_activos: bool = False) -> list[Reparto]:
        return self.find(
            lambda r: r.repartidor_id == repartidor_id and (r.estado.es_activo or not solo_activos)
        )

    def get_by_paquete(self, paquete_id: int) -> list[Reparto]:
        """Historial de repartos de un paquete (puede tener cancelados previos)."""
        return self.find(lambda r: r.paquete_id == paquete_id)

    def get_vigente_de_paquete(self, paquete_id: int) -> Reparto | None:
        """Reparto no cancelado del paquete (activo o entregado), si existe."""
        vigentes = self.find(
            lambda r: r.paquete_id == paquete_id and r.estado != EstadoReparto.CANCELADO
        )
        return vigentes[0] if vigentes else None

    def actualizar_estado(self, reparto_id: int, nuevo_estado: EstadoReparto) -> Reparto:
        reparto = self.get_by_id(reparto_id)
        reparto.estado = nuevo_estado
        return self.update(reparto)
