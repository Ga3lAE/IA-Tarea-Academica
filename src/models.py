"""
Módulo de Modelado Supervisado y Validación Cruzada Espacial (Sprint 6).

Implementa la suite completa de modelos (5 principales del informe + familias extendidas
de la literatura PMT y Machine Learning tabular) bajo validación cruzada agrupada
`GroupKFold(n_splits=5)` por conglomerado censal sobre ENAHO 2024 (N = 4,090).

Optimizaciones de Concurrencia y Rendimiento:
1. Paralelismo multiproceso con `joblib.Parallel` (backend `loky`) tanto a nivel de candidatos
   en el benchmark como a nivel de pliegues en la validación cruzada repetida (30 corridas).
2. Control de hilos internos (`n_jobs=1` e `inner_max_num_threads=1` dentro de cada worker)
   para eliminar la contención de hilos (*oversubscription*).
3. Pre-cálculo por pliegue de las vistas preprocesadas (`robust_28`, `tree_28`, `viv_robust_11`,
   `viv_tree_11`) estrictamente dentro de `tr_idx` (cero fuga de datos), evitando repetir
   450+ veces la imputación por conglomerado y el One-Hot Encoding en un mismo fold.
"""
import sys
import time
import warnings
from pathlib import Path
from typing import Dict, List, Tuple, Optional, Any
import numpy as np
import pandas as pd
from joblib import Parallel, delayed, parallel_config

from sklearn.base import clone
from sklearn.model_selection import GroupKFold
from sklearn.metrics import (
    average_precision_score,
    roc_auc_score,
    brier_score_loss,
    precision_recall_curve,
)
from sklearn.linear_model import LogisticRegression, Ridge, QuantileRegressor
from sklearn.discriminant_analysis import LinearDiscriminantAnalysis
from sklearn.naive_bayes import GaussianNB
from sklearn.tree import DecisionTreeClassifier
from sklearn.ensemble import (
    RandomForestClassifier,
    ExtraTreesClassifier,
    HistGradientBoostingClassifier,
    AdaBoostClassifier,
    StackingClassifier,
)
from sklearn.svm import SVC
from sklearn.neighbors import KNeighborsClassifier
from sklearn.neural_network import MLPClassifier

_ROOT = Path(__file__).resolve().parents[1]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from src.preprocessing import (
    CANONICAL_FEATURES_28,
    NUMERIC_COLS,
    CATEGORICAL_COLS,
    VIVIENDA_NUMERIC_COLS,
    VIVIENDA_CATEGORICAL_COLS,
    VIVIENDA_FEATURES_12,
    TARGET_COL,
    GROUP_COL,
    SecondaryHouseholdImputer,
    build_preprocessor,
    build_full_pipeline,
    prepare_xy_data,
)

try:
    from lightgbm import LGBMClassifier
    HAS_LIGHTGBM = True
except Exception:
    LGBMClassifier = None
    HAS_LIGHTGBM = False

try:
    from xgboost import XGBClassifier
    HAS_XGBOOST = True
except Exception:
    XGBClassifier = None
    HAS_XGBOOST = False

try:
    from catboost import CatBoostClassifier
    HAS_CATBOOST = True
except Exception:
    CatBoostClassifier = None
    HAS_CATBOOST = False


# =============================================================================
# MÉTRICAS OPERATIVAS DE FOCALIZACIÓN SOCIAL (A COBERTURA FIJA Y UMBRAL)
# =============================================================================

def compute_targeting_metrics(
    y_true: np.ndarray,
    scores: np.ndarray,
    budget_coverage: float = 0.20,
    min_recall_target: float = 0.70,
) -> Dict[str, float]:
    """
    Calcula las métricas de desempeño canónicas sobre puntajes continuos o probabilidades:
    - PR-AUC y ROC-AUC
    - Error de Exclusión (EE = FN / (TP + FN)) y Error de Inclusión (IE = FP / (TP + FP))
      a cobertura presupuestal fija B = 20%
    - F1 máximo, Precisión máxima sujeta a Recall >= 0.70 y umbral óptimo tau* (para H3)
    - Puntaje de Brier (si los scores están en [0, 1])
    """
    y_arr = np.asarray(y_true, dtype=int)
    s_arr = np.asarray(scores, dtype=float)

    pr_auc = float(average_precision_score(y_arr, s_arr))
    roc_auc = float(roc_auc_score(y_arr, s_arr))

    n = len(y_arr)
    k = int(round(budget_coverage * n))
    top_idx = np.argsort(-s_arr)[:k]
    sel = np.zeros(n, dtype=bool)
    sel[top_idx] = True

    pobres = y_arr == 1
    tp_b = int((sel & pobres).sum())
    fp_b = int((sel & ~pobres).sum())
    fn_b = int((~sel & pobres).sum())

    ee_b20 = float(fn_b / max(1, tp_b + fn_b))
    ie_b20 = float(fp_b / max(1, tp_b + fp_b))

    prec, rec, thresh = precision_recall_curve(y_arr, s_arr)
    f1_vals = 2.0 * prec * rec / np.clip(prec + rec, 1e-9, None)
    best_f1_idx = int(np.argmax(f1_vals))
    f1_max = float(f1_vals[best_f1_idx])

    valid_r70 = np.where(rec[:-1] >= min_recall_target)[0]
    if len(valid_r70) > 0:
        best_r70_idx = int(valid_r70[np.argmax(prec[valid_r70])])
        prec_at_r70 = float(prec[best_r70_idx])
        rec_at_r70 = float(rec[best_r70_idx])
        tau_r70 = float(thresh[best_r70_idx])
    else:
        prec_at_r70 = 0.0
        rec_at_r70 = 0.0
        tau_r70 = 0.5

    s_prob = np.clip(s_arr, 0.0, 1.0)
    brier = float(brier_score_loss(y_arr, s_prob))

    return {
        "PR_AUC": pr_auc,
        "ROC_AUC": roc_auc,
        "EE_B20": ee_b20,
        "IE_B20": ie_b20,
        "F1_Max": f1_max,
        "Prec_at_Rec70": prec_at_r70,
        "Rec_at_Rec70": rec_at_r70,
        "Tau_Rec70": tau_r70,
        "Brier": brier,
    }


def _calibrate_continuous_score_to_prob(
    neg_lngpc_train: np.ndarray,
    y_train: np.ndarray,
    neg_lngpc_eval: np.ndarray,
) -> np.ndarray:
    """
    Transforma el puntaje continuo (-ln_gasto_predicho) de PMT-MCO o PMT-Cuantílico
    en una probabilidad calibrada en [0, 1] mediante escalamiento logístico univariado
    ajustado únicamente en el pliegue de entrenamiento.
    """
    cal = LogisticRegression()
    cal.fit(neg_lngpc_train.reshape(-1, 1), y_train)
    return cal.predict_proba(neg_lngpc_eval.reshape(-1, 1))[:, 1]


# =============================================================================
# PRE-CÁLCULO ANTI-FUGA DE VISTAS POR PLIEGUE Y EVALUACIÓN CV
# =============================================================================

def _build_fold_view_dict(
    X_full: pd.DataFrame,
    X_viv: pd.DataFrame,
    y_arr: np.ndarray,
    y_lngpc_arr: np.ndarray,
    tr_idx: np.ndarray,
    val_idx: np.ndarray,
) -> Dict[str, Any]:
    """
    Ajusta los transformadores anti-fuga una única vez sobre `tr_idx` y genera las
    4 vistas de matrices listas para todos los modelos en ese pliegue:
    - 'robust_28': 28 vars con RobustScaler + OneHotEncoder
    - 'tree_28':   28 vars sin escalado + OneHotEncoder
    - 'viv_robust_11': 11 vars M01 con RobustScaler + OneHotEncoder
    - 'viv_tree_11':   11 vars M01 sin escalado + OneHotEncoder
    """
    # 1. Limpiador de hogares secundarios en 28 variables
    cl_full = SecondaryHouseholdImputer()
    X_tr_clean = cl_full.fit_transform(X_full.iloc[tr_idx])
    X_val_clean = cl_full.transform(X_full.iloc[val_idx])

    prep_rob28 = build_preprocessor(scale_numeric=True, scaler_type="robust", one_hot=True)
    prep_tree28 = build_preprocessor(scale_numeric=False, scaler_type="none", one_hot=True)

    # 2. Limpiador en 11 variables de Vivienda (M01)
    cl_viv = SecondaryHouseholdImputer()
    X_viv_tr_clean = cl_viv.fit_transform(X_viv.iloc[tr_idx])
    X_viv_val_clean = cl_viv.transform(X_viv.iloc[val_idx])

    prep_rob11 = build_preprocessor(
        numeric_cols=VIVIENDA_NUMERIC_COLS,
        categorical_cols=VIVIENDA_CATEGORICAL_COLS,
        scale_numeric=True,
        scaler_type="robust",
        one_hot=True,
    )
    prep_tree11 = build_preprocessor(
        numeric_cols=VIVIENDA_NUMERIC_COLS,
        categorical_cols=VIVIENDA_CATEGORICAL_COLS,
        scale_numeric=False,
        scaler_type="none",
        one_hot=True,
    )

    return {
        "tr_idx": tr_idx,
        "val_idx": val_idx,
        "y_tr": y_arr[tr_idx],
        "y_val": y_arr[val_idx],
        "y_lngpc_tr": y_lngpc_arr[tr_idx],
        "robust_28": (prep_rob28.fit_transform(X_tr_clean), prep_rob28.transform(X_val_clean)),
        "tree_28": (prep_tree28.fit_transform(X_tr_clean), prep_tree28.transform(X_val_clean)),
        "viv_robust_11": (prep_rob11.fit_transform(X_viv_tr_clean), prep_rob11.transform(X_viv_val_clean)),
        "viv_tree_11": (prep_tree11.fit_transform(X_viv_tr_clean), prep_tree11.transform(X_viv_val_clean)),
    }


def _fit_predict_on_fold_view(
    estimator,
    fold_view: Dict[str, Any],
    view_key: str,
    is_continuous_pmt: bool,
) -> np.ndarray:
    """Ajusta un estimador sobre la vista precomputada del fold y retorna probabilidades en validación."""
    est = clone(estimator)
    X_tr_mat, X_val_mat = fold_view[view_key]
    y_tr = fold_view["y_tr"]

    if is_continuous_pmt:
        y_c_tr = fold_view["y_lngpc_tr"]
        est.fit(X_tr_mat, y_c_tr)
        neg_tr = -est.predict(X_tr_mat)
        neg_val = -est.predict(X_val_mat)
        return _calibrate_continuous_score_to_prob(neg_tr, y_tr, neg_val)

    est.fit(X_tr_mat, y_tr)
    return est.predict_proba(X_val_mat)[:, 1]


def evaluate_pipeline_cv(
    pipe,
    X: pd.DataFrame,
    y: pd.Series,
    groups: pd.Series,
    n_splits: int = 5,
    is_continuous_pmt: bool = False,
    y_continuous: Optional[pd.Series] = None,
) -> Tuple[np.ndarray, Dict[str, float], List[Dict[str, float]]]:
    """
    Ejecuta validación cruzada espacial GroupKFold(n_splits=5) para un Pipeline arbitrario.
    """
    gkf = GroupKFold(n_splits=n_splits)
    oof_probs = np.zeros(len(y), dtype=float)
    fold_metrics = []

    y_arr = y.values
    grp_arr = groups.values
    y_cont_arr = y_continuous.values if y_continuous is not None else None

    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        for fold_idx, (tr_idx, val_idx) in enumerate(gkf.split(X, y_arr, grp_arr), start=1):
            model_fold = clone(pipe)
            X_f_tr, X_f_val = X.iloc[tr_idx], X.iloc[val_idx]
            y_f_tr, y_f_val = y_arr[tr_idx], y_arr[val_idx]

            if is_continuous_pmt:
                y_c_tr = y_cont_arr[tr_idx]
                model_fold.fit(X_f_tr, y_c_tr)
                neg_pred_tr = -model_fold.predict(X_f_tr)
                neg_pred_val = -model_fold.predict(X_f_val)
                probs_val = _calibrate_continuous_score_to_prob(neg_pred_tr, y_f_tr, neg_pred_val)
            else:
                model_fold.fit(X_f_tr, y_f_tr)
                probs_val = model_fold.predict_proba(X_f_val)[:, 1]

            oof_probs[val_idx] = probs_val
            m_fold = compute_targeting_metrics(y_f_val, probs_val)
            m_fold["fold"] = fold_idx
            fold_metrics.append(m_fold)

    oof_summary = compute_targeting_metrics(y_arr, oof_probs)
    oof_summary["PR_AUC_Fold_Mean"] = float(np.mean([m["PR_AUC"] for m in fold_metrics]))
    oof_summary["PR_AUC_Fold_Std"] = float(np.std([m["PR_AUC"] for m in fold_metrics], ddof=1))
    oof_summary["EE_B20_Fold_Mean"] = float(np.mean([m["EE_B20"] for m in fold_metrics]))
    oof_summary["EE_B20_Fold_Std"] = float(np.std([m["EE_B20"] for m in fold_metrics], ddof=1))

    return oof_probs, oof_summary, fold_metrics


# =============================================================================
# COMPARATIVA DE ESCALADORES DENTRO DEL K-FOLD (ROBUST VS STANDARD VS MINMAX)
# =============================================================================

def compare_scalers_cv(
    df_train: pd.DataFrame,
    n_splits: int = 5,
    n_jobs: int = -1,
) -> pd.DataFrame:
    """
    Verifica empíricamente en GroupKFold(5) sobre ENAHO 2024 el efecto del escalador
    numérico interno al fold ('robust', 'standard', 'minmax') en paralelo.
    """
    X, y, groups = prepare_xy_data(df_train, features=CANONICAL_FEATURES_28)
    gamma = float((y == 0).sum() / (y == 1).sum())
    w_bal = {0: 1.0, 1: gamma}

    tasks = []
    for sc_type in ("robust", "standard", "minmax"):
        for model_label, est in [
            ("Logística ElasticNet", LogisticRegression(
                solver="saga", l1_ratio=0.5, C=0.2,
                class_weight=w_bal, max_iter=1500, random_state=42
            )),
            ("MLP Red Neuronal", MLPClassifier(
                hidden_layer_sizes=(64, 32), alpha=0.1, early_stopping=True,
                max_iter=300, random_state=42
            )),
            ("KNN (k=25)", KNeighborsClassifier(n_neighbors=25, weights="distance", n_jobs=1)),
        ]:
            tasks.append((sc_type, model_label, est))

    def _run_one(sc_type, model_label, est):
        pipe = build_full_pipeline(est, scale_numeric=True, scaler_type=sc_type, one_hot=True)
        _, summary, _ = evaluate_pipeline_cv(pipe, X, y, groups, n_splits=n_splits)
        return {
            "Modelo": model_label,
            "Escalador_Interno": sc_type,
            "PR_AUC_OOF": round(summary["PR_AUC"], 4),
            "PR_AUC_Mean": round(summary["PR_AUC_Fold_Mean"], 4),
            "PR_AUC_Std": round(summary["PR_AUC_Fold_Std"], 4),
            "ROC_AUC_OOF": round(summary["ROC_AUC"], 4),
            "EE_B20_OOF": round(summary["EE_B20"], 4),
        }

    with parallel_config(backend="loky", inner_max_num_threads=1):
        rows = Parallel(n_jobs=n_jobs)(delayed(_run_one)(s, m, e) for s, m, e in tasks)
    return pd.DataFrame(rows)


# =============================================================================
# CATÁLOGO DE MODELOS (CON n_jobs=1 INTERNO PARA PARALELISMO EXTERNO LIMPIO)
# =============================================================================

def _make_gbdt_estimator(
    alpha_weight: float,
    learning_rate: float = 0.05,
    num_leaves: int = 15,
    min_child: int = 30,
    n_jobs: int = 1,
):
    if HAS_LIGHTGBM:
        return LGBMClassifier(
            n_estimators=250,
            learning_rate=learning_rate,
            num_leaves=num_leaves,
            min_child_samples=min_child,
            subsample=0.8,
            colsample_bytree=0.8,
            reg_alpha=1.0,
            reg_lambda=1.0,
            scale_pos_weight=alpha_weight,
            random_state=42,
            n_jobs=n_jobs,
            verbose=-1,
        )
    return HistGradientBoostingClassifier(
        max_iter=250,
        learning_rate=learning_rate,
        max_leaf_nodes=num_leaves,
        min_samples_leaf=min_child,
        l2_regularization=1.0,
        class_weight={0: 1.0, 1: alpha_weight},
        random_state=42,
    )


def build_candidate_registry(gamma: float) -> List[Dict[str, Any]]:
    """
    Define el registro completo de las 99 configuraciones candidatas de los 19 modelos (8 familias).
    Cada candidato especifica su `view_key` ('robust_28', 'tree_28', 'viv_robust_11', 'viv_tree_11')
    y su `estimator` con `n_jobs=1` para permitir paralelismo multiproceso externo sin contención.
    """
    alphas = [1.0, 2.0, round(gamma, 4)]
    candidates: List[Dict[str, Any]] = []

    def _add(name, family, config_desc, alpha, is_cont, features, view_key, est, scale_num, sc_type):
        num_c = VIVIENDA_NUMERIC_COLS if len(features) == len(VIVIENDA_FEATURES_12) else NUMERIC_COLS
        cat_c = VIVIENDA_CATEGORICAL_COLS if len(features) == len(VIVIENDA_FEATURES_12) else CATEGORICAL_COLS
        candidates.append({
            "name": name,
            "family": family,
            "config_desc": config_desc,
            "alpha": alpha,
            "is_continuous_pmt": is_cont,
            "features": features,
            "view_key": view_key,
            "estimator": est,
            "pipe": build_full_pipeline(
                est,
                numeric_cols=num_c,
                categorical_cols=cat_c,
                scale_numeric=scale_num,
                scaler_type=sc_type,
                one_hot=True,
            ),
        })

    # 1. Baselines de Representación Solo Vivienda (M01, 11 vars) -> H1
    for a in alphas:
        est = LogisticRegression(
            solver="saga", C=0.5, l1_ratio=0.5,
            class_weight={0: 1.0, 1: a}, max_iter=1500, random_state=42
        )
        _add("Logistica_Solo_Vivienda", "01_Baseline_Vivienda (H1)", f"C=0.5, l1=0.5, alpha={a:.2f}",
             a, False, VIVIENDA_FEATURES_12, "viv_robust_11", est, True, "robust")

    est_rf_viv = RandomForestClassifier(
        n_estimators=300, max_depth=8, min_samples_leaf=15,
        class_weight={0: 1.0, 1: gamma}, n_jobs=1, random_state=42
    )
    _add("RF_Solo_Vivienda", "01_Baseline_Vivienda (H1)", f"n=300, max_depth=8, min_leaf=15, alpha={gamma:.2f}",
         round(gamma, 4), False, VIVIENDA_FEATURES_12, "viv_tree_11", est_rf_viv, False, "none")

    # 2. Familia Econométrica PMT Continua (ln(gasto) en R^28, regresión lineal regularizada Ridge)
    for ridge_a in [1e-4, 1.0, 10.0]:
        _add("PMT_MCO", "02_Econometrico_PMT", f"OLS/Ridge(alpha={ridge_a}) sobre ln(gasto)",
             1.0, True, CANONICAL_FEATURES_28, "robust_28", Ridge(alpha=ridge_a, random_state=42), True, "robust")

    _add("PMT_Quantile_20", "02_Econometrico_PMT", "QuantileRegressor(q=0.20, alpha=0.01) sobre ln(gasto)",
         1.0, True, CANONICAL_FEATURES_28, "robust_28",
         QuantileRegressor(quantile=0.20, alpha=0.01, solver="highs"), True, "robust")

    # 3. Familia Lineal y Generativa (R^28, RobustScaler)
    for a in alphas:
        for c_val in [0.05, 0.2, 1.0]:
            for l1_val in [0.0, 0.5, 1.0]:
                est = LogisticRegression(
                    solver="saga", C=c_val, l1_ratio=l1_val,
                    class_weight={0: 1.0, 1: a}, max_iter=1500, random_state=42
                )
                _add("Logistica_ElasticNet", "03_Lineal_Regularizado",
                     f"C={c_val}, l1_ratio={l1_val}, alpha={a:.2f}",
                     a, False, CANONICAL_FEATURES_28, "robust_28", est, True, "robust")

    _add("LDA", "03_Lineal_Generativo", "LinearDiscriminantAnalysis(solver='lsqr', shrinkage='auto')",
         1.0, False, CANONICAL_FEATURES_28, "robust_28",
         LinearDiscriminantAnalysis(solver="lsqr", shrinkage="auto"), True, "robust")

    _add("Naive_Bayes", "03_Lineal_Generativo", "GaussianNB(var_smoothing=1e-2)",
         1.0, False, CANONICAL_FEATURES_28, "robust_28",
         GaussianNB(var_smoothing=1e-2), True, "robust")

    # 4. Familia Árboles y Bagging (R^28, sin escalado)
    for a in alphas:
        for ccp in [0.001, 0.003, 0.006]:
            est = DecisionTreeClassifier(
                max_depth=6, min_samples_leaf=25, ccp_alpha=ccp,
                class_weight={0: 1.0, 1: a}, random_state=42
            )
            _add("CART_Podado", "04_Arbol_Individual",
                 f"max_depth=6, min_leaf=25, ccp_alpha={ccp}, alpha={a:.2f}",
                 a, False, CANONICAL_FEATURES_28, "tree_28", est, False, "none")

    for a in alphas:
        for depth in [8, 12]:
            for min_leaf in [10, 20]:
                est = RandomForestClassifier(
                    n_estimators=400, max_depth=depth, min_samples_leaf=min_leaf,
                    class_weight={0: 1.0, 1: a}, n_jobs=1, random_state=42
                )
                _add("Random_Forest", "05_Ensamble_Bagging",
                     f"n=400, max_depth={depth}, min_leaf={min_leaf}, alpha={a:.2f}",
                     a, False, CANONICAL_FEATURES_28, "tree_28", est, False, "none")

    for a in [1.0, round(gamma, 4)]:
        est = ExtraTreesClassifier(
            n_estimators=400, max_depth=12, min_samples_leaf=10,
            class_weight={0: 1.0, 1: a}, n_jobs=1, random_state=42
        )
        _add("Extra_Trees", "05_Ensamble_Bagging",
             f"n=400, max_depth=12, min_leaf=10, alpha={a:.2f}",
             a, False, CANONICAL_FEATURES_28, "tree_28", est, False, "none")

    # 5. Familia Gradient Boosting (R^28, sin escalado, algoritmos explícitos separados sin enmascarar)
    if HAS_LIGHTGBM:
        for a in alphas:
            for lr in [0.03, 0.05]:
                for leaves in [15, 25]:
                    est = LGBMClassifier(
                        n_estimators=250,
                        learning_rate=lr,
                        num_leaves=leaves,
                        min_child_samples=30,
                        subsample=0.8,
                        colsample_bytree=0.8,
                        reg_alpha=1.0,
                        reg_lambda=1.0,
                        scale_pos_weight=a,
                        random_state=42,
                        n_jobs=1,
                        verbose=-1,
                    )
                    _add("LightGBM_GBDT", "06_Ensamble_Boosting",
                         f"LightGBM(lr={lr}, leaves={leaves}, alpha={a:.2f})",
                         a, False, CANONICAL_FEATURES_28, "tree_28", est, False, "none")

    if HAS_XGBOOST:
        for a in alphas:
            for md, lr in [(3, 0.05), (4, 0.03), (5, 0.03)]:
                est_xgb = XGBClassifier(
                    n_estimators=250,
                    max_depth=md,
                    learning_rate=lr,
                    subsample=0.8,
                    colsample_bytree=0.8,
                    reg_alpha=1.0,
                    reg_lambda=5.0,
                    scale_pos_weight=a,
                    eval_metric="logloss",
                    random_state=42,
                    n_jobs=1,
                )
                _add("XGBoost_GBDT", "06_Ensamble_Boosting",
                     f"XGBoost(depth={md}, lr={lr}, alpha={a:.2f})",
                     a, False, CANONICAL_FEATURES_28, "tree_28", est_xgb, False, "none")

    if HAS_CATBOOST:
        for a in alphas:
            for md, lr in [(4, 0.05), (6, 0.03)]:
                est_cat = CatBoostClassifier(
                    iterations=250,
                    depth=md,
                    learning_rate=lr,
                    l2_leaf_reg=5.0,
                    scale_pos_weight=float(a),
                    random_seed=42,
                    thread_count=1,
                    verbose=0,
                    allow_writing_files=False,
                )
                _add("CatBoost_GBDT", "06_Ensamble_Boosting",
                     f"CatBoost(depth={md}, lr={lr}, alpha={a:.2f})",
                     a, False, CANONICAL_FEATURES_28, "tree_28", est_cat, False, "none")

    for a in alphas:
        for lr, leaves in [(0.03, 15), (0.05, 25)]:
            est_hgb = HistGradientBoostingClassifier(
                max_iter=250,
                learning_rate=lr,
                max_leaf_nodes=leaves,
                min_samples_leaf=30,
                l2_regularization=1.0,
                class_weight={0: 1.0, 1: a},
                random_state=42,
            )
            _add("HistGBDT_Sklearn", "06_Ensamble_Boosting",
                 f"HistGBDT(lr={lr}, leaves={leaves}, alpha={a:.2f})",
                 a, False, CANONICAL_FEATURES_28, "tree_28", est_hgb, False, "none")

    est_ada = AdaBoostClassifier(
        estimator=DecisionTreeClassifier(max_depth=2, min_samples_leaf=20, random_state=42),
        n_estimators=150, learning_rate=0.1, random_state=42
    )
    _add("AdaBoost", "06_Ensamble_Boosting", "AdaBoost(n=150, lr=0.1, base=CART_depth2)",
         1.0, False, CANONICAL_FEATURES_28, "tree_28", est_ada, False, "none")

    # 6. Familia Kernels, Vecindad y Redes Neuronales (RobustScaler)
    for a in [1.0, 2.0]:
        est = SVC(kernel="rbf", C=1.0, probability=True, class_weight={0: 1.0, 1: a}, random_state=42)
        _add("SVM_RBF", "07_NoLineal_Kernel_NN", f"SVC(kernel='rbf', C=1.0, alpha={a:.2f})",
             a, False, CANONICAL_FEATURES_28, "robust_28", est, True, "robust")

    _add("KNN", "07_NoLineal_Kernel_NN", "KNeighbors(k=35, weights='distance')",
         1.0, False, CANONICAL_FEATURES_28, "robust_28",
         KNeighborsClassifier(n_neighbors=35, weights="distance", n_jobs=1), True, "robust")

    _add("MLP_Red_Neuronal", "07_NoLineal_Kernel_NN", "MLP(hidden=(64, 32), alpha_l2=0.5, early_stopping=True)",
         1.0, False, CANONICAL_FEATURES_28, "robust_28",
         MLPClassifier(
             hidden_layer_sizes=(64, 32), alpha=0.5, learning_rate_init=0.005,
             early_stopping=True, max_iter=300, random_state=42
         ), True, "robust")

    # 7. Meta-Ensamble (Stacking Multifamilia)
    stack_est = StackingClassifier(
        estimators=[
            ("lr", LogisticRegression(solver="saga", C=0.2, l1_ratio=0.5, max_iter=1200, random_state=42)),
            ("rf", RandomForestClassifier(n_estimators=300, max_depth=10, min_samples_leaf=15, n_jobs=1, random_state=42)),
            ("et", ExtraTreesClassifier(n_estimators=300, max_depth=12, min_samples_leaf=15, n_jobs=1, random_state=42)),
            ("gb", _make_gbdt_estimator(alpha_weight=1.0, learning_rate=0.03, num_leaves=15, min_child=30, n_jobs=1)),
        ],
        final_estimator=LogisticRegression(C=1.0, random_state=42),
        cv=3,
        n_jobs=1,
    )
    _add("Stacking_Ensemble", "08_Meta_Ensamble", "Stacking(ElasticNet + RF + ExtraTrees + GBDT -> Logit)",
         1.0, False, CANONICAL_FEATURES_28, "robust_28", stack_est, True, "robust")

    return candidates


def _evaluate_candidate_on_precomputed_folds(
    cand: Dict[str, Any],
    fold_views: List[Dict[str, Any]],
    y_arr: np.ndarray,
) -> Dict[str, Any]:
    """Worker paralelo que evalúa un candidato sobre las vistas ya precomputadas de los K folds."""
    oof_probs = np.zeros(len(y_arr), dtype=float)
    fold_list = []

    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        for fold_idx, fv in enumerate(fold_views, start=1):
            probs_val = _fit_predict_on_fold_view(
                cand["estimator"],
                fv,
                view_key=cand["view_key"],
                is_continuous_pmt=cand["is_continuous_pmt"],
            )
            oof_probs[fv["val_idx"]] = probs_val
            m_fold = compute_targeting_metrics(fv["y_val"], probs_val)
            m_fold["fold"] = fold_idx
            fold_list.append(m_fold)

    summary = compute_targeting_metrics(y_arr, oof_probs)
    summary["PR_AUC_Fold_Mean"] = float(np.mean([m["PR_AUC"] for m in fold_list]))
    summary["PR_AUC_Fold_Std"] = float(np.std([m["PR_AUC"] for m in fold_list], ddof=1))
    summary["EE_B20_Fold_Mean"] = float(np.mean([m["EE_B20"] for m in fold_list]))
    summary["EE_B20_Fold_Std"] = float(np.std([m["EE_B20"] for m in fold_list], ddof=1))

    row = {
        "Modelo": cand["name"],
        "Familia": cand["family"],
        "Configuracion": cand["config_desc"],
        "Alpha_Costo": cand["alpha"],
        "N_Vars_Base": len(cand["features"]),
        "PR_AUC_OOF": summary["PR_AUC"],
        "PR_AUC_Mean": summary["PR_AUC_Fold_Mean"],
        "PR_AUC_Std": summary["PR_AUC_Fold_Std"],
        "ROC_AUC_OOF": summary["ROC_AUC"],
        "EE_B20_OOF": summary["EE_B20"],
        "IE_B20_OOF": summary["IE_B20"],
        "F1_Max_OOF": summary["F1_Max"],
        "Prec_at_Rec70_OOF": summary["Prec_at_Rec70"],
        "Tau_Rec70_2024": summary["Tau_Rec70"],
        "Brier_OOF": summary["Brier"],
    }
    return {
        "cand": cand,
        "oof_probs": oof_probs,
        "metrics_cv": summary,
        "fold_metrics": fold_list,
        "row": row,
    }


def run_spatial_cv_benchmark(
    df_train: pd.DataFrame,
    n_splits: int = 5,
    n_jobs: int = -1,
    verbose: bool = True,
) -> Tuple[pd.DataFrame, pd.DataFrame, Dict[str, Dict[str, Any]]]:
    """
    Ejecuta en paralelo la búsqueda de hiperparámetros/alpha y comparación de modelos bajo
    GroupKFold(n_splits=5) por conglomerado censal en ENAHO 2024 (N = 4,090).
    """
    t0 = time.perf_counter()
    X_full, y, groups = prepare_xy_data(df_train, features=CANONICAL_FEATURES_28)
    X_viv, _, _ = prepare_xy_data(df_train, features=VIVIENDA_FEATURES_12)
    y_arr = y.values
    y_lngpc_arr = df_train["lngpc"].values
    grp_arr = groups.values

    gamma = float((y_arr == 0).sum() / (y_arr == 1).sum())
    candidates = build_candidate_registry(gamma=gamma)

    if verbose:
        print(
            f"[run_spatial_cv_benchmark] Pre-calculando vistas de {n_splits} pliegues y evaluando "
            f"{len(candidates)} configuraciones en paralelo (n_jobs={n_jobs})..."
        )

    gkf = GroupKFold(n_splits=n_splits)
    splits = list(gkf.split(X_full, y_arr, grp_arr))

    with parallel_config(backend="loky", inner_max_num_threads=1):
        fold_views = Parallel(n_jobs=n_jobs)(
            delayed(_build_fold_view_dict)(X_full, X_viv, y_arr, y_lngpc_arr, tr_idx, val_idx)
            for tr_idx, val_idx in splits
        )
        results = Parallel(n_jobs=n_jobs)(
            delayed(_evaluate_candidate_on_precomputed_folds)(cand, fold_views, y_arr)
            for cand in candidates
        )

    all_rows = [r["row"] for r in results]
    best_by_name: Dict[str, Dict[str, Any]] = {}
    for res in results:
        name = res["cand"]["name"]
        if (name not in best_by_name) or (res["metrics_cv"]["PR_AUC"] > best_by_name[name]["metrics_cv"]["PR_AUC"]):
            best_by_name[name] = res

    # Reentrenar en paralelo los 19 modelos ganadores sobre el 100% de ENAHO 2024
    def _fit_winner(name: str, info: Dict[str, Any]):
        cand = info["cand"]
        X_in = X_viv if len(cand["features"]) == len(VIVIENDA_FEATURES_12) else X_full
        final_pipe = clone(cand["pipe"])
        calibrator = None
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            if cand["is_continuous_pmt"]:
                final_pipe.fit(X_in, y_lngpc_arr)
                neg_pred_full = -final_pipe.predict(X_in)
                calibrator = LogisticRegression()
                calibrator.fit(neg_pred_full.reshape(-1, 1), y_arr)
            else:
                final_pipe.fit(X_in, y_arr)
        return name, {
            "pipe": final_pipe,
            "estimator": cand["estimator"],
            "view_key": cand["view_key"],
            "calibrator": calibrator,
            "is_continuous_pmt": cand["is_continuous_pmt"],
            "features": cand["features"],
            "family": cand["family"],
            "config_desc": cand["config_desc"],
            "alpha": cand["alpha"],
            "oof_probs": info["oof_probs"],
            "metrics_cv": info["metrics_cv"],
            "fold_metrics": info["fold_metrics"],
        }

    with parallel_config(backend="loky", inner_max_num_threads=1):
        fitted_pairs = Parallel(n_jobs=n_jobs)(
            delayed(_fit_winner)(name, info) for name, info in best_by_name.items()
        )
    fitted_best_artifacts = dict(fitted_pairs)

    all_configs_df = pd.DataFrame(all_rows).sort_values(by=["Modelo", "PR_AUC_OOF"], ascending=[True, False]).reset_index(drop=True)
    best_models_df = (
        pd.DataFrame([v["row"] for v in best_by_name.values()])
        .sort_values(by="PR_AUC_OOF", ascending=False)
        .reset_index(drop=True)
    )

    elapsed = time.perf_counter() - t0
    if verbose:
        print(f"✓ Benchmark CV 2024 completado en {elapsed:.2f} s ({len(best_models_df)} modelos únicos seleccionados).")

    return best_models_df, all_configs_df, fitted_best_artifacts


def predict_poverty_probs(
    artifact: Dict[str, Any],
    df_eval: pd.DataFrame,
) -> np.ndarray:
    """
    Genera probabilidades predichas sobre cualquier conjunto de evaluación (ej. Test OOT 2025)
    usando el artefacto entrenado exclusivamente en 2024.
    """
    X_eval, _, _ = prepare_xy_data(df_eval, features=artifact["features"])
    pipe = artifact["pipe"]
    if artifact["is_continuous_pmt"]:
        neg_pred = -pipe.predict(X_eval)
        return artifact["calibrator"].predict_proba(neg_pred.reshape(-1, 1))[:, 1]
    return pipe.predict_proba(X_eval)[:, 1]


def extract_cv_folds_dataframe(
    fitted_artifacts: Dict[str, Dict[str, Any]],
) -> pd.DataFrame:
    """
    Extrae las métricas de cada uno de los 5 folds para todos los modelos ganadores
    en formato largo.
    """
    rows = []
    for name, art in fitted_artifacts.items():
        for fm in art["fold_metrics"]:
            rows.append({
                "Modelo": name,
                "Familia": art["family"],
                "Fold": fm["fold"],
                "PR_AUC": fm["PR_AUC"],
                "ROC_AUC": fm["ROC_AUC"],
                "EE_B20": fm["EE_B20"],
                "IE_B20": fm["IE_B20"],
                "F1_Max": fm["F1_Max"],
                "Prec_at_Rec70": fm["Prec_at_Rec70"],
                "Brier": fm["Brier"],
            })
    return pd.DataFrame(rows)


def _evaluate_one_split_all_models(
    rep: int,
    run_id: int,
    tr_idx: np.ndarray,
    val_idx: np.ndarray,
    X_full: pd.DataFrame,
    X_viv: pd.DataFrame,
    y_arr: np.ndarray,
    y_lngpc_arr: np.ndarray,
    model_specs: List[Dict[str, Any]],
) -> List[Dict[str, Any]]:
    """
    Worker paralelo para un pliegue espacial `(rep, run_id)`:
    1. Calcula una sola vez las 4 vistas preprocesadas del pliegue.
    2. Entrena y evalúa los 19 modelos ganadores sobre esas vistas.
    """
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        fv = _build_fold_view_dict(X_full, X_viv, y_arr, y_lngpc_arr, tr_idx, val_idx)
        out = []
        for spec in model_specs:
            probs_val = _fit_predict_on_fold_view(
                spec["estimator"],
                fv,
                view_key=spec["view_key"],
                is_continuous_pmt=spec["is_continuous_pmt"],
            )
            m = compute_targeting_metrics(fv["y_val"], probs_val)
            out.append({
                "Modelo": spec["name"],
                "Familia": spec["family"],
                "Repeticion": rep,
                "Fold": run_id,
                "PR_AUC": m["PR_AUC"],
                "ROC_AUC": m["ROC_AUC"],
                "EE_B20": m["EE_B20"],
                "IE_B20": m["IE_B20"],
                "F1_Max": m["F1_Max"],
                "Prec_at_Rec70": m["Prec_at_Rec70"],
                "Brier": m["Brier"],
            })
        return out


def run_repeated_spatial_cv(
    fitted_artifacts: Dict[str, Dict[str, Any]],
    df_train: pd.DataFrame,
    n_splits: int = 5,
    n_repeats: int = 6,
    random_state: int = 42,
    n_jobs: int = -1,
    verbose: bool = True,
) -> pd.DataFrame:
    """
    Ejecuta en paralelo Validación Cruzada Espacial Repetida (Repeated GroupKFold:
    n_repeats x n_splits = 30 corridas por modelo) permutando aleatoriamente los 704
    conglomerados censales en cada repetición.
    """
    t0 = time.perf_counter()
    X_full, y, groups = prepare_xy_data(df_train, features=CANONICAL_FEATURES_28)
    X_viv, _, _ = prepare_xy_data(df_train, features=VIVIENDA_FEATURES_12)
    y_arr = y.values
    y_lngpc_arr = df_train["lngpc"].values
    grp_arr = groups.values

    unique_groups = np.unique(grp_arr)
    rng = np.random.default_rng(random_state)

    # Extraer especificaciones ligeras de los 19 modelos ganadores
    model_specs = []
    for name, art in fitted_artifacts.items():
        est = art.get("estimator", art["pipe"].named_steps["model"])
        vkey = art.get("view_key")
        if vkey is None:
            is_viv = len(art["features"]) == len(VIVIENDA_FEATURES_12)
            has_scaler = "scaler" in art["pipe"].named_steps["preprocessor"].named_transformers_["num"].named_steps
            vkey = ("viv_robust_11" if has_scaler else "viv_tree_11") if is_viv else ("robust_28" if has_scaler else "tree_28")
        model_specs.append({
            "name": name,
            "family": art["family"],
            "estimator": est,
            "view_key": vkey,
            "is_continuous_pmt": art["is_continuous_pmt"],
        })

    split_tasks = []
    for rep in range(1, n_repeats + 1):
        perm_groups = rng.permutation(unique_groups)
        group_to_fold = {g: (i % n_splits) for i, g in enumerate(perm_groups)}
        fold_assignment = np.array([group_to_fold[g] for g in grp_arr])

        for fold_idx in range(n_splits):
            run_id = (rep - 1) * n_splits + (fold_idx + 1)
            val_mask = fold_assignment == fold_idx
            tr_idx = np.where(~val_mask)[0]
            val_idx = np.where(val_mask)[0]
            split_tasks.append((rep, run_id, tr_idx, val_idx))

    total_runs = len(split_tasks)
    if verbose:
        print(
            f"[run_repeated_spatial_cv] Ejecutando en paralelo {total_runs} pliegues espaciales "
            f"x {len(model_specs)} modelos = {total_runs * len(model_specs)} evaluaciones (n_jobs={n_jobs})..."
        )

    with parallel_config(backend="loky", inner_max_num_threads=1):
        nested_rows = Parallel(n_jobs=n_jobs)(
            delayed(_evaluate_one_split_all_models)(
                rep, run_id, tr_idx, val_idx, X_full, X_viv, y_arr, y_lngpc_arr, model_specs
            )
            for rep, run_id, tr_idx, val_idx in split_tasks
        )

    rows = [item for sublist in nested_rows for item in sublist]
    elapsed = time.perf_counter() - t0
    if verbose:
        print(f"✓ Validación cruzada repetida completada en {elapsed:.2f} s ({len(rows):,d} evaluaciones generadas).")
    return pd.DataFrame(rows)


def rank_models_by_folds(
    folds_df: pd.DataFrame,
    best_models_df: pd.DataFrame,
) -> pd.DataFrame:
    """
    Construye el ranking estadístico de los modelos combinando métricas OOF,
    estadísticos de los Boxplots (Mediana, IQR, Media, DE), Rango Promedio
    por corrida (Friedman) y p-valor de Wilcoxon pareado frente al modelo #1.
    """
    from scipy.stats import wilcoxon

    df_f = folds_df.copy()
    df_f["Rank_PR_Fold"] = df_f.groupby("Fold")["PR_AUC"].rank(ascending=False, method="min")
    df_f["Rank_EE_Fold"] = df_f.groupby("Fold")["EE_B20"].rank(ascending=True, method="min")

    grp = df_f.groupby("Modelo")
    stats = pd.DataFrame({
        "N_Corridas": grp["PR_AUC"].count(),
        "PR_AUC_Mediana": grp["PR_AUC"].median(),
        "PR_AUC_IQR": grp["PR_AUC"].quantile(0.75) - grp["PR_AUC"].quantile(0.25),
        "PR_AUC_Mean_Runs": grp["PR_AUC"].mean(),
        "PR_AUC_Std_Runs": grp["PR_AUC"].std(ddof=1),
        "EE_B20_Mediana": grp["EE_B20"].median(),
        "EE_B20_IQR": grp["EE_B20"].quantile(0.75) - grp["EE_B20"].quantile(0.25),
        "EE_B20_Mean_Runs": grp["EE_B20"].mean(),
        "Rank_Medio_PR": grp["Rank_PR_Fold"].mean(),
        "Veces_Top1_PR": grp["Rank_PR_Fold"].apply(lambda s: int((s == 1).sum())),
        "Veces_Top3_PR": grp["Rank_PR_Fold"].apply(lambda s: int((s <= 3).sum())),
    }).reset_index()

    merged = best_models_df.merge(stats, on="Modelo", how="left")
    merged = merged.sort_values(by=["PR_AUC_Mediana", "PR_AUC_Mean_Runs"], ascending=[False, False]).reset_index(drop=True)

    top_model = merged.loc[0, "Modelo"]
    top_scores = df_f[df_f["Modelo"] == top_model].sort_values("Fold")["PR_AUC"].values
    pvals = []
    for m_name in merged["Modelo"]:
        if m_name == top_model:
            pvals.append(1.0)
        else:
            m_scores = df_f[df_f["Modelo"] == m_name].sort_values("Fold")["PR_AUC"].values
            try:
                _, p_val = wilcoxon(top_scores, m_scores, alternative="two-sided")
                pvals.append(float(p_val))
            except Exception:
                pvals.append(np.nan)
    merged["Wilcoxon_p_vs_Top1"] = pvals
    return merged


def select_winner_from_cv_2024(
    ranking_cv_df: pd.DataFrame,
    best_models_df: pd.DataFrame,
) -> Dict[str, Any]:
    """
    Regla formal de selección ex-ante usando EXCLUSIVAMENTE la validación cruzada en ENAHO 2024
    (Opción 1B: Validación Cruzada Espacial Repetida de 30 corridas = 6 repeticiones x 5 pliegues
    sobre los 704 conglomerados censales de 2024, antes de evaluar el conjunto de prueba OOT 2025).

    Criterio lexicográfico pre-especificado sobre las 30 corridas en 2024:
    1. Mayor mediana de PR-AUC (`PR_AUC_Mediana`).
    2. Menor rango promedio por corrida (`Rank_Medio_PR`, test de Friedman).
    3. Menor mediana de Error de Exclusión a B=20% (`EE_B20_Mediana`).
    """
    ordered = ranking_cv_df.sort_values(
        by=["PR_AUC_Mediana", "Rank_Medio_PR", "EE_B20_Mediana"],
        ascending=[False, True, True],
    ).reset_index(drop=True)

    winner_row = ordered.iloc[0]
    runner_up_row = ordered.iloc[1] if len(ordered) > 1 else ordered.iloc[0]
    single_cv_top = best_models_df.sort_values(by="PR_AUC_OOF", ascending=False).iloc[0]

    return {
        "winner_name": str(winner_row["Modelo"]),
        "winner_family": str(winner_row["Familia"]),
        "selection_rule": "Repeated_Spatial_CV_30runs_2024 (PR_AUC_Mediana + Rank_Medio_PR + EE_B20_Mediana)",
        "pr_auc_mediana_2024": float(winner_row["PR_AUC_Mediana"]),
        "pr_auc_mean_runs_2024": float(winner_row["PR_AUC_Mean_Runs"]),
        "rank_medio_pr_2024": float(winner_row["Rank_Medio_PR"]),
        "ee_b20_mediana_2024": float(winner_row["EE_B20_Mediana"]),
        "pr_auc_oof_5fold_2024": float(winner_row["PR_AUC_OOF"]),
        "runner_up_30runs": str(runner_up_row["Modelo"]),
        "single_5fold_top1": str(single_cv_top["Modelo"]),
        "single_5fold_top1_pr_auc": float(single_cv_top["PR_AUC_OOF"]),
        "ordered_ranking_df": ordered,
    }


def plot_cv_boxplots(
    folds_df: pd.DataFrame,
    save_path: Optional[Path] = None,
    show: bool = True,
):
    """
    Genera la figura de Boxplots comparativos de todos los modelos evaluados sobre las corridas
    de GroupKFold (Panel A: PR-AUC por pliegue; Panel B: Error de Exclusión EE a B=20%).
    """
    import matplotlib.pyplot as plt
    import seaborn as sns

    order_pr = (
        folds_df.groupby("Modelo")["PR_AUC"]
        .median()
        .sort_values(ascending=False)
        .index.tolist()
    )

    sns.set_theme(style="whitegrid")
    fig, axes = plt.subplots(1, 2, figsize=(15, 7.6), sharey=True)

    sns.boxplot(
        data=folds_df,
        x="PR_AUC",
        y="Modelo",
        order=order_pr,
        ax=axes[0],
        palette="viridis",
        hue="Modelo",
        legend=False,
        width=0.6,
        showmeans=True,
        meanprops={"marker": "D", "markerfacecolor": "white", "markeredgecolor": "black", "markersize": 6},
    )
    sns.stripplot(
        data=folds_df,
        x="PR_AUC",
        y="Modelo",
        order=order_pr,
        ax=axes[0],
        color="black",
        alpha=0.55,
        size=4.5,
        jitter=0.15,
    )
    axes[0].set_title("A. Distribución de PR-AUC en GroupKFold (Mayor es mejor)", fontweight="bold", fontsize=11)
    axes[0].set_xlabel("PR-AUC por Pliegue (Con ♦ = Media, Línea = Mediana)")
    axes[0].set_ylabel("Modelo Supervisado")

    sns.boxplot(
        data=folds_df,
        x="EE_B20",
        y="Modelo",
        order=order_pr,
        ax=axes[1],
        palette="magma_r",
        hue="Modelo",
        legend=False,
        width=0.6,
        showmeans=True,
        meanprops={"marker": "D", "markerfacecolor": "white", "markeredgecolor": "black", "markersize": 6},
    )
    sns.stripplot(
        data=folds_df,
        x="EE_B20",
        y="Modelo",
        order=order_pr,
        ax=axes[1],
        color="black",
        alpha=0.55,
        size=4.5,
        jitter=0.15,
    )
    axes[1].set_title("B. Error de Exclusión (EE a B=20%) en GroupKFold (Menor es mejor)", fontweight="bold", fontsize=11)
    axes[1].set_xlabel("Error de Exclusión FN / (TP + FN) por Pliegue")
    axes[1].set_ylabel("")

    n_runs = folds_df["Fold"].nunique()
    n_models = folds_df["Modelo"].nunique()
    plt.suptitle(
        f"Comparación de {n_models} Modelos mediante Boxplots de Validación Cruzada Espacial ({n_runs} Corridas en ENAHO 2024)",
        fontweight="bold",
        fontsize=13,
        y=1.01,
    )
    plt.tight_layout()

    if save_path is not None:
        save_path = Path(save_path)
        try:
            save_path.parent.mkdir(parents=True, exist_ok=True)
            fig.savefig(save_path, dpi=300, bbox_inches="tight")
            if save_path.suffix.lower() == ".png":
                fig.savefig(save_path.with_suffix(".pdf"), bbox_inches="tight")
        except OSError as e:
            print(f"[plot_cv_boxplots] Aviso al guardar en {save_path}: {e}")

    if show:
        plt.show()
    else:
        plt.close(fig)
    return fig


if __name__ == "__main__":
    from src.dataset import load_train_test_master

    t_start = time.perf_counter()
    print("=== Ejecución Paralela del Sprint 6: src/models.py ===")
    df_2024, _ = load_train_test_master()

    print("\n1. Comparativa de Escaladores Internos al Fold (Paralelo):")
    scaler_df = compare_scalers_cv(df_2024)
    print(scaler_df.to_string(index=False))

    print("\n2. Benchmark Completo de las 99 Configuraciones / 19 Modelos en GroupKFold(5):")
    best_df, all_df, artifacts = run_spatial_cv_benchmark(df_2024)

    print("\n3. Validación Cruzada Espacial Repetida (30 Corridas x 19 Modelos = 570 Evaluaciones):")
    rep_df = run_repeated_spatial_cv(artifacts, df_2024, n_splits=5, n_repeats=6)
    rank_df = rank_models_by_folds(rep_df, best_df)
    cols = [
        "Modelo", "N_Corridas", "PR_AUC_Mediana", "PR_AUC_IQR", "PR_AUC_Mean_Runs",
        "PR_AUC_Std_Runs", "Rank_Medio_PR", "Veces_Top1_PR", "Veces_Top3_PR",
        "Wilcoxon_p_vs_Top1", "EE_B20_Mediana", "EE_B20_IQR"
    ]
    print(rank_df[cols].to_string(index=False))
    print(f"\n⏱ Tiempo total extremo a extremo: {time.perf_counter() - t_start:.2f} s")
