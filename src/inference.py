"""
Módulo de Producción, Exportación Anti-Overfitting e Inferencia sobre Encuestas (Sprint 7B).

Responsabilidades:
1. Reentrenar el modelo ganador (`Stacking_Ensemble`) y su acompañante explicativo (`HistGBDT`)
   sobre los microdatos combinados 2024+2025 **deduplicando los 930 hogares repetidos del panel**
   (conservando la observación más reciente de 2025 -> N = 7,289 hogares únicos en 706 conglomerados).
2. Regularizar la arquitectura (`Stacking_Tight`) y auditar explícitamente la brecha
   Train vs. GroupKFold(5) Out-of-Fold (OOF) para prevenir overfitting.
3. Calibrar y congelar los umbrales (`tau_rec70` y corte presupuestal `B = 20%`) estrictamente
   sobre predicciones Out-of-Fold (OOF) antes de serializar el paquete en `models/winner_bundle.joblib`.
4. Traducir respuestas humanas en español (catálogo oficial INEI ENAHO) al vector canónico R^28,
   calcular probabilidades, percentiles de riesgo, decisión de focalización y explicaciones locales.
"""
import sys
import warnings
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Tuple, Optional, Any, Union, Sequence

import joblib
import numpy as np
import pandas as pd
from joblib import Parallel, delayed, parallel_config
from sklearn.base import clone
from sklearn.ensemble import (
    ExtraTreesClassifier,
    HistGradientBoostingClassifier,
    RandomForestClassifier,
    StackingClassifier,
)
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import GroupKFold

_ROOT = Path(__file__).resolve().parents[1]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from src.dataset import KEY_HOGAR, build_combined_dataset
from src.evaluation import _histgb_tree_contribs, _map_encoded_name_to_original
from src.models import compute_targeting_metrics
from src.preprocessing import (
    AUX_GROUP_COL,
    CANONICAL_FEATURES_28,
    CATEGORICAL_COLS,
    GROUP_COL,
    NUMERIC_COLS,
    TARGET_COL,
    build_full_pipeline,
)

DEFAULT_BUNDLE_PATH = _ROOT / "models" / "winner_bundle.joblib"


# =============================================================================
# CATÁLOGO OFICIAL DE PREGUNTAS ENAHO (INEI CED-01-100 / 300 / 500)
# =============================================================================

ENAHO_SURVEY_CATALOG: Dict[str, Dict[str, Any]] = {
    "tipo_vivienda": {
        "prompt": "Tipo de vivienda (P101)",
        "options": {
            1: "Casa independiente",
            2: "Departamento en edificio",
            3: "Vivienda en quinta",
            4: "Vivienda en casa de vecindad (callejón, solar o corralón)",
            5: "Choza o cabaña",
            6: "Vivienda improvisada",
            7: "Local no destinado para habitación humana",
            8: "Otro",
        },
    },
    "material_pared": {
        "prompt": "Material predominante en las paredes exteriores (P102A)",
        "options": {
            1: "Ladrillo o bloque de cemento",
            2: "Piedra o sillar con cal o cemento",
            3: "Adobe",
            4: "Tapia",
            5: "Quincha (caña con barro)",
            6: "Piedra con barro",
            7: "Madera (pona, tornillo, etc.)",
            8: "Triplay / calamina / estera",
            9: "Otro material",
        },
    },
    "material_piso": {
        "prompt": "Material predominante en los pisos (P103)",
        "options": {
            1: "Parquet o madera pulida",
            2: "Láminas asfálticas, vinílicos o similares",
            3: "Losetas, terrazos o similares",
            4: "Madera (pona, tornillo, etc.)",
            5: "Cemento",
            6: "Tierra",
            7: "Otro material",
        },
    },
    "tenencia_vivienda": {
        "prompt": "Régimen de tenencia de la vivienda (P105)",
        "options": {
            1: "Alquilada",
            2: "Propia, totalmente pagada",
            3: "Propia, por invasión",
            4: "Propia, comprándola a plazos",
            5: "Cedida por centro de trabajo",
            6: "Cedida por otro hogar o institución",
            7: "Otra forma",
        },
    },
    "fuente_agua": {
        "prompt": "Procedencia principal del agua en el hogar (P110)",
        "options": {
            1: "Red pública dentro de la vivienda",
            2: "Red pública fuera de la vivienda (dentro del edificio)",
            3: "Pilón o pileta de uso público",
            4: "Camión-cisterna u otro similar",
            5: "Pozo (agua subterránea)",
            6: "Manantial o puquio",
            8: "Río, acequia, lago o laguna",
            7: "Otra",
        },
    },
    "agua_todos_los_dias": {
        "prompt": "¿Tiene servicio de agua todos los días de la semana? (P110C)",
        "options": {
            1: "Sí, todos los días",
            2: "No, servicio restringido / por horas o días",
        },
    },
    "conexion_bano": {
        "prompt": "El baño o servicio higiénico está conectado a (P111)",
        "options": {
            1: "Red pública de desagüe dentro de la vivienda",
            2: "Red pública de desagüe fuera de la vivienda (dentro del edificio)",
            3: "Letrina (con tratamiento)",
            4: "Pozo séptico, tanque séptico o biodigestor",
            5: "Pozo ciego o negro",
            6: "Río, acequia, canal o similar",
            9: "Campo abierto o al aire libre",
            7: "Otra",
        },
    },
    "combustible_cocina": {
        "prompt": "Combustible principal utilizado para cocinar (P113)",
        "options": {
            1: "Electricidad",
            2: "Gas (balón GLP)",
            3: "Gas natural (sistema de tuberías)",
            5: "Carbón",
            6: "Leña",
            9: "Bosta / estiércol",
            7: "Otro",
            8: "No cocinan en el hogar",
        },
    },
    "tiene_internet": {
        "prompt": "¿El hogar cuenta con conexión a Internet (fijo/móvil)? (P1144)",
        "options": {
            1: "Sí tiene Internet",
            0: "No tiene Internet",
        },
    },
    "jefe_mujer": {
        "prompt": "Sexo de la jefa / jefe del hogar (P207)",
        "options": {
            0: "Hombre",
            1: "Mujer",
        },
    },
    "educ_nivel": {
        "prompt": "Último nivel de estudios aprobado (P301)",
        "options": {
            1: "Sin nivel",
            2: "Educación inicial / básica especial",
            3: "Primaria incompleta",
            4: "Primaria completa",
            5: "Secundaria incompleta",
            6: "Secundaria completa",
            7: "Superior no universitaria incompleta",
            8: "Superior no universitaria completa",
            9: "Superior universitaria incompleta",
            10: "Superior universitaria completa",
            11: "Maestría / Doctorado",
        },
    },
    "jefe_ocupado": {
        "prompt": "¿El jefe/a de hogar trabajó o tuvo empleo la semana pasada? (OCU500)",
        "options": {
            1: "Sí (Ocupado)",
            0: "No (Desempleado o inactivo)",
        },
    },
    "jefe_cat_ocupacional": {
        "prompt": "Categoría ocupacional del jefe/a de hogar (P507)",
        "options": {
            1: "Empleador o patrono",
            2: "Trabajador independiente",
            3: "Empleado",
            4: "Obrero",
            5: "Trabajador familiar no remunerado",
            6: "Trabajador del hogar",
            7: "Otro",
        },
    },
    "jefe_empresa_ruc": {
        "prompt": "Formalidad SUNAT de la empresa donde trabaja el jefe/a (P510A1)",
        "options": {
            1: "Persona Jurídica (S.A., S.R.L., E.I.R.L., sector público, etc.)",
            2: "Persona Natural con R.U.C., RUS o RER",
            3: "No está registrado (sin RUC / informal)",
        },
    },
    "jefe_sin_pension": {
        "prompt": "¿El jefe/a está afiliado a algún sistema de pensiones (AFP/ONP/otro)? (P558A)",
        "options": {
            0: "Sí está afiliado (AFP, ONP, Ley 20530 u otro)",
            1: "No está afiliado a ningún sistema de pensiones",
        },
    },
    "ubigeo": {
        "prompt": "Distrito de residencia en Lima Metropolitana / Callao (UBIGEO 6 dígitos, usado solo para imputación espacial en hogares secundarios)",
        "options": {
            "150132": "San Juan de Lurigancho (150132)",
            "070106": "Ventanilla - Callao (070106)",
            "150108": "Chorrillos (150108)",
            "150110": "Comas (150110)",
            "150103": "Ate (150103)",
            "150142": "Villa El Salvador (150142)",
            "150140": "Santiago de Surco (150140)",
            "150122": "Miraflores (150122)",
            "070101": "Callao Cercado (070101)",
            "__nuevo_distrito__": "Otro distrito / No especificado (usa mediana global)",
        },
    },
}


# Perfiles demostrativos realistas para pruebas rápidas en script y notebook
PRESET_HOUSEHOLDS: Dict[str, Dict[str, Any]] = {
    "vulnerable_hacinado": {
        "descripcion": "Hogar numeroso de Lima periférica, piso cemento/tierra, hacinado y empleo informal sin pensión",
        "ubigeo": "150132",        # San Juan de Lurigancho
        "es_hogar_secundario": False,
        "tipo_vivienda": 6,        # Vivienda improvisada
        "material_pared": 8,       # Triplay/calamina/estera
        "material_piso": 6,        # Tierra
        "total_habitaciones": 2,
        "total_dormitorios": 1,
        "tenencia_vivienda": 3,    # Propia por invasión
        "fuente_agua": 4,          # Camión-cisterna
        "agua_todos_los_dias": None,
        "conexion_bano": 5,        # Pozo ciego/negro
        "combustible_cocina": 2,   # Balón GLP
        "tiene_internet": 0,
        "n_miembros": 6,
        "n_ninos_0_5": 2,
        "n_menores_14": 3,
        "n_mayores_65": 0,
        "jefe_edad": 36,
        "jefe_mujer": 1,
        "educ_jefe": 4,            # Primaria completa
        "educ_max_hogar": 5,       # Secundaria incompleta
        "n_ocupados": 1,
        "jefe_ocupado": 1,
        "jefe_horas_semanales": 48.0,
        "jefe_cat_ocupacional": 2, # Independiente
        "jefe_empresa_ruc": 3,     # Sin RUC
        "jefe_sin_pension": 1,     # Sin pensión
    },
    "secundario_sin_m01": {
        "descripcion": "Hogar secundario (joven pareja con hijo en vivienda familiar compartida en Chorrillos, sin ficha M01)",
        "ubigeo": "150108",        # Chorrillos (activa cascada distrital: mediana 4.0 hab / 3.0 dorm)
        "es_hogar_secundario": True,
        "tenencia_vivienda": 6,    # Cedida por otro hogar
        "fuente_agua": 1,
        "agua_todos_los_dias": 1,
        "conexion_bano": 1,
        "combustible_cocina": 2,
        "tiene_internet": 1,
        "n_miembros": 4,
        "n_ninos_0_5": 1,
        "n_menores_14": 2,
        "n_mayores_65": 0,
        "jefe_edad": 29,
        "jefe_mujer": 0,
        "educ_jefe": 6,            # Secundaria completa
        "educ_max_hogar": 6,
        "n_ocupados": 1,
        "jefe_ocupado": 1,
        "jefe_horas_semanales": 45.0,
        "jefe_cat_ocupacional": 4, # Obrero
        "jefe_empresa_ruc": 3,     # Sin RUC
        "jefe_sin_pension": 1,
    },
    "formal_estable": {
        "descripcion": "Hogar nuclear en departamento con empleo formal, educación superior e internet",
        "ubigeo": "150140",        # Santiago de Surco
        "es_hogar_secundario": False,
        "tipo_vivienda": 2,        # Departamento
        "material_pared": 1,       # Ladrillo
        "material_piso": 1,        # Parquet
        "total_habitaciones": 4,
        "total_dormitorios": 2,
        "tenencia_vivienda": 4,    # Propia comprándola a plazos
        "fuente_agua": 1,
        "agua_todos_los_dias": 1,
        "conexion_bano": 1,
        "combustible_cocina": 3,   # Gas natural
        "tiene_internet": 1,
        "n_miembros": 3,
        "n_ninos_0_5": 0,
        "n_menores_14": 1,
        "n_mayores_65": 0,
        "jefe_edad": 42,
        "jefe_mujer": 0,
        "educ_jefe": 10,           # Universitaria completa
        "educ_max_hogar": 11,      # Maestría/Doctorado
        "n_ocupados": 2,
        "jefe_ocupado": 1,
        "jefe_horas_semanales": 44.0,
        "jefe_cat_ocupacional": 3, # Empleado
        "jefe_empresa_ruc": 1,     # Persona Jurídica
        "jefe_sin_pension": 0,     # Afiliado AFP/ONP
    },
}


# =============================================================================
# CONSTRUCCIÓN Y ENTRENAMIENTO ANTI-OVERFITTING DEL MODELO DE PRODUCCIÓN
# =============================================================================

def load_deduplicated_pooled_dataset(
    years: Sequence[int] = (2024, 2025),
    data_root: Union[str, Path] = _ROOT / "Data",
    verbose: bool = True,
) -> pd.DataFrame:
    """
    Construye el conjunto multi-año combinado (ej. 2024 + 2025) y **deduplica los hogares
    repetidos del panel longitudinal** conservando únicamente su registro más reciente (`keep='last'`),
    evitando que un mismo hogar se duplique entre años o sobre-pese el ajuste.
    """
    df_all = build_combined_dataset(years=tuple(years), data_root=data_root)
    n_raw = len(df_all)
    df_unique = (
        df_all.sort_values("year")
        .drop_duplicates(subset=KEY_HOGAR, keep="last")
        .reset_index(drop=True)
    )
    if verbose:
        print(
            f"[load_deduplicated_pooled_dataset] Años={list(years)} | Bruto={n_raw:,d} -> "
            f"Únicos={len(df_unique):,d} ({n_raw - len(df_unique):,d} repetidos deduplicados) | "
            f"Conglomerados={df_unique[GROUP_COL].nunique():,d}"
        )
    return df_unique


def build_production_gbdt_pipeline() -> Any:
    """HistGBDT regularizado (100% compatible en Python 3.12 LTS y scikit-learn) usado como explicador."""
    hgb = HistGradientBoostingClassifier(
        max_iter=120,
        learning_rate=0.03,
        max_leaf_nodes=10,
        max_depth=4,
        min_samples_leaf=45,
        l2_regularization=8.0,
        random_state=42,
    )
    return build_full_pipeline(
        hgb,
        numeric_cols=NUMERIC_COLS,
        categorical_cols=CATEGORICAL_COLS,
        scale_numeric=False,
        scaler_type="none",
        one_hot=True,
    )


def build_production_stacking_pipeline(n_jobs_inner: int = 1) -> Any:
    """
    Construye el Stacking_Ensemble ganador con regularización ajustada (`Stacking_Tight`)
    para minimizar la brecha Train vs. OOF sin sacrificar PR-AUC ni calibración.
    """
    hgb = HistGradientBoostingClassifier(
        max_iter=120,
        learning_rate=0.03,
        max_leaf_nodes=10,
        max_depth=4,
        min_samples_leaf=45,
        l2_regularization=8.0,
        random_state=42,
    )
    stack = StackingClassifier(
        estimators=[
            ("lr", LogisticRegression(C=0.15, l1_ratio=0.5, solver="saga", max_iter=1200, random_state=42)),
            ("rf", RandomForestClassifier(
                n_estimators=250, max_depth=7, min_samples_leaf=30,
                max_features="sqrt", n_jobs=n_jobs_inner, random_state=42,
            )),
            ("et", ExtraTreesClassifier(
                n_estimators=250, max_depth=8, min_samples_leaf=30,
                max_features="sqrt", n_jobs=n_jobs_inner, random_state=42,
            )),
            ("gb", hgb),
        ],
        final_estimator=LogisticRegression(C=0.2, random_state=42),
        cv=5,
        n_jobs=n_jobs_inner,
    )
    return build_full_pipeline(
        stack,
        numeric_cols=NUMERIC_COLS,
        categorical_cols=CATEGORICAL_COLS,
        scale_numeric=True,
        scaler_type="robust",
        one_hot=True,
    )


def _eval_fold_pair(tr_idx, va_idx, X, y_arr, base_stack_pipe, base_gbdt_pipe):
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        ps = clone(base_stack_pipe).fit(X.iloc[tr_idx], y_arr[tr_idx])
        pg = clone(base_gbdt_pipe).fit(X.iloc[tr_idx], y_arr[tr_idx])
        return (
            va_idx,
            ps.predict_proba(X.iloc[va_idx])[:, 1],
            pg.predict_proba(X.iloc[va_idx])[:, 1],
        )


def train_and_export_deployment_bundle(
    years: Sequence[int] = (2024, 2025),
    data_root: Union[str, Path] = _ROOT / "Data",
    save_path: Optional[Union[str, Path]] = DEFAULT_BUNDLE_PATH,
    budget_coverage: float = 0.20,
    verbose: bool = True,
) -> Tuple[Dict[str, Any], pd.DataFrame]:
    """
    Entrena el modelo ganador (`Stacking_Ensemble`) + explicador (`HistGBDT`) sobre datos
    multi-año deduplicados, calibra umbrales estrictamente Out-Of-Fold (`GroupKFold(5)`),
    audita la brecha Train vs. OOF para descartar overfitting y exporta el paquete `.joblib`.
    """
    df_u = load_deduplicated_pooled_dataset(years=years, data_root=data_root, verbose=verbose)
    cols_in = [c for c in CANONICAL_FEATURES_28 + [GROUP_COL, AUX_GROUP_COL] if c in df_u.columns]
    X = df_u[cols_in].copy()
    y_arr = df_u[TARGET_COL].values.astype(int)
    grp_arr = df_u[GROUP_COL].values

    base_stack_cv = build_production_stacking_pipeline(n_jobs_inner=1)
    base_gbdt_cv = build_production_gbdt_pipeline()

    gkf = GroupKFold(n_splits=5)
    splits = list(gkf.split(X, y_arr, grp_arr))

    with parallel_config(backend="loky", inner_max_num_threads=1):
        fold_outputs = Parallel(n_jobs=-1)(
            delayed(_eval_fold_pair)(tr_idx, va_idx, X, y_arr, base_stack_cv, base_gbdt_cv)
            for tr_idx, va_idx in splits
        )

    oof_stack = np.zeros(len(y_arr), dtype=float)
    oof_gbdt = np.zeros(len(y_arr), dtype=float)
    for va_idx, p_st, p_gb in fold_outputs:
        oof_stack[va_idx] = p_st
        oof_gbdt[va_idx] = p_gb

    # Ajuste final sobre el 100% de los hogares únicos (sin tocar los umbrales OOF ya fijados)
    pipe_stack_full = build_production_stacking_pipeline(n_jobs_inner=-1)
    pipe_gbdt_full = build_production_gbdt_pipeline()
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        pipe_stack_full.fit(X, y_arr)
        pipe_gbdt_full.fit(X, y_arr)
        ins_stack = pipe_stack_full.predict_proba(X)[:, 1]
        ins_gbdt = pipe_gbdt_full.predict_proba(X)[:, 1]

    m_oof_stack = compute_targeting_metrics(y_arr, oof_stack, budget_coverage=budget_coverage)
    m_ins_stack = compute_targeting_metrics(y_arr, ins_stack, budget_coverage=budget_coverage)
    m_oof_gbdt = compute_targeting_metrics(y_arr, oof_gbdt, budget_coverage=budget_coverage)
    m_ins_gbdt = compute_targeting_metrics(y_arr, ins_gbdt, budget_coverage=budget_coverage)

    audit_df = pd.DataFrame([
        {
            "Modelo": "Stacking_Ensemble (Ganador)",
            "N_Hogares_Unicos": len(y_arr),
            "PR_AUC_Train": round(m_ins_stack["PR_AUC"], 4),
            "PR_AUC_OOF": round(m_oof_stack["PR_AUC"], 4),
            "Gap_Overfit_PR": round(m_ins_stack["PR_AUC"] - m_oof_stack["PR_AUC"], 4),
            "ROC_AUC_OOF": round(m_oof_stack["ROC_AUC"], 4),
            "EE_B20_OOF": round(m_oof_stack["EE_B20"], 4),
            "Brier_OOF": round(m_oof_stack["Brier"], 4),
            "Tau_Rec70_OOF": round(m_oof_stack["Tau_Rec70"], 4),
        },
        {
            "Modelo": "HistGBDT (Explicador Local)",
            "N_Hogares_Unicos": len(y_arr),
            "PR_AUC_Train": round(m_ins_gbdt["PR_AUC"], 4),
            "PR_AUC_OOF": round(m_oof_gbdt["PR_AUC"], 4),
            "Gap_Overfit_PR": round(m_ins_gbdt["PR_AUC"] - m_oof_gbdt["PR_AUC"], 4),
            "ROC_AUC_OOF": round(m_oof_gbdt["ROC_AUC"], 4),
            "EE_B20_OOF": round(m_oof_gbdt["EE_B20"], 4),
            "Brier_OOF": round(m_oof_gbdt["Brier"], 4),
            "Tau_Rec70_OOF": round(m_oof_gbdt["Tau_Rec70"], 4),
        },
    ])

    cutoff_b20 = float(np.quantile(oof_stack, 1.0 - budget_coverage))
    bundle: Dict[str, Any] = {
        "winner_name": "Stacking_Ensemble",
        "selection_rule_2024": "Repeated_Spatial_CV_30runs_2024 (Opción 1B: PR_AUC_Mediana + Rank_Medio_PR sobre 704 conglomerados de ENAHO 2024)",
        "explainer_name": "HistGBDT_Regularizado",
        "train_years": list(years),
        "n_unique_households": int(len(y_arr)),
        "n_clusters": int(df_u[GROUP_COL].nunique()),
        "prevalence": float(y_arr.mean()),
        "features": list(CANONICAL_FEATURES_28),
        "pipe_stacking": pipe_stack_full,
        "pipe_gbdt": pipe_gbdt_full,
        "tau_rec70": float(m_oof_stack["Tau_Rec70"]),
        "cutoff_b20": cutoff_b20,
        "budget_coverage": float(budget_coverage),
        "oof_probs_sorted": np.sort(oof_stack.astype(np.float32)),
        "metrics_audit_records": audit_df.to_dict(orient="records"),
        "created_at": datetime.now().isoformat(timespec="seconds"),
    }

    if save_path is not None:
        out_path = Path(save_path)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        joblib.dump(bundle, out_path, compress=3)
        if verbose:
            print(f"✓ Paquete ganador guardado en: {out_path} ({out_path.stat().st_size / 1024:.1f} KB)")

    bundle["metrics_audit"] = audit_df

    if verbose:
        print("\n=== AUDITORÍA ANTI-OVERFITTING DEL MODELO DE PRODUCCIÓN (TRAIN VS. OOF) ===")
        print(audit_df.to_string(index=False))

    return bundle, audit_df


def load_deployment_bundle(path: Union[str, Path] = DEFAULT_BUNDLE_PATH) -> Dict[str, Any]:
    """Carga el paquete serializado `winner_bundle.joblib`."""
    p = Path(path)
    if not p.exists():
        raise FileNotFoundError(
            f"No existe el modelo exportado en '{p}'. Ejecuta `train_and_export_deployment_bundle()` primero."
        )
    bundle = joblib.load(p)
    if "metrics_audit" not in bundle and "metrics_audit_records" in bundle:
        bundle["metrics_audit"] = pd.DataFrame(bundle["metrics_audit_records"])
    return bundle


# =============================================================================
# CONSTRUCCIÓN DE VECTOR R^28 E INFERENCIA INDIVIDUAL CON EXPLICACIÓN LOCAL
# =============================================================================

def build_household_dataframe_from_answers(answers: Dict[str, Any]) -> pd.DataFrame:
    """
    Convierte un diccionario de respuestas humanas de encuesta al DataFrame exacto
    esperado por el Pipeline (28 variables canónicas + `conglomerado`).
    Calcula automáticamente ratios estructurales y aplica reglas de salto ENAHO.
    """
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
    """
    Evalúa un hogar encuestado usando el paquete ganador serializado:
    retorna probabilidad de pobreza, percentil respecto a Lima y Callao,
    dictamen binario (tau_rec70), elegibilidad en Top 20% y factores explicativos.
    """
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


def _format_driver_lines(df_drivers: pd.DataFrame, empty_msg: str) -> List[str]:
    if df_drivers.empty:
        return [f"     ({empty_msg})"]
    out = []
    for _, r in df_drivers.iterrows():
        val = r["Valor_Input"]
        val_str = "   N/A" if pd.isna(val) else f"{float(val):6.2f}"
        out.append(f"     • {r['Variable']:22s} = {val_str}  ({r['Contribucion_LogOdds']:+.3f} log-odds)")
    return out


def format_prediction_report(res: Dict[str, Any], label: str = "Hogar Evaluado") -> str:
    """Formatea un diagnóstico legible para consola y salidas del notebook."""
    lines = [
        "====================================================================",
        f" DIAGNÓSTICO DE FOCALIZACIÓN SOCIAL — {label}",
        "====================================================================",
        f" Probabilidad estimada de pobreza (Stacking): {res['prob_pobreza']*100:6.2f}%  (HistGBDT: {res['prob_gbdt']*100:5.2f}%)",
        f" Percentil de vulnerabilidad (Lima & Callao): Percentil {res['percentil_riesgo_lima']:5.1f} / 100",
        f" Dictamen operativo (tau = {res['tau_rec70']:.3f})        : "
        + ("PRIORITARIO / EN RIESGO DE POBREZA" if res["en_riesgo_tau"] else "NO PRIORITARIO (Debajo del umbral)"),
        f" Cupo presupuestal Top 20% (corte = {res['cutoff_b20']:.3f}): "
        + ("SÍ CALIFICA en el 20% más vulnerable" if res["prioritario_top20"] else "NO ingresa al Top 20%"),
        "",
        " [+] Principales factores que AUMENTAN el riesgo en este hogar:",
        *_format_driver_lines(res["factores_riesgo"], "Ningún factor con contribución positiva relevante"),
        "\n [-] Principales factores PROTECTORES que REDUCEN el riesgo:",
        *_format_driver_lines(res["factores_proteccion"], "Ningún factor protector relevante"),
        "====================================================================",
    ]
    return "\n".join(lines)


# =============================================================================
# ENCUESTA INTERACTIVA POR CONSOLA / CELDA
# =============================================================================

def _ask_int(prompt: str, min_val: int, max_val: int, default: Optional[int] = None) -> int:
    suffix = f" [por defecto={default}]" if default is not None else ""
    while True:
        raw = input(f"{prompt} ({min_val}-{max_val}){suffix}: ").strip()
        if raw == "" and default is not None:
            return default
        try:
            val = int(raw)
            if min_val <= val <= max_val:
                return val
        except ValueError:
            pass
        print(f"   -> Ingresa un entero entre {min_val} y {max_val}.")


def _ask_choice(catalog_key: str, default: Optional[int] = None) -> int:
    spec = ENAHO_SURVEY_CATALOG[catalog_key]
    print(f"\n{spec['prompt']}:")
    for code, desc in spec["options"].items():
        print(f"  [{code}] {desc}")
    valid = set(spec["options"].keys())
    suffix = f" [por defecto={default}]" if default is not None else ""
    while True:
        raw = input(f"Selecciona código{suffix}: ").strip()
        if raw == "" and default is not None and default in valid:
            return default
        try:
            val = int(raw)
            if val in valid:
                return val
        except ValueError:
            pass
        print(f"   -> Código inválido. Opciones válidas: {sorted(valid)}")


def run_interactive_survey(bundle: Dict[str, Any]) -> Dict[str, Any]:
    """
    Ejecuta la encuesta socioeconómica interactiva en español (compatible tanto con terminal
    como con celda de Jupyter), evalúa al hogar y muestra el reporte explicativo completo.
    """
    print("\n=== ENCUESTA SOCIOECONÓMICA DE HOGAR (ENAHO R^28 — LIMA METROPOLITANA Y CALLAO) ===")
    ubigeo_raw = input("Código UBIGEO distrital de 6 dígitos (ej. 150132 SJL, 150108 Chorrillos, 070106 Ventanilla) [Enter=__nuevo_distrito__]: ").strip()
    ubigeo_val = ubigeo_raw if (len(ubigeo_raw) == 6 and ubigeo_raw.isdigit()) else "__nuevo_distrito__"
    sec_raw = input("¿Es hogar secundario sin ficha física de vivienda (Módulo 01)? [s/N]: ").strip().lower()
    es_sec = sec_raw in {"s", "si", "sí", "y", "yes", "1"}

    answers: Dict[str, Any] = {"es_hogar_secundario": es_sec, "ubigeo": ubigeo_val}
    if not es_sec:
        answers["tipo_vivienda"] = _ask_choice("tipo_vivienda", default=1)
        answers["material_pared"] = _ask_choice("material_pared", default=1)
        answers["material_piso"] = _ask_choice("material_piso", default=5)
        tot_hab = _ask_int("\nTotal habitaciones (sin baño, cocina ni pasadizos)", 1, 20, default=3)
        answers["total_habitaciones"] = tot_hab
        answers["total_dormitorios"] = _ask_int("Dormitorios de uso exclusivo para dormir", 0, tot_hab, default=min(2, tot_hab))

    answers["tenencia_vivienda"] = _ask_choice("tenencia_vivienda", default=2)
    answers["fuente_agua"] = _ask_choice("fuente_agua", default=1)
    if answers["fuente_agua"] in (1, 2, 3):
        answers["agua_todos_los_dias"] = _ask_choice("agua_todos_los_dias", default=1)
    else:
        answers["agua_todos_los_dias"] = None
    answers["conexion_bano"] = _ask_choice("conexion_bano", default=1)
    answers["combustible_cocina"] = _ask_choice("combustible_cocina", default=2)
    answers["tiene_internet"] = _ask_choice("tiene_internet", default=1)

    n_miem = _ask_int("\nNúmero total de miembros residentes habituales del hogar", 1, 20, default=4)
    n_05 = _ask_int("Cantidad de niños de 0 a 5 años", 0, n_miem, default=0)
    n_14 = _ask_int("Cantidad total de menores de 14 años (incluye 0-5 años)", n_05, n_miem, default=n_05)
    n_65 = _ask_int("Cantidad de adultos de 65 años a más", 0, n_miem - n_14, default=0)
    answers.update({
        "n_miembros": n_miem,
        "n_ninos_0_5": n_05,
        "n_menores_14": n_14,
        "n_mayores_65": n_65,
        "jefe_edad": _ask_int("Edad del jefe/a de hogar (años)", 18, 100, default=45),
        "jefe_mujer": _ask_choice("jefe_mujer", default=0),
    })

    print("\n--- Nivel Educativo (Jefe y Máximo del Hogar) ---")
    ed_jefe = _ask_choice("educ_nivel", default=6)
    print("\nNivel educativo MÁXIMO entre todos los miembros del hogar (>= nivel del jefe):")
    ed_max = _ask_int("Ingresa código de nivel máximo (1-11)", int(ed_jefe), 11, default=max(int(ed_jefe), 6))
    answers["educ_jefe"] = ed_jefe
    answers["educ_max_hogar"] = ed_max

    print("\n--- Situación Laboral y Previsional ---")
    answers["n_ocupados"] = _ask_int("Número total de miembros ocupados en el hogar", 0, n_miem, default=1)
    jefe_ocup = _ask_choice("jefe_ocupado", default=1)
    answers["jefe_ocupado"] = jefe_ocup
    if jefe_ocup == 1:
        answers["jefe_horas_semanales"] = float(_ask_int("Horas semanales trabajadas del jefe/a", 1, 100, default=40))
        answers["jefe_cat_ocupacional"] = _ask_choice("jefe_cat_ocupacional", default=3)
        answers["jefe_empresa_ruc"] = _ask_choice("jefe_empresa_ruc", default=2)
    answers["jefe_sin_pension"] = _ask_choice("jefe_sin_pension", default=1)

    res = predict_single_household(bundle, answers)
    print("\n" + format_prediction_report(res, label="Encuesta del Usuario"))
    return res
