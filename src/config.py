"""Configuración centralizada: rutas, tarifas y parámetros de la API de clima."""

from pathlib import Path
from typing import Final

# --- Rutas -------------------------------------------------------------------
RAIZ_PROYECTO: Final[Path] = Path(__file__).resolve().parent.parent
DATA_DIR: Final[Path] = RAIZ_PROYECTO / "data"
REPORTES_DIR: Final[Path] = RAIZ_PROYECTO / "reportes"

# --- Tarifas (en pesos argentinos) ----------------------------------------------
# La tarifa base por zona se define en el Enum Zona (src/models/zona.py).
COSTO_POR_KG: Final[float] = 150.0
COSTO_POR_DM3: Final[float] = 8.0

# --- API de clima (Open-Meteo, sin API key) -----------------------------------
OPEN_METEO_URL: Final[str] = "https://api.open-meteo.com/v1/forecast"
CLIMA_TIMEOUT_SEG: Final[float] = 4.0
CLIMA_CACHE_SEG: Final[int] = 600  # 10 minutos: no se consulta la API por cada paquete

# Recargos por clima (porcentaje sobre el costo base del envío)
RECARGO_TORMENTA_PCT: Final[float] = 25.0
RECARGO_LLUVIA_PCT: Final[float] = 15.0
RECARGO_VIENTO_PCT: Final[float] = 10.0
VIENTO_FUERTE_KMH: Final[float] = 40.0
# Si la API no responde se aplica un recargo base conservador (modo offline)
RECARGO_FALLBACK_PCT: Final[float] = 10.0
