"""
Validation suite for ENAHO data pipelines.
Provides strict assertions for schemas, rows, primary keys, and data quality.
"""
from typing import List, Set, Any, Optional
import pandas as pd


class ValidationError(Exception):
    """Base exception for data validation failures."""
    pass


class SchemaError(ValidationError):
    """Raised when columns or data types do not conform to expected schema."""
    pass


class RowValidationError(ValidationError):
    """Raised when row counts or uniqueness constraints are violated."""
    pass


class DataQualityError(ValidationError):
    """Raised when data values violate domain boundaries or nullness rules."""
    pass


class SchemaValidator:
    """Validates structural and column requirements."""

    @staticmethod
    def validate_required_columns(df: pd.DataFrame, required_columns: List[str]) -> None:
        """Asserts that all required columns exist in the DataFrame."""
        missing = [col for col in required_columns if col not in df.columns]
        if missing:
            raise SchemaError(
                f"Missing {len(missing)} required column(s) in DataFrame: {missing}\n"
                f"Available columns ({len(df.columns)}): {list(df.columns[:10])}..."
            )


class RowValidator:
    """Validates volume, cardinality, and key constraints."""

    @staticmethod
    def validate_row_count(
        df: pd.DataFrame,
        min_rows: Optional[int] = None,
        max_rows: Optional[int] = None,
        context_name: str = "dataset"
    ) -> None:
        """Asserts that total row count falls within expected bounds."""
        n_rows = len(df)
        if min_rows is not None and n_rows < min_rows:
            raise RowValidationError(
                f"Row count for {context_name} is below expected threshold: "
                f"found {n_rows} rows, expected at least {min_rows}."
            )
        if max_rows is not None and n_rows > max_rows:
            raise RowValidationError(
                f"Row count for {context_name} exceeds expected threshold: "
                f"found {n_rows} rows, expected at most {max_rows}."
            )

    @staticmethod
    def validate_primary_key(df: pd.DataFrame, primary_key: List[str]) -> None:
        """Asserts that the primary key columns are unique and contain no duplicates."""
        # Check presence of pk columns
        for col in primary_key:
            if col not in df.columns and col not in df.index.names:
                raise SchemaError(f"Primary key column '{col}' not present in columns or index.")

        # Check duplicates
        if df.index.names == primary_key:
            is_dup = df.index.duplicated().any()
        else:
            is_dup = df.duplicated(subset=primary_key).any()

        if is_dup:
            if df.index.names == primary_key:
                dup_sample = df[df.index.duplicated(keep=False)].index.tolist()[:5]
            else:
                dup_sample = df[df.duplicated(subset=primary_key, keep=False)][primary_key].head(5).to_dict('records')
            raise RowValidationError(
                f"Primary key uniqueness violation! Duplicate keys detected: {dup_sample}"
            )


class QualityValidator:
    """Validates nullness, numeric ranges, and categorical domains."""

    @staticmethod
    def validate_no_nulls(df: pd.DataFrame, columns: List[str]) -> None:
        """Asserts that specified columns contain zero null values."""
        null_report = {}
        for col in columns:
            if col in df.columns:
                n_nulls = df[col].isna().sum()
                if n_nulls > 0:
                    null_report[col] = int(n_nulls)
            elif col not in df.index.names:
                null_report[col] = "Column not found"

        if null_report:
            raise DataQualityError(
                f"Strict non-null constraint violated! Columns with nulls:\n{null_report}"
            )

    @staticmethod
    def validate_numeric_bounds(
        df: pd.DataFrame,
        column: str,
        min_val: Optional[float] = None,
        max_val: Optional[float] = None
    ) -> None:
        """Asserts that numeric column values fall within realistic boundaries."""
        if column not in df.columns:
            return
        series = pd.to_numeric(df[column], errors='coerce').dropna()
        if min_val is not None and (series < min_val).any():
            violators = (series < min_val).sum()
            raise DataQualityError(
                f"Column '{column}' has {violators} values below minimum threshold {min_val}."
            )
        if max_val is not None and (series > max_val).any():
            violators = (series > max_val).sum()
            raise DataQualityError(
                f"Column '{column}' has {violators} values exceeding maximum threshold {max_val}."
            )
