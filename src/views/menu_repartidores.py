"""Menú ABM de repartidores."""

from src.models.zona import TipoVehiculo, Zona
from src.services.estadisticas_service import EstadisticasService
from src.services.repartidor_service import RepartidorService
from src.views import consola as c


class MenuRepartidores:
    def __init__(self, servicio: RepartidorService, estadisticas: EstadisticasService) -> None:
        self._servicio = servicio
        self._estadisticas = estadisticas

    def ejecutar(self) -> None:
        acciones = {"1": self.listar, "2": self.alta, "3": self.modificar, "4": self.baja}
        while True:
            c.limpiar()
            opcion = c.menu({
                "1": "Listar repartidores (con ocupación)",
                "2": "Alta de repartidor",
                "3": "Modificar repartidor",
                "4": "Baja de repartidor",
                "0": "Volver",
            }, "REPARTIDORES")
            if opcion == "0":
                return
            c.ejecutar_accion(acciones[opcion])

    def listar(self) -> None:
        c.subtitulo("Listado de repartidores")
        df = self._estadisticas.df_repartidores()
        c.mostrar_tabla(df[["id", "nombre", "telefono", "zona", "vehiculo", "paquetes_activos",
                            "carga_kg", "cap_peso_kg", "carga_dm3", "cap_vol_dm3", "ocupacion_%"]])
        c.info("\nCapacidades por vehículo: " + " | ".join(
            f"{v.value}: {v.capacidad_peso_kg:g} kg / {v.capacidad_volumen_dm3:g} dm³" for v in TipoVehiculo
        ))

    def alta(self) -> None:
        c.subtitulo("Alta de repartidor  (x para cancelar)")
        repartidor = self._servicio.crear(
            nombre=c.pedir_texto("Nombre y apellido"),
            telefono=c.pedir_texto("Teléfono"),
            zona=c.pedir_opcion_enum("Zona", Zona),
            vehiculo=c.pedir_opcion_enum("Vehículo", TipoVehiculo),
        )
        c.exito(f"Repartidor creado con ID {repartidor.id}.")

    def modificar(self) -> None:
        c.subtitulo("Modificar repartidor  (Enter conserva el valor, x cancela)")
        repartidor = self._servicio.obtener(c.pedir_entero("ID del repartidor", minimo=1))
        repartidor.nombre = c.pedir_texto("Nombre y apellido", repartidor.nombre)
        repartidor.telefono = c.pedir_texto("Teléfono", repartidor.telefono)
        repartidor.zona = c.pedir_opcion_enum("Zona", Zona, repartidor.zona)
        repartidor.vehiculo = c.pedir_opcion_enum("Vehículo", TipoVehiculo, repartidor.vehiculo)
        self._servicio.modificar(repartidor)
        c.exito(f"Repartidor {repartidor.id} actualizado.")

    def baja(self) -> None:
        c.subtitulo("Baja de repartidor  (x para cancelar)")
        repartidor = self._servicio.obtener(c.pedir_entero("ID del repartidor", minimo=1))
        if c.confirmar(f"¿Eliminar a {repartidor.nombre} ({repartidor.zona})?"):
            self._servicio.eliminar(repartidor.id)
            c.exito("Repartidor eliminado.")
        else:
            c.info("Operación cancelada.")
