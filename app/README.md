# Encuesta web de Condiciones de Vida del Hogar (Lima Metropolitana y Callao)

Interfaz ciudadana y API para recoger, en lenguaje sencillo, las respuestas crudas que necesita el modelo del proyecto
(`models/winner_bundle.joblib`). **Etapa 1:** la API recibe y valida las respuestas, sin modelo y sin guardar datos.
**Etapa 2:** conectar el modelo (ver la última sección).

```
app/
├── shared/survey_catalog.json   ← catálogo único: preguntas, opciones y códigos ENAHO (lo leen la web y la API)
├── backend/                     ← FastAPI + Pydantic v2 (validación y reglas de salto)
│   ├── api/  (main.py, rules.py, schemas.py, summary.py, catalog.py)
│   └── tests/test_api.py        ← 22 pruebas (pytest)
├── frontend/                    ← React 19 + Vite + TypeScript + Tailwind 4 (estilo "chai latte")
│   └── nginx.conf               ← sirve la web y redirige /api al contenedor de la API
└── docker-compose.yml           ← despliegue: 2 contenedores (api, web)
```

## Flujo

1. **Portada** (`/`): qué es la encuesta, qué no es (no es un trámite oficial ni da acceso a programas sociales) y cómo se tratan los datos.
2. **Encuesta** (`/encuesta`): 5 pasos (Tu hogar, La vivienda, Tenencia y servicios, Integrantes y estudios, Trabajo y pensiones) con una ficha viva lateral, borrador en `localStorage` y validación en cada paso.
   - Si el hogar comparte la vivienda con otro hogar principal, se omite el paso de vivienda (`es_hogar_secundario`).
   - La frecuencia del agua solo se pregunta con red pública o pilón; las preguntas laborales, solo si la jefatura trabajó.
   - Las edades se registran sin doble conteo (0–5, 6–13, 65+; el grupo de 14–64 se calcula) y los contadores no dejan superar el total del hogar.
   - En hogares de una persona, las edades, el nivel educativo máximo y los ocupados se completan solos.
3. **Revisión** con edición por bloque y **comprobante** con folio (`ENC-2026-XXXXXX`) y el resumen que devuelve la API.

La web no calcula ratios ni escala variables: envía conteos y códigos. Los ratios (`personas_por_hab`, `tasa_dependencia`, `ocupados_por_miembro`) los calcula el modelo en la Etapa 2.

## API

| Método | Ruta | Respuesta |
| :--- | :--- | :--- |
| GET | `/health` | `{"status": "ok", "stage": "validation_only", "model_ready": false}` |
| GET | `/api/v1/survey-schema` | El catálogo `shared/survey_catalog.json` |
| POST | `/api/v1/surveys/validate` | 200: folio, fecha, resumen por bloques y `answers_normalized` · 422: `{"errors": [{"field", "message"}]}` |

`answers_normalized` es exactamente el diccionario que recibe `build_household_dataframe_from_answers` en `src/inference.py`
(una prueba automática lo verifica leyendo ese archivo). Documentación interactiva: `/api/docs`.

## Desarrollo local

```bash
# API (Python 3.12+)
cd app/backend
python -m venv .venv
.venv/Scripts/pip install -r requirements-dev.txt     # Linux/Mac: .venv/bin/pip
.venv/Scripts/python -m pytest -q
.venv/Scripts/python -m uvicorn api.main:app --port 8000

# Web (Node 22+), en otra terminal: http://localhost:5173 (redirige /api al puerto 8000)
cd app/frontend
npm install
npm run dev
```

## Despliegue con Docker

```bash
cd app
docker compose up -d --build      # web en el puerto 80 (cambiar con WEB_PORT=8080)
docker compose ps                 # ambos servicios deben figurar "healthy"/"running"
curl http://localhost/health
```

### En AWS Academy Learner Lab (EC2)

1. **Lanzar la instancia:** Ubuntu Server 24.04, `t3.small` (o `t3.micro` con swap), 16 GB de disco.
   - Security group: entrada TCP 22 (SSH) y TCP 80 (HTTP) desde `0.0.0.0/0`.
2. **Instalar Docker:**
   ```bash
   sudo apt-get update && sudo apt-get install -y docker.io docker-compose-v2 docker-buildx git
   sudo usermod -aG docker ubuntu && newgrp docker
   ```
3. **Clonar y levantar:**
   ```bash
   git clone https://github.com/Ga3lAE/IA-Tarea-Academica.git
   cd IA-Tarea-Academica/app
   docker compose up -d --build
   ```
4. **Abrir** `http://<IP pública de la instancia>`.

Notas para la exposición:
- El Learner Lab apaga la sesión a las ~4 horas y la IP pública cambia al reiniciar; iniciar el lab y verificar la URL 15–20 minutos antes. Una Elastic IP evita el cambio de IP.
- Para HTTPS sin dominio, poner una distribución de CloudFront delante de la instancia (origen HTTP:80, sin caché para `/api/*`).
- Al terminar el curso: detener o terminar la instancia y liberar la Elastic IP.

## Etapa 2: conectar el modelo

El `.joblib` solo necesita scikit-learn (Stacking con LogisticRegression, RandomForest, ExtraTrees y HistGradientBoosting); no usa lightgbm, xgboost, catboost ni shap.

1. **Dependencias:** añadir a `backend/requirements.txt` `scikit-learn==1.9.1`, `numpy`, `pandas` y `joblib==1.6.0`, iguales a las del entorno que serializó el artefacto.
2. **Contexto de construcción:** cambiarlo a la raíz del repositorio y copiar en la imagen `src/preprocessing.py` (con un `src/__init__.py`, porque el pickle importa `src.preprocessing.SecondaryHouseholdImputer`) y `models/winner_bundle.joblib`.
   - Añadir un `.dockerignore` en la raíz que excluya `Data/` y `notebooks/`.
3. **Endpoint:** crear `POST /api/v1/predict`.
   - Reutilizar `validate_and_normalize`.
   - Construir la fila con la lógica de `build_household_dataframe_from_answers`, copiada a un módulo liviano sin importar `src.dataset` ni `src.models`.
   - Devolver probabilidad, percentil (`oof_probs_sorted`), `tau_rec70` y `cutoff_b20`.
