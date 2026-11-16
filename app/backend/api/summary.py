"""Resumen legible de las respuestas validadas (para el comprobante)."""
from __future__ import annotations

from typing import Any, Dict, List

from . import catalog
from .schemas import SummaryBlock, SummaryItem


def _count(n: int, unit_field: str) -> str:
    singular, plural = catalog.field(unit_field)["unit"]
    return f"{n} {singular if n == 1 else plural}"


def _lbl(name: str, data: Dict[str, Any]) -> str:
    return catalog.label_for(name, data[name])


def build_summary(data: Dict[str, Any]) -> List[SummaryBlock]:
    n = data["n_miembros"]
    hogar = [
        SummaryItem(label="Integrantes", value=_count(n, "n_miembros")),
        SummaryItem(label="Distrito", value=_lbl("ubigeo", data)),
        SummaryItem(
            label="Situación en la vivienda",
            value="Comparte la vivienda con otro hogar" if data["es_hogar_secundario"] else "Hogar principal",
        ),
    ]
    blocks = [SummaryBlock(block="Tu hogar", items=hogar)]

    if not data["es_hogar_secundario"]:
        blocks.append(SummaryBlock(block="La vivienda", items=[
            SummaryItem(label="Tipo", value=_lbl("tipo_vivienda", data)),
            SummaryItem(label="Paredes", value=_lbl("material_pared", data)),
            SummaryItem(label="Piso", value=_lbl("material_piso", data)),
            SummaryItem(
                label="Habitaciones",
                value=f"{_count(data['total_habitaciones'], 'total_habitaciones')}, "
                      f"{_count(data['total_dormitorios'], 'total_dormitorios')}",
            ),
        ]))

    servicios = [
        SummaryItem(label="Tenencia", value=_lbl("tenencia_vivienda", data)),
        SummaryItem(label="Agua", value=_lbl("fuente_agua", data)),
    ]
    if data["agua_todos_los_dias"] is not None:
        servicios.append(SummaryItem(label="Frecuencia del agua", value=_lbl("agua_todos_los_dias", data)))
    servicios += [
        SummaryItem(label="Baño", value=_lbl("conexion_bano", data)),
        SummaryItem(label="Cocina con", value=_lbl("combustible_cocina", data)),
        SummaryItem(label="Internet", value=_lbl("tiene_internet", data)),
    ]
    blocks.append(SummaryBlock(block="Tenencia y servicios", items=servicios))

    adultos = n - data["n_menores_14"] - data["n_mayores_65"]
    blocks.append(SummaryBlock(block="Integrantes y educación", items=[
        SummaryItem(label="Jefatura", value=f"{_lbl('jefe_mujer', data)}, {data['jefe_edad']} años"),
        SummaryItem(label="Estudios de la jefatura", value=_lbl("educ_jefe", data)),
        SummaryItem(label="Nivel más alto del hogar", value=_lbl("educ_max_hogar", data)),
        SummaryItem(
            label="Edades",
            value=f"{data['n_menores_14']} menores de 14 (de ellos {data['n_ninos_0_5']} de 0 a 5), "
                  f"{adultos} de 14 a 64 y {data['n_mayores_65']} de 65 a más",
        ),
    ]))

    empleo = [SummaryItem(label="La jefatura trabajó", value="Sí" if data["jefe_ocupado"] == 1 else "No")]
    if data["jefe_ocupado"] == 1:
        empleo += [
            SummaryItem(label="Horas a la semana", value=_count(data["jefe_horas_semanales"], "jefe_horas_semanales")),
            SummaryItem(label="Se desempeña como", value=_lbl("jefe_cat_ocupacional", data)),
            SummaryItem(label="Registro del trabajo", value=_lbl("jefe_empresa_ruc", data)),
        ]
    empleo += [
        SummaryItem(label="Pensiones", value=_lbl("jefe_sin_pension", data)),
        SummaryItem(label="Personas que trabajan", value=_count(data["n_ocupados"], "n_ocupados")),
    ]
    blocks.append(SummaryBlock(block="Empleo y protección social", items=empleo))
    return blocks
