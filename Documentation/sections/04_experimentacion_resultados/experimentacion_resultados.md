# Sección 4: Experimentación y Resultados

## 1. Setup Experimental Detallado

### Datos Usados y Origen
* **Fuente:** Microdatos oficiales de la Encuesta Nacional de Hogares (ENAHO), ejecutada por el Instituto Nacional de Estadística e Informática (INEI).
* **Módulos Integrados:**
  * Módulo 01: Características de la Vivienda y del Hogar.
  * Módulo 02: Características de los Miembros del Hogar (Demografía).
  * Módulo 03: Educación.
  * Módulo 05: Empleo e Ingresos (Informalidad y ocupación).
  * Módulo 34: Sumaria (Cálculo de la etiqueta de pobreza).
* **Ámbito Geográfico:** Departamento de Lima (código UBIGEO prefijo `15`) y Provincia Constitucional del Callao (prefijo `07`).
* **Volumen Muestral:**
  * ENAHO 2024 (Encuesta 966): **5,571 hogares**.
  * ENAHO 2025 (Encuesta 1031): **5,589 hogares**.
  * Total acumulado: **11,160 hogares**.

---

### Métricas de Evaluación
Dado el desbalance de clases (18.6% positivos vs 81.4% negativos), la exactitud global (*Accuracy*) resulta una métrica engañosa. El sistema se evalúa mediante:

1. **$F_1$-Score de la Clase Minoritaria (Pobreza):**
   $$F_1 = 2 \cdot \frac{\text{Precision} \cdot \text{Recall}}{\text{Precision} + \text{Recall}}$$
   Representa la media armónica entre la precisión y la exhaustividad de detección de hogares vulnerables.
2. **Recall / Sensibilidad ($\text{TPR}$):**
   $$\text{Recall} = \frac{TP}{TP + FN} = 1 - \text{Tasa de Error de Exclusión}$$
   Métrica crítica de política pública: mide la proporción de hogares verdaderamente pobres que reciben asistencia.
3. **Área Bajo la Curva Precision-Recall (PR-AUC):**
   Métrica robusta recomendada por la literatura para evaluar modelos tabulares con clases desbalanceadas.
4. **Área Bajo la Curva ROC (ROC-AUC):**
   Capacidad global del clasificador para ordenar pares aleatorios de clases positivas y negativas.
5. **Brier Score:**
   $$\text{BS} = \frac{1}{N} \sum_{i=1}^N (\hat{p}_i - y_i)^2$$
   Evalúa la calibración probabilística de las predicciones.

---

### Plan de Experimentos y Estrategia de Validación
Se planificaron tres experimentos computacionales sistemáticos:

1. **Experimento 1: Comparación de Familias de Algoritmos (Benchmark):**
   * *Modelos evaluados:*
     1. Regresión Logística (L2 penalizada / ElasticNet).
     2. Árbol de Decisión CART (sin poda vs con poda $\alpha$).
     3. Random Forest (100 a 500 árboles, bootstrap).
     4. LightGBM / XGBoost con función de pérdida sensible al costo.
   * *Estrategia de Validación:* 5-Fold Stratified Cross-Validation sobre la base 2024.
2. **Experimento 2: Impacto del Preprocesamiento (Ablation Study):**
   * Evaluar el clasificador bajo tres configuraciones de ingeniería de características:
     * *Configuración A (Cruda):* One-Hot Encoding estándar sobre todas las categorías originales (incluidas colas $<1\%$).
     * *Configuración B (Domain Binning):* Agrupación semántica guiada por dominio de materiales y servicios.
     * *Configuración C (Multimodal Completa):* Domain Binning + Agregaciones demográficas del Módulo 02 + Informalidad del Módulo 05.
3. **Experimento 3: Validación Fuera de Tiempo (*Out-of-Time Test*):**
   * Entrenar el modelo óptimo exclusivamente con el año 2024 completo.
   * Evaluar a ciegas sobre el año 2025 para comprobar la resistencia a la deriva conceptual (*concept drift*) y la estabilidad temporal de los proxies habitacionales.

---

### Preguntas Guía que Responderán los Experimentos:
1. **¿El enfoque desarrollado resuelve siempre el problema?**
   Evalúa si el modelo identifica hogares pobres en distritos heterogéneos y con tipologías habitacionales diversas (ladrillo vs madera).
2. **¿Qué tan eficientemente lo resuelven?**
   Mide tiempos de entrenamiento e inferencia (milisegundos por hogar).
3. **¿Cuál es el desempeño comparado con otros modelos de referencia?**
   Contrasta el incremento de $F_1$-score de LightGBM frente al baseline lineal de Regresión Logística.
4. **¿Cómo influyen los parámetros en su desempeño?**
   Analiza la sensibilidad frente a la profundidad máxima de los árboles (`max_depth`), la tasa de aprendizaje (`learning_rate`) y el factor de penalización asimétrica ($c_1/c_0$).
