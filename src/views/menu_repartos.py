"""Menú de asignación de paquetes, repartos y clima."""

import pandas as pd

from src.models.zona import EstadoReparto
from src.services.asignacion_service import AsignacionService, calcular_costo_base
from src.services.clima_service import ClimaService
from src.services.estadisticas_service import EstadisticasService
from src.views import consola as c


class MenuRepartos:
    def __init__(self, asignacion: AsignacionService, clima: ClimaService,
                 estadisticas: EstadisticasService) -> None:
        self._asignacion = asignacion
        self._clima = clima
        self._estadisticas = estadisticas

    def ejecutar(self) -> None:
        acciones = {
            "1": self.ver_sin_asignar,
            "2": self.asignar_manual,
            "3": self.asignar_automatico,
            "4": self.listar_repartos,
            "5": self.cambiar_estado,
            "6": self.ver_clima,
            "7": self.alternar_offline,
        }
        while True:
            c.limpiar()
            estado_api = "OFFLINE (simulado)" if self._clima.modo_offline else "online"
            opcion = c.menu({
                "1": "Ver paquetes sin asignar",
                "2": "Asignar paquete manualmente",
                "3": "Asignación automática (greedy)",
                "4": "Listar repartos",
                "5": "Cambiar estado de un reparto",
                "6": "Ver clima por zona",
                "7": f"Simular caída de la API de clima  [API: {estado_api}]",
                "0": "Volver",
            }, "ASIGNACIÓN Y REPARTOS")
            if opcion == "0":
                return
            c.ejecutar_accion(acciones[opcion])

    def ver_sin_asignar(self) -> None:
        c.subtitulo("Paquetes sin asignar")
        filas = [{
            "id": p.id, "descripcion": p.descripcion, "zona": p.zona.value,
            "peso_kg": p.peso_kg, "volumen_dm3": p.volumen_dm3,
            "costo_base": calcular_costo_base(p),
        } for p in self._asignacion.paquetes_sin_asignar()]
        c.mostrar_tabla(pd.DataFrame(filas), "Todos los paquetes tienen un reparto vigente.")

    def asignar_manual(self) -> None:
        c.subtitulo("Asignación manual  (x para cancelar)")
        self.ver_sin_asignar()
        paquete_id = c.pedir_entero("\n  ID del paquete", minimo=1)

        paquete = next((p for p in self._asignacion.paquetes_sin_asignar() if p.id == paquete_id), None)
        if paquete:  # si no está en la lista, `asignar` informa el motivo exacto
            disponibles = self._asignacion.repartidores_disponibles(paquete)
            cargas = self._asignacion.cargas_actuales()
            if disponibles:
                c.info(f"\nRepartidores de {paquete.zona} con lugar para este paquete:")
                c.mostrar_tabla(pd.DataFrame([{
                    "id": r.id, "nombre": r.nombre, "vehiculo": r.vehiculo.value,
                    "libre_kg": round(r.capacidad_peso_kg - cargas[r.id].peso_kg, 2),
                    "libre_dm3": round(r.capacidad_volumen_dm3 - cargas[r.id].volumen_dm3, 2),
                } for r in disponibles]))
            else:
                c.advertencia(f"Ningún repartidor de {paquete.zona} tiene lugar para este paquete.")

        repartidor_id = c.pedir_entero("\n  ID del repartidor", minimo=1)
        reparto = self._asignacion.asignar(paquete_id, repartidor_id)
        self._informar_reparto_creado(reparto.id, reparto.clima, reparto.recargo_pct, reparto.costo_total)

    def asignar_automatico(self) -> None:
        c.subtitulo("Asignación automática (Best-Fit Decreasing)")
        if not self._asignacion.paquetes_sin_asignar():
            c.advertencia("No hay paquetes pendientes de asignar.")
            return
        if not c.confirmar("¿Asignar automáticamente todos los paquetes pendientes?"):
            c.info("Operación cancelada.")
            return
        resultado = self._asignacion.asignar_automatico()
        self._avisar_si_fallback()

        if resultado.asignados:
            c.exito(f"{len(resultado.asignados)} paquete(s) asignado(s):")
            nombres = self._asignacion.nombres_repartidores()
            c.mostrar_tabla(pd.DataFrame([{
                "reparto": r.id, "paquete": r.paquete_id, "repartidor": nombres.get(r.repartidor_id, "?"),
                "zona": r.zona.value, "clima": r.clima, "recargo_%": r.recargo_pct,
                "costo_total": r.costo_total,
            } for r in resultado.asignados]))
        if resultado.no_asignados:
            print()
            c.advertencia(f"{len(resultado.no_asignados)} paquete(s) sin asignar:")
            c.mostrar_tabla(pd.DataFrame([{
                "paquete": p.id, "descripcion": p.descripcion, "zona": p.zona.value,
                "peso_kg": p.peso_kg, "motivo": motivo,
            } for p, motivo in resultado.no_asignados]))

    def listar_repartos(self) -> None:
        c.subtitulo("Repartos")
        df = self._estadisticas.df_repartos()
        c.mostrar_tabla(df[["id", "paquete_id", "paquete", "repartidor", "zona", "fecha",
                            "clima", "recargo_pct", "costo_total", "estado"]])

    def cambiar_estado(self) -> None:
        c.subtitulo("Cambiar estado  (x para cancelar)")
        activos = self._estadisticas.df_repartos()
        activos = activos[activos["estado"].isin([EstadoReparto.PENDIENTE.value, EstadoReparto.EN_CAMINO.value])]
        c.mostrar_tabla(activos[["id", "paquete", "repartidor", "zona", "estado"]],
                        "No hay repartos pendientes ni en camino.")
        if activos.empty:
            return
        reparto_id = c.pedir_entero("\n  ID del reparto", minimo=1)
        actual = self._asignacion.obtener_reparto(reparto_id).estado
        posibles = list(actual.transiciones_validas())
        if not posibles:
            c.advertencia(f"El reparto está {actual} y ya no admite cambios.")
            return
        nuevo = c.pedir_opcion_enum(f"Nuevo estado (actual: {actual})", EstadoReparto, opciones=posibles)
        self._asignacion.cambiar_estado(reparto_id, nuevo)
        c.exito(f"Reparto {reparto_id}: {actual} → {nuevo}.")
        if nuevo == EstadoReparto.CANCELADO:
            c.info("El paquete quedó libre para volver a asignarse.")

    def ver_clima(self) -> None:
        c.subtitulo("Clima actual por zona (Open-Meteo)")
        filas = []
        for clima in self._clima.obtener_todas():
            filas.append({
                "zona": clima.zona.value,
                "referencia": clima.zona.referencia,
                "condicion": clima.descripcion,
                "temp_°C": "-" if clima.temperatura_c is None else round(clima.temperatura_c, 1),
                "lluvia_mm": "-" if clima.precipitacion_mm is None else clima.precipitacion_mm,
                "viento_kmh": "-" if clima.viento_kmh is None else clima.viento_kmh,
                "recargo_%": clima.recargo_pct,
            })
        c.mostrar_tabla(pd.DataFrame(filas))
        self._avisar_si_fallback()
        c.info("\nRegla: tormenta +25 % | lluvia/llovizna/nieve +15 % | viento ≥ 40 km/h +10 % | "
               "sin datos +10 %")

    def alternar_offline(self) -> None:
        if self._clima.alternar_modo_offline():
            c.advertencia("Modo OFFLINE activado: se usará el recargo base sin consultar la API.")
        else:
            c.exito("Modo online: se vuelve a consultar Open-Meteo.")

    # --- auxiliares -------------------------------------------------------------
    def _avisar_si_fallback(self) -> None:
        if self._clima.ultimo_error:
            c.advertencia(f"No se pudo consultar el clima, se aplicó el recargo base. "
                          f"Detalle: {self._clima.ultimo_error[:120]}")

    def _informar_reparto_creado(self, reparto_id: int, clima: str, recargo: float, total: float) -> None:
        self._avisar_si_fallback()
        c.exito(f"Reparto {reparto_id} creado. Clima: {clima} | recargo {recargo:g} % | "
                f"total {c.moneda(total)}")
