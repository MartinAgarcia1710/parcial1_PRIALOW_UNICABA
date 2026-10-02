"""Menú ABM de paquetes."""

import pandas as pd

from src.models.zona import Zona
from src.services.estadisticas_service import EstadisticasService
from src.services.paquete_service import PaqueteService
from src.views import consola as c


class MenuPaquetes:
    def __init__(self, servicio: PaqueteService, estadisticas: EstadisticasService) -> None:
        self._servicio = servicio
        self._estadisticas = estadisticas

    def ejecutar(self) -> None:
        acciones = {
            "1": self.listar,
            "2": self.listar_por_zona,
            "3": self.alta,
            "4": self.modificar,
            "5": self.baja,
        }
        while True:
            c.limpiar()
            opcion = c.menu({
                "1": "Listar paquetes",
                "2": "Listar por zona",
                "3": "Alta de paquete",
                "4": "Modificar paquete",
                "5": "Baja de paquete",
                "0": "Volver",
            }, "PAQUETES")
            if opcion == "0":
                return
            c.ejecutar_accion(acciones[opcion])

    def _tabla(self, df: pd.DataFrame) -> pd.DataFrame:
        return df[["id", "descripcion", "destinatario", "direccion", "zona",
                   "peso_kg", "volumen_dm3", "estado", "repartidor"]]

    def listar(self) -> None:
        c.subtitulo("Listado de paquetes")
        c.mostrar_tabla(self._tabla(self._estadisticas.df_paquetes()))

    def listar_por_zona(self) -> None:
        zona = c.pedir_opcion_enum("Zona", Zona)
        df = self._estadisticas.df_paquetes()
        c.subtitulo(f"Paquetes de {zona}")
        c.mostrar_tabla(self._tabla(df[df["zona"] == zona.value]))

    def alta(self) -> None:
        c.subtitulo("Alta de paquete  (x para cancelar)")
        paquete = self._servicio.crear(
            descripcion=c.pedir_texto("Descripción"),
            destinatario=c.pedir_texto("Destinatario"),
            direccion=c.pedir_texto("Dirección"),
            zona=c.pedir_opcion_enum("Zona", Zona),
            peso_kg=c.pedir_decimal("Peso (kg)", maximo=500),
            volumen_dm3=c.pedir_decimal("Volumen (dm³ = litros)", maximo=2000),
        )
        c.exito(f"Paquete creado con ID {paquete.id}.")

    def modificar(self) -> None:
        c.subtitulo("Modificar paquete  (Enter conserva el valor, x cancela)")
        paquete = self._servicio.obtener(c.pedir_entero("ID del paquete", minimo=1))
        paquete.descripcion = c.pedir_texto("Descripción", paquete.descripcion)
        paquete.destinatario = c.pedir_texto("Destinatario", paquete.destinatario)
        paquete.direccion = c.pedir_texto("Dirección", paquete.direccion)
        paquete.zona = c.pedir_opcion_enum("Zona", Zona, paquete.zona)
        paquete.peso_kg = c.pedir_decimal("Peso (kg)", paquete.peso_kg, maximo=500)
        paquete.volumen_dm3 = c.pedir_decimal("Volumen (dm³)", paquete.volumen_dm3, maximo=2000)
        self._servicio.modificar(paquete)
        c.exito(f"Paquete {paquete.id} actualizado.")

    def baja(self) -> None:
        c.subtitulo("Baja de paquete  (x para cancelar)")
        paquete = self._servicio.obtener(c.pedir_entero("ID del paquete", minimo=1))
        if c.confirmar(f"¿Eliminar '{paquete.descripcion}' para {paquete.destinatario}?"):
            self._servicio.eliminar(paquete.id)
            c.exito("Paquete eliminado.")
        else:
            c.info("Operación cancelada.")
