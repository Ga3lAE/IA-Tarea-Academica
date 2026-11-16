"""Modelos Pydantic de entrada y salida de la API."""
from __future__ import annotations

from typing import Any, Dict, List, Literal, Optional

from pydantic import BaseModel, ConfigDict, Field


class SurveyAnswers(BaseModel):
    """Respuestas crudas de la encuesta (sin ratios ni escalamiento).

    Los rangos simples se validan aquí; los códigos permitidos y las reglas cruzadas
    (saltos de la ENAHO y coherencia entre preguntas) se validan en `rules.py`.
    """

    model_config = ConfigDict(extra="forbid", strict=True)

    # Paso 1: hogar
    es_hogar_secundario: bool
    ubigeo: str = Field(default="__nuevo_distrito__", max_length=20)
    n_miembros: int = Field(ge=1, le=20)

    # Paso 2: vivienda (se omite en hogares secundarios)
    tipo_vivienda: Optional[int] = None
    material_pared: Optional[int] = None
    material_piso: Optional[int] = None
    total_habitaciones: Optional[int] = Field(default=None, ge=1, le=20)
    total_dormitorios: Optional[int] = Field(default=None, ge=0, le=20)

    # Paso 3: tenencia y servicios
    tenencia_vivienda: int
    fuente_agua: int
    agua_todos_los_dias: Optional[int] = None
    conexion_bano: int
    combustible_cocina: int
    tiene_internet: int

    # Paso 4: integrantes y educación
    jefe_mujer: int
    jefe_edad: int = Field(ge=18, le=100)
    educ_jefe: int
    educ_max_hogar: int
    n_ninos_0_5: int = Field(ge=0, le=19)
    n_menores_14: int = Field(ge=0, le=19)
    n_mayores_65: int = Field(ge=0, le=20)

    # Paso 5: empleo y protección social
    jefe_ocupado: int
    jefe_horas_semanales: Optional[int] = Field(default=None, ge=0, le=100)
    jefe_cat_ocupacional: Optional[int] = None
    jefe_empresa_ruc: Optional[int] = None
    jefe_sin_pension: int
    n_ocupados: int = Field(ge=0, le=20)


class FieldError(BaseModel):
    field: str
    message: str


class ErrorResponse(BaseModel):
    status: Literal["invalid"] = "invalid"
    errors: List[FieldError]


class SummaryItem(BaseModel):
    label: str
    value: str


class SummaryBlock(BaseModel):
    block: str
    items: List[SummaryItem]


class Factor(BaseModel):
    variable: str
    etiqueta: str
    valor: str
    contribucion: float


class ModelInfo(BaseModel):
    nombre: Optional[str] = None
    explicador: Optional[str] = None
    hogares_entrenamiento: int = 0
    anios: List[int] = []
    creado: str = ""
    pr_auc_oof: Optional[float] = None
    roc_auc_oof: Optional[float] = None
    umbral_riesgo: Optional[float] = None
    umbral_prioridad: Optional[float] = None


class Prediction(BaseModel):
    probabilidad: float
    percentil: float
    nivel: Literal["alto", "medio", "bajo"]
    en_riesgo: bool
    prioritario_top20: bool
    umbral_riesgo: float
    umbral_prioridad: float
    probabilidad_explicador: float
    factores_riesgo: List[Factor]
    factores_proteccion: List[Factor]
    modelo: ModelInfo


class PredictionReceipt(BaseModel):
    receipt_id: str
    received_at: str
    status: Literal["predicted"] = "predicted"
    message: str
    summary: List[SummaryBlock]
    answers_normalized: Dict[str, Any]
    prediction: Prediction


class ValidationReceipt(BaseModel):
    receipt_id: str
    received_at: str
    status: Literal["validated_pending_model"] = "validated_pending_model"
    message: str
    summary: List[SummaryBlock]
    answers_normalized: Dict[str, Any]
