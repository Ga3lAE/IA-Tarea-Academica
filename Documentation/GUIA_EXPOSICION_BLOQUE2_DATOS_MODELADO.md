# Datos y modelado (Vale) — 1:45 min

## Contenido para la(s) diapositiva(s)

**Título:** Datos y modelado

- **Fuente:** ENAHO (INEI), Lima Metropolitana y Callao (DOMINIO = 8)
- **Entrenamiento:** ENAHO 2024 → 4,090 hogares
- **Prueba (fuera de tiempo):** ENAHO 2025 → 3,199 hogares (se sacan 930 hogares panel que ya estaban en 2024)
- **Unidad de análisis:** el hogar (una fila por hogar)
- **Target:** y = 1 si el hogar es pobre (extremo + no extremo), 0 si no es pobre. Sale de la Sumaria (Módulo 34) del INEI
- **Desbalance:** 774 pobres de 4,090 (18.92 %), ~1 pobre por cada 4 no pobres
- **Variables (sin ingreso ni gasto), 4 bloques:** vivienda, composición del hogar, educación, empleo
- **Operador Φ (personas → hogar):**
  - Jefe del hogar: edad, sexo, nivel educativo, horas de trabajo, pensión
  - Resumen de todos los miembros: tasa de dependencia, hacinamiento, máximo nivel educativo, fracción de ocupados
- **Datos faltantes (plan):** mediana calculada solo con entrenamiento; no se eliminan valores extremos
- **Estado actual:** datos descargados y limpieza inicial del Módulo 01 (vivienda); lo demás es lo que sigue

## Lo que dirá (guion oral)

Ahora les cuento con qué datos trabajamos. Usamos la ENAHO del INEI, solo de Lima Metropolitana y Callao. Vamos a entrenar con la ENAHO 2024, que tiene 4,090 hogares, y a probar con la 2025, que queda en 3,199 hogares después de sacar a 930 que ya estaban en 2024.

Cada fila es un hogar, y lo que queremos predecir es si es pobre o no. Esa etiqueta sale de la Sumaria del INEI, donde juntamos pobre extremo y no extremo como "pobre". En 2024 son 774 hogares pobres, un 18.9 %, o sea más o menos 1 pobre por cada 4 no pobres. Por eso las clases están desbalanceadas, y lo vamos a tener en cuenta al entrenar.

Algo importante: no vamos a usar ingreso ni gasto como variable. Solo cosas fáciles de observar, en 4 bloques: vivienda, composición del hogar, educación y empleo.

El reto es que la ENAHO viene por personas y nosotros necesitamos una fila por hogar. Para eso diseñamos un operador Φ con dos partes. Una toma los datos del jefe del hogar, como su edad, sexo, educación y si tiene pensión. La otra resume a todos los miembros, por ejemplo la tasa de dependencia, el hacinamiento, el máximo nivel educativo del hogar y la fracción de personas que trabajan.

Para los datos faltantes, el plan es rellenar con la mediana calculada solo con los datos de entrenamiento, y no eliminar valores extremos para no dejar fuera a los hogares más vulnerables. Hasta ahora descargamos los datos y empezamos la limpieza del módulo de vivienda. El resto del procesamiento y los modelos son lo que sigue.

Con esto tenemos la tabla de hogares lista para modelar, y Gael les cuenta cómo la vamos a usar.
