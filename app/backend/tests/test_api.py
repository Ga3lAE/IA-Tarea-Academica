"""Pruebas de la API de validación (Etapa 1)."""
import re
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from api.main import app

client = TestClient(app)
URL = "/api/v1/surveys/validate"

PRINCIPAL = {
    "es_hogar_secundario": False, "ubigeo": "150132", "n_miembros": 4,
    "tipo_vivienda": 1, "material_pared": 1, "material_piso": 5,
    "total_habitaciones": 3, "total_dormitorios": 2,
    "tenencia_vivienda": 2, "fuente_agua": 1, "agua_todos_los_dias": 1,
    "conexion_bano": 1, "combustible_cocina": 2, "tiene_internet": 1,
    "jefe_mujer": 1, "jefe_edad": 42, "educ_jefe": 6, "educ_max_hogar": 8,
    "n_ninos_0_5": 1, "n_menores_14": 2, "n_mayores_65": 0,
    "jefe_ocupado": 1, "jefe_horas_semanales": 48, "jefe_cat_ocupacional": 3,
    "jefe_empresa_ruc": 1, "jefe_sin_pension": 0, "n_ocupados": 2,
}


def post(**changes):
    payload = {**PRINCIPAL, **changes}
    return client.post(URL, json=payload)


def fields(resp):
    return {e["field"] for e in resp.json()["errors"]}


def test_health_and_schema():
    assert client.get("/health").json()["status"] == "ok"
    schema = client.get("/api/v1/survey-schema").json()
    assert "n_miembros" in schema["fields"]


def test_hogar_principal_valido():
    r = post()
    assert r.status_code == 200, r.text
    body = r.json()
    assert re.fullmatch(r"ENC-\d{4}-[A-Z2-9]{6}", body["receipt_id"])
    assert body["status"] == "validated_pending_model"
    assert [b["block"] for b in body["summary"]][0] == "Tu hogar"


def test_hogar_secundario_anula_vivienda():
    r = post(es_hogar_secundario=True, tipo_vivienda=None, material_pared=None, material_piso=None,
             total_habitaciones=None, total_dormitorios=None, tenencia_vivienda=6)
    assert r.status_code == 200, r.text
    norm = r.json()["answers_normalized"]
    assert all(norm[k] is None for k in ("tipo_vivienda", "material_pared", "material_piso",
                                          "total_habitaciones", "total_dormitorios"))
    assert all(b["block"] != "La vivienda" for b in r.json()["summary"])


def test_hogar_principal_exige_vivienda():
    r = post(tipo_vivienda=None, total_habitaciones=None)
    assert r.status_code == 422
    assert {"tipo_vivienda", "total_habitaciones"} <= fields(r)


def test_dormitorios_no_superan_habitaciones():
    assert fields(post(total_habitaciones=2, total_dormitorios=3)) == {"total_dormitorios"}


def test_frecuencia_agua_se_limpia_si_no_es_red_publica():
    r = post(fuente_agua=4, agua_todos_los_dias=2)
    assert r.status_code == 200
    assert r.json()["answers_normalized"]["agua_todos_los_dias"] is None


def test_frecuencia_agua_obligatoria_con_red_publica():
    assert fields(post(fuente_agua=1, agua_todos_los_dias=None)) == {"agua_todos_los_dias"}


@pytest.mark.parametrize("changes, campo", [
    ({"n_ninos_0_5": 3, "n_menores_14": 2}, "n_ninos_0_5"),
    ({"n_menores_14": 3, "n_mayores_65": 2}, "n_menores_14"),
    ({"n_menores_14": 4, "n_ninos_0_5": 1, "n_ocupados": 0, "jefe_ocupado": 0,
      "jefe_horas_semanales": None, "jefe_cat_ocupacional": None, "jefe_empresa_ruc": None}, "n_menores_14"),
    ({"jefe_edad": 70, "n_mayores_65": 0}, "n_mayores_65"),
    ({"educ_max_hogar": 4}, "educ_max_hogar"),
    ({"jefe_horas_semanales": None}, "jefe_horas_semanales"),
    ({"n_ocupados": 0}, "n_ocupados"),
    ({"n_ocupados": 3}, "n_ocupados"),
    ({"tipo_vivienda": 42}, "tipo_vivienda"),
    ({"ubigeo": "999999"}, "ubigeo"),
])
def test_reglas_de_coherencia(changes, campo):
    r = post(**changes)
    assert r.status_code == 422
    assert campo in fields(r)


def test_unipersonal_educacion_igual_a_jefe():
    r = post(n_miembros=1, n_ninos_0_5=0, n_menores_14=0, n_ocupados=1, educ_jefe=6, educ_max_hogar=8)
    assert fields(r) == {"educ_max_hogar"}


def test_jefe_no_ocupado_normaliza_empleo():
    r = post(jefe_ocupado=0, n_ocupados=1, jefe_horas_semanales=40, jefe_cat_ocupacional=3, jefe_empresa_ruc=1)
    assert r.status_code == 200, r.text
    norm = r.json()["answers_normalized"]
    assert norm["jefe_horas_semanales"] is None and norm["jefe_cat_ocupacional"] is None


def test_trabajador_del_hogar_sin_registro():
    """Como en la ENAHO (P510A1), no se pregunta el RUC a trabajadores del hogar: se envía 0."""
    r = post(jefe_cat_ocupacional=6, jefe_empresa_ruc=None)
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["answers_normalized"]["jefe_empresa_ruc"] == 0
    empleo = body["summary"][-1]["items"]
    assert all(it["label"] != "Registro del trabajo" for it in empleo)


def test_sector_publico_y_cero_horas():
    """Empleados públicos usan el código 0 (sin P510A1) y un ocupado ausente puede tener 0 horas."""
    r = post(jefe_empresa_ruc=0, jefe_horas_semanales=0)
    assert r.status_code == 200, r.text
    assert r.json()["answers_normalized"]["jefe_empresa_ruc"] == 0


def test_errores_de_tipo_son_amigables():
    payload = {**PRINCIPAL, "n_miembros": "cuatro", "extra": 1}
    payload.pop("jefe_edad")
    r = client.post(URL, json=payload)
    assert r.status_code == 422
    msgs = {e["field"]: e["message"] for e in r.json()["errors"]}
    assert msgs["jefe_edad"] == "Esta pregunta es obligatoria."
    assert "n_miembros" in msgs and "extra" in msgs


def test_rango_amigable():
    r = post(n_miembros=25)
    assert r.json()["errors"][0]["message"] == "Ingresa un valor entre 1 y 20."


def test_contrato_con_el_modelo():
    """Toda respuesta que lee build_household_dataframe_from_answers existe en la salida normalizada."""
    src = Path(__file__).resolve().parents[1] / "api" / "inference.py"
    assert src.exists(), f"No existe {src}"
    text = src.read_text(encoding="utf-8")
    start = text.index("def build_household_dataframe_from_answers")
    body = text[start:text.index("\ndef ", start + 10)]
    usadas = set(re.findall(r'answers(?:\.get\(|\[)"(\w+)"', body)) - {"conglomerado"}
    norm = post().json()["answers_normalized"]
    assert usadas <= set(norm), usadas - set(norm)
