# Plan de concretización v2: implementación corregida y orden de ejecución

**Fecha y hora de registro:** 08 de octubre de 2026, 20:30 (-05:00)
**Base:** `concretizacion_2026-10-08_20-03.md` (v1). Aquí solo van las **correcciones y agregados**; lo que no se menciona se implementa tal como está en v1.
**Respaldo:** [`problemas_2026-10-08_20-30.md`](./problemas_2026-10-08_20-30.md) · [`metodologia_2026-10-08_20-30.md`](./metodologia_2026-10-08_20-30.md) · [`scripts/chequeo_cobertura.py`](./scripts/chequeo_cobertura.py)

---

## 1. Bibliografía: `references.bib` definitivo (reemplaza §1 de v1)

Cambios respecto de v1:
- `inei2024pobreza` → `inei2025pobreza`: título y año corregidos (E-08).
- Se **eliminan** `trivelli2023pobreza` y `grade2024autoconstruccion`, que no existen (E-09, E-10).
- Se **agregan** `espinoza2020mapeo`, `roberts2017cross` y `noriega2018fairness`.
- Se **eliminan** las entradas no citadas o erróneas del `.bib` actual: `eaamo2023moving`, `jean2016combining`, `blumenstock2015predicting` y `fernandez2018smote`.

```bibtex
@article{mcbride2018retooling,
  author={McBride, Linden and Nichols, Austin},
  title={Retooling poverty targeting using out-of-sample validation and machine learning},
  journal={The World Bank Economic Review}, volume={32}, number={3}, pages={531--550}, year={2018},
  doi={10.1093/wber/lhw056}}

@article{brown2018poor,
  author={Brown, Caitlin and Ravallion, Martin and van de Walle, Dominique},
  title={A poor means test? {E}conometric targeting in {A}frica},
  journal={Journal of Development Economics}, volume={134}, pages={109--124}, year={2018},
  doi={10.1016/j.jdeveco.2018.05.004}}

@inproceedings{noriega2020algorithmic,
  author={Noriega-Campero, Alejandro and Garcia-Bulle, Bernardo and Cantu, Luis Fernando and Bakker, Michiel A. and Tejerina, Luis and Pentland, Alex},
  title={Algorithmic targeting of social policies: Fairness, accuracy, and distributed governance},
  booktitle={Proc. 2020 Conference on Fairness, Accountability, and Transparency (FAT*)},
  pages={241--251}, year={2020}, doi={10.1145/3351095.3375784}}

@inproceedings{noriega2018fairness,
  author={Noriega, Alejandro and Garcia-Bulle, Bernardo and Tejerina, Luis and Pentland, Alex},
  title={Algorithmic fairness and efficiency in targeting social welfare programs at scale},
  booktitle={Bloomberg Data for Good Exchange Conference}, address={New York}, year={2018}}

@inproceedings{aiken2023moving,
  author={Aiken, Emily and Ohlenburg, Tim and Blumenstock, Joshua},
  title={Moving targets: When does a poverty prediction model need to be updated?},
  booktitle={Proc. 6th ACM SIGCAS/SIGCHI Conference on Computing and Sustainable Societies (COMPASS '23)},
  year={2023}, doi={10.1145/3588001.3609369}}

@article{aiken2022machine,
  author={Aiken, Emily and Bellue, Suzanne and Karlan, Dean and Udry, Christopher and Blumenstock, Joshua E.},
  title={Machine learning and phone data can improve targeting of humanitarian aid},
  journal={Nature}, volume={603}, number={7903}, pages={864--870}, year={2022},
  doi={10.1038/s41586-022-04484-9}}

@inproceedings{grinsztajn2022tree,
  author={Grinsztajn, L{\'e}o and Oyallon, Edouard and Varoquaux, Ga{\"e}l},
  title={Why do tree-based models still outperform deep learning on typical tabular data?},
  booktitle={Advances in Neural Information Processing Systems}, volume={35}, pages={507--520}, year={2022}}

@inproceedings{elkan2001foundations,
  author={Elkan, Charles},
  title={The foundations of cost-sensitive learning},
  booktitle={Proc. 17th International Joint Conference on Artificial Intelligence (IJCAI)},
  pages={973--978}, year={2001}}

@article{roberts2017cross,
  author={Roberts, David R. and Bahn, Volker and Ciuti, Simone and Boyce, Mark S. and Elith, Jane and others},
  title={Cross-validation strategies for data with temporal, spatial, hierarchical, or phylogenetic structure},
  journal={Ecography}, volume={40}, number={8}, pages={913--929}, year={2017}, doi={10.1111/ecog.02881}}

@book{mitchell1997machine,
  author={Mitchell, Tom M.}, title={Machine Learning}, publisher={McGraw-Hill}, address={New York}, year={1997}}

@techreport{inei2025pobreza,
  author={{Instituto Nacional de Estad{\'i}stica e Inform{\'a}tica}},
  title={Per{\'u}: Evoluci{\'o}n de la Pobreza Monetaria, 2015--2024. Informe T{\'e}cnico},
  institution={INEI}, address={Lima}, month=may, year={2025},
  url={https://www.gob.pe/institucion/inei/informes-publicaciones/6763186-peru-evolucion-de-la-pobreza-monetaria-2015-2024}}

@techreport{espinoza2020mapeo,
  author={Espinoza, {\'A}lvaro and Fort, Ricardo},
  title={Mapeo y tipolog{\'i}a de la expansi{\'o}n urbana en el {P}er{\'u}},
  institution={Grupo de An{\'a}lisis para el Desarrollo (GRADE) y Asociaci{\'o}n de Desarrolladores Inmobiliarios (ADI)},
  address={Lima}, year={2020},
  url={https://www.grade.org.pe/wp-content/uploads/EspinozaFort_GRADEADI_expansionurbana.pdf}}

@book{grosh2022revisiting,
  author={Grosh, Margaret and Leite, Phillippe and Wai-Poi, Matthew and Tesliuc, Emil},
  title={Revisiting Targeting in Social Assistance: A New Look at Old Dilemmas},
  publisher={World Bank}, address={Washington, DC}, year={2022}}
```

**Aceptación:** `bibtex main` sin *warnings* de entradas faltantes y `grep -c "\[?\]"` igual a 0 en el texto del PDF.

---

## 2. Textos LaTeX corregidos

### 2.1 Resumen (`main.tex`, reemplaza el actual; ≤ 12 líneas, sin cifras, citas ni fórmulas)
```latex
\textbf{Resumen}---La pobreza monetaria de Lima Metropolitana y el Callao se duplicó tras la pandemia y hoy concentra a más de un tercio de los pobres del país, mientras que buena parte de los hogares pobres no recibe apoyo de los programas sociales. Este trabajo plantea identificar a los hogares pobres sin medir su ingreso ni su gasto, mediante clasificadores supervisados entrenados con características observables de la vivienda, la composición del hogar, la educación y el empleo, tomadas de la Encuesta Nacional de Hogares. Se comparan una línea base econométrica, una regresión logística y ensambles de árboles, con aprendizaje sensible al costo, comparación de modelos a igual cobertura presupuestal, validación agrupada por conglomerado y evaluación fuera de tiempo que excluye a los hogares repetidos entre años. El objetivo es determinar si la mejora en la detección proviene de una representación más rica del hogar o de la complejidad del algoritmo, y si se mantiene de un año al siguiente.
```

### 2.2 Introducción: cambios sobre el texto v1 §2.1
| Texto v1 | Reemplazar por |
|---|---|
| `\cite{inei2024pobreza}` | `\cite{inei2025pobreza}` |
| «pobreza urbana cara» `\cite{trivelli2023pobreza}`, condicionada por una tasa de subempleo e informalidad laboral del 57.3\% que genera… | A diferencia de la pobreza rural, la pobreza urbana se asocia a ingresos informales y volátiles, difíciles de verificar por los programas sociales. |
| Históricamente, los mecanismos de focalización estatal mediante PMT, diseñados sobre regresiones lineales por MCO, han mostrado severas fallas estructurales en grandes metrópolis. | Los mecanismos de focalización basados en \textit{Proxy Means Testing} (PMT), calibrados habitualmente con regresiones lineales sobre el gasto, excluyen a una fracción considerable de los hogares pobres \cite{brown2018poor}. |
| …se comprueba que el 63.0\% de los hogares pobres urbanos no recibe asistencia alguna… | …en Lima Metropolitana, el 67.2\% de los hogares pobres (520 de 774) no registra transferencias monetarias públicas ni donaciones públicas de alimentos, una brecha de cobertura que no puede atribuirse únicamente al instrumento de focalización. |
| …producto de décadas de autoconstrucción informal consolidada `\cite{grade2024autoconstruccion}`, la probabilidad condicional de pobreza en viviendas con paredes de ladrillo alcanza el 14.5\%, frente a un 35.0\%… Dado que el 76.1\%… | …dado que más del 90\% de la expansión urbana reciente fue informal y autoconstruida \cite{espinoza2020mapeo}, el 84.5\% de los hogares limeños tiene paredes de ladrillo: la pobreza es de 15.5\% en ellos frente a 40.0\% en viviendas de madera o estera. El material discrimina, pero no basta: un modelo solo con vivienda alcanza una PR-AUC de 0.35, frente a 0.55 al añadir demografía, educación y empleo. |
| Pregunta e hipótesis H1–H4 de v1 | Pregunta y tabla H1–H4 de `metodologia_2026-10-08_20-30.md` §3 (H2 como prueba de equivalencia) |
| OE3: …optimizados con pérdidas sensibles al costo ($c_1 \gg c_0$). | …con pérdida sensible al costo cuyo peso $\alpha = c_1/c_0$ se trata como hiperparámetro. |
| OE4: …curvas de exclusión a cobertura fija y auditoría… | …comparación de modelos con la misma cobertura presupuestal (B = 20\%) y curvas de exclusión-inclusión. |

> Las cifras 84,5 %, 15,5 % y 40,0 % se calcularon con `DOMINIO 8` y 2024 (`Data/processed/modulo01_2024_cleaned.csv` cruzado con Sumaria). Con 2,15 % (nulos), usar la cifra del año correspondiente: 106 hogares en 2024 y 120 en 2025.

### 2.3 Trabajos relacionados (reemplaza íntegramente v1 §2.2)
```latex
\section{Trabajos relacionados}

McBride y Nichols \cite{mcbride2018retooling} replicaron las herramientas PMT de USAID con encuestas de Bolivia, Timor-Leste y Malawi, y compararon modelos elegidos por validación cruzada con \textit{random forest} y \textit{quantile regression forest}. La selección fuera de muestra mejoró el criterio balanceado de exactitud de pobreza (BPAC) entre 2.7\% y 17.5\% y redujo la subcobertura; además, el modelo paramétrico bien validado rindió igual o mejor que los ensambles. Sus particiones aleatorias ignoran el diseño muestral y, según los autores, el método funciona fuera de muestra pero no fuera de población. Adoptamos su selección por validación y un comparador lineal fuerte.

Brown, Ravallion y van de Walle \cite{brown2018poor} evaluaron el PMT econométrico en nueve países africanos: con una pobreza de 20\%, el PMT por MCO excluye en promedio al 81\% de los pobres, y los estimadores centrados en la pobreza reducen esa exclusión a costa de más inclusión. No evalúan aprendizaje automático y su contexto es mayormente rural. Adoptamos el PMT-MCO sobre $\ln(\text{gasto})$ como línea base y priorizamos el error de exclusión.

Noriega-Campero et al. \cite{noriega2020algorithmic} reportan que la focalización con aprendizaje automático habría cubierto a casi un millón de pobres más en dos países sin elevar el gasto, aunque genera disparidades entre subgrupos si no se restringe. En su versión preliminar \cite{noriega2018fairness}, el \textit{gradient boosting} fue el mejor modelo, el umbral define una curva exclusión-inclusión y los pobres urbanos de Ecuador resultaron 2.3 veces más excluidos que los rurales. Evalúan con una sola partición aleatoria y sin validación temporal. Adoptamos la comparación con la misma cobertura y la auditoría por subgrupos.

Aiken, Ohlenburg y Blumenstock \cite{aiken2023moving} analizaron diez años de encuestas de cuatro países africanos: los errores del PMT aumentan 1.7 puntos porcentuales por año sin actualización, sobre todo por el cambio en las características de los hogares. Su evidencia proviene de PMT lineales en contextos rurales. Adoptamos la evaluación fuera de tiempo 2024$\rightarrow$2025.

Como apoyo, Aiken et al. \cite{aiken2022machine} muestran que, con datos de telefonía, la exclusión baja 4--21\% frente a la focalización geográfica pero sube 9--35\% frente a un PMT con registro social, lo que respalda usar datos de encuesta; y Grinsztajn et al. \cite{grinsztajn2022tree} muestran que los árboles son el estado del arte en tablas de tamaño medio.
```
Si sobra espacio (máximo 0,25 pág.), agregar una **Tabla 1** con 4 filas (estudio · datos · método · hallazgo · limitación · adopción).

### 2.4 Metodología: cambios sobre el texto v1 §2.3
| Lugar | Texto v1 | Reemplazar por |
|---|---|---|
| Medida de desempeño | …donde la relación $c_1/c_0 \approx 4.28$ penaliza asimétricamente…, induciendo un umbral operativo analítico $p^* = c_0/(c_0+c_1) \approx 0.19$. | …donde $\alpha = c_1/c_0 \in \{1, 2, \gamma\}$, con $\gamma \approx 4.28$ el cociente de frecuencias, se elige por validación. Reponderar equivale a desplazar el umbral de un modelo sin costos a $p^* = 1/(1+\alpha)$ \cite{elkan2001foundations}, por lo que no se aplican ambos a la vez. Los modelos se comparan con la misma cobertura B = 20\% \cite{noriega2020algorithmic}. |
| Tabla 2, fila "Validación interna por conglomerados" | Aiken et al., McBride \& Nichols | `Roberts et al. \cite{roberts2017cross}` |
| Tabla 2, fila nueva | — | Purga de panel · 930 hogares repetidos se excluyen del test · `\cite{aiken2023moving}` (ya está; mantener) |
| Operadores (OBS-15) | `HousingCohortImputer`, `HouseholdAggregator`, `DomainBinner` | Describirlos por su función, sin nombres de clase inexistentes, o con los nombres reales del código: imputación intra-vivienda (`Modulo01Processor.clean_and_impute`), agregación individuo→hogar (procesadores de los módulos 02, 03 y 05) y agrupación de categorías **ajustada solo con 2024** |
| Figura de pisos | Frecuencias y tasas departamentales | Recalcular con `DOMINIO 8`, 2024: noble 49,8 % (pobreza 8,2 %), cemento 46,0 % (28,9 %), precario 4,2 % (37,2 %). Si falta espacio, eliminar la figura y dejar una frase |
| Párrafo de patologías del EDA | "…el 57.3\% de jefes de hogar labora en la informalidad…" | Eliminar (E-14) |
| Figura del pipeline, caja 3 | Pérdida sensible al costo $c_1/c_0 \approx 4.28$ | Pérdida sensible al costo con $\alpha$ como hiperparámetro; comparación con la misma cobertura B |

### 2.5 Declaración de uso de IA (reemplaza v1 §2.4; **el grupo debe ajustarla a su uso real**)
```latex
\section{Declaración de uso de IA}
Se emplearon asistentes de inteligencia artificial (indicar herramientas, por ejemplo Claude y ChatGPT) para: (i) revisar y verificar la bibliografía contra sus fuentes originales; (ii) auditar el código y los cálculos sobre los microdatos de la ENAHO; (iii) proponer borradores de redacción y de código en Python y \LaTeX. Todas las cifras del informe fueron recalculadas con los scripts del repositorio y los textos fueron revisados y editados por el grupo. La responsabilidad del contenido final recae en los autores.
```

### 2.6 Secciones fuera del parcial
Para respetar el límite de 4 páginas, **comentar** en `main.tex` los `\input` de 04 (experimentación), 05 (conclusión), 06 (trabajos futuros) y 07 (ética). Se mantienen 08 (repositorio), 09 (contribución), 10 (IA) y 11 (referencias).

---

## 3. Parches de código (v1 1–5 se aplican tal cual; se agregan 6–9)

**Parche 5 (v1) completo:** reemplazar la búsqueda de `find_csv` para Sumaria por un patrón exacto:
```python
# src/pipeline.py, al inicio de find_csv
import re
patterns = {"modulo34": re.compile(rf"^Sumaria-{year}\.csv$", re.I)}
pat = patterns.get(mod_clean)
...
for f in d.glob("*.csv"):
    if f.name.endswith("_cleaned.csv"):
        continue
    if (pat.match(f.name) if pat else year_str in f.name):
        return f
```

**Parche 6 (G-04), llave con año:** en `ENAHOPipeline.run_module`:
```python
df_year = processor.process().reset_index()
df_year.insert(0, "anio_encuesta", yr)
...
df_concat = pd.concat(list(results.values()), axis=0, ignore_index=True)
```
Y en `src/config/base.py`: `PRIMARY_KEY_HOUSEHOLD_PANEL = ["anio_encuesta", "conglomerado", "vivienda", "hogar"]`.

**Parche 7 (OBS-19), transparencia de los *fallbacks*:** en `Modulo01Processor.apply_mappings`, antes de `fillna(default_val)`, registrar `n_fallback = mapped_series.isna().sum()` por columna y loguearlo. En `clean_and_impute`, reemplazar `fillna(1)` por la mediana del dominio y agregar el indicador `habitaciones_imputadas`.

**Parche 8, separador de salida:** unificar con `DEFAULT_OUTPUT_SEPARATOR = ","` y corregir el *docstring* y `IMPLEMENTATION.md` (o al revés, pero en un solo valor).

**Parche 9, validación del alcance:** después del Parche 1, ajustar `MIN_EXPECTED_ROWS_LIMA_CALLAO = 3800` y `MAX_EXPECTED_ROWS_LIMA_CALLAO = 4600`, y regenerar `Data/processed/modulo01_{2024,2025}_cleaned.csv` (deben quedar 4,090 y 4,129 filas).

---

## 4. Orden de ejecución con criterio de aceptación

| Paso | Acción | Aceptación |
|:-:|---|---|
| 1 | Parches de código 1–9 y regeneración de `Data/processed/` | 4,090 y 4,129 filas; 0 cruces entre viviendas en la imputación; el notebook corre sin `KeyError` y se sube **con salidas** |
| 2 | `references.bib` (§1) | `bibtex` sin *warnings* de entradas faltantes |
| 3 | Resumen, introducción, trabajos relacionados y metodología (§2.1–2.4) | Ninguna cifra sin script de respaldo (`scripts/analisis_alcance.py`, `scripts/cifras_contexto.py`, `scripts/chequeo_factibilidad.py`, `scripts/chequeo_cobertura.py`) |
| 4 | Declaraciones (§2.5) y secciones fuera del parcial (§2.6) | La declaración de IA refleja el uso real |
| 5 | Compilar: `pdflatex` → `bibtex` → `pdflatex` ×2 | 0 `[?]`, 0 errores; **cuerpo ≤ 4 páginas** (las referencias pueden pasar a la pág. 5); sin textos guía de la plantilla |
| 6 | Revisión visual del PDF y renombrado a `GrupoX-TA-Parcial.pdf` (X = número de grupo) | Cumple la guía §6 (nombre del archivo) |
| 7 | Commits por bloque y *push* | Mensajes: `FIX: alcance DOMINIO 8 y bugs módulo 01`, `FIX: bibliografía verificada`, `MOD: informe parcial v2` |
