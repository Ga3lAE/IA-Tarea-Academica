"""
Base module processor adhering to SOLID principles (Open/Closed Principle).
Defines the template method workflow for any ENAHO module across multiple years.
"""
from abc import ABC, abstractmethod
import os
from pathlib import Path
from typing import Optional, List, Tuple, Union, Sequence
import pandas as pd

from src.config.base import (
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
        filter_geographic: bool = True,
        filter_lima_callao: Optional[bool] = None,  # Backward compatibility alias
        filter_valid_results: bool = True,
        ubigeo_prefixes: Optional[Union[str, Sequence[str]]] = None,
        encoding: Optional[str] = None,
        sep: Optional[str] = None,          # None = auto-detect (; or ,); can be forced
        output_sep: Optional[str] = None,   # None = uses DEFAULT_OUTPUT_SEPARATOR (,)
        min_rows: Optional[int] = None,
        max_rows: Optional[int] = None,
        verbose: bool = True
    ):
        """
        Initializes an ENAHO module preprocessor.

        Parameters
        ----------
        file_path : Union[str, Path]
            Path to the raw CSV file (e.g. 'Data/1031-Modulo01/Enaho01-2025-100.csv').
        year : Optional[int], default=None
            Survey year (e.g. 2024, 2025). If None, automatically inferred from the file path.
        output_path : Optional[Union[str, Path]], default=None
            Destination path for the cleaned output file (CSV or Parquet). If None, no file is exported.
        filter_geographic : bool, default=True
            Whether to filter households by geographical code (UBIGEO).
            - True: Filters using `ubigeo_prefixes` (by default Lima & Callao).
            - False: Disables geographic filtering, processing the entire national dataset (all 25 departments).
        filter_valid_results : bool, default=True
            Whether to keep only completed/sufficient interviews (RESULT 1: Completa, 2: Incompleta).
        ubigeo_prefixes : Optional[Union[str, Sequence[str]]], default=None
            Department or province prefix codes to filter by (e.g., ('07', '1501') for Lima Metropolitana y Callao,
            ('01',) for Amazonas, ('02',) for Áncash, ('20', '13') for Piura/La Libertad).
            If None and filter_geographic=True, defaults to DEFAULT_UBIGEO_PREFIXES in src/config/base.py.
        encoding : Optional[str], default=None
            File character encoding (e.g. 'latin-1', 'utf-8', 'cp1252').
            If None, uses DEFAULT_ENCODING ('latin-1').
        sep : Optional[str], default=None
            Input column delimiter of the raw CSV.
            - None: AUTO-DETECT. Inspects header and sample lines to detect ',' vs ';'.
            - ';' or ',': Forces reading with the specified delimiter.
        output_sep : Optional[str], default=None
            Delimiter used when saving the cleaned CSV via `output_path`.
            If None, uses DEFAULT_OUTPUT_SEPARATOR (',').
        min_rows : Optional[int], default=None
            Custom minimum row count assertion.
            If None, automatically inferred based on scope (Lima Metropolitana: 3,800, Dpto. Lima + Callao: 4,000, Nacional: 25,000, Custom: 50).
        max_rows : Optional[int], default=None
            Custom maximum row count assertion.
            If None, automatically inferred based on scope.
        verbose : bool, default=True
            Whether to print progress log messages during execution.
        """
        # Dynamically import defaults from config at instantiation time (not import time)
        from src.config.base import (
            DEFAULT_ENCODING,
            DEFAULT_SEPARATOR,
            DEFAULT_OUTPUT_SEPARATOR,
            DEFAULT_UBIGEO_PREFIXES
        )

        self.file_path = Path(file_path)
        self.year = year or self._infer_year_from_path(self.file_path)
        self.output_path = Path(output_path) if output_path else None
        
        # Handle backward compatibility for filter_lima_callao
        if filter_lima_callao is not None:
            self.filter_geographic = filter_lima_callao
        else:
            self.filter_geographic = filter_geographic

        self.filter_valid_results = filter_valid_results
        
        # Resolve UBIGEO prefixes dynamically
        if ubigeo_prefixes is not None:
            if isinstance(ubigeo_prefixes, str):
                self.ubigeo_prefixes = (ubigeo_prefixes,)
            else:
                self.ubigeo_prefixes = tuple(ubigeo_prefixes)
        else:
            self.ubigeo_prefixes = tuple(DEFAULT_UBIGEO_PREFIXES) if DEFAULT_UBIGEO_PREFIXES else None

        self.encoding = encoding or DEFAULT_ENCODING
        self.sep = sep if sep is not None else DEFAULT_SEPARATOR
        self.output_sep = output_sep or DEFAULT_OUTPUT_SEPARATOR
        self.min_rows = min_rows
        self.max_rows = max_rows
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

    def _check_git_lfs_pointer(self) -> None:
        """Detects if the file is an unresolved Git LFS pointer text file."""
        try:
            with open(self.file_path, "r", encoding="utf-8", errors="ignore") as f:
                first_line = f.readline().strip()
                if first_line.startswith("version https://git-lfs.github.com/spec/v1"):
                    raise RuntimeError(
                        f"\n[GIT LFS ERROR] El archivo '{self.file_path.name}' es un puntero de Git LFS (3 líneas) y no contiene la data real.\n"
                        f"Para descargar la data real, ejecuta en tu terminal:\n"
                        f"    git lfs checkout\n"
                        f"o:\n"
                        f"    git lfs pull\n"
                    )
        except UnicodeDecodeError:
            pass

    def _detect_delimiter(self) -> str:
        """Robustly detects whether the file is comma or semicolon separated."""
        with open(self.file_path, 'r', encoding=self.encoding, errors='ignore') as f:
            sample_lines = [f.readline() for _ in range(5)]
            sample_text = "".join(sample_lines)

            # Check header line count first
            header = sample_lines[0] if sample_lines else ""
            sc_count = header.count(';')
            cm_count = header.count(',')

            if sc_count > cm_count:
                return ';'
            elif cm_count > sc_count:
                return ','

            # Check aggregate across multiple lines
            if sample_text.count(';') > sample_text.count(','):
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
        """Loads data from CSV handling whitespace, delimiter, encoding, and Git LFS check."""
        if not self.file_path.exists():
            raise FileNotFoundError(f"Input file does not exist: {self.file_path}")

        # Check if the file is just an unresolved Git LFS pointer
        self._check_git_lfs_pointer()

        delimiter = self.sep if self.sep not in (None, 'auto') else self._detect_delimiter()
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
        """Filters completed interviews and geographic region (custom UBIGEO prefixes or national)."""
        filtered = df.copy()

        # Interview result filter (1: Complete, 2: Incomplete with sufficient data)
        if self.filter_valid_results and 'RESULT' in filtered.columns:
            filtered['RESULT'] = pd.to_numeric(filtered['RESULT'], errors='coerce')
            filtered = filtered[filtered['RESULT'].isin(VALID_SURVEY_RESULTS)]

        # Standardize UBIGEO to 6-digit zero-padded string
        if 'UBIGEO' in filtered.columns:
            filtered['UBIGEO'] = filtered['UBIGEO'].astype(str).str.strip().str.split('.').str[0].str.zfill(6)

        # Geographic UBIGEO filter (if enabled and prefixes provided)
        if self.filter_geographic and self.ubigeo_prefixes and 'UBIGEO' in filtered.columns:
            filtered = filtered[filtered['UBIGEO'].str.startswith(self.ubigeo_prefixes)]
            self.log(f"Applied UBIGEO filter with prefixes {self.ubigeo_prefixes}")
        else:
            self.log("Geographic filter disabled: Processing national scope (all UBIGEOs)")

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
        """Exports processed DataFrame to CSV (with output_sep) or Parquet."""
        self.output_path.parent.mkdir(parents=True, exist_ok=True)
        if str(self.output_path).endswith('.parquet'):
            df.to_parquet(self.output_path, index=True)
        else:
            df.to_csv(self.output_path, sep=self.output_sep, index=True)
        self.log(f"Exported clean dataset to: {self.output_path} (sep='{self.output_sep}')")
