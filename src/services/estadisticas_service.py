"""Indicadores (KPIs) con pandas y gráficos con matplotlib."""

from pathlib import Path

import matplotlib
import matplotlib.pyplot as plt
import pandas as pd

from src.config import REPORTES_DIR
from src.models.zona import EstadoReparto, Zona
from src.repositories.paquete_repository import PaqueteRepository
from src.repositories.repartidor_repository import RepartidorRepository
from src.repositories.reparto_repository import RepartoRepository
from src.services.asignacion_service import AsignacionService

ORDEN_ZONAS = [z.value for z in Zona]
ORDEN_ESTADOS = [e.value for e in EstadoReparto]
COLORES_ESTADO = {
    "Pendiente": "#E8A33D",
    "En camino": "#3B82C4",
    "Entregado": "#3FA66B",
    "Cancelado": "#C2504A",
}


class EstadisticasService:
    def __init__(self, paquetes: PaqueteRepository, repartidores: RepartidorRepository,
                 repartos: RepartoRepository, asignacion: AsignacionService) -> None:
        self._paquetes = paquetes
        self._repartidores = repartidores
        self._repartos = repartos
        self._asignacion = asignacion

    # --- DataFrames base -------------------------------------------------------
    def df_paquetes(self) -> pd.DataFrame:
        """Paquetes con el estado de su envío y el repartidor asignado."""
        columnas = ["id", "descripcion", "destinatario", "direccion", "zona", "peso_kg", "volumen_dm3"]
        df = pd.DataFrame([p.to_dict() for p in self._paquetes.get_all()], columns=columnas)
        df = df.astype({"id": int, "peso_kg": float, "volumen_dm3": float})

        repartos = self.df_repartos()
        vigentes = repartos[repartos["estado"] != EstadoReparto.CANCELADO.value]
        vigentes = vigentes[["paquete_id", "estado", "repartidor"]].rename(columns={"paquete_id": "id"})
        df = df.merge(vigentes, on="id", how="left")
        df["estado"] = df["estado"].fillna("Sin asignar")
        df["repartidor"] = df["repartidor"].fillna("-")
        return df

    def df_repartidores(self) -> pd.DataFrame:
        """Repartidores con su carga activa y porcentaje de ocupación."""
        cargas = self._asignacion.cargas_actuales()
        filas = []
        for r in self._repartidores.get_all():
            carga = cargas.get(r.id)
            filas.append({
                "id": r.id,
                "nombre": r.nombre,
                "telefono": r.telefono,
                "zona": r.zona.value,
                "vehiculo": r.vehiculo.value,
                "cap_peso_kg": r.capacidad_peso_kg,
                "cap_vol_dm3": r.capacidad_volumen_dm3,
                "carga_kg": round(carga.peso_kg, 2) if carga else 0.0,
                "carga_dm3": round(carga.volumen_dm3, 2) if carga else 0.0,
                "paquetes_activos": carga.cantidad if carga else 0,
            })
        df = pd.DataFrame(filas, columns=[
            "id", "nombre", "telefono", "zona", "vehiculo", "cap_peso_kg", "cap_vol_dm3",
            "carga_kg", "carga_dm3", "paquetes_activos",
        ])
        df["ocup_peso_%"] = (df["carga_kg"] / df["cap_peso_kg"] * 100).round(1)
        df["ocup_vol_%"] = (df["carga_dm3"] / df["cap_vol_dm3"] * 100).round(1)
        # La ocupación efectiva es la dimensión que limita (la que está más llena)
        df["ocupacion_%"] = df[["ocup_peso_%", "ocup_vol_%"]].max(axis=1)
        return df

    def df_repartos(self) -> pd.DataFrame:
        """Repartos con el nombre del repartidor y la descripción del paquete."""
        columnas = ["id", "paquete_id", "repartidor_id", "zona", "fecha", "costo_base",
                    "recargo_pct", "costo_total", "clima", "estado"]
        df = pd.DataFrame([r.to_dict() for r in self._repartos.get_all()], columns=columnas)
        df = df.astype({"id": int, "paquete_id": int, "repartidor_id": int,
                        "costo_base": float, "recargo_pct": float, "costo_total": float})
        nombres = {r.id: r.nombre for r in self._repartidores.get_all()}
        paquetes = {p.id: p.descripcion for p in self._paquetes.get_all()}
        df["repartidor"] = df["repartidor_id"].map(nombres).fillna("(eliminado)")
        df["paquete"] = df["paquete_id"].map(paquetes).fillna("(eliminado)")
        return df

    # --- KPI 1: tasa de ocupación de repartidores ------------------------------
    def kpi_ocupacion(self) -> tuple[pd.DataFrame, float]:
        """Ocupación por repartidor y tasa global ponderada por capacidad.

        Por repartidor: ocupación = max(carga_kg / cap_kg, carga_dm3 / cap_dm3) × 100
        Global (ponderada): Σ carga_kg / Σ cap_kg × 100  → un camión pesa más que una moto.
        """
        df = self.df_repartidores()
        tabla = df[["nombre", "zona", "vehiculo", "paquetes_activos", "carga_kg",
                    "cap_peso_kg", "ocup_peso_%", "ocup_vol_%", "ocupacion_%"]]
        tabla = tabla.sort_values("ocupacion_%", ascending=False).reset_index(drop=True)
        capacidad_total = df["cap_peso_kg"].sum()
        global_pct = float(round(df["carga_kg"].sum() / capacidad_total * 100, 1)) if capacidad_total else 0.0
        return tabla, global_pct

    # --- KPI 2: costo medio por zona -------------------------------------------
    def kpi_costo_por_zona(self) -> pd.DataFrame:
        """Costo promedio, total y recargo medio por zona (excluye repartos cancelados).

        costo_promedio(zona) = Σ costo_total / cantidad de repartos de la zona
        """
        df = self.df_repartos()
        df = df[df["estado"] != EstadoReparto.CANCELADO.value]
        tabla = (
            df.groupby("zona")
            .agg(repartos=("id", "count"),
                 costo_promedio=("costo_total", "mean"),
                 costo_total=("costo_total", "sum"),
                 recargo_prom_pct=("recargo_pct", "mean"))
            .reindex(ORDEN_ZONAS)  # muestra las 4 zonas aunque alguna no tenga repartos
            .fillna({"repartos": 0, "costo_total": 0.0})
            .round(2)
        )
        tabla["repartos"] = tabla["repartos"].astype(int)
        return tabla.rename_axis("zona").reset_index()

    # --- KPI 3: distribución de estados ----------------------------------------
    def kpi_estados(self) -> pd.DataFrame:
        """Cantidad y porcentaje de repartos en cada estado."""
        df = self.df_repartos()
        conteo = df["estado"].value_counts().reindex(ORDEN_ESTADOS, fill_value=0)
        total = int(conteo.sum())
        tabla = pd.DataFrame({
            "estado": conteo.index,
            "cantidad": conteo.values,
            "porcentaje": (conteo.values / total * 100).round(1) if total else 0.0,
        })
        return tabla

    # --- Resumen ---------------------------------------------------------------
    def resumen(self) -> dict[str, float | int]:
        paquetes = self.df_paquetes()
        repartos = self.df_repartos()
        no_cancelados = repartos[repartos["estado"] != EstadoReparto.CANCELADO.value]
        _, ocupacion_global = self.kpi_ocupacion()
        return {
            "paquetes": len(paquetes),
            "sin_asignar": int((paquetes["estado"] == "Sin asignar").sum()),
            "repartidores": len(self._repartidores.get_all()),
            "repartos": len(repartos),
            "ocupacion_global_%": float(ocupacion_global),
            "facturacion_total": round(float(no_cancelados["costo_total"].sum()), 2),
            "recargo_clima_prom_%": round(float(no_cancelados["recargo_pct"].mean()), 1)
            if len(no_cancelados) else 0.0,
        }

    # --- Gráficos --------------------------------------------------------------
    def generar_graficos(self, ruta: Path | None = None) -> Path:
        """Arma un tablero con los 3 KPIs y lo guarda como PNG. Devuelve la ruta."""
        ocupacion, global_pct = self.kpi_ocupacion()
        costos = self.kpi_costo_por_zona()
        estados = self.kpi_estados()

        fig, (ax1, ax2, ax3) = plt.subplots(1, 3, figsize=(17, 5.8))
        fig.suptitle("Plataforma Logística — Indicadores", fontsize=15, fontweight="bold")

        # 1) Ocupación por repartidor (barras horizontales)
        ocup = ocupacion.sort_values("ocupacion_%")
        etiquetas = [f"{n} ({v})" for n, v in zip(ocup["nombre"], ocup["vehiculo"])]
        colores = ["#C2504A" if v >= 90 else "#E8A33D" if v >= 60 else "#3FA66B"
                   for v in ocup["ocupacion_%"]]
        ax1.barh(etiquetas, ocup["ocupacion_%"], color=colores)
        ax1.axvline(global_pct, color="#444", linestyle="--", linewidth=1)
        ax1.text(global_pct, len(ocup) - 0.5, f" global por peso {global_pct:.0f}%", fontsize=8, va="bottom")
        ax1.set_xlim(0, 105)
        ax1.set_xlabel("% de ocupación (dimensión limitante)")
        ax1.set_title("Ocupación por repartidor")
        ax1.tick_params(axis="y", labelsize=8)

        # 2) Costo medio por zona
        valores = costos["costo_promedio"].fillna(0)
        barras = ax2.bar(costos["zona"], valores, color="#3B82C4")
        for barra, valor, cant in zip(barras, valores, costos["repartos"]):
            ax2.annotate(f"${valor:,.0f}".replace(",", ".") + f"\n({cant} rep.)", (barra.get_x() + barra.get_width() / 2, valor),
                         ha="center", va="bottom", fontsize=8)
        ax2.set_ylabel("Costo promedio por envío ($)")
        ax2.set_title("Costo medio por zona")
        ax2.set_ylim(0, max(valores.max() * 1.25, 1))

        # 3) Distribución de estados
        con_datos = estados[estados["cantidad"] > 0]
        if con_datos.empty:
            ax3.text(0.5, 0.5, "Sin repartos", ha="center", va="center")
            ax3.axis("off")
        else:
            ax3.pie(con_datos["cantidad"], labels=con_datos["estado"], autopct="%1.0f%%",
                    colors=[COLORES_ESTADO[e] for e in con_datos["estado"]], startangle=90,
                    wedgeprops={"edgecolor": "white"})
        ax3.set_title("Distribución de estados de repartos")

        fig.tight_layout()
        destino = ruta or REPORTES_DIR / "estadisticas.png"
        destino.parent.mkdir(parents=True, exist_ok=True)
        fig.savefig(destino, dpi=120)
        self._ultima_figura = fig
        return destino

    def mostrar_graficos(self) -> None:
        """Abre la ventana de matplotlib (si el backend es interactivo)."""
        if matplotlib.get_backend().lower() == "agg":
            plt.close("all")
            return
        plt.show()
        plt.close("all")
