# Registro de Asistencia con Inteligencia Artificial

**Materia:** Elementos de Programación IA y Low Code (2C2026)  
**Trabajo Práctico:** TP 1 - Desarrollo de una aplicación en Python asistido por IA  
**Docente:** Esteban Calcagno  
**Proyecto:** Plataforma de Gestión Logística con POO y Patrón Repositorio  

---

## 1. Resumen de Decisiones y Criterios Adoptados

| Aspecto | Propuesta Inicial | Respuesta / Recomendación IA | Decisión Final |
| :--- | :--- | :--- | :--- |
| **Arquitectura de Dominio** | Evaluar el uso de Data Transfer Objects (DTO). | Descartar DTOs para evitar *boilerplate* y sobreingeniería en un entorno local sin red. | **Aceptada:** Se utilizan directamente las entidades de dominio tipadas. |
| **API de Clima** | Consultar un clima aleatorio de cualquier lugar del planeta. | Consultar coordenadas reales de Buenos Aires (Open-Meteo, sin token) y agregar tolerancia a fallos (`mock fallback`). | **Aceptada:** Permite coherencia de negocio y resiliencia en la demostración oral. |
| **Indicadores (KPIs)** | Dejar abiertos los 3 cálculos requeridos por la consigna. | Definir formalmente: tasa de ocupación de repartidores, costo medio por zona y distribución de estados. | **Aceptada:** Cumple explícitamente el requisito mínimo de 3 métricas. |
| **Patrón Repositorio** | Clases de persistencia para cada modelo en CSV. | Implementar un `BaseRepository[T]` genérico con `Generic` y `TypeVar` para reducir repetición de código I/O. | **Aceptada:** Buenas prácticas de diseño y tipado estricto. |
| **Relación Reparto–Paquete** | Un reparto "conecta paquetes con repartidores" (cardinalidad sin definir). | Un reparto por paquete (1 a 1) y N repartos por repartidor, para no guardar listas de IDs dentro de una celda CSV. | **Aceptada:** CSV normalizado; cada envío tiene su propio estado, costo y clima. |
| **Regla clima → costo** | Asignar un clima a cada zona (sin regla de impacto). | Coordenadas de una localidad por zona y recargo: tormenta +25 %, lluvia +15 %, viento ≥ 40 km/h +10 %, API caída +10 %. Caché de 10 min y timeout de 4 s. | **Aceptada:** El clima tiene un efecto medible en el KPI de costos. |
| **Algoritmo de asignación** | Asignación controlando peso/volumen (greedy o mochila sin decidir). | Greedy *Best-Fit Decreasing*: la mochila exacta en 2 dimensiones es NP-difícil y no se justifica. | **Aceptada:** O(n·m), simple de explicar en la defensa. |
| **Capacidad de repartidores** | Validar peso/volumen del paquete. | Capacidad definida por tipo de vehículo (Moto/Auto/Camioneta) y validación contra la **carga activa acumulada**, no solo contra el paquete. | **Aceptada.** |
| **Gráficos** | Dos gráficos en Matplotlib. | Un tablero con tres gráficos, uno por KPI (ocupación, costo por zona, estados). | **Aceptada:** cada KPI tiene su visualización. |
| **Capa de servicios ABM** | Las vistas llaman directamente a los repositorios. | Agregar `PaqueteService` y `RepartidorService` con reglas de integridad (no borrar con repartos registrados, no editar con reparto vigente). | **Aceptada:** las vistas no acceden a los repositorios. |
| **Pruebas** | Pruebas manuales previstas. | Suite `unittest` (21 pruebas) con una API de clima simulada para probar el fallback sin depender de la red. | **Aceptada.** |

---

## 2. Registro Cronológico de Prompts y Respuestas

### Prompt 1: Planteo del problema, alcance y solicitud de feedback arquitectónico
> **Usuario:**
> *Presenta la consigna del TP1 y expone la propuesta de arquitectura:*
> "Voy a desarrollar una plataforma para gestion de una logistica, pero voy usar Programacion orientada a objetos. Y voy a usar un pseudo patron repositorio separado en modulos y paquetes, todo modularizado al extremo. El Crud va a ser de paquetes, repartidores y reparto... Las zonas seran 4: CABA, Zona Norte, Zona Oeste y Zona Sur. Pienso en conectar alguna api de clima de uso libre para tomar un clima random de algun lugar del planeta y asignarlo a cada zona... El menu principal tendrá CRUD de paquetes y repartidores, Asignar paquetes (controlando peso/volumen) y Estadísticas (matplotlib)... Las tablas se verán con pandas en consola... Necesito un feedback, pasar en limpio, sugerencias y un esquema de carpetas."

> **Respuesta IA (Síntesis):**
> 1. **Evaluación de viabilidad:** Se validó la cobertura de los requisitos de la cátedra (pandas, matplotlib, typing, excepciones, API externa). Se alertó sobre el límite de tiempo de 5 minutos en la defensa oral, recomendando simplificar la entrada de datos (seeder) y descartar el uso de DTOs.
> 2. **Ajustes de alcance:** Reemplazo de la API aleatoria por **Open-Meteo** (sin API key, coordenadas de CABA/AMBA) con manejo de excepción fallback por si no hay conexión durante el examen. Definición clara de los 3 KPIs mínimos.
> 3. **Estructura modular propuesta:**
>    - `data/`: Archivos CSV.
>    - `src/models/`: Clases de dominio puras (`Paquete`, `Repartidor`, `Reparto`, `Zona`).
>    - `src/repositories/`: Persistencia I/O (`BaseRepository`, repositorios específicos).
>    - `src/services/`: Lógica de negocio (asignación greedy/mochila, API climática, pandas/kpis).
>    - `src/views/`: Menú interactivo y formato con `colorama`.
>    - Raíz: `main.py`, `analisis.ipynb`, `requirements.txt`, `README.md`.

---

### Prompt 2: Validación de sugerencias
> **Usuario:**
> "Estoy de acuerdo con lo que me propones. sobre todo lo de la api de clima y las estadisticas o resultados"

> **Respuesta IA (Síntesis):**
> - Se formalizó la consulta al endpoint de Open-Meteo (`https://api.open-meteo.com/v1/forecast?...`).
> - Se detallaron matemáticamente los 3 indicadores a calcular con `pandas` (Tasa de ocupación ponderada, costo promedio por zona y desglose de estados).
> - Se propuso el diseño visual con dos gráficos en Matplotlib.

---

### Prompt 3: Generación de la Capa de Modelos y Repositorios
> **Usuario:**
> "bien, para ahorrarme tiempo, pasame los models y repositories asi me enfoco en toda la funcionalidad"

> **Respuesta IA (Síntesis):**
> Se entregó el código estructurado en dos capas:
>
> 1. **Modelos (`src/models/`):**
>    - `zona.py`: Enums `Zona` y `EstadoReparto`.
>    - `paquete.py`: Dataclass `Paquete` con parseo y tipado completo.
>    - `repartidor.py`: Dataclass `Repartidor` con validación interna de capacidad (`puede_cargar`).
>    - `reparto.py`: Dataclass `Reparto` que conecta paquetes con repartidores, costo y estado.
>
> 2. **Repositorios (`src/repositories/`):**
>    - `base_repository.py`: Clase abstracta y genérica `BaseRepository[T]` que automatiza la creación de carpetas, lectura, escritura y parseo de diccionarios en archivos CSV con `try/except`.
>    - `paquete_repository.py`: CRUD e incremento autoincremental de IDs.
>    - `repartidor_repository.py`: CRUD e incremento autoincremental de IDs.
>    - `reparto_repository.py`: CRUD, búsqueda por repartidor/paquete y actualización de estados.

---

### Prompt 4: Solicitud de consolidación documental
> **Usuario:**
> "Los veo bien, no iba a usar genericos pero me parece correcto y de buenas practicas. Bueno, por ahora genera toda esta conversación en un "README_IA.md" asi ya lo documento y me pongo a trabajar en el resto. Cualquier cosa si surge algo te consulto"

> **Respuesta IA:**
> Creación del presente archivo `README_IA.md`.

---

### Prompt 5: Revisión del README_IA (Claude, Anthropic)
> **Usuario:**
> "Hola, voy a construir la app que detallo en el archivo "README_IA.md". Por favor revisalo y dame un feedback por el chat"

> **Respuesta IA (Síntesis):**
> - Detectó que `requirements.txt` estaba en UTF-16 (generado con `pip freeze >` en PowerShell) y que faltaban `pandas`, `matplotlib` y `requests`.
> - Recomendó un `.gitignore` para no subir `venv/`.
> - Señaló decisiones abiertas: regla concreta clima → costo y coordenadas por zona, fórmulas de los KPIs, greedy vs. mochila, cardinalidad de `Reparto` y valores de `EstadoReparto`.
> - Advirtió riesgos de implementación: `puede_cargar` debe considerar la carga acumulada, IDs con `max + 1` en lugar de `len + 1`, `newline=""` y `encoding="utf-8"` en CSV, serialización de Enums.
> - Sugirió registrar también los casos en que la IA se equivoca o el código se modifica.

---

### Prompt 6: Corrección de archivos de configuración
> **Usuario:**
> "armalo"

> **Respuesta IA:**
> Reescribió `requirements.txt` en UTF-8 y creó `.gitignore` (venv, `__pycache__`, checkpoints de Jupyter, `data/*.csv`).

---

### Prompt 7: Construcción de la aplicación completa
> **Usuario:**
> "Necesito que armes la app"

> **Respuesta IA (Síntesis):**
> Resolvió las decisiones abiertas (ver tabla de la sección 1) y generó:
> - `src/models/`: `Entidad` (contrato abstracto), Enums `Zona` (coordenadas y tarifa), `EstadoReparto` (transiciones válidas) y `TipoVehiculo` (capacidades), dataclasses con validación en `__post_init__`.
> - `src/repositories/`: `BaseRepository[T]` genérico con CRUD, `find`, `add_many` y errores de CSV como `PersistenciaError`.
> - `src/services/`: clima (Open-Meteo, caché, fallback y modo offline simulado), asignación (manual y greedy), estadísticas (3 KPIs + tablero de gráficos), ABM y seeder reproducible.
> - `src/views/`: menús de consola con `colorama`, selección con una tecla (`readchar`) y entradas validadas (coma decimal, `x` para cancelar, Enter para conservar).
> - `main.py`, `analisis.ipynb`, `tests/test_logistica.py`, `README.md`.
>
> **Ajustes durante el desarrollo (detectados al probar):**
> - Si la API no respondía, cada paquete de una asignación masiva esperaba el timeout. Se agregó una caché corta (60 s) también para el resultado *fallback*.
> - El primer escenario del seeder dejaba casi vacía una camioneta y repartidores saturados en otras zonas; se rebalancearon los vehículos por zona para que los KPIs sean más representativos.
> - La tasa de ocupación global devolvía un tipo `numpy.float64`; se convirtió a `float` nativo.

---

## 3. Verificación de Funcionamiento y Pruebas Realizadas

**Pruebas automáticas** (`python -m unittest -v`): **21 pruebas, todas OK.**

| Grupo | Qué se verifica |
| :--- | :--- |
| Repositorios e I/O | Creación automática de `data/` y encabezados; tipos `int`/`float`/`Enum` tras leer; IDs sin duplicar después de borrar; ID inexistente; CSV corrupto → `PersistenciaError`; validaciones de los modelos. |
| Asignación | Recargo aplicado al costo; zona incompatible; capacidad **acumulada** excedida; paquete asignado dos veces; cancelar libera capacidad; transiciones de estado inválidas; greedy respeta zona y capacidad. |
| ABM | No se edita ni borra un paquete asignado; no se cambia el vehículo con repartos activos. |
| Clima | Regla de recargos; parseo de la respuesta de Open-Meteo (con API simulada); **sin conexión → fallback +10 % sin detener la app**; modo offline manual. |
| Estadísticas | KPIs sin datos no fallan; valores correctos con un caso conocido (50 % de ocupación). |

**Prueba de flujo completo:** se recorrieron todos los menús (seeder, KPIs, gráficos, asignación manual y automática, cambio de estado, alta y cancelación de cargas, entradas inválidas). La app no se cortó en ningún caso y los errores de negocio se mostraron como mensajes.

**Prueba sin red:** en el entorno de desarrollo la API estaba bloqueada; la app aplicó automáticamente el recargo base y mostró el aviso. Para la defensa se puede usar *Asignación y repartos → Simular caída de la API*.
