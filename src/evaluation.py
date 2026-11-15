"""
Módulo de Evaluación Fuera de Tiempo (OOT 2025), Inferencia por Cluster Bootstrap,
Explicabilidad (TreeSHAP) y Auditoría Ética por Subgrupos (Sprint 7).

Reglas metodológicas:
1. Evaluación estrictamente ciega sobre ENAHO 2025 sin hogares panel (N_test = 3,199,
   601 conglomerados), aplicando pipelines y umbrales congelados en ENAHO 2024.
2. Métricas reportadas por hogar muestral y ponderadas por `factor_expansion` (FACTOR07).
3. Contraste formal de hipótesis H1 a H4 mediante Cluster Bootstrap (1,000 réplicas
   remuestreadas a nivel de conglomerado censal).
4. Explicabilidad global y por dependencia parcial con TreeSHAP sobre el mejor ensamble
   de árboles, más agregación por variable canónica original (R^28) y bloque temático.
5. Auditoría de equidad algorítmica por subgrupos vulnerables para Implicancias Éticas.
"""
import sys
import warnings
from pathlib import Path
from typing import Dict, List, Tuple, Optional, Any
import numpy as np
import pandas as pd

from sklearn.metrics import (
    average_precision_score,
    roc_auc_score,
    brier_score_loss,
    precision_score,
    recall_score,
    f1_score,
)

_ROOT = Path(__file__).resolve().parents[1]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from src.preprocessing import (
    NUMERIC_COLS,
    CATEGORICAL_COLS,
    CANONICAL_FEATURES_28,
    TARGET_COL,
    GROUP_COL,
    prepare_xy_data,
)
from src.models import (
    compute_targeting_metrics,
    predict_poverty_probs,
)


# =============================================================================
# 1. MÉTRICAS POR HOGAR Y PONDERADAS POR FACTOR DE EXPANSIÓN (OOT 2025)
# =============================================================================

def _weighted_ee_ie_at_B(
    y_true: np.ndarray,
    scores: np.ndarray,
    weights: Optional[np.ndarray] = None,
    budget_coverage: float = 0.20,
) -> Tuple[float, float]:
    """
    Calcula Error de Exclusión (EE) y Error de Inclusión (IE) seleccionando
    los hogares con mayor puntaje hasta cubrir una fracción B de la población
    (o de los hogares si weights is None).
    """
    n = len(y_true)
    order = np.argsort(-scores)
    y_ord = y_true[order] == 1

    if weights is None:
        k = int(round(budget_coverage * n))
        sel = np.zeros(n, dtype=bool)
        sel[:k] = True
        tp = float((sel & y_ord).sum())
        fp = float((sel & ~y_ord).sum())
        fn = float((~sel & y_ord).sum())
    else:
        w_ord = weights[order]
        cum_w = np.cumsum(w_ord)
        cutoff_w = budget_coverage * w_ord.sum()
        sel = cum_w <= cutoff_w
        if not sel.any():
            sel[0] = True
        tp = float(w_ord[sel & y_ord].sum())
        fp = float(w_ord[sel & ~y_ord].sum())
        fn = float(w_ord[~sel & y_ord].sum())

    ee = fn / max(1e-12, tp + fn)
    ie = fp / max(1e-12, tp + fp)
    return float(ee), float(ie)


def evaluate_oot_2025(
    fitted_artifacts: Dict[str, Dict[str, Any]],
    df_2025_test: pd.DataFrame,
    budget_coverage: float = 0.20,
) -> Tuple[pd.DataFrame, Dict[str, np.ndarray]]:
    """
    Evalúa todos los modelos entrenados en 2024 sobre el conjunto ciego OOT 2025 (N=3,199).
    Calcula métricas por hogar y ponderadas por `factor_expansion`, además de evaluar
    el punto operativo H3 usando el umbral `tau_2024` congelado de la validación OOF 2024.
    """
    y_test = df_2025_test[TARGET_COL].values.astype(int)
    w_test = df_2025_test["factor_expansion"].values.astype(float)

    rows = []
    probs_2025: Dict[str, np.ndarray] = {}

    for name, art in fitted_artifacts.items():
        probs = predict_poverty_probs(art, df_2025_test)
        probs_2025[name] = probs

        # Métricas por hogar muestral
        m_unw = compute_targeting_metrics(y_test, probs, budget_coverage=budget_coverage)

        # Métricas ponderadas por factor de expansión poblacional
        pr_w = float(average_precision_score(y_test, probs, sample_weight=w_test))
        roc_w = float(roc_auc_score(y_test, probs, sample_weight=w_test))
        brier_w = float(brier_score_loss(y_test, np.clip(probs, 0.0, 1.0), sample_weight=w_test))
        ee_w, ie_w = _weighted_ee_ie_at_B(y_test, probs, weights=w_test, budget_coverage=budget_coverage)

        # Evaluación operativa H3 con umbral tau congelado de 2024 (sin mirar 2025)
        tau_2024 = float(art["metrics_cv"]["Tau_Rec70"])
        y_pred_tau = (probs >= tau_2024).astype(int)
        rec_tau_2025 = float(recall_score(y_test, y_pred_tau, zero_division=0))
        prec_tau_2025 = float(precision_score(y_test, y_pred_tau, zero_division=0))
        f1_tau_2025 = float(f1_score(y_test, y_pred_tau, zero_division=0))

        # Degradación temporal H4 (CV OOF 2024 -> Test OOT 2025)
        pr_cv_2024 = float(art["metrics_cv"]["PR_AUC"])
        delta_temp_pr = pr_cv_2024 - m_unw["PR_AUC"]

        rows.append({
            "Modelo": name,
            "Familia": art["family"],
            "Alpha_Costo": art["alpha"],
            "PR_AUC_2024_CV": pr_cv_2024,
            "PR_AUC_2025": m_unw["PR_AUC"],
            "PR_AUC_2025_Pond": pr_w,
            "Delta_Temp_PR (H4)": delta_temp_pr,
            "ROC_AUC_2025": m_unw["ROC_AUC"],
            "ROC_AUC_2025_Pond": roc_w,
            "EE_B20_2025": m_unw["EE_B20"],
            "IE_B20_2025": m_unw["IE_B20"],
            "EE_B20_2025_Pond": ee_w,
            "IE_B20_2025_Pond": ie_w,
            "Brier_2025": m_unw["Brier"],
            "Brier_2025_Pond": brier_w,
            "Tau_Congelado_2024": tau_2024,
            "Recall_Tau_2025 (H3)": rec_tau_2025,
            "Prec_Tau_2025 (H3)": prec_tau_2025,
            "F1_Tau_2025": f1_tau_2025,
        })

    oot_df = pd.DataFrame(rows).sort_values(by="PR_AUC_2025", ascending=False).reset_index(drop=True)
    return oot_df, probs_2025


# =============================================================================
# 2. CURVAS PARAMÉTRICAS EE VS. IE PARA COBERTURA B in [0.10, 0.40]
# =============================================================================

def compute_ee_ie_curves(
    y_true: np.ndarray,
    probs_dict: Dict[str, np.ndarray],
    models_to_plot: Optional[List[str]] = None,
    b_grid: Optional[np.ndarray] = None,
) -> pd.DataFrame:
    """
    Calcula las curvas Error de Exclusión (EE) y Error de Inclusión (IE) a través
    de la grilla presupuestal B in [0.10, 0.40].
    """
    if b_grid is None:
        b_grid = np.linspace(0.10, 0.40, 13)
    if models_to_plot is None:
        models_to_plot = [
            m for m in [
                "Stacking_Ensemble",
                "Logistica_ElasticNet",
                "LightGBM_GBDT",
                "Random_Forest",
                "PMT_MCO",
                "CART_Podado",
                "Logistica_Solo_Vivienda",
            ] if m in probs_dict
        ]

    rows = []
    for name in models_to_plot:
        s = probs_dict[name]
        for b in b_grid:
            ee, ie = _weighted_ee_ie_at_B(y_true, s, weights=None, budget_coverage=float(b))
            rows.append({
                "Modelo": name,
                "Cobertura_B": round(float(b), 4),
                "EE": ee,
                "IE": ie,
            })
    return pd.DataFrame(rows)


def plot_ee_ie_curves(
    curves_df: pd.DataFrame,
    save_path: Optional[Path] = None,
    show: bool = True,
):
    """Grafica curvas EE vs. Cobertura B y frontera EE vs. IE en Test OOT 2025."""
    import matplotlib.pyplot as plt
    import seaborn as sns

    sns.set_theme(style="whitegrid")
    fig, axes = plt.subplots(1, 2, figsize=(13.5, 5.2))

    sns.lineplot(
        data=curves_df, x="Cobertura_B", y="EE", hue="Modelo",
        style="Modelo", markers=True, dashes=False, linewidth=2.0, ax=axes[0],
    )
    axes[0].axvline(0.20, color="gray", linestyle="--", linewidth=1.2, label="Cobertura fija B=20%")
    axes[0].set_title("A. Error de Exclusión vs. Cobertura Presupuestal (Test 2025)", fontweight="bold")
    axes[0].set_xlabel("Cobertura Presupuestal B (Fracción de Hogares Seleccionados)")
    axes[0].set_ylabel("Error de Exclusión (EE = FN / (TP + FN))")

    sns.lineplot(
        data=curves_df, x="IE", y="EE", hue="Modelo",
        style="Modelo", markers=True, dashes=False, linewidth=2.0, ax=axes[1],
    )
    axes[1].set_title("B. Frontera Trade-off Exclusión vs. Inclusión (B en [0.10, 0.40])", fontweight="bold")
    axes[1].set_xlabel("Error de Inclusión (IE = FP / (TP + FP))")
    axes[1].set_ylabel("Error de Exclusión (EE)")

    plt.tight_layout()
    if save_path is not None:
        save_path = Path(save_path)
        try:
            save_path.parent.mkdir(parents=True, exist_ok=True)
            fig.savefig(save_path, dpi=300, bbox_inches="tight")
            if save_path.suffix.lower() == ".png":
                fig.savefig(save_path.with_suffix(".pdf"), bbox_inches="tight")
        except OSError as e:
            print(f"[plot_ee_ie_curves] Aviso al guardar en {save_path}: {e}")

    if show:
        plt.show()
    else:
        plt.close(fig)
    return fig


# =============================================================================
# 3. INFERENCIA ESTADÍSTICA POR CLUSTER BOOTSTRAP (1,000 RÉPLICAS, H1-H4)
# =============================================================================

def _cluster_bootstrap_indices(groups: np.ndarray, n_boot: int = 1000, seed: int = 42) -> List[np.ndarray]:
    """Genera n_boot listas de índices remuestreando conglomerados con reemplazo."""
    rng = np.random.default_rng(seed)
    ug = np.unique(groups)
    gi = {g: np.where(groups == g)[0] for g in ug}
    n_clusters = len(ug)
    return [
        np.concatenate([gi[g] for g in rng.choice(ug, size=n_clusters, replace=True)])
        for _ in range(n_boot)
    ]


def _ci_summary(arr: np.ndarray) -> Tuple[float, float, float]:
    return float(np.mean(arr)), float(np.percentile(arr, 2.5)), float(np.percentile(arr, 97.5))


def run_cluster_bootstrap_hypotheses(
    df_2024: pd.DataFrame,
    df_2025_test: pd.DataFrame,
    fitted_artifacts: Dict[str, Dict[str, Any]],
    probs_2025: Dict[str, np.ndarray],
    n_boot: int = 1000,
    seed: int = 42,
) -> pd.DataFrame:
    """
    Contrasta formalmente las hipótesis H1, H2, H3 y H4 mediante Cluster Bootstrap
    de 1,000 réplicas a nivel de conglomerado censal (601 clústeres en 2025 y 704 en 2024).
    """
    y24 = df_2024[TARGET_COL].values.astype(int)
    g24 = df_2024[GROUP_COL].values
    y25 = df_2025_test[TARGET_COL].values.astype(int)
    g25 = df_2025_test[GROUP_COL].values

    boot_25 = _cluster_bootstrap_indices(g25, n_boot=n_boot, seed=seed)
    boot_24 = _cluster_bootstrap_indices(g24, n_boot=n_boot, seed=seed + 1)

    rows = []

    # -------------------------------------------------------------------------
    # H1: Ganancia de Representación >= +0.12 en PR-AUC (4 módulos vs Solo Vivienda) en 2025
    # -------------------------------------------------------------------------
    h1_pairs = [
        ("Logistica_ElasticNet", "Logistica_Solo_Vivienda"),
        ("Random_Forest", "RF_Solo_Vivienda"),
        ("LightGBM_GBDT", "RF_Solo_Vivienda"),
        ("Stacking_Ensemble", "Logistica_Solo_Vivienda"),
    ]
    for m_full, m_viv in h1_pairs:
        if m_full in probs_2025 and m_viv in probs_2025:
            p_full, p_viv = probs_2025[m_full], probs_2025[m_viv]
            obs = float(average_precision_score(y25, p_full) - average_precision_score(y25, p_viv))
            diffs = np.array([
                average_precision_score(y25[idx], p_full[idx]) - average_precision_score(y25[idx], p_viv[idx])
                for idx in boot_25
            ])
            mean_b, lo, hi = _ci_summary(diffs)
            rows.append({
                "Hipotesis": "H1 (Representación >= +0.12)",
                "Contraste": f"{m_full} - {m_viv} (PR-AUC 2025)",
                "Valor_Observado": obs,
                "Media_Bootstrap": mean_b,
                "IC95_Inf": lo,
                "IC95_Sup": hi,
                "Criterio_Meta": "IC95_Inf >= +0.12",
                "Resultado": "CORROBORADA" if lo >= 0.12 else ("PARCIAL (Obs >= 0.12)" if obs >= 0.12 else "NO CORROBORADA"),
            })

    # -------------------------------------------------------------------------
    # H2: Equivalencia Algorítmica en EE (B=20%) dentro de +-0.035 en Test 2025
    # -------------------------------------------------------------------------
    h2_pairs = [
        ("LightGBM_GBDT", "Logistica_ElasticNet"),
        ("LightGBM_GBDT", "PMT_MCO"),
        ("Random_Forest", "Logistica_ElasticNet"),
        ("Random_Forest", "PMT_MCO"),
        ("Stacking_Ensemble", "Logistica_ElasticNet"),
        ("Stacking_Ensemble", "PMT_MCO"),
    ]
    for m_ens, m_lin in h2_pairs:
        if m_ens in probs_2025 and m_lin in probs_2025:
            p_e, p_l = probs_2025[m_ens], probs_2025[m_lin]
            ee_e_obs, _ = _weighted_ee_ie_at_B(y25, p_e, None, 0.20)
            ee_l_obs, _ = _weighted_ee_ie_at_B(y25, p_l, None, 0.20)
            obs = ee_e_obs - ee_l_obs
            diffs = np.array([
                _weighted_ee_ie_at_B(y25[idx], p_e[idx], None, 0.20)[0]
                - _weighted_ee_ie_at_B(y25[idx], p_l[idx], None, 0.20)[0]
                for idx in boot_25
            ])
            mean_b, lo, hi = _ci_summary(diffs)
            ok_band = (lo >= -0.035) and (hi <= 0.035)
            rows.append({
                "Hipotesis": "H2 (Equivalencia EE ±0.035)",
                "Contraste": f"EE({m_ens}) - EE({m_lin}) @ B=20% (2025)",
                "Valor_Observado": obs,
                "Media_Bootstrap": mean_b,
                "IC95_Inf": lo,
                "IC95_Sup": hi,
                "Criterio_Meta": "IC95% dentro [-0.035, +0.035]",
                "Resultado": "CORROBORADA" if ok_band else ("DENTRO PUNTO (IC excede)" if abs(obs) <= 0.035 else "REFUTADA"),
            })

    # -------------------------------------------------------------------------
    # H3: Punto Operativo en 2025 con tau congelado de 2024 (Rec>=0.70, Prec>=0.40)
    # -------------------------------------------------------------------------
    for m_name in ["Stacking_Ensemble", "Logistica_ElasticNet", "LightGBM_GBDT", "Random_Forest", "PMT_MCO"]:
        if m_name in probs_2025:
            tau = float(fitted_artifacts[m_name]["metrics_cv"]["Tau_Rec70"])
            pred = (probs_2025[m_name] >= tau).astype(int)
            rec_obs = float(recall_score(y25, pred, zero_division=0))
            prec_obs = float(precision_score(y25, pred, zero_division=0))

            recs = np.array([recall_score(y25[idx], pred[idx], zero_division=0) for idx in boot_25])
            precs = np.array([precision_score(y25[idx], pred[idx], zero_division=0) for idx in boot_25])

            r_mean, r_lo, r_hi = _ci_summary(recs)
            p_mean, p_lo, p_hi = _ci_summary(precs)
            rows.append({
                "Hipotesis": "H3 (Recall >= 0.70 con tau_2024)",
                "Contraste": f"{m_name} Recall 2025 (tau={tau:.3f})",
                "Valor_Observado": rec_obs,
                "Media_Bootstrap": r_mean,
                "IC95_Inf": r_lo,
                "IC95_Sup": r_hi,
                "Criterio_Meta": "Recall >= 0.70",
                "Resultado": "CORROBORADA" if rec_obs >= 0.70 else "NO CORROBORADA",
            })
            rows.append({
                "Hipotesis": "H3 (Precisión >= 0.40 con tau_2024)",
                "Contraste": f"{m_name} Precisión 2025 (tau={tau:.3f})",
                "Valor_Observado": prec_obs,
                "Media_Bootstrap": p_mean,
                "IC95_Inf": p_lo,
                "IC95_Sup": p_hi,
                "Criterio_Meta": "Precisión >= 0.40",
                "Resultado": "CORROBORADA" if prec_obs >= 0.40 else "NO CORROBORADA",
            })

    # -------------------------------------------------------------------------
    # H4: Degradación temporal PR-AUC (CV 2024 -> Test 2025) <= 0.05
    # -------------------------------------------------------------------------
    for m_name in ["Stacking_Ensemble", "Logistica_ElasticNet", "LightGBM_GBDT", "Random_Forest", "PMT_MCO"]:
        if m_name in probs_2025:
            oof_24 = fitted_artifacts[m_name]["oof_probs"]
            p_25 = probs_2025[m_name]
            obs = float(average_precision_score(y24, oof_24) - average_precision_score(y25, p_25))
            deltas = np.array([
                average_precision_score(y24[i24], oof_24[i24]) - average_precision_score(y25[i25], p_25[i25])
                for i24, i25 in zip(boot_24, boot_25)
            ])
            mean_b, lo, hi = _ci_summary(deltas)
            rows.append({
                "Hipotesis": "H4 (Caída Temporal <= 0.05)",
                "Contraste": f"{m_name}: PR-AUC(2024) - PR-AUC(2025)",
                "Valor_Observado": obs,
                "Media_Bootstrap": mean_b,
                "IC95_Inf": lo,
                "IC95_Sup": hi,
                "Criterio_Meta": "Delta <= 0.05 (IC95_Sup <= 0.05)",
                "Resultado": "CORROBORADA" if hi <= 0.05 else ("CORROBORADA PUNTO (IC > 0.05)" if obs <= 0.05 else "NO CORROBORADA"),
            })

    return pd.DataFrame(rows)


# =============================================================================
# 4. EXPLICABILIDAD CON TREESHAP SOBRE EL MEJOR ENSAMBLE DE ÁRBOLES
# =============================================================================

_BLOCK_MAP: Dict[str, str] = {}
for _c in ["total_habitaciones", "total_dormitorios", "tipo_vivienda", "material_pared",
           "material_piso", "tenencia_vivienda", "fuente_agua", "agua_todos_los_dias",
           "conexion_bano", "combustible_cocina", "tiene_internet"]:
    _BLOCK_MAP[_c] = "Vivienda (M01)"
for _c in ["n_miembros", "n_ninos_0_5", "n_menores_14", "n_mayores_65",
           "tasa_dependencia", "jefe_edad", "jefe_mujer"]:
    _BLOCK_MAP[_c] = "Demografía (M02)"
for _c in ["educ_jefe", "educ_max_hogar"]:
    _BLOCK_MAP[_c] = "Educación (M03)"
for _c in ["n_ocupados", "ocupados_por_miembro", "personas_por_hab", "jefe_horas_semanales",
           "jefe_ocupado", "jefe_cat_ocupacional", "jefe_empresa_ruc", "jefe_sin_pension"]:
    _BLOCK_MAP[_c] = "Empleo y Ratios (M05/Φ)"


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


def _treeshap_single_signature(nodes: np.ndarray, dec: np.ndarray, node_to_int: Dict[int, int], n_features: int) -> np.ndarray:
    """Ejecuta el algoritmo TreeSHAP (Lundberg & Lee, 2018) sobre un vector único de decisiones."""
    phi = np.zeros(n_features, dtype=np.float64)
    is_leaf = nodes["is_leaf"].astype(bool)
    vals = nodes["value"]
    cnts = nodes["count"].astype(np.float64)
    lefts = nodes["left"]
    rights = nodes["right"]
    fidx = nodes["feature_idx"]

    def _recurse(node: int, mf: List[int], mz: List[float], mo: List[float], mw: List[float],
                 pz: float, po: float, pi: int) -> None:
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
    """
    Calcula valores TreeSHAP exactos (Lundberg & Lee, 2018, algoritmo tree_path_dependent)
    en espacio log-odds para HistGradientBoostingClassifier sin requerir `shap`.
    """
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


def _compute_shap_without_library(model: Any, X_mat: np.ndarray) -> Tuple[np.ndarray, str]:
    """
    Respaldo sin dependencia externa `shap`:
    - Si es LightGBM (`booster_`), usa TreeSHAP nativo en C++ (`pred_contrib=True`).
    - Si es HistGradientBoostingClassifier (`_predictors`), usa TreeSHAP exacto en NumPy/Python.
    """
    if hasattr(model, "booster_"):
        raw = np.asarray(model.booster_.predict(X_mat, pred_contrib=True))
        return raw[:, :-1], "TreeSHAP nativo de LightGBM (pred_contrib=True)"
    if hasattr(model, "_predictors"):
        return _histgb_tree_contribs(model, X_mat), "TreeSHAP exacto sin librería externa (HistGBDT)"
    raise ImportError(
        "Se requiere el paquete 'shap' (o LightGBM / HistGBDT) para explicar este tipo de estimador."
    )


def _plot_native_beeswarm(
    shap_vals: np.ndarray,
    X_mat: np.ndarray,
    feature_names: List[str],
    max_display: int = 15,
    title: str = "Importancia Local de Atributos (Test OOT 2025) — Top 15",
):
    """Dibuja un gráfico beeswarm en Matplotlib puro cuando `shap` no está disponible."""
    import matplotlib.pyplot as plt

    mean_abs = np.abs(shap_vals).mean(axis=0)
    top_idx = np.argsort(mean_abs)[-max_display:]  # orden ascendente para y=0..k-1

    rng = np.random.default_rng(42)
    fig, ax = plt.subplots(figsize=(9.5, 6.0))
    for y_pos, col_idx in enumerate(top_idx):
        s_col = shap_vals[:, col_idx]
        x_col = X_mat[:, col_idx].astype(float)
        vmin, vmax = np.nanpercentile(x_col, 2), np.nanpercentile(x_col, 98)
        x_norm = np.clip((x_col - vmin) / max(1e-12, vmax - vmin), 0.0, 1.0)
        jitter = rng.uniform(-0.28, 0.28, size=len(s_col))
        sc = ax.scatter(
            s_col, y_pos + jitter, c=x_norm, cmap="coolwarm",
            alpha=0.55, s=10, edgecolors="none",
        )

    ax.axvline(0.0, color="gray", linestyle="--", linewidth=1.0)
    ax.set_yticks(range(len(top_idx)))
    ax.set_yticklabels([feature_names[i] for i in top_idx])
    ax.set_xlabel("Contribución en log-odds hacia pobreza monetaria")
    ax.set_title(title, fontweight="bold")
    cbar = plt.colorbar(sc, ax=ax, pad=0.02)
    cbar.set_label("Valor del atributo (bajo -> alto)")
    cbar.set_ticks([0.0, 1.0])
    cbar.set_ticklabels(["Bajo", "Alto"])
    plt.tight_layout()
    return fig


def compute_treeshap_analysis(
    tree_artifact: Dict[str, Any],
    df_2025_test: pd.DataFrame,
    save_dir: Optional[Path] = None,
    show: bool = True,
) -> Dict[str, Any]:
    """
    Ejecuta TreeSHAP sobre el ensamble de árboles (LightGBM_GBDT o Random_Forest)
    evaluado en Test 2025 (N=3,199):
    - Beeswarm global de las Top-15 features codificadas
    - Agregación exacta por variable original (28 variables) y por bloque temático
    - Gráficos de dependencia parcial en variables clave (hacinamiento, ocupación, educación)
    """
    import matplotlib.pyplot as plt

    try:
        import shap
        has_shap = True
    except ImportError:
        shap = None
        has_shap = False

    pipe = tree_artifact["pipe"]
    cleaner = pipe.named_steps["cleaner"]
    preprocessor = pipe.named_steps["preprocessor"]
    model = pipe.named_steps["model"]

    X_eval, _, _ = prepare_xy_data(df_2025_test, features=tree_artifact["features"])
    X_clean = cleaner.transform(X_eval)
    X_mat = preprocessor.transform(X_clean)

    feat_names = list(preprocessor.get_feature_names_out())
    clean_feat_names = [f.split("__", 1)[-1] for f in feat_names]

    if has_shap:
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            explainer = shap.TreeExplainer(model)
            shap_vals_raw = explainer.shap_values(X_mat)

        # Normalizar formato según versión de shap / tipo de modelo (clase positiva 1)
        if isinstance(shap_vals_raw, list):
            shap_vals = np.asarray(shap_vals_raw[1])
        elif np.asarray(shap_vals_raw).ndim == 3:
            shap_vals = np.asarray(shap_vals_raw)[:, :, 1]
        else:
            shap_vals = np.asarray(shap_vals_raw)
    else:
        shap_vals, method_label = _compute_shap_without_library(model, X_mat)
        print(f"[compute_treeshap_analysis] Paquete 'shap' no instalado en este kernel; usando {method_label}.")

    mean_abs_encoded = np.abs(shap_vals).mean(axis=0)
    encoded_imp_df = pd.DataFrame({
        "Feature_Codificada": clean_feat_names,
        "Variable_Original": [_map_encoded_name_to_original(f) for f in feat_names],
        "Mean_Abs_SHAP": mean_abs_encoded,
    }).sort_values(by="Mean_Abs_SHAP", ascending=False).reset_index(drop=True)

    # Agregación aditiva exacta por variable original R^28 y por bloque temático
    orig_imp_df = (
        encoded_imp_df.groupby("Variable_Original", as_index=False)["Mean_Abs_SHAP"]
        .sum()
        .sort_values(by="Mean_Abs_SHAP", ascending=False)
        .reset_index(drop=True)
    )
    orig_imp_df["Bloque"] = orig_imp_df["Variable_Original"].map(lambda c: _BLOCK_MAP.get(c, "Otro"))
    total_shap = orig_imp_df["Mean_Abs_SHAP"].sum()
    orig_imp_df["Participacion_%"] = (orig_imp_df["Mean_Abs_SHAP"] / max(1e-12, total_shap)) * 100.0

    block_imp_df = (
        orig_imp_df.groupby("Bloque", as_index=False)[["Mean_Abs_SHAP", "Participacion_%"]]
        .sum()
        .sort_values(by="Participacion_%", ascending=False)
        .reset_index(drop=True)
    )

    # Figuras TreeSHAP
    fig_beeswarm = None
    fig_dep = None
    try:
        if has_shap:
            plt.figure(figsize=(9.5, 6.0))
            shap.summary_plot(shap_vals, X_mat, feature_names=clean_feat_names, max_display=15, show=False)
            plt.title("TreeSHAP Global (Test OOT 2025) — Top 15 Atributos Predictivos", fontweight="bold")
            plt.tight_layout()
            fig_beeswarm = plt.gcf()
        else:
            fig_beeswarm = _plot_native_beeswarm(
                shap_vals,
                X_mat,
                feature_names=clean_feat_names,
                max_display=15,
                title="TreePath Global (Test OOT 2025) — Top 15 Atributos Predictivos",
            )
        if save_dir is not None:
            try:
                Path(save_dir).mkdir(parents=True, exist_ok=True)
                fig_beeswarm.savefig(Path(save_dir) / "shap_beeswarm_2025.png", dpi=300, bbox_inches="tight")
                fig_beeswarm.savefig(Path(save_dir) / "shap_beeswarm_2025.pdf", bbox_inches="tight")
            except OSError as e:
                print(f"[TreeSHAP] Aviso al guardar beeswarm: {e}")
        if show:
            plt.show()
        else:
            plt.close(fig_beeswarm)

        # Gráficos de dependencia parcial en 3 variables estructurales clave (escala original)
        dep_vars = ["personas_por_hab", "ocupados_por_miembro", "educ_jefe"]
        fig_dep, axes = plt.subplots(1, 3, figsize=(15, 4.3))
        for ax, var_name in zip(axes, dep_vars):
            if var_name in clean_feat_names:
                j = clean_feat_names.index(var_name)
                ax.scatter(
                    X_clean[var_name].values,
                    shap_vals[:, j],
                    c=X_clean["educ_max_hogar"].values if "educ_max_hogar" in X_clean else None,
                    cmap="coolwarm",
                    alpha=0.45,
                    s=14,
                )
                ax.axhline(0.0, color="black", linestyle="--", linewidth=0.9)
                ax.set_xlabel(f"{var_name} (valor original)")
                ax.set_ylabel("Valor SHAP (log-odds pobreza)")
                ax.set_title(f"Dependencia: {var_name}", fontweight="bold")
        plt.suptitle("Dependencia Parcial TreeSHAP en Hacinamiento, Empleo y Educación (Test 2025)", fontweight="bold")
        plt.tight_layout()
        if save_dir is not None:
            try:
                fig_dep.savefig(Path(save_dir) / "shap_dependence_2025.png", dpi=300, bbox_inches="tight")
                fig_dep.savefig(Path(save_dir) / "shap_dependence_2025.pdf", bbox_inches="tight")
            except OSError as e:
                print(f"[TreeSHAP] Aviso al guardar dependencia: {e}")
        if show:
            plt.show()
        else:
            plt.close(fig_dep)
    except Exception as e:
        print(f"[TreeSHAP] Aviso al graficar: {e}")

    return {
        "shap_values": shap_vals,
        "feature_names": clean_feat_names,
        "encoded_importance": encoded_imp_df,
        "original_importance": orig_imp_df,
        "block_importance": block_imp_df,
    }


# =============================================================================
# 5. AUDITORÍA DE EQUIDAD POR SUBGRUPOS EN TEST 2025 (IMPLICANCIAS ÉTICAS)
# =============================================================================

def audit_subgroup_fairness_2025(
    df_2025_test: pd.DataFrame,
    probs_2025: Dict[str, np.ndarray],
    fitted_artifacts: Dict[str, Dict[str, Any]],
    model_name: str = "LightGBM_GBDT",
) -> pd.DataFrame:
    """
    Evalúa si el modelo elegido presenta sesgos de exclusión o inclusión dispares
    entre subgrupos sensibles en Test OOT 2025:
    - Sexo de jefatura (jefe_mujer == 1 vs 0)
    - Hogares secundarios sin datos físicos de vivienda (sin_datos_vivienda == 1 vs 0)
    - Cobertura previsional del jefe (jefe_sin_pension == 1 vs 0)
    """
    y_true = df_2025_test[TARGET_COL].values.astype(int)
    scores = probs_2025[model_name]
    tau = float(fitted_artifacts[model_name]["metrics_cv"]["Tau_Rec70"])
    y_pred_tau = (scores >= tau).astype(int)

    # Umbral de corte global para B = 20%
    k_global = int(round(0.20 * len(y_true)))
    thr_b20 = float(np.sort(scores)[::-1][k_global - 1])
    sel_b20 = scores >= thr_b20

    subgroups = [
        ("Global Test 2025", np.ones(len(df_2025_test), dtype=bool)),
        ("Jefatura: Mujer (1)", df_2025_test["jefe_mujer"] == 1),
        ("Jefatura: Hombre (0)", df_2025_test["jefe_mujer"] == 0),
        ("Hogar Secundario sin M01 (1)", df_2025_test["sin_datos_vivienda"] == 1),
        ("Hogar Principal con M01 (0)", df_2025_test["sin_datos_vivienda"] == 0),
        ("Jefe Sin Pensión (1)", df_2025_test["jefe_sin_pension"] == 1),
        ("Jefe Con Pensión (0)", df_2025_test["jefe_sin_pension"] == 0),
    ]

    rows = []
    for label, mask in subgroups:
        m = mask.values if isinstance(mask, pd.Series) else mask
        y_sub = y_true[m]
        s_sub = scores[m]
        sel_sub = sel_b20[m]
        pred_sub = y_pred_tau[m]

        pob = y_sub == 1
        tp_b = int((sel_sub & pob).sum())
        fp_b = int((sel_sub & ~pob).sum())
        fn_b = int((~sel_sub & pob).sum())

        rows.append({
            "Subgrupo": label,
            "N_Hogares": int(m.sum()),
            "Pobreza_Real_%": round(float(y_sub.mean()) * 100.0, 2),
            "Tasa_Seleccion_B20_%": round(float(sel_sub.mean()) * 100.0, 2),
            "PR_AUC": round(float(average_precision_score(y_sub, s_sub)), 4),
            "ROC_AUC": round(float(roc_auc_score(y_sub, s_sub)), 4),
            "EE_B20": round(fn_b / max(1, tp_b + fn_b), 4),
            "IE_B20": round(fp_b / max(1, tp_b + fp_b), 4),
            "Recall_Tau": round(float(recall_score(y_sub, pred_sub, zero_division=0)), 4),
            "Prec_Tau": round(float(precision_score(y_sub, pred_sub, zero_division=0)), 4),
        })
    return pd.DataFrame(rows)


if __name__ == "__main__":
    import matplotlib
    matplotlib.use("Agg")
    from src.dataset import load_train_test_master
    from src.models import run_spatial_cv_benchmark

    print("=== Ejecución Completa del Sprint 7: src/evaluation.py ===")
    df_2024, df_2025_test = load_train_test_master()

    # 1. Entrenar modelos únicamente en 2024 (CV espacial GroupKFold(5))
    best_cv_df, _, artifacts_2024 = run_spatial_cv_benchmark(df_2024, n_splits=5, verbose=True)

    # 2. Evaluación ciega OOT 2025
    oot_df, probs_2025 = evaluate_oot_2025(artifacts_2024, df_2025_test)
    print("\n1. Resultados Fuera de Tiempo (ENAHO 2025, N = 3,199 hogares independientes):")
    cols_oot = [
        "Modelo", "PR_AUC_2024_CV", "PR_AUC_2025", "PR_AUC_2025_Pond",
        "Delta_Temp_PR (H4)", "ROC_AUC_2025", "EE_B20_2025", "IE_B20_2025",
        "EE_B20_2025_Pond", "Recall_Tau_2025 (H3)", "Prec_Tau_2025 (H3)", "Brier_2025"
    ]
    print(oot_df[cols_oot].to_string(index=False))

    # 3. Cluster Bootstrap (1,000 réplicas) para contraste de H1 a H4
    print("\n2. Contraste Formal de Hipótesis H1-H4 (Cluster Bootstrap, 1,000 réplicas):")
    hyp_df = run_cluster_bootstrap_hypotheses(df_2024, df_2025_test, artifacts_2024, probs_2025, n_boot=1000)
    print(hyp_df.to_string(index=False))

    # 4. Curvas EE-IE en 2025
    curves_df = compute_ee_ie_curves(df_2025_test[TARGET_COL].values, probs_2025)
    out_fig_dir = Path("/Users/gaelarias/.gemini/antigravity-cli/brain/58d3a516-9469-46e5-b82d-2211dad9a100")
    plot_ee_ie_curves(curves_df, save_path=out_fig_dir / "ee_ie_curves_2025.png", show=False)

    # 5. TreeSHAP sobre LightGBM_GBDT en Test 2025
    print("\n3. Explicabilidad TreeSHAP (LightGBM_GBDT sobre Test 2025):")
    shap_res = compute_treeshap_analysis(artifacts_2024["LightGBM_GBDT"], df_2025_test, save_dir=out_fig_dir, show=False)
    print("\n   Top 12 Variables Originales (R^28) por |SHAP| Agregado:")
    print(shap_res["original_importance"].head(12).to_string(index=False))
    print("\n   Contribución por Bloque Temático:")
    print(shap_res["block_importance"].to_string(index=False))

    # 6. Auditoría de equidad por subgrupos (Implicancias Éticas)
    print("\n4. Auditoría de Equidad por Subgrupos en Test 2025 (LightGBM_GBDT):")
    fair_df = audit_subgroup_fairness_2025(df_2025_test, probs_2025, artifacts_2024, model_name="LightGBM_GBDT")
    print(fair_df.to_string(index=False))
