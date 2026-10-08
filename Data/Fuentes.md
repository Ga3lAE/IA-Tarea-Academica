# Fuentes Oficiales de Microdatos (Data Sources)

Este proyecto utiliza microdatos oficiales a nivel de hogar e individuo de la **Encuesta Nacional de Hogares (ENAHO)** elaborada por el **Instituto Nacional de Estadística e Informática (INEI)** del Perú.

---

## 1. Plataforma de Microdatos INEI
- **Portal Oficial:** [Microdatos INEI](https://proyectos.inei.gob.pe/microdatos/)
- **Consulta:**
  1. **Encuesta:** `ENAHO Metodología ACTUALIZADA`
  2. **Tipo de Estudio:** `Condiciones de Vida y Pobreza - ENAHO`
  3. **Años de Muestra:**
     - `2024` (Código de consulta 966)
     - `2025` (Código de consulta 1031)
     - `2026` (En ejecución preliminar para prueba out-of-time / despliegue)
  4. **Periodicidad:** `Anual - (Ene-Dic)`

---

## 2. Módulos ENAHO Utilizados y Estructura Relacional

El sistema integra horizontal y jerárquicamente cinco módulos analíticos mediante la llave primaria compuesta de hogar:
$$\text{PK}_{\text{hogar}} = \{\text{CONGLOME}, \text{VIVIENDA}, \text{HOGAR}\}$$

| Módulo | Archivo Raw (CSV) | Nivel de Observación | Descripción y Contenido |
| :--- | :--- | :--- | :--- |
| **01 (Vivienda)** | `Enaho01-YYYY-100.csv` | Hogar | Características físicas del hábitat, materiales de pared/piso/techo, servicios básicos (agua, desagüe, luz), hacinamiento y seguridad jurídica de tenencia. |
| **02 (Demografía)** | `Enaho01-YYYY-200.csv` | Miembro / Individuo | Estructura demográfica, parentesco, edad y sexo de miembros, carga de dependencia (niños/ancianos) y shocks de salud crónica / discapacidad. |
| **03 (Educación)** | `Enaho01A-YYYY-300.csv` | Miembro / Individuo | Nivel educativo alcanzado, años de estudio del jefe y miembros, asistencia escolar y analfabetismo funcional. |
| **05 (Empleo)** | `Enaho01a-YYYY-500.csv` | Miembro / Individuo | Condición de ocupación, subempleo, informalidad laboral (sin RUC / sin contrato), horas semanales trabajadas y afiliación a seguridad social (pensiones/salud). |
| **34 (Sumaria)** | `Sumaria-YYYY.csv` | Hogar | **Variable Objetivo ($Y$):** Pobreza monetaria oficial (`POBREZA`), línea de pobreza (`LINEA`), gasto per cápita y transferencias de programas sociales. |

---

## 3. Cobertura Geográfica
- **Ámbito:** Lima Metropolitana y la Provincia Constitucional del Callao.
- **Filtro UBIGEO:** Prefijos departamentales `'07'` (Callao) y `'15'` (Lima).
