"""Asignación de paquetes a repartidores y ciclo de vida de los repartos."""

from dataclasses import dataclass, field
from datetime import datetime

from src.config import COSTO_POR_DM3, COSTO_POR_KG
from src.exceptions import (
    CapacidadExcedidaError, PaqueteYaAsignadoError, TransicionEstadoInvalidaError,
    ZonaIncompatibleError,
)
from src.models.paquete import Paquete
from src.models.repartidor import Repartidor
from src.models.reparto import Reparto
from src.models.zona import EstadoReparto
from src.repositories.paquete_repository import PaqueteRepository
from src.repositories.repartidor_repository import RepartidorRepository
from src.repositories.reparto_repository import RepartoRepository
from src.services.clima_service import ClimaService


@dataclass
class Carga:
    """Carga activa de un repartidor (repartos pendientes + en camino)."""

    peso_kg: float = 0.0
    volumen_dm3: float = 0.0
    cantidad: int = 0


@dataclass
class ResultadoAsignacion:
    asignados: list[Reparto] = field(default_factory=list)
    no_asignados: list[tuple[Paquete, str]] = field(default_factory=list)


def calcular_costo_base(paquete: Paquete) -> float:
    """Tarifa fija de la zona + costo por peso + costo por volumen."""
    return round(
        paquete.zona.tarifa_base + paquete.peso_kg * COSTO_POR_KG + paquete.volumen_dm3 * COSTO_POR_DM3,
        2,
    )


class AsignacionService:
    def __init__(self, paquetes: PaqueteRepository, repartidores: RepartidorRepository,
                 repartos: RepartoRepository, clima: ClimaService) -> None:
        self._paquetes = paquetes
        self._repartidores = repartidores
        self._repartos = repartos
        self._clima = clima

    # --- consultas ---------------------------------------------------------------
    def cargas_actuales(self) -> dict[int, Carga]:
        """Carga activa de cada repartidor, calculada en una sola pasada."""
        paquetes = {p.id: p for p in self._paquetes.get_all()}
        cargas: dict[int, Carga] = {r.id: Carga() for r in self._repartidores.get_all()}
        for reparto in self._repartos.get_all():
            if not reparto.estado.es_activo or reparto.paquete_id not in paquetes:
                continue
            paquete = paquetes[reparto.paquete_id]
            carga = cargas.setdefault(reparto.repartidor_id, Carga())
            carga.peso_kg += paquete.peso_kg
            carga.volumen_dm3 += paquete.volumen_dm3
            carga.cantidad += 1
        return cargas

    def paquetes_sin_asignar(self) -> list[Paquete]:
        """Paquetes sin reparto vigente (nunca asignados o con el reparto cancelado)."""
        vigentes = {r.paquete_id for r in self._repartos.get_all()
                    if r.estado != EstadoReparto.CANCELADO}
        return [p for p in self._paquetes.get_all() if p.id not in vigentes]

    def repartidores_disponibles(self, paquete: Paquete) -> list[Repartidor]:
        """Repartidores de la zona del paquete que todavía tienen lugar para él."""
        cargas = self.cargas_actuales()
        return [
            r for r in self._repartidores.get_by_zona(paquete.zona)
            if r.puede_cargar(paquete, cargas[r.id].peso_kg, cargas[r.id].volumen_dm3)
        ]

    def listar_repartos(self) -> list[Reparto]:
        return self._repartos.get_all()

    def obtener_reparto(self, reparto_id: int) -> Reparto:
        return self._repartos.get_by_id(reparto_id)

    def nombres_repartidores(self) -> dict[int, str]:
        return {r.id: r.nombre for r in self._repartidores.get_all()}

    # --- comandos ----------------------------------------------------------------
    def asignar(self, paquete_id: int, repartidor_id: int) -> Reparto:
        """Asignación manual con todas las validaciones de negocio."""
        paquete = self._paquetes.get_by_id(paquete_id)
        repartidor = self._repartidores.get_by_id(repartidor_id)

        vigente = self._repartos.get_vigente_de_paquete(paquete_id)
        if vigente:
            raise PaqueteYaAsignadoError(
                f"El paquete {paquete_id} ya está en el reparto {vigente.id} ({vigente.estado})."
            )
        if paquete.zona != repartidor.zona:
            raise ZonaIncompatibleError(
                f"El paquete es de {paquete.zona} y el repartidor trabaja en {repartidor.zona}."
            )
        carga = self.cargas_actuales().get(repartidor_id, Carga())
        if not repartidor.puede_cargar(paquete, carga.peso_kg, carga.volumen_dm3):
            libre_peso = repartidor.capacidad_peso_kg - carga.peso_kg
            libre_vol = repartidor.capacidad_volumen_dm3 - carga.volumen_dm3
            raise CapacidadExcedidaError(
                f"{repartidor.nombre} tiene libre {libre_peso:.1f} kg / {libre_vol:.1f} dm³ "
                f"y el paquete pesa {paquete.peso_kg:.1f} kg / ocupa {paquete.volumen_dm3:.1f} dm³."
            )
        return self._repartos.add(self._crear_reparto(paquete, repartidor))

    def asignar_automatico(self) -> ResultadoAsignacion:
        """Heurística greedy Best-Fit Decreasing (variante de la mochila / bin packing).

        1. Ordena los paquetes sin asignar de mayor a menor peso.
        2. Para cada paquete busca, en su zona, los repartidores donde entra.
        3. Elige el que queda con MENOS capacidad libre de peso después de cargarlo
           (el "mejor ajuste"): así se completan vehículos y se dejan libres los grandes
           para los paquetes pesados que puedan llegar.
        No garantiza el óptimo (eso sería una mochila multidimensional, NP-difícil),
        pero es O(n·m), simple de explicar y da buenos resultados en la práctica.
        """
        resultado = ResultadoAsignacion()
        cargas = self.cargas_actuales()
        repartidores = self._repartidores.get_all()
        pendientes = sorted(self.paquetes_sin_asignar(), key=lambda p: p.peso_kg, reverse=True)

        for paquete in pendientes:
            candidatos = [
                r for r in repartidores
                if r.zona == paquete.zona
                and r.puede_cargar(paquete, cargas[r.id].peso_kg, cargas[r.id].volumen_dm3)
            ]
            if not candidatos:
                hay_en_zona = any(r.zona == paquete.zona for r in repartidores)
                motivo = ("Sin capacidad disponible en la zona" if hay_en_zona
                          else "No hay repartidores en la zona")
                resultado.no_asignados.append((paquete, motivo))
                continue

            elegido = min(
                candidatos,
                key=lambda r: r.capacidad_peso_kg - cargas[r.id].peso_kg - paquete.peso_kg,
            )
            cargas[elegido.id].peso_kg += paquete.peso_kg
            cargas[elegido.id].volumen_dm3 += paquete.volumen_dm3
            cargas[elegido.id].cantidad += 1
            resultado.asignados.append(self._crear_reparto(paquete, elegido))

        if resultado.asignados:
            self._repartos.add_many(resultado.asignados)  # una sola escritura al CSV
        return resultado

    def cambiar_estado(self, reparto_id: int, nuevo_estado: EstadoReparto) -> Reparto:
        reparto = self._repartos.get_by_id(reparto_id)
        if nuevo_estado not in reparto.estado.transiciones_validas():
            permitidos = ", ".join(str(e) for e in reparto.estado.transiciones_validas()) or "ninguno"
            raise TransicionEstadoInvalidaError(
                f"No se puede pasar de '{reparto.estado}' a '{nuevo_estado}'. Permitidos: {permitidos}."
            )
        return self._repartos.actualizar_estado(reparto_id, nuevo_estado)

    # --- privados ----------------------------------------------------------------
    def _crear_reparto(self, paquete: Paquete, repartidor: Repartidor) -> Reparto:
        clima = self._clima.obtener_clima(paquete.zona)
        return Reparto(
            paquete_id=paquete.id,
            repartidor_id=repartidor.id,
            zona=paquete.zona,
            fecha=datetime.now().replace(second=0, microsecond=0),
            costo_base=calcular_costo_base(paquete),
            recargo_pct=clima.recargo_pct,
            clima=clima.resumen,
        )
