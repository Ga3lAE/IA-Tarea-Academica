"""Etapa 2: estimación con el modelo entrenado del proyecto (`models/winner_bundle.joblib`).

No duplica lógica del entrenamiento: reutiliza `predict_single_household` de `src/inference.py`
(la misma función de la encuesta por consola). Este módulo solo localiza el artefacto, lo carga una
vez y traduce las contribuciones TreeSHAP del explicador a frases legibles para el ciudadano.
"""
from __future__ import annotations

import math
import os
import sys
import threading
from pathlib import Path
from typing import Any, Dict, List, Optional

from . import catalog

_HERE = Path(__file__).resolve()
# Repositorio: app/backend/api/predictor.py -> raíz = parents[3] | Contenedor: /srv/api/predictor.py -> /srv
_BASES = [_HERE.parents[3], _HERE.parents[1]] if len(_HERE.parents) > 3 else [_HERE.parents[1]]

_lock = threading.Lock()
_state: Dict[str, Any] = {"bundle": None, "error": None, "predict": None}

MIN_EFECTO = 0.05
VIVIENDA_SIN_FICHA = ("tipo_vivienda", "material_pared", "material_piso")
CATEGORICAS = {
    "tipo_vivienda", "material_pared", "material_piso", "tenencia_vivienda", "fuente_agua",
    "agua_todos_los_dias", "conexion_bano", "combustible_cocina", "tiene_internet", "jefe_mujer",
    "jefe_ocupado", "jefe_cat_ocupacional", "jefe_empresa_ruc", "jefe_sin_pension", "educ_jefe", "educ_max_hogar",
}
ETIQUETAS = {
    "tipo_vivienda": "Tipo de vivienda",
    "material_pared": "Paredes",
    "material_piso": "Piso",
    "total_habitaciones": "Habitaciones",
    "total_dormitorios": "Dormitorios",
    "personas_por_hab": "Personas por habitación",
    "tenencia_vivienda": "Tenencia de la vivienda",
    "fuente_agua": "Agua",
    "agua_todos_los_dias": "Frecuencia del agua",
    "conexion_bano": "Baño",
    "combustible_cocina": "Cocina con",
    "tiene_internet": "Internet",
    "n_miembros": "Integrantes del hogar",
    "n_ninos_0_5": "Niñas y niños de 0 a 5 años",
    "n_menores_14": "Menores de 14 años",
    "n_mayores_65": "Personas de 65 años a más",
    "tasa_dependencia": "Dependientes por persona de 14 a 64 años",
    "jefe_edad": "Edad de la jefa o jefe",
    "jefe_mujer": "Jefatura del hogar",
    "educ_jefe": "Estudios de la jefa o jefe",
    "educ_max_hogar": "Nivel de estudios más alto del hogar",
    "n_ocupados": "Personas que trabajan",
    "ocupados_por_miembro": "Integrantes que trabajan",
    "jefe_horas_semanales": "Horas de trabajo de la jefa o jefe",
    "jefe_ocupado": "La jefa o jefe trabajó",
    "jefe_cat_ocupacional": "Ocupación de la jefa o jefe",
    "jefe_empresa_ruc": "Registro del trabajo",
    "jefe_sin_pension": "Pensiones de la jefa o jefe",
}


def _find(rel: str) -> Optional[Path]:
    for base in _BASES:
        p = base / rel
        if p.exists():
            return p
    return None


def bundle_path() -> Optional[Path]:
    env = os.getenv("MODEL_BUNDLE_PATH")
    return Path(env) if env else _find("models/winner_bundle.joblib")


def load_model() -> None:
    """Carga el artefacto una sola vez (al iniciar la API). Si falla, la API sigue validando."""
    with _lock:
        if _state["bundle"] is not None:
            return
        try:
            src_dir = _find("src/inference.py")
            if src_dir is None:
                raise FileNotFoundError("No se encontró src/inference.py (necesario para usar el modelo).")
            root = str(src_dir.parents[1])
            if root not in sys.path:
                sys.path.insert(0, root)
            from src.inference import load_deployment_bundle, predict_single_household  # noqa: E402

            path = bundle_path()
            if path is None or not path.exists():
                raise FileNotFoundError("No se encontró models/winner_bundle.joblib.")
            _state["bundle"] = load_deployment_bundle(path)
            _state["predict"] = predict_single_household
            _state["error"] = None
        except Exception as exc:  # pragma: no cover - se informa en /health
            _state["error"] = f"{type(exc).__name__}: {exc}"


def model_ready() -> bool:
    return _state["bundle"] is not None


def model_error() -> Optional[str]:
    return _state["error"]


def model_info() -> Dict[str, Any]:
    b = _state["bundle"]
    if b is None:
        return {}
    audit = (b.get("metrics_audit_records") or [{}])[0]
    return {
        "nombre": b.get("winner_name"),
        "explicador": b.get("explainer_name"),
        "hogares_entrenamiento": int(b.get("n_unique_households", 0)),
        "anios": list(b.get("train_years", [])),
        "creado": str(b.get("created_at", "")),
        "pr_auc_oof": audit.get("PR_AUC_OOF"),
        "roc_auc_oof": audit.get("ROC_AUC_OOF"),
        "umbral_riesgo": float(b["tau_rec70"]),
        "umbral_prioridad": float(b["cutoff_b20"]),
    }


# ----------------------------------------------------------------------------- explicación legible

def _fmt_num(x: float, dec: int = 0) -> str:
    return f"{x:.{dec}f}".replace(".", ",") if dec else str(int(round(x)))


def _valor(var: str, value: Any, answers: Dict[str, Any]) -> str:
    if value is None or (isinstance(value, float) and math.isnan(value)):
        if var == "agua_todos_los_dias":
            return "No aplica (sin red pública ni pilón)"
        if var == "combustible_cocina":
            return "No cocinan en casa"
        return "Sin dato"
    v = float(value)
    if var in CATEGORICAS:
        if var in ("jefe_cat_ocupacional", "jefe_empresa_ruc") and v == 0:
            if answers.get("jefe_ocupado") != 1:
                return "No aplica (no trabajó)"
            if var == "jefe_empresa_ruc" and answers.get("jefe_cat_ocupacional") == 6:
                return "No aplica (trabajador del hogar)"
        if var == "jefe_mujer":
            return "Mujer" if v == 1 else "Hombre"
        if var == "jefe_ocupado":
            return "Sí" if v == 1 else "No"
        return catalog.label_for(var, int(v))
    if var == "ocupados_por_miembro":
        return f"{round(v * 100)} %"
    if var == "personas_por_hab" and answers.get("es_hogar_secundario"):
        return f"{_fmt_num(v, 1)} (estimado)"
    if var in ("personas_por_hab", "tasa_dependencia"):
        return _fmt_num(v, 1)
    if var in ("total_habitaciones", "total_dormitorios") and answers.get("es_hogar_secundario"):
        return f"{_fmt_num(v)} (estimado con la mediana de la zona)"
    if var == "jefe_edad":
        return f"{_fmt_num(v)} años"
    if var == "jefe_horas_semanales":
        return f"{_fmt_num(v)} horas"
    return _fmt_num(v)


def _factores(contrib_df, answers: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Convierte las contribuciones (log-odds) de las 28 variables en factores legibles.

    En hogares que comparten vivienda, las variables de vivienda sin ficha propia se agrupan en un
    solo factor para no mostrar "Sin dato" tres veces.
    """
    items: List[Dict[str, Any]] = []
    sin_ficha = 0.0
    for row in contrib_df.itertuples(index=False):
        var, val, c = row.Variable, row.Valor_Input, float(row.Contribucion_LogOdds)
        if answers.get("es_hogar_secundario") and var in VIVIENDA_SIN_FICHA:
            sin_ficha += c
            continue
        items.append({"variable": var, "etiqueta": ETIQUETAS.get(var, var), "valor": _valor(var, val, answers),
                      "contribucion": round(c, 4)})
    if answers.get("es_hogar_secundario"):
        items.append({"variable": "vivienda_compartida", "etiqueta": "Vivienda",
                      "valor": "Comparte la vivienda con otro hogar (sin datos propios de la construcción)",
                      "contribucion": round(sin_ficha, 4)})
    return items


def predict(answers: Dict[str, Any], top_k: int = 4) -> Dict[str, Any]:
    """Estima la probabilidad de pobreza monetaria del hogar a partir de las respuestas normalizadas."""
    if not model_ready():
        raise RuntimeError(model_error() or "Modelo no disponible.")
    b = _state["bundle"]
    res = _state["predict"](b, answers, top_k_drivers=28)
    prob = float(res["prob_pobreza"])
    tau, cut = float(b["tau_rec70"]), float(b["cutoff_b20"])
    nivel = "alto" if prob >= cut else ("medio" if prob >= tau else "bajo")

    factores = _factores(res["contribuciones_28"], answers)
    # Solo factores con efecto apreciable (|contribución| >= 0.05 log-odds) para no mostrar ruido.
    riesgo = sorted((f for f in factores if f["contribucion"] >= MIN_EFECTO), key=lambda f: -f["contribucion"])[:top_k]
    proteccion = sorted((f for f in factores if f["contribucion"] <= -MIN_EFECTO), key=lambda f: f["contribucion"])[:top_k]
    return {
        "probabilidad": round(prob, 4),
        "percentil": round(float(res["percentil_riesgo_lima"]), 1),
        "nivel": nivel,
        "en_riesgo": bool(res["en_riesgo_tau"]),
        "prioritario_top20": bool(res["prioritario_top20"]),
        "umbral_riesgo": round(tau, 4),
        "umbral_prioridad": round(cut, 4),
        "probabilidad_explicador": round(float(res["prob_gbdt"]), 4),
        "factores_riesgo": riesgo,
        "factores_proteccion": proteccion,
        "modelo": model_info(),
    }
