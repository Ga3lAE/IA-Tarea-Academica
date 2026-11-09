"""
Módulo de Preprocesamiento y Transformadores Anti-Fuga (Scikit-Learn).
Implementa la selección canónica de variables (R^28), el preprocesamiento robusto,
la codificación One-Hot de categorías infrecuentes y el levantamiento de la observación OBS-P01
(imputación por mediana de conglomerado en 72 hogares secundarios).
"""
import sys
from pathlib import Path
from typing import List, Tuple, Optional, Union
import pandas as pd
import numpy as np

from sklearn.base import BaseEstimator, TransformerMixin
from sklearn.pipeline import Pipeline
from sklearn.compose import ColumnTransformer
from sklearn.preprocessing import RobustScaler, OneHotEncoder, OrdinalEncoder
from sklearn.impute import SimpleImputer

# Asegurar importación tanto si se ejecuta desde raíz como desde src/
_ROOT = Path(__file__).resolve().parents[1]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

# =============================================================================
# CONSTANTES METODOLÓGICAS: ESPACIO CANÓNICO R^28
# =============================================================================

# 14 Variables Numéricas / Continuas / Ratios / Ordinales
NUMERIC_COLS: List[str] = [
    # Vivienda (3)
    "total_habitaciones",
    "total_dormitorios",
    "personas_por_hab",
    # Demografía (6)
    "n_miembros",
    "n_ninos_0_5",
    "n_menores_14",
    "n_mayores_65",
    "tasa_dependencia",
    "jefe_edad",
    # Educación (2)
    "educ_jefe",
    "educ_max_hogar",
    # Empleo (3)
    "n_ocupados",
    "ocupados_por_miembro",
    "jefe_horas_semanales",
]

# 14 Variables Categóricas / Nominales / Binarias
CATEGORICAL_COLS: List[str] = [
    # Vivienda (9)
    "tipo_vivienda",
    "material_pared",
    "material_piso",
    "tenencia_vivienda",
    "fuente_agua",
    "agua_todos_los_dias",
    "conexion_bano",
    "combustible_cocina",
    "tiene_internet",
    # Demografía (1)
    "jefe_mujer",
    # Empleo (4)
    "jefe_ocupado",
    "jefe_cat_ocupacional",
    "jefe_empresa_ruc",
    "jefe_sin_pension",
]

# Las 28 variables metodológicas que conforman el vector x_i in R^28
CANONICAL_FEATURES_28: List[str] = NUMERIC_COLS + CATEGORICAL_COLS

TARGET_COL: str = "target_pobreza"
TARGET_ALIAS: str = "y"
GROUP_COL: str = "conglomerado"


# =============================================================================
# TRANSFORMADORES PERSONALIZADOS ANTI-FUGA
# =============================================================================

class SecondaryHouseholdImputer(BaseEstimator, TransformerMixin):
    """
    Transformador Scikit-Learn que resuelve la Observación OBS-P01 del Jurado:
    1. Imputa atributos numéricos de vivienda ('total_habitaciones', 'total_dormitorios')
       utilizando la mediana del conglomerado censal (CONGLOME) calculada estrictamente
       sobre el fold de entrenamiento, con respaldo en la mediana global de train.
    2. Recalcula de forma consistente 'personas_por_hab' tras la imputación física.
    3. Resuelve nulos estructurales de empleo asignando 0.0 horas semanales trabajadas
       cuando el jefe de hogar no trabaja (jefe_ocupado == 0).
    """

    def __init__(self, group_col: str = GROUP_COL):
        self.group_col = group_col
        self.cong_hab_median_: dict = {}
        self.cong_dor_median_: dict = {}
        self.global_hab_median_: float = 3.0
        self.global_dor_median_: float = 2.0

    def fit(self, X: pd.DataFrame, y=None):
        df = X if isinstance(X, pd.DataFrame) else pd.DataFrame(X)
        if self.group_col in df.columns:
            self.cong_hab_median_ = (
                df.groupby(self.group_col)["total_habitaciones"]
                .median()
                .dropna()
                .to_dict()
            )
            self.cong_dor_median_ = (
                df.groupby(self.group_col)["total_dormitorios"]
                .median()
                .dropna()
                .to_dict()
            )
        if "total_habitaciones" in df.columns:
            self.global_hab_median_ = float(df["total_habitaciones"].median())
        if "total_dormitorios" in df.columns:
            self.global_dor_median_ = float(df["total_dormitorios"].median())
        return self

    def transform(self, X: pd.DataFrame) -> pd.DataFrame:
        df = X.copy() if isinstance(X, pd.DataFrame) else pd.DataFrame(X)

        # 1. Imputación por conglomerado censal en vivienda
        if self.group_col in df.columns:
            hab_imp = df[self.group_col].map(self.cong_hab_median_).fillna(self.global_hab_median_)
            dor_imp = df[self.group_col].map(self.cong_dor_median_).fillna(self.global_dor_median_)
        else:
            hab_imp = self.global_hab_median_
            dor_imp = self.global_dor_median_

        if "total_habitaciones" in df.columns:
            df["total_habitaciones"] = df["total_habitaciones"].fillna(hab_imp)
        if "total_dormitorios" in df.columns:
            df["total_dormitorios"] = df["total_dormitorios"].fillna(dor_imp)

        # 2. Recalcular hacinamiento tras la imputación de habitaciones
        if "personas_por_hab" in df.columns and "n_miembros" in df.columns:
            hab_safe = df["total_habitaciones"].clip(lower=1)
            df["personas_por_hab"] = df["personas_por_hab"].fillna(df["n_miembros"] / hab_safe)

        # 3. Nulo estructural de horas de empleo: si no trabaja -> 0 horas
        if "jefe_horas_semanales" in df.columns and "jefe_ocupado" in df.columns:
            df.loc[df["jefe_ocupado"] == 0, "jefe_horas_semanales"] = 0.0

        return df


# =============================================================================
# CONSTRUCTORES DE PIPELINES DE PREPROCESAMIENTO
# =============================================================================

def build_preprocessor(
    numeric_cols: Optional[List[str]] = None,
    categorical_cols: Optional[List[str]] = None,
    scale_numeric: bool = True,
    one_hot: bool = True,
    min_category_frequency: int = 20,
) -> ColumnTransformer:
    """
    Construye el ColumnTransformer de Scikit-Learn para las 28 variables canónicas.

    Parámetros
    ----------
    numeric_cols : list[str] | None
        Lista de variables numéricas (por defecto NUMERIC_COLS).
    categorical_cols : list[str] | None
        Lista de variables categóricas (por defecto CATEGORICAL_COLS).
    scale_numeric : bool, default=True
        Si es True, aplica RobustScaler() a las numéricas (recomendado para modelos lineales).
    one_hot : bool, default=True
        Si es True, aplica OneHotEncoder agrupando categorías con frecuencia < min_category_frequency.
        Si es False, aplica OrdinalEncoder (para árboles nativos).
    min_category_frequency : int, default=20
        Frecuencia mínima para agrupar categorías raras (< 1% de la muestra).

    Retorna
    -------
    ColumnTransformer
    """
    if numeric_cols is None:
        numeric_cols = NUMERIC_COLS
    if categorical_cols is None:
        categorical_cols = CATEGORICAL_COLS

    # Rama Numérica
    num_steps = [("imputer", SimpleImputer(strategy="median"))]
    if scale_numeric:
        num_steps.append(("scaler", RobustScaler()))
    num_pipe = Pipeline(num_steps)

    # Rama Categórica
    cat_steps = [("imputer", SimpleImputer(strategy="constant", fill_value=-1))]
    if one_hot:
        cat_steps.append((
            "encoder",
            OneHotEncoder(
                handle_unknown="ignore",
                min_frequency=min_category_frequency,
                sparse_output=False,
            )
        ))
    else:
        cat_steps.append((
            "encoder",
            OrdinalEncoder(
                handle_unknown="use_encoded_value",
                unknown_value=-1,
            )
        ))
    cat_pipe = Pipeline(cat_steps)

    preprocessor = ColumnTransformer(
        transformers=[
            ("num", num_pipe, numeric_cols),
            ("cat", cat_pipe, categorical_cols),
        ],
        remainder="drop",
    )
    return preprocessor


def build_full_pipeline(
    estimator,
    scale_numeric: bool = True,
    one_hot: bool = True,
    min_category_frequency: int = 20,
) -> Pipeline:
    """
    Construye el Pipeline end-to-end garantizando cero fuga de datos:
    1. SecondaryHouseholdImputer (mediana conglomerado + nulos estructurales)
    2. ColumnTransformer (imputación mediana general, escalamiento y codificación)
    3. Estimador supervisado (Clasificador o Regresor)
    """
    cleaner = SecondaryHouseholdImputer()
    preprocessor = build_preprocessor(
        scale_numeric=scale_numeric,
        one_hot=one_hot,
        min_category_frequency=min_category_frequency,
    )
    return Pipeline([
        ("cleaner", cleaner),
        ("preprocessor", preprocessor),
        ("model", estimator),
    ])


def prepare_xy_data(
    df: pd.DataFrame,
    features: Optional[List[str]] = None,
    target_col: str = TARGET_COL,
    group_col: str = GROUP_COL,
) -> Tuple[pd.DataFrame, pd.Series, pd.Series]:
    """
    Extrae (X, y, groups) desde un DataFrame consolidado del Big DF.

    Parámetros
    ----------
    df : pd.DataFrame
        DataFrame consolidado (2024 o 2025).
    features : list[str] | None
        Variables a incluir en X (por defecto CANONICAL_FEATURES_28 + [group_col] para el limpiador).
    target_col : str, default='target_pobreza'
        Nombre de la variable objetivo binaria.
    group_col : str, default='conglomerado'
        Nombre de la variable de agrupación espacial para GroupKFold.

    Retorna
    -------
    X : pd.DataFrame
    y : pd.Series
    groups : pd.Series
    """
    if features is None:
        features = CANONICAL_FEATURES_28

    # Garantizar que group_col esté presente en X para que SecondaryHouseholdImputer opere
    cols_to_extract = list(dict.fromkeys(features + [group_col]))
    cols_present = [c for c in cols_to_extract if c in df.columns]

    X = df[cols_present].copy()
    y = df[target_col].copy() if target_col in df.columns else df[TARGET_ALIAS].copy()
    groups = df[group_col].copy()

    return X, y, groups


if __name__ == "__main__":
    from src.dataset import load_train_test_master

    print("=== Test de Verificación de src/preprocessing.py ===")
    df_tr, df_te = load_train_test_master()

    X_tr, y_tr, grp_tr = prepare_xy_data(df_tr)
    X_te, y_te, grp_te = prepare_xy_data(df_te)

    cleaner = SecondaryHouseholdImputer()
    X_tr_clean = cleaner.fit_transform(X_tr)
    X_te_clean = cleaner.transform(X_te)

    prep = build_preprocessor(scale_numeric=True, one_hot=True)
    X_tr_proc = prep.fit_transform(X_tr_clean)
    X_te_proc = prep.transform(X_te_clean)

    print(f"✓ Train transformado: {X_tr_proc.shape} | NaNs: {np.isnan(X_tr_proc).any()}")
    print(f"✓ Test transformado:  {X_te_proc.shape} | NaNs: {np.isnan(X_te_proc).any()}")
    print(f"✓ Features One-Hot generadas: {X_tr_proc.shape[1]}")
    print("✓ Módulo src/preprocessing.py validado exitosamente.")
