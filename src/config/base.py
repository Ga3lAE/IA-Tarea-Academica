"""
Base configuration constants for ENAHO processing.
"""
from dataclasses import dataclass, field
from typing import List, Tuple

# Encoding and file reading defaults
DEFAULT_ENCODING = "latin-1"
DEFAULT_SEPARATOR = ";"

# Geographic filter: Lima (15) and Callao (07)
DEFAULT_UBIGEO_PREFIXES: Tuple[str, ...] = ("07", "15")

# Valid survey interview results (1: Completa, 2: Incompleta con datos suficientes)
VALID_SURVEY_RESULTS: List[int] = [1, 2]

# Standard primary keys
PRIMARY_KEY_HOUSEHOLD: List[str] = ["conglomerado", "vivienda", "hogar"]
PRIMARY_KEY_INDIVIDUAL: List[str] = ["conglomerado", "vivienda", "hogar", "codperso"]
