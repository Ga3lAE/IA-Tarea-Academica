"""API de la encuesta web — Etapa 1 (recepción y validación, sin persistencia ni modelo)."""
from __future__ import annotations

import secrets
from datetime import datetime, timezone
from typing import Any, Dict

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from . import catalog
from .rules import validate_and_normalize
from .schemas import ErrorResponse, FieldError, SurveyAnswers, ValidationReceipt
from .summary import build_summary

STAGE = "validation_only"
_FOLIO_ALPHABET = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"

app = FastAPI(
    title="Encuesta de Condiciones de Vida del Hogar — API",
    version=catalog.load_catalog()["version"],
    docs_url="/api/docs",
    openapi_url="/api/openapi.json",
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


@app.get("/health")
@app.get("/api/health")
def health() -> Dict[str, Any]:
    return {"status": "ok", "stage": STAGE, "model_ready": False, "catalog_version": catalog.load_catalog()["version"]}


@app.get("/api/v1/survey-schema")
def survey_schema() -> Dict[str, Any]:
    return catalog.load_catalog()


@app.post(
    "/api/v1/surveys/validate",
    response_model=ValidationReceipt,
    responses={422: {"model": ErrorResponse}},
)
def validate_survey(answers: SurveyAnswers):
    data, errors = validate_and_normalize(answers)
    if errors:
        body = ErrorResponse(errors=[FieldError(field=f, message=m) for f, m in errors])
        return JSONResponse(status_code=422, content=body.model_dump())

    now = datetime.now(timezone.utc)
    folio = "ENC-{}-{}".format(now.year, "".join(secrets.choice(_FOLIO_ALPHABET) for _ in range(6)))
    return ValidationReceipt(
        receipt_id=folio,
        received_at=now.isoformat(timespec="seconds"),
        message="Encuesta recibida y validada. El análisis del modelo se integrará en la siguiente etapa.",
        summary=build_summary(data),
        answers_normalized=data,
    )
