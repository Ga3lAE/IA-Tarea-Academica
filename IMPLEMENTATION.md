# Bitácora de Implementación y Roadmap del Proyecto

> Documento vivo de seguimiento paso a paso del desarrollo del proyecto de clasificación de pobreza urbana (Lima y Callao) con ENAHO.

---

## Estado Global del Proyecto

```mermaid
flowchart LR
    Fase1["Fase 1: Módulo 01<br>(Vivienda & Core)"] --> Fase2["Fase 2: Módulos 02 & 03<br>(Demografía & Educ)"]
    Fase2 --> Fase3["Fase 3: Módulo 05<br>(Empleo & Informalidad)"]
    Fase3 --> Fase4["Fase 4: Módulo 34<br>(Target & Master Merge)"]
    Fase4 --> Fase5["Fase 5: EDA &<br>Feature Selection"]
    Fase5 --> Fase6["Fase 6: Modelado ML<br>& Desbalance"]
    Fase6 --> Fase7["Fase 7: XAI &<br>Reporte Final"]

    style Fase1 fill:#2e7d32,stroke:#1b5e20,color:#fff
    style Fase2 fill:#f57c00,stroke:#e65100,color:#fff
    style Fase3 fill:#546e7a,stroke:#37474f,color:#fff
    style Fase4 fill:#546e7a,stroke:#37474f,color:#fff
    style Fase5 fill:#546e7a,stroke:#37474f,color:#fff
    style Fase6 fill:#546e7a,stroke:#37474f,color:#fff
    style Fase7 fill:#546e7a,stroke:#37474f,color:#fff
```

| Fase | Descripción | Estado | Archivos Principales |
| :---: | :--- | :---: | :--- |
| **1** | Arquitectura Base, Validadores y Módulo 01 (Vivienda) | **COMPLETADO** | `src/core/*`, `src/processors/modulo01.py`, `main.ipynb` |
| **2** | Ingesta y Agregaciones de Módulo 02 (Demografía) y 03 (Educación) | **EN PROGRESO** | `src/config/modulo02.py`, `src/config/modulo03.py` |
| **3** | Ingesta y Variables de Informalidad del Módulo 05 (Empleo) | **PENDIENTE** | `src/processors/modulo05.py` |
| **4** | Módulo 34 (Sumaria), Definición de Target y Master Merge | **PENDIENTE** | `src/processors/modulo34.py`, `src/master_merge.py` |
| **5** | EDA Integral, Varianza, Multicolinealidad y Information Value | **PENDIENTE** | `notebooks/eda_consolidado.ipynb` |
| **6** | Modelado Predictivo, Remuestreo / Pesos y Calibración | **PENDIENTE** | `src/models/*`, `notebooks/modelado.ipynb` |
| **7** | Interpretabilidad (TreeSHAP) y Entrega de Tarea Académica | **PENDIENTE** | `reports/informe_final.pdf` |

---

## Fase 1: Arquitectura Base y Módulo 01 (Vivienda y Servicios) — COMPLETADA

### Decisiones Técnicas Implementadas
1. **Adopción de Principios SOLID:**
   - Creación de `BaseModuleProcessor` en `src/core/base_processor.py` aplicando el patrón **Template Method**.
   - Ciclo de vida modular estandarizado:
     $$\text{load\_data()} \to \text{validate\_raw\_schema()} \to \text{filter\_scope()} \to \text{clean\_and\_impute()} \to \text{feature\_engineering()} \to \text{apply\_mappings()} \to \text{validate\_processed\_data()} \to \text{save\_data()}$$
2. **Detección Automática de Delimitadores:**
   - La ENAHO 2025 utiliza punto y coma (`;`), mientras que 2024 utiliza comas (`,`). El método `_detect_delimiter()` en la clase base lee la cabecera y adapta dinámicamente el parser de Pandas.
3. **Resolución de Nulos Estructurales en Vivienda:**
   - **Los 72 nulos (1.76%) de 2024 y 96 (2.33%) de 2025** en materiales de piso, pared y dormitorios correspondían a hogares secundarios (`HOGAR 22, 33...`) que cohabitan en una misma vivienda con el hogar principal (`HOGAR 11`). Se resolvieron mediante propagación intra-vivienda (`transform(ffill().bfill())` aislado por `conglomerado` y `vivienda`), logrando **0.00% de nulos**.
   - **Nulos en Título de Propiedad (32%) y SUNARP (57%):** Se fusionaron en la feature de alta señal jurídica `seguridad_tenencia`.
4. **Validaciones Estrictas (`src/core/validators.py`):**
   - Comprobación previa de columnas obligatorias.
   - Comprobación de recuentos de filas esperados para Lima Metropolitana, `DOMINIO 8` ($3,800 \le N \le 4,600$).
   - Aserción de unicidad de la llave primaria `(conglomerado, vivienda, hogar)`.
   - Comprobación de 0% nulos en columnas esenciales.
5. **Refactorización de Notebooks y Estructura Modular:**
   - Se migró el código interactivo hacia `notebooks/01_modulos/01_vivienda_modulo01.ipynb`, consolidando el procesamiento y análisis de 2024 y 2025 en un flujo limpio que exporta directamente a `Data/processed/`.
6. **Orquestación Multi-Año (`src/pipeline.py`):**
   - Ejecución conjunta de 2024 (4,090 hogares) y 2025 (4,129 hogares) de Lima Metropolitana (`DOMINIO 8`) generando un dataset histórico de **8,219 hogares limpios**, indexado por `(anio_encuesta, conglomerado, vivienda, hogar)` con almacenamiento centralizado en `Data/processed/`.
7. **Documentación de Parámetros de Configuración (`BaseModuleProcessor`):**
   - Se estandarizó la signatura de todos los procesadores para permitir parametrización flexible en runtime (delimitador, codificación, filtros geográficos, umbrales de validación) sin alterar el código fuente ni romper el principio Open/Closed.

---

### Referencia de Parámetros de `BaseModuleProcessor`

Todos los procesadores de módulos (`Modulo01Processor`, `Modulo02Processor`, etc.) heredan de `BaseModuleProcessor` y admiten los siguientes argumentos:

| Parámetro | Tipo | Por Defecto | Descripción |
| :--- | :--- | :--- | :--- |
| `file_path` | `str \| Path` | *(Obligatorio)* | Ruta al archivo CSV crudo de la ENAHO (ej. `Data/2025/enaho/1031-Modulo01/Enaho01-2025-100.csv`). |
| `year` | `int \| None` | `None` | Año de la encuesta (ej. 2024, 2025). Si es `None`, se infiere del nombre del archivo o carpeta. |
| `output_path` | `str \| Path \| None` | `None` | Ruta destino para guardar el CSV o Parquet limpio. Si es `None`, no se exporta a disco. |
| `filter_geographic` | `bool` | `True` | Activa o desactiva el filtro geográfico por UBIGEO. Si es `False`, procesa los 25 departamentos a nivel nacional. |
| `ubigeo_prefixes` | `str \| tuple \| list \| None` | `('07', '1501')` | Prefijos de UBIGEO a filtrar (ej. `('07', '1501')` para Lima Metropolitana = `DOMINIO 8`; `('07', '15')` para todo el departamento de Lima + Callao, `('01', '02')` para Amazonas/Áncash). |
| `filter_valid_results` | `bool` | `True` | Filtra entrevistas completas o con datos suficientes (`RESULT` $\in \{1, 2\}$). |
| `sep` | `str \| None` | `None` (Auto) | Delimitador del CSV crudo de entrada. Si es `None`, auto-detecta si el archivo usa `,` o `;`. Permite forzar `','` o `';'`. |
| `output_sep` | `str \| None` | `','` | Delimitador para exportar el CSV limpio. Por defecto es `','`. |
| `encoding` | `str \| None` | `'latin-1'` | Codificación de caracteres del archivo original (típico de INEI: `latin-1`). |
| `min_rows` | `int \| None` | Dinámico | Umbral mínimo de filas para la aserción de integridad. Se ajusta según el ámbito geográfico. |
| `max_rows` | `int \| None` | Dinámico | Umbral máximo de filas para la aserción de integridad. |
| `verbose` | `bool` | `True` | Imprime el progreso paso a paso en consola/Jupyter. |

---

## Fase 2: Módulo 02 (Demografía) y Módulo 03 (Educación) — SIGUIENTE PASO

### Objetivos Específicos
1. **Doble Nivel de Extracción:**
   - A diferencia del Módulo 01 (que ya viene a nivel hogar), los módulos 02 y 03 vienen a **nivel individuo** (`CODPERSO`).
   - Se deben generar dos ramas por hogar:
     - **Rama Jefe de Hogar (`P203 == 1`):** Características directas de la cabeza de familia.
     - **Rama Agregada del Hogar (`groupby`):** Estadísticas resumen del núcleo familiar.
2. **Variables a Procesar en Módulo 02 (Demografía):**
   - *Jefe:* `sexo_jefe` (`P207`), `edad_jefe` (`P208A`), `estado_civil_jefe` (`P209`).
   - *Hogar:* `tamano_hogar`, `num_ninos_0_5`, `num_escolares_6_17`, `num_adultos_mayores_65`, `tasa_dependencia`, `porc_mujeres_hogar`.
3. **Variables a Procesar en Módulo 03 (Educación):**
   - *Jefe:* `nivel_educ_jefe` (`P301A` - codificado ordinalmente), `lengua_materna_jefe` (`P300A`), `alfabeto_jefe` (`P302`).
   - *Hogar:* `max_nivel_educ_hogar`, `asistencia_escolar_hogar` (% de menores que asisten).

---

## Fase 3: Módulo 05 (Empleo e Informalidad)

### Objetivos Específicos
- Procesar la situación de empleo individual ($\ge 14$ años).
- Extraer indicadores clave del Jefe de Hogar:
  - `condicion_empleo_jefe` (`OCU500`: ocupado, desocupado, inactivo).
  - `categoria_ocup_jefe` (`P507`: asalariado, independiente, obrero, TFNR).
  - `formalidad_empresa_ruc` (`P510A1`: registrada en SUNAT vs informal).
  - `afiliacion_pension` (`P558A5`: AFP/ONP vs Sin pensión).
- Agregados del hogar:
  - `num_ocupados_hogar`, `tasa_ocupacion_hogar`.

---

## Fase 4: Módulo 34 (Sumaria), Target y Master Merge

### Objetivos Específicos
- Extracción de la variable objetivo binaria:
  $$y = 1 \text{ si } \text{POBREZA} \in [1, 2], \quad y = 0 \text{ si } \text{POBREZA} = 3$$
- **Regla Estricta de Prevención de Data Leakage:**
  - Descarte total de sumatorias monetarias de ingreso y gasto (`GASHOG2D`, `INGHOG2D`, `LINEA`, etc.).
- Fusión interna de todos los módulos limpios utilizando como llave `['anio_encuesta', 'conglomerado', 'vivienda', 'hogar']` (930 hogares panel se repiten entre 2024 y 2025).

---

## Fase 5: EDA Integral y Selección de Características

### Objetivos Específicos
- Diagnóstico univariado y bivariado con respecto a la variable `Target`.
- Cálculo de **Mutual Information (MI)** y **Weight of Evidence / Information Value (WoE/IV)** para ranquear predictores.
- Evaluación de colinealidad mediante **Variance Inflation Factor (VIF)**.
- Consolidación del dataset final con **35 - 45 features densas**.

---

## Fase 6: Modelado Predictivo y Manejo del Desbalance

### Objetivos Específicos
1. **Esquema de Partición:**
   - `GroupKFold` (5 folds) por conglomerado en 2024 y prueba fuera de tiempo en 2025 **sin los 930 hogares panel** (ver `Documentation/Observaciones a levantar/Plan 2`).
2. **Modelos Candidatos:**
   - **Baseline:** Regresión Logística regularizada (Lasso/Ridge) con `class_weight='balanced'`.
   - **Árboles Ensamble:** Random Forest Classifier.
   - **Gradient Boosting:** LightGBM / XGBoost con `scale_pos_weight`.
3. **Métricas de Rendimiento:**
   - **Primarias:** F1-Score (clase Pobre / Macro), PR-AUC (Precision-Recall AUC).
   - **Secundarias:** ROC-AUC, Brier Score (calibración probabilística).
4. **Calibración de Umbral (*Threshold Tuning*):**
   - Evaluar curvas Precision-Recall para seleccionar el umbral óptimo de decisión según costos de falsos positivos vs falsos negativos en focalización social.

---

## Fase 7: Interpretabilidad y Entrega Académica

### Objetivos Específicos
- Análisis global y local con **TreeSHAP (SHapley Additive exPlanations)**.
- Identificación de las variables más influyentes en la predicción de pobreza en Lima y Callao.
- Redacción del informe final con enfoque de rigor académico para la rúbrica PUCP.
