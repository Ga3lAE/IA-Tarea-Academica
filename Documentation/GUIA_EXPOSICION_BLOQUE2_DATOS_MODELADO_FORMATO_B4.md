# Guía de Exposición: Bloque 2 — Datos y Modelado
**Curso:** Inteligencia Artificial (1INF24) — Tarea Académica  
**Proyecto:** Clasificación de la Pobreza Monetaria en Lima Metropolitana mediante Aprendizaje Supervisado sobre Microdatos de la ENAHO  
**Autores:** Gael Sebastian Arias Escalante, Melanie Nadine Mallqui Huaraz, Valeshka del Pilar Lavado Guerra, Edilvan Franco Salcedo Enciso  
**Expositora del bloque:** Valeshka del Pilar Lavado Guerra  

---

## 📌 1. Objetivos y Dinámica de la Exposición

El bloque 2 dura **1 minuto 45 segundos**. Presenta los datos y cómo los convertimos en una tabla lista para modelar. Va después de la presentación del problema y antes de que Gael explique cómo se usará la tabla.

Debe dejar claros 4 puntos:
1. **Con qué datos trabajamos:** ENAHO (INEI) de Lima Metropolitana y Callao; entrenamiento con 2024 y prueba fuera de tiempo con 2025.
2. **Qué predecimos:** si el hogar es pobre (1) o no pobre (0), con clases desbalanceadas (18.9 % pobres).
3. **Con qué variables y cómo:** sin ingreso ni gasto; 4 bloques de variables y un operador Φ que pasa de personas a hogar.
4. **Cómo tratamos los datos faltantes** y en qué estado está el trabajo.

> ⚠️ **Regla de oro:** el procesamiento completo y los modelos **no están terminados**. Los datos faltantes se presentan como **plan** (mediana solo con entrenamiento), nunca como algo ya ejecutado. Lo que sí está hecho es la descarga de datos y la limpieza inicial del Módulo 01 (vivienda) (ver §4).

---

## 🎞️ 2. Estructura Lámina por Lámina (Slide-by-Slide)

```mermaid
flowchart LR
    L1["Lámina 1\nFuente, hogares\ny target"] --> L2["Lámina 2\nVariables y\noperador Φ"]
    L2 --> L3["Lámina 3\nDatos faltantes\ny estado actual"]
```

---

### 🔹 LÁMINA 1: Fuente, Hogares y Target
* **Tiempo sugerido:** 40 segundos
* **Título de la diapositiva:** Datos y modelado
* **Elementos visuales a incluir:**
  * **Fuente:** ENAHO (INEI), Lima Metropolitana y Callao (`DOMINIO = 8`).
  * Esquema de dos cajas:
    * **Entrenamiento:** ENAHO 2024 → **4,090 hogares**.
    * **Prueba (fuera de tiempo):** ENAHO 2025 → **3,199 hogares** (se sacan **930** hogares panel que ya estaban en 2024).
  * **Unidad de análisis:** el hogar (una fila por hogar).
  * **Target:** y = 1 si el hogar es pobre (extremo + no extremo), y = 0 si no es pobre. Sale de la Sumaria (Módulo 34) del INEI.
  * Barra de proporciones: **774 pobres de 4,090 (18.92 %)**, ≈ 1 pobre por cada 4 no pobres.

#### 🗣️ Guión Verbal (Talking Points):
> *"Ahora les cuento con qué datos trabajamos. Usamos la ENAHO del INEI, solo de Lima Metropolitana y Callao. Vamos a entrenar con la ENAHO 2024, que tiene 4,090 hogares, y a probar con la 2025, que queda en 3,199 hogares después de sacar a 930 que ya estaban en 2024.*
>
> *Cada fila es un hogar, y lo que queremos predecir es si es pobre o no. Esa etiqueta sale de la Sumaria del INEI, donde juntamos pobre extremo y no extremo como 'pobre'. En 2024 son 774 hogares pobres, un 18.9 %, o sea más o menos 1 pobre por cada 4 no pobres. Por eso las clases están desbalanceadas, y lo vamos a tener en cuenta al entrenar."*

---

### 🔹 LÁMINA 2: Variables y Operador Φ
* **Tiempo sugerido:** 40 segundos
* **Título de la diapositiva:** De personas a hogares: el operador Φ
* **Elementos visuales a incluir:**
  * Aviso destacado: **"Sin ingreso ni gasto como variables"** (solo cosas fáciles de observar).
  * **4 bloques de variables:** vivienda · composición del hogar · educación · empleo.
  * Diagrama del operador **Φ (personas → hogar)** con dos ramas:

| Rama | Qué toma | Variables |
| :--- | :--- | :--- |
| **Jefe del hogar** | Datos de una sola persona | Edad, sexo, nivel educativo, horas de trabajo, pensión |
| **Resumen de todos los miembros** | Agrega a todas las personas del hogar | Tasa de dependencia, hacinamiento, máximo nivel educativo, fracción de ocupados |

#### 🗣️ Guión Verbal (Talking Points):
> *"Algo importante: no vamos a usar ingreso ni gasto como variable. Solo cosas fáciles de observar, en 4 bloques: vivienda, composición del hogar, educación y empleo.*
>
> *El reto es que la ENAHO viene por personas y nosotros necesitamos una fila por hogar. Para eso diseñamos un operador Φ con dos partes. Una toma los datos del jefe del hogar, como su edad, sexo, educación y si tiene pensión. La otra resume a todos los miembros, por ejemplo la tasa de dependencia, el hacinamiento, el máximo nivel educativo del hogar y la fracción de personas que trabajan."*

---

### 🔹 LÁMINA 3: Datos Faltantes y Estado Actual
* **Tiempo sugerido:** 25 segundos
* **Título de la diapositiva:** Datos faltantes y dónde estamos
* **Elementos visuales a incluir:**
  * **Plan para datos faltantes:** imputar con la **mediana calculada solo con entrenamiento**; **no se eliminan valores extremos**.
  * Línea de avance:
    * ✅ Datos descargados
    * ✅ Limpieza inicial del Módulo 01 (vivienda)
    * ⏳ Resto del procesamiento y modelos (lo que sigue)

#### 🗣️ Guión Verbal (Talking Points):
> *"Para los datos faltantes, el plan es rellenar con la mediana calculada solo con los datos de entrenamiento, y no eliminar valores extremos para no dejar fuera a los hogares más vulnerables. Hasta ahora descargamos los datos y empezamos la limpieza del módulo de vivienda. El resto del procesamiento y los modelos son lo que sigue.*
>
> *Con esto tenemos la tabla de hogares lista para modelar, y Gael les cuenta cómo la vamos a usar."*

---

## 📊 3. Cifras Verificadas (para copiar al PPT)

| Cifra | Valor | Fuente |
| :--- | :--- | :--- |
| Hogares 2024 (entrenamiento) | 4,090 | Guía del bloque 2 |
| Hogares pobres 2024 | 774 (18.92 %) | Guía del bloque 2 |
| Proporción de clases | ~1 pobre por cada 4 no pobres | Guía del bloque 2 |
| Hogares 2025 para la prueba (sin panel) | 3,199 | Guía del bloque 2 |
| Hogares panel excluidos de la prueba | 930 | Guía del bloque 2 |
| Dominio geográfico | Lima Metropolitana y Callao (`DOMINIO = 8`) | Guía del bloque 2 |
| Origen del target | Sumaria, Módulo 34 (INEI) | Guía del bloque 2 |
| % de pobres en la prueba 2025 | 17.4 % | Guía del bloque 4 (Informe, Sección 3) |

---

## 🚫 4. Lo que Todavía NO es un Resultado

| Pendiente | Qué decir si preguntan |
| :--- | :--- |
| Imputación de faltantes con la mediana | *"Es el plan: la mediana se calcula solo con entrenamiento para no filtrar información de la prueba."* |
| Limpieza de los módulos de empleo, educación y composición | *"Empezamos por el Módulo 01 (vivienda); el resto sigue."* |
| Construcción final de la tabla con el operador Φ | *"El diseño de Φ está definido; la construcción completa de la tabla es lo que sigue."* |
| Entrenamiento y evaluación de los modelos | *"Eso lo presenta Gael en su bloque y Edilvan en evaluación."* |

---

## 🛡️ 5. Preguntas Frecuentes del Jurado sobre Datos y Modelado

### P1: *"¿Por qué no usan ingreso ni gasto como variable?"*
* **Respuesta:** *"Porque queremos identificar hogares pobres con variables fáciles de observar, sin tener que medir el gasto, que es lo costoso. El target sí sale del gasto, pero el modelo no lo usa para predecir."*

### P2: *"¿Por qué juntan pobre extremo y no extremo?"*
* **Respuesta:** *"Porque definimos el problema como clasificación binaria: pobre (extremo o no extremo) frente a no pobre. La etiqueta sale de la Sumaria del INEI."*

### P3: *"¿Cómo manejan el desbalance de clases?"*
* **Respuesta:** *"Solo 18.9 % de los hogares son pobres, así que lo tenemos en cuenta al entrenar con pesos para la clase pobre, y evaluamos con PR-AUC y error de exclusión, no con exactitud."*

### P4: *"¿Por qué sacan 930 hogares de la prueba 2025?"*
* **Respuesta:** *"Son hogares panel que ya estaban en 2024. Si los dejáramos, el modelo ya habría visto esos hogares y la prueba sería demasiado optimista."*

### P5: *"¿Por qué la mediana solo con entrenamiento?"*
* **Respuesta:** *"Para no filtrar información de la prueba al entrenamiento. La imputación se ajusta solo con datos de entrenamiento."*

### P6: *"¿Por qué no eliminan valores extremos?"*
* **Respuesta:** *"Porque los valores extremos suelen ser justamente de los hogares más vulnerables, y eliminarlos los dejaría fuera del modelo."*

### P7: *"¿Qué hace exactamente el operador Φ?"*
* **Respuesta:** *"La ENAHO viene por personas y necesitamos una fila por hogar. Φ toma los datos del jefe del hogar y resume a todos los miembros, por ejemplo con la tasa de dependencia, el hacinamiento, el máximo nivel educativo y la fracción de ocupados."*

### P8: *"¿Por qué solo Lima Metropolitana y Callao?"*
* **Respuesta:** *"Ese es el alcance del proyecto: usamos solo el dominio 8 de la ENAHO. Los resultados no se pueden extrapolar a otras zonas del país."*

---

## ⏱️ 6. Resumen de Tiempos

| Lámina | Contenido Principal | Tiempo |
| :---: | :--- | :---: |
| **L1** | Fuente, hogares y target | 0:40 |
| **L2** | Variables y operador Φ | 0:40 |
| **L3** | Datos faltantes y estado actual | 0:25 |
| **Total** | **Bloque 2: Datos y modelado** | **1:45** |
