"""Contrato común de las entidades persistibles en CSV."""

from abc import ABC, abstractmethod
from typing import Self


class Entidad(ABC):
    """Toda entidad tiene un ID entero y sabe convertirse desde/hacia una fila CSV.

    El repositorio genérico (BaseRepository[T]) solo depende de este contrato,
    por eso puede persistir cualquier modelo sin conocer sus campos.
    """

    id: int

    @classmethod
    @abstractmethod
    def campos(cls) -> list[str]:
        """Encabezados del CSV, en orden."""

    @abstractmethod
    def to_dict(self) -> dict[str, str]:
        """Serializa la entidad a una fila CSV (todos los valores como texto)."""

    @classmethod
    @abstractmethod
    def from_dict(cls, fila: dict[str, str]) -> Self:
        """Reconstruye la entidad a partir de una fila CSV, convirtiendo tipos."""
