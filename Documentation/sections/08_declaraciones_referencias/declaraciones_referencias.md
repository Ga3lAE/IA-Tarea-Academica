# Sección 8: Declaraciones y Referencias

## 1. Repositorio del Trabajo
* **Enlace Oficial:** `https://github.com/usuario/pucp-ia-tarea-academica`
* **Acceso y Credenciales:** Repositorio público / privado con invitación de acceso al correo institucional del docente del curso (1INF24).
* **Estructura del Repositorio:**
  * `src/`: Pipeline de datos modular (Open/Closed Principle) y procesadores por módulo.
  * `Data/`: Microdatos ENAHO 2024 y 2025 versionados mediante Git LFS.
  * `Documentation/`: Formato de informe oficial, borradores en Markdown y proyecto LaTeX modular.
  * `notebooks/`: Cuadernos Jupyter con validaciones automáticas y exploraciones de EDA.

---

## 2. Declaración de Contribución de Integrantes

| Integrante | Código PUCP | Responsabilidades y Aportes al Proyecto |
| :--- | :---: | :--- |
| **Gael Arias** | 2021XXXX | Arquitectura de software modular (`src/core/base_processor.py`), validadores de esquema y calidad bajo principios SOLID, formalización matemática del problema de aprendizaje supervisado y estructuración del proyecto LaTeX. |
| **Integrante 2** | 2021XXXX | Revisión exhaustiva de literatura científica sobre Proxy Means Testing, extracción y limpieza de microdatos del Módulo 01 (Vivienda) y Módulo 02 (Demografía), y diseño de los experimentos de ablation. |
| **Integrante 3** | 2021XXXX | Formulación de la función de pérdida sensible al costo, extracción del Módulo 05 (Empleo informal), diseño del setup de validación temporal out-of-time (2024 $\to$ 2025) y redacción del informe. |

---

## 3. Declaración de Uso de Inteligencia Artificial

Durante el desarrollo del presente trabajo académico se utilizaron herramientas de Inteligencia Artificial Generativa bajo el siguiente marco ético y operativo:
* **Herramientas Utilizadas:** Modelos de lenguaje avanzados (Claude / Gemini / ChatGPT) como asistentes de soporte técnico.
* **Propósito de Uso:** Asistencia en la estructuración de la plantilla en $\text{\LaTeX}$ (geometría de páginas, configuración de colores y macros `fancyhdr`), depuración sintáctica de scripts en Python y revisión de estilo de citas bibliográficas IEEE.
* **Validación y Responsabilidad:** Todo el contenido conceptual, diseño metodológico, formulación matemática, análisis empírico de microdatos de la ENAHO y conclusiones fueron concebidos, revisados críticamente, verificados e integrados por los integrantes del grupo. La responsabilidad total sobre la originalidad, veracidad e integridad del informe recae enteramente en los autores.

---

## 4. Referencias Bibliográficas (Formato IEEE)

1. L. McBride and A. Nichols, "Retooling poverty targeting using out-of-sample machine learning and proxy means tests," *The World Bank Economic Review*, vol. 32, no. 3, pp. 531--550, 2018.
2. N. Jean, M. Burke, M. Sherrie, S. Ermon, D. B. Lobell, and S. Biswas, "Combining satellite imagery and machine learning to predict poverty," *Science*, vol. 353, no. 6301, pp. 790--794, 2016.
3. J. Blumenstock, G. Cadamuro, and R. On, "Predicting poverty and wealth from mobile phone metadata and machine learning," *Science*, vol. 350, no. 6264, pp. 1073--1076, 2015.
4. G. Ke, Q. Meng, T. Finley, T. Wang, W. Chen, W. Ma, Q. Ye, and T.-Y. Liu, "LightGBM: A highly efficient gradient boosting decision tree," in *Advances in Neural Information Processing Systems (NeurIPS)*, vol. 30, pp. 3146--3154, 2017.
5. S. M. Lundberg and S.-I. Lee, "A unified approach to interpreting model predictions," in *Advances in Neural Information Processing Systems (NeurIPS)*, vol. 30, pp. 4765--4774, 2017.
6. A. Fernández, S. García, F. Herrera, and N. V. Chawla, "SMOTE for learning from imbalanced data: progress and challenges, marking the 15-year anniversary," *Journal of Artificial Intelligence Research*, vol. 61, pp. 863--905, 2018.
7. V. O. K. Li, "Hints on writing technical papers and making presentations," *IEEE Transactions on Education*, vol. 42, no. 2, pp. 134--137, mayo de 1999.
