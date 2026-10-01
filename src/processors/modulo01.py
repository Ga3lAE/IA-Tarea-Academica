"""
Concrete processor for ENAHO Modulo 01 (Vivienda y Hogar).
Implements dwelling inheritance, tenure consolidation, categorical mapping, and data quality validation.
"""
from typing import Optional, Union, Dict, Any
from pathlib import Path
import numpy as np
import pandas as pd

from src.core.base_processor import BaseModuleProcessor
from src.core.validators import (
    SchemaValidator,
    RowValidator,
    QualityValidator
)
from src.config.modulo01 import (
    COLUMNS_RENAME_MOD01,
    CATEGORICAL_MAPPINGS_MOD01,
    DWELLING_INHERITANCE_COLUMNS,
    STRICT_NON_NULL_COLUMNS_MOD01,
    MIN_EXPECTED_ROWS_LIMA_CALLAO,
    MAX_EXPECTED_ROWS_LIMA_CALLAO
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
                # Forward fill within the same dwelling (CONGLOME, VIVIENDA)
                cleaned[col] = cleaned.groupby(['CONGLOME', 'VIVIENDA'])[col].ffill().bfill()

        # Clean numeric counts
        for num_col in ['P104', 'P104A']:
            if num_col in cleaned.columns:
                cleaned[num_col] = pd.to_numeric(cleaned[num_col], errors='coerce').fillna(1)
                cleaned[num_col] = cleaned[num_col].apply(lambda x: 1 if x <= 0 else x)

        return cleaned

    def feature_engineering(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Transforms skip patterns and generates high-signal features:
        1. Consolidates P105A, P106A, and P106B into 'seguridad_tenencia' (0% nulls).
        2. Formats binary connectivity flags (cable, internet).
        """
        engineered = df.copy()

        # Consolidate tenure and SUNARP registry
        def map_tenure_security(row) -> str:
            p105 = str(row.get('P105A', '')).strip()
            p106a = str(row.get('P106A', '')).strip()
            p106b = str(row.get('P106B', '')).strip()

            if p105 == '1':
                return 'alquilada'
            elif p105 in ['5', '6', '7']:
                return 'cedida_posesion_informal'
            elif p106a == '1' and p106b == '1':
                return 'propia_registrada_sunarp'
            elif p106a == '1':
                return 'propia_titulada_no_sunarp'
            else:
                return 'propia_sin_titulo'

        engineered['seguridad_tenencia'] = engineered.apply(map_tenure_security, axis=1)

        # Standardize binary flags
        for flag_col in ['P1143', 'P1144']:
            if flag_col in engineered.columns:
                val = engineered[flag_col].astype(str).str.strip()
                engineered[flag_col] = (val == '1').astype(int)

        return engineered

    def apply_mappings(self, df: pd.DataFrame) -> pd.DataFrame:
        """Standardizes column names and maps categorical codes into readable labels."""
        mapped = df[list(COLUMNS_RENAME_MOD01.keys()) + ['seguridad_tenencia']].copy()
        mapped.rename(columns=COLUMNS_RENAME_MOD01, inplace=True)

        # Apply category mappings (supporting both int and str values)
        for col, mapping in CATEGORICAL_MAPPINGS_MOD01.items():
            if col in mapped.columns:
                # Convert to numeric where possible to match integer dict keys
                numeric_series = pd.to_numeric(mapped[col], errors='coerce')
                # Map using integer keys, fall back to string keys if any
                mapped_series = numeric_series.map(mapping)
                # Keep original if unmapped or assign 'otro'
                mapped[col] = mapped_series.fillna(mapped[col].astype(str).str.strip()).replace({'': 'otro', 'nan': 'otro'})

        # Set primary key index
        mapped.set_index(PRIMARY_KEY_HOUSEHOLD, inplace=True)

        # Convert object columns to categorical
        str_cols = mapped.select_dtypes(include=['object']).columns
        mapped[str_cols] = mapped[str_cols].astype('category')

        return mapped

    def validate_processed_data(self, df: pd.DataFrame) -> None:
        """Runs the validation suite on final clean dataset."""
        # 1. Row count validation
        RowValidator.validate_row_count(
            df,
            min_rows=MIN_EXPECTED_ROWS_LIMA_CALLAO,
            max_rows=MAX_EXPECTED_ROWS_LIMA_CALLAO,
            context_name=f"Modulo 01 ({self.year})"
        )

        # 2. Primary key uniqueness validation
        RowValidator.validate_primary_key(df, PRIMARY_KEY_HOUSEHOLD)

        # 3. Strict non-null checks
        QualityValidator.validate_no_nulls(df, STRICT_NON_NULL_COLUMNS_MOD01)

        # 4. Numeric boundary checks
        QualityValidator.validate_numeric_bounds(df, 'total_habitaciones', min_val=1, max_val=30)
        QualityValidator.validate_numeric_bounds(df, 'total_dormitorios', min_val=1, max_val=20)
