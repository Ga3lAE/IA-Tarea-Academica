"""
Chequeo de H2: error de exclusión con cobertura fija B = 20 % para PMT-MCO, logística y random forest.
Reutiliza la construcción de variables de chequeo_factibilidad.py (misma carpeta).
Entrena con 2024 (DOMINIO 8) y evalúa en 2025 sin hogares panel; IC 95 % por bootstrap de conglomerados.
Timestamp: 2026-10-08_20-30
Uso: python "Documentation/Observaciones a levantar/Plan 2/scripts/chequeo_cobertura.py" Data
Resultado de referencia: EE@20% = 0.408 (PMT-MCO), 0.411 (logística), 0.411 (RF); diferencias con IC dentro de ±0.03.
"""
import sys
from pathlib import Path

import numpy as np
from sklearn.ensemble import RandomForestClassifier
from sklearn.linear_model import LinearRegression, LogisticRegression
from sklearn.pipeline import make_pipeline

base = Path(__file__).with_name("chequeo_factibilidad.py")
src = base.read_text(encoding="utf-8")
ns = {"__file__": str(base), "__name__": "chequeo_factibilidad"}  # no ejecuta su bloque __main__
sys.argv = sys.argv[:2]
exec(compile(src, str(base), "exec"), ns)
tr, te, prep, CAT, NUM, KEY, read = (ns[k] for k in ("tr", "te", "prep", "CAT", "NUM", "KEY", "read"))

# Gasto per cápita mensual: solo variable dependiente del PMT-MCO, nunca predictor
for d, yr in ((tr, 2024), (te, 2025)):
    s = read(yr, "34", "Sumaria-*[0-9][0-9][0-9][0-9].csv", KEY + ["GASHOG2D", "MIEPERHO"])
    s["lngpc"] = np.log(s.GASHOG2D / (12 * s.MIEPERHO))
    d["lngpc"] = d.merge(s[KEY + ["lngpc"]], on=KEY, how="left")["lngpc"].values

cols, B = CAT + NUM, 0.20
w = {0: 1, 1: (1 - tr.y.mean()) / tr.y.mean()}
scores = {
    "PMT-MCO ln(gasto)": -make_pipeline(prep(cols), LinearRegression()).fit(tr[cols], tr.lngpc).predict(te[cols]),
    "Logística": make_pipeline(prep(cols), LogisticRegression(max_iter=2000, class_weight=w))
    .fit(tr[cols], tr.y).predict_proba(te[cols])[:, 1],
    "Random forest": make_pipeline(prep(cols), RandomForestClassifier(400, min_samples_leaf=10, class_weight="balanced_subsample",
                                                                      n_jobs=-1, random_state=0))
    .fit(tr[cols], tr.y).predict_proba(te[cols])[:, 1],
}
y, cong = te.y.values, te.CONGLOME.values


def ee_at_B(score, idx):
    k = int(round(B * len(idx)))
    sel = np.zeros(len(idx), bool)
    sel[np.argsort(-score[idx])[:k]] = True
    pobres = y[idx] == 1
    return 1 - (sel & pobres).sum() / max(pobres.sum(), 1)


print(f"Test 2025 sin panel: n={len(y)}, prevalencia={y.mean():.1%}, cobertura B={B:.0%}")
for k, s in scores.items():
    print(f"  {k:<20} error de exclusión @B = {ee_at_B(s, np.arange(len(y))):.3f}")

rng = np.random.default_rng(0)
ucong = np.unique(cong)
groups = {c: np.where(cong == c)[0] for c in ucong}
for a, b in (("PMT-MCO ln(gasto)", "Random forest"), ("Logística", "Random forest"), ("PMT-MCO ln(gasto)", "Logística")):
    diffs = [ee_at_B(scores[a], idx) - ee_at_B(scores[b], idx)
             for idx in (np.concatenate([groups[c] for c in rng.choice(ucong, len(ucong))]) for _ in range(1000))]
    lo, hi = np.percentile(diffs, [2.5, 97.5])
    print(f"  EE({a}) - EE({b}) = {np.mean(diffs):+.3f}  IC95% [{lo:+.3f}, {hi:+.3f}]")
