# Sección 2: Trabajos Relacionados

> **⚠️ Nota (Plan 2, 2026-10-08):** este documento conserva textos anteriores al levantamiento de observaciones (alcance de 5,571 hogares, matriz `INGTPUHD`, hipótesis previas, atribuciones de papers sin verificar). La versión vigente es la de los archivos `.tex` y la de [`Observaciones a levantar/Plan 2`](../../Observaciones%20a%20levantar/Plan%202/README.md).

## 1. Síntesis Crítica del Núcleo de Publicaciones Científicas

Para sustentar el diseño del pipeline y las adaptaciones algorítmicas, se seleccionó un núcleo estratégico de cuatro publicaciones primarias de alto impacto internacional indexadas en *Nature*, *NeurIPS*, *The World Bank Economic Review* y *ACM*, cubriendo los pilares de focalización social, arquitectura tabular, fallo de modelos lineales y validación temporal:

### Publicación 1: Machine Learning y Reducción del Error de Exclusión en Crisis Post-COVID
* **Referencia:** Aiken, E., Bellue, S., Karlan, D., Udry, C., & Blumenstock, J. (2022). *Machine learning and phone data can improve targeting of humanitarian aid*. **Nature**, 603(7903), 864–870.
* **Problema Abordado:** Ineficiencia y desactualización de los registros sociales estatales estáticos para focalizar transferencias monetarias de emergencia en poblaciones vulnerables durante la pandemia de COVID-19.
* **Aportes y Hallazgos:** Demostraron que el aprendizaje supervisado entrenado sobre proxies observables no monetarios reduce la tasa de error de exclusión de los hogares más pobres entre un **4% y un 21%** frente a los métodos de focalización tradicionales empleados por los gobiernos.
* **Conexión con Nuestro Proyecto:** Valida empíricamente que la Inteligencia Artificial es superior a los padrones burocráticos estáticos para identificar a las familias en extrema necesidad sin requerir mediciones directas de ingresos volátiles.

---

### Publicación 2: Superioridad de Modelos Basados en Árboles sobre Deep Learning en Datos Tabulares
* **Referencia:** Grinsztajn, L., Oyallon, E., & Varoquaux, G. (2022). *Why do tree-based models still outperform deep learning on tabular data?*. **Advances in Neural Information Processing Systems (NeurIPS 2022)**, Datasets and Benchmarks Track.
* **Problema Abordado:** La discrepancia teórica y empírica de por qué las arquitecturas de Deep Learning (MLP, ResNet, TabNet) fracasan consistentemente frente a modelos basados en árboles en datos tabulares heterogéneos.
* **Aportes y Hallazgos:** Mediante un benchmark masivo sobre 45 conjuntos de datos tabulares, probaron que el sesgo inductivo de los árboles de decisión (capacidad para modelar funciones escalonadas no suaves e invarianza ante transformaciones monótonas) se adapta de forma óptima a variables de encuestas mixtas, superando categóricamente a las redes neuronales profundas.
* **Conexión con Nuestro Proyecto:** Constituye la justificación teórica fundamental para seleccionar ensambles basados en árboles (CART, Random Forest y Gradient Boosting / LightGBM) como la arquitectura central sobre los microdatos de la ENAHO.

---

### Publicación 3: Fallo de las Regresiones Lineales de Proxy Means Testing (PMT)
* **Referencia:** McBride, L., & Nichols, A. (2018). *Retooling poverty targeting using out-of-sample machine learning and proxy means tests*. **The World Bank Economic Review**, 32(3), 531–550.
* **Problema Abordado:** Evaluación de la efectividad de las fórmulas tradicionales de Proxy Means Testing (PMT) construidas con Mínimos Cuadrados Ordinarios (MCO) frente a algoritmos de Machine Learning no paramétricos.
* **Aportes y Hallazgos:** Probaron que las regresiones MCO sufren de sobreajuste dentro de muestra (*in-sample*) y se degradan drásticamente fuera de muestra (*out-of-sample*). Los ensambles basados en árboles lograron reducir la **tasa de error de exclusión social entre un 10% y un 18%** al capturar interacciones no lineales de privación que los modelos aditivos lineales ignoran.
* **Conexión con Nuestro Proyecto:** Respalda la crítica metodológica al sistema SISFOH en Lima y Callao y justifica el reemplazo de fórmulas lineales por clasificadores de ensamble no lineales.

---

### Publicación 4: Degradación Temporal Fuera de Tiempo (*Moving Targets* y *Data Drift*)
* **Referencia:** World Bank & EAAMO (2023). *Moving targets: When does a poverty prediction model need to be updated?*. In **Proceedings of the 3rd ACM Conference on Equity and Access in Algorithms, Mechanisms, and Optimization (EAAMO 2023)**.
* **Problema Abordado:** La pérdida de precisión y sesgo algorítmico que sufren los modelos de predicción de pobreza a lo largo del tiempo debido a shocks inflacionarios y desplazamientos en el mercado laboral (*dataset drift*).
* **Aportes y Hallazgos:** Demostraron que la validación cruzada aleatoria convencional sobrestima el desempeño real al permitir fuga de información temporal (*temporal leakage*). Propusieron protocolos rigurosos de validación fuera de tiempo (*out-of-time*) entrenando en un periodo $t$ y probando en $t+1$.
* **Conexión con Nuestro Proyecto:** Fundamenta técnicamente nuestro esquema experimental estricto de partición temporal (Entrenamiento en ENAHO 2024 y Prueba Ciega en ENAHO 2025) para garantizar modelos robustos ante la inflación urbana.

---

## 2. Cuadro Comparativo Multidimensional de Enfoques en la Literatura

| Dimensión | PMT Tradicional (SISFOH / MCO) | Ayuda Humanitaria (Aiken et al., Nature) | Benchmark Tabular (Grinsztajn et al., NeurIPS) | Nuestro Enfoque (ENAHO ML Tabular PUCP) |
| :--- | :--- | :--- | :--- | :--- |
| **Algoritmo Base** | Regresión Lineal Aditiva | Gradient Boosting y Redes | Benchmark GBDT vs. Deep Learning (45 datasets) | Jerarquía del curso: Regresión Logística, CART, Random Forest y LightGBM |
| **Tipo de Variables** | Aditivas declaradas | Metadatos móviles y satelitales | Datos tabulares numéricos y categóricos mixtos | Microdatos ENAHO multimodulares (Vivienda + Demografía + Empleo informal) |
| **Tratamiento del Desbalance** | Ninguno (corte arbitrario de percentil) | Calibración de umbral por cuota presupuestal | Métricas estándar balanceadas / AUC | Función de pérdida sensible al costo ($c_1 \gg c_0$) y calibración de umbral ($\tau$) |
| **Esquema de Validación** | Rara vez evaluado fuera de muestra | Validación espacial geográfica | K-fold estratificado estándar | Validación temporal estricta fuera de tiempo (*Train 2024 $\to$ Test 2025*) |
| **Explicabilidad** | Coeficientes beta $\beta_j$ (lineal) | Coeficientes y pesos agregados | Análisis teórico de sesgo inductivo | TreeSHAP (valores exactos de Shapley por hogar) |
