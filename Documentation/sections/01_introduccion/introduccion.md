# Sección 1: Introducción

## 1. Descripción del Problema: Contexto, Relevancia y Justificación

### Contexto Socioeconómico
En Lima Metropolitana y la Provincia Constitucional del Callao, la pobreza monetaria urbana experimentó un incremento significativo tras los recientes choques inflacionarios y la precarización del mercado laboral, situándose en **18.61% en 2024** y **17.41% en 2025** según la Encuesta Nacional de Hogares (ENAHO) del Instituto Nacional de Estadística e Informática (INEI). A diferencia del entorno rural, la pobreza urbana se caracteriza por una alta volatilidad y heterogeneidad: familias enteras fluctúan alrededor del umbral de subsistencia debido a la dependencia de ingresos informales del día a día.

### El Problema de la Focalización Tradicional (Falla de los Modelos Lineales)
Los programas sociales en el Perú (SISFOH / MIDIS, transferencias condicionadas como Juntos, Pensión 65 y bonos de emergencia) emplean metodologías tradicionales de *Proxy Means Testing* (PMT) fundamentadas en regresiones lineales por mínimos cuadrados ordinarios (MCO / OLS). Este enfoque presenta tres fallas estructurales críticas:
1. **Supuesto de Aditividad Lineal:** Asume que cada atributo habitacional o demográfico aporta de forma independiente y constante al nivel de vida, ignorando interacciones no lineales complejas (por ejemplo, el efecto conjunto de cohabitación multifamiliar con jefatura laboral informal).
2. **Sensibilidad al Subreporte y Volatilidad del Ingreso:** En un contexto donde la informalidad laboral urbana supera el 65%, los ingresos monetarios son altamente estacionales e impredecibles, además de sufrir de subreporte sistemático por desconfianza ciudadana.
3. **Alto Error de Exclusión (Falsos Negativos):** Los modelos lineales rígidos penalizan de manera inexacta a hogares vulnerables, cometiendo errores de exclusión que privan de asistencia social a familias que realmente se encuentran bajo la línea de pobreza.

### Justificación de la Inteligencia Artificial / Aprendizaje Automático
Frente a las limitaciones de los censos periódicos y las mediciones de consumo de alta latencia, el Aprendizaje Automático Supervisado permite inducir una función de mapeo $f: \mathcal{X} \to \mathcal{Y}$ a partir de atributos observables, duraderos y de bajo costo de verificación (materiales físicos de la vivienda, acceso a servicios en red, estructura de dependencia demográfica e inserción laboral informal). Esto permite automatizar la identificación de vulnerabilidad con alta precisión y capacidad de actualización anual continua.

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

## 3. Hipótesis y Pregunta de Investigación

### Pregunta de Investigación
> *¿En qué medida un pipeline de aprendizaje automático supervisado basado en clasificadores no lineales (Gradient Boosted Decision Trees), adaptado con reducción dimensional semántica y optimización sensible al costo, supera a los modelos lineales tradicionales de PMT en la identificación de hogares en condición de pobreza en Lima Metropolitana y Callao?*

### Hipótesis de Trabajo
> *La implementación de un modelo de ensamble no paramétrico (LightGBM/XGBoost) entrenado sobre un espacio de características multidimensional consolidado (Vivienda, Demografía, Educación y Empleo informal), con preprocesamiento guiado por dominio y ajuste contra el desbalance de clases, incrementará el $F_1$-score de la clase minoritaria (pobreza) en al menos 15 puntos porcentuales respecto al modelo lineal de referencia (Regresión Logística), reduciendo el error de exclusión social por debajo del 20% en una evaluación ciega fuera de tiempo (out-of-time 2024 $\to$ 2025).*

---

## 4. Objetivos del Proyecto

### Objetivo General
Desarrollar, entrenar, validar y analizar un sistema de clasificación binaria supervisado basado en ensambles de árboles de decisión para clasificar hogares en situación de pobreza en Lima Metropolitana y el Callao utilizando microdatos multi-anuales de la ENAHO.

### Objetivos Específicos
1. **Ingesta y Limpieza Modular:** Construir un pipeline modular de datos (principios SOLID, patrón Template Method) para integrar, depurar y resolver valores faltantes estructurales por cohabitación en los módulos 01, 02, 03, 05 y 34 de la ENAHO.
2. **Ingeniería de Características y Agrupación Semántica:** Diseñar operadores de agregación multinivel ($\text{individuo} \to \text{hogar}$) y un esquema de agrupación semántica (*Domain-based Binning*) para mitigar la alta cardinalidad y las colas largas en variables habitacionales sin destruir la señal socioeconómica.
3. **Modelado y Optimización de Clasificadores:** Entrenar y comparar algoritmos supervisados de clasificación (Regresión Logística baseline, Árboles CART, Random Forest y LightGBM) incorporando funciones de pérdida sensibles al costo para penalizar asimétricamente el error de exclusión.
4. **Evaluación Rigurosa y Explicabilidad:** Evaluar el rendimiento del clasificador mediante partición temporal out-of-time (entrenamiento en 2024, prueba en 2025) con métricas orientadas a desbalance ($F_1$-score, Recall, PR-AUC), garantizando estricto control de fuga de datos (*zero data leakage*) y auditando la importancia de variables con TreeSHAP.
