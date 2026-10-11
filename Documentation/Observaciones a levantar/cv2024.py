"""Evidencia preliminar SOLO con 2024 (GroupKFold por conglomerado), sin tocar 2025.
Uso (desde la raíz del repositorio): python "Documentation/Observaciones a levantar/cv2024.py"
"""
import sys
from pathlib import Path
import numpy as np
from sklearn.ensemble import RandomForestClassifier
from sklearn.linear_model import LinearRegression, LogisticRegression
from sklearn.metrics import average_precision_score, precision_recall_curve
from sklearn.model_selection import GroupKFold
from sklearn.pipeline import make_pipeline

repo = Path(__file__).resolve().parents[2]  # raíz del repositorio
base = repo / "Documentation" / "Observaciones a levantar" / "chequeo_factibilidad_2026-10-08_20-03.py"
ns = {"__file__": str(base), "__name__": "chequeo"}
sys.argv = [sys.argv[0], str(repo / "Data")]
exec(compile(base.read_text(encoding="utf-8"), str(base), "exec"), ns)
build, prep, CAT, NUM, VIV, KEY, read = (ns[k] for k in ("build", "prep", "CAT", "NUM", "VIV", "KEY", "read"))

tr = build(2024).reset_index(drop=True)
s = read(2024, "34", "Sumaria-*[0-9][0-9][0-9][0-9].csv", KEY + ["GASHOG2D", "MIEPERHO"])
s["lngpc"] = np.log(s.GASHOG2D / (12 * s.MIEPERHO))
tr["lngpc"] = tr.merge(s[KEY + ["lngpc"]], on=KEY, how="left")["lngpc"].values
for c in CAT:
    tr[c] = tr[c].fillna(-1).astype(int).astype(str)
tr[NUM] = tr[NUM].fillna(tr[NUM].median())
ns["tr"], ns["te"] = tr, tr.iloc[:0].copy()

y, groups = tr.y.values, tr.CONGLOME.values
gkf = GroupKFold(n_splits=5)
todas = CAT + NUM
w = {0: 1, 1: (1 - y.mean()) / y.mean()}


def oof(make_model, cols, target="y", reg=False):
    out = np.zeros(len(tr))
    for a, b in gkf.split(tr, y, groups):
        pipe = make_pipeline(prep(cols), make_model())
        pipe.fit(tr.iloc[a][cols], tr.iloc[a][target])
        out[b] = -pipe.predict(tr.iloc[b][cols]) if reg else pipe.predict_proba(tr.iloc[b][cols])[:, 1]
    return out


def ee_at_B(score, idx, B=0.20):
    k = int(round(B * len(idx)))
    sel = np.zeros(len(idx), bool)
    sel[np.argsort(-score[idx])[:k]] = True
    pobres = y[idx] == 1
    return 1 - (sel & pobres).sum() / pobres.sum()


sc = {
    "Logística (solo vivienda)": oof(lambda: LogisticRegression(max_iter=2000, class_weight=w), VIV),
    "Logística (4 módulos)": oof(lambda: LogisticRegression(max_iter=2000, class_weight=w), todas),
    "Random forest (4 módulos)": oof(lambda: RandomForestClassifier(400, min_samples_leaf=10, class_weight="balanced_subsample",
                                                                    n_jobs=-1, random_state=0), todas),
    "PMT-MCO ln(gasto) (4 módulos)": oof(lambda: LinearRegression(), todas, target="lngpc", reg=True),
}
print(f"2024 DOMINIO 8: n={len(y)}, prevalencia={y.mean():.3f}; GroupKFold(5) por CONGLOME")
allidx = np.arange(len(y))
for k, p in sc.items():
    prec, rec, _ = precision_recall_curve(y, p)
    f1 = (2 * prec * rec / np.clip(prec + rec, 1e-9, None)).max()
    p70 = prec[rec >= 0.70].max()
    print(f"  {k:<32} PR-AUC={average_precision_score(y, p):.3f}  F1max={f1:.3f}  Prec@Recall70={p70:.3f}  EE@B20={ee_at_B(p, allidx):.3f}")

rng = np.random.default_rng(0)
ug = np.unique(groups)
gi = {g: np.where(groups == g)[0] for g in ug}
for a, b in (("PMT-MCO ln(gasto) (4 módulos)", "Random forest (4 módulos)"), ("Logística (4 módulos)", "Random forest (4 módulos)")):
    d = [ee_at_B(sc[a], idx) - ee_at_B(sc[b], idx)
         for idx in (np.concatenate([gi[g] for g in rng.choice(ug, len(ug))]) for _ in range(1000))]
    print(f"  EE({a}) - EE({b}) = {np.mean(d):+.3f}  IC95% [{np.percentile(d, 2.5):+.3f}, {np.percentile(d, 97.5):+.3f}]")
d = []
for _ in range(1000):
    idx = np.concatenate([gi[g] for g in rng.choice(ug, len(ug))])
    d.append(average_precision_score(y[idx], sc["Logística (4 módulos)"][idx]) - average_precision_score(y[idx], sc["Logística (solo vivienda)"][idx]))
print(f"  dPR-AUC (4 módulos - vivienda, logística) = {np.mean(d):+.3f}  IC95% [{np.percentile(d, 2.5):+.3f}, {np.percentile(d, 97.5):+.3f}]")
