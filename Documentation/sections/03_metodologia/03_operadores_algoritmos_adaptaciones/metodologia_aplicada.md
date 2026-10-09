# Metodología Aplicada: Operadores y Adaptaciones Algorítmicas en ENAHO

> **⚠️ Nota (Plan 2, 2026-10-08):** este documento conserva textos anteriores al levantamiento de observaciones (alcance de 5,571 hogares, matriz `INGTPUHD`, hipótesis previas, atribuciones de papers sin verificar). La versión vigente es la de los archivos `.tex` y la de [`Observaciones a levantar/Plan 2`](../../../Observaciones%20a%20levantar/Plan%202/README.md).

Este documento detalla la implementación y adaptación técnica de los operadores de procesamiento y los modelos de clasificación aplicados a los microdatos de la **ENAHO (2024--2025)** para Lima Metropolitana y Callao.

---

## 1. Operadores de Preprocesamiento Desarrollados

### 1.1 Operador de Imputación por Cohabitación Intra-Vivienda (`HousingCohortImputer`)
* **Problema en ENAHO:** El 2.15% de los hogares en Lima corresponden a hogares secundarios (`HOGAR 22, 33...`) que habitan cuartos alquilados o secciones compartidas dentro de la misma edificación física que el hogar principal (`HOGAR 11`). En el Módulo 01, los encuestadores del INEI omiten registrar los materiales físicos de la vivienda para estos hogares secundarios, generando nulos estructurales.
* **Implementación:**
  ```python
  def imputar_cohabitacion_vivienda(df: pd.DataFrame) -> pd.DataFrame:
      """
      Propaga atributos estructurales de la vivienda física a hogares secundarios.
      Clave de agrupación: (CONGLOME, VIVIENDA).
      """
      cols_fisicas = ['P101', 'P102', 'P103', 'P104', 'P110']
      df[cols_fisicas] = (
          df.groupby(['CONGLOME', 'VIVIENDA'])[cols_fisicas]
            .transform(lambda s: s.ffill().bfill())
      )
      return df
  ```
* **Impacto Numérico:** Resuelve el 100% de los nulos de infraestructura habitacional sin inventar datos sintéticos ni recurrir a imputaciones globales no contextualizadas.

---

### 1.2 Operador de Agregación Multinivel Relacional (`HouseholdAggregator`)
* **Problema en ENAHO:** Los módulos 02 (demografía), 03 (educación) y 05 (empleo e ingresos) registran filas a nivel de individuo (`CODPERSO`). Para vincularlos con el Módulo 01 y la etiqueta de Sumaria, se requiere un colapso dimensional hacia la clave `(CONGLOME, VIVIENDA, HOGAR)`.
* **Implementación:**
  1. **Filtro Jefe de Hogar (`P203 == 1`):**
     * Extrae: `jefe_sexo = (P207 == 2).astype(int)` (1 si es mujer).
     * `jefe_edad = P208A`
     * `jefe_educ = P301A` (nivel educativo alcanzado)
     * `jefe_informal = OCU500 == 1 & (OCU500 != 1 o sin RUC/derechos)`
     * `jefe_pension = (P558A == 1 | P558B == 1).astype(int)`
  2. **Agregaciones Colectivas del Hogar:**
     * `tamano_hogar = count(CODPERSO)`
     * `num_ninos_5 = sum(edad < 5)`
     * `num_ancianos_65 = sum(edad >= 65)`
     * `tasa_dependencia = (num_ninos_5 + num_ancianos_65) / max(1, personas_edad_15_64)`
     * `max_educ_hogar = max(P301A)`
     * `tasa_ocupacion = sum(ocupado) / max(1, personas_edad_ge_14)`

---

### 1.3 Operador de Agrupación Semántica Guiada por Dominio (`DomainBinner`)
* **Problema en ENAHO:** La variable `P103` (material de pisos) contiene 7 categorías oficiales en el manual del INEI, con frecuencias inferiores al 0.8% en categorías como "mármol/porcelanato importado" o "caña/bambú". Un *One-Hot encoding* dispersa la matriz $X$ y deteriora el ajuste.
* **Mapeo Implementado:**
  * **Pisos:**
    * Grupo 3 (Noble Acabado): Parquet, loseta, cerámico, vinílico (tasa de pobreza en muestra: 7.1%).
    * Grupo 2 (Cemento Básico): Cemento pulido o frotachado (tasa de pobreza: 24.3%).
    * Grupo 1 (Precario/Tierra): Tierra afirmada, madera rústica, caña (tasa de pobreza: 37.0%).
  * **Agua Potable:**
    * Red pública interna vs Red externa/pilón vs Camión cisterna/pozo.
  * **Combustible:**
    * Gas natural por tubería / Eléctrico vs GLP en balón vs Carbón / Leña / Biomasa.

---

## 2. Adaptaciones Algorítmicas y Configuración de Hiperparámetros

Se implementan y comparan los 4 modelos de la jerarquía del curso utilizando Scikit-Learn y LightGBM con parámetros afinados mediante búsqueda en grilla y validación cruzada estratificada de 5 particiones sobre la ENAHO 2024:

### 2.1 Regresión Logística ElasticNet (Baseline Lineal Paramétrico)
```python
from sklearn.linear_model import LogisticRegression

# c1 / c0 = 4.372 ponderado mediante class_weight
model_lr = LogisticRegression(
    penalty='elasticnet',
    solver='saga',
    l1_ratio=0.5,        # 50% L1 (selección) y 50% L2 (estabilidad)
    C=0.1,               # Fuerza de regularización
    class_weight={0: 1.0, 1: 4.372},
    max_iter=1000,
    random_state=42
)
```

### 2.2 Árbol de Decisión CART (Modelo No Paramétrico Ortogonal)
```python
from sklearn.tree import DecisionTreeClassifier

model_cart = DecisionTreeClassifier(
    criterion='gini',
    max_depth=6,         # Control estricto de sobreajuste
    min_samples_split=30,
    min_samples_leaf=15,
    class_weight={0: 1.0, 1: 4.372},
    ccp_alpha=0.002,     # Poda por costo-complejidad
    random_state=42
)
```

### 2.3 Random Forest Classifier (Ensamble por Bagging)
```python
from sklearn.ensemble import RandomForestClassifier

model_rf = RandomForestClassifier(
    n_estimators=300,
    max_depth=10,
    max_features='sqrt',
    min_samples_leaf=10,
    class_weight='balanced_subsample',
    bootstrap=True,
    n_jobs=-1,
    random_state=42
)
```

### 2.4 LightGBM Classifier (Ensamble por Boosting con Pérdida Sensible al Costo)
```python
import lightgbm as lgb

model_lgb = lgb.LGBMClassifier(
    n_estimators=350,
    learning_rate=0.03,
    num_leaves=31,
    max_depth=6,
    scale_pos_weight=4.372,  # Ponderación directa del gradiente de la clase positiva
    subsample=0.8,           # Bagging fraccional de instancias
    colsample_bytree=0.8,    # Subespacio aleatorio de columnas
    reg_alpha=0.1,           # Regularización L1 en hojas
    reg_lambda=1.0,          # Regularización L2 en hojas
    random_state=42
)
```

---

## 3. Protocolo de Calibración de Umbral Operativo

Una vez inducido el modelo, se obtienen las probabilidades posteriores $\hat{p}_i = P(y_i = 1 \mid \mathbf{x}_i)$. Para evitar que el umbral estático de 0.50 descarte a familias pobres vulnerables, se busca:
$$\tau^* = \arg\max_{\tau \in [0.15, 0.55]} F_1(\tau)$$
restringido a que la tasa de falsos negativos no supere el 30% ($\text{Recall} \ge 0.70$).
El umbral resultante se congela para su evaluación ciega e inalterable sobre la ENAHO 2025.
