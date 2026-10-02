"""Carga de datos de ejemplo para la demostración (evita tipear todo en la defensa)."""

import random
from dataclasses import dataclass

from src.models.paquete import Paquete
from src.models.repartidor import Repartidor
from src.models.zona import EstadoReparto, TipoVehiculo, Zona
from src.repositories.paquete_repository import PaqueteRepository
from src.repositories.repartidor_repository import RepartidorRepository
from src.repositories.reparto_repository import RepartoRepository
from src.services.asignacion_service import AsignacionService

_REPARTIDORES: list[tuple[str, str, Zona, TipoVehiculo]] = [
    ("Lucía Fernández", "11-4521-3301", Zona.CABA, TipoVehiculo.MOTO),
    ("Diego Ramírez", "11-4733-1290", Zona.CABA, TipoVehiculo.CAMIONETA),
    ("Sofía Acosta", "11-5102-7781", Zona.ZONA_NORTE, TipoVehiculo.MOTO),
    ("Matías Herrera", "11-3388-0045", Zona.ZONA_NORTE, TipoVehiculo.AUTO),
    ("Valentina Ruiz", "11-6620-4418", Zona.ZONA_OESTE, TipoVehiculo.MOTO),
    ("Nicolás Benítez", "11-2917-5532", Zona.ZONA_OESTE, TipoVehiculo.AUTO),
    ("Camila Sosa", "11-4089-6627", Zona.ZONA_SUR, TipoVehiculo.MOTO),
    ("Julián Medina", "11-5576-2210", Zona.ZONA_SUR, TipoVehiculo.AUTO),
]

# (descripción, rango de peso en kg, rango de volumen en dm3)
_TIPOS_PAQUETE: list[tuple[str, tuple[float, float], tuple[float, float]]] = [
    ("Sobre con documentación", (0.1, 0.5), (0.5, 2.0)),
    ("Caja de libros", (4.0, 12.0), (15.0, 35.0)),
    ("Notebook", (1.5, 3.0), (6.0, 10.0)),
    ("Indumentaria", (0.5, 3.0), (5.0, 20.0)),
    ("Electrodoméstico chico", (3.0, 9.0), (20.0, 60.0)),
    ("Repuestos de auto", (5.0, 20.0), (10.0, 40.0)),
    ("Monitor 27 pulgadas", (6.0, 8.0), (60.0, 80.0)),
    ("Microondas", (11.0, 15.0), (45.0, 60.0)),
    ("Bicicleta desarmada", (12.0, 18.0), (150.0, 220.0)),
    ("Bolsa de alimento para mascotas", (15.0, 22.0), (30.0, 45.0)),
]

_DESTINATARIOS = [
    "Ana Gómez", "Carlos Pereyra", "Florencia Díaz", "Martina López", "Gonzalo Romero",
    "Paula Torres", "Federico Álvarez", "Rocío Molina", "Tomás Castro", "Agustina Ríos",
    "Ezequiel Vega", "Milagros Ortiz", "Bruno Suárez", "Carolina Rojas", "Facundo Luna",
]

_CALLES: dict[Zona, list[str]] = {
    Zona.CABA: ["Av. Corrientes", "Av. Rivadavia", "Av. Santa Fe", "Av. Cabildo", "Av. San Juan"],
    Zona.ZONA_NORTE: ["Av. Centenario", "Av. Maipú", "Av. Libertador", "Belgrano", "Av. Márquez"],
    Zona.ZONA_OESTE: ["Av. Rivadavia", "Av. Gaona", "Brown", "Belgrano", "Av. Vergara"],
    Zona.ZONA_SUR: ["Av. Hipólito Yrigoyen", "Av. Mitre", "Laprida", "Av. Pavón", "Oliden"],
}


@dataclass
class ResultadoSeed:
    repartidores: int
    paquetes: int
    asignados: int
    sin_asignar: int


class SeederService:
    def __init__(self, paquetes: PaqueteRepository, repartidores: RepartidorRepository,
                 repartos: RepartoRepository, asignacion: AsignacionService) -> None:
        self._paquetes = paquetes
        self._repartidores = repartidores
        self._repartos = repartos
        self._asignacion = asignacion

    def hay_datos(self) -> bool:
        return bool(self._paquetes.get_all() or self._repartidores.get_all())

    def cargar(self, cantidad_paquetes: int = 36, semilla: int = 2026) -> ResultadoSeed:
        """Borra todo y genera un escenario reproducible (misma semilla = mismos datos)."""
        rnd = random.Random(semilla)
        self._repartos.clear()
        self._paquetes.clear()
        self._repartidores.clear()

        self._repartidores.add_many([Repartidor(n, t, z, v) for n, t, z, v in _REPARTIDORES])

        nuevos: list[Paquete] = []
        zonas = list(Zona)
        for _ in range(cantidad_paquetes):
            descripcion, (pmin, pmax), (vmin, vmax) = rnd.choice(_TIPOS_PAQUETE)
            zona = rnd.choice(zonas)
            nuevos.append(Paquete(
                descripcion=descripcion,
                destinatario=rnd.choice(_DESTINATARIOS),
                direccion=f"{rnd.choice(_CALLES[zona])} {rnd.randint(100, 5900)}",
                zona=zona,
                peso_kg=round(rnd.uniform(pmin, pmax), 2),
                volumen_dm3=round(rnd.uniform(vmin, vmax), 1),
            ))
        self._paquetes.add_many(nuevos)

        resultado = self._asignacion.asignar_automatico()

        # Avanza algunos repartos para que las estadísticas tengan variedad
        for reparto in resultado.asignados:
            sorteo = rnd.random()
            if sorteo < 0.30:
                self._asignacion.cambiar_estado(reparto.id, EstadoReparto.EN_CAMINO)
            elif sorteo < 0.55:
                self._asignacion.cambiar_estado(reparto.id, EstadoReparto.EN_CAMINO)
                self._asignacion.cambiar_estado(reparto.id, EstadoReparto.ENTREGADO)
            elif sorteo < 0.62:
                self._asignacion.cambiar_estado(reparto.id, EstadoReparto.CANCELADO)

        return ResultadoSeed(
            repartidores=len(_REPARTIDORES),
            paquetes=len(nuevos),
            asignados=len(resultado.asignados),
            sin_asignar=len(resultado.no_asignados),
        )
