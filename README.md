# Predicción de Pobreza Urbana en Lima y Callao mediante Machine Learning

> **Curso:** Inteligencia Artificial (2026-2) — Tarea Académica  
> **Institución:** Pontificia Universidad Católica del Perú (PUCP)  
> **Fuente de Datos:** Encuesta Nacional de Hogares (ENAHO) — Instituto Nacional de Estadística e Informática (INEI)  

---

## 1. Descripción del Proyecto

El objetivo principal de este proyecto es diseñar, entrenar y evaluar modelos de **Machine Learning para la clasificación binaria de hogares en situación de pobreza en Lima Metropolitana y la Provincia Constitucional del Callao**.

La variable objetivo se formula a nivel de **Hogar**:
$$\text{Target } (y) = \begin{cases} 
1 & \text{si el hogar está en Pobreza Extrema o Pobreza No Extrema (Pobreza Total)} \\
0 & \text{si el hogar es No Pobre}
\end{cases}$$

### Enfoque Metodológico: Proxy Means Testing (PMT)
En la estadística oficial del INEI, la pobreza monetaria se calcula determinísticamente comparando el gasto mensual per cápita contra el valor de la canasta básica (`LINEA`). 

Para construir un modelo de predicción e inferencia real (útil para focalización de programas sociales y políticas públicas sin necesidad de auditar los gastos diarios del hogar), **se excluyen estrictamente las variables de gasto e ingreso monetario de Sumaria**. Esto previene el **Data Leakage** (fuga de información) y obliga a los modelos a aprender a partir de variables estructurales: características constructivas de la vivienda, hacinamiento, nivel educativo acumulado, formalidad laboral, tenencia de activos y composición demográfica.

---

## 2. Microdatos y Fuentes de Información

Los datos provienen de la **ENAHO con Metodología Actualizada** del INEI para los periodos post-pandemia (**2024 y 2025**, ampliable a **2023**):

| Módulo | Archivo Raw | Nombre Temático | Nivel de Granularidad | Registros (Lima y Callao) |
| :--- | :--- | :--- | :--- | :---: |
| **Módulo 34** | `Sumaria-*.csv` | Resumen de Hogares y Target Oficial | Hogar | ~5,580 / año |
| **Módulo 01** | `Enaho01-*-100.csv`| Características de la Vivienda y Servicios Básicos | Hogar | ~5,580 / año |
| **Módulo 02** | `Enaho01-*-200.csv`| Características Demográficas de los Miembros | Persona | ~18,000 / año |
| **Módulo 03** | `Enaho01A-*-300.csv`| Educación y Capital Humano ($\ge 3$ años) | Persona | ~17,000 / año |
| **Módulo 05** | `Enaho01a-*-500.csv`| Empleo, Ocupación e Informalidad ($\ge 14$ años) | Persona | ~14,000 / año |

*Fuente complementaria planificada:* [Gasto presupuestal de los organismos públicos descentralizados, regionales y municipales (Datos Abiertos Perú)](https://www.datosabiertos.gob.pe/).

---

## 3. Desafíos Técnicos de los Datos Urbanos y Soluciones

### A. Desbalance de Clases (~17.4% Pobreza vs ~82.6% No Pobre)
En Lima y Callao la pobreza representa aproximadamente el **17.4% de los hogares** (ratio ~1:4.7). Un modelo trivial (*dummy*) que prediga siempre "No Pobre" obtendría ~82.6% de Accuracy con Recall = 0%.
- **Estrategia:** Optimización orientada a **F1-Score (clase minoritaria / macro)**, **PR-AUC (Precision-Recall AUC)**, matrices de costos, pesos de clase (`class_weight='balanced'`) y calibración de umbrales (*Threshold Tuning*).

### B. Filtro de Baja Varianza en Entorno Metropolitano (*Low Variance Filter*)
A diferencia del ámbito rural, en Lima y Callao la luz eléctrica (`P1121`, 98.6%), la tenencia de celular (`P1142`, 97.2%) y las Necesidades Básicas Insatisfechas oficiales (`NBI1` a `NBI5`, >96% sin carencias) son cuasi-constantes. El pipeline descarta estas variables por no poseer varianza discriminante en entornos urbanos consolidados.

### C. Nulos Estructurales y Saltos de Cuestionario (*Skip Patterns*)
- **120 nulos (2.15%) en pisos, paredes y cuartos:** Ocurrían en hogares secundarios (`HOGAR 22, 33...`) que comparten vivienda con un hogar principal (`HOGAR 11`). El procesador propaga las características físicas del inmueble dentro de la misma vivienda (`ffill()` por `conglomerado` y `vivienda`), reduciendo los nulos a **0.00%**.
- **Nulos en Título de Propiedad (32%) y SUNARP (57%):** No son datos perdidos al azar; corresponden a inquilinos y hogares con viviendas cedidas. Se consolidan en la variable categórica `seguridad_tenencia` (`propia_registrada_sunarp`, `propia_titulada_no_sunarp`, `propia_sin_titulo`, `alquilada`, `cedida_posesion_informal`).

---

## 4. Arquitectura de Software (Principios SOLID)

El proyecto implementa el patrón **Template Method** respetando el **Principio Abierto/Cerrado (Open/Closed Principle - OCP)**:

```
src/
├── config/
│   ├── base.py                   # Constantes de alcance geográfico y llaves primarias
│   └── modulo01.py               # Mapeos, esquemas y reglas de validación de Vivienda
├── core/
│   ├── base_processor.py         # Clase abstracta BaseModuleProcessor (Template Method)
│   └── validators.py             # Aserciones estrictas (Schema, Rows, PK Uniqueness, Nulls)
├── processors/
│   └── modulo01.py               # Implementación concreta para Módulo 01
└── pipeline.py                   # Orquestador multi-año y multi-módulo
```

### Extensibilidad (OCP)
- **Cerrado a modificación:** `BaseModuleProcessor` blinda el ciclo de vida de los datos, la codificación, la autodetección de delimitador (`,` vs `;`), los filtros geográficos y la persistencia.
- **Abierto a extensión:** Cada nuevo módulo (Módulo 02, 03, 05, 34) se incorpora creando una subclase que hereda de `BaseModuleProcessor` e implementa sus hooks específicos sin alterar el resto del sistema.

---

## 5. Estructura del Repositorio

```
Tarea Académica/
├── README.md                     # Documento principal del proyecto
├── IMPLEMENTATION.md             # Bitácora detallada de implementación paso a paso
├── requirements.txt              # Dependencias del proyecto
├── .gitignore                    # Reglas de exclusión para Git y compilación LaTeX
├── src/                          # Código modular y procesadores (OOP / OCP)
│   ├── config/                   # Diccionarios de mapeo y esquemas por módulo
│   ├── core/                     # BaseModuleProcessor y suite de validadores
│   ├── processors/               # Implementaciones concretas por módulo ENAHO
│   └── pipeline.py               # Orquestador multi-año y multi-módulo
├── notebooks/                    # Flujo de trabajo interactivo por etapas
│   ├── 01_modulos/               # Extracción y limpieza modular (01_vivienda_modulo01.ipynb)
│   ├── 02_integracion/           # Fusión relacional jerárquica a nivel hogar (01 + 02 + 03 + 05 + 34)
│   ├── 03_eda/                   # Análisis exploratorio multivariado de pobreza
│   ├── 04_modelado/              # Modelos de clasificación supervisada out-of-time
│   └── README.md                 # Guía del flujo de notebooks
├── Documentation/                # Informe académico (PUCP 1INF24)
│   ├── latex/                    # Master LaTeX (main.tex, main.pdf)
│   └── sections/                 # Capítulos modulares (.md y .tex sincronizados)
└── Data/
    ├── 2024/
    │   └── enaho/                # Microdatos ENAHO 2024 (966-Modulo01 a 966-Modulo34)
    ├── 2025/
    │   └── enaho/                # Microdatos ENAHO 2025 (1031-Modulo01 a 1031-Modulo34)
    ├── 2026/
    │   └── enaho/                # Microdatos preliminares ENAHO 2026 (alerta temprana)
    ├── processed/                # Datasets limpios estandarizados (*_cleaned.csv)
    └── Fuentes.md                # Enlaces oficiales y diccionario metodológico INEI
```

---

## 6. Instalación y Uso Rápido

### Requisitos Previos
Python 3.10 o superior con `pandas`, `numpy`, `matplotlib`, `seaborn` y `scikit-learn`.

```bash
# Clonar el repositorio
git clone <url-del-repositorio>
cd "Tarea Académica"

# Instalar dependencias
pip install -r requirements.txt
```

### Procesar Datos mediante el Orquestador Multi-Año
```python
from src.pipeline import ENAHOPipeline

# Instanciar el pipeline
pipe = ENAHOPipeline(data_root="Data")

# Procesar Módulo 01 para 2024 y 2025 de forma conjunta (11,160 hogares)
df_vivienda_consolidada = pipe.run_module(
    module_code="modulo01",
    years=[2024, 2025],
    export_cleaned=True,
    concatenate_years=True
)
print("Dimensiones del dataset consolidado:", df_vivienda_consolidada.shape)
```
