"""Enumeraciones del dominio: zonas, estados de reparto y tipos de vehículo."""

from enum import Enum


class Zona(Enum):
    """Zonas de cobertura del AMBA con coordenadas de referencia y tarifa base."""

    CABA = "CABA"
    ZONA_NORTE = "Zona Norte"
    ZONA_OESTE = "Zona Oeste"
    ZONA_SUR = "Zona Sur"

    @property
    def coordenadas(self) -> tuple[float, float]:
        """(latitud, longitud) de una localidad representativa de la zona."""
        return _COORDENADAS[self]

    @property
    def referencia(self) -> str:
        """Localidad usada como referencia para consultar el clima."""
        return _REFERENCIAS[self]

    @property
    def tarifa_base(self) -> float:
        """Costo fijo de un envío a la zona, en pesos."""
        return _TARIFAS[self]

    def __str__(self) -> str:
        return self.value


_COORDENADAS: dict[Zona, tuple[float, float]] = {
    Zona.CABA: (-34.6037, -58.3816),        # Obelisco
    Zona.ZONA_NORTE: (-34.4708, -58.5286),  # San Isidro
    Zona.ZONA_OESTE: (-34.6534, -58.6198),  # Morón
    Zona.ZONA_SUR: (-34.7609, -58.4063),    # Lomas de Zamora
}

_REFERENCIAS: dict[Zona, str] = {
    Zona.CABA: "Obelisco",
    Zona.ZONA_NORTE: "San Isidro",
    Zona.ZONA_OESTE: "Morón",
    Zona.ZONA_SUR: "Lomas de Zamora",
}

_TARIFAS: dict[Zona, float] = {
    Zona.CABA: 1800.0,
    Zona.ZONA_NORTE: 2500.0,
    Zona.ZONA_OESTE: 2300.0,
    Zona.ZONA_SUR: 2400.0,
}


class EstadoReparto(Enum):
    """Ciclo de vida de un reparto."""

    PENDIENTE = "Pendiente"
    EN_CAMINO = "En camino"
    ENTREGADO = "Entregado"
    CANCELADO = "Cancelado"

    @property
    def es_activo(self) -> bool:
        """Un reparto activo ocupa capacidad del repartidor."""
        return self in (EstadoReparto.PENDIENTE, EstadoReparto.EN_CAMINO)

    def transiciones_validas(self) -> tuple["EstadoReparto", ...]:
        """Estados a los que se puede pasar desde el estado actual."""
        return _TRANSICIONES[self]

    def __str__(self) -> str:
        return self.value


_TRANSICIONES: dict[EstadoReparto, tuple[EstadoReparto, ...]] = {
    EstadoReparto.PENDIENTE: (EstadoReparto.EN_CAMINO, EstadoReparto.CANCELADO),
    EstadoReparto.EN_CAMINO: (EstadoReparto.ENTREGADO, EstadoReparto.CANCELADO),
    EstadoReparto.ENTREGADO: (),
    EstadoReparto.CANCELADO: (),
}


class TipoVehiculo(Enum):
    """Tipo de vehículo del repartidor; define su capacidad máxima."""

    MOTO = "Moto"
    AUTO = "Auto"
    CAMIONETA = "Camioneta"

    @property
    def capacidad_peso_kg(self) -> float:
        return _CAPACIDADES[self][0]

    @property
    def capacidad_volumen_dm3(self) -> float:
        return _CAPACIDADES[self][1]

    def __str__(self) -> str:
        return self.value


# (peso máximo en kg, volumen máximo en dm3 = litros)
_CAPACIDADES: dict[TipoVehiculo, tuple[float, float]] = {
    TipoVehiculo.MOTO: (25.0, 90.0),
    TipoVehiculo.AUTO: (120.0, 400.0),
    TipoVehiculo.CAMIONETA: (500.0, 2000.0),
}
