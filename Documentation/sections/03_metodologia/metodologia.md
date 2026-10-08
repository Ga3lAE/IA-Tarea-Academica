# Sección 3: Metodología

## 1. Desmitificación Empírica: ¿Por Qué la Pobreza No es un Árbol Simple de Materiales?

Durante la exploración inicial se planteó una interrogante crítica:  
*¿Podría este problema degenerar en un árbol de decisión trivial de 2 o 3 reglas (ejemplo: si la pared es de madera o estera, entonces el hogar es pobre)?*

Para responder rigurosamente, se evaluaron los **5,571 hogares de Lima Metropolitana y el Callao** (ENAHO 2024), contrastando las condiciones habitacionales contra la etiqueta oficial de pobreza monetaria de Sumaria (**18.61% pobres vs 81.39% no pobres**). La evidencia empírica desmintió de forma contundente cualquier regla trivial:

### Evidencia Empírica de los Datos:
1. **El 59.40% de los hogares pobres en Lima viven en casas con paredes de LADRILLO Y BLOQUE DE CEMENTO:**
   De los 1,037 hogares pobres identificados, 616 habitan viviendas consolidadas de albañilería noble.
2. **El 65.03% de los hogares con paredes de MADERA NO SON POBRES:**
   De 509 hogares con pared de madera, 331 tienen ingresos y consumo per cápita superiores a la línea de pobreza.
3. **El 70.18% de los hogares con paredes de ADOBE NO SON POBRES:**
   De 560 hogares con adobe, 393 pertenecen al estrato no pobre.
4. **El 79.46% de los hogares pobres tienen PISO DE CEMENTO O LOSETA:**
   Solo una minoría de los pobres urbanos habita sobre pisos de tierra pura.

### Explicación del Fenómeno: Pobreza Multidimensional e Interacciones No Lineales
En el entorno urbano, una vivienda de ladrillo construida hace décadas en distritos populares (San Juan de Lurigancho, Comas, Villa El Salvador) puede albergar hoy a un núcleo familiar de 6 personas sostenido por un único trabajador informal sin contrato ni pensión. A pesar de la solidez física de las paredes, el gasto per cápita cae a S/. 280 mensuales, situando al hogar en pobreza monetaria.

Por el contrario, una pareja joven sin hijos que recién adquiere un lote con paredes de madera pero cuyos dos integrantes trabajan como técnicos formales gana S/. 3,200 mensuales combinados (gasto per cápita S/. 1,600), siendo holgadamente no pobres.

**Conclusión Metodológica:** Ningún clasificador basado exclusivamente en el Módulo de Vivienda (01) puede resolver el problema. Se requiere obligatoriamente capturar las **interacciones no lineales entre Vivienda (Módulo 01), Demografía y Dependencia (Módulo 02), Capital Humano (Módulo 03) e Informalidad Laboral (Módulo 05)**.

---

## 2. Formalización Matemática del Problema (Framework de Aprendizaje Supervisado)

Siguiendo la formalización canónica de Tom Mitchell (1997) establecida en el curso:

* **Tarea ($T$):** Clasificación binaria que asigna a cada hogar $i$ una etiqueta $\hat{y}_i \in \{0, 1\}$, donde:
  $$y_i = \begin{cases} 1 & \text{si el hogar está en Pobreza Total (Extrema o No Extrema)} \\ 0 & \text{si el hogar es No Pobre} \end{cases}$$
* **Experiencia ($E$):** Muestra de microdatos multi-anual etiquetada $\mathcal{D}_{\text{train}} = \{(\mathbf{x}_i, y_i)\}_{i=1}^N$, donde cada vector $\mathbf{x}_i \in \mathcal{X} \subset \mathbb{R}^d$ sintetiza atributos habitacionales, demográficos y laborales.
* **Medida de Desempeño ($P$):**
  * $F_1$-score de la clase minoritaria (media armónica entre Precision y Recall).
  * Área bajo la curva Precision-Recall (PR-AUC).
  * Sensibilidad / Recall de la clase pobre ($1 - \text{Tasa de Error de Exclusión}$).
  * Brier Score (para calibración de probabilidades).

### Función de Pérdida Sensible al Costo (*Cost-Sensitive Loss*)
Dado que el error de exclusión social (dejar sin subsidio a un hogar pobre, Falso Negativo) tiene un costo social mucho mayor que el error de inclusión (dar subsidio a un no pobre, Falso Positivo), se parametriza la función de pérdida asimétrica:
$$\mathcal{L}(\theta) = -\frac{1}{N} \sum_{i=1}^N \left[ c_1 y_i \log(\hat{p}_i) + c_0 (1 - y_i) \log(1 - \hat{p}_i) \right]$$
donde $c_1 > c_0$ (típicamente $c_1 / c_0 \approx \frac{1 - \pi}{\pi} \approx \frac{0.814}{0.186} \approx 4.37$) balancea la penalización del gradiente.

---

## 3. Comportamiento Entrada / Salida

* **Espacio de Entrada ($\mathcal{X}$):** Vector multidimensional derivado del cruce de 4 módulos a nivel de hogar:
  1. *Vivienda (Módulo 01):* Calidad de piso, pared, techo, tipo de vivienda, abastecimiento de agua, saneamiento, combustible de cocina, tenencia jurídica (título, SUNARP), total de dormitorios, indicador de hacinamiento, internet, cable.
  2. *Demografía (Módulo 02):* Tamaño del hogar, número de niños menores de 5 años, adultos mayores, tasa de dependencia demográfica, sexo y edad del jefe de hogar.
  3. *Educación (Módulo 03):* Años de educación formal del jefe de hogar, máximo nivel educativo en la familia, asistencia escolar de menores.
  4. *Empleo e Informalidad (Módulo 05):* Condición de actividad del jefe (ocupado/desocupado/inactivo), condición de informalidad (empleo sin RUC ni derechos), afiliación a pensión (AFP/ONP), horas semanales trabajadas, tasa de ocupación familiar.
* **Espacio de Salida ($\mathcal{Y}$):** Probabilidad posterior estimada $\hat{p}_i = P(y_i = 1 \mid \mathbf{x}_i) \in [0, 1]$ y clasificación binaria discreta $\hat{y}_i = \mathbb{I}(\hat{p}_i \ge \tau)$, donde el umbral $\tau$ se optimiza mediante búsqueda lineal sobre el conjunto de validación.

---

## 4. Operadores y Adaptaciones Algorítmicas Desarrolladas

### 1. Imputación Intra-Vivienda por Cohabitación Multifamiliar
En la ENAHO, el 2.15% de los hogares en Lima corresponden a hogares secundarios (`HOGAR 22, 33...`) que alquilan cuartos o comparten la vivienda física con el hogar principal (`HOGAR 11`). Para estos hogares secundarios, el encuestador del INEI deja vacías las preguntas de materiales físicos de la vivienda.
* **Operador:** Se diseñó un operador de propagación agrupada por clave física `(CONGLOME, VIVIENDA)` mediante forward-fill y backward-fill (`ffill().bfill()`), resolviendo el 100% de los nulos estructurales sin imputar valores sintéticos ajenos a la vivienda real.

### 2. Agregación Multinivel ($\text{Individuo} \to \text{Hogar}$)
Los módulos 02, 03 y 05 vienen a nivel de persona (`CODPERSO`). Para llevarlos a nivel de hogar `(CONGLOME, VIVIENDA, HOGAR)`, se implementó un operador dual $\Phi(\cdot)$:
* **Rama Jefe de Hogar ($P203 = 1$):** Extrae directamente los atributos del decisor principal del hogar (sexo, edad, nivel educativo, informalidad laboral, pensión).
* **Rama Núcleo del Hogar:** Aplica funciones de agregación estadística:
  $$\text{tamano\_hogar} = \sum \mathbb{I}(\text{persona}), \quad \text{tasa\_dependencia} = \frac{\sum \mathbb{I}(\text{edad} < 15 \lor \text{edad} \ge 65)}{\sum \mathbb{I}(15 \le \text{edad} \le 64)}$$
  $$\text{max\_educ\_hogar} = \max_{j} (\text{nivel\_educ}_j), \quad \text{tasa\_ocupacion} = \frac{\sum \mathbb{I}(\text{ocupado}_j)}{\sum \mathbb{I}(\text{edad}_j \ge 14)}$$

### 3. Agrupación Semántica Guiada por Dominio (*Domain-based Binning*)
Para evitar la maldición de la dimensionalidad y el sobreajuste que produciría un One-Hot Encoding sobre 9 categorías con colas inferiores al 1%, se reagruparon las categorías por afinidad socioeconómica:
* `piso_calidad`: `noble_acabado` (loseta, parquet, vinílico: 7.1% pobreza) vs `cemento_basico` (24.3% pobreza) vs `precario_tierra` (tierra, tablas: 37.0% pobreza).
* `combustible_tipo`: `gas_glp` (58.6% hogares) vs `gas_natural_electricidad` (33.1%) vs `biomasa_precaria` (leña, bosta, carbón: 36.5% pobreza).
* `agua_acceso`: `red_publica` (87.4%) vs `fuente_vulnerable` (camión cisterna, pilón, pozo: 26.8% pobreza).

### 4. Política Estricta de Fuga de Datos (*Zero Data Leakage*)
Se eliminaron por diseño del espacio $\mathcal{X}$ las variables de gastos monetarios (`GASHOG2D`, `GASTOMON`), ingresos (`INGHOG2D`) y las líneas de pobreza (`LINEA`, `LINPE`) del Módulo 34. Dichas columnas solo intervienen para generar la etiqueta de supervisión $y_i$ y se aíslan completamente del vector de entrada.

---

## 5. Modelos de Clasificación a Comparar (Taxonomía del Curso 1INF24)

1. **Baseline Paramétrico:** **Regresión Logística con Regularización ElasticNet** (función sigmoide, combinación L1/L2 para selección de variables dispersas).
2. **Modelo No Paramétrico Ortogonal:** **Árbol de Decisión CART** (criterio de división por Ganancia de Información / Entropía e Índice de Impureza de Gini, con poda por costo-complejidad $\alpha$).
3. **Ensamble por Bagging:** **Random Forest Classifier** (agregación de árboles paralelos con selección aleatoria de atributos y estimación out-of-bag).
4. **Ensamble por Boosting Secuencial:** **LightGBM / XGBoost Classifier** (optimización por descenso de gradiente sobre árboles de decisión con leaf-wise split y regularización L1/L2 en hojas).
