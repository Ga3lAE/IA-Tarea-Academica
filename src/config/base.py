"""
Base configuration constants for ENAHO processing.
"""
from typing import List, Tuple, Optional

# Encoding and file reading defaults
DEFAULT_ENCODING: str = "latin-1"
DEFAULT_SEPARATOR: Optional[str] = None  # None = auto-detect (; or ,); can be set to ";" or ","
DEFAULT_OUTPUT_SEPARATOR: str = ","      # Output CSV separator (standard for Spanish Excel / Peru)

# Default geographic filter: Lima (15) and Callao (07)
DEFAULT_UBIGEO_PREFIXES: Tuple[str, ...] = ("07", "15")

# Valid survey interview results (1: Completa, 2: Incompleta con datos suficientes)
VALID_SURVEY_RESULTS: List[int] = [1, 2]

# Standard primary keys
PRIMARY_KEY_HOUSEHOLD: List[str] = ["conglomerado", "vivienda", "hogar"]
PRIMARY_KEY_INDIVIDUAL: List[str] = ["conglomerado", "vivienda", "hogar", "codperso"]
