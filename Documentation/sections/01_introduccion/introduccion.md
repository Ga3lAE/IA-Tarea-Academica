# Sección 1: Introducción

## 1. Descripción del Problema: Contexto, Relevancia y Justificación

### Contexto Socioeconómico y Territorial
En Lima Metropolitana y la Provincia Constitucional del Callao, la pobreza monetaria urbana experimentó una agudización severa tras la crisis sanitaria y los recientes choques inflacionarios en la canasta básica familiar. Según el Instituto Nacional de Estadística e Informática (INEI, 2024), la pobreza monetaria afectó al **28.2% de la población de la capital en 2024** (~2.9 millones de personas), duplicando los registros prepandemia (14.2% en 2019). En la muestra de microdatos de la Encuesta Nacional de Hogares (ENAHO 2024), esto se traduce en una prevalencia del **18.61% de los hogares** bajo la línea de pobreza oficial.

A diferencia del entorno rural, la pobreza metropolitana se caracteriza por ser una **"pobreza cara" y de alta volatilidad** (IEP, 2023): las familias dependen en un 100% de la compra diaria de alimentos en el mercado, asumen costos de agua por camión cisterna hasta seis veces superiores a la red pública, y subsisten ancladas a una tasa de **empleo informal del 57.3% en Lima** (INEI, 2024), alcanzando el 60.6% en mujeres y más del 75% en estratos vulnerables (GRADE, 2024).

### La Falla Estructural de la Focalización Tradicional (SISFOH / PMT Lineal)
El Sistema de Focalización de Hogares (SISFOH / MIDIS) emplea metodologías tradicionales de *Proxy Means Testing* (PMT) sustentadas en regresiones lineales por Mínimos Cuadrados Ordinarios (MCO). Este instrumento presenta tres fallas estructurales críticas en el ámbito metropolitano:
1. **Supuesto de Aditividad Lineal e Independencia:** Asume que cada atributo habitacional o demográfico suma o resta bienestar de forma aislada, ignorando interacciones no lineales complejas (por ejemplo, el impacto conjunto de jefatura informal, hacinamiento y shocks de enfermedad crónica).
2. **La Falacia de la Autoconstrucción Urbana:** En Lima, más del 70% del parque habitacional se construye de manera informal y progresiva a lo largo de décadas (GRADE, 2024). En consecuencia, los microdatos revelan que **el 59.40% de los hogares pobres residen en viviendas con paredes de ladrillo y cemento**, y **el 79.46% cuenta con pisos de cemento o loseta**. Utilizar reglas o filtros univariados basados predominantemente en la infraestructura física penaliza de forma inexacta a familias en extrema precariedad económica.
3. **Grave Brecha de Subcobertura (Error de Exclusión):** La rigidez y descalibración del sistema tradicional genera una exclusión masiva: en los microdatos de la ENAHO 2024, **739 de los 1,037 hogares pobres urbanos (el 71.26%) no reciben ninguna transferencia monetaria ni programa alimentario del Estado** (`INGTPUHD == 0`), constituyendo "hogares invisibles" desprovistos de protección social. Paralelamente, 1,299 hogares no pobres absorben recursos públicos escasos debido a errores de inclusión (filtración).

### Relevancia y Justificación del Problema
La identificación certera y oportuna de la pobreza urbana no es un mero desafío estadístico, sino una prioridad ética y de política pública. Ante la imposibilidad presupuestal y operativa de realizar censos continuos de 300 preguntas, y dada la inviabilidad de confiar en ingresos monetarios informales inobservables y subreportados, se evidencia la necesidad imperiosa de **formular un marco de inferencia no lineal capaz de mapear proxies socioeconómicos multidimensionales observables, duraderos y no manipulables** (habitabilidad, carga demográfica, capital humano y precariedad laboral) hacia la condición real de vulnerabilidad, priorizando la reducción asimétrica del error de exclusión social.

---

## 2. Decisión Arquitectónica Fundamental: ¿Por Qué Clasificación Binaria y NO Regresión Continua?

Durante la fase de diseño se evaluaron dos paradigmas predictivos del curso:
1. **Regresión Supervisada Continua del Gasto per Cápita:** Predecir el valor continuo en soles del gasto mensual por persona ($\hat{y} \in \mathbb{R}^+$) y compararlo posteriormente contra la línea de pobreza ($\text{LINEA} \approx \text{S/. } 520$).
2. **Clasificación Supervisada Binaria Directa:** Predecir directamente la pertenencia a la clase vulnerable o no vulnerable ($y \in \{0, 1\}$).

### Justificación Técnica de la Elección por Clasificación Binaria
Se determinó que la **Clasificación Binaria Directa** es metodológica y estadísticamente superior para este problema por las siguientes razones:

1. **La Distorsión de la Varianza de Altos Ingresos en el Error Cuadrático ($MSE$):**
   En Lima y Callao, el gasto per cápita presenta una distribución fuertemente asimétrica (log-normal con cola pesada), oscilando entre **S/. 97.74 y S/. 21,745.73** mensuales. Un modelo de regresión que optimiza el error cuadrático medio:
   $$\min_{\theta} \frac{1}{N} \sum_{i=1}^N (y_i - \hat{y}_i)^2$$
   asigna un costo desproporcionado a errores en hogares de clase media alta o alta. Un error de S/. 3,000 en un hogar de S/. 18,000 genera una penalización de $3,000^2 = 9,000,000$, mientras que un error crítico en la frontera de pobreza (predecir S/. 550 cuando el gasto real era S/. 450) apenas penaliza con $100^2 = 10,000$. Como consecuencia, **el modelo de regresión gasta el grueso de su capacidad matemática aprendiendo a separar a la clase media de los ricos, descuidando la frontera de los hogares pobres**.

2. **Foco Absoluto en la Frontera de Decisión Social:**
   Para efectos de la política pública de focalización, la diferencia de consumo entre un hogar de S/. 2,500 y uno de S/. 15,000 es completamente irrelevante (ambos son no pobres). La clasificación binaria mapea a todos los hogares sobre la línea como clase `0`, obligando al algoritmo a concentrar toda su capacidad de discriminación en el umbral crítico de pobreza.

3. **Optimización con Pérdidas Sensibles al Costo (*Cost-Sensitive Learning*):**
   La clasificación binaria permite incorporar funciones de pérdida asimétricas donde cometer un falso negativo (excluir a un pobre) tiene un peso de penalización significativamente mayor que cometer un falso positivo (incluir a un no pobre), propiedad inaccesible de forma directa en regresión estándar.

4. **Tratamiento Explícito del Desbalance de Clases:**
   Al formalizarse como clasificación binaria, el problema aborda de forma directa el desbalance moderado (18.6% positivos vs 81.4% negativos), permitiendo calibrar umbrales de decisión ($\tau$) y evaluar métricas idóneas del curso como $F_1$-score y PR-AUC.

---

## 3. Preguntas de Investigación e Hipótesis de Trabajo

### Pregunta General de Investigación
> *¿En qué medida el desarrollo de un sistema de clasificación binaria supervisada basado en modelos de árboles de decisión (CART, Random Forest y Gradient Boosting), integrando características físicas de la vivienda con la composición demográfica y laboral del hogar de la ENAHO, supera a los modelos lineales tradicionales de referencia (Regresión Logística) en la detección de hogares en pobreza y en la reducción del error de exclusión social en Lima Metropolitana y el Callao bajo una evaluación temporal fuera de tiempo (2024 $\to$ 2025)?*

### Preguntas Específicas
1. **Representación y Multidimensionalidad:** ¿Qué incremento en el poder predictivo ($F_1$-score y PR-AUC) aporta la integración de proxies demográficos familiares (Módulo 02) y de empleo informal (Módulo 05) respecto a un modelo basado únicamente en infraestructura física de la vivienda (Módulo 01)?
2. **Capacidad Algorítmica (No Linealidad vs. Linealidad):** ¿Logran los modelos de ensamble no lineales basados en árboles (Random Forest y Gradient Boosting) superar con significancia estadística el techo discriminatorio de la Regresión Logística al capturar interacciones socioeconómicas complejas?
3. **Optimización Social y Pérdida Asimétrica:** ¿Permite la ponderación asimétrica de la función de pérdida sensible al costo ($c_1 \gg c_0$) reducir el error de exclusión de los hogares pobres (alcanzar un Recall $\ge 80\%$) sin deteriorar desproporcionadamente la precisión del sistema?
4. **Robustez y Generalización Temporal:** ¿Conserva el modelo entrenado con los microdatos de 2024 su capacidad de discriminación al ser evaluado en un entorno ciego sobre los microdatos de 2025, o experimenta una degradación severa por desplazamiento de la distribución económica (*data drift*)?

### Hipótesis General
> *La implementación de un clasificador supervisado de ensamble basado en árboles de decisión (Random Forest / Gradient Boosting), entrenado sobre un espacio de características multidimensional de la ENAHO (Vivienda, Demografía, Educación e Informalidad laboral) y optimizado con pérdidas sensibles al costo, incrementará el $F_1$-score de la clase en pobreza en al menos 15 puntos porcentuales respecto al modelo lineal de referencia (Regresión Logística), reduciendo la tasa de error de exclusión por debajo del 20% ($\text{Recall} \ge 80\%$) en la evaluación ciega fuera de tiempo (2024 $\to$ 2025).*

### Hipótesis Específicas de Contraste Experimental
* **$H_1$ (Aporte Multidimensional):** La inclusión combinada de proxies de composición familiar (Módulo 02) y empleo informal (Módulo 05) junto al hábitat incrementará el área bajo la curva Precision-Recall (PR-AUC) en al menos **0.12 puntos** frente al modelo exclusivo de vivienda (Módulo 01).
* **$H_2$ (Superioridad de Ensambles):** Los métodos de ensamble no lineales superarán a la Regresión Logística con una ventaja $\ge 10$ puntos porcentuales en $F_1$-score, con significancia estadística ($p < 0.05$ evaluado mediante el test de McNemar).
* **$H_3$ (Efectividad Sensible al Costo):** La calibración asimétrica de pesos de pérdida ($c_1 / c_0 \approx 4.37$) reducirá los Falsos Negativos en al menos un **35%** frente al modelo estándar no ponderado, manteniendo una precisión $\ge 60\%$.
* **$H_4$ (Estabilidad Temporal Out-of-Time):** El clasificador retendrá al menos el **85% de su puntaje $F_1$ original** al evaluarse ciegamente sobre la muestra del año 2025 frente al año de entrenamiento 2024.

---

## 4. Objetivos del Proyecto

### Objetivo General
Desarrollar, entrenar y evaluar comparativamente un sistema de clasificación binaria supervisado basado en modelos de árboles de decisión (CART, Random Forest y Gradient Boosting), integrando microdatos multidimensionales de vivienda, composición familiar y empleo informal de la ENAHO, para optimizar la identificación de hogares en condición de pobreza monetaria y reducir asimétricamente el error de exclusión social en Lima Metropolitana y el Callao bajo una evaluación temporal fuera de tiempo (2024 $\to$ 2025).

### Objetivos Específicos
1. **Ingesta y Limpieza Modular de Datos:** Construir e implementar un pipeline modular de software bajo principios SOLID (patrón *Template Method*) que automatice la ingestión, detección de delimitadores, filtrado geográfico y la resolución de nulos estructurales por cohabitación intra-vivienda en los módulos 01, 02, 03, 05 y 34 de la ENAHO, garantizando un 0% de valores faltantes y consistencia relacional.
2. **Ingeniería de Características y Representación Multidimensional:** Diseñar y estructurar operadores de agregación relacional a nivel de hogar ($\text{individuo} \to \text{hogar}$) para incorporar proxies de composición demográfica familiar (Módulo 02), educación del jefe (Módulo 03) e informalidad laboral (Módulo 05), aplicando agrupación semántica (*Domain-based Binning*) sobre variables habitacionales para mitigar la dispersión en categorías raras sin perder señal socioeconómica.
3. **Modelado y Optimización con Pérdida Asimétrica:** Entrenar y optimizar la jerarquía de modelos de clasificación supervisada estudiados en el curso (Regresión Logística baseline, Árbol CART, Random Forest y Gradient Boosting / LightGBM), calibrando funciones de pérdida sensibles al costo (*Cost-Sensitive Loss*) mediante ponderación asimétrica ($c_1 / c_0 \approx 4.37$) para penalizar con mayor severidad los Falsos Negativos (hogares pobres excluidos) sobre los Falsos Positivos.
4. **Evaluación Experimental y Auditoría de Explicabilidad:** Evaluar el desempeño de los modelos en un esquema ciego fuera de tiempo (*Train 2024 $\to$ Test 2025*) mediante métricas adaptadas al desbalance de clases ($F_1$-score, Recall, PR-AUC), auditando la atribución de importancia e interacciones no lineales con valores de Shapley (TreeSHAP) para garantizar la interpretabilidad y equidad ética del sistema.
