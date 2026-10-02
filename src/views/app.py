"""Menú principal: compone las dependencias y delega en cada submenú."""

from colorama import Fore, Style

from src.repositories.paquete_repository import PaqueteRepository
from src.repositories.repartidor_repository import RepartidorRepository
from src.repositories.reparto_repository import RepartoRepository
from src.services.asignacion_service import AsignacionService
from src.services.clima_service import ClimaService
from src.services.estadisticas_service import EstadisticasService
from src.services.paquete_service import PaqueteService
from src.services.repartidor_service import RepartidorService
from src.services.seeder_service import SeederService
from src.views import consola as c
from src.views.menu_estadisticas import MenuEstadisticas
from src.views.menu_paquetes import MenuPaquetes
from src.views.menu_repartidores import MenuRepartidores
from src.views.menu_repartos import MenuRepartos


class App:
    def __init__(self) -> None:
        # Composición de dependencias (inyección manual por constructor)
        paquetes = PaqueteRepository()
        repartidores = RepartidorRepository()
        repartos = RepartoRepository()
        clima = ClimaService()
        asignacion = AsignacionService(paquetes, repartidores, repartos, clima)
        estadisticas = EstadisticasService(paquetes, repartidores, repartos, asignacion)

        self._seeder = SeederService(paquetes, repartidores, repartos, asignacion)
        self._estadisticas = estadisticas
        self._menu_paquetes = MenuPaquetes(PaqueteService(paquetes, repartos), estadisticas)
        self._menu_repartidores = MenuRepartidores(RepartidorService(repartidores, repartos), estadisticas)
        self._menu_repartos = MenuRepartos(asignacion, clima, estadisticas)
        self._menu_estadisticas = MenuEstadisticas(estadisticas)

    def ejecutar(self) -> None:
        while True:
            c.limpiar()
            self._encabezado()
            opcion = c.menu({
                "1": "Paquetes",
                "2": "Repartidores",
                "3": "Asignación y repartos",
                "4": "Estadísticas",
                "5": "Cargar datos de ejemplo",
                "0": "Salir",
            })
            match opcion:
                case "1":
                    self._menu_paquetes.ejecutar()
                case "2":
                    self._menu_repartidores.ejecutar()
                case "3":
                    self._menu_repartos.ejecutar()
                case "4":
                    self._menu_estadisticas.ejecutar()
                case "5":
                    c.ejecutar_accion(self._cargar_ejemplo)
                case "0":
                    print(f"\n{Fore.CYAN}¡Hasta luego!{Style.RESET_ALL}")
                    return

    def _encabezado(self) -> None:
        ancho = 48
        print(f"{Fore.CYAN}{Style.BRIGHT}")
        print("  ╔" + "═" * ancho + "╗")
        for linea in ("PLATAFORMA DE GESTIÓN LOGÍSTICA", "CABA · Zona Norte · Zona Oeste · Zona Sur"):
            print("  ║" + linea.center(ancho) + "║")
        print("  ╚" + "═" * ancho + f"╝{Style.RESET_ALL}")
        try:
            r = self._estadisticas.resumen()
            c.info(f"  {r['paquetes']} paquetes ({r['sin_asignar']} sin asignar) · "
                   f"{r['repartidores']} repartidores · ocupación global {r['ocupacion_global_%']} %\n")
        except Exception:  # el encabezado nunca debe impedir usar el menú
            print()

    def _cargar_ejemplo(self) -> None:
        c.subtitulo("Datos de ejemplo")
        if self._seeder.hay_datos() and not c.confirmar(
            "Se BORRARÁN los datos actuales y se generarán datos de prueba. ¿Continuar?"
        ):
            c.info("Operación cancelada.")
            return
        c.info("Generando datos y consultando el clima de las 4 zonas...")
        resultado = self._seeder.cargar()
        c.exito(f"{resultado.repartidores} repartidores y {resultado.paquetes} paquetes creados. "
                f"Asignados: {resultado.asignados} · sin lugar: {resultado.sin_asignar}.")
