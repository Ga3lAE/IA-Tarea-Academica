# Plan 2: levantamiento de observaciones v2 (implementado)

**Iteración:** `2026-10-08_20-30` · **Corrige a:** plan v1 (`../*_2026-10-08_20-03.md`)
**Estado:** ✅ implementado en el código y en el informe; PDF del entregable parcial compilado y verificado.

---

## 1. Contenido de esta carpeta

| Archivo | Para qué sirve |
|---|---|
| [`GrupoX-TA-Parcial.pdf`](./GrupoX-TA-Parcial.pdf) | **Entregable parcial** compilado desde `Documentation/latex/main.tex`. Antes de subirlo a Paideia, renombrarlo con el número de grupo (`GrupoN-TA-Parcial.pdf`; guía §6) |
| [`problemas_2026-10-08_20-30.md`](./problemas_2026-10-08_20-30.md) | Auditoría del plan v1: 15 errores factuales, 5 inconsistencias metodológicas y 7 vacíos frente a la rúbrica |
| [`metodologia_2026-10-08_20-30.md`](./metodologia_2026-10-08_20-30.md) | Decisiones v2: alcance y cifras, fichas de papers verificadas, H1–H4, regla de decisión, protocolo y presupuesto de páginas |
| [`concretizacion_2026-10-08_20-30.md`](./concretizacion_2026-10-08_20-30.md) | Bibliografía, textos LaTeX, parches de código y orden de ejecución con criterios de aceptación |
| [`scripts/analisis_alcance.py`](./scripts/analisis_alcance.py) | Alcance (`DOMINIO 8` vs. otros), pobreza ponderada = INEI, línea de pobreza, conglomerados y hogares panel |
| [`scripts/cifras_contexto.py`](./scripts/cifras_contexto.py) | Brecha de cobertura (67.2 %), materiales de vivienda (84.5 %, 15.5 % vs. 40.0 %), agrupación de pisos y nulos estructurales |
| [`scripts/chequeo_factibilidad.py`](./scripts/chequeo_factibilidad.py) | Modelo base 2024 → 2025: PR-AUC 0.35 (solo vivienda) → 0.55 (4 módulos); evidencia de H1 y H3 |
| [`scripts/chequeo_cobertura.py`](./scripts/chequeo_cobertura.py) | Error de exclusión con B = 20 % para PMT-MCO, logística y RF, con IC *bootstrap*; evidencia de H2 |

**Reproducir todas las cifras del informe** (desde la raíz del repositorio, con `Data/` descargado vía Git LFS):
```bash
python -m pip install pandas scikit-learn
python -c "from src.pipeline import ENAHOPipeline; ENAHOPipeline('Data').run_module('modulo01', [2024, 2025])"
python "Documentation/Observaciones a levantar/Plan 2/scripts/analisis_alcance.py" Data
python "Documentation/Observaciones a levantar/Plan 2/scripts/cifras_contexto.py" Data
python "Documentation/Observaciones a levantar/Plan 2/scripts/chequeo_factibilidad.py" Data
python "Documentation/Observaciones a levantar/Plan 2/scripts/chequeo_cobertura.py" Data
```

**Recompilar el PDF** (desde `Documentation/latex/`): `pdflatex main` → `bibtex main` → `pdflatex main` ×2.

---

## 2. Qué se implementó (cambios fuera de esta carpeta)

### Código (`src/`, `notebooks/`, `Data/processed/`)
| Cambio | Archivo | Observación |
|---|---|---|
| Alcance Lima Metropolitana = `DOMINIO 8` (`UBIGEO` `07` + `1501`) y límites de filas 3,800–4,600 | `src/config/base.py`, `src/config/modulo01.py`, `src/processors/modulo01.py` | OBS-04 |
| Imputación intra-vivienda aislada por grupo (`transform`) | `src/processors/modulo01.py` | OBS-16 |
| Mapeos INEI de `P110` (7 = Otra, 8 = Río) y `P113A` (sin código 4; 7 = Otro) | `src/config/modulo01.py` | OBS-17 |
| *Fallbacks* (`'otro'`, `fillna(1)`) registrados en el log | `src/processors/modulo01.py` | OBS-19 |
| `find_csv` con patrón exacto `Sumaria-YYYY.csv` y orden determinista | `src/pipeline.py` | OBS-20 |
| Unión multianual con llave `(anio_encuesta, conglomerado, vivienda, hogar)` | `src/pipeline.py`, `src/config/base.py` | G-04 (930 hogares panel) |
| Separador de salida unificado (`,`) en código y documentación | `src/config/base.py`, `src/core/base_processor.py` | OBS-22 |
| Columnas del notebook (`material_pared_exterior`, `material_piso`) | `notebooks/01_modulos/01_vivienda_modulo01.ipynb` | OBS-18 |
| Datos procesados regenerados: 4,090 (2024) y 4,129 (2025) hogares | `Data/processed/modulo01_*_cleaned.csv` | — |

### Informe (`Documentation/`)
| Cambio | Archivo |
|---|---|
| Bibliografía verificada (14 entradas; sin `[?]`) | `latex/references.bib` |
| Título, resumen (≤ 12 líneas, sin citas ni cifras) y secciones 4–7 fuera del parcial | `latex/main.tex` |
| Introducción: contexto con cifras verificadas, H1–H4 (H2 como equivalencia) y objetivos | `sections/01_introduccion/introduccion.tex` |
| Trabajos relacionados: 4 papers evaluados (incluye limitaciones), Tabla 1 y brecha de investigación | `sections/02_trabajos_relacionados/trabajos_relacionados.tex` |
| Metodología: ⟨T,E,P⟩, entrada/salida, 8 operadores/adaptaciones (incluye TreeSHAP), Tabla 2 y Figura 1 | `sections/03_metodologia/metodologia.tex` |
| Repositorio real, contribución sin códigos ficticios y declaración de IA fiel al uso | `sections/08_…`, `09_…`, `10_…` |

---

## 3. Verificación del entregable contra la guía y la rúbrica

| Requisito | Estado |
|---|---|
| Cuerpo ≤ 4 páginas sin bibliografía, doble columna, Montserrat | ✅ El cuerpo termina al inicio de la pág. 4; las referencias ocupan el resto de la pág. 4 |
| Contexto, relevancia y justificación (3 pts) | ✅ Cifras INEI y ENAHO reproducibles; problema dimensionado (8,219 hogares) |
| Hipótesis, pregunta y objetivos (3 pts) | ✅ H1–H4 falsables con evidencia preliminar; objetivo general y 4 específicos |
| ≥ 3 publicaciones identificadas **y evaluadas** (6 pts) | ✅ 4 papers con datos, método, hallazgo, **limitación** y adopción (Tabla 1) + 2 de apoyo |
| Metodología y adaptaciones con base en papers (6 pts) | ✅ Tabla 2 adaptación ↔ paper; figura autocontenida; protocolo contra la fuga |
| Redacción (2 pts) | ✅ Sin textos guía de la plantilla; estilo IEEE uniforme; 0 errores de compilación |
| Declaración de uso de IA (plantilla) | ✅ Describe el uso real; **el grupo debe confirmarla** |

---

## 4. Relación con la "Ronda 2" (archivos `../*_2026-10-08_20-30.md`)

Se integraron sus aportes válidos (brecha de investigación, TreeSHAP, tono, notación y modo condicional). Sus datos bibliográficos y numéricos que no coinciden con las fuentes están listados en [`problemas_2026-10-08_20-30.md` §6](./problemas_2026-10-08_20-30.md) y **no** se usaron en el informe.

## 5. Pendiente para el grupo

1. **Renombrar el PDF** con el número de grupo y subirlo a Paideia.
2. **Revisar la declaración de IA y la de contribución** (`sections/09_…` y `sections/10_…`): reflejan lo que figura en el repositorio, pero cada integrante debe validarlas.
3. **Para el entregable final:**
   - Implementar los procesadores de los módulos 02, 03, 05 y 34 con los operadores descritos en la metodología.
   - Ejecutar los experimentos de H1–H4 con validación agrupada.
   - Redactar las secciones 4–7, que ya están separadas en `main.tex`.
4. Las capas 1–2 de `Documentation/sections/**/metodologia*.md` y las síntesis `.md` conservan textos previos al plan. **La versión vigente es la de los `.tex`.** Cada archivo afectado tiene una nota al inicio.
