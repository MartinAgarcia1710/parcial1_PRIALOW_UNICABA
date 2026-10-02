"""Repositorio genérico sobre archivos CSV (Patrón Repositorio)."""

import csv
from abc import ABC
from pathlib import Path
from typing import Callable, Generic, TypeVar

from src.config import DATA_DIR
from src.exceptions import EntidadNoEncontradaError, PersistenciaError
from src.models.entidad import Entidad

T = TypeVar("T", bound=Entidad)


class BaseRepository(ABC, Generic[T]):
    """CRUD genérico para cualquier `Entidad` persistida en un CSV.

    Cada repositorio concreto solo indica qué modelo maneja y en qué archivo;
    la lectura, escritura, parseo y generación de IDs se resuelven acá.
    """

    def __init__(self, modelo: type[T], nombre_archivo: str, nombre_entidad: str,
                 data_dir: Path = DATA_DIR) -> None:
        self._modelo = modelo
        self._nombre_entidad = nombre_entidad
        self._ruta = data_dir / nombre_archivo
        self._campos = modelo.campos()
        self._inicializar_archivo()

    @property
    def ruta(self) -> Path:
        return self._ruta

    # --- I/O --------------------------------------------------------------------
    def _inicializar_archivo(self) -> None:
        """Crea la carpeta data/ y el CSV con encabezados si no existen."""
        try:
            self._ruta.parent.mkdir(parents=True, exist_ok=True)
            if not self._ruta.exists() or self._ruta.stat().st_size == 0:
                self._guardar_todos([])
        except OSError as e:
            raise PersistenciaError(f"No se pudo crear {self._ruta}: {e}") from e

    def _guardar_todos(self, entidades: list[T]) -> None:
        try:
            # newline="" evita líneas en blanco intermedias en Windows
            with self._ruta.open("w", encoding="utf-8", newline="") as f:
                escritor = csv.DictWriter(f, fieldnames=self._campos)
                escritor.writeheader()
                for entidad in entidades:
                    escritor.writerow(entidad.to_dict())
        except OSError as e:
            raise PersistenciaError(f"No se pudo escribir {self._ruta.name}: {e}") from e

    def get_all(self) -> list[T]:
        try:
            with self._ruta.open("r", encoding="utf-8", newline="") as f:
                filas = list(csv.DictReader(f))
        except FileNotFoundError:
            self._inicializar_archivo()
            return []
        except OSError as e:
            raise PersistenciaError(f"No se pudo leer {self._ruta.name}: {e}") from e

        entidades: list[T] = []
        for nro_linea, fila in enumerate(filas, start=2):  # línea 1 = encabezado
            try:
                entidades.append(self._modelo.from_dict(fila))
            except (KeyError, ValueError, TypeError) as e:
                raise PersistenciaError(
                    f"Dato inválido en {self._ruta.name}, línea {nro_linea}: {e}"
                ) from e
        return entidades

    # --- CRUD -------------------------------------------------------------------
    def get_by_id(self, id_: int) -> T:
        for entidad in self.get_all():
            if entidad.id == id_:
                return entidad
        raise EntidadNoEncontradaError(self._nombre_entidad, id_)

    def existe(self, id_: int) -> bool:
        return any(e.id == id_ for e in self.get_all())

    def find(self, criterio: Callable[[T], bool]) -> list[T]:
        """Devuelve las entidades que cumplen el criterio."""
        return [e for e in self.get_all() if criterio(e)]

    def add(self, entidad: T) -> T:
        """Agrega la entidad asignándole un ID nuevo (máximo actual + 1)."""
        entidades = self.get_all()
        # max+1 y no len+1: si se borró un registro, len+1 duplicaría IDs
        entidad.id = max((e.id for e in entidades), default=0) + 1
        entidades.append(entidad)
        self._guardar_todos(entidades)
        return entidad

    def add_many(self, nuevas: list[T]) -> list[T]:
        """Alta masiva en una sola escritura (lo usa el seeder)."""
        entidades = self.get_all()
        siguiente = max((e.id for e in entidades), default=0) + 1
        for i, entidad in enumerate(nuevas):
            entidad.id = siguiente + i
        entidades.extend(nuevas)
        self._guardar_todos(entidades)
        return nuevas

    def update(self, entidad: T) -> T:
        entidades = self.get_all()
        for i, actual in enumerate(entidades):
            if actual.id == entidad.id:
                entidades[i] = entidad
                self._guardar_todos(entidades)
                return entidad
        raise EntidadNoEncontradaError(self._nombre_entidad, entidad.id)

    def delete(self, id_: int) -> None:
        entidades = self.get_all()
        restantes = [e for e in entidades if e.id != id_]
        if len(restantes) == len(entidades):
            raise EntidadNoEncontradaError(self._nombre_entidad, id_)
        self._guardar_todos(restantes)

    def clear(self) -> None:
        """Vacía el archivo dejando solo los encabezados."""
        self._guardar_todos([])
