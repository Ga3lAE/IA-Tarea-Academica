"""Reglas de salto de la ENAHO y coherencia entre preguntas.

`validate_and_normalize` devuelve el diccionario normalizado que en la Etapa 2 se
entregará tal cual a `build_household_dataframe_from_answers` (src/inference.py),
o la lista de errores por campo si las respuestas no son coherentes.
"""
from __future__ import annotations

from typing import Any, Dict, List, Tuple

from . import catalog
from .schemas import SurveyAnswers

VIVIENDA_FIELDS = ("tipo_vivienda", "material_pared", "material_piso", "total_habitaciones", "total_dormitorios")
EMPLEO_JEFE_FIELDS = ("jefe_horas_semanales", "jefe_cat_ocupacional", "jefe_empresa_ruc")
CHOICE_FIELDS = (
    "tipo_vivienda", "material_pared", "material_piso", "tenencia_vivienda", "fuente_agua",
    "agua_todos_los_dias", "conexion_bano", "combustible_cocina", "tiene_internet", "jefe_mujer",
    "educ_jefe", "educ_max_hogar", "jefe_ocupado", "jefe_cat_ocupacional", "jefe_empresa_ruc",
    "jefe_sin_pension",
)
AGUA_CON_FRECUENCIA = {1, 2, 3}

Errors = List[Tuple[str, str]]


def _check_codes(data: Dict[str, Any], errors: Errors) -> None:
    if data["ubigeo"] not in catalog.allowed_values("ubigeo"):
        errors.append(("ubigeo", "Elige un distrito de la lista."))
    for name in CHOICE_FIELDS:
        value = data.get(name)
        if value is not None and value not in catalog.allowed_values(name):
            errors.append((name, "Elige una de las opciones disponibles."))


def validate_and_normalize(answers: SurveyAnswers) -> Tuple[Dict[str, Any], Errors]:
    data = answers.model_dump()
    errors: Errors = []
    _check_codes(data, errors)

    n = data["n_miembros"]

    # Regla 1: hogar secundario -> sin ficha de vivienda; hogar principal -> vivienda completa.
    if data["es_hogar_secundario"]:
        for name in VIVIENDA_FIELDS:
            data[name] = None
    else:
        for name in ("tipo_vivienda", "material_pared", "material_piso", "total_habitaciones"):
            if data[name] is None:
                errors.append((name, "Esta pregunta es obligatoria para el hogar principal."))
        if data["total_dormitorios"] is None:
            errors.append(("total_dormitorios", "Indica cuántas habitaciones se usan para dormir."))
        elif data["total_habitaciones"] is not None and data["total_dormitorios"] > data["total_habitaciones"]:
            errors.append(("total_dormitorios", "No puede haber más dormitorios que habitaciones."))

    # Regla 2: la frecuencia del agua solo aplica a red pública o pilón.
    if data["fuente_agua"] in AGUA_CON_FRECUENCIA:
        if data["agua_todos_los_dias"] is None:
            errors.append(("agua_todos_los_dias", "Indica si tienen agua todos los días."))
    else:
        data["agua_todos_los_dias"] = None

    # Regla 3: composición por edades sin doble conteo.
    ninos, menores, mayores = data["n_ninos_0_5"], data["n_menores_14"], data["n_mayores_65"]
    if ninos > menores:
        errors.append(("n_ninos_0_5", "Los niños de 0 a 5 años también son menores de 14."))
    if menores + mayores > n:
        errors.append(("n_menores_14", f"Menores de 14 y mayores de 65 suman más que las {n} personas del hogar."))
    elif data["jefe_edad"] >= 65 and mayores < 1:
        errors.append(("n_mayores_65", "La jefa o jefe tiene 65 años o más: cuenta al menos una persona de ese grupo."))
    elif data["jefe_edad"] < 65 and n - menores - mayores < 1:
        errors.append(("n_menores_14", "Falta contar a la jefa o jefe del hogar entre las personas de 14 a 64 años."))

    # Regla 4: el nivel educativo máximo del hogar no puede ser menor que el del jefe.
    if data["educ_max_hogar"] < data["educ_jefe"]:
        errors.append(("educ_max_hogar", "El nivel más alto del hogar no puede ser menor que el de la jefa o jefe."))
    elif n == 1 and data["educ_max_hogar"] != data["educ_jefe"]:
        errors.append(("educ_max_hogar", "En un hogar de una persona, el nivel más alto es el de la jefa o jefe."))

    # Regla 5: datos laborales del jefe solo si trabajó.
    if data["jefe_ocupado"] == 1:
        for name, msg in (
            ("jefe_horas_semanales", "Indica las horas trabajadas la semana pasada."),
            ("jefe_cat_ocupacional", "Indica cómo se desempeña en su trabajo principal."),
            ("jefe_empresa_ruc", "Indica cómo está registrado el lugar donde trabaja."),
        ):
            if data[name] is None:
                errors.append((name, msg))
    else:
        for name in EMPLEO_JEFE_FIELDS:
            data[name] = None

    # Regla 6: ocupados del hogar (el empleo de la ENAHO se mide en personas de 14 años a más).
    en_edad_trabajar = n - menores
    max_ocupados = en_edad_trabajar - (0 if data["jefe_ocupado"] == 1 else 1)
    if data["jefe_ocupado"] == 1 and data["n_ocupados"] < 1:
        errors.append(("n_ocupados", "La jefa o jefe trabajó: cuenta al menos una persona ocupada."))
    elif data["n_ocupados"] > max(0, max_ocupados):
        errors.append(("n_ocupados", f"Como máximo pueden ser {max(0, max_ocupados)} según las edades y la situación de la jefa o jefe."))

    return data, errors
