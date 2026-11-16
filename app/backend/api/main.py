"""API de la encuesta web: validación de respuestas (Etapa 1) y estimación con el modelo (Etapa 2).

No guarda respuestas: cada solicitud se valida, se evalúa en memoria y se descarta.
"""
from __future__ import annotations

import secrets
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from typing import Any, Dict, Tuple

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from . import catalog, predictor
from .rules import validate_and_normalize
from .schemas import ErrorResponse, FieldError, PredictionReceipt, SurveyAnswers, ValidationReceipt
from .summary import build_summary

_FOLIO_ALPHABET = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"


@asynccontextmanager
async def lifespan(_: FastAPI):
    predictor.load_model()  # una sola carga del .joblib por proceso
    yield


app = FastAPI(
    title="Encuesta de Condiciones de Vida del Hogar — API",
    version=catalog.load_catalog()["version"],
    docs_url="/api/docs",
    openapi_url="/api/openapi.json",
    lifespan=lifespan,
)


def _friendly(err: Dict[str, Any]) -> FieldError:
    loc = [str(p) for p in err.get("loc", []) if p not in ("body",)]
    field = loc[-1] if loc else "general"
    kind = err.get("type", "")
    ctx = err.get("ctx") or {}
    if kind == "missing":
        msg = "Esta pregunta es obligatoria."
    elif kind in ("greater_than_equal", "less_than_equal"):
        lo, hi = None, None
        try:
            lo, hi = catalog.bounds(field)
        except KeyError:
            pass
        msg = f"Ingresa un valor entre {lo} y {hi}." if lo is not None else f"Valor fuera de rango ({ctx})."
    elif kind == "extra_forbidden":
        msg = "Campo no reconocido por la encuesta."
    elif kind.startswith(("int_", "bool_", "string_")):
        msg = "El formato de la respuesta no es válido."
    else:
        msg = "Respuesta no válida."
    return FieldError(field=field, message=msg)


@app.exception_handler(RequestValidationError)
async def _validation_handler(_: Request, exc: RequestValidationError) -> JSONResponse:
    body = ErrorResponse(errors=[_friendly(e) for e in exc.errors()])
    return JSONResponse(status_code=422, content=body.model_dump())


def _invalid(errors) -> JSONResponse:
    body = ErrorResponse(errors=[FieldError(field=f, message=m) for f, m in errors])
    return JSONResponse(status_code=422, content=body.model_dump())


def _folio() -> Tuple[str, str]:
    now = datetime.now(timezone.utc)
    folio = "ENC-{}-{}".format(now.year, "".join(secrets.choice(_FOLIO_ALPHABET) for _ in range(6)))
    return folio, now.isoformat(timespec="seconds")


@app.get("/health")
@app.get("/api/health")
def health() -> Dict[str, Any]:
    ready = predictor.model_ready()
    return {
        "status": "ok",
        "stage": "prediction" if ready else "validation_only",
        "model_ready": ready,
        "model": predictor.model_info() if ready else None,
        "model_error": predictor.model_error(),
        "catalog_version": catalog.load_catalog()["version"],
    }


@app.get("/api/v1/survey-schema")
def survey_schema() -> Dict[str, Any]:
    return catalog.load_catalog()


@app.post("/api/v1/surveys/validate", response_model=ValidationReceipt, responses={422: {"model": ErrorResponse}})
def validate_survey(answers: SurveyAnswers):
    """Etapa 1: solo valida y resume (útil si el modelo no está disponible)."""
    data, errors = validate_and_normalize(answers)
    if errors:
        return _invalid(errors)
    folio, ts = _folio()
    return ValidationReceipt(
        receipt_id=folio,
        received_at=ts,
        message="Encuesta recibida y validada.",
        summary=build_summary(data),
        answers_normalized=data,
    )


@app.post(
    "/api/v1/predict",
    response_model=PredictionReceipt,
    responses={422: {"model": ErrorResponse}, 503: {"description": "Modelo no disponible"}},
)
def predict_household(answers: SurveyAnswers):
    """Etapa 2: valida las respuestas y estima la probabilidad de pobreza monetaria del hogar."""
    data, errors = validate_and_normalize(answers)
    if errors:
        return _invalid(errors)
    if not predictor.model_ready():
        return JSONResponse(
            status_code=503,
            content={"status": "unavailable", "message": "El modelo no está disponible en este momento.",
                     "detail": predictor.model_error()},
        )
    folio, ts = _folio()
    return PredictionReceipt(
        receipt_id=folio,
        received_at=ts,
        message="Estimación calculada con el modelo del proyecto. Las respuestas no se guardaron.",
        summary=build_summary(data),
        answers_normalized=data,
        prediction=predictor.predict(data),
    )
