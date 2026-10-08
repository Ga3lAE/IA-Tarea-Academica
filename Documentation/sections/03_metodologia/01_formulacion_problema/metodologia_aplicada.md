# Metodología Aplicada: Formulación Matemática del Clasificador de Pobreza Urbana

Este documento materializa el marco matemático abstracto de aprendizaje supervisado sobre el caso concreto de clasificación de pobreza de hogares en **Lima Metropolitana y la Provincia Constitucional del Callao** a partir de los microdatos oficiales de la **ENAHO**.

---

## 1. Instanciación del Marco Canónico $\langle T, E, P \rangle$

### 1.1 Tarea de Aprendizaje ($T$)
Clasificación binaria supervisada a nivel de **hogar** $i$, formalizada como la inducción de una función de hipótesis $\hat{y}_i = f(\mathbf{x}_i)$, donde:
$$y_i = \begin{cases} 
1 & \text{si el hogar se encuentra en situación de Pobreza Total (Extrema o No Extrema)} \\ 
0 & \text{si el hogar se encuentra en situación de No Pobreza} 
\end{cases}$$

La etiqueta de verdad fundamental (*ground truth*) proviene de la variable agregada oficial `POBREZA` del Módulo 34 (Sumaria) del INEI, re-codificada como:
$$y_i = \mathbb{I}(\text{POBREZA}_i \in \{1, 2\})$$
donde $\text{POBREZA}_i = 1$ indica Pobreza Extrema (gasto per cápita inferior a la canasta básica de alimentos), $\text{POBREZA}_i = 2$ indica Pobreza No Extrema (gasto per cápita inferior a la canasta básica total de consumo) y $\text{POBREZA}_i = 3$ indica No Pobreza.

### 1.2 Experiencia Supervisada ($E$)
La muestra de entrenamiento y ajuste $\mathcal{D}_{\text{train}}$ corresponde al conjunto de microdatos de la **ENAHO 2024** para Lima Metropolitana y Callao (`DOMINIO == 8` y `DEPARTAMENTO == 15, 07`):
$$\mathcal{D}_{\text{train}} = \{(\mathbf{x}_i, y_i)\}_{i=1}^{N_{\text{train}}}, \quad \text{con } N_{\text{train}} = 5,571 \text{ hogares observados}$$

La distribución empírica de clases en la muestra no expandida es:
* **Hogares Pobres ($y_i = 1$):** $1,037$ hogares (**$18.61\%$**).
* **Hogares No Pobres ($y_i = 0$):** $4,534$ hogares (**$81.39\%$**).
* **Razón de Desbalance Empírico ($\gamma$):**
  $$\gamma = \frac{N_{y=0}}{N_{y=1}} = \frac{4,534}{1,037} \approx 4.372$$

Para la evaluación final de generalización estricta, la experiencia se extiende al conjunto fuera de tiempo (*out-of-time*) de la **ENAHO 2025** ($\mathcal{D}_{\text{test}}$), garantizando ausencia de contaminación temporal.

### 1.3 Medida de Desempeño Cuantitativa ($P$)
Debido al desbalance 1:4.37 y a la asimetría del costo de exclusión de políticas públicas, el modelo se evalúa sobre las siguientes métricas:
1. **$F_1$-score de la clase minoritaria ($y=1$):** Maximización de la media armónica entre precisión y exhaustividad en la detección de hogares pobres.
2. **Recall / Sensibilidad de Pobreza ($1 - \text{Error de Exclusión}$):** Objetivo operacional: alcanzar $\text{Recall} \ge 0.70$ sobre la muestra ciega 2025.
3. **PR-AUC (Área bajo la curva Precision-Recall):** Métrica primaria de discriminación global independiente del umbral.
4. **Brier Score:** Para medir la calibración probabilística de $\hat{p}_i = P(y_i = 1 \mid \mathbf{x}_i)$.

---

## 2. Formulación Matemática de la Pérdida Asimétrica Sensible al Costo

El error de exclusión (clasificar a un hogar pobre como no pobre, privándolo de asistencia social) genera una trampa de pobreza intergeneracional y desnutrición infantil crónica. Por el contrario, el error de inclusión (otorgar un beneficio a un hogar no pobre vulnerable) genera un costo de ineficiencia presupuestal estatal acotado.

Por consiguiente, se establece una relación de penalización $c_{\text{FN}} \approx 4.37 \cdot c_{\text{FP}}$. La función de pérdida a optimizar para los clasificadores probabilísticos (Regresión Logística y LightGBM) se define como:

$$\mathcal{L}_{\text{CS}}(\mathbf{w}) = -\frac{1}{N} \sum_{i=1}^N \left[ 4.372 \cdot y_i \log(\hat{p}_i(\mathbf{w})) + 1.0 \cdot (1 - y_i) \log(1 - \hat{p}_i(\mathbf{w})) \right] + \lambda \Omega(\mathbf{w})$$

donde:
* $\hat{p}_i(\mathbf{w}) = \sigma(\mathbf{w}^T \mathbf{x}_i) = \frac{1}{1 + e^{-\mathbf{w}^T \mathbf{x}_i}}$ para el caso lineal/logístico.
* $\Omega(\mathbf{w})$ es el término de regularización (ElasticNet para regresión logística o regularización de hojas $L_1/L_2$ para LightGBM).

---

## 3. Función de Decisión y Calibración Operativa del Umbral ($\tau^*$)

El clasificador no emplea el umbral arbitrario de $\tau = 0.50$ (el cual asumiría clases balanceadas y costos simétricos). La asignación binaria final sigue la regla:

$$\hat{y}_i = \mathbb{I}(\hat{p}_i \ge \tau^*)$$

El umbral óptimo $\tau^*$ se determina mediante búsqueda lineal sobre el conjunto de validación interna:
$$\tau^* = \arg\max_{\tau \in [0.10, 0.60]} F_1(\tau; \mathcal{D}_{\text{val}})$$
sujeto a la restricción operativa de política pública:
$$\text{Recall}(\tau^*; \mathcal{D}_{\text{val}}) \ge 0.70$$
