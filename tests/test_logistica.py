"""Pruebas automáticas (unittest, sin dependencias extra).

Ejecutar desde la raíz del proyecto:
    python -m unittest -v
"""

import shutil
import tempfile
import unittest
from pathlib import Path

import requests

from src.exceptions import (
    CapacidadExcedidaError, EntidadNoEncontradaError, OperacionNoPermitidaError,
    PaqueteYaAsignadoError, PersistenciaError, TransicionEstadoInvalidaError,
    ValidacionError, ZonaIncompatibleError,
)
from src.models import EstadoReparto, Paquete, Repartidor, TipoVehiculo, Zona
from src.repositories import PaqueteRepository, RepartidorRepository, RepartoRepository
from src.services import (
    AsignacionService, ClimaService, EstadisticasService, PaqueteService, RepartidorService,
)
from src.services.clima_service import calcular_recargo


class _RespuestaFalsa:
    def __init__(self, datos: dict) -> None:
        self._datos = datos

    def raise_for_status(self) -> None:
        pass

    def json(self) -> dict:
        return self._datos


def api_lluvia(*_args, **_kwargs) -> _RespuestaFalsa:
    return _RespuestaFalsa({"current": {"temperature_2m": 14.2, "precipitation": 1.4,
                                        "weather_code": 63, "wind_speed_10m": 12.0}})


def api_caida(*_args, **_kwargs):
    raise requests.ConnectionError("sin conexión")


class BaseTest(unittest.TestCase):
    def setUp(self) -> None:
        self.dir = Path(tempfile.mkdtemp())
        self.paquetes = PaqueteRepository(self.dir)
        self.repartidores = RepartidorRepository(self.dir)
        self.repartos = RepartoRepository(self.dir)
        self.clima = ClimaService(http_get=api_lluvia)
        self.asignacion = AsignacionService(self.paquetes, self.repartidores, self.repartos, self.clima)

    def tearDown(self) -> None:
        shutil.rmtree(self.dir, ignore_errors=True)

    def nuevo_paquete(self, peso: float = 5, volumen: float = 10, zona: Zona = Zona.CABA) -> Paquete:
        return self.paquetes.add(Paquete("Caja", "Ana", "Calle 1", zona, peso, volumen))

    def nuevo_repartidor(self, vehiculo: TipoVehiculo = TipoVehiculo.MOTO, zona: Zona = Zona.CABA) -> Repartidor:
        return self.repartidores.add(Repartidor("Luis", "11-1234", zona, vehiculo))


class TestRepositorios(BaseTest):
    def test_crea_carpeta_y_encabezados(self) -> None:
        for archivo in ("paquetes.csv", "repartidores.csv", "repartos.csv"):
            self.assertTrue((self.dir / archivo).exists())
        self.assertEqual((self.dir / "paquetes.csv").read_text(encoding="utf-8").strip(),
                         ",".join(Paquete.campos()))

    def test_tipos_se_conservan(self) -> None:
        self.nuevo_paquete(peso=2.5, volumen=7)
        leido = self.paquetes.get_all()[0]
        self.assertIsInstance(leido.id, int)
        self.assertIsInstance(leido.peso_kg, float)
        self.assertIs(leido.zona, Zona.CABA)

    def test_ids_no_se_repiten_tras_borrar(self) -> None:
        a, b = self.nuevo_paquete(), self.nuevo_paquete()
        self.paquetes.delete(a.id)
        c = self.nuevo_paquete()
        self.assertEqual(c.id, b.id + 1)

    def test_id_inexistente(self) -> None:
        with self.assertRaises(EntidadNoEncontradaError):
            self.paquetes.get_by_id(999)

    def test_csv_corrupto(self) -> None:
        with (self.dir / "paquetes.csv").open("a", encoding="utf-8") as f:
            f.write("1,Caja,Ana,Calle,Marte,abc,1\n")
        with self.assertRaises(PersistenciaError):
            self.paquetes.get_all()

    def test_validaciones_del_modelo(self) -> None:
        with self.assertRaises(ValidacionError):
            Paquete("Caja", "Ana", "Calle", Zona.CABA, -1, 10)
        with self.assertRaises(ValidacionError):
            Repartidor("  ", "11", Zona.CABA, TipoVehiculo.MOTO)


class TestAsignacion(BaseTest):
    def test_asignacion_valida_aplica_recargo(self) -> None:
        p, r = self.nuevo_paquete(), self.nuevo_repartidor()
        reparto = self.asignacion.asignar(p.id, r.id)
        self.assertEqual(reparto.recargo_pct, 15.0)  # lluvia
        self.assertEqual(reparto.estado, EstadoReparto.PENDIENTE)
        self.assertAlmostEqual(reparto.costo_total, reparto.costo_base * 1.15, places=2)

    def test_zona_incompatible(self) -> None:
        p = self.nuevo_paquete(zona=Zona.ZONA_SUR)
        r = self.nuevo_repartidor(zona=Zona.CABA)
        with self.assertRaises(ZonaIncompatibleError):
            self.asignacion.asignar(p.id, r.id)

    def test_capacidad_acumulada(self) -> None:
        r = self.nuevo_repartidor(TipoVehiculo.MOTO)  # 25 kg
        self.asignacion.asignar(self.nuevo_paquete(peso=15).id, r.id)
        with self.assertRaises(CapacidadExcedidaError):
            self.asignacion.asignar(self.nuevo_paquete(peso=15).id, r.id)

    def test_no_se_asigna_dos_veces(self) -> None:
        p = self.nuevo_paquete()
        r1, r2 = self.nuevo_repartidor(), self.nuevo_repartidor()
        self.asignacion.asignar(p.id, r1.id)
        with self.assertRaises(PaqueteYaAsignadoError):
            self.asignacion.asignar(p.id, r2.id)

    def test_cancelar_libera_capacidad(self) -> None:
        r = self.nuevo_repartidor(TipoVehiculo.MOTO)
        reparto = self.asignacion.asignar(self.nuevo_paquete(peso=20).id, r.id)
        self.asignacion.cambiar_estado(reparto.id, EstadoReparto.CANCELADO)
        self.assertEqual(self.asignacion.cargas_actuales()[r.id].peso_kg, 0)
        self.assertEqual(len(self.asignacion.paquetes_sin_asignar()), 1)

    def test_transiciones(self) -> None:
        reparto = self.asignacion.asignar(self.nuevo_paquete().id, self.nuevo_repartidor().id)
        with self.assertRaises(TransicionEstadoInvalidaError):
            self.asignacion.cambiar_estado(reparto.id, EstadoReparto.ENTREGADO)
        self.asignacion.cambiar_estado(reparto.id, EstadoReparto.EN_CAMINO)
        self.asignacion.cambiar_estado(reparto.id, EstadoReparto.ENTREGADO)
        with self.assertRaises(TransicionEstadoInvalidaError):
            self.asignacion.cambiar_estado(reparto.id, EstadoReparto.CANCELADO)

    def test_greedy_respeta_capacidad_y_zona(self) -> None:
        moto = self.nuevo_repartidor(TipoVehiculo.MOTO)
        auto = self.nuevo_repartidor(TipoVehiculo.AUTO)
        for peso in (20, 18, 10, 6, 3):
            self.nuevo_paquete(peso=peso)
        self.nuevo_paquete(zona=Zona.ZONA_OESTE)  # sin repartidores en la zona
        resultado = self.asignacion.asignar_automatico()
        self.assertEqual(len(resultado.asignados), 5)
        self.assertEqual(resultado.no_asignados[0][1], "No hay repartidores en la zona")
        cargas = self.asignacion.cargas_actuales()
        self.assertLessEqual(cargas[moto.id].peso_kg, 25)
        self.assertLessEqual(cargas[auto.id].peso_kg, 120)


class TestServiciosABM(BaseTest):
    def test_no_modificar_ni_borrar_paquete_asignado(self) -> None:
        servicio = PaqueteService(self.paquetes, self.repartos)
        p = self.nuevo_paquete()
        self.asignacion.asignar(p.id, self.nuevo_repartidor().id)
        with self.assertRaises(OperacionNoPermitidaError):
            servicio.modificar(p)
        with self.assertRaises(OperacionNoPermitidaError):
            servicio.eliminar(p.id)

    def test_no_cambiar_vehiculo_con_repartos_activos(self) -> None:
        servicio = RepartidorService(self.repartidores, self.repartos)
        r = self.nuevo_repartidor()
        self.asignacion.asignar(self.nuevo_paquete().id, r.id)
        r.vehiculo = TipoVehiculo.AUTO
        with self.assertRaises(OperacionNoPermitidaError):
            servicio.modificar(r)


class TestClima(unittest.TestCase):
    def test_regla_de_recargo(self) -> None:
        self.assertEqual(calcular_recargo(0, 0, 10), 0)
        self.assertEqual(calcular_recargo(61, 2, 10), 15)
        self.assertEqual(calcular_recargo(95, 5, 10), 25)
        self.assertEqual(calcular_recargo(3, 0, 45), 10)
        self.assertEqual(calcular_recargo(95, 5, 50), 35)

    def test_parseo_respuesta_api(self) -> None:
        clima = ClimaService(http_get=api_lluvia).obtener_clima(Zona.CABA)
        self.assertFalse(clima.es_fallback)
        self.assertEqual(clima.descripcion, "Lluvia")
        self.assertEqual(clima.recargo_pct, 15)

    def test_fallback_sin_conexion(self) -> None:
        servicio = ClimaService(http_get=api_caida)
        clima = servicio.obtener_clima(Zona.ZONA_SUR)
        self.assertTrue(clima.es_fallback)
        self.assertEqual(clima.recargo_pct, 10)
        self.assertIn("ConnectionError", servicio.ultimo_error or "")

    def test_modo_offline_manual(self) -> None:
        servicio = ClimaService(http_get=api_lluvia)
        servicio.alternar_modo_offline()
        self.assertTrue(servicio.obtener_clima(Zona.CABA).es_fallback)


class TestEstadisticas(BaseTest):
    def test_kpis_sin_datos_no_fallan(self) -> None:
        stats = EstadisticasService(self.paquetes, self.repartidores, self.repartos, self.asignacion)
        _, global_pct = stats.kpi_ocupacion()
        self.assertEqual(global_pct, 0.0)
        self.assertEqual(len(stats.kpi_costo_por_zona()), 4)
        self.assertEqual(stats.kpi_estados()["cantidad"].sum(), 0)

    def test_kpis_con_datos(self) -> None:
        r = self.nuevo_repartidor(TipoVehiculo.MOTO)
        self.asignacion.asignar(self.nuevo_paquete(peso=12.5, volumen=10).id, r.id)
        stats = EstadisticasService(self.paquetes, self.repartidores, self.repartos, self.asignacion)
        tabla, global_pct = stats.kpi_ocupacion()
        self.assertEqual(tabla.loc[0, "ocupacion_%"], 50.0)
        self.assertEqual(global_pct, 50.0)
        estados = stats.kpi_estados().set_index("estado")
        self.assertEqual(estados.loc["Pendiente", "porcentaje"], 100.0)


if __name__ == "__main__":
    unittest.main()
