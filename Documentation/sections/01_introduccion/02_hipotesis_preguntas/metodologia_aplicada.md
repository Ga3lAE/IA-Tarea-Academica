# Metodología Aplicada: Formulación de Hipótesis y Preguntas de Investigación

> [!WARNING]
> **AVISO DE VERSIÓN Y DEPRECACIÓN:** Este borrador de Capa 2 conserva cifras y formulaciones exploratorias previas. La versión oficial y evaluable es [`Documentation/sections/01_introduccion/introduccion.tex`](../introduccion.tex) y [`Documentation/latex/main.pdf`](../../../latex/main.pdf).

Este documento aterriza los marcos metodológicos abstractos (PICOT, FINER, Falsacionismo popperiano y Teoría de Evaluación en Desbalance) a la investigación sobre **clasificación de pobreza en Lima Metropolitana y Callao con la ENAHO**, adaptado estrictamente al **alcance y sílabo del curso de Inteligencia Artificial (1INF24 - PUCP)**.

---

## 1. Aterrizaje del Marco PICOT al Caso de Estudio

```text
┌────────────────────────────────────────────────────────────────────────────────────────────────────────┐
│                        MATRIZ PICOT APLICADA A LA INVESTIGACIÓN DE LA ENAHO                            │
├─────────┬──────────────────────────────────────────────────────────────────────────────────────────────┤
│ P       │ • Población y Datos: Microdatos anuales de la Encuesta Nacional de Hogares (ENAHO) del INEI  │
│(Dataset)│   correspondientes a Lima Metropolitana (Dpto. 15) y el Callao (Dpto. 07).                  │
│         │ • Tamaño Muestral: 11,160 hogares encuestados (5,571 en 2024 y 5,589 en 2025).              │
│         │ • Prevalencia de Pobreza: 18.61% hogares en 2024 y 17.41% en 2025 (clase minoritaria desbal.)│
├─────────┼──────────────────────────────────────────────────────────────────────────────────────────────┤
│ I       │ • Intervención / Modelo Propuesto: Pipeline supervisado de clasificación no lineal basado en │
│(Modelo) │   modelos de árboles de decisión (Árbol CART, Random Forest y Gradient Boosted Decision      │
│         │   Trees / LightGBM) entrenados sobre un espacio de características multidimensional          │
│         │   (Vivienda + Composición familiar/Demografía + Educación + Empleo informal) con ajuste de  │
│         │   función de pérdida sensible al costo (Cost-Sensitive Learning).                            │
├─────────┼──────────────────────────────────────────────────────────────────────────────────────────────┤
│ C       │ • Comparador / Modelo Baseline: Modelo lineal paramétrico de referencia estándar del curso   │
│(Baseline│   (Regresión Logística), análogo metodológico a las fórmulas de Proxy Means Testing que usa  │
│         │   el SISFOH tradicionalmente.                                                                │
├─────────┼──────────────────────────────────────────────────────────────────────────────────────────────┤
│ O       │ • Outcome / Métricas de Evaluación:                                                          │
│(Métricas│   - F1-score de la clase minoritaria (pobreza, y = 1).                                       │
│         │   - Tasa de detección / Recall (reducción del error de exclusión por debajo del 20%).        │
│         │   - Área bajo la curva Precision-Recall (PR-AUC).                                            │
├─────────┼──────────────────────────────────────────────────────────────────────────────────────────────┤
│ T       │ • Timeframe / Esquema Temporal: Evaluación ciega fuera de tiempo (Out-of-Time Validation):   │
│(Tiempo) │   Entrenamiento exclusivo en la muestra 2024 y prueba en la muestra 2025 (cero fuga de datos)│
└─────────┴──────────────────────────────────────────────────────────────────────────────────────────────┘
```

---

## 2. Justificación de los Conceptos Dentro del Alcance del Curso (PUCP 1INF24)

Para garantizar total claridad sobre por qué cada concepto forma parte del proyecto, se desmitifica su rol técnico y pedagógico:

### 2.1 ¿Qué son los "Proxies Demográficos" y por qué están en nuestro alcance?
* **Concepto:** Un *proxy* es simplemente una **variable sustituta o indirecta**. Debido a que el ingreso de familias informales en Lima no se puede observar directamente en planillas bancarias, se utilizan características visibles del hogar que reflejan su vulnerabilidad económica.
* **Justificación en los Datos:** En la carpeta `Data/` ya se dispone del **Módulo 02 de la ENAHO** (`Enaho01-YYYY-200.csv`), titulado *"Características de los Miembros del Hogar"*. Contiene columnas elementales: edad, sexo y parentesco con el jefe de hogar.
* **Operación Técnica:** Mediante una simple agregación tabular a nivel de hogar (`groupby`), se calculan variables de alto impacto:
  - `total_miembros`: Tamaño de la familia.
  - `hijos_menores_5`: Cantidad de niños en primera infancia.
  - `razon_dependencia`: $\frac{\text{Niños (<14)} + \text{Ancianos (>65)}}{\text{Adultos en edad laboral (15-64)}}$.
* **Vínculo con el Problema:** Un hogar con 5 dependientes y un único sostén laboral tiene una probabilidad drásticamente mayor de caer en pobreza que un hogar de 2 adultos que trabajan, independientemente de que su casa sea de ladrillo o madera.

### 2.2 ¿Por qué se usan $F_1$-score y PR-AUC en lugar de Accuracy?
* **La trampa del desbalance:** En la muestra de Lima y Callao, **el 18.61% de los hogares son pobres y el 81.39% NO lo son**.
* Si un modelo ingenuo predice siempre que ningún hogar es pobre ($\hat{y} = 0$), alcanzaría un **81.39% de Accuracy**, pero con un **Recall de 0%**: dejaría al 100% de las familias pobres sin identificar y sin ayuda del Estado.
* **Por qué están en el curso:** El sílabo de Inteligencia Artificial enseña que en problemas con clases desbalanceadas, la evaluación rigurosa exige:
  - **Recall:** Asegurar que se capture a la mayor cantidad de hogares vulnerables (minimizar falsos negativos).
  - **Precision:** Evitar entregar ayuda a hogares no pobres (controlar falsos positivos).
  - **$F_1$-score:** Evaluar el equilibrio real del modelo frente a la clase difícil.

### 2.3 ¿Por qué comparamos familias de árboles contra modelos lineales?
En lugar de imponer un único algoritmo, el proyecto evalúa el desempeño comparativo entre las distintas familias de modelos supervisados estudiadas en el curso de IA:
1. **Regresión Logística (Modelo Lineal Baseline):** Evalúa la hipótesis de si las fronteras de decisión aditivas son suficientes para modelar la pobreza.
2. **Árbol de Decisión CART (Modelo No Lineal Simple):** Evalúa si particiones jerárquicas simples tipo regla (`IF habitaciones <= 2 AND agua == cisterna THEN pobre`) mejoran la discriminación.
3. **Random Forest (Ensamble por Bagging):** Evalúa la reducción de varianza al promediar múltiples árboles entrenados sobre submuestras con reemplazo.
4. **Gradient Boosted Trees / LightGBM (Ensamble por Boosting):** Evalúa la optimización secuencial de errores. Se utiliza LightGBM como la librería estándar de la industria en Python por su alta eficiencia computacional y bajo consumo de memoria frente al `GradientBoostingClassifier` estándar de `scikit-learn`.

---

## 3. Preguntas de Investigación Formalizadas

### Pregunta General de Investigación
> **"¿En qué medida el desarrollo de un sistema de clasificación binaria supervisada basado en modelos de árboles de decisión (CART, Random Forest y Gradient Boosting), integrando características físicas de la vivienda con la composición demográfica y laboral del hogar de la ENAHO, supera a los modelos lineales tradicionales de referencia (Regresión Logística) en la detección de hogares en pobreza y en la reducción del error de exclusión social en Lima Metropolitana y el Callao bajo una evaluación temporal fuera de tiempo (2024 $\to$ 2025)?"**

### Preguntas Específicas
1. **Representación de Datos y Multidimensionalidad:**
   * *¿Qué incremento en el $F_1$-score y en la curva PR-AUC se logra al enriquecer los datos de vivienda con la composición demográfica familiar (Módulo 02) y la inserción laboral informal (Módulo 05) respecto a un clasificador alimentado únicamente por infraestructura física (Módulo 01)?*
2. **Capacidad Algorítmica (No Linealidad vs. Linealidad):**
   * *¿Logran los algoritmos de ensamble no lineales (Random Forest y Gradient Boosting) superar con significancia estadística el techo predictivo de la Regresión Logística al capturar interacciones complejas en los datos urbanos?*
3. **Optimización Social y Pérdida Asimétrica:**
   * *¿Permite la ponderación asimétrica de la función de pérdida sensible al costo ($c_1 \gg c_0$) reducir el error de exclusión de los hogares pobres (alcanzar un Recall $\ge 80\%$) sin deteriorar de manera excesiva la precisión del sistema?*
4. **Robustez y Generalización Temporal:**
   * *¿Conserva el modelo entrenado con los microdatos de 2024 su capacidad de discriminación al ser probado en un entorno ciego sobre los microdatos de 2025, o sufre una degradación severa por desplazamiento de la distribución económica (*data drift*)?*

---

## 4. Hipótesis de Investigación Científicas (Falsables)

### Hipótesis General
> **"La implementación de un clasificador supervisado de ensamble basado en árboles de decisión (Random Forest / Gradient Boosting), entrenado sobre un espacio de características multidimensional de la ENAHO (Vivienda, Demografía, Educación e Informalidad laboral) y optimizado con pérdidas sensibles al costo, incrementará el $F_1$-score de la clase en pobreza en al menos 15 puntos porcentuales respecto al modelo lineal de referencia (Regresión Logística), reduciendo la tasa de error de exclusión por debajo del 20% ($\text{Recall} \ge 80\%$) en la evaluación ciega fuera de tiempo (2024 $\to$ 2025)."**

### Hipótesis Específicas de Contraste Experimental

* **$H_1$ (Aporte del Espacio Multidimensional):**
  La combinación de los módulos de Vivienda (01) con Demografía (02) y Empleo informal (05) incrementará el área bajo la curva Precision-Recall (PR-AUC) en al menos **0.12 puntos** en comparación con el modelo entrenado únicamente con atributos habitacionales del Módulo 01.
  * *Criterio de refutación:* Si $\Delta \text{PR-AUC} < 0.12$, se refuta la hipótesis de que las variables demográficas y laborales aportan discriminación significativa sobre el hábitat físico.

* **$H_2$ (Superioridad de Ensambles sobre Modelos Lineales):**
  Los métodos de ensamble no lineales (Random Forest y Gradient Boosting) superarán a la Regresión Logística con una mejora de al menos **10 puntos porcentuales en $F_1$-score**, con diferencia estadísticamente significativa ($p < 0.05$ evaluado mediante test de McNemar sobre las predicciones pareadas).
  * *Criterio de refutación:* Si la diferencia en $F_1$-score es menor a 10 puntos o carece de significancia estadística ($p \ge 0.05$).

* **$H_3$ (Efectividad de la Pérdida Sensible al Costo):**
  La calibración asimétrica de pesos en la función de pérdida ($c_1 / c_0 \approx 4.37$, en proporción inversa a la prevalencia de pobreza) reducirá los Falsos Negativos en al menos un **35%** frente al entrenamiento estándar no ponderado, manteniendo una precisión mínima del **60%** en la clase minoritaria.
  * *Criterio de refutación:* Si la reducción de falsos negativos es inferior al 35% o la precisión se desploma por debajo del 60%.

* **$H_4$ (Estabilidad Temporal Fuera de Tiempo):**
  El modelo entrenado con microdatos del año 2024 retendrá al menos el **85% de su puntaje $F_1$ original** al ser evaluado ciegamente sobre la muestra del año 2025, demostrando resistencia frente a variaciones interanuales y cambios coyunturales del mercado urbano.
  * *Criterio de refutación:* Si el rendimiento en 2025 cae por debajo del 85% del valor alcanzado en validación cruzada interna sobre 2024.
