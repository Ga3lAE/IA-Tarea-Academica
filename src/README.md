# Arquitectura de Software Modular (`src/`)

> **Curso:** Inteligencia Artificial (1INF24) — Pontificia Universidad Católica del Perú (PUCP)  
> **Proyecto:** Clasificación de Pobreza Urbana en Lima Metropolitana mediante Machine Learning sobre microdatos ENAHO (INEI).

---

## 📌 Principios de Diseño (KISS: *Keep It Simple, Stupid*)

La carpeta `src/` contiene la biblioteca de funciones y clases puras en Python que alimentan los notebooks interactivos y los experimentos del proyecto.

Se diseñó bajo tres premisas fundamentales:
1. **Transparencia y Legibilidad:** Nombres de columnas estandarizados según los Diccionarios Metodológicos Oficiales del INEI (sin acrónimos crudos como `P101` o `P203`).
2. **Cero Data Leakage:** Separación estricta entre la ingesta de datos brutos y el preprocesamiento estadístico. Ninguna variable de gasto o ingreso se utiliza como predictor, y las imputaciones se ajustan exclusivamente en el conjunto de entrenamiento.
3. **Desacoplamiento:** El código ejecutable se organiza en módulos especializados sin sobre-ingeniería ni clases abstractas innecesarias.

---

## 📂 Organización de Módulos

```text
src/
├── __init__.py           # Declaración del paquete src
├── README.md             # Documentación técnica de la biblioteca (este archivo)
├── io_enaho.py           # Ingesta, lectura directa y normalización de los 5 módulos ENAHO
├── dataset.py            # Operador de reducción relacional Phi y construcción del Big DataFrame
├── preprocessing.py      # (Fase 3) Transformadores de Scikit-Learn (mediana por CONGLOME y categoría 'desconocido')
├── models.py             # (Fase 4) Definición de los 5 modelos supervisados y optimización con GroupKFold(5)
└── evaluation.py         # (Fase 5) Cluster Bootstrap (1,000 réplicas), curvas EE-IE y TreeSHAP
```

---

## 🚀 Descripción de Módulos Activos

### 1. `io_enaho.py` (Capa de Ingesta y Lectura)
- **Propósito:** Lee los archivos CSV originales de la ENAHO (2024 y 2025) manejando de forma automática o por parámetro los delimitadores (`,` para 2024 y `;` para 2025).
- **Funciones Principales:**
  - `load_modulo34(year)`: Sumaria (Marco de hogares en Lima Metropolitana, target de pobreza `y` / `target_pobreza` y log-gasto `lngpc` para baseline).
  - `load_modulo01(year)`: Vivienda y servicios (conservando intactos los valores nulos en hogares secundarios).
  - `load_modulo02(year)`: Demografía de residentes habituales y jefatura de hogar.
  - `load_modulo03(year)`: Educación y capital humano ($\ge 3$ años).
  - `load_modulo05(year)`: Empleo e informalidad laboral ($\ge 14$ años).
  - `load_all_raw_modules(year)`: Carga y cruza los 5 módulos para el ámbito de Lima Metropolitana (`DOMINIO == 8`).

### 2. `dataset.py` (Capa de Integración del Big DataFrame)
- **Propósito:** Aplica el **Operador Relacional $\Phi$** para colapsar los registros a nivel individuo hacia el nivel de hogar y une las 5 tablas sobre la llave primaria `['conglomerado', 'vivienda', 'hogar']`.
- **Funciones Principales:**
  - `build_master_dataset(year, purge_panel_2025=True)`: Devuelve el Big DataFrame unificado para el año solicitado ($4,090$ filas en 2024; $3,199$ filas en 2025 tras purgar los 930 hogares repetidos).
  - `load_train_test_master()`: Retorna la tupla `(df_2024_train, df_2025_test)` lista para el análisis.
