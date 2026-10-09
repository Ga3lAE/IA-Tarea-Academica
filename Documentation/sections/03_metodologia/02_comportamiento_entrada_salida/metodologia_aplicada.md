# Metodología Aplicada: Comportamiento Entrada/Salida y Diagnóstico EDA en Microdatos ENAHO

> **⚠️ Nota (Plan 2, 2026-10-08):** este documento conserva textos anteriores al levantamiento de observaciones (alcance de 5,571 hogares, matriz `INGTPUHD`, hipótesis previas, atribuciones de papers sin verificar). La versión vigente es la de los archivos `.tex` y la de [`Observaciones a levantar/Plan 2`](../../../Observaciones%20a%20levantar/Plan%202/README.md).

Este documento define la estructura técnica de las entradas y salidas del sistema sobre los microdatos de la **ENAHO (2024--2025)** para Lima Metropolitana y Callao, detallando los **inconvenientes empíricos identificados durante el Análisis Exploratorio de Datos (EDA Inicial)** y las salvaguardas de ingeniería para mitigarlos.

---

## 1. Unidad Muestral y Clave Primaria

La unidad elemental de observación e inferencia del sistema es el **Hogar Urbano**, identificado de manera biyectiva en los registros del INEI por la tupla:
$$\text{ID}_{\text{hogar}} = (\texttt{CONGLOME}, \texttt{VIVIENDA}, \texttt{HOGAR})$$

* Ámbito geográfico delimitado: Lima Metropolitana y la Provincia Constitucional del Callao:
  $$\texttt{DOMINIO} = 8 \quad \land \quad \texttt{DEPARTAMENTO} \in \{15, 07\}$$
* Total de observaciones en ENAHO 2024: $N = 5,571$ hogares.

---

## 2. Inconvenientes Prácticos de los Microdatos (Diagnóstico del EDA Inicial)

Durante la fase de exploración y perfilado de datos (*Exploratory Data Analysis*), se detectaron 5 fricciones empíricas críticas que invalidan el uso de algoritmos estándares sin adaptación previa:

### Inconveniente 1: Desbalance Severo de Clases y Riesgo de la Paradoja de Exactitud
* **Evidencia del EDA:** De los 5,571 hogares, únicamente 1,037 se encuentran en pobreza monetaria (**18.61%**), frente a 4,534 hogares no pobres (**81.39%**). La razón de desbalance es de $\gamma = 4.372$ a $1$.
* **Consecuencia Práctica:** Un clasificador ingenuo que prediga sistemáticamente $\hat{y}_i = 0$ (no pobre) alcanzaría un engañoso **81.4% de Exactitud (*Accuracy*)**, pero incurriría en un **100% de Error de Exclusión Social**, privando de asistencia al 100% de familias en pobreza extrema.
* **Estrategia de Mitigación:** 
  1. Abandono de *Accuracy* y optimización de $F_1$-score minoritario, PR-AUC y Recall.
  2. Ponderación asimétrica del gradiente (*Cost-Sensitive Loss*) asignando un factor de escala de penalización $c_1/c_0 = 4.372$ (`scale_pos_weight`).
  3. Descarte del método SMOTE ingenuo: generar vecinos sintéticos sobre variables categóricas heterogéneas crea distorsiones absurdas (ej. hogares con piso de loseta fina y paredes de paja sin agua).

### Inconveniente 2: Nulos Estructurales por Cohabitación Multifamiliar
* **Evidencia del EDA y Diagnóstico con Heatmap:** El **2.15% de los registros en Lima (120 hogares)** presentan valores nulos (`NaN`) en la totalidad de las variables físicas de la vivienda en el Módulo 01 (`P101`, `P102`, `P103`, etc.).
  * Al graficar una matriz de calor (*Missingness Heatmap*) condicionada por el código de hogar (`HOGAR == 1` vs `HOGAR > 1`), se comprueba que la tasa de nulos es **0.0%** en el hogar principal y **100.0%** en hogares secundarios.
* **Causa Identificada:** No se trata de omisiones estocásticas (MCAR), sino de un diseño muestral del INEI (*Missing at Random - MAR* condicional al predio): cuando dos o más familias cohabitan en una misma edificación física (`HOGAR 11` y `HOGAR 22`), el encuestador solo registra los materiales en el hogar principal.
* **Estrategia de Mitigación:** Operador `HousingCohortImputer` que propaga por bloque (`ffill().bfill()`) las características habitacionales del predio compartido entre hogares del mismo conglomerado y vivienda física, recuperando el 100% de la información real sin inventar datos sintéticos.

### Inconveniente 3: Dispersión Extrema y Colas Largas en Atributos Categóricos (*Sparsity*)
* **Evidencia del EDA:** Atributos como material de paredes (`P102`) o pisos (`P103`) cuentan con 7 a 9 categorías oficiales en el INEI. Categorías como *"Mármol / Porcelanato importado"* ($0.23\%$), *"Caña o estera con torta de barro"* ($0.45\%$) o *"Madera rústica / chonta"* ($0.78\%$) exhiben frecuencias menores al 1%.
* **Consecuencia Práctica:** La aplicación ciega de *One-Hot Encoding* genera una matriz hiperdispersa con decenas de columnas irrelevantes, provocando sobreajuste (*overfitting*) y fragmentación excesiva de las particiones de los árboles.
* **Estrategia de Mitigación:** Operador `DomainBinner` que agrupa semánticamente las categorías en tres estratos ordenados de vulnerabilidad (Noble Acabado vs Cemento Básico vs Precario/Tierra), guiado por las tasas de pobreza empíricas del EDA.

### Inconveniente 4: Discrepancia de Granularidad Relacional ($1:M$)
* **Evidencia del EDA:** El Módulo 01 está estructurado a nivel de hogar, mientras que los módulos 02 (demografía), 03 (educación) y 05 (empleo) contienen $N_{\text{pers}} = 19,420$ filas a nivel de individuo (`CODPERSO`). Los hogares varían desde personas solas ($M_i = 1$) hasta familias multigeneracionales de 12 personas ($M_i = 12$).
* **Estrategia de Mitigación:** Operador relacional $\Phi(\cdot)$ que desacopla la extracción del decisor principal (Jefe de hogar $P203 = 1$) de los funcionales estadísticos del colectivo familiar (tamaño, tasas de dependencia infantil y de la tercera edad, tasa de ocupación laboral, máximo nivel educativo).

### Inconveniente 5: Riesgo Severo de Fuga de Información (*Data Leakage*)
* **Evidencia del EDA:** Variables como `GASHOG2D` (gasto bruto mensual) e `INGHOG2D` (ingreso del hogar) se correlacionan en más de $0.85$ con la pobreza monetaria. Si un modelo las utiliza, alcanza un $F_1 \approx 0.99$ dentro de muestra, pero se vuelve inservible en campo porque un empadronador territorial no puede auditar los gastos de consumo en visitas rápidas.
* **Estrategia de Mitigación:** Cortafuegos estricto (*Zero-Leakage Firewall*): aislamiento y eliminación absoluta de todas las columnas financieras del Módulo 34 previas al particionamiento.

### Inconveniente 6: Multicolinealidad Categórica e Invalidez de la Correlación de Pearson
* **Evidencia del EDA:** Más del 70% de las variables son nominales u ordinales. Calcular correlación de Pearson introduce relaciones métricas lineales inexistentes. Además, variables como abastecimiento de agua y red de alcantarillado presentan redundancia estructural casi idéntica.
* **Estrategia de Mitigación:** 
  1. Uso de **V de Cramér ($V$)** para evaluar pares de variables categóricas. Se podan covariables con $V > 0.80$ para evitar multicolinealidad.
  2. Uso de **Información Mutua ($I(X; Y)$)** para cuantificar el poder discriminante de cada característica respecto al target sin suposiciones de linealidad.

---

## 3. Reducción de Dimensionalidad por Curaduría y Selección de Características

En lugar de aplicar una reducción factorial continua destructiva (como PCA o FAMD), que rotaría el espacio dificultando las divisiones ortogonales de LightGBM y destruyendo la explicabilidad univariada de TreeSHAP requerida para políticas públicas, la **reducción de dimensionalidad** se ejecuta como una **selección supervisada y curada de variables en 3 etapas**:

1. **Filtro 1 (Aislamiento Ético y Operativo):** De las $>400$ variables crudas de la ENAHO, se excluyen variables financieras y de identificación administrativa, reteniendo ~80 atributos observables del hogar.
2. **Filtro 2 (Poda de Redundancia por V de Cramér):** Se eliminan variables que duplican información con $V > 0.80$ (e.g., eliminando duplicación entre tipo de baño y desagüe).
3. **Filtro 3 (Ranking por Información Mutua y Dominio):** Se seleccionan las ~20 características con mayor reducción de entropía del target de pobreza.

---

## 4. Estructura del Espacio de Entrada ($\mathcal{X}$) y Salida ($\mathcal{Y}$)

### 4.1 Vector de Características $\mathbf{x}_i \in \mathbb{R}^d$ ($d \approx 20$)
Concatenación de los 4 subvectores procesados y no redundantes:
$$\mathbf{x}_i = \left[ \mathbf{x}_i^{(\text{viv})}, \, \mathbf{x}_i^{(\text{dem})}, \, \mathbf{x}_i^{(\text{educ})}, \, \mathbf{x}_i^{(\text{emp})} \right]^T$$

* **Vivienda ($\mathbf{x}_i^{(\text{viv})}$):** Estrato de piso (`estrato_piso`), estrato de pared (`estrato_pared`), abastecimiento de agua de red (`acceso_agua_red`), red de desagüe (`saneamiento_red`), alumbrado eléctrico, combustible de cocina seguro, ratio de hacinamiento por dormitorio (`ratio_hacinamiento`).
* **Demografía ($\mathbf{x}_i^{(\text{dem})}$):** Tamaño del hogar (truncado p99), tasa de dependencia etaria, presencia de infantes menores de 5 años (`presencia_infantes`), hogar monoparental con jefa mujer (`monoparental_femenino`).
* **Educación ($\mathbf{x}_i^{(\text{educ})}$):** Años de estudio del jefe (`jefe_anos_educacion`), máximo nivel educativo en el hogar (`hogar_max_educacion`), tasa de asistencia escolar de menores.
* **Empleo e Informalidad ($\mathbf{x}_i^{(\text{emp})}$):** Condición de empleo informal del jefe (`jefe_empleo_informal`), tasa de ocupación laboral del hogar, afiliación a sistema de pensiones del jefe (`jefe_afiliacion_pension`), tenencia de seguro de salud contributivo.

### 4.2 Espacio de Salida ($\mathcal{Y}$)
* **Probabilidad Posterior $\hat{p}_i = P(y_i = 1 \mid \mathbf{x}_i) \in [0, 1]$:** Mide el índice de privación predicho por el clasificador.
* **Decisión Operativa $\hat{y}_i = \mathbb{I}(\hat{p}_i \ge \tau^*) \in \{0, 1\}$:** Con umbral calibrado $\tau^* \approx 0.28 - 0.32$ para garantizar que el Recall de pobreza supere el 70% ante el desbalance natural de Lima.
