# Metodología Teórica: Formulación Formal del Problema de Aprendizaje Supervisado

Este documento presenta el marco matemático y conceptual abstracto para formular un problema de **Clasificación Supervisada Binaria Desbalanceada con Costos Asimétricos**, prescindiendo de cualquier referencia al caso de estudio particular o conjunto de datos específico.

---

## 1. El Marco Canónico de Aprendizaje Automático (Tom Mitchell, 1997)

Un programa computacional aprende a partir de la experiencia formalizada mediante la terna canónica $\langle T, E, P \rangle$:

1. **Tarea ($T$):**  
   Corresponde al mapeo funcional o regla de decisión inductiva:
   $$f: \mathcal{X} \to \mathcal{Y}$$
   donde $\mathcal{X} \subseteq \mathbb{R}^d$ representa el espacio euclídeo de características de dimensión $d$, y $\mathcal{Y} = \{0, 1\}$ denota el espacio discreto de etiquetas binarias. La tarea consiste en asignar a una instancia no observada $\mathbf{x} \in \mathcal{X}$ una etiqueta predicha $\hat{y} \in \mathcal{Y}$ que refleje su verdadera clase latente.

2. **Experiencia ($E$):**  
   Corresponde al conjunto finito de entrenamiento supervisado:
   $$\mathcal{D} = \{(\mathbf{x}_i, y_i)\}_{i=1}^N \sim \mathcal{P}_{\mathcal{X} \times \mathcal{Y}}$$
   donde cada par $(\mathbf{x}_i, y_i)$ se asume extraído de manera independiente e idénticamente distribuida (i.i.d.) a partir de una distribución de probabilidad conjunta subyacente $\mathcal{P}(\mathbf{X}, Y)$.

3. **Medida de Desempeño ($P$):**  
   Corresponde al funcional cuantitativo que evalúa la generalización del modelo fuera de muestra sobre una distribución de prueba $\mathcal{D}_{\text{test}}$. Cuando la distribución marginal de clases es severamente desbalanceada ($\mathbb{P}(Y=1) \ll \mathbb{P}(Y=0)$), la exactitud global (*Accuracy*) pierde validez como métrica de desempeño, requiriendo métricas basadas en la matriz de confusión:
   $$\text{Precision} = \frac{TP}{TP + FP}, \quad \text{Recall} = \frac{TP}{TP + FN}$$
   $$F_1\text{-score} = 2 \cdot \frac{\text{Precision} \cdot \text{Recall}}{\text{Precision} + \text{Recall}}$$
   así como el Área bajo la Curva de Precisión-Exhaustividad (PR-AUC), la cual es invariante ante el volumen de verdaderos negativos ($TN$).

---

## 2. Espacio de Hipótesis y Estimación Probabilística Posterior

El objetivo del aprendizaje inductivo consiste en seleccionar una función hipótesis $h \in \mathcal{H}$ que estime la probabilidad a posteriori de pertenencia a la clase positiva condicional al vector de atributos:
$$\eta(\mathbf{x}) = \mathbb{P}(Y = 1 \mid \mathbf{X} = \mathbf{x})$$

El estimador inducido $\hat{p}(\mathbf{x}) = \hat{\mathbb{P}}(Y = 1 \mid \mathbf{x})$ genera una regla de clasificación binaria mediante la aplicación de una función umbral $\tau \in [0, 1]$:
$$\hat{y} = g(\hat{p}(\mathbf{x}); \tau) = \mathbb{I}(\hat{p}(\mathbf{x}) \ge \tau)$$
donde $\mathbb{I}(\cdot)$ es la función indicatriz de Boole.

---

## 3. Función de Pérdida Sensible al Costo (*Cost-Sensitive Loss*)

En problemas reales de decisión, los errores de predicción no conllevan el mismo costo operativo, social o económico. Definamos la matriz de costos de error $\mathbf{C} \in \mathbb{R}^{2 \times 2}$:

| | Clase Real $Y = 0$ | Clase Real $Y = 1$ |
| :---: | :---: | :---: |
| **Predicción $\hat{Y} = 0$** | $C(0, 0) = 0$ | $C(0, 1) = c_{\text{FN}}$ |
| **Predicción $\hat{Y} = 1$** | $C(1, 0) = c_{\text{FP}}$ | $C(1, 1) = 0$ |

Cuando omitir una instancia positiva conlleva una penalización sustancialmente superior a generar una falsa alarma ($c_{\text{FN}} \gg c_{\text{FP}}$), la función estándar de entropía cruzada binaria no refleja el objetivo del sistema. Se formula entonces la **Pérdida Logística Ponderada Sensible al Costo**:

$$\mathcal{L}_{\text{CS}}(\theta) = -\frac{1}{N} \sum_{i=1}^N \left[ c_1 \, y_i \log(\hat{p}_i) + c_0 \, (1 - y_i) \log(1 - \hat{p}_i) \right]$$

donde los coeficientes de ponderación satisfacen:
$$\frac{c_1}{c_0} = \frac{c_{\text{FN}}}{c_{\text{FP}}} \approx \frac{\mathbb{P}(Y=0)}{\mathbb{P}(Y=1)}$$

Bajo esta parametrización, el gradiente de la función de pérdida asigna un peso mayor a los errores cometidos sobre las instancias de la clase minoritaria, forzando al algoritmo de optimización a desplazar la frontera de decisión para maximizar el Recall de dicha clase.
