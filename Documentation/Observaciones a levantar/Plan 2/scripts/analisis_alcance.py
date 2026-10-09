"""Cifras de alcance del informe parcial (Sumaria ENAHO 2024-2025): hogares, pobreza ponderada,
línea de pobreza, conglomerados y hogares panel por alcance geográfico.
Uso: python "Documentation/Observaciones a levantar/Plan 2/scripts/analisis_alcance.py" Data
"""
import sys
from pathlib import Path
import pandas as pd

ROOT = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("Data")
FILES = {2024: ROOT / "2024" / "enaho" / "966-Modulo34" / "Sumaria-2024.csv",
         2025: ROOT / "2025" / "enaho" / "1031-Modulo34" / "Sumaria-2025.csv"}
COLS = ["CONGLOME", "VIVIENDA", "HOGAR", "UBIGEO", "DOMINIO", "ESTRATO", "LINEA",
        "MIEPERHO", "POBREZA", "FACTOR07"]


def load(path):
    with open(path, encoding="latin-1") as f:
        sep = ";" if f.readline().count(";") > 5 else ","
    df = pd.read_csv(path, sep=sep, encoding="latin-1", usecols=lambda c: c.upper() in COLS, dtype=str)
    df.columns = [c.upper() for c in df.columns]
    df["UBIGEO"] = df["UBIGEO"].str.strip().str.zfill(6)
    for c in ["DOMINIO", "ESTRATO", "MIEPERHO", "POBREZA"]:
        df[c] = pd.to_numeric(df[c], errors="coerce")
    df["FACTOR07"] = pd.to_numeric(df["FACTOR07"].str.replace(",", "."), errors="coerce")
    return df


def resumen(d):
    pobre = d["POBREZA"].isin([1, 2])
    w_hog = d["FACTOR07"]
    w_per = d["FACTOR07"] * d["MIEPERHO"]
    return {
        "hogares": len(d),
        "conglomerados": d["CONGLOME"].nunique(),
        "hog_pobres": int(pobre.sum()),
        "hog_pobres_ext": int((d["POBREZA"] == 1).sum()),
        "%hog_pobres_sin_pond": round(100 * pobre.mean(), 1),
        "%hog_pobres_pond": round(100 * (w_hog * pobre).sum() / w_hog.sum(), 1),
        "%personas_pobres_pond": round(100 * (w_per * pobre).sum() / w_per.sum(), 1),
        "poblacion_expandida_M": round(w_per.sum() / 1e6, 2),
    }


for yr, path in FILES.items():
    df = load(path)
    print(f"\n===== {yr}: {len(df)} hogares en Sumaria nacional =====")
    print("DOMINIO por prefijo UBIGEO (07=Callao, 1501=Prov. Lima, 15xx resto dpto. Lima):")
    df["zona"] = "otro"
    df.loc[df["UBIGEO"].str.startswith("07"), "zona"] = "Callao(07)"
    df.loc[df["UBIGEO"].str.startswith("1501"), "zona"] = "ProvLima(1501)"
    df.loc[df["UBIGEO"].str.startswith("15") & ~df["UBIGEO"].str.startswith("1501"), "zona"] = "LimaProvincias(15xx)"
    print(pd.crosstab(df["zona"], df["DOMINIO"]))
    print("POBREZA values:", df["POBREZA"].value_counts(dropna=False).to_dict())
    scopes = {
        "A) DOMINIO=8 (Lima Metropolitana INEI)": df["DOMINIO"] == 8,
        "B) Provincia de Lima (1501) sin Callao": df["UBIGEO"].str.startswith("1501"),
        "C) Callao (07) solo": df["UBIGEO"].str.startswith("07"),
        "D) Dpto. Lima + Callao (filtro actual)": df["UBIGEO"].str.startswith(("15", "07")),
        "E) Lima Provincias (15xx sin 1501)": df["zona"] == "LimaProvincias(15xx)",
        "Nacional": pd.Series(True, index=df.index),
    }
    rows = {k: resumen(df[m]) for k, m in scopes.items()}
    print(pd.DataFrame(rows).T.to_string())
    lm = df[df["DOMINIO"] == 8]
    print("ESTRATO en Lima Metropolitana:", lm["ESTRATO"].value_counts().sort_index().to_dict())
    linea = pd.to_numeric(lm["LINEA"].str.replace(",", "."), errors="coerce")
    print("Línea de pobreza en Lima Metropolitana:", sorted(linea.round(1).unique()))
    globals()[f"df{yr}"] = df

k = ["CONGLOME", "VIVIENDA", "HOGAR"]
a = df2024[df2024["DOMINIO"] == 8]; b = df2025[df2025["DOMINIO"] == 8]
print("\nConglomerados LM comunes 2024-2025:", len(set(a.CONGLOME) & set(b.CONGLOME)))
print("Llaves hogar LM comunes 2024-2025:", len(a.merge(b, on=k)))

# Cifras adicionales citadas en el informe (participación en la pobreza nacional y línea de pobreza)
for yr, df in [(2024, df2024), (2025, df2025)]:
    w = df["FACTOR07"] * df["MIEPERHO"]
    pob = df["POBREZA"].isin([1, 2])
    lm = df["DOMINIO"] == 8
    print(f"{yr}: LM = {100 * (w * lm).sum() / w.sum():.1f}% de la población y "
          f"{100 * (w * pob * lm).sum() / (w * pob).sum():.1f}% de los pobres; "
          f"pobreza extrema LM = {100 * (w * (df['POBREZA'] == 1) * lm).sum() / (w * lm).sum():.1f}%")
