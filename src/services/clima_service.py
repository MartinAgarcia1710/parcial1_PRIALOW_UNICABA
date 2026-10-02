"""Consulta del clima actual por zona con Open-Meteo (sin API key) y tolerancia a fallos."""

import time
from dataclasses import dataclass
from typing import Any, Callable

import requests

from src.config import (
    CLIMA_CACHE_SEG, CLIMA_TIMEOUT_SEG, OPEN_METEO_URL, RECARGO_FALLBACK_PCT,
    RECARGO_LLUVIA_PCT, RECARGO_TORMENTA_PCT, RECARGO_VIENTO_PCT, VIENTO_FUERTE_KMH,
)
from src.models.zona import Zona


@dataclass(frozen=True)
class Clima:
    zona: Zona
    descripcion: str
    temperatura_c: float | None
    precipitacion_mm: float | None
    viento_kmh: float | None
    recargo_pct: float
    es_fallback: bool = False

    @property
    def resumen(self) -> str:
        """Texto corto que se guarda en el reparto."""
        if self.es_fallback:
            return "Sin datos (offline)"
        return f"{self.descripcion} {self.temperatura_c:.0f}°C"


# Códigos WMO que devuelve Open-Meteo en `weather_code`
_DESCRIPCIONES_WMO: dict[int, str] = {
    0: "Despejado", 1: "Mayormente despejado", 2: "Parcialmente nublado", 3: "Nublado",
    45: "Niebla", 48: "Niebla con escarcha",
    51: "Llovizna leve", 53: "Llovizna", 55: "Llovizna intensa",
    56: "Llovizna helada", 57: "Llovizna helada intensa",
    61: "Lluvia leve", 63: "Lluvia", 65: "Lluvia intensa",
    66: "Lluvia helada", 67: "Lluvia helada intensa",
    71: "Nevada leve", 73: "Nevada", 75: "Nevada intensa", 77: "Granizo fino",
    80: "Chaparrones leves", 81: "Chaparrones", 82: "Chaparrones violentos",
    85: "Chaparrones de nieve", 86: "Chaparrones de nieve intensos",
    95: "Tormenta", 96: "Tormenta con granizo", 99: "Tormenta con granizo intenso",
}


def calcular_recargo(codigo: int, precipitacion_mm: float, viento_kmh: float) -> float:
    """Regla de negocio del recargo por clima (en %).

    - Tormenta (códigos 95-99): +25 %
    - Lluvia, llovizna, chaparrones o nieve (códigos 51-86) o precipitación > 0: +15 %
    - Viento >= 40 km/h: +10 % adicional (acumulable)
    """
    recargo = 0.0
    if codigo >= 95:
        recargo += RECARGO_TORMENTA_PCT
    elif 51 <= codigo <= 86 or precipitacion_mm > 0:
        recargo += RECARGO_LLUVIA_PCT
    if viento_kmh >= VIENTO_FUERTE_KMH:
        recargo += RECARGO_VIENTO_PCT
    return recargo


HttpGet = Callable[..., Any]
FALLBACK_CACHE_SEG = 60


class ClimaService:
    """Obtiene el clima de cada zona, con caché en memoria y modo offline.

    Si la API falla (sin conexión, timeout, respuesta inválida) no se corta la
    aplicación: se devuelve un clima "fallback" con un recargo base conservador.
    """

    def __init__(self, http_get: HttpGet = requests.get, cache_seg: int = CLIMA_CACHE_SEG) -> None:
        self._http_get = http_get
        self._cache_seg = cache_seg
        # zona -> (momento de vencimiento, clima)
        self._cache: dict[Zona, tuple[float, Clima]] = {}
        self.modo_offline = False  # permite simular la caída de la API en la defensa
        self.ultimo_error: str | None = None

    def obtener_clima(self, zona: Zona) -> Clima:
        if self.modo_offline:
            self.ultimo_error = "Modo offline activado manualmente."
            return self._fallback(zona)

        en_cache = self._cache.get(zona)
        if en_cache and time.monotonic() < en_cache[0]:
            return en_cache[1]

        try:
            clima = self._consultar_api(zona)
            vigencia = self._cache_seg
            self.ultimo_error = None
        except (requests.RequestException, KeyError, ValueError, TypeError) as e:
            self.ultimo_error = f"{type(e).__name__}: {e}"
            clima = self._fallback(zona)
            # El fallback se guarda poco tiempo: evita esperar el timeout por cada
            # paquete en una asignación masiva, pero se reintenta al minuto.
            vigencia = FALLBACK_CACHE_SEG

        self._cache[zona] = (time.monotonic() + vigencia, clima)
        return clima

    def obtener_todas(self) -> list[Clima]:
        return [self.obtener_clima(zona) for zona in Zona]

    def alternar_modo_offline(self) -> bool:
        """Activa/desactiva la simulación de caída de la API. Devuelve el nuevo estado."""
        self.modo_offline = not self.modo_offline
        self.limpiar_cache()
        return self.modo_offline

    def limpiar_cache(self) -> None:
        self._cache.clear()

    # --- privados -----------------------------------------------------------------
    def _consultar_api(self, zona: Zona) -> Clima:
        lat, lon = zona.coordenadas
        respuesta = self._http_get(
            OPEN_METEO_URL,
            params={
                "latitude": lat,
                "longitude": lon,
                "current": "temperature_2m,precipitation,weather_code,wind_speed_10m",
                "timezone": "America/Argentina/Buenos_Aires",
            },
            timeout=CLIMA_TIMEOUT_SEG,
        )
        respuesta.raise_for_status()
        actual = respuesta.json()["current"]

        codigo = int(actual["weather_code"])
        temperatura = float(actual["temperature_2m"])
        precipitacion = float(actual["precipitation"])
        viento = float(actual["wind_speed_10m"])
        return Clima(
            zona=zona,
            descripcion=_DESCRIPCIONES_WMO.get(codigo, f"Código {codigo}"),
            temperatura_c=temperatura,
            precipitacion_mm=precipitacion,
            viento_kmh=viento,
            recargo_pct=calcular_recargo(codigo, precipitacion, viento),
        )

    @staticmethod
    def _fallback(zona: Zona) -> Clima:
        return Clima(
            zona=zona,
            descripcion="Sin datos (offline)",
            temperatura_c=None,
            precipitacion_mm=None,
            viento_kmh=None,
            recargo_pct=RECARGO_FALLBACK_PCT,
            es_fallback=True,
        )
