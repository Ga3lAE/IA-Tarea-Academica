# Flujo de Trabajo en Notebooks (Workflows)

Esta carpeta estructura los experimentos interactivos y el análisis de datos por etapas progresivas del proyecto de Inteligencia Artificial (PUCP 1INF24).

```
notebooks/
├── 01_modulos/       # Limpieza y extracción individual por módulo ENAHO
├── 02_integracion/   # Unión relacional a nivel hogar y cruce con datos municipales
├── 03_eda/           # Análisis exploratorio multivariado de pobreza (Lima y Callao)
├── 04_modelado/      # Clasificación binaria out-of-time, optimización de costos y SHAP
└── README.md
```

---

## Estructura de Etapas

### 1. `01_modulos/` (Extracción y Limpieza Modular)
- **Objetivo:** Ejecutar y validar el pipeline de cada módulo de ENAHO de forma independiente para 2024 y 2025 (extensible a 2026).
- **Notebooks:**
  - `01_vivienda_modulo01.ipynb`: Procesamiento del Módulo 01 (Vivienda y Hogar), resolución de nulos estructurales intra-vivienda, imputación y validación de tipos.
  - *(Próximos)* `02_demografia_modulo02.ipynb`, `03_educacion_modulo03.ipynb`, `04_empleo_modulo05.ipynb`, `05_sumaria_modulo34.ipynb` (Variable Objetivo $Y$).

### 2. `02_integracion/` (Fusión Relacional y Enriquecimiento Territorial)
- **Objetivo:** Integrar horizontalmente los módulos procesados utilizando la clave primaria de hogar:
  $$\text{PK} = \{\text{CONGLOME}, \text{VIVIENDA}, \text{HOGAR}\}$$
- **Enriquecimiento Externo:** Cruce con la base de datos abiertos del MEF (gasto presupuestal municipal por habitante) usando el `UBIGEO` distrital (6 dígitos) para incorporar el contexto territorial institucional.

### 3. `03_eda/` (Análisis Exploratorio y Binarización de Categorías)
- **Objetivo:** Demostrar estadísticamente por qué un único árbol o regla simple falla (mitos de materiales precarios vs. pobreza real) y justificar el uso de modelos no lineales.
- **Agrupación de Categorías Raras:** Análisis de frecuencias (< 1%) y colapso semántico de categorías hacia variables de calidad ordinal o indicadores consolidados.

### 4. `04_modelado/` (Clasificación Supervisada de Pobreza y Evaluación Out-of-Time)
- **Objetivo:** Formular y entrenar modelos predictivos supervisados de clasificación binaria ($Y \in \{0, 1\}$).
- **Estrategia Temporal:** Train en 2024 $\to$ Test Out-of-Time en 2025 $\to$ Despliegue anticipado sobre 2026 (alerta temprana con módulos 01, 02 y 03).
- **Función de Pérdida Sensible al Costo:** Penalización asimétrica de Falsos Negativos ($FN$, dejar a un hogar pobre sin asistencia social) frente a Falsos Positivos ($FP$).
- **Explicabilidad:** Explicaciones locales y globales con TreeSHAP / KernelSHAP.
