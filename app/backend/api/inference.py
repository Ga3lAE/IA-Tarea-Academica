"""Núcleo autocontenido de inferencia y explicabilidad TreeSHAP para el backend.

Reúne únicamente las piezas necesarias para servir `winner_bundle.joblib` sin depender
del código de ingesta ni entrenamiento de la raíz del repositorio (`src/`):
- `SecondaryHouseholdImputer` y constantes del espacio canónico R^28.
- `build_household_dataframe_from_answers`: convierte respuestas normalizadas al DataFrame R^28.
- `predict_single_household` + TreeSHAP exacto para `HistGradientBoostingClassifier`.
- Shim en memoria para cargar artefactos `.joblib` que referencien `src.preprocessing`.
"""
from __future__ import annotations

import importlib.util
import sys
import types
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

import joblib
import numpy as np
import pandas as pd
from sklearn.base import BaseEstimator, TransformerMixin

# =============================================================================
# CONSTANTES METODOLÓGICAS: ESPACIO CANÓNICO R^28
# =============================================================================

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

CANONICAL_FEATURES_28: List[str] = NUMERIC_COLS + CATEGORICAL_COLS
GROUP_COL: str = "conglomerado"
AUX_GROUP_COL: str = "ubigeo"


# =============================================================================
# TRANSFORMADOR SERIALIZADO EN EL BUNDLE
# =============================================================================

class SecondaryHouseholdImputer(BaseEstimator, TransformerMixin):
    """Imputación espacial jerárquica para hogares secundarios y nulos estructurales de empleo."""

    def __init__(self, group_col: str = GROUP_COL, aux_group_col: str = AUX_GROUP_COL):
        self.group_col = group_col
        self.aux_group_col = aux_group_col
        self.cong_hab_median_: dict = {}
        self.cong_dor_median_: dict = {}
        self.ubigeo_hab_median_: dict = {}
        self.ubigeo_dor_median_: dict = {}
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
        if self.aux_group_col in df.columns:
            self.ubigeo_hab_median_ = (
                df.groupby(self.aux_group_col)["total_habitaciones"]
                .median()
                .dropna()
                .to_dict()
            )
            self.ubigeo_dor_median_ = (
                df.groupby(self.aux_group_col)["total_dormitorios"]
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

        hab_imp = pd.Series(np.nan, index=df.index, dtype=float)
        dor_imp = pd.Series(np.nan, index=df.index, dtype=float)

        if self.group_col in df.columns and self.cong_hab_median_:
            hab_imp = df[self.group_col].map(self.cong_hab_median_)
            dor_imp = df[self.group_col].map(self.cong_dor_median_)

        if self.aux_group_col in df.columns and getattr(self, "ubigeo_hab_median_", None):
            hab_imp = hab_imp.fillna(df[self.aux_group_col].map(self.ubigeo_hab_median_))
            dor_imp = dor_imp.fillna(df[self.aux_group_col].map(self.ubigeo_dor_median_))

        hab_imp = hab_imp.fillna(self.global_hab_median_)
        dor_imp = dor_imp.fillna(self.global_dor_median_)

        if "total_habitaciones" in df.columns:
            df["total_habitaciones"] = df["total_habitaciones"].fillna(hab_imp)
        if "total_dormitorios" in df.columns:
            df["total_dormitorios"] = df["total_dormitorios"].fillna(dor_imp)

        if "personas_por_hab" in df.columns and "n_miembros" in df.columns:
            hab_safe = df["total_habitaciones"].clip(lower=1)
            df["personas_por_hab"] = df["personas_por_hab"].fillna(df["n_miembros"] / hab_safe)

        if "jefe_horas_semanales" in df.columns and "jefe_ocupado" in df.columns:
            df.loc[df["jefe_ocupado"] == 0, "jefe_horas_semanales"] = 0.0

        return df

    def get_feature_names_out(self, input_features=None):
        if input_features is not None:
            return np.asarray(input_features, dtype=object)
        return None


def _ensure_pickle_compat() -> None:
    """Registra `src.preprocessing.SecondaryHouseholdImputer` si `src.preprocessing` no existe.

    Permite deserializar copias directas de `winner_bundle.joblib` entrenadas desde la raíz
    del proyecto sin copiar ni referenciar la carpeta `src/` dentro de `app/`.
    """
    if "src.preprocessing" in sys.modules:
        return
    try:
        if importlib.util.find_spec("src.preprocessing") is not None:
            return
    except ModuleNotFoundError:
        pass

    src_mod = sys.modules.get("src")
    if src_mod is None:
        src_mod = types.ModuleType("src")
        src_mod.__path__ = []
        sys.modules["src"] = src_mod
    prep_mod = types.ModuleType("src.preprocessing")
    prep_mod.SecondaryHouseholdImputer = SecondaryHouseholdImputer
    src_mod.preprocessing = prep_mod
    sys.modules["src.preprocessing"] = prep_mod


def load_deployment_bundle(path: Union[str, Path]) -> Dict[str, Any]:
    """Carga el paquete serializado `winner_bundle.joblib` de forma autocontenida."""
    p = Path(path)
    if not p.exists():
        raise FileNotFoundError(f"No existe el modelo exportado en '{p}'.")
    _ensure_pickle_compat()
    bundle = joblib.load(p)
    if "metrics_audit" not in bundle and "metrics_audit_records" in bundle:
        bundle["metrics_audit"] = pd.DataFrame(bundle["metrics_audit_records"])
    return bundle


# =============================================================================
# TREESHAP EXACTO PARA HISTGBDT SIN DEPENDENCIA EXTERNA `shap`
# =============================================================================

def _map_encoded_name_to_original(enc_name: str) -> str:
    """Mapea un nombre transformado (ej. 'cat__material_pared_1.0' o 'num__jefe_edad') a su variable R^28."""
    raw = enc_name.split("__", 1)[-1]
    for orig in sorted(CANONICAL_FEATURES_28, key=len, reverse=True):
        if raw == orig or raw.startswith(orig + "_"):
            return orig
    return raw


def _treeshap_unwind_weights(nw: List[float], ulen: int, zi: float, oi: float) -> List[float]:
    """Desenrolla los pesos polinomiales de la ruta al eliminar una característica previa."""
    nlen = ulen - 1
    unw = [0.0] * nlen
    if oi != 0.0:
        d = nw[nlen]
        for j in range(nlen - 1, -1, -1):
            w_j = d * ulen / (oi * (j + 1))
            unw[j] = w_j
            d = nw[j] - w_j * zi * (nlen - j) / ulen
    else:
        for j in range(nlen - 1, -1, -1):
            unw[j] = nw[j] * ulen / (zi * (nlen - j))
    return unw


def _treeshap_single_signature(
    nodes: np.ndarray, dec: np.ndarray, node_to_int: Dict[int, int], n_features: int
) -> np.ndarray:
    """Ejecuta el algoritmo TreeSHAP (Lundberg & Lee, 2018) sobre un vector único de decisiones."""
    phi = np.zeros(n_features, dtype=np.float64)
    is_leaf = nodes["is_leaf"].astype(bool)
    vals = nodes["value"]
    cnts = nodes["count"].astype(np.float64)
    lefts = nodes["left"]
    rights = nodes["right"]
    fidx = nodes["feature_idx"]

    def _recurse(
        node: int,
        mf: List[int],
        mz: List[float],
        mo: List[float],
        mw: List[float],
        pz: float,
        po: float,
        pi: int,
    ) -> None:
        ulen = len(mf)
        nf = mf + [pi]
        nz = mz + [pz]
        no = mo + [po]
        nw = mw + [1.0 if ulen == 0 else 0.0]
        for i in range(ulen - 1, -1, -1):
            nw[i + 1] += po * nw[i] * (i + 1) / (ulen + 1)
            nw[i] = pz * nw[i] * (ulen - i) / (ulen + 1)
        ulen += 1

        if is_leaf[node]:
            v = float(vals[node])
            for i in range(1, ulen):
                s = sum(_treeshap_unwind_weights(nw, ulen, nz[i], no[i]))
                phi[nf[i]] += v * (no[i] - nz[i]) * s
            return

        l_ch, r_ch = int(lefts[node]), int(rights[node])
        hot, cold = (l_ch, r_ch) if dec[node_to_int[node]] == 1 else (r_ch, l_ch)
        f_node = int(fidx[node])
        c_node = cnts[node]
        iz, io = 1.0, 1.0
        if f_node in nf[1:]:
            k_prev = nf.index(f_node, 1)
            iz, io = nz[k_prev], no[k_prev]
            nw2 = _treeshap_unwind_weights(nw, ulen, iz, io)
            nf2 = nf[:k_prev] + nf[k_prev + 1:]
            nz2 = nz[:k_prev] + nz[k_prev + 1:]
            no2 = no[:k_prev] + no[k_prev + 1:]
        else:
            nf2, nz2, no2, nw2 = nf, nz, no, nw
        _recurse(hot, nf2, nz2, no2, nw2, iz * cnts[hot] / c_node, io, f_node)
        _recurse(cold, nf2, nz2, no2, nw2, iz * cnts[cold] / c_node, 0.0, f_node)

    _recurse(0, [-1], [1.0], [1.0], [1.0], 1.0, 1.0, -1)
    return phi


def _histgb_tree_contribs(model: Any, X_mat: np.ndarray) -> np.ndarray:
    """Calcula valores TreeSHAP exactos en espacio log-odds para HistGradientBoostingClassifier."""
    X_arr = np.asarray(X_mat, dtype=np.float64)
    n_samples, n_features = X_arr.shape
    contribs = np.zeros((n_samples, n_features), dtype=np.float64)

    for tree_group in model._predictors:
        nodes = tree_group[0].nodes
        if len(nodes) <= 1:
            continue
        is_leaf = nodes["is_leaf"].astype(bool)
        internal_ids = np.where(~is_leaf)[0]
        f_int = nodes["feature_idx"][internal_ids]
        thr_int = nodes["num_threshold"][internal_ids]
        ml_int = nodes["missing_go_to_left"][internal_ids].astype(bool)
        xv = X_arr[:, f_int]
        go_left = np.where(np.isnan(xv), ml_int[None, :], xv <= thr_int[None, :]).astype(np.uint8)
        uniq_rows, inv = np.unique(go_left, axis=0, return_inverse=True)
        node_to_int = {int(nid): k for k, nid in enumerate(internal_ids)}
        uniq_phi = np.vstack([
            _treeshap_single_signature(nodes, dec, node_to_int, n_features) for dec in uniq_rows
        ])
        contribs += uniq_phi[inv]

    return contribs


# =============================================================================
# CONSTRUCCIÓN DE VECTOR R^28 E INFERENCIA INDIVIDUAL CON EXPLICACIÓN LOCAL
# =============================================================================

def build_household_dataframe_from_answers(answers: Dict[str, Any]) -> pd.DataFrame:
    """Convierte las respuestas normalizadas de la encuesta al DataFrame esperado por el Pipeline."""
    es_sec = bool(answers.get("es_hogar_secundario", False))

    n_miembros = max(1, int(answers["n_miembros"]))
    n_ninos_0_5 = int(np.clip(int(answers.get("n_ninos_0_5", 0)), 0, n_miembros))
    n_menores_14 = int(np.clip(int(answers.get("n_menores_14", n_ninos_0_5)), n_ninos_0_5, n_miembros))
    n_mayores_65 = int(np.clip(int(answers.get("n_mayores_65", 0)), 0, n_miembros - n_menores_14))

    activos = max(1, n_miembros - n_menores_14 - n_mayores_65)
    tasa_dep = float(n_menores_14 + n_mayores_65) / float(activos)

    n_ocupados = int(np.clip(int(answers.get("n_ocupados", 0)), 0, n_miembros))
    ocup_por_miembro = float(np.clip(n_ocupados / float(n_miembros), 0.0, 1.0))

    if es_sec:
        tipo_viv = np.nan
        mat_pared = np.nan
        mat_piso = np.nan
        tot_hab = np.nan
        tot_dorm = np.nan
        pers_por_hab = np.nan
    else:
        tot_hab = max(1.0, float(answers["total_habitaciones"]))
        tot_dorm = float(np.clip(float(answers.get("total_dormitorios", 1)), 0.0, tot_hab))
        tipo_viv = float(answers["tipo_vivienda"])
        mat_pared = float(answers["material_pared"])
        mat_piso = float(answers["material_piso"])
        pers_por_hab = float(n_miembros) / tot_hab

    fuente_agua = float(answers["fuente_agua"])
    agua_dias = (
        float(answers["agua_todos_los_dias"])
        if int(fuente_agua) in (1, 2, 3) and answers.get("agua_todos_los_dias") is not None
        else np.nan
    )

    comb_raw = answers.get("combustible_cocina")
    combustible = np.nan if comb_raw is None or int(comb_raw) == 8 else float(comb_raw)

    educ_jefe = float(answers["educ_jefe"])
    educ_max = max(educ_jefe, float(answers.get("educ_max_hogar", educ_jefe)))

    jefe_ocup = int(answers["jefe_ocupado"])
    if jefe_ocup == 1:
        horas_sem = max(0.0, float(answers.get("jefe_horas_semanales", 40.0)))
        cat_ocup = float(answers["jefe_cat_ocupacional"])
        emp_ruc = float(answers["jefe_empresa_ruc"])
    else:
        horas_sem = 0.0
        cat_ocup = 0.0
        emp_ruc = 0.0

    row = {
        "conglomerado": str(answers.get("conglomerado", "__nuevo_hogar__")),
        "ubigeo": str(answers.get("ubigeo", "__nuevo_distrito__")),
        # Numéricas (14)
        "total_habitaciones": tot_hab,
        "total_dormitorios": tot_dorm,
        "personas_por_hab": pers_por_hab,
        "n_miembros": float(n_miembros),
        "n_ninos_0_5": float(n_ninos_0_5),
        "n_menores_14": float(n_menores_14),
        "n_mayores_65": float(n_mayores_65),
        "tasa_dependencia": tasa_dep,
        "jefe_edad": float(answers["jefe_edad"]),
        "educ_jefe": educ_jefe,
        "educ_max_hogar": educ_max,
        "n_ocupados": float(n_ocupados),
        "ocupados_por_miembro": ocup_por_miembro,
        "jefe_horas_semanales": horas_sem,
        # Categóricas (14)
        "tipo_vivienda": tipo_viv,
        "material_pared": mat_pared,
        "material_piso": mat_piso,
        "tenencia_vivienda": float(answers["tenencia_vivienda"]),
        "fuente_agua": fuente_agua,
        "agua_todos_los_dias": agua_dias,
        "conexion_bano": float(answers["conexion_bano"]),
        "combustible_cocina": combustible,
        "tiene_internet": float(answers["tiene_internet"]),
        "jefe_mujer": float(answers["jefe_mujer"]),
        "jefe_ocupado": float(jefe_ocup),
        "jefe_cat_ocupacional": cat_ocup,
        "jefe_empresa_ruc": emp_ruc,
        "jefe_sin_pension": float(answers["jefe_sin_pension"]),
    }
    return pd.DataFrame([row])


def _explain_single_household(pipe_gbdt: Any, df_one: pd.DataFrame) -> pd.DataFrame:
    """Descompone en espacio log-odds las contribuciones de las 28 variables originales."""
    cleaner = pipe_gbdt.named_steps["cleaner"]
    preprocessor = pipe_gbdt.named_steps["preprocessor"]
    model = pipe_gbdt.named_steps["model"]

    x_clean = cleaner.transform(df_one)
    x_mat = preprocessor.transform(x_clean)
    feat_names = list(preprocessor.get_feature_names_out())

    contribs = _histgb_tree_contribs(model, x_mat)[0]
    raw_df = pd.DataFrame({
        "Variable": [_map_encoded_name_to_original(f) for f in feat_names],
        "Contribucion_LogOdds": contribs,
    })
    agg = (
        raw_df.groupby("Variable", as_index=False)["Contribucion_LogOdds"]
        .sum()
        .assign(Abs_Impact=lambda d: d["Contribucion_LogOdds"].abs())
        .sort_values("Abs_Impact", ascending=False)
        .reset_index(drop=True)
    )
    agg["Valor_Input"] = agg["Variable"].map(lambda c: x_clean.iloc[0][c] if c in x_clean.columns else np.nan)
    return agg[["Variable", "Valor_Input", "Contribucion_LogOdds"]]


def predict_single_household(
    bundle: Dict[str, Any],
    answers_or_df: Union[Dict[str, Any], pd.DataFrame],
    top_k_drivers: int = 5,
) -> Dict[str, Any]:
    """Evalúa un hogar encuestado usando el paquete ganador serializado."""
    df_one = (
        answers_or_df
        if isinstance(answers_or_df, pd.DataFrame)
        else build_household_dataframe_from_answers(answers_or_df)
    )

    prob_stack = float(bundle["pipe_stacking"].predict_proba(df_one)[:, 1][0])
    prob_gbdt = float(bundle["pipe_gbdt"].predict_proba(df_one)[:, 1][0])

    oof_sorted = bundle["oof_probs_sorted"]
    rank_idx = int(np.searchsorted(oof_sorted, prob_stack, side="right"))
    risk_percentile = 100.0 * rank_idx / max(1, len(oof_sorted))

    tau = float(bundle["tau_rec70"])
    cut_b20 = float(bundle["cutoff_b20"])
    contrib_df = _explain_single_household(bundle["pipe_gbdt"], df_one)

    risk_drivers = contrib_df[contrib_df["Contribucion_LogOdds"] > 0].head(top_k_drivers)
    protect_drivers = (
        contrib_df[contrib_df["Contribucion_LogOdds"] < 0]
        .sort_values("Contribucion_LogOdds", ascending=True)
        .head(top_k_drivers)
    )

    return {
        "prob_pobreza": prob_stack,
        "prob_gbdt": prob_gbdt,
        "percentil_riesgo_lima": risk_percentile,
        "tau_rec70": tau,
        "en_riesgo_tau": prob_stack >= tau,
        "cutoff_b20": cut_b20,
        "prioritario_top20": prob_stack >= cut_b20,
        "datos_procesados": df_one,
        "contribuciones_28": contrib_df,
        "factores_riesgo": risk_drivers,
        "factores_proteccion": protect_drivers,
    }
