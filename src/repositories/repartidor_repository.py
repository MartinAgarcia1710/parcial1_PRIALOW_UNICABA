from pathlib import Path

from src.config import DATA_DIR
from src.models.repartidor import Repartidor
from src.models.zona import Zona
from src.repositories.base_repository import BaseRepository


class RepartidorRepository(BaseRepository[Repartidor]):
    def __init__(self, data_dir: Path = DATA_DIR) -> None:
        super().__init__(Repartidor, "repartidores.csv", "repartidor", data_dir)

    def get_by_zona(self, zona: Zona) -> list[Repartidor]:
        return self.find(lambda r: r.zona == zona)
