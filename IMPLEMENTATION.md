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
| **2** | Reducción $\Phi$, Big DataFrame y Purga de Panel | **COMPLETADO** | `src/dataset.py` | Consolidación relacional: Train 2024 ($N = 4{,}090$) y Test 2025 independiente ($N_{\text{test}} = 3{,}199$) tras purgar 930 hogares repetidos. |
| **3** | Sincronización y Gobernanza Documental | **COMPLETADO** | `README.md`, `IMPLEMENTATION.md` | Eliminación de referencias a clases abstractas legadas y documentación formal de OBS-P01/P02 y auditoría 18:33. |
| **4** | Refinamiento de Ingesta y Agregaciones en Hogar | **COMPLETADO** | `src/dataset.py`, `src/io_enaho.py` | Resolución de inconsistencias RC-02, RC-06, RC-07, RC-08, RC-09 y RC-05 de la auditoría técnica. |
| **5** | Preprocesamiento Anti-Fuga y Espacio $\mathbb{R}^{28}$ | **COMPLETADO** | `src/preprocessing.py` | Pipeline Scikit-Learn: imputación de 72 hogares por mediana de conglomerado censal (OBS-P01), categoría `"desconocido"` y One-Hot robusto (81 features, 0% NaNs). |
| **6** | Modelado Supervisado y Validación Cruzada Espacial | **SIGUIENTE PASO** | `src/models.py` | Entrenamiento de 5 modelos (PMT-MCO, ElasticNet, CART podado, Random Forest, LightGBM) bajo `GroupKFold(5)` por conglomerado censal. |
| **7** | Evaluación Fuera de Tiempo, Inferencia y XAI | **PENDIENTE** | `src/evaluation.py` | Curvas EE-IE a $B=20\%$, contraste de $H_1$ a $H_4$ con 1,000 réplicas *Cluster Bootstrap*, y explicabilidad con TreeSHAP. |
| **8** | Informe Académico Final en $\text{\LaTeX}$ ($\le 8$ páginas) | **PENDIENTE** | `Documentation/latex/main.tex`, `sections/*` | Documento final compilado con las Secciones 04 a 07 completas, sin advertencias y alineado a la rúbrica PUCP (meta: 20.0 / 20). |

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
1. **Suite de 5 Clasificadores:**
   - **Línea Base Econométrica (PMT-MCO):** Modelo OLS sobre $\ln(\text{gasto})$, prediciendo pobreza si $\widehat{\ln(\text{gasto})} < \ln(\text{línea})$.
   - **Regresión Logística ElasticNet:** Penalización $L_1/L_2$ con ponderación de clase sensible al costo ($\alpha$).
   - **Árbol de Decisión CART:** Poda por complejidad de costo ($\alpha_{\text{ccp}}$) para interpretabilidad directa.
   - **Random Forest:** Ensamble de 300 árboles con submuestreo balanceado.
   - **LightGBM:** Gradient Boosting con regularización $L_1/L_2$, `scale_pos_weight` parametrizado por $\alpha$.
2. **Protocolo Espacial:**
   - `GroupKFold(n_splits=5)` agrupado por `conglomerado` censal sobre la muestra 2024 ($N = 4{,}090$).
   - Optimización de hiperparámetros con `GridSearchCV` orientada a maximizar PR-AUC.

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
