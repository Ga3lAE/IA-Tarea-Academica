"""
Chequeo rápido de factibilidad de las hipótesis (NO es el modelo final).

Construye ~25 variables simples (módulos 01, 02, 03, 05) para Lima Metropolitana
(DOMINIO = 8), entrena con 2024 y evalúa con 2025 (sin hogares panel repetidos).
Timestamp: 2026-10-08_20-03
Uso: python "Documentation/Observaciones a levantar/chequeo_factibilidad_2026-10-08_20-03.py" Data
"""
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.ensemble import HistGradientBoostingClassifier, RandomForestClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import average_precision_score, f1_score, precision_recall_curve, roc_auc_score
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler

ROOT = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("Data")
FOLDER = {2024: "2024/enaho/966-Modulo", 2025: "2025/enaho/1031-Modulo"}
KEY = ["CONGLOME", "VIVIENDA", "HOGAR"]


def read(yr, mod, pattern, cols):
    path = next((ROOT / f"{FOLDER[yr]}{mod}").glob(pattern))
    with open(path, encoding="latin-1") as f:
        sep = ";" if f.readline().count(";") > 5 else ","
    df = pd.read_csv(path, sep=sep, encoding="latin-1", dtype=str,
                     usecols=lambda c: c.upper() in cols)
    df.columns = [c.upper() for c in df.columns]
    for c in df.columns:
        df[c] = df[c].str.strip()
    for c in set(df.columns) - set(KEY) - {"UBIGEO"}:
        df[c] = pd.to_numeric(df[c].str.replace(",", "."), errors="coerce")
    return df


def build(yr):
    s = read(yr, "34", "Sumaria-*[0-9][0-9][0-9][0-9].csv", KEY + ["DOMINIO", "POBREZA", "FACTOR07", "MIEPERHO"])
    s = s[s.DOMINIO == 8]
    s["y"] = s.POBREZA.isin([1, 2]).astype(int)

    v = read(yr, "01", "Enaho01-*-100.csv", KEY + ["RESULT", "P101", "P102", "P103", "P104", "P104A", "P105A",
                                                   "P106A", "P110", "P111A", "P113A", "P1143", "P1144"])
    v = v[v.RESULT.isin([1, 2])]
    phys = ["P101", "P102", "P103", "P104", "P104A"]
    v[phys] = v.groupby(["CONGLOME", "VIVIENDA"])[phys].transform(lambda x: x.ffill().bfill())

    p = read(yr, "02", "Enaho01-*-200.csv", KEY + ["P203", "P204", "P205", "P206", "P207", "P208A"])
    res = p[(p.P204 == 1) & (p.P205 != 1) | (p.P204 == 2) & (p.P206 == 1)]  # miembros residentes
    g = res.groupby(KEY)
    dem = pd.DataFrame({
        "n_miembros": g.size(),
        "n_ninos_0_5": g.P208A.apply(lambda a: (a <= 5).sum()),
        "n_menores_14": g.P208A.apply(lambda a: (a < 14).sum()),
        "n_mayores_65": g.P208A.apply(lambda a: (a >= 65).sum()),
    })
    jefe = res[res.P203 == 1].set_index(KEY)
    dem["jefe_mujer"] = (jefe.P207 == 2).astype(float)
    dem["jefe_edad"] = jefe.P208A
    dem["dependencia"] = (dem.n_menores_14 + dem.n_mayores_65) / (dem.n_miembros - dem.n_menores_14 - dem.n_mayores_65).clip(lower=1)

    e = read(yr, "03", "Enaho01A-*-300.csv", KEY + ["P203", "P301A"])
    edu = pd.DataFrame({"educ_max_hogar": e.groupby(KEY).P301A.max(),
                        "educ_jefe": e[e.P203 == 1].set_index(KEY).P301A})

    t = read(yr, "05", "Enaho01a-*-500.csv", KEY + ["P203", "OCU500", "P507", "P513T", "P558A5"])
    emp = pd.DataFrame({"n_ocupados": t.groupby(KEY).OCU500.apply(lambda a: (a == 1).sum())})
    tj = t[t.P203 == 1].set_index(KEY)
    emp["jefe_ocupado"] = (tj.OCU500 == 1).astype(float)
    emp["jefe_cat_ocup"] = tj.P507
    emp["jefe_horas"] = tj.P513T
    emp["jefe_sin_pension"] = (tj.P558A5 == 5).astype(float)

    df = (s.set_index(KEY).join(v.set_index(KEY), how="inner")
          .join(dem).join(edu).join(emp))
    df["personas_por_hab"] = df.n_miembros / df.P104.clip(lower=1)
    df["ocupados_por_miembro"] = df.n_ocupados.fillna(0) / df.n_miembros.clip(lower=1)
    df["anio"] = yr
    return df.reset_index()


CAT = ["P101", "P102", "P103", "P105A", "P106A", "P110", "P111A", "P113A", "P1143", "P1144", "jefe_cat_ocup"]
NUM = ["P104", "P104A", "n_miembros", "n_ninos_0_5", "n_menores_14", "n_mayores_65", "jefe_mujer", "jefe_edad",
       "dependencia", "educ_max_hogar", "educ_jefe", "n_ocupados", "jefe_ocupado", "jefe_horas",
       "jefe_sin_pension", "personas_por_hab", "ocupados_por_miembro"]
VIV = ["P101", "P102", "P103", "P105A", "P106A", "P110", "P111A", "P113A", "P1143", "P1144", "P104", "P104A"]

tr, te = build(2024), build(2025)
panel = tr[KEY].merge(te[KEY])
te = te.merge(panel.assign(_p=1), how="left", on=KEY)
te = te[te._p.isna()].drop(columns="_p")
print(f"train 2024: {len(tr)} hogares ({tr.y.mean():.1%} pobres) | test 2025 sin panel: {len(te)} ({te.y.mean():.1%})")


def prep(cols):
    cat = [c for c in cols if c in CAT]
    num = [c for c in cols if c in NUM]
    for d in (tr, te):
        d[cat] = d[cat].fillna(-1).astype(int).astype(str)
        d[num] = d[num].fillna(d[num].median())
    return ColumnTransformer([("c", OneHotEncoder(handle_unknown="ignore", min_frequency=20), cat),
                              ("n", StandardScaler(), num)])


def evaluar(nombre, modelo, cols):
    pipe = make_pipeline(prep(cols), modelo).fit(tr[cols], tr.y)
    p = pipe.predict_proba(te[cols])[:, 1]
    prec, rec, thr = precision_recall_curve(te.y, p)
    f1s = 2 * prec * rec / np.clip(prec + rec, 1e-9, None)
    p_at_r80 = prec[rec >= 0.80].max()
    r_at_p60 = rec[prec >= 0.60].max() if (prec >= 0.60).any() else 0.0
    print(f"{nombre:<38} ROC-AUC={roc_auc_score(te.y, p):.3f}  PR-AUC={average_precision_score(te.y, p):.3f}  "
          f"F1max={f1s.max():.3f}  Prec@Recall80={p_at_r80:.3f}  Recall@Prec60={r_at_p60:.3f}  "
          f"F1@0.5={f1_score(te.y, p >= 0.5):.3f}")


if __name__ == "__main__":
    todas = CAT + NUM
    w = {0: 1, 1: (1 - tr.y.mean()) / tr.y.mean()}
    evaluar("Logística (solo vivienda, mód. 01)", LogisticRegression(max_iter=2000, class_weight=w), VIV)
    evaluar("Logística (todas)", LogisticRegression(max_iter=2000, class_weight=w), todas)
    evaluar("Random forest (todas)", RandomForestClassifier(400, min_samples_leaf=10, class_weight="balanced_subsample",
                                                            n_jobs=-1, random_state=0), todas)
    evaluar("Gradient boosting (todas)", HistGradientBoostingClassifier(learning_rate=0.05, max_iter=300,
                                                                        class_weight=w, random_state=0), todas)
