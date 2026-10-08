# Sección 6: Sugerencias de Trabajos Futuros

## 1. Extensiones y Mejoras Metodológicas

1. **Incorporación de Metadatos Espaciales y Satelitales:**
   Integrar datos geoespaciales georreferenciados (imágenes de luminosidad nocturna *Nighttime Lights - NTL*, índice de vegetación NDVI y distancia euclidiana a vías principales y centros de salud mediante OpenStreetMap) para enriquecer el vector $\mathbf{x}_i$ con el entorno del conglomerado urbano.

2. **Modelos de Redes Neuronales Tabulares:**
   Comparar los modelos basados en árboles (GBDT) frente a arquitecturas modernas de *Deep Learning* para datos tabulares, tales como **TabNet** (con mecanismos de atención secuencial) y Multilayer Perceptrons (MLP) con *Entity Embeddings* para variables categóricas de alta cardinalidad.

3. **Predicción Multiclase de Vulnerabilidad:**
   Extender el clasificador binario hacia una escala de 3 estratos: Pobreza Extrema, Pobreza No Extrema y Hogares Vulnerables no pobres, apoyando políticas preventivas contra la recaída económica.

4. **Despliegue Operativo y Auditoría en Tiempo Real:**
   Empaquetar el pipeline en un contenedor Docker con una API REST (FastAPI) y un panel interactivo (Streamlit) que permita a los trabajadores sociales ingresar los datos de una ficha de campo y obtener la clasificación, la probabilidad calibrada y la cascada de explicabilidad TreeSHAP en tiempo real.
