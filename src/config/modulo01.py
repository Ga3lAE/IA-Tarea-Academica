"""
Configuration and metadata schema for ENAHO Modulo 01 (Vivienda y Hogar).
Defines exact categorical mappings, boolean translations, and validation constraints.
"""
from typing import Dict, Any, List

# Column renaming map: technical INEI name -> standardized snake_case name
COLUMNS_RENAME_MOD01: Dict[str, str] = {
    'CONGLOME': 'conglomerado',
    'VIVIENDA': 'vivienda',
    'HOGAR': 'hogar',
    'UBIGEO': 'ubigeo',
    'RESULT': 'resultado_encuesta',
    'P101': 'tipo_vivienda',
    'P102': 'material_pared_exterior',
    'P103': 'material_piso',
    'P104': 'total_habitaciones',
    'P104A': 'total_dormitorios',
    'P105A': 'tenencia_vivienda',
    'P106A': 'titulo_propiedad',
    'P106B': 'registro_sunarp',
    'P110': 'fuente_agua',
    'P110C': 'agua_todos_los_dias',
    'P111A': 'conexion_bano',
    'P113A': 'combustible_cocina',
    'P1143': 'tiene_tv_cable',
    'P1144': 'tiene_internet',
    'NBI1': 'vivienda_inadecuada',
    'NBI2': 'vivienda_hacinamiento',
    'NBI3': 'vivienda_sin_bano',
    'NBI4': 'nino_sin_educacion',
    'NBI5': 'dependencia_economica'
}

# Physical dwelling columns to inherit from primary household (HOGAR 11)
# to secondary households (HOGAR 22, 33...) within the same dwelling
DWELLING_INHERITANCE_COLUMNS: List[str] = [
    'P101', 'P102', 'P103', 'P104', 'P104A', 'P110', 'P111A'
]

# Real quantitative continuous/count columns in Modulo 01
NUMERIC_COLUMNS_MOD01: List[str] = [
    'total_habitaciones',
    'total_dormitorios'
]

# Categorical mapping dictionaries (all code values, 1-2-3 answers and booleans to string labels)
CATEGORICAL_MAPPINGS_MOD01: Dict[str, Dict[Any, str]] = {
    'tipo_vivienda': {
        1: 'casa_independiente',
        2: 'departamento_edificio',
        3: 'quinta',
        4: 'casa_vecindad_callejon',
        5: 'choza_cabana',
        6: 'vivienda_improvisada',
        7: 'local_no_destinado_habitacion',
        8: 'otro'
    },
    'material_pared_exterior': {
        1: 'ladrillo_bloque_cemento',
        2: 'piedra_sillar_cemento',
        3: 'adobe',
        4: 'tapia',
        5: 'quincha',
        6: 'piedra_barro',
        7: 'madera',
        8: 'triplay_calamina_estera',
        9: 'otro'
    },
    'material_piso': {
        1: 'parquet_madera_pulida',
        2: 'vinilico_similares',
        3: 'loseta_terrazo_ceramico',
        4: 'madera_tablas',
        5: 'cemento',
        6: 'tierra',
        7: 'otro'
    },
    'fuente_agua': {
        1: 'red_interior',
        2: 'red_exterior_edificio',
        3: 'pilon_publico',
        4: 'camion_cisterna',
        5: 'pozo_subterraneo',
        6: 'manantial_puquio',
        7: 'otro',                # INEI: 7 = Otra
        8: 'rio_acequia_laguna'   # INEI: 8 = Río, acequia, lago, laguna
    },
    'conexion_bano': {
        1: 'red_interior',
        2: 'red_exterior_edificio',
        3: 'letrina_ventilada',
        4: 'pozo_septico',
        5: 'pozo_ciego_negro',
        6: 'rio_canal_acequia',
        7: 'otro',
        8: 'sin_bano_campo_abierto',
        9: 'sin_bano_campo_abierto'
    },
    'combustible_cocina': {
        # Códigos según Diccionario ENAHO 2024-2025 (P113A): no existe el código 4
        1: 'electricidad',
        2: 'gas_glp',
        3: 'gas_natural',
        5: 'carbon',
        6: 'lena',
        7: 'otro',
        8: 'no_cocina'
    },
    'tenencia_vivienda': {
        1: 'alquilada',
        2: 'propia_pagada',
        3: 'propia_invasion',
        4: 'propia_plazos',
        5: 'cedida_trabajo',
        6: 'cedida_otro',
        7: 'otro'
    },
    'titulo_propiedad': {
        1: 'si',
        2: 'no',
        3: 'en_tramite'
    },
    'registro_sunarp': {
        1: 'si',
        2: 'no'
    },
    'agua_todos_los_dias': {
        1: 'si',
        2: 'no'
    },
    'tiene_tv_cable': {
        1: 'si',
        0: 'no',
        2: 'no'
    },
    'tiene_internet': {
        1: 'si',
        0: 'no',
        2: 'no'
    },
    'vivienda_inadecuada': {
        0: 'adecuada',
        1: 'inadecuada'
    },
    'vivienda_hacinamiento': {
        0: 'no_hacinada',
        1: 'hacinada'
    },
    'vivienda_sin_bano': {
        0: 'con_bano',
        1: 'sin_bano'
    },
    'nino_sin_educacion': {
        0: 'asiste',
        1: 'no_asiste'
    },
    'dependencia_economica': {
        0: 'baja_dependencia',
        1: 'alta_dependencia'
    }
}

# Default values for skip patterns when survey question was conditionally omitted
SKIP_PATTERN_DEFAULTS: Dict[str, str] = {
    'titulo_propiedad': 'no_aplica',          # When dwelling is rented or ceded
    'registro_sunarp': 'no_aplica',           # When dwelling has no title or is rented
    'agua_todos_los_dias': 'no_aplica_sin_red',# When dwelling has no piped water
    'tiene_tv_cable': 'no',                   # Default absent
    'tiene_internet': 'no'                    # Default absent
}

# Validation constraints
# Departamento de Lima completo + Callao (prefijos UBIGEO '15' y '07')
MIN_EXPECTED_ROWS_LIMA_CALLAO: int = 4000
MAX_EXPECTED_ROWS_LIMA_CALLAO: int = 7500

# Lima Metropolitana y Callao = DOMINIO 8 (prefijos UBIGEO '1501' y '07'): 4,090 (2024) y 4,129 (2025)
MIN_EXPECTED_ROWS_LIMA_METRO: int = 3800
MAX_EXPECTED_ROWS_LIMA_METRO: int = 4600

STRICT_NON_NULL_COLUMNS_MOD01: List[str] = [
    'tipo_vivienda',
    'material_pared_exterior',
    'material_piso',
    'total_habitaciones',
    'total_dormitorios',
    'tenencia_vivienda',
    'titulo_propiedad',
    'registro_sunarp',
    'seguridad_tenencia',
    'fuente_agua',
    'agua_todos_los_dias',
    'conexion_bano',
    'combustible_cocina',
    'tiene_tv_cable',
    'tiene_internet'
]
