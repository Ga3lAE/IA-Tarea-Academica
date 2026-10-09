# Sección 5: Conclusión

> **⚠️ Nota (Plan 2, 2026-10-08):** este documento conserva textos anteriores al levantamiento de observaciones (alcance de 5,571 hogares, matriz `INGTPUHD`, hipótesis previas, atribuciones de papers sin verificar). La versión vigente es la de los archivos `.tex` y la de [`Observaciones a levantar/Plan 2`](../../Observaciones%20a%20levantar/Plan%202/README.md).

## 1. Conclusiones Principales del Trabajo

1. **Inviabilidad de Modelos Lineales y Reglas Simples:**
   La evidencia empírica extraída de la ENAHO demuestra que la pobreza urbana en Lima y Callao no puede capturarse mediante reglas heurísticas basadas en materiales físicos de la vivienda (el 59.4% de los pobres habitan en viviendas de albañilería noble de ladrillo). La pobreza urbana es un fenómeno multidimensional que demanda capturar interacciones no lineales entre infraestructura habitacional, dependencia demográfica e informalidad en el empleo.

2. **Superioridad del Paradigma de Clasificación Supervisada:**
   Frente a la regresión continua del gasto —que distorsiona su aprendizaje intentando ajustar la enorme varianza de los hogares de altos ingresos—, la clasificación binaria supervisada concentra eficientemente su frontera de optimización en los hogares vulnerables, permitiendo la integración de pérdidas sensibles al costo (*Cost-Sensitive Loss*) para penalizar el error de exclusión social.

3. **Eficacia del Preprocesamiento Guiado por Dominio:**
   La agrupación semántica de categorías de baja frecuencia (*Domain-based Binning*) previene la dispersión (*sparsity*) del espacio de atributos sin borrar la señal discriminante de las condiciones habitacionales precarias.

4. **Validación de la Hipótesis:**
   El pipeline formulado establece una base metodológica sólida que proyecta superar en al menos 15 puntos porcentuales el $F_1$-score de la regresión logística tradicional, ofreciendo una herramienta viable y auditable para la modernización de los sistemas de focalización de transferencias sociales en el Perú.
