"""
Base configuration constants for ENAHO processing.
"""
from typing import List, Tuple, Optional

# Encoding and file reading defaults
DEFAULT_ENCODING: str = "latin-1"
DEFAULT_SEPARATOR: Optional[str] = None  # None = auto-detect (; or ,); can be set to ";" or ","
DEFAULT_OUTPUT_SEPARATOR: str = ","      # Output CSV separator for Data/processed/

# Default geographic filter: Lima Metropolitana y Callao (ENAHO DOMINIO 8)
# = Provincia de Lima ('1501') + Provincia Constitucional del Callao ('07').
# Use ("07", "15") to include the whole department of Lima (Lima Provincias, other INEI domains).
DEFAULT_UBIGEO_PREFIXES: Tuple[str, ...] = ("07", "1501")

# Valid survey interview results (1: Completa, 2: Incompleta con datos suficientes)
VALID_SURVEY_RESULTS: List[int] = [1, 2]

# Standard primary keys
PRIMARY_KEY_HOUSEHOLD: List[str] = ["conglomerado", "vivienda", "hogar"]
PRIMARY_KEY_INDIVIDUAL: List[str] = ["conglomerado", "vivienda", "hogar", "codperso"]

# Multi-year key: ENAHO has a panel subsample (930 households of DOMINIO 8 repeat in 2024 and 2025)
PRIMARY_KEY_HOUSEHOLD_PANEL: List[str] = ["anio_encuesta", "conglomerado", "vivienda", "hogar"]
