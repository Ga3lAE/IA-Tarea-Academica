# Sección 7: Implicancias Éticas

## 1. Análisis de Riesgos Éticos en la Automatización de Políticas Sociales

El despliegue de sistemas de Inteligencia Artificial para la asignación de recursos públicos y subsidios sociales condiciona directamente el bienestar material de personas en situación de extrema vulnerabilidad. Si el sistema propuesto se escalara a nivel de producción en entidades estatales (como el MIDIS o el SISFOH), generaría implicancias éticas críticas que deben mitigarse por diseño:

### 1. Sesgo Algorítmico y Discriminación Geográfica
* **Riesgo:** Si el modelo correlaciona excesivamente con el código geográfico (`UBIGEO` o conglomerado), podría generar "zonas rojas" donde hogares en necesidad real sean excluidos automáticamente simplemente por residir en un distrito clasificado con menor tasa agregada de pobreza.
* **Mitigación:** Asegurar que los pesos de las características se basen en atributos intrínsecos de necesidad humana (hacinamiento, dependencia demográfica, precariedad física) y no en sesgos geográficos agregados; auditar la paridad estadística (*Demographic Parity*) y la igualdad de oportunidades (*Equal Opportunity*) entre distritos.

### 2. Severidad Asimétrica del Error (Falso Negativo vs Falso Positivo)
* **Riesgo:** En clasificación binaria estándar, el algoritmo trata ambos errores con el mismo costo. Sin embargo, en el contexto social, un **Falso Negativo** priva a una familia indigente de alimentación o salud básica, mientras que un **Falso Positivo** solo representa un costo fiscal marginal.
* **Mitigación:** Implementación explícita de aprendizaje sensible al costo (*Cost-Sensitive Loss*) y calibración conservadora del umbral de decisión ($\tau$), priorizando la maximización del Recall (sensibilidad) de la clase vulnerable para minimizar el error de exclusión.

### 3. Explicabilidad Algorítmica y Derecho a la Justificación Administrativa
* **Riesgo:** Los modelos de ensamble de árboles complejos (GBDT) funcionan como "cajas negras" opacas, lo que imposibilitaría a un ciudadano comprender o apelar formalmente por qué se le denegó un subsidio estatal.
* **Mitigación:** Integración de explicabilidad local basada en teoría de juegos cooperativos mediante **TreeSHAP** (*SHapley Additive exPlanations*). Cada predicción debe acompañarse de una ficha desglosada que señale exactamente qué factores contribuyeron a la decisión (ej. +0.25 por alta dependencia demográfica, -0.15 por tener piso de loseta), garantizando el derecho a la transparencia y auditoría pública.

### 4. Privacidad y Gobernanza de Datos Sensibles
* **Riesgo:** La recolección masiva de microdatos habitacionales expone información sobre la vida privada de los ciudadanos a posibles filtraciones o ataques cibernéticos.
* **Mitigación:** Cumplimiento riguroso de la Ley N° 29733 (Ley de Protección de Datos Personales del Perú); anonimización irreversible de identificadores personales en reposo y en tránsito; uso exclusivo de claves administrativas sin nombres ni DNI en el pipeline de inferencia.
