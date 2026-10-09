"""
Concrete processor for ENAHO Modulo 01 (Vivienda y Hogar).
Strictly separates categorical features (booleans, 1-2-3 survey codes) from real numeric variables.
Implements dwelling inheritance, skip-pattern resolution, explicit domain labeling, and validation.
"""
from typing import Optional, Union, Dict, Any, Sequence
from pathlib import Path
import numpy as np
import pandas as pd

from src.core.base_processor import BaseModuleProcessor
from src.core.validators import (
    SchemaValidator,
    RowValidator,
    QualityValidator,
    DataQualityError
)
from src.config.modulo01 import (
    COLUMNS_RENAME_MOD01,
    CATEGORICAL_MAPPINGS_MOD01,
    DWELLING_INHERITANCE_COLUMNS,
    NUMERIC_COLUMNS_MOD01,
    SKIP_PATTERN_DEFAULTS,
    STRICT_NON_NULL_COLUMNS_MOD01,
    MIN_EXPECTED_ROWS_LIMA_CALLAO,
    MAX_EXPECTED_ROWS_LIMA_CALLAO,
    MIN_EXPECTED_ROWS_LIMA_METRO,
    MAX_EXPECTED_ROWS_LIMA_METRO
)
from src.config.base import PRIMARY_KEY_HOUSEHOLD


class Modulo01Processor(BaseModuleProcessor):
    """
    Extends BaseModuleProcessor to handle specific survey logic of Modulo 01.
    """

    def validate_raw_schema(self, df: pd.DataFrame) -> None:
        """Validates that all necessary raw columns exist."""
        required = list(COLUMNS_RENAME_MOD01.keys())
        SchemaValidator.validate_required_columns(df, required)

    def clean_and_impute(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Resolves structural missingness:
        1. Inherits physical dwelling characteristics for secondary households (HOGAR 22, 33...).
        2. Cleans whitespace strings into standardized representations.
        """
        cleaned = df.copy()

        # Clean spaces in dwelling inheritance columns
        for col in DWELLING_INHERITANCE_COLUMNS:
            if col in cleaned.columns:
                cleaned[col] = cleaned[col].astype(str).str.strip().replace({'': np.nan, 'nan': np.nan, 'None': np.nan})
                # Forward/backward fill strictly within the same physical dwelling (CONGLOME, VIVIENDA)
                cleaned[col] = cleaned.groupby(['CONGLOME', 'VIVIENDA'])[col].transform(lambda s: s.ffill().bfill())

        # Clean numeric counts
        for num_col in ['P104', 'P104A']:
            if num_col in cleaned.columns:
                cleaned[num_col] = pd.to_numeric(cleaned[num_col], errors='coerce')
                n_fallback = int((cleaned[num_col].isna() | (cleaned[num_col] <= 0)).sum())
                if n_fallback:
                    self.log(f"{num_col}: {n_fallback} valores nulos o <= 0 reemplazados por 1 (fallback)")
                cleaned[num_col] = cleaned[num_col].fillna(1)
                cleaned[num_col] = cleaned[num_col].apply(lambda x: 1 if x <= 0 else x)

        return cleaned

    def feature_engineering(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Transforms skip patterns and generates high-signal features:
        Consolidates P105A, P106A, and P106B into 'seguridad_tenencia'.
        """
        engineered = df.copy()

        def to_int_or_none(val):
            try:
                if pd.isna(val) or str(val).strip() in ['', 'nan', 'None']:
                    return None
                return int(float(val))
            except (ValueError, TypeError):
                return None

        def map_tenure_security(row) -> str:
            p105 = to_int_or_none(row.get('P105A'))
            p106a = to_int_or_none(row.get('P106A'))
            p106b = to_int_or_none(row.get('P106B'))

            if p105 == 1:
                return 'alquilada'
            elif p105 in [5, 6, 7]:
                return 'cedida_posesion_informal'
            elif p106a == 1 and p106b == 1:
                return 'propia_registrada_sunarp'
            elif p106a == 1:
                return 'propia_titulada_no_sunarp'
            elif p106a in [2, 3] or p105 in [2, 3, 4]:
                return 'propia_sin_titulo'
            else:
                return 'otro'

        engineered['seguridad_tenencia'] = engineered.apply(map_tenure_security, axis=1)

        return engineered

    def apply_mappings(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Standardizes column names, maps categorical codes/booleans into text labels,
        and enforces correct pandas types (category vs numeric).
        """
        mapped = df[list(COLUMNS_RENAME_MOD01.keys()) + ['seguridad_tenencia']].copy()
        mapped.rename(columns=COLUMNS_RENAME_MOD01, inplace=True)

        # Map survey interview result
        if 'resultado_encuesta' in mapped.columns:
            mapped['resultado_encuesta'] = pd.to_numeric(mapped['resultado_encuesta'], errors='coerce').map({
                1: 'completa',
                2: 'incompleta'
            }).fillna('incompleta')

        # Apply category mappings (supporting both int and str values)
        for col, mapping in CATEGORICAL_MAPPINGS_MOD01.items():
            if col in mapped.columns:
                str_series = mapped[col].astype(str).str.strip()
                num_series = pd.to_numeric(str_series, errors='coerce')
                
                # Map using integer dict
                mapped_series = num_series.map(mapping)

                # Default fallback for skip patterns if any (logged for transparency)
                default_val = SKIP_PATTERN_DEFAULTS.get(col, 'otro')
                n_fallback = int(mapped_series.isna().sum())
                if n_fallback:
                    self.log(f"{col}: {n_fallback} registros sin código válido asignados a '{default_val}' (fallback)")
                mapped[col] = mapped_series.fillna(default_val)
                mapped[col] = mapped[col].replace({'': default_val, 'nan': default_val})

        # Ensure skip patterns on non-mapped categorical columns if any
        for col, default_val in SKIP_PATTERN_DEFAULTS.items():
            if col in mapped.columns and col not in CATEGORICAL_MAPPINGS_MOD01:
                mapped[col] = mapped[col].astype(str).str.strip().replace({'': default_val, 'nan': default_val})

        # Set primary key index
        mapped.set_index(PRIMARY_KEY_HOUSEHOLD, inplace=True)

        # Explicitly ensure numerical columns are real numbers
        for num_col in NUMERIC_COLUMNS_MOD01:
            if num_col in mapped.columns:
                mapped[num_col] = pd.to_numeric(mapped[num_col], errors='coerce')

        # Explicitly convert ALL other features to pandas category dtype
        cat_cols = [c for c in mapped.columns if c not in NUMERIC_COLUMNS_MOD01]
        for c in cat_cols:
            mapped[c] = mapped[c].astype('category')

        return mapped

    def validate_processed_data(self, df: pd.DataFrame) -> None:
        """Runs the validation suite on final clean dataset with dynamic row limits."""
        # 1. Row count validation (adapt to geographic scope)
        if self.min_rows is not None or self.max_rows is not None:
            min_r = self.min_rows
            max_r = self.max_rows
        elif not self.filter_geographic or not self.ubigeo_prefixes:
            min_r = 25000  # National Peru lower bound
            max_r = 60000  # National Peru upper bound
        elif set(self.ubigeo_prefixes) == {"07", "1501"}:
            # Lima Metropolitana y Callao (DOMINIO 8)
            min_r = MIN_EXPECTED_ROWS_LIMA_METRO
            max_r = MAX_EXPECTED_ROWS_LIMA_METRO
        elif set(self.ubigeo_prefixes) == {"07", "15"}:
            # Departamento de Lima completo + Callao (incluye Lima Provincias)
            min_r = MIN_EXPECTED_ROWS_LIMA_CALLAO
            max_r = MAX_EXPECTED_ROWS_LIMA_CALLAO
        else:
            # Custom department/region filter (e.g. ('01', '02'))
            min_r = 50
            max_r = None

        RowValidator.validate_row_count(
            df,
            min_rows=min_r,
            max_rows=max_r,
            context_name=f"Modulo 01 ({self.year})"
        )

        # 2. Primary key uniqueness validation
        RowValidator.validate_primary_key(df, PRIMARY_KEY_HOUSEHOLD)

        # 3. Strict non-null checks
        QualityValidator.validate_no_nulls(df, STRICT_NON_NULL_COLUMNS_MOD01)

        # 4. Numeric boundary checks
        QualityValidator.validate_numeric_bounds(df, 'total_habitaciones', min_val=1, max_val=30)
        QualityValidator.validate_numeric_bounds(df, 'total_dormitorios', min_val=1, max_val=20)

        # 5. Type validation: ensure numeric columns are ONLY total_habitaciones and total_dormitorios
        actual_num_cols = df.select_dtypes(include=np.number).columns.tolist()
        expected_num_cols = NUMERIC_COLUMNS_MOD01
        if set(actual_num_cols) != set(expected_num_cols):
            raise DataQualityError(
                f"Data types misconfigured! Expected numeric columns {expected_num_cols}, "
                f"but found {actual_num_cols}."
            )
