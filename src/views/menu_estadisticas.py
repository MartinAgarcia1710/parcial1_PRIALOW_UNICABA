"""Pantalla de indicadores y gráficos."""

from src.services.estadisticas_service import EstadisticasService
from src.views import consola as c


class MenuEstadisticas:
    def __init__(self, estadisticas: EstadisticasService) -> None:
        self._estadisticas = estadisticas

    def ejecutar(self) -> None:
        acciones = {"1": self.ver_indicadores, "2": self.ver_graficos}
        while True:
            c.limpiar()
            opcion = c.menu({
                "1": "Ver indicadores (tablas)",
                "2": "Ver gráficos (matplotlib)",
                "0": "Volver",
            }, "ESTADÍSTICAS")
            if opcion == "0":
                return
            c.ejecutar_accion(acciones[opcion])

    def ver_indicadores(self) -> None:
        r = self._estadisticas.resumen()
        c.subtitulo("Resumen general")
        print(f"  Paquetes: {r['paquetes']}  (sin asignar: {r['sin_asignar']})   "
              f"Repartidores: {r['repartidores']}   Repartos: {r['repartos']}")
        print(f"  Facturación (sin cancelados): {c.moneda(float(r['facturacion_total']))}   "
              f"Recargo promedio por clima: {r['recargo_clima_prom_%']} %")

        tabla, global_pct = self._estadisticas.kpi_ocupacion()
        c.subtitulo(f"KPI 1 · Tasa de ocupación de repartidores  (global ponderada: {global_pct} %)")
        c.mostrar_tabla(tabla)
        c.info("ocupación = máx(carga kg / capacidad kg, carga dm³ / capacidad dm³) · solo repartos activos")

        c.subtitulo("KPI 2 · Costo medio por zona (excluye cancelados)")
        c.mostrar_tabla(self._estadisticas.kpi_costo_por_zona())

        c.subtitulo("KPI 3 · Distribución de estados de los repartos")
        c.mostrar_tabla(self._estadisticas.kpi_estados())

    def ver_graficos(self) -> None:
        ruta = self._estadisticas.generar_graficos()
        c.exito(f"Gráfico guardado en {ruta}")
        c.info("Se abre la ventana de matplotlib; cerrala para volver al menú.")
        self._estadisticas.mostrar_graficos()
