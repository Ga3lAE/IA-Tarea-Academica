# Predicción y Clasificación de Pobreza Urbana en Lima y Callao mediante Machine Learning

> **Curso:** Inteligencia Artificial (1INF24 - 2026-2) — Tarea Académica  
> **Institución:** Pontificia Universidad Católica del Perú (PUCP)  
> **Equipo 3:** Gael Sebastian Arias Escalante, Melanie Nadine Mallqui Huaraz, Valeshka del Pilar Lavado Guerra, Edilvan Franco Salcedo Enciso.  
> **Fuente de Datos:** Encuesta Nacional de Hogares (ENAHO) — Instituto Nacional de Estadística e Informática (INEI).  

---

## 1. Descripción del Proyecto

El objetivo de este proyecto es diseñar, entrenar y evaluar comparativamente modelos de **Machine Learning para la clasificación binaria de hogares en situación de pobreza monetaria en Lima Metropolitana y la Provincia Constitucional del Callao** (`DOMINIO == 8`), con foco en la minimización del error de exclusión de hogares vulnerables y la estabilidad temporal fuera de tiempo (*out-of-time*).

La variable objetivo se formaliza a nivel de **Hogar** a partir del Módulo 34 (Sumaria):
$$\text{Target } (y) = \begin{cases} 
1 & \text{si el hogar está en Pobreza Extrema o Pobreza No Extrema (Pobreza Total)} \\
0 & \text{si el hogar es No Pobre}
\end{cases}$$

### Enfoque Metodológico: Proxy Means Testing (PMT) y Cero Fuga
En la estadística oficial del INEI, la pobreza se define comparando el gasto mensual per cápita auditado contra el valor de la canasta básica (`LINEA`, S/ 559.20 en Lima Metropolitana). 

Para construir un clasificador útil para la focalización ágil de programas de protección social sin necesidad de auditar los gastos diarios familiares, **se excluyen de forma estricta todas las variables de ingreso y gasto monetario**. El clasificador induce patrones de vulnerabilidad exclusivamente a partir de características estructurales observables: materialidad de la vivienda, hacinamiento, composición y carga demográfica, nivel educativo acumulado y condiciones de formalidad laboral e inserción previsional.

---

## 2. Microdatos y Fuentes de Información

El proyecto integra microdatos de la **ENAHO con Metodología Actualizada** del INEI para los periodos post-pandemia (**2024 y 2025**):

| Módulo | Archivo Raw | Nombre Temático | Nivel de Granularidad | Registros (Lima Metropolitana, `DOMINIO 8`) |
| :--- | :--- | :--- | :---: | :---: |
| **Módulo 34** | `Sumaria-*.csv` | Resumen de Hogares y Target Oficial | Hogar | 4,090 (2024) / 4,129 (2025) |
| **Módulo 01** | `Enaho01-*-100.csv` | Características de la Vivienda y Servicios | Hogar | 4,090 (2024) / 4,129 (2025) |
| **Módulo 02** | `Enaho01-*-200.csv` | Composición Demográfica de Residentes | Individuo | ~13,600 miembros / año |
| **Módulo 03** | `Enaho01A-*-300.csv`| Educación y Capital Humano ($\ge 3$ años) | Individuo | Miembros $\ge 3$ años |
| **Módulo 05** | `Enaho01a-*-500.csv`| Empleo, Formalidad y Horas ($\ge 14$ años) | Individuo | Miembros $\ge 14$ años |

* **Conjunto de Entrenamiento:** ENAHO 2024 completa ($N = 4{,}090$ hogares, $18.92\%$ de pobreza monetaria).
* **Conjunto de Prueba Fuera de Tiempo (Out-of-Time):** ENAHO 2025 con **purga estricta de los 930 hogares panel** repetidos que fueron encuestados en 2024, consolidando un test independiente de **$N_{\text{test}} = 3{,}199$ hogares nuevos** ($17.41\%$ de pobreza monetaria).

> [!IMPORTANT]
> **Gestión de Microdatos con Git LFS:**  
> Los microdatos brutos en `Data/` están versionados con **Git LFS**. Para descargarlos antes de ejecutar:
> ```bash
> git lfs install
> git lfs pull
> ```

---

## 3. Desafíos Técnicos de los Datos Urbanos y Soluciones

### A. Desbalance de Clases (~18.9% Pobreza vs ~81.1% No Pobre)
En Lima Metropolitana la pobreza afecta al 18.92% de los hogares en 2024 (razón de desbalance $\gamma \approx 4.28$). Un modelo ingenuo que prediga siempre "No Pobre" obtendría ~81% de Accuracy pero un Recall de 0%.
- **Estrategia:** Optimización orientada a **PR-AUC**, matrices de costo asimétricas con peso de penalización $\alpha \in \{1, 2, \gamma\}$ sobre la pérdida logística y comparación de modelos a **cobertura presupuestal fija ($B = 20\%$)** mediante curvas de Error de Exclusión ($\mathrm{EE}$) y Error de Inclusión ($\mathrm{IE}$).

### B. Tratamiento Riguroso de Nulos en Hogares Secundarios (Levantamiento OBS-P01)
- En el Módulo 01, **72 hogares secundarios en 2024 y 96 en 2025** (`hogar >= '22'`) que cohabitan en un mismo lote o inmueble con el hogar principal carecen de registro en 5 atributos físicos de la vivienda (`tipo_vivienda`, `material_pared`, `material_piso`, `total_habitaciones`, `total_dormitorios`).
- En atención a la retroalimentación del jurado (**OBS-P01**), **se descarta cualquier propagación intra-vivienda (`ffill/bfill`)**. Las condiciones de habitabilidad de hogares secundarios pueden diferir sustancialmente de las del principal.
- **Solución implementada:** Las variables cualitativas de vivienda se imputan mediante la categoría explícita `"desconocido"`, mientras que los conteos de habitaciones y dormitorios se imputan mediante la **mediana del conglomerado censal (`conglomerado`)** calculada estrictamente en el pliegue de entrenamiento (con respaldo en la mediana global de train).

### C. Espacio de Características Canónico ($\mathbf{x}_i \in \mathbb{R}^{28}$)
Se descartan variables con nula varianza en Lima Metropolitana (ej. alumbrado eléctrico con >98% de cobertura y Necesidades Básicas Insatisfechas oficiales NBI1-NBI5 con >96% ceros) y se estructura un vector denso de **28 predictores**:
* **11 de Vivienda:** Tipo, paredes, pisos, tenencia, agua, saneamiento, combustible, internet, habitaciones y dormitorios.
* **7 de Demografía:** Tamaño del hogar, menores de 5, menores de 14, adultos mayores de 65, tasa de dependencia, edad y sexo del jefe.
* **2 de Educación:** Nivel educativo máximo del jefe y máximo acumulado en el hogar.
* **8 de Empleo y Ratios:** Ocupados totales, ocupados por miembro, hacinamiento (personas por cuarto), condición laboral, categoría ocupacional, horas trabajadas, formalidad (RUC) y cobertura previsional del jefe.

---

## 4. Arquitectura de Software Modular (`src/`)

El código sigue una arquitectura directa y modular (principio **KISS**), separando claramente las responsabilidades:

```text
src/
├── __init__.py           # Declaración del paquete
├── README.md             # Guía técnica de la biblioteca modular
├── io_enaho.py           # Ingesta, autodetección de delimitadores y estandarización INEI
├── dataset.py            # Operador Phi (persona -> hogar), Big DataFrame y purga de panel
├── preprocessing.py      # Espacio canónico R^28 y transformadores anti-fuga (Scikit-Learn)
├── models.py             # Definición y ajuste de los 5 clasificadores bajo GroupKFold(5)
└── evaluation.py         # Curvas EE-IE, Cluster Bootstrap (1,000 réplicas) y TreeSHAP
```

---

## 5. Estructura del Repositorio

```text
Tarea Académica/
├── README.md                     # Documento principal del proyecto (este archivo)
├── IMPLEMENTATION.md             # Bitácora detallada de sprints, auditorías y roadmap
├── requirements.txt              # Dependencias del proyecto
├── .gitignore                    # Reglas de exclusión para Git, temporales y LaTeX
│
├── src/                          # Biblioteca modular de Python (KISS)
│   ├── io_enaho.py               # Lectura de los 5 módulos ENAHO
│   ├── dataset.py                # Integración relacional y purga de panel
│   └── preprocessing.py          # Preprocesamiento anti-fuga y espacio R^28
│
├── notebooks/                    # Entorno analítico interactivo
│   ├── pipeline_completo.ipynb   # Flujo end-to-end: ingesta, EDA, modelado y SHAP
│   └── README.md                 # Guía del flujo interactivo
│
├── Documentation/                # Sistema de documentación académica oficial
│   ├── latex/                    # Master LaTeX (main.tex, main.pdf, references.bib)
│   ├── sections/                 # Capítulos modulares del informe (01 a 11)
│   ├── Observaciones a levantar/ # Memoria de auditorías, logs por timestamp y rúbricas
│   └── README.md                 # Guía del sistema documental
│
└── Data/
    ├── 2024/enaho/               # Microdatos brutos ENAHO 2024 (M01, M02, M03, M05, M34)
    ├── 2025/enaho/               # Microdatos brutos ENAHO 2025 (M01, M02, M03, M05, M34)
    ├── processed/                # Datasets consolidados procesados
    └── Fuentes.md                # Fichas metodológicas y enlaces oficiales del INEI
```

---

## 6. Instalación y Uso Rápido

### Requisitos Previos
Python 3.10 o superior:
```bash
git clone <url-del-repositorio>
cd "Tarea Académica"
pip install -r requirements.txt
```

### Construir los Conjuntos de Entrenamiento y Prueba
```python
from src.dataset import load_train_test_master

# Cargar Train 2024 (4,090 hogares) y Test 2025 sin panel (3,199 hogares)
df_train, df_test = load_train_test_master(data_root="Data")

print(f"Train 2024: {df_train.shape} | Tasa de pobreza: {df_train['y'].mean():.2%}")
print(f"Test 2025:  {df_test.shape}  | Tasa de pobreza: {df_test['y'].mean():.2%}")
```

### Aplicar el Preprocesamiento Anti-Fuga ($\mathbb{R}^{28}$)
```python
from src.preprocessing import build_preprocessor, CANONICAL_FEATURES_28

preprocessor = build_preprocessor()

# Ajustar únicamente sobre train para evitar cualquier filtración de datos
X_train = df_train[CANONICAL_FEATURES_28]
X_train_trans = preprocessor.fit_transform(X_train)

print(f"Matriz procesada de entrenamiento: {X_train_trans.shape}")
```
