"""Carga del catálogo único de la encuesta (app/shared/survey_catalog.json)."""
from __future__ import annotations

import json
import os
from functools import lru_cache
from pathlib import Path
from typing import Any, Dict


def _catalog_path() -> Path:
    env = os.getenv("SURVEY_CATALOG_PATH")
    if env:
        return Path(env)
    here = Path(__file__).resolve()
    # Repositorio: app/backend/api/catalog.py -> app/shared | Contenedor: /srv/api/catalog.py -> /srv/shared
    for base in (here.parents[2], here.parents[1]):
        candidate = base / "shared" / "survey_catalog.json"
        if candidate.exists():
            return candidate
    raise FileNotFoundError("No se encontró shared/survey_catalog.json (defina SURVEY_CATALOG_PATH).")


@lru_cache(maxsize=1)
def load_catalog() -> Dict[str, Any]:
    with _catalog_path().open(encoding="utf-8") as fh:
        return json.load(fh)


def field(name: str) -> Dict[str, Any]:
    return load_catalog()["fields"][name]


def options(name: str) -> list[Dict[str, Any]]:
    spec = field(name)
    if "options_from" in spec:
        return field(spec["options_from"])["options"]
    return spec.get("options", [])


def allowed_values(name: str) -> set:
    return {opt["value"] for opt in options(name)}


def label_for(name: str, value: Any) -> str:
    for opt in options(name):
        if opt["value"] == value:
            return opt["label"]
    return str(value)


def bounds(name: str) -> tuple[int, int]:
    spec = field(name)
    return int(spec["min"]), int(spec["max"])
