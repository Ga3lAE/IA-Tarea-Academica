# Flujo de Trabajo en Notebooks (Jupyter Workflows)

> **Curso:** Inteligencia Artificial (1INF24) — Pontificia Universidad Católica del Perú (PUCP)  
> **Proyecto:** Clasificación de Pobreza Urbana en Lima Metropolitana mediante Machine Learning sobre microdatos ENAHO.

---

## 📌 Estado Actual: Sprint 1 (Ingesta y Auditoría de Microdatos)

Siguiendo el principio de desarrollo iterativo y sin sobre-ingeniería, la carpeta `notebooks/` cuenta con un único notebook enfocado en la **ingesta y verificación de los datos**:

```text
notebooks/
├── pipeline_completo.ipynb   # Ingesta, lectura y auditoría de integridad de los 5 módulos ENAHO (2024 y 2025)
└── README.md                 # Guía de ejecución del notebook
```

---

## 🚀 Contenido del Notebook (`pipeline_completo.ipynb`)

El notebook está delimitado exclusivamente a la **Fase de Ingesta y Lectura**:

1. **Configuración del Entorno:**
   - Vinculación a la raíz del repositorio y carga de las funciones de `src/io_enaho.py`.
2. **Módulo 34 (Sumaria):**
   - Lectura del marco maestro de hogares en Lima Metropolitana (`DOMINIO == 8`), target binario `y`, factor de expansión y gasto per cápita para la línea base.
3. **Módulo 01 (Vivienda y Servicios):**
   - Lectura de características físicas con **conservación estricta de valores nulos en hogares secundarios** (levantamiento de la observación del jurado, sin `ffill/bfill`).
4. **Módulo 02 (Demografía):**
   - Lectura de miembros residentes habituales, identificación de la jefatura de hogar, edad y sexo.
5. **Módulo 03 (Educación):**
   - Lectura de miembros de 3 años o más y niveles educativos alcanzados.
6. **Módulo 05 (Empleo e Informalidad):**
   - Lectura de la población en edad de trabajar (PET $\ge 14$ años), categorías ocupacionales y afiliación a pensión, con exclusión estricta de ingresos monetarios (cero *data leakage*).
7. **Matriz Consolidada de Auditoría:**
   - Comparación tabular 2024 vs. 2025 de filas, columnas, hogares únicos cubiertos y verificación de unicidad de llaves primarias (`PK Única: True`).
