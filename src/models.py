"""
Módulo de Modelado Supervisado y Validación Cruzada Espacial (Sprint 6).

Implementa la suite completa de modelos (5 principales del informe + familias extendidas
de la literatura PMT y Machine Learning tabular) bajo validación cruzada agrupada
`GroupKFold(n_splits=5)` por conglomerado censal sobre ENAHO 2024 (N = 4,090).

Reglas metodológicas clave:
1. Cero fuga espacial y de preprocesamiento: SecondaryHouseholdImputer, SimpleImputer,
   escalador numérico y OneHotEncoder se ajustan estrictamente DENTRO de cada fold.
2. Escalamiento diferenciado por familia:
   - Modelos lineales, generativos, kernels, distancias y redes neuronales:
     `scale_numeric=True, scaler_type="robust"` (RobustScaler por defecto, alineado con O-24;
     incluye comparador explícito contra StandardScaler y MinMaxScaler).
   - Modelos basados en árboles (CART, Random Forest, Extra Trees, Gradient Boosting):
     `scale_numeric=False, scaler_type="none"` (invarianza monotónica).
3. Aprendizaje sensible al costo (Elkan, 2001): peso de la clase pobre alpha in {1.0, 2.0, gamma}
   optimizado por validación cruzada orientada a PR-AUC, sin doble compensación de umbral.
"""
import sys
import warnings
from pathlib import Path
from typing import Dict, List, Tuple, Optional, Any
import numpy as np
import pandas as pd

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
    build_full_pipeline,
    prepare_xy_data,
)

# Detectar disponibilidad de LightGBM nativo (requiere libomp en macOS)
try:
    from lightgbm import LGBMClassifier
    HAS_LIGHTGBM = True
except Exception:
    LGBMClassifier = None
    HAS_LIGHTGBM = False


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

    # Selección a cobertura presupuestal fija B (ej. top 20% con mayor puntaje)
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

    # Curva Precision-Recall para F1_max y calibración operativa H3 (Recall >= 0.70)
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

    # Brier score sobre probabilidades en [0, 1]
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


# =============================================================================
# EVALUACIÓN ESPACIAL GROUPKFOLD(5) Y CALIBRACIÓN PLATT PARA PMT CONTINUO
# =============================================================================

def _calibrate_continuous_score_to_prob(
    neg_lngpc_train: np.ndarray,
    y_train: np.ndarray,
    neg_lngpc_eval: np.ndarray,
) -> np.ndarray:
    """
    Transforma el puntaje continuo (-ln_gasto_predicho) de PMT-MCO o PMT-Cuantílico
    en una probabilidad calibrada en [0, 1] mediante escalamiento logístico univariado
    ajustado únicamente en el pliegue de entrenamiento (preserva el orden exacto del ranking).
    """
    cal = LogisticRegression()
    cal.fit(neg_lngpc_train.reshape(-1, 1), y_train)
    return cal.predict_proba(neg_lngpc_eval.reshape(-1, 1))[:, 1]


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
    Ejecuta validación cruzada espacial GroupKFold(n_splits=5) agrupada por conglomerado.
    Retorna:
    - oof_probs: vector de predicciones Out-Of-Fold (N,) sobre todo el conjunto 2024
    - summary_metrics: diccionario con métricas OOF globales y media/desv entre folds
    - fold_metrics: lista de métricas por cada uno de los 5 folds
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
                # Ajusta sobre ln(gasto per cápita) en el fold de entrenamiento
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
) -> pd.DataFrame:
    """
    Verifica empíricamente en GroupKFold(5) sobre ENAHO 2024 el efecto del escalador
    numérico interno al fold ('robust', 'standard', 'minmax') en modelos sensibles a escala.
    """
    X, y, groups = prepare_xy_data(df_train, features=CANONICAL_FEATURES_28)
    gamma = float((y == 0).sum() / (y == 1).sum())
    w_bal = {0: 1.0, 1: gamma}

    rows = []
    for sc_type in ("robust", "standard", "minmax"):
        for model_label, est in [
            ("Logística ElasticNet", LogisticRegression(
                penalty="elasticnet", solver="saga", l1_ratio=0.5, C=0.2,
                class_weight=w_bal, max_iter=1500, random_state=42
            )),
            ("MLP Red Neuronal", MLPClassifier(
                hidden_layer_sizes=(64, 32), alpha=0.1, early_stopping=True,
                max_iter=300, random_state=42
            )),
            ("KNN (k=25)", KNeighborsClassifier(n_neighbors=25, weights="distance")),
        ]:
            pipe = build_full_pipeline(
                est,
                scale_numeric=True,
                scaler_type=sc_type,
                one_hot=True,
            )
            _, summary, _ = evaluate_pipeline_cv(pipe, X, y, groups, n_splits=n_splits)
            rows.append({
                "Modelo": model_label,
                "Escalador_Interno": sc_type,
                "PR_AUC_OOF": round(summary["PR_AUC"], 4),
                "PR_AUC_Mean": round(summary["PR_AUC_Fold_Mean"], 4),
                "PR_AUC_Std": round(summary["PR_AUC_Fold_Std"], 4),
                "ROC_AUC_OOF": round(summary["ROC_AUC"], 4),
                "EE_B20_OOF": round(summary["EE_B20"], 4),
            })
    return pd.DataFrame(rows)


# =============================================================================
# CATÁLOGO DE MODELOS Y OPTIMIZACIÓN COST-SENSITIVE POR GROUPKFOLD(5)
# =============================================================================

def _make_gbdt_estimator(alpha_weight: float, learning_rate: float = 0.05, num_leaves: int = 15, min_child: int = 30):
    """
    Retorna LightGBM nativo si libomp está presente, o HistGradientBoostingClassifier
    (implementación equivalente en Scikit-Learn de árboles por histogramas leaf-wise).
    """
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
            n_jobs=-1,
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
    Define el registro completo de modelos candidatos a evaluar en GroupKFold(5).
    Incluye búsqueda sobre el hiperparámetro de costo alpha in {1.0, 2.0, gamma}
    y regularización estructural en las 5 familias principales + modelos extendidos.
    """
    alphas = [1.0, 2.0, round(gamma, 4)]
    candidates: List[Dict[str, Any]] = []

    # -------------------------------------------------------------------------
    # 1. BASELINES DE REPRESENTACIÓN (SOLO VIVIENDA - MÓDULO 01, 12 VARS) -> H1
    # -------------------------------------------------------------------------
    for a in alphas:
        candidates.append({
            "name": "Logistica_Solo_Vivienda",
            "family": "01_Baseline_Vivienda (H1)",
            "config_desc": f"C=0.5, l1=0.5, alpha={a:.2f}",
            "alpha": a,
            "is_continuous_pmt": False,
            "features": VIVIENDA_FEATURES_12,
            "pipe": build_full_pipeline(
                LogisticRegression(
                    penalty="elasticnet", solver="saga", C=0.5, l1_ratio=0.5,
                    class_weight={0: 1.0, 1: a}, max_iter=1500, random_state=42
                ),
                numeric_cols=VIVIENDA_NUMERIC_COLS,
                categorical_cols=VIVIENDA_CATEGORICAL_COLS,
                scale_numeric=True,
                scaler_type="robust",
                one_hot=True,
            ),
        })

    candidates.append({
        "name": "RF_Solo_Vivienda",
        "family": "01_Baseline_Vivienda (H1)",
        "config_desc": f"n=300, max_depth=8, min_leaf=15, alpha={gamma:.2f}",
        "alpha": round(gamma, 4),
        "is_continuous_pmt": False,
        "features": VIVIENDA_FEATURES_12,
        "pipe": build_full_pipeline(
            RandomForestClassifier(
                n_estimators=300, max_depth=8, min_samples_leaf=15,
                class_weight={0: 1.0, 1: gamma}, n_jobs=-1, random_state=42
            ),
            numeric_cols=VIVIENDA_NUMERIC_COLS,
            categorical_cols=VIVIENDA_CATEGORICAL_COLS,
            scale_numeric=False,
            scaler_type="none",
            one_hot=True,
        ),
    })

    # -------------------------------------------------------------------------
    # 2. FAMILIA ECONOMÉTRICA PMT CONTINUA (PREDICE ln(gasto) EN R^28)
    # -------------------------------------------------------------------------
    for ridge_a in [1e-4, 1.0, 10.0]:
        candidates.append({
            "name": "PMT_MCO",
            "family": "02_Econometrico_PMT",
            "config_desc": f"OLS/Ridge(alpha={ridge_a}) sobre ln(gasto)",
            "alpha": 1.0,
            "is_continuous_pmt": True,
            "features": CANONICAL_FEATURES_28,
            "pipe": build_full_pipeline(
                Ridge(alpha=ridge_a, random_state=42),
                scale_numeric=True,
                scaler_type="robust",
                one_hot=True,
            ),
        })

    candidates.append({
        "name": "PMT_Quantile_20",
        "family": "02_Econometrico_PMT",
        "config_desc": "QuantileRegressor(q=0.20, alpha=0.01) sobre ln(gasto)",
        "alpha": 1.0,
        "is_continuous_pmt": True,
        "features": CANONICAL_FEATURES_28,
        "pipe": build_full_pipeline(
            QuantileRegressor(quantile=0.20, alpha=0.01, solver="highs"),
            scale_numeric=True,
            scaler_type="robust",
            one_hot=True,
        ),
    })

    # -------------------------------------------------------------------------
    # 3. FAMILIA LINEAL Y GENERATIVA (R^28, ROBUST SCALER INTERNO)
    # -------------------------------------------------------------------------
    for a in alphas:
        for c_val in [0.05, 0.2, 1.0]:
            for l1_val in [0.0, 0.5, 1.0]:
                candidates.append({
                    "name": "Logistica_ElasticNet",
                    "family": "03_Lineal_Regularizado",
                    "config_desc": f"C={c_val}, l1_ratio={l1_val}, alpha={a:.2f}",
                    "alpha": a,
                    "is_continuous_pmt": False,
                    "features": CANONICAL_FEATURES_28,
                    "pipe": build_full_pipeline(
                        LogisticRegression(
                            penalty="elasticnet", solver="saga", C=c_val, l1_ratio=l1_val,
                            class_weight={0: 1.0, 1: a}, max_iter=1500, random_state=42
                        ),
                        scale_numeric=True,
                        scaler_type="robust",
                        one_hot=True,
                    ),
                })

    candidates.append({
        "name": "LDA",
        "family": "03_Lineal_Generativo",
        "config_desc": "LinearDiscriminantAnalysis(solver='lsqr', shrinkage='auto')",
        "alpha": 1.0,
        "is_continuous_pmt": False,
        "features": CANONICAL_FEATURES_28,
        "pipe": build_full_pipeline(
            LinearDiscriminantAnalysis(solver="lsqr", shrinkage="auto"),
            scale_numeric=True,
            scaler_type="robust",
            one_hot=True,
        ),
    })

    candidates.append({
        "name": "Naive_Bayes",
        "family": "03_Lineal_Generativo",
        "config_desc": "GaussianNB(var_smoothing=1e-2)",
        "alpha": 1.0,
        "is_continuous_pmt": False,
        "features": CANONICAL_FEATURES_28,
        "pipe": build_full_pipeline(
            GaussianNB(var_smoothing=1e-2),
            scale_numeric=True,
            scaler_type="robust",
            one_hot=True,
        ),
    })

    # -------------------------------------------------------------------------
    # 4. FAMILIA ÁRBOLES Y BAGGING (R^28, SIN ESCALADO)
    # -------------------------------------------------------------------------
    for a in alphas:
        for ccp in [0.001, 0.003, 0.006]:
            candidates.append({
                "name": "CART_Podado",
                "family": "04_Arbol_Individual",
                "config_desc": f"max_depth=6, min_leaf=25, ccp_alpha={ccp}, alpha={a:.2f}",
                "alpha": a,
                "is_continuous_pmt": False,
                "features": CANONICAL_FEATURES_28,
                "pipe": build_full_pipeline(
                    DecisionTreeClassifier(
                        max_depth=6, min_samples_leaf=25, ccp_alpha=ccp,
                        class_weight={0: 1.0, 1: a}, random_state=42
                    ),
                    scale_numeric=False,
                    scaler_type="none",
                    one_hot=True,
                ),
            })

    for a in alphas:
        for depth in [8, 12]:
            for min_leaf in [10, 20]:
                candidates.append({
                    "name": "Random_Forest",
                    "family": "05_Ensamble_Bagging",
                    "config_desc": f"n=400, max_depth={depth}, min_leaf={min_leaf}, alpha={a:.2f}",
                    "alpha": a,
                    "is_continuous_pmt": False,
                    "features": CANONICAL_FEATURES_28,
                    "pipe": build_full_pipeline(
                        RandomForestClassifier(
                            n_estimators=400, max_depth=depth, min_samples_leaf=min_leaf,
                            class_weight={0: 1.0, 1: a}, n_jobs=-1, random_state=42
                        ),
                        scale_numeric=False,
                        scaler_type="none",
                        one_hot=True,
                    ),
                })

    for a in [1.0, round(gamma, 4)]:
        candidates.append({
            "name": "Extra_Trees",
            "family": "05_Ensamble_Bagging",
            "config_desc": f"n=400, max_depth=12, min_leaf=10, alpha={a:.2f}",
            "alpha": a,
            "is_continuous_pmt": False,
            "features": CANONICAL_FEATURES_28,
            "pipe": build_full_pipeline(
                ExtraTreesClassifier(
                    n_estimators=400, max_depth=12, min_samples_leaf=10,
                    class_weight={0: 1.0, 1: a}, n_jobs=-1, random_state=42
                ),
                scale_numeric=False,
                scaler_type="none",
                one_hot=True,
            ),
        })

    # -------------------------------------------------------------------------
    # 5. FAMILIA GRADIENT BOOSTING (R^28, SIN ESCALADO)
    # -------------------------------------------------------------------------
    gbdt_engine = "LightGBM" if HAS_LIGHTGBM else "HistGBDT_LeafWise"
    for a in alphas:
        for lr in [0.03, 0.05]:
            for leaves in [15, 25]:
                candidates.append({
                    "name": "LightGBM_GBDT",
                    "family": "06_Ensamble_Boosting",
                    "config_desc": f"{gbdt_engine}(lr={lr}, leaves={leaves}, alpha={a:.2f})",
                    "alpha": a,
                    "is_continuous_pmt": False,
                    "features": CANONICAL_FEATURES_28,
                    "pipe": build_full_pipeline(
                        _make_gbdt_estimator(alpha_weight=a, learning_rate=lr, num_leaves=leaves, min_child=30),
                        scale_numeric=False,
                        scaler_type="none",
                        one_hot=True,
                    ),
                })

    candidates.append({
        "name": "AdaBoost",
        "family": "06_Ensamble_Boosting",
        "config_desc": "AdaBoost(n=150, lr=0.1, base=CART_depth2)",
        "alpha": 1.0,
        "is_continuous_pmt": False,
        "features": CANONICAL_FEATURES_28,
        "pipe": build_full_pipeline(
            AdaBoostClassifier(
                estimator=DecisionTreeClassifier(max_depth=2, min_samples_leaf=20, random_state=42),
                n_estimators=150,
                learning_rate=0.1,
                random_state=42,
            ),
            scale_numeric=False,
            scaler_type="none",
            one_hot=True,
        ),
    })

    # -------------------------------------------------------------------------
    # 6. FAMILIA KERNELS, VECINDAD Y REDES NEURONALES (ROBUST SCALER INTERNO)
    # -------------------------------------------------------------------------
    for a in [1.0, 2.0]:
        candidates.append({
            "name": "SVM_RBF",
            "family": "07_NoLineal_Kernel_NN",
            "config_desc": f"SVC(kernel='rbf', C=1.0, alpha={a:.2f})",
            "alpha": a,
            "is_continuous_pmt": False,
            "features": CANONICAL_FEATURES_28,
            "pipe": build_full_pipeline(
                SVC(kernel="rbf", C=1.0, probability=True, class_weight={0: 1.0, 1: a}, random_state=42),
                scale_numeric=True,
                scaler_type="robust",
                one_hot=True,
            ),
        })

    candidates.append({
        "name": "KNN",
        "family": "07_NoLineal_Kernel_NN",
        "config_desc": "KNeighbors(k=35, weights='distance')",
        "alpha": 1.0,
        "is_continuous_pmt": False,
        "features": CANONICAL_FEATURES_28,
        "pipe": build_full_pipeline(
            KNeighborsClassifier(n_neighbors=35, weights="distance", n_jobs=-1),
            scale_numeric=True,
            scaler_type="robust",
            one_hot=True,
        ),
    })

    candidates.append({
        "name": "MLP_Red_Neuronal",
        "family": "07_NoLineal_Kernel_NN",
        "config_desc": "MLP(hidden=(64, 32), alpha_l2=0.5, early_stopping=True)",
        "alpha": 1.0,
        "is_continuous_pmt": False,
        "features": CANONICAL_FEATURES_28,
        "pipe": build_full_pipeline(
            MLPClassifier(
                hidden_layer_sizes=(64, 32), alpha=0.5, learning_rate_init=0.005,
                early_stopping=True, max_iter=300, random_state=42
            ),
            scale_numeric=True,
            scaler_type="robust",
            one_hot=True,
        ),
    })

    # -------------------------------------------------------------------------
    # 7. META-ENSAMBLE (STACKING MULTIFAMILIA)
    # -------------------------------------------------------------------------
    stack_est = StackingClassifier(
        estimators=[
            ("lr", LogisticRegression(penalty="elasticnet", solver="saga", C=0.2, l1_ratio=0.5, max_iter=1200, random_state=42)),
            ("rf", RandomForestClassifier(n_estimators=300, max_depth=10, min_samples_leaf=15, n_jobs=-1, random_state=42)),
            ("et", ExtraTreesClassifier(n_estimators=300, max_depth=12, min_samples_leaf=15, n_jobs=-1, random_state=42)),
            ("gb", _make_gbdt_estimator(alpha_weight=1.0, learning_rate=0.03, num_leaves=15, min_child=30)),
        ],
        final_estimator=LogisticRegression(C=1.0, random_state=42),
        cv=3,
        n_jobs=-1,
    )
    candidates.append({
        "name": "Stacking_Ensemble",
        "family": "08_Meta_Ensamble",
        "config_desc": "Stacking(ElasticNet + RF + ExtraTrees + GBDT -> Logit)",
        "alpha": 1.0,
        "is_continuous_pmt": False,
        "features": CANONICAL_FEATURES_28,
        "pipe": build_full_pipeline(
            stack_est,
            scale_numeric=True,
            scaler_type="robust",
            one_hot=True,
        ),
    })

    return candidates


def run_spatial_cv_benchmark(
    df_train: pd.DataFrame,
    n_splits: int = 5,
    verbose: bool = True,
) -> Tuple[pd.DataFrame, pd.DataFrame, Dict[str, Dict[str, Any]]]:
    """
    Ejecuta la búsqueda de hiperparámetros/alpha y comparación de modelos bajo
    GroupKFold(n_splits=5) por conglomerado censal en ENAHO 2024 (N = 4,090).

    Retorna:
    - best_models_df: Tabla resumen del mejor modelo de cada tipo ordenado por PR-AUC OOF.
    - all_configs_df: Tabla completa con todas las configuraciones evaluadas.
    - fitted_best_artifacts: Diccionario por nombre de modelo con:
        * 'pipe': pipeline reentrenado sobre todo ENAHO 2024
        * 'calibrator': calibrador Platt (si es PMT continuo) ajustado en 2024
        * 'oof_probs': predicciones Out-Of-Fold (4,090,) en 2024
        * 'metrics_cv': diccionario de métricas OOF y de folds
        * 'features': lista de variables de entrada utilizadas
        * 'config_desc': descripción de hiperparámetros ganadores
        * 'alpha': peso de clase seleccionado
    """
    X_full, y, groups = prepare_xy_data(df_train, features=CANONICAL_FEATURES_28)
    X_viv, _, _ = prepare_xy_data(df_train, features=VIVIENDA_FEATURES_12)
    y_lngpc = df_train["lngpc"].copy()

    gamma = float((y == 0).sum() / (y == 1).sum())
    candidates = build_candidate_registry(gamma=gamma)

    all_rows = []
    best_by_name: Dict[str, Dict[str, Any]] = {}

    if verbose:
        print(f"[run_spatial_cv_benchmark] Evaluando {len(candidates)} configuraciones en GroupKFold({n_splits}) sobre {len(y):,d} hogares...")

    for cand in candidates:
        name = cand["name"]
        X_in = X_viv if len(cand["features"]) == len(VIVIENDA_FEATURES_12) else X_full
        oof_probs, summary, fold_list = evaluate_pipeline_cv(
            cand["pipe"],
            X=X_in,
            y=y,
            groups=groups,
            n_splits=n_splits,
            is_continuous_pmt=cand["is_continuous_pmt"],
            y_continuous=y_lngpc if cand["is_continuous_pmt"] else None,
        )

        row = {
            "Modelo": name,
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
        all_rows.append(row)

        # Seleccionar la mejor configuración de cada modelo según PR-AUC OOF
        if (name not in best_by_name) or (summary["PR_AUC"] > best_by_name[name]["metrics_cv"]["PR_AUC"]):
            best_by_name[name] = {
                "cand": cand,
                "oof_probs": oof_probs,
                "metrics_cv": summary,
                "fold_metrics": fold_list,
                "row": row,
            }

    # Reentrenar el mejor pipeline de cada modelo sobre el 100% de ENAHO 2024
    fitted_best_artifacts: Dict[str, Dict[str, Any]] = {}
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        for name, info in best_by_name.items():
            cand = info["cand"]
            X_in = X_viv if len(cand["features"]) == len(VIVIENDA_FEATURES_12) else X_full
            final_pipe = clone(cand["pipe"])
            calibrator = None
            if cand["is_continuous_pmt"]:
                final_pipe.fit(X_in, y_lngpc.values)
                neg_pred_full = -final_pipe.predict(X_in)
                calibrator = LogisticRegression()
                calibrator.fit(neg_pred_full.reshape(-1, 1), y.values)
            else:
                final_pipe.fit(X_in, y.values)

            fitted_best_artifacts[name] = {
                "pipe": final_pipe,
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

    all_configs_df = pd.DataFrame(all_rows).sort_values(by=["Modelo", "PR_AUC_OOF"], ascending=[True, False]).reset_index(drop=True)
    best_models_df = (
        pd.DataFrame([v["row"] for v in best_by_name.values()])
        .sort_values(by="PR_AUC_OOF", ascending=False)
        .reset_index(drop=True)
    )

    if verbose:
        print(f"✓ Benchmark CV 2024 completado ({len(best_models_df)} modelos únicos seleccionados).")

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
    en formato largo (ideal para Boxplots de Validación Cruzada y análisis de estabilidad).
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


def run_repeated_spatial_cv(
    fitted_artifacts: Dict[str, Dict[str, Any]],
    df_train: pd.DataFrame,
    n_splits: int = 5,
    n_repeats: int = 6,
    random_state: int = 42,
    verbose: bool = True,
) -> pd.DataFrame:
    """
    Ejecuta Validación Cruzada Espacial Repetida (Repeated GroupKFold: n_repeats x n_splits
    = 30 corridas por modelo por defecto) permutando aleatoriamente los 704 conglomerados
    censales en cada repetición, garantizando que ningún conglomerado se divida entre
    entrenamiento y validación.

    Permite construir Boxplots densos (30 evaluaciones por modelo) y pruebas de hipótesis
    pareadas (Wilcoxon / Friedman) con alta potencia estadística.
    """
    X_full, y, groups = prepare_xy_data(df_train, features=CANONICAL_FEATURES_28)
    X_viv, _, _ = prepare_xy_data(df_train, features=VIVIENDA_FEATURES_12)
    y_arr = y.values
    y_lngpc_arr = df_train["lngpc"].values
    grp_arr = groups.values

    unique_groups = np.unique(grp_arr)
    rng = np.random.default_rng(random_state)

    total_runs = n_splits * n_repeats
    if verbose:
        print(
            f"[run_repeated_spatial_cv] Ejecutando {n_repeats} repeticiones x {n_splits} folds "
            f"= {total_runs} corridas espaciales por cada uno de los {len(fitted_artifacts)} modelos..."
        )

    rows = []
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        for rep in range(1, n_repeats + 1):
            # Permutar los conglomerados y asignarlos a n_splits pliegues balanceados
            perm_groups = rng.permutation(unique_groups)
            group_to_fold = {g: (i % n_splits) for i, g in enumerate(perm_groups)}
            fold_assignment = np.array([group_to_fold[g] for g in grp_arr])

            for fold_idx in range(n_splits):
                run_id = (rep - 1) * n_splits + (fold_idx + 1)
                val_mask = fold_assignment == fold_idx
                tr_idx = np.where(~val_mask)[0]
                val_idx = np.where(val_mask)[0]

                y_f_tr, y_f_val = y_arr[tr_idx], y_arr[val_idx]

                for name, art in fitted_artifacts.items():
                    X_in = X_viv if len(art["features"]) == len(VIVIENDA_FEATURES_12) else X_full
                    X_f_tr, X_f_val = X_in.iloc[tr_idx], X_in.iloc[val_idx]
                    model_fold = clone(art["pipe"])

                    if art["is_continuous_pmt"]:
                        y_c_tr = y_lngpc_arr[tr_idx]
                        model_fold.fit(X_f_tr, y_c_tr)
                        neg_tr = -model_fold.predict(X_f_tr)
                        neg_val = -model_fold.predict(X_f_val)
                        probs_val = _calibrate_continuous_score_to_prob(neg_tr, y_f_tr, neg_val)
                    else:
                        model_fold.fit(X_f_tr, y_f_tr)
                        probs_val = model_fold.predict_proba(X_f_val)[:, 1]

                    m = compute_targeting_metrics(y_f_val, probs_val)
                    rows.append({
                        "Modelo": name,
                        "Familia": art["family"],
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

    if verbose:
        print(f"✓ Validación cruzada repetida completada: {len(rows):,d} evaluaciones generadas.")
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
    n_runs = df_f["Fold"].nunique()
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

    # Test de Wilcoxon pareado frente al modelo con mejor mediana de PR-AUC
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


def plot_cv_boxplots(
    folds_df: pd.DataFrame,
    save_path: Optional[Path] = None,
    show: bool = True,
):
    """
    Genera la figura de Boxplots comparativos de los 16 modelos sobre los 5 folds
    de GroupKFold (Panel A: PR-AUC por fold; Panel B: Error de Exclusión EE a B=20%).
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
    fig, axes = plt.subplots(1, 2, figsize=(15, 6.8), sharey=True)

    # Panel A: Boxplot de PR-AUC en los 5 folds
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
        size=5,
        jitter=0.12,
    )
    axes[0].set_title("A. Distribución de PR-AUC en GroupKFold(5) (Mayor es mejor)", fontweight="bold", fontsize=11)
    axes[0].set_xlabel("PR-AUC por Pliegue (Con ♦ = Media, Línea = Mediana)")
    axes[0].set_ylabel("Modelo Supervisado")

    # Panel B: Boxplot de Error de Exclusión a B=20% en los 5 folds
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
        size=5,
        jitter=0.12,
    )
    axes[1].set_title("B. Error de Exclusión (EE a B=20%) en GroupKFold(5) (Menor es mejor)", fontweight="bold", fontsize=11)
    axes[1].set_xlabel("Error de Exclusión FN / (TP + FN) por Pliegue")
    axes[1].set_ylabel("")

    n_runs = folds_df["Fold"].nunique()
    plt.suptitle(
        f"Comparación de 16 Modelos mediante Boxplots de Validación Cruzada Espacial ({n_runs} Corridas en ENAHO 2024)",
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

    print("=== Ejecución de Verificación del Sprint 6: src/models.py ===")
    df_2024, _ = load_train_test_master()

    print("\n1. Comparativa de Escaladores Internos al Fold (Robust vs Standard vs MinMax):")
    scaler_df = compare_scalers_cv(df_2024)
    print(scaler_df.to_string(index=False))

    print("\n2. Benchmark Completo de las 16 Familias/Modelos en GroupKFold(5) (ENAHO 2024):")
    best_df, all_df, artifacts = run_spatial_cv_benchmark(df_2024)
    cols_show = [
        "Modelo", "Familia", "Alpha_Costo", "PR_AUC_OOF", "PR_AUC_Mean",
        "PR_AUC_Std", "ROC_AUC_OOF", "EE_B20_OOF", "Prec_at_Rec70_OOF", "Configuracion"
    ]
    print(best_df[cols_show].to_string(index=False))
