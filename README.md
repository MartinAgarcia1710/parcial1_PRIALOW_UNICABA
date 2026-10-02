# Plataforma de Gestión Logística

**TP 1 — Elementos de Programación IA y Low Code (2C2026)**
Aplicación de consola en Python para gestionar paquetes, repartidores y repartos en 4 zonas del AMBA, con POO, patrón Repositorio sobre CSV, clima en tiempo real (Open-Meteo) e indicadores con pandas y matplotlib.

> La bitácora del uso de IA durante el desarrollo está en [`README_IA.md`](README_IA.md).

---

## Instalación y ejecución

```powershell
# 1. Crear y activar el entorno virtual (Windows)
python -m venv venv
venv\Scripts\activate

# 2. Instalar dependencias
pip install -r requirements.txt

# 3. Ejecutar la app (desde la raíz del proyecto)
python main.py

# 4. Ejecutar las pruebas automáticas
python -m unittest -v
```

**Para la demo:** en el menú principal, opción **5 · Cargar datos de ejemplo**. Genera 8 repartidores y 36 paquetes, los asigna automáticamente y avanza algunos estados, así las estadísticas tienen datos desde el primer minuto. Usa una semilla fija: siempre genera el mismo escenario.

---

## Funcionalidades

| Menú | Opciones |
| :--- | :--- |
| **1 · Paquetes** | Listar (con estado y repartidor), listar por zona, alta, modificación, baja |
| **2 · Repartidores** | Listar con carga y % de ocupación, alta, modificación, baja |
| **3 · Asignación y repartos** | Ver pendientes, asignación manual (con validación de zona, peso y volumen), asignación automática *greedy*, listar repartos, cambiar estado, ver clima por zona, **simular caída de la API** |
| **4 · Estadísticas** | 3 KPIs en tablas pandas + tablero de 3 gráficos matplotlib (se guarda en `reportes/estadisticas.png`) |
| **5 · Datos de ejemplo** | Seeder reproducible |

En cualquier carga se puede escribir **`x`** para cancelar; en las modificaciones, **Enter** conserva el valor actual.

---

## Arquitectura

```
├── main.py                      # Punto de entrada
├── analisis.ipynb               # Notebook de análisis (reutiliza src/)
├── requirements.txt
├── data/                        # CSV generados automáticamente
├── reportes/                    # Gráficos exportados
├── tests/test_logistica.py      # 21 pruebas con unittest
└── src/
    ├── config.py                # Rutas, tarifas, parámetros de la API
    ├── exceptions.py            # Jerarquía de excepciones propias (LogisticaError)
    ├── models/                  # Dominio puro (dataclasses + Enums)
    │   ├── entidad.py           #   Contrato abstracto: id, to_dict, from_dict
    │   ├── zona.py              #   Zona, EstadoReparto, TipoVehiculo
    │   ├── paquete.py · repartidor.py · reparto.py
    ├── repositories/            # Persistencia CSV
    │   ├── base_repository.py   #   BaseRepository[T] genérico (Generic + TypeVar)
    │   └── paquete_ · repartidor_ · reparto_repository.py
    ├── services/                # Lógica de negocio
    │   ├── clima_service.py     #   Open-Meteo + caché + fallback offline
    │   ├── asignacion_service.py#   Validaciones, greedy, ciclo de estados
    │   ├── estadisticas_service.py # KPIs pandas + gráficos matplotlib
    │   ├── paquete_service.py · repartidor_service.py  # Reglas del ABM
    │   └── seeder_service.py    #   Datos de ejemplo
    └── views/                   # Consola (colorama + readchar)
        ├── consola.py           #   Entradas validadas, colores, tablas
        ├── app.py               #   Menú principal y composición de dependencias
        └── menu_*.py            #   Un submenú por módulo
```

Las capas solo dependen hacia abajo: **views → services → repositories → models**. Las vistas no tocan los CSV y los modelos no saben nada de archivos ni de la consola.

---

## Reglas de negocio

**Vehículos y capacidad**

| Vehículo | Peso máx. | Volumen máx. |
| :--- | ---: | ---: |
| Moto | 25 kg | 90 dm³ |
| Auto | 120 kg | 400 dm³ |
| Camioneta | 500 kg | 2000 dm³ |

- Un paquete solo puede asignarse a un repartidor **de su misma zona** y si entra **sumado a la carga activa** (repartos pendientes + en camino).
- **Un reparto = un paquete** (1 a 1). Un repartidor tiene N repartos. Así el CSV queda normalizado (sin listas dentro de una celda).
- Estados: `Pendiente → En camino → Entregado`; desde Pendiente o En camino se puede pasar a `Cancelado`. Cancelar libera la capacidad y el paquete vuelve a quedar sin asignar.
- No se pueden borrar paquetes ni repartidores con repartos registrados, ni modificar un paquete con reparto vigente.

**Costo de un envío**

```
costo_base  = tarifa base de la zona + $150 × kg + $8 × dm³
costo_total = costo_base × (1 + recargo_clima % / 100)
```

Tarifa base: CABA $1.800 · Zona Norte $2.500 · Zona Oeste $2.300 · Zona Sur $2.400.

**Recargo por clima (Open-Meteo, sin API key)**

Se consulta el clima actual de una localidad de referencia por zona: Obelisco (CABA), San Isidro (Norte), Morón (Oeste) y Lomas de Zamora (Sur).

| Condición (código WMO) | Recargo |
| :--- | ---: |
| Tormenta (95–99) | +25 % |
| Lluvia, llovizna, chaparrones o nieve (51–86) o precipitación > 0 | +15 % |
| Viento ≥ 40 km/h | +10 % (acumulable) |
| **API caída / sin conexión** | **+10 % (recargo base)** |

La respuesta se guarda en caché 10 minutos para no consultar la API por cada paquete. Si falla (timeout de 4 s, sin red, respuesta inválida), la app **no se corta**: aplica el recargo base y lo avisa. La opción *Simular caída de la API* permite mostrarlo en la defensa sin desconectar el wifi.

**Asignación automática — Best-Fit Decreasing (greedy)**

1. Ordena los paquetes sin asignar de mayor a menor peso.
2. Para cada uno, filtra los repartidores de su zona donde entra (peso **y** volumen).
3. Elige el que queda con **menos capacidad libre** después de cargarlo, para llenar vehículos y reservar los grandes para paquetes pesados.

No garantiza el óptimo (sería una mochila multidimensional, un problema NP-difícil), pero es O(n·m) y fácil de justificar.

---

## Indicadores (KPIs)

| KPI | Cálculo |
| :--- | :--- |
| **1. Tasa de ocupación** | Por repartidor: `máx(carga_kg / cap_kg, carga_dm³ / cap_dm³) × 100` (la dimensión limitante). Global ponderada: `Σ carga_kg / Σ cap_kg × 100`. |
| **2. Costo medio por zona** | `Σ costo_total / cantidad de repartos` agrupado por zona (sin cancelados), más el total y el recargo promedio. |
| **3. Distribución de estados** | Cantidad y porcentaje de repartos en cada estado. |

---

## Tecnologías y conceptos aplicados

POO con `dataclasses` y clases abstractas (`ABC`) · `Enum` con propiedades · tipado (`Generic`, `TypeVar`, `Self`, `X | None`) · patrón Repositorio · inyección de dependencias por constructor · excepciones propias · `pandas` (merge, groupby, agg, reindex, value_counts) · `matplotlib` · `requests` contra una API REST · `colorama` y `readchar` · `unittest` con dobles de prueba para la API.
