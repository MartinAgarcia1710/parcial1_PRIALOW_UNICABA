from pathlib import Path

from src.config import DATA_DIR
from src.models.paquete import Paquete
from src.models.zona import Zona
from src.repositories.base_repository import BaseRepository


class PaqueteRepository(BaseRepository[Paquete]):
    def __init__(self, data_dir: Path = DATA_DIR) -> None:
        super().__init__(Paquete, "paquetes.csv", "paquete", data_dir)

    def get_by_zona(self, zona: Zona) -> list[Paquete]:
        return self.find(lambda p: p.zona == zona)
