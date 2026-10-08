# Sección 2: Trabajos Relacionados

## 1. Síntesis Crítica de Publicaciones Científicas Relevantes

Para sustentar el diseño del pipeline y las adaptaciones algorítmicas, se analizaron cuatro publicaciones científicas de alto impacto internacional indexadas en Scopus y Web of Science:

### Publicación 1: Proxy Means Testing mediante Machine Learning en Países en Desarrollo
* **Referencia:** McBride, L., & Nichols, A. (2018). *Retooling poverty targeting using out-of-sample machine learning and proxy means tests*. **The World Bank Economic Review**, 32(3), 531-550.
* **Problema Abordado:** Evaluación de la efectividad de fórmulas tradicionales de Proxy Means Testing (PMT) construidas con Mínimos Cuadrados Ordinarios (MCO) frente a algoritmos de Machine Learning (Lasso, Ridge, Random Forest y Gradient Boosting) para la asignación de transferencias monetarias en Bolivia, Timor-Leste y Malawi.
* **Aportes y Hallazgos Principales:**
  * Los autores demuestran que las regresiones MCO convencionales sufren de sobreajuste dentro de muestra (*in-sample*) y se degradan severamente al aplicarse fuera de muestra (*out-of-sample*).
  * Los algoritmos de ensambles basados en árboles lograron reducir la **tasa de error de exclusión social entre un 10% y un 18%** en comparación con los modelos de PMT paramétricos de los gobiernos.
  * Concluyen que la no linealidad inherente de los árboles de decisión permite capturar umbrales de privación multidimensional que los modelos aditivos lineales pasan por alto.
* **Conexión Directa con Nuestro Proyecto:** Constituye la principal justificación empírica para abandonar los modelos lineales tipo SISFOH en Lima y Callao y adoptar Gradient Boosted Decision Trees (GBDT).

---

### Publicación 2: Inferencia de Bienestar y Pobreza Mediante Proxies No Monetarios
* **Referencias:** 
  * Jean, N., Burke, M., Sherrie, M., Ermon, S., Lobell, D. B., & Biswas, S. (2016). *Combining satellite imagery and machine learning to predict poverty*. **Science**, 353(6301), 790-794.
  * Blumenstock, J., Cadamuro, G., & On, R. (2015). *Predicting poverty and wealth from mobile phone metadata and machine learning*. **Science**, 350(6264), 1073-1076.
* **Problema Abordado:** La dificultad de medir el consumo y la pobreza en países en desarrollo debido al alto costo, infrecuencia y retraso temporal de los censos de población e ingresos.
* **Aportes y Hallazgos Principales:**
  * Demostraron que variables observables indirectas (calidad de materiales de los techos y pisos, acceso a redes eléctricas, infraestructura de transporte) correlacionan con coeficientes superiores al 70% con las encuestas de gasto de los hogares del Banco Mundial (LSMS).
  * La acumulación de activos duraderos en el hogar filtra el ruido estacional de los ingresos transitorios y refleja la verdadera capacidad económica permanente (*Permanent Income Hypothesis*).
* **Conexión Directa con Nuestro Proyecto:** Valida la estrategia de utilizar los atributos habitacionales del Módulo 01 (pisos, paredes, saneamiento, combustibles) y demográficos del Módulo 02 como estimadores estables de la pobreza sin requerir mediciones directas de ingresos.

---

### Publicación 3: Algoritmos Tabulares Avanzados y Manejo de Desbalance de Clases
* **Referencias:** 
  * Ke, G., Meng, Q., Finley, T., Wang, T., Chen, W., Ma, W., ... & Liu, T. Y. (2017). *LightGBM: A highly efficient gradient boosting decision tree*. **Advances in Neural Information Processing Systems (NeurIPS)**, 30.
  * Fernández, A., García, S., Herrera, F., & Chawla, N. V. (2018). *SMOTE for learning from imbalanced data: progress and challenges*. **Journal of Artificial Intelligence Research**, 61, 863-905.
* **Problema Abordado:** Optimización computacional de ensambles de árboles de decisión sobre datos tabulares heterogéneos y aprendizaje bajo distribuciones asimétricas de clases.
* **Aportes y Hallazgos Principales:**
  * Ke et al. demostraron que la partición leaf-wise de LightGBM combinada con *Gradient-based One-Side Sampling* (GOSS) y *Exclusive Feature Bundling* (EFB) alcanza convergencia acelerada y alta capacidad de discriminación en datasets con mezclas de variables continuas y categóricas.
  * Fernández et al. revisaron 15 años de investigación en desbalance y evidenciaron que en datos tabulares con interacciones no lineales densas, el sobremuestreo sintético indiscriminado (SMOTE) puede generar instancias artificiales en regiones de solapamiento de clases, recomendando en su lugar el **ajuste de umbral de decisión (*Threshold Moving*)** y el **aprendizaje sensible al costo (*Cost-Sensitive Learning*)**.
* **Conexión Directa con Nuestro Proyecto:** Guía la elección de LightGBM como modelo principal y el uso de funciones de pérdida asimétricas ponderadas para contrarrestar la proporción 18.6% / 81.4% de pobreza en Lima y Callao sin distorsionar la distribución natural de los datos.

---

## 2. Cuadro Comparativo de Enfoques en la Literatura

| Dimensión | PMT Tradicional (SISFOH / OLS) | Modelos Satelitales (Jean et al.) | Nuestro Enfoque (ENAHO ML Tabular) |
| :--- | :--- | :--- | :--- |
| **Algoritmo Base** | Regresión Lineal MCO | Redes Convolucionales (CNN) | Gradient Boosted Trees (LightGBM) |
| **Tipo de Variables** | Aditivas declaradas | Imágenes satelitales / NTL | Microdatos multimodulares (Vivienda + Empleo + Demografía) |
| **Nivel de Resolución** | Hogar (estático) | Clúster / Distrito agregado | Hogar individual con agregación multinivel |
| **Tratamiento del Desbalance** | Ninguno (corte MCO arbitrario) | N/A (regresión espacial continua) | Cost-Sensitive Loss + Calibración de Umbral ($\tau$) |
| **Evaluación Fuera de Tiempo** | Rara vez evaluado | Validación espacial geográfica | Partición temporal estricta (2024 $\to$ 2025) |
| **Explicabilidad** | Coeficientes beta $\beta_j$ | Grad-CAM (mapas de calor) | TreeSHAP (valores Shapley auditables) |
