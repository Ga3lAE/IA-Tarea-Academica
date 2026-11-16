"""Pruebas de la Etapa 2: estimación autocontenida con backend/models/winner_bundle.joblib."""
import sys

import pytest
from fastapi.testclient import TestClient

from api import predictor
from api.inference import load_deployment_bundle
from api.main import app

predictor.load_model()

client = TestClient(app)
URL = "/api/v1/predict"

# Valores publicados en el log 2026-11-15_19-18 (src/encuesta_pobreza.py --preset all, mismo .joblib)
ESPERADO = {
    "vulnerable_hacinado": (0.9144, 100.0),
    "secundario_sin_m01": (0.5952, 92.1),
    "formal_estable": (0.0417, 4.8),
}

# Réplica exacta de los 3 perfiles de referencia para probar la API sin importar src/.
PRESET_HOUSEHOLDS = {
    "vulnerable_hacinado": {
        "ubigeo": "150132",
        "es_hogar_secundario": False,
        "tipo_vivienda": 6,
        "material_pared": 8,
        "material_piso": 6,
        "total_habitaciones": 2,
        "total_dormitorios": 1,
        "tenencia_vivienda": 3,
        "fuente_agua": 4,
        "agua_todos_los_dias": None,
        "conexion_bano": 5,
        "combustible_cocina": 2,
        "tiene_internet": 0,
        "n_miembros": 6,
        "n_ninos_0_5": 2,
        "n_menores_14": 3,
        "n_mayores_65": 0,
        "jefe_edad": 36,
        "jefe_mujer": 1,
        "educ_jefe": 4,
        "educ_max_hogar": 5,
        "n_ocupados": 1,
        "jefe_ocupado": 1,
        "jefe_horas_semanales": 48,
        "jefe_cat_ocupacional": 2,
        "jefe_empresa_ruc": 3,
        "jefe_sin_pension": 1,
    },
    "secundario_sin_m01": {
        "ubigeo": "150108",
        "es_hogar_secundario": True,
        "tenencia_vivienda": 6,
        "fuente_agua": 1,
        "agua_todos_los_dias": 1,
        "conexion_bano": 1,
        "combustible_cocina": 2,
        "tiene_internet": 1,
        "n_miembros": 4,
        "n_ninos_0_5": 1,
        "n_menores_14": 2,
        "n_mayores_65": 0,
        "jefe_edad": 29,
        "jefe_mujer": 0,
        "educ_jefe": 6,
        "educ_max_hogar": 6,
        "n_ocupados": 1,
        "jefe_ocupado": 1,
        "jefe_horas_semanales": 45,
        "jefe_cat_ocupacional": 4,
        "jefe_empresa_ruc": 3,
        "jefe_sin_pension": 1,
    },
    "formal_estable": {
        "ubigeo": "150140",
        "es_hogar_secundario": False,
        "tipo_vivienda": 2,
        "material_pared": 1,
        "material_piso": 1,
        "total_habitaciones": 4,
        "total_dormitorios": 2,
        "tenencia_vivienda": 4,
        "fuente_agua": 1,
        "agua_todos_los_dias": 1,
        "conexion_bano": 1,
        "combustible_cocina": 3,
        "tiene_internet": 1,
        "n_miembros": 3,
        "n_ninos_0_5": 0,
        "n_menores_14": 1,
        "n_mayores_65": 0,
        "jefe_edad": 42,
        "jefe_mujer": 0,
        "educ_jefe": 10,
        "educ_max_hogar": 11,
        "n_ocupados": 2,
        "jefe_ocupado": 1,
        "jefe_horas_semanales": 44,
        "jefe_cat_ocupacional": 3,
        "jefe_empresa_ruc": 1,
        "jefe_sin_pension": 0,
    },
}


def _preset_payload(name):
    return dict(PRESET_HOUSEHOLDS[name])


@pytest.mark.parametrize("name", list(ESPERADO))
def test_web_y_consola_dan_la_misma_estimacion(name):
    """El formulario web (POST /api/v1/predict) reproduce exactamente la encuesta por consola."""
    r = client.post(URL, json=_preset_payload(name))
    assert r.status_code == 200, r.text
    pred = r.json()["prediction"]
    prob, pct = ESPERADO[name]
    assert pred["probabilidad"] == pytest.approx(prob, abs=1e-4)
    assert pred["percentil"] == pytest.approx(pct, abs=0.1)


def test_niveles_y_umbrales():
    alto = client.post(URL, json=_preset_payload("vulnerable_hacinado")).json()["prediction"]
    bajo = client.post(URL, json=_preset_payload("formal_estable")).json()["prediction"]
    assert alto["nivel"] == "alto" and alto["prioritario_top20"] and alto["en_riesgo"]
    assert bajo["nivel"] == "bajo" and not bajo["en_riesgo"]
    assert 0 < alto["umbral_riesgo"] < alto["umbral_prioridad"] < 1
    assert alto["modelo"]["hogares_entrenamiento"] == 7289


def test_factores_legibles():
    for name in ESPERADO:
        pred = client.post(URL, json=_preset_payload(name)).json()["prediction"]
        factores = pred["factores_riesgo"] + pred["factores_proteccion"]
        assert factores, name
        assert all(abs(f["contribucion"]) >= 0.05 for f in factores)
        for f in factores:
            assert "nan" not in f["valor"].lower() and f["valor"] != "Sin dato", f
            assert f["etiqueta"] != f["variable"], f
        assert all(f["contribucion"] > 0 for f in pred["factores_riesgo"])
        assert all(f["contribucion"] < 0 for f in pred["factores_proteccion"])


def test_hogar_secundario_agrupa_vivienda_sin_ficha():
    pred = client.post(URL, json=_preset_payload("secundario_sin_m01")).json()["prediction"]
    variables = {f["variable"] for f in pred["factores_riesgo"] + pred["factores_proteccion"]}
    assert not variables & {"tipo_vivienda", "material_pared", "material_piso"}
    assert "vivienda_compartida" in variables


def test_predict_valida_antes_de_estimar():
    p = _preset_payload("formal_estable")
    p["total_dormitorios"] = 9
    r = client.post(URL, json=p)
    assert r.status_code == 422
    assert r.json()["errors"][0]["field"] == "total_dormitorios"


def test_health_informa_modelo():
    h = client.get("/health").json()
    assert h["model_ready"] is True and h["stage"] == "prediction"
    assert h["model"]["nombre"] == "Stacking_Ensemble"


def test_carga_sin_paquete_src_externo(monkeypatch):
    """El backend deserializa winner_bundle.joblib sin depender de src/ fuera de app/."""
    backend_root = str(predictor.bundle_path().parents[1])
    monkeypatch.delitem(sys.modules, "src", raising=False)
    monkeypatch.delitem(sys.modules, "src.preprocessing", raising=False)
    monkeypatch.setattr(sys, "path", [backend_root])
    bundle = load_deployment_bundle(predictor.bundle_path())
    assert "pipe_stacking" in bundle and "pipe_gbdt" in bundle
