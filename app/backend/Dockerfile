# API de la encuesta: validación + estimación con el modelo del proyecto.
# Contexto de construcción: RAÍZ del repositorio (ver app/docker-compose.yml y /.dockerignore),
# para copiar el modelo entrenado y el código de inferencia sin duplicarlos dentro de app/.
FROM python:3.14-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    SURVEY_CATALOG_PATH=/srv/shared/survey_catalog.json \
    MODEL_BUNDLE_PATH=/srv/models/winner_bundle.joblib

WORKDIR /srv
COPY app/backend/requirements.txt .
RUN pip install -r requirements.txt

# Código de la API y catálogo único de la encuesta
COPY app/backend/api ./api
COPY app/shared ./shared
# Inferencia del proyecto (src/inference.py y dependencias) y modelo entrenado
COPY src/*.py ./src/
COPY models/winner_bundle.joblib ./models/winner_bundle.joblib

RUN useradd --system --uid 10001 appuser
USER appuser

EXPOSE 8000
HEALTHCHECK --interval=30s --timeout=3s --start-period=20s --retries=3 \
  CMD python -c "import json, urllib.request; h = json.load(urllib.request.urlopen('http://127.0.0.1:8000/health', timeout=2)); assert h['model_ready']"
# Un solo proceso: el modelo responde en ~150 ms y así cabe holgado en una t3.micro/t3.small.
CMD ["uvicorn", "api.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "1", "--proxy-headers", "--forwarded-allow-ips", "*"]
