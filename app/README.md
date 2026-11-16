# Encuesta y estimación web de pobreza monetaria del hogar (Lima Metropolitana y Callao)

Interfaz ciudadana y API que recogen, en lenguaje sencillo, las respuestas crudas del hogar. Al terminar, el **modelo entrenado del proyecto** (`models/winner_bundle.joblib`: Stacking entrenado con 7,289 hogares de la ENAHO 2024–2025) estima la probabilidad de pobreza monetaria y explica qué características pesaron más. La API no guarda respuestas.

```
app/
├── shared/survey_catalog.json   ← catálogo único: preguntas, opciones y códigos ENAHO (lo leen la web y la API)
├── backend/                     ← FastAPI + Pydantic v2
│   ├── api/  main.py            ← rutas; carga el modelo una vez al iniciar
│   │         rules.py           ← saltos de la ENAHO y coherencia entre preguntas
│   │         predictor.py       ← estimación: reutiliza src/inference.py y traduce los factores a lenguaje ciudadano
│   │         schemas.py, summary.py, catalog.py
│   └── tests/                   ← 32 pruebas (pytest): validación + paridad exacta con la encuesta por consola
├── frontend/                    ← React 19 + Vite + TypeScript + Tailwind 4 (estilo "chai latte")
│   └── nginx.conf               ← sirve la web y redirige /api al contenedor de la API
└── docker-compose.yml           ← despliegue: 2 contenedores (api, web)
```

## Flujo

1. **Portada** (`/`): qué hace la herramienta, qué no es (no es un trámite oficial ni da acceso a programas sociales) y cómo se tratan los datos.
2. **Encuesta** (`/encuesta`): 5 pasos (Tu hogar, La vivienda, Tenencia y servicios, Integrantes y estudios, Trabajo y pensiones) con una ficha viva lateral, borrador en `localStorage` y validación en cada paso.
   - Si el hogar comparte la vivienda con otro hogar principal, se omite el paso de vivienda (`es_hogar_secundario`).
   - La frecuencia del agua solo se pregunta con red pública o pilón; las preguntas laborales, solo si la jefatura trabajó; el registro del trabajo no se pregunta a trabajadores del hogar (como en la ENAHO).
   - Las edades se registran sin doble conteo (0–5, 6–13, 65+; el grupo de 14–64 se calcula) y los contadores no dejan superar el total del hogar.
   - En hogares de una persona, las edades, el nivel educativo máximo y los ocupados se completan solos.
3. **Revisión** con edición por bloque.
4. **Resultado:**
   - probabilidad estimada y nivel:
     - **alta** si está entre el 20% de mayor probabilidad (≥ `cutoff_b20` = 29.1%);
     - **moderada** si supera el umbral de riesgo (≥ `tau_rec70` = 19.7%);
     - **baja** en otro caso;
   - percentil frente a los hogares de entrenamiento;
   - factores que elevan o reducen la estimación (TreeSHAP del explicador);
   - cómo leer el resultado y sus límites;
   - folio y resumen de respuestas.

La web no calcula ratios ni escala variables: envía conteos y códigos. Los ratios (`personas_por_hab`, `tasa_dependencia`, `ocupados_por_miembro`), la imputación de hogares secundarios y el escalamiento los aplica el pipeline congelado del modelo.

## API

| Método | Ruta | Respuesta |
| :--- | :--- | :--- |
| GET | `/health` | `status`, `stage` (`prediction` o `validation_only`), `model_ready` y metadatos del modelo (umbrales, hogares de entrenamiento) |
| GET | `/api/v1/survey-schema` | El catálogo `shared/survey_catalog.json` |
| POST | `/api/v1/predict` | 200: folio, resumen, `answers_normalized` y `prediction` (probabilidad, percentil, nivel, umbrales, `factores_riesgo`, `factores_proteccion`) · 422: `{"errors": [{"field", "message"}]}` · 503 si el modelo no cargó |
| POST | `/api/v1/surveys/validate` | Solo validación (sin modelo) |

**Sin duplicar el entrenamiento:** `api/predictor.py` llama a `predict_single_household` de `src/inference.py`, la misma función que `src/encuesta_pobreza.py`. Las pruebas confirman que los 3 perfiles de `PRESET_HOUSEHOLDS` enviados por la web dan exactamente las cifras de la consola: 91.44%, 59.52% y 4.17%. Documentación interactiva: `/api/docs`.

## Desarrollo local

```bash
# API (Python 3.14; el .joblib requiere scikit-learn 1.9.1)
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

En local, la API encuentra `src/` y `models/winner_bundle.joblib` en la raíz del repositorio.

## Despliegue con Docker

```bash
cd app
docker compose up -d --build      # web en el puerto 80 (cambiar con WEB_PORT=8080)
docker compose ps                 # "api" debe figurar healthy (el healthcheck exige model_ready)
curl http://localhost/health
```

**Contexto de la imagen de la API:** es la raíz del repositorio. La imagen copia `src/*.py` y `models/winner_bundle.joblib`, y el `.dockerignore` de la raíz deja fuera `Data/`, `notebooks/` y `Documentation/`. Así el modelo viaja dentro de la imagen sin duplicarlo en `app/`.

**Si se reentrena el modelo:** volver a ejecutar `docker compose up -d --build`.

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
