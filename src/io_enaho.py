"""
Módulo de ingesta y lectura directa de microdatos ENAHO (Módulos 01, 02, 03, 05 y 34).
Diseñado bajo el principio KISS: lectura directa, delimitadores configurables y
nombres de columnas estandarizados según los Diccionarios Oficiales del INEI.

Regla metodológica crítica (Observación del Jurado - Entregable Parcial):
- NO se realiza imputación intra-vivienda (ffill/bfill) en los hogares secundarios (hogar >= 22)
  al leer el Módulo 01. Los valores faltantes se preservan como NaN para ser tratados en la etapa
  de preprocesamiento mediante la categoría 'desconocido' (categóricas) o la mediana del
  conglomerado censal (numéricas).
"""
from pathlib import Path
from typing import Dict, List, Optional, Sequence, Union
import numpy as np
import pandas as pd

# Llaves primarias estándar del proyecto (nombres legibles)
KEY_HOGAR: List[str] = ["conglomerado", "vivienda", "hogar"]
KEY_PERSONA: List[str] = ["conglomerado", "vivienda", "hogar", "cod_persona"]

# Prefijos de carpetas por año en Data/{year}/enaho/
YEAR_FOLDER_PREFIX: Dict[int, str] = {
    2024: "2024/enaho/966-Modulo",
    2025: "2025/enaho/1031-Modulo",
}

# Separador por defecto conocido por año (puede sobreescribirse por parámetro)
DEFAULT_YEAR_SEP: Dict[int, str] = {
    2024: ",",
    2025: ";",
}

# =============================================================================
# MAPEOS DE COLUMNAS RAW -> DICCIONARIO METODOLÓGICO INEI
# =============================================================================

RENAME_MODULO34: Dict[str, str] = {
    "CONGLOME": "conglomerado",
    "VIVIENDA": "vivienda",
    "HOGAR": "hogar",
    "UBIGEO": "ubigeo",
    "DOMINIO": "dominio",
    "ESTRATO": "estrato",
    "POBREZA": "pobreza_oficial",
    "FACTOR07": "factor_expansion",
    "MIEPERHO": "miembros_hogar",
    "GASHOG2D": "gasto_anual_hogar",
    "LINEA": "linea_pobreza",
}

RENAME_MODULO01: Dict[str, str] = {
    "CONGLOME": "conglomerado",
    "VIVIENDA": "vivienda",
    "HOGAR": "hogar",
    "UBIGEO": "ubigeo",
    "DOMINIO": "dominio",
    "RESULT": "resultado_encuesta",
    "P101": "tipo_vivienda",
    "P102": "material_pared",
    "P103": "material_piso",
    "P104": "total_habitaciones",
    "P104A": "total_dormitorios",
    "P105A": "tenencia_vivienda",
    "P106A": "titulo_propiedad",
    "P106B": "registro_sunarp",
    "P110": "fuente_agua",
    "P110C": "agua_todos_los_dias",
    "P111A": "conexion_bano",
    "P113A": "combustible_cocina",
    "P1143": "tiene_tv_cable",
    "P1144": "tiene_internet",
    "NBI1": "nbi_vivienda_inadecuada",
    "NBI2": "nbi_hacinamiento",
    "NBI3": "nbi_sin_bano",
    "NBI4": "nbi_nino_sin_escuela",
    "NBI5": "nbi_alta_dependencia",
}

RENAME_MODULO02: Dict[str, str] = {
    "CONGLOME": "conglomerado",
    "VIVIENDA": "vivienda",
    "HOGAR": "hogar",
    "CODPERSO": "cod_persona",
    "P203": "parentesco_jefe",
    "P204": "es_miembro_habitual",
    "P205": "ausente_mas_3_meses",
    "P206": "presente_mas_3_meses",
    "P207": "sexo",
    "P208A": "edad",
    "P209": "estado_civil",
}

RENAME_MODULO03: Dict[str, str] = {
    "CONGLOME": "conglomerado",
    "VIVIENDA": "vivienda",
    "HOGAR": "hogar",
    "CODPERSO": "cod_persona",
    "P203": "parentesco_jefe",
    "P300A": "lengua_materna",
    "P301A": "nivel_educativo",
    "P302": "sabe_leer_escribir",
    "P306": "asiste_centro_educativo",
    "P307": "tipo_institucion_educ",
}

RENAME_MODULO05: Dict[str, str] = {
    "CONGLOME": "conglomerado",
    "VIVIENDA": "vivienda",
    "HOGAR": "hogar",
    "CODPERSO": "cod_persona",
    "P203": "parentesco_jefe",
    "OCU500": "condicion_actividad",
    "P507": "categoria_ocupacional",
    "P510A1": "empresa_tiene_ruc",
    "P513T": "horas_semanales_trabajadas",
    "P558A5": "afiliacion_pension",
}


def _check_git_lfs(file_path: Path) -> None:
    """Verifica que el archivo CSV no sea un puntero de texto de Git LFS sin descargar."""
    with open(file_path, "r", encoding="latin-1", errors="ignore") as f:
        first_line = f.readline().strip()
        if first_line.startswith("version https://git-lfs.github.com/spec/v1"):
            raise RuntimeError(
                f"El archivo '{file_path}' es un puntero de Git LFS. "
                "Ejecuta 'git lfs pull' para descargar los microdatos reales."
            )


def _detect_sep(file_path: Path, encoding: str = "latin-1") -> str:
    """Detecta el separador (',' o ';') leyendo únicamente la primera línea."""
    with open(file_path, "r", encoding=encoding, errors="ignore") as f:
        header = f.readline()
    return ";" if header.count(";") > header.count(",") else ","


def resolve_module_path(
    year: int,
    module_code: str,
    pattern: str,
    data_root: Union[str, Path] = "Data",
) -> Path:
    """Resuelve la ruta exacta al archivo CSV de un módulo y año de la ENAHO."""
    root = Path(data_root)
    if year not in YEAR_FOLDER_PREFIX:
        raise ValueError(f"Año {year} no configurado en YEAR_FOLDER_PREFIX: {list(YEAR_FOLDER_PREFIX.keys())}")

    folder = root / f"{YEAR_FOLDER_PREFIX[year]}{module_code}"
    matches = sorted(folder.glob(pattern))
    if not matches:
        raise FileNotFoundError(f"No se encontró archivo con patrón '{pattern}' en {folder}")
    return matches[0]


def read_enaho_csv(
    file_path: Union[str, Path],
    usecols: Optional[Sequence[str]] = None,
    rename_map: Optional[Dict[str, str]] = None,
    sep: Optional[str] = None,
    encoding: str = "latin-1",
) -> pd.DataFrame:
    """
    Lee un archivo CSV de la ENAHO, limpia espacios en blanco y renombra columnas según diccionario.
    """
    path = Path(file_path)
    if not path.exists():
        raise FileNotFoundError(f"Archivo no encontrado: {path}")

    _check_git_lfs(path)
    delimiter = sep if sep is not None else _detect_sep(path, encoding=encoding)

    if usecols is not None:
        wanted = {c.upper() for c in usecols}
        col_filter = lambda c: c.strip().upper() in wanted
    else:
        col_filter = None

    df = pd.read_csv(
        path,
        sep=delimiter,
        encoding=encoding,
        dtype=str,
        usecols=col_filter,
        low_memory=False,
    )
    df.columns = [c.strip().upper() for c in df.columns]

    if usecols is not None:
        missing = [c.upper() for c in usecols if c.upper() not in df.columns]
        if missing:
            raise KeyError(f"Faltan columnas requeridas {missing} en {path.name}")

    # Limpiar espacios en blanco
    for col in df.columns:
        df[col] = df[col].str.strip()

    # Convertir a numérico columnas que no sean llaves ni ubigeo
    raw_keys = {"CONGLOME", "VIVIENDA", "HOGAR", "CODPERSO", "UBIGEO"}
    for col in df.columns:
        if col not in raw_keys:
            df[col] = pd.to_numeric(df[col].str.replace(",", ".", regex=False), errors="coerce")

    # Renombrar a nombres de diccionario si se especificó
    if rename_map is not None:
        df.rename(columns=rename_map, inplace=True)

    return df


# =============================================================================
# FUNCIONES POR MÓDULO (CON NOMBRES SEMÁNTICOS INEI)
# =============================================================================

def load_modulo34(
    year: int,
    data_root: Union[str, Path] = "Data",
    sep: Optional[str] = None,
    filter_lima_metro: bool = True,
) -> pd.DataFrame:
    """
    Lee el Módulo 34 (Sumaria).
    Filtra Lima Metropolitana y Callao (dominio == 8) y genera target_pobreza y lngpc.
    """
    path = resolve_module_path(year, "34", f"Sumaria-{year}.csv", data_root=data_root)
    df = read_enaho_csv(
        path,
        usecols=list(RENAME_MODULO34.keys()),
        rename_map=RENAME_MODULO34,
        sep=sep or DEFAULT_YEAR_SEP.get(year),
    )

    if filter_lima_metro:
        df = df[df["dominio"] == 8].copy()

    # Variable objetivo binaria: 1 = Pobre (extremo o no extremo), 0 = No pobre
    df["target_pobreza"] = df["pobreza_oficial"].isin([1, 2]).astype(int)
    df["y"] = df["target_pobreza"]  # Alias canónico de Machine Learning

    # Logaritmo del gasto mensual per cápita (solo para baseline PMT-MCO)
    df["lngpc"] = np.log(df["gasto_anual_hogar"] / (12.0 * df["miembros_hogar"]))

    return df.reset_index(drop=True)


def load_modulo01(
    year: int,
    data_root: Union[str, Path] = "Data",
    sep: Optional[str] = None,
    filter_valid_results: bool = True,
) -> pd.DataFrame:
    """
    Lee el Módulo 01 (Vivienda y Servicios Básicos).
    NOTA METODOLÓGICA: Conserva intactos los valores NaN en hogares secundarios (hogar != '11').
    """
    path = resolve_module_path(year, "01", f"Enaho01-{year}-100.csv", data_root=data_root)
    df = read_enaho_csv(
        path,
        usecols=list(RENAME_MODULO01.keys()),
        rename_map=RENAME_MODULO01,
        sep=sep or DEFAULT_YEAR_SEP.get(year),
    )

    if filter_valid_results:
        df = df[df["resultado_encuesta"].isin([1, 2])].copy()

    # Indicador explícito de hogar secundario (hogar != '11')
    df["es_hogar_secundario"] = (df["hogar"] != "11").astype(int)

    return df.reset_index(drop=True)


def load_modulo02(
    year: int,
    data_root: Union[str, Path] = "Data",
    sep: Optional[str] = None,
    filter_residents: bool = True,
) -> pd.DataFrame:
    """
    Lee el Módulo 02 (Características Demográficas de los Miembros).
    """
    path = resolve_module_path(year, "02", f"Enaho01-{year}-200.csv", data_root=data_root)
    df = read_enaho_csv(
        path,
        usecols=list(RENAME_MODULO02.keys()),
        rename_map=RENAME_MODULO02,
        sep=sep or DEFAULT_YEAR_SEP.get(year),
    )

    if filter_residents:
        es_residente = ((df["es_miembro_habitual"] == 1) & (df["ausente_mas_3_meses"] != 1)) | \
                       ((df["es_miembro_habitual"] == 2) & (df["presente_mas_3_meses"] == 1))
        df = df[es_residente].copy()

    return df.reset_index(drop=True)


def load_modulo03(
    year: int,
    data_root: Union[str, Path] = "Data",
    sep: Optional[str] = None,
) -> pd.DataFrame:
    """
    Lee el Módulo 03 (Educación y Capital Humano).
    """
    path = resolve_module_path(year, "03", f"Enaho01A-{year}-300.csv", data_root=data_root)
    df = read_enaho_csv(
        path,
        usecols=list(RENAME_MODULO03.keys()),
        rename_map=RENAME_MODULO03,
        sep=sep or DEFAULT_YEAR_SEP.get(year),
    )
    return df.reset_index(drop=True)


def load_modulo05(
    year: int,
    data_root: Union[str, Path] = "Data",
    sep: Optional[str] = None,
) -> pd.DataFrame:
    """
    Lee el Módulo 05 (Empleo e Informalidad Laboral).
    Excluye estrictamente ingresos monetarios (cero data leakage).
    """
    path = resolve_module_path(year, "05", f"Enaho01a-{year}-500.csv", data_root=data_root)
    df = read_enaho_csv(
        path,
        usecols=list(RENAME_MODULO05.keys()),
        rename_map=RENAME_MODULO05,
        sep=sep or DEFAULT_YEAR_SEP.get(year),
    )
    return df.reset_index(drop=True)


def load_all_raw_modules(
    year: int,
    data_root: Union[str, Path] = "Data",
    sep: Optional[str] = None,
) -> Dict[str, pd.DataFrame]:
    """
    Carga los 5 módulos de un año filtrando al marco de Lima Metropolitana (dominio == 8).
    """
    m34 = load_modulo34(year, data_root=data_root, sep=sep, filter_lima_metro=True)
    hogares_lima = m34[KEY_HOGAR].drop_duplicates()

    m01 = load_modulo01(year, data_root=data_root, sep=sep).merge(hogares_lima, on=KEY_HOGAR, how="inner")
    m02 = load_modulo02(year, data_root=data_root, sep=sep).merge(hogares_lima, on=KEY_HOGAR, how="inner")
    m03 = load_modulo03(year, data_root=data_root, sep=sep).merge(hogares_lima, on=KEY_HOGAR, how="inner")
    m05 = load_modulo05(year, data_root=data_root, sep=sep).merge(hogares_lima, on=KEY_HOGAR, how="inner")

    return {
        "modulo34": m34,
        "modulo01": m01,
        "modulo02": m02,
        "modulo03": m03,
        "modulo05": m05,
    }


if __name__ == "__main__":
    for yr in (2024, 2025):
        print(f"\n{'='*72}")
        print(f"VERIFICACIÓN DE LECTURA ENAHO {yr} — LIMA METROPOLITANA (DOMINIO 8)")
        print(f"{'='*72}")
        mods = load_all_raw_modules(yr)
        for name, df_mod in mods.items():
            pk = KEY_HOGAR if name in ("modulo34", "modulo01") else KEY_PERSONA
            n_hogares = df_mod[KEY_HOGAR].drop_duplicates().shape[0]
            pk_unique = not df_mod.duplicated(subset=pk).any()
            print(
                f"  {name:<10} | filas: {len(df_mod):>6,d} | hogares únicos: {n_hogares:>5,d} "
                f"| cols: {df_mod.shape[1]:>2d} | PK única: {pk_unique}"
            )
            print(f"             Columnas: {list(df_mod.columns[:6])}...")
        m01 = mods["modulo01"]
        n_sec = int((m01["es_hogar_secundario"] == 1).sum())
        n_null_viv = int(m01["tipo_vivienda"].isna().sum())
        n_null_hab = int(m01["total_habitaciones"].isna().sum())
        print(
            f"  [Diagnóstico M01 {yr}] Hogares secundarios: {n_sec} "
            f"| Nulos en tipo_vivienda: {n_null_viv} | Nulos en total_habitaciones: {n_null_hab}"
        )
