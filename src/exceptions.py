"""Excepciones propias del dominio logístico."""


class LogisticaError(Exception):
    """Excepción base de la aplicación. Todas las demás heredan de esta."""


class ValidacionError(LogisticaError):
    """Un dato ingresado no cumple las reglas del dominio."""


class EntidadNoEncontradaError(LogisticaError):
    """No existe una entidad con el ID solicitado."""

    def __init__(self, entidad: str, id_: int) -> None:
        super().__init__(f"No existe {entidad} con ID {id_}.")
        self.entidad = entidad
        self.id_ = id_


class PersistenciaError(LogisticaError):
    """Fallo al leer o escribir los archivos CSV."""


class CapacidadExcedidaError(LogisticaError):
    """El paquete supera la capacidad disponible del repartidor."""


class ZonaIncompatibleError(LogisticaError):
    """El paquete y el repartidor pertenecen a zonas distintas."""


class PaqueteYaAsignadoError(LogisticaError):
    """El paquete ya tiene un reparto activo o entregado."""


class TransicionEstadoInvalidaError(LogisticaError):
    """El cambio de estado solicitado no está permitido."""


class OperacionNoPermitidaError(LogisticaError):
    """La operación viola una regla de negocio (p. ej. borrar algo en uso)."""
