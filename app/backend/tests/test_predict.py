"""Pruebas de la Etapa 2: estimación con models/winner_bundle.joblib a través de la API."""
import pytest
from fastapi.testclient import TestClient

from api import predictor
from api.main import app

predictor.load_model()
pytestmark = pytest.mark.skipif(not predictor.model_ready(), reason=f"Modelo no disponible: {predictor.model_error()}")

client = TestClient(app)
URL = "/api/v1/predict"

# Valores publicados en el log 2026-11-15_19-18 (src/encuesta_pobreza.py --preset all, mismo .joblib)
ESPERADO = {
    "vulnerable_hacinado": (0.9144, 100.0),
    "secundario_sin_m01": (0.5952, 92.1),
    "formal_estable": (0.0417, 4.8),
}


def _preset_payload(name):
    from src.inference import PRESET_HOUSEHOLDS
    p = {k: v for k, v in PRESET_HOUSEHOLDS[name].items() if k != "descripcion"}
    if p.get("jefe_horas_semanales") is not None:
        p["jefe_horas_semanales"] = int(p["jefe_horas_semanales"])
    return p


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
