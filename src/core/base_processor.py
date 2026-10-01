"""
Base module processor adhering to SOLID principles (Open/Closed Principle).
Defines the template method workflow for any ENAHO module across multiple years.
"""
from abc import ABC, abstractmethod
import os
from pathlib import Path
from typing import Optional, List, Tuple, Union
import pandas as pd

from src.config.base import (
    DEFAULT_ENCODING,
    DEFAULT_UBIGEO_PREFIXES,
    VALID_SURVEY_RESULTS,
    PRIMARY_KEY_HOUSEHOLD
)
from src.core.validators import (
    SchemaValidator,
    RowValidator,
    QualityValidator
)


class BaseModuleProcessor(ABC):
    """
    Abstract Base Class for ENAHO module preprocessors.
    
    Adheres to the Open/Closed Principle:
    - Closed for modification: The overall execution workflow (process template method) is fixed.
    - Open for extension: Derived classes implement module-specific cleaning,
      feature engineering, and validation hooks.
    """

    def __init__(
        self,
        file_path: Union[str, Path],
        year: Optional[int] = None,
        output_path: Optional[Union[str, Path]] = None,
        filter_lima_callao: bool = True,
        filter_valid_results: bool = True,
        ubigeo_prefixes: Tuple[str, ...] = DEFAULT_UBIGEO_PREFIXES,
        encoding: str = DEFAULT_ENCODING,
        sep: Optional[str] = None,  # If None, automatically detects ; or ,
        verbose: bool = True
    ):
        self.file_path = Path(file_path)
        self.year = year or self._infer_year_from_path(self.file_path)
        self.output_path = Path(output_path) if output_path else None
        self.filter_lima_callao = filter_lima_callao
        self.filter_valid_results = filter_valid_results
        self.ubigeo_prefixes = ubigeo_prefixes
        self.encoding = encoding
        self.sep = sep
        self.verbose = verbose

    @staticmethod
    def _infer_year_from_path(path: Path) -> Optional[int]:
        """Tries to infer survey year from file name or directory name."""
        name = str(path)
        for yr in [2023, 2024, 2025, 2026]:
            if str(yr) in name:
                return yr
        return None

    def log(self, message: str) -> None:
        """Utility logger."""
        if self.verbose:
            prefix = f"[{self.__class__.__name__}" + (f" - {self.year}" if self.year else "") + "]"
            print(f"{prefix} {message}")

    def _detect_delimiter(self) -> str:
        """Automatically detects whether the file is comma or semicolon separated."""
        with open(self.file_path, 'r', encoding=self.encoding, errors='ignore') as f:
            first_line = f.readline()
            if first_line.count(';') > first_line.count(','):
                return ';'
            return ','

    # ==========================================
    # TEMPLATE METHOD (Workflow Orchestrator)
    # ==========================================
    def process(self) -> pd.DataFrame:
        """
        Executes the end-to-end extraction and validation pipeline.
        Subclasses should NOT override this method; instead override the lifecycle hooks below.
        """
        self.log(f"Starting processing from: {self.file_path}")
        
        # 1. Load raw data
        df = self.load_data()
        self.log(f"Raw data loaded: {df.shape[0]} rows, {df.shape[1]} columns.")

        # 2. Validate raw schema
        self.validate_raw_schema(df)

        # 3. Filter geographical and interview scope
        df = self.filter_scope(df)
        self.log(f"After scope filters: {df.shape[0]} rows, {df.shape[1]} columns.")

        # 4. Clean and impute structural missingness
        df = self.clean_and_impute(df)

        # 5. Domain feature engineering
        df = self.feature_engineering(df)

        # 6. Apply value mappings and column renaming
        df = self.apply_mappings(df)

        # 7. Validate processed data
        self.validate_processed_data(df)

        # 8. Save output if requested
        if self.output_path:
            self.save_data(df)

        self.log(f"Processing successfully completed: {df.shape[0]} rows, {df.shape[1]} columns.")
        return df

    # ==========================================
    # LIFECYCLE HOOKS (Extensible points)
    # ==========================================
    def load_data(self) -> pd.DataFrame:
        """Loads data from CSV handling whitespace, delimiter, and encoding."""
        if not self.file_path.exists():
            raise FileNotFoundError(f"Input file does not exist: {self.file_path}")

        delimiter = self.sep if self.sep is not None else self._detect_delimiter()
        self.log(f"Detected delimiter: '{delimiter}' for {self.file_path.name}")

        df = pd.read_csv(
            self.file_path,
            sep=delimiter,
            encoding=self.encoding,
            skipinitialspace=True,
            low_memory=False
        )
        return df

    @abstractmethod
    def validate_raw_schema(self, df: pd.DataFrame) -> None:
        """Asserts required raw columns exist before processing."""
        pass

    def filter_scope(self, df: pd.DataFrame) -> pd.DataFrame:
        """Filters completed interviews and geographic region (Lima & Callao)."""
        filtered = df.copy()

        # Interview result filter (1: Complete, 2: Incomplete with sufficient data)
        if self.filter_valid_results and 'RESULT' in filtered.columns:
            filtered['RESULT'] = pd.to_numeric(filtered['RESULT'], errors='coerce')
            filtered = filtered[filtered['RESULT'].isin(VALID_SURVEY_RESULTS)]

        # Lima and Callao UBIGEO filter
        if self.filter_lima_callao and 'UBIGEO' in filtered.columns:
            filtered['UBIGEO'] = filtered['UBIGEO'].astype(str).str.strip().str.zfill(6)
            filtered = filtered[filtered['UBIGEO'].str.startswith(self.ubigeo_prefixes)]

        return filtered

    @abstractmethod
    def clean_and_impute(self, df: pd.DataFrame) -> pd.DataFrame:
        """Module-specific cleaning and structural missingness resolution."""
        pass

    @abstractmethod
    def feature_engineering(self, df: pd.DataFrame) -> pd.DataFrame:
        """Module-specific domain transformations and aggregations."""
        pass

    @abstractmethod
    def apply_mappings(self, df: pd.DataFrame) -> pd.DataFrame:
        """Standardizes column names and maps categorical codes into readable labels."""
        pass

    @abstractmethod
    def validate_processed_data(self, df: pd.DataFrame) -> None:
        """Final validations on rows, uniqueness, and data quality."""
        pass

    def save_data(self, df: pd.DataFrame) -> None:
        """Exports processed DataFrame to CSV or Parquet."""
        self.output_path.parent.mkdir(parents=True, exist_ok=True)
        if str(self.output_path).endswith('.parquet'):
            df.to_parquet(self.output_path, index=True)
        else:
            df.to_csv(self.output_path, index=True)
        self.log(f"Exported clean dataset to: {self.output_path}")
