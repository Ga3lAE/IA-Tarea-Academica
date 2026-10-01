"""
Master pipeline orchestrator for ENAHO data workflows.
Demonstrates the Open/Closed Principle by allowing dynamic registration and execution
of module processors across single or multiple survey years.
"""
from pathlib import Path
from typing import Dict, List, Optional, Type, Union
import pandas as pd

from src.core.base_processor import BaseModuleProcessor
from src.processors.modulo01 import Modulo01Processor


class ENAHOPipeline:
    """
    Orchestrates execution of multiple ENAHO modules across years.
    Open for extension: Register new module processors without changing pipeline logic.
    """

    def __init__(self, data_root: Union[str, Path] = "Data", verbose: bool = True):
        self.data_root = Path(data_root)
        self.verbose = verbose
        # Module registry: module_code -> Processor Class
        self._registry: Dict[str, Type[BaseModuleProcessor]] = {
            "modulo01": Modulo01Processor,
        }

    def register_processor(self, module_code: str, processor_cls: Type[BaseModuleProcessor]) -> None:
        """Dynamically registers a new processor (Open/Closed Principle)."""
        self._registry[module_code.lower()] = processor_cls
        if self.verbose:
            print(f"[ENAHOPipeline] Registered processor for: {module_code}")

    def find_csv(self, year: int, module_code: str) -> Optional[Path]:
        """Discovers the raw CSV file based on year and module code (case-insensitive)."""
        mod_clean = module_code.lower().replace("-", "").replace("_", "")
        for d in self.data_root.iterdir():
            if not d.is_dir():
                continue
            d_clean = d.name.lower().replace("-", "").replace("_", "")
            if mod_clean in d_clean:
                for f in d.glob("*.csv"):
                    if str(year) in f.name and not f.name.endswith("_cleaned.csv"):
                        return f
        return None

    def run_module(
        self,
        module_code: str,
        years: List[int],
        export_cleaned: bool = True,
        concatenate_years: bool = True
    ) -> Union[pd.DataFrame, Dict[int, pd.DataFrame]]:
        """
        Runs the specified module across one or more years.
        
        Args:
            module_code: Name of module (e.g. 'modulo01').
            years: List of survey years (e.g. [2024, 2025]).
            export_cleaned: Whether to save _cleaned.csv files.
            concatenate_years: Whether to concatenate all years into a single DataFrame.
        """
        mod_key = module_code.lower()
        if mod_key not in self._registry:
            raise KeyError(
                f"Processor for '{module_code}' not found in registry. "
                f"Available processors: {list(self._registry.keys())}"
            )

        processor_cls = self._registry[mod_key]
        results: Dict[int, pd.DataFrame] = {}

        for yr in years:
            csv_path = self.find_csv(yr, module_code)
            if not csv_path:
                print(f"[ENAHOPipeline] Warning: CSV for {module_code} ({yr}) not found under {self.data_root}")
                continue

            output_path = csv_path.parent / csv_path.name.replace(".csv", "_cleaned.csv") if export_cleaned else None
            
            processor = processor_cls(
                file_path=csv_path,
                year=yr,
                output_path=output_path,
                verbose=self.verbose
            )
            df_year = processor.process()
            df_year['anio_encuesta'] = yr
            results[yr] = df_year

        if concatenate_years and results:
            df_concat = pd.concat(list(results.values()), axis=0)
            if self.verbose:
                print(f"[ENAHOPipeline] Consolidated multi-year {module_code}: {df_concat.shape[0]} total rows across {list(results.keys())}")
            return df_concat

        return results
