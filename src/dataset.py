"""
Construcción y consolidación del Big DataFrame a nivel hogar (Módulos 01 + 02 + 03 + 05 + 34).
Aplica el Operador de Reducción Relacional Phi (persona -> hogar) y la purga estricta
de panel longitudinal para el test 2025.

NOTA: Delimitado estrictamente a la integración de datos. Cero imputación de nulos ni escalado.
"""
import sys
from pathlib import Path
from typing import Optional, Union, Tuple, List
import pandas as pd
import numpy as np

# Asegurar importación tanto si se ejecuta desde raíz como desde src/
_ROOT = Path(__file__).resolve().parents[1]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from src.io_enaho import (
    load_all_raw_modules,
    load_modulo34,
    KEY_HOGAR,
    KEY_PERSONA,
)


def build_master_dataset(
    year: int,
    data_root: Union[str, Path] = "Data",
    purge_panel_2025: bool = True,
    sep: Optional[str] = None,
) -> pd.DataFrame:
    """
    Construye el Big DataFrame a nivel hogar para un año específico.

    Parámetros
    ----------
    year : int
        Año de la encuesta ENAHO (ej. 2024 o 2025).
    data_root : str | Path, default="Data"
        Directorio raíz donde residen las carpetas de datos.
    purge_panel_2025 : bool, default=True
        Si es True y year == 2025, purga los hogares panel que se repiten con 2024
        para garantizar evaluación fuera de tiempo (OOT) independiente.
    sep : str | None, default=None
        Delimitador de los archivos CSV (por defecto detecta o usa el del año).

    Retorna
    -------
    pd.DataFrame
        DataFrame consolidado a nivel hogar con las variables de los 5 módulos.
    """
    data_root = Path(data_root)
    mods = load_all_raw_modules(year, data_root=data_root, sep=sep)

    s = mods["modulo34"]
    v = mods["modulo01"]
    p = mods["modulo02"]
    e = mods["modulo03"]
    t = mods["modulo05"]

    base_idx = s.set_index(KEY_HOGAR).index

    # -------------------------------------------------------------------------
    # 1. Agregaciones de Demografía (Módulo 02)
    # Excluye trabajadores del hogar puertas adentro (parentesco_jefe in {8, 9})
    # -------------------------------------------------------------------------
    p_miembros = p[~p["parentesco_jefe"].isin([8, 9])]
    gp = p_miembros.groupby(KEY_HOGAR)

    dem = pd.DataFrame(index=base_idx)
    dem["n_miembros"] = gp.size().reindex(base_idx, fill_value=0)
    dem["n_ninos_0_5"] = gp["edad"].apply(lambda a: (a <= 5).sum()).reindex(base_idx, fill_value=0)
    dem["n_menores_14"] = gp["edad"].apply(lambda a: (a < 14).sum()).reindex(base_idx, fill_value=0)
    dem["n_mayores_65"] = gp["edad"].apply(lambda a: (a >= 65).sum()).reindex(base_idx, fill_value=0)

    # Rama del Jefe de Hogar (parentesco_jefe == 1)
    jefe_p = p[p["parentesco_jefe"] == 1].drop_duplicates(subset=KEY_HOGAR).set_index(KEY_HOGAR).reindex(base_idx)
    dem["jefe_mujer"] = (jefe_p["sexo"] == 2).astype(float)
    dem["jefe_edad"] = jefe_p["edad"]
    dem["jefe_estado_civil"] = jefe_p["estado_civil"]

    # Tasa de dependencia demográfica: (menores < 14 + mayores >= 65) / adultos en edad activa (14 a 64)
    activos = (dem["n_miembros"] - dem["n_menores_14"] - dem["n_mayores_65"]).clip(lower=1)
    dem["tasa_dependencia"] = (dem["n_menores_14"] + dem["n_mayores_65"]) / activos

    # -------------------------------------------------------------------------
    # 2. Agregaciones de Educación (Módulo 03)
    # Limpieza ordinal: 99 (no sabe/missing) -> NaN; 12 (básica especial) -> 2
    # -------------------------------------------------------------------------
    clean_educ = e["nivel_educativo"].replace({99: np.nan, 12: 2})
    ge = e.assign(clean_educ=clean_educ).groupby(KEY_HOGAR)

    edu = pd.DataFrame(index=base_idx)
    edu["educ_max_hogar"] = ge["clean_educ"].max().reindex(base_idx)

    jefe_e = e[e["parentesco_jefe"] == 1].drop_duplicates(subset=KEY_HOGAR).set_index(KEY_HOGAR).reindex(base_idx)
    edu["educ_jefe"] = jefe_e["nivel_educativo"].replace({99: np.nan, 12: 2})

    # -------------------------------------------------------------------------
    # 3. Agregaciones de Empleo (Módulo 05)
    # Inactivos reciben formalmente 0 horas y categoría 0 (no_ocupado / no_aplica)
    # -------------------------------------------------------------------------
    gt = t.groupby(KEY_HOGAR)
    emp = pd.DataFrame(index=base_idx)
    emp["n_ocupados"] = gt["condicion_actividad"].apply(lambda a: (a == 1).sum()).reindex(base_idx, fill_value=0)

    jefe_t = t[t["parentesco_jefe"] == 1].drop_duplicates(subset=KEY_HOGAR).set_index(KEY_HOGAR).reindex(base_idx)
    jefe_ocup = (jefe_t["condicion_actividad"] == 1).astype(float)
    jefe_ocup[jefe_t["condicion_actividad"].isna()] = np.nan
    emp["jefe_ocupado"] = jefe_ocup

    emp["jefe_horas_semanales"] = np.where(jefe_ocup == 1, jefe_t["horas_semanales_trabajadas"], 0.0)
    emp.loc[jefe_ocup.isna(), "jefe_horas_semanales"] = np.nan

    emp["jefe_cat_ocupacional"] = np.where(jefe_ocup == 1, jefe_t["categoria_ocupacional"].fillna(0), 0.0)
    emp.loc[jefe_ocup.isna(), "jefe_cat_ocupacional"] = np.nan

    emp["jefe_empresa_ruc"] = np.where(jefe_ocup == 1, jefe_t["empresa_tiene_ruc"].fillna(0), 0.0)
    emp.loc[jefe_ocup.isna(), "jefe_empresa_ruc"] = np.nan

    emp["jefe_sin_pension"] = jefe_t["afiliacion_pension"].map({5.0: 1.0, 0.0: 0.0})

    # -------------------------------------------------------------------------
    # 4. Fusión Horizontal Relacional
    # -------------------------------------------------------------------------
    cols_m01 = [c for c in v.columns if c not in {"ubigeo", "dominio"}]

    df = (
        s.set_index(KEY_HOGAR)
        .join(v[cols_m01].set_index(KEY_HOGAR), how="inner")
        .join(dem, how="left")
        .join(edu, how="left")
        .join(emp, how="left")
    )

    # -------------------------------------------------------------------------
    # 5. Ratios Estructurales del Hogar
    # -------------------------------------------------------------------------
    df["personas_por_hab"] = df["n_miembros"] / df["total_habitaciones"].clip(lower=1)
    df["ocupados_por_miembro"] = (df["n_ocupados"].fillna(0) / df["n_miembros"].clip(lower=1)).clip(lower=0.0, upper=1.0)
    df["anio_encuesta"] = year

    master_df = df.reset_index()

    # -------------------------------------------------------------------------
    # 6. Purga de Panel Longitudinal (OOT) para 2025 si fue solicitada
    # -------------------------------------------------------------------------
    if year == 2025 and purge_panel_2025:
        m34_2024 = load_modulo34(2024, data_root=data_root)
        panel_keys = m34_2024[KEY_HOGAR].merge(master_df[KEY_HOGAR], on=KEY_HOGAR)
        n_panel = len(panel_keys)
        master_df = master_df.merge(panel_keys.assign(_panel=1), on=KEY_HOGAR, how="left")
        master_df = master_df[master_df["_panel"].isna()].drop(columns=["_panel"]).reset_index(drop=True)
        print(f"[build_master_dataset 2025] Purga de panel: {n_panel:,d} hogares repetidos eliminados.")

    return master_df


def load_train_test_master(
    data_root: Union[str, Path] = "Data"
) -> Tuple[pd.DataFrame, pd.DataFrame]:
    """Carga y retorna conjuntamente (df_2024_train, df_2025_test) ya listos."""
    df_2024 = build_master_dataset(2024, data_root=data_root, purge_panel_2025=False)
    df_2025_test = build_master_dataset(2025, data_root=data_root, purge_panel_2025=True)
    return df_2024, df_2025_test


def load_canonical_train_test(
    data_root: Union[str, Path] = "Data"
) -> Tuple[pd.DataFrame, pd.Series, pd.Series, pd.DataFrame, pd.Series, pd.Series]:
    """
    Carga y retorna los conjuntos canónicos libres de data leakage:
    (X_train, y_train, groups_train, X_test, y_test, groups_test)
    utilizando el espacio canónico de 28 características (R^28).
    """
    from src.preprocessing import CANONICAL_FEATURES_28, TARGET_COL, GROUP_COL

    df_train, df_test = load_train_test_master(data_root=data_root)

    X_train = df_train[CANONICAL_FEATURES_28].copy()
    y_train = df_train[TARGET_COL].copy()
    groups_train = df_train[GROUP_COL].copy()

    X_test = df_test[CANONICAL_FEATURES_28].copy()
    y_test = df_test[TARGET_COL].copy()
    groups_test = df_test[GROUP_COL].copy()

    return X_train, y_train, groups_train, X_test, y_test, groups_test


if __name__ == "__main__":
    df24, df25 = load_train_test_master()
    print(f"\n✓ Big DF 2024 (Train): {df24.shape} | Pobres: {df24['y'].sum():,d} ({df24['y'].mean():.2%})")
    print(f"✓ Big DF 2025 (Test sin panel): {df25.shape} | Pobres: {df25['y'].sum():,d} ({df25['y'].mean():.2%})")
    print(f"✓ Sin datos de vivienda: Train={df24['sin_datos_vivienda'].sum()}, Test={df25['sin_datos_vivienda'].sum()}")
    print(f"✓ Max ocupados_por_miembro: Train={df24['ocupados_por_miembro'].max():.2f}, Test={df25['ocupados_por_miembro'].max():.2f}")
    print(f"✓ Max educ_max_hogar: Train={df24['educ_max_hogar'].max():.1f}, Test={df25['educ_max_hogar'].max():.1f}")
