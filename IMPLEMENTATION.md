# Bitácora de Implementación y Roadmap del Proyecto

> Documento vivo de seguimiento paso a paso del desarrollo del proyecto de clasificación de pobreza urbana (Lima y Callao) con microdatos ENAHO.  
> **Curso:** Inteligencia Artificial (1INF24 - 2026-2) — PUCP.  
> **Equipo 3:** Gael Sebastian Arias Escalante, Melanie Nadine Mallqui Huaraz, Valeshka del Pilar Lavado Guerra, Edilvan Franco Salcedo Enciso.  

---

## 1. Estado Global del Proyecto por Sprints

El proyecto organiza su desarrollo en **8 Sprints modulares** diseñados para maximizar el control granular de errores y garantizar cero fuga de datos:

```mermaid
flowchart LR
    S1["Sprint 1: Ingesta ENAHO<br>5 módulos 2024-2025"] --> S2["Sprint 2: Big DataFrame<br>& Purga Panel 2025"]
    S2 --> S3["Sprint 3: Documentación<br>& Gobernanza"]
    S3 --> S4["Sprint 4: Refinamiento<br>Agregaciones"]
    S4 --> S5["Sprint 5: Preproc. R^28<br>& Anti-Fuga"]
    S5 --> S6["Sprint 6: Modelado ML<br>& GroupKFold"]
    S6 --> S7["Sprint 7: OOT 2025,<br>Bootstrap & SHAP"]
    S7 --> S8["Sprint 8: Informe LaTeX<br>& Entrega Final"]

    style S1 fill:#2e7d32,stroke:#1b5e20,color:#fff
    style S2 fill:#2e7d32,stroke:#1b5e20,color:#fff
    style S3 fill:#2e7d32,stroke:#1b5e20,color:#fff
    style S4 fill:#f57c00,stroke:#e65100,color:#fff
    style S5 fill:#546e7a,stroke:#37474f,color:#fff
    style S6 fill:#546e7a,stroke:#37474f,color:#fff
    style S7 fill:#546e7a,stroke:#37474f,color:#fff
    style S8 fill:#546e7a,stroke:#37474f,color:#fff
```

| Sprint | Descripción | Estado | Archivos Principales | Criterio de Éxito / Entregable |
| :---: | :--- | :---: | :--- | :--- |
| **1** | Ingesta modular directa de 5 módulos ENAHO (KISS) | **COMPLETADO** | `src/io_enaho.py` | Carga transparente de M01, M02, M03, M05 y M34 con autodetección de delimitador (`,` en 2024, `;` en 2025). |
| **2** | Reducción $\Phi$ y Big DataFrame Multi-Año (`2024+2025`) | **COMPLETADO** | `src/dataset.py` | Consolidación relacional pura (`build_combined_dataset()`): $8{,}219$ hogares ($4{,}090$ de 2024 + $4{,}129$ de 2025) con columna `year`, sin purgar ni modificar filas. |
| **3** | Sincronización y Gobernanza Documental | **COMPLETADO** | `README.md`, `IMPLEMENTATION.md` | Eliminación de referencias a clases abstractas legadas y documentación formal de OBS-P01/P02 y auditoría 18:33. |
| **4** | Refinamiento de Agregaciones y EDA Temporal/Panel | **COMPLETADO** | `src/dataset.py`, `src/io_enaho.py`, `notebooks/pipeline_completo.ipynb` | Resolución de RC-02 a RC-09, análisis temporal 2024 vs. 2025 y detección de los 930 hogares panel repetidos sobre el Big DF unificado antes de particionar. |
| **5** | Partición OOT, Preprocesamiento Anti-Fuga y $\mathbb{R}^{28}$ | **COMPLETADO** | `src/dataset.py`, `src/preprocessing.py` | Partición explícita `split_oot_train_test()` (purga de 930 panel $\to$ Test $N=3{,}199$) y Pipeline Scikit-Learn sobre Train 2024 ($N=4{,}090$, 0% NaNs). |
| **6** | Modelado Supervisado Extendido y Validación Espacial | **COMPLETADO** | `src/models.py`, `src/preprocessing.py` | 19 modelos en 8 familias (`LightGBM`, `XGBoost`, `CatBoost`, `HistGBDT`, `Stacking`, etc.) bajo `GroupKFold(5)` y 30 corridas repetidas, comparativa de escaladores y regla de selección ex-ante en 2024. |
| **7** | Evaluación Fuera de Tiempo, Inferencia y XAI | **COMPLETADO** | `src/evaluation.py`, `notebooks/pipeline_completo.ipynb` | Evaluación ciega OOT 2025 ($N=3{,}199$) con pesos `factor_expansion`, curvas EE-IE ($B \in [0.10, 0.40]$), *Cluster Bootstrap* (1,000 réplicas) para $H_1$–$H_4$, TreeSHAP exacto (4 bloques alineados) y auditoría ética. |
| **7B** | Consolidación 2024+2025 Anti-Overfitting, Exportación `.joblib` y Encuesta | **COMPLETADO** | `src/inference.py`, `src/encuesta_pobreza.py`, `models/winner_bundle.joblib`, `notebooks/pipeline_completo.ipynb` | Consolidado multi-año deduplicado ($N=7{,}289$ hogares únicos), `Stacking_Tight`, cascada espacial `conglomerado -> ubigeo -> global`, entorno unificado Python 3.12 (`.venv`) y CLI interactiva en `src/encuesta_pobreza.py`. |
| **7C (Sprint 1 Correcciones)** | Entorno Python 3.12, 19 Modelos, Cascada `ubigeo`, Regla 2024 y Corrida Única | **COMPLETADO** | `requirements.txt`, `src/preprocessing.py`, `src/models.py`, `src/evaluation.py`, `notebooks/pipeline_completo.ipynb` | Unificación en Python 3.12 (`catboost 1.2.10`, `xgboost 3.4.1`, `lightgbm 4.7.0`, `shap 0.54.1`), cascada `conglomerado -> ubigeo -> global` (`I1`), selección formal en 30 corridas de 2024 (`1B`), reclasificación `personas_por_hab` (`2A`), título `TreeSHAP Global` y 25/25 celdas ejecutadas con figuras regeneradas. |
| **8 (Sprint 2 Informe)** | Informe Académico Final en $\text{\LaTeX}$ ($\le 8$ páginas) | **SIGUIENTE PASO** | `Documentation/latex/main.tex`, `references.bib`, `sections/*` | Documento final compilado con Secciones 01, 03, 04–07, 09–11 actualizadas, citas completas y contraste honesto de $H_1$–$H_4$ al 95% de confianza. |

---

## 2. Registro de Auditorías y Levantamiento de Observaciones

### A. Observaciones del Jurado al Entregable Parcial (Calificación: 19.0 / 20.0)
Documentadas en detalle en [`Documentation/Observaciones a levantar/log_cambios_2026-11-07_23-25.md`](Documentation/Observaciones%20a%20levantar/log_cambios_2026-11-07_23-25.md):

* **OBS-P01 (-0.5 pts en Metodología): Imputación en Hogares Secundarios**
  * *Observación:* A 72 hogares secundarios en 2024 y 96 en 2025 que comparten lote/vivienda con un hogar principal se les propagaron atributos físicos mediante `ffill/bfill`. En lotes multifamiliares, las condiciones de habitabilidad o servicios pueden diferir. Es más riguroso imputar faltantes numéricos con la mediana del conglomerado censal y los cualitativos con `"desconocido"`.
  * *Solución:* Se descartó totalmente la propagación intra-vivienda. Se implementó `SecondaryHouseholdImputer` en [`src/preprocessing.py`](src/preprocessing.py).
* **OBS-P02 (-0.5 pts en Redacción): Declaración de Contribución de Integrantes**
  * *Observación:* Se omitió la sección formal de contribución individual exigida por la rúbrica (había sido comentada en `main.tex` para ajustar el texto a 4 páginas).
  * *Solución:* Reactivada y descomentada en la línea 102 de [`Documentation/latex/main.tex`](Documentation/latex/main.tex) importando [`declaracion_contribucion.tex`](Documentation/sections/09_declaracion_contribucion/declaracion_contribucion.tex).

---

### B. Inventario de Control de Calidad: Auditoría de la Rama (Log 18:33)
Registrado en [`Documentation/Observaciones a levantar/log_cambios_2026-11-08_18-33.md`](Documentation/Observaciones%20a%20levantar/log_cambios_2026-11-08_18-33.md):

| ID | Prioridad | Dimensión | Problema Identificado | Sprint Asignado |
| :---: | :---: | :--- | :--- | :---: |
| **RC-01** | Alta | Notebook | Celdas 15 a 30 de `pipeline_completo.ipynb` pendientes de ejecución y guardado de outputs. | Sprint 4 / 5 |
| **RC-02** | Alta | Datos | `es_hogar_secundario` marca 146 hogares (`hogar != '11'`). Debe usarse `sin_datos_vivienda = tipo_vivienda.isna()` para los 72 reales. | Sprint 4 |
| **RC-03** | Alta | Datos | Solo 5 variables físicas faltan en los 72 hogares (`tipo_vivienda`, `material_pared`, `material_piso`, `total_habitaciones`, `total_dormitorios`). | Sprint 4 |
| **RC-04** | Alta | Metodología | La mediana por conglomerado en validación cruzada requiere fallback a la mediana de train para evitar nulos en clústeres no vistos. | Sprint 5 |
| **RC-05** | Alta | Anti-Fuga | El Big DataFrame contiene variables con fuga (`lngpc`, `gasto_anual_hogar`). Exigir lista explícita `CANONICAL_FEATURES_28`. | Sprint 4 |
| **RC-06** | Media | Residentes | Filtrar no residentes en M03 y M05 para evitar que miembros ausentes sumen en ratios del hogar. | Sprint 4 |
| **RC-07** | Media | Tamaño Hogar | `n_miembros` debe coincidir con `miembros_hogar` (`MIEPERHO`) excluyendo trabajadores del hogar (`P203 in {8, 9}`). | Sprint 4 |
| **RC-08** | Media | Educación | Códigos `99` (missing) y `12` (básica especial) en `P301A` distorsionan `educ_max_hogar` con `max()`. Tratar antes de agregar. | Sprint 4 |
| **RC-09** | Media | Empleo | Si `jefe_ocupado == 0`, asignar horas = 0.0 y categoría ocupacional `"no_ocupado"`. | Sprint 4 |
| **RC-10** | Media | Ratios | Calcular `personas_por_hab` tras imputar `total_habitaciones` dentro del pipeline. | Sprint 5 |
| **RC-11** | Media | Variables NBI | Descartar `NBI1` a `NBI5` del vector predictivo por ser agregados oficiales cuasi-constantes. | Sprint 4 |
| **RC-12** | Media | Espacio $\mathbb{R}^{28}$ | Congelar formalmente las 28 variables canónicas alineadas con la Sección 3 del informe. | Sprint 4 / 5 |
| **RC-13** | Media | Docs | Actualizar `README.md` e `IMPLEMENTATION.md` eliminando referencias a la arquitectura previa y a `ffill/bfill`. | **Sprint 3 (Resuelto)** |
| **RC-14** | Baja | Documentación | Corregir rangos de valores de `OCU500` en logs metodológicos. | Sprint 4 |
| **RC-15** | Baja | Demografía | Documentar recorte en denominador de `tasa_dependencia` para hogares sin adultos en edad activa. | Sprint 4 |
| **RC-16** | Baja | Limpieza | Mover scripts de ejemplo o talleres del curso fuera del árbol principal de código. | Sprint 4 |

---

## 3. Plan Detallado de los Próximos Sprints

### Sprint 4: Refinamiento de Ingesta y Agregaciones (`dataset.py`)
1. **Refactorización de `build_master_dataset()`:**
   - Incorporar indicador booleano `sin_datos_vivienda` en lugar de la heurística de hogar secundario.
   - Limpiar `P301A` en Módulo 03: mapear código `99` a `NaN` y ubicar adecuadamente educación básica especial (`12`) antes de calcular `educ_max_hogar` y `educ_jefe`.
   - Ajustar Módulo 05 para jefes no ocupados: asignar horas semanales trabajadas iguales a `0.0` y categoría ocupacional `"no_ocupado"`.
   - Filtrar trabajadores del hogar puertas adentro (`parentesco_jefe in {8, 9}`) para que el recuento de miembros sea idéntico a `MIEPERHO`.
2. **Blindaje de Columnas:**
   - Asegurar que la exportación contenga la tupla canónica de entrenamiento `(X, y, groups)` donde $X$ se restringe a `CANONICAL_FEATURES_28`.

---

### Sprint 5: Preprocesamiento Anti-Fuga y Espacio $\mathbb{R}^{28}$ (`preprocessing.py`)
1. **Perfeccionamiento de `SecondaryHouseholdImputer`:**
   - Implementar cálculo de mediana por conglomerado estrictamente sobre las filas de entrenamiento del fold, utilizando la mediana global de train como respaldo incondicional.
   - Recalcular `personas_por_hab = n_miembros / total_habitaciones` dentro de la etapa de transformación.
2. **Estructura del `ColumnTransformer`:**
   - **Numéricas (14):** `SecondaryHouseholdImputer` $\to$ `SimpleImputer(strategy='median')` $\to$ `RobustScaler()`.
   - **Nominales / Categóricas (14):** `SimpleImputer(strategy='constant', fill_value='desconocido')` $\to$ `OneHotEncoder(handle_unknown='ignore', min_frequency=0.01, sparse_output=False)`.

---

### Sprint 6: Modelado Supervisado y Validación Cruzada (`models.py`)
1. **Preprocesamiento y Escalamiento Diferenciado por Familia (Cero Fuga dentro de cada Fold):**
   - **Verificación de Escaladores (`compare_scalers_cv`):** Comparativa empírica interna al K-Fold entre `RobustScaler`, `StandardScaler` y `MinMaxScaler` sobre modelos sensibles a escala; se fija `RobustScaler` por defecto conforme a la preservación de outliers (`O-24`, `metodologia.tex`).
   - **Lineales, Econométricos, Generativos, Kernels, Distancias y Redes (`PMT-MCO`, `PMT-Quantile`, `ElasticNet`, `LDA`, `Naive Bayes`, `SVM-RBF`, `KNN`, `MLP`):** `scale_numeric=True, scaler_type="robust"` + `OneHotEncoder(min_frequency=0.01)`.
   - **Árboles y Ensambles (`CART`, `Random Forest`, `Extra Trees`, `LightGBM / HistGBDT`, `AdaBoost`):** `scale_numeric=False, scaler_type="none"` (invarianza monotónica) + `OneHotEncoder(min_frequency=0.01)`.
2. **Batería Ampliada de 16 Modelos en 8 Familias:**
   - **Baselines de Representación Solo Vivienda ($H_1$, 12 vars):** `Logistica_Solo_Vivienda`, `RF_Solo_Vivienda`.
   - **Econométricos Continuos ($\ln(\text{gasto})$, 28 vars):** `PMT_MCO` (OLS/Ridge), `PMT_Quantile_20` (Regresión Cuantílica $q=0.20$).
   - **Lineales y Generativos:** `Logistica_ElasticNet` ($L_1/L_2$ con $\alpha \in \{1, 2, \gamma\}$), `LDA`, `Naive_Bayes`.
   - **Árbol Individual Podado:** `CART_Podado` ($\alpha_{\text{ccp}}$, peso $\alpha$).
   - **Ensambles Bagging:** `Random_Forest`, `Extra_Trees` (con peso $\alpha$).
   - **Ensambles Gradient Boosting:** `LightGBM_GBDT` (`LGBMClassifier` / `HistGradientBoostingClassifier` leaf-wise con peso $\alpha$), `AdaBoost`.
   - **No Lineales (Kernels, Vecindad y Deep Learning Tabular):** `SVM_RBF`, `KNN`, `MLP_Red_Neuronal`.
   - **Meta-Ensamble:** `Stacking_Ensemble` (combinando Lineal + Bagging + Boosting).
3. **Protocolo Espacial y Validación (2024):**
   - `GroupKFold(n_splits=5)` agrupado por `conglomerado` censal sobre la muestra 2024 ($N = 4{,}090$), generando predicciones *Out-Of-Fold* (OOF) de validación para calibrar el umbral $\tau$ ($H_3$) sin tocar Test 2025.
   - Optimización de hiperparámetros orientada a maximizar PR-AUC.

---

### Sprint 7: Evaluación Fuera de Tiempo, Inferencia y XAI (`evaluation.py`)
1. **Evaluación Out-of-Time 2025:**
   - Evaluación ciega sobre el test de 2025 ($N_{\text{test}} = 3{,}199$, 601 conglomerados).
2. **Métricas a Cobertura Fija ($B = 20\%$):**
   - Error de Exclusión ($\mathrm{EE} = FN / (TP + FN)$) y Error de Inclusión ($\mathrm{IE} = FP / (TP + FP)$).
   - Trazado de curvas paramétricas EE vs. IE para $B \in [0.10, 0.40]$.
3. **Inferencia Estadística por *Cluster Bootstrap*:**
   - 1,000 réplicas remuestreadas a nivel de conglomerado con reemplazo para contrastar las 4 hipótesis formales:
     - $H_1$: Ganancia en PR-AUC $\ge +0.12$.
     - $H_2$: Equivalencia de EE entre ensamble y modelos lineales dentro de $\pm 0.035$.
     - $H_3$: Punto operativo con Recall $\ge 0.70$ y Precisión $\ge 0.40$ en 2025.
     - $H_4$: Degradación temporal en PR-AUC $\le 0.05$.
4. **Explicabilidad con TreeSHAP:**
   - Descomposición aditiva sobre el mejor modelo ensamble: gráfico global Beeswarm y gráficos de dependencia parcial de variables de empleo y hacinamiento.

---

### Sprint 8: Informe Académico Final en $\text{\LaTeX}$ y Cierre
1. **Redacción de Secciones Faltantes:**
   - Sección 04: *Experimentación y Resultados* (Tablas de CV y Test 2025, contraste de $H_1$ a $H_4$, curvas EE-IE).
   - Sección 05: *Conclusión* (Respuestas a la pregunta de investigación).
   - Sección 06: *Sugerencias Futuras* (Extensiones a otras regiones, frecuencia de actualización).
   - Sección 07: *Implicancias Éticas* (Justicia distributiva, no discriminación, impacto social).
2. **Control Tipográfico y Extensión:**
   - Mantener el límite riguroso de **máximo 8 páginas de cuerpo** (sin incluir referencias).
   - Compilación en `pdflatex` con 0 errores y generación de `Documentation/latex/main.pdf`.
