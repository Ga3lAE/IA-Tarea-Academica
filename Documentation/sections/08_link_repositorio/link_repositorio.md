# Sección 8: Link del Repositorio del Trabajo

## 1. Repositorio Oficial del Proyecto
* **Enlace Oficial:** `https://github.com/usuario/pucp-ia-tarea-academica`
* **Acceso y Credenciales:** Repositorio institucional con permisos de lectura para el docente y asistentes del curso Inteligencia Artificial (1INF24 - PUCP).

---

## 2. Estructura y Contenido del Repositorio
* `src/`: Pipeline de datos modular desarrollado bajo principios SOLID y arquitectura desacoplada.
  * `core/`: Clases base abstractas, validadores de esquema de microdatos y cortafuegos contra fuga de información (*Zero-Leakage Firewall*).
  * `processors/`: Procesadores especializados por módulo de la ENAHO (01, 02, 03, 05, 34).
* `Data/`: Microdatos ENAHO 2024 y 2025 organizados en subcarpetas `raw/` y `processed/` (versionados con Git LFS).
* `Documentation/`: Memoria metodológica modular en Markdown y proyecto tipográfico oficial en $\text{\LaTeX}$ (`main.tex` $\to$ `main.pdf`).
* `notebooks/`: Cuadernos Jupyter con validaciones automáticas, análisis exploratorio (EDA) y curvas de calibración.
