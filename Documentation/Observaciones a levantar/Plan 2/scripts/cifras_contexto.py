"""
Cifras de contexto citadas en el informe parcial (Lima Metropolitana = DOMINIO 8, ENAHO 2024):
- Brecha de cobertura: hogares pobres sin transferencias públicas (INGTPUHD) ni donaciones públicas de alimentos (GRU13HD1).
- Paredes de ladrillo y tasa de pobreza por material de paredes y de pisos.
- Hogares secundarios sin datos físicos de vivienda (nulos estructurales del Módulo 01).
Requiere Data/processed/modulo01_2024_cleaned.csv generado con el pipeline (alcance DOMINIO 8).
Uso: python "Documentation/Observaciones a levantar/Plan 2/scripts/cifras_contexto.py" Data
"""
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("Data")
KEY = ["conglomerado", "vivienda", "hogar"]

s = pd.read_csv(ROOT / "2024" / "enaho" / "966-Modulo34" / "Sumaria-2024.csv", encoding="latin-1",
                usecols=lambda c: c.upper() in ["CONGLOME", "VIVIENDA", "HOGAR", "DOMINIO", "POBREZA", "FACTOR07",
                                                "MIEPERHO", "INGTPUHD", "GRU13HD1"])
s.columns = [c.lower() for c in s.columns]
s = s.rename(columns={"conglome": "conglomerado"})
for c in ["factor07", "ingtpuhd", "gru13hd1"]:
    s[c] = pd.to_numeric(s[c].astype(str).str.replace(",", "."), errors="coerce").fillna(0)
s = s[s.dominio == 8]
pobre = s.pobreza.isin([1, 2])

# 1. Brecha de cobertura de programas sociales
sin_apoyo = (s.ingtpuhd <= 0) & (s.gru13hd1 <= 0)
w = s.factor07 * s.mieperho
print(f"Hogares pobres 2024: {pobre.sum()} | sin transferencias ni donaciones públicas: {(pobre & sin_apoyo).sum()} "
      f"({100 * (pobre & sin_apoyo).sum() / pobre.sum():.1f}%) | ponderado por personas: "
      f"{100 * (w * (pobre & sin_apoyo)).sum() / (w * pobre).sum():.1f}%")

# 2. Materiales de la vivienda
v = pd.read_csv(ROOT / "processed" / "modulo01_2024_cleaned.csv", sep=None, engine="python")
m = v.merge(s[KEY + ["pobreza"]], on=KEY)
p = m.pobreza.isin([1, 2])
pared = m.material_pared_exterior
print(f"Hogares con paredes de ladrillo: {100 * (pared == 'ladrillo_bloque_cemento').mean():.1f}%")
for nombre, cats in [("ladrillo", ["ladrillo_bloque_cemento"]), ("madera/estera", ["madera", "triplay_calamina_estera"])]:
    mk = pared.isin(cats)
    print(f"  Pobreza con paredes de {nombre}: {100 * p[mk].mean():.1f}% (n={mk.sum()})")
grupos = {"acabado noble": ["parquet_madera_pulida", "vinilico_similares", "loseta_terrazo_ceramico"],
          "cemento": ["cemento"], "precario": ["tierra", "madera_tablas", "otro"]}
for nombre, cats in grupos.items():
    mk = m.material_piso.isin(cats)
    print(f"  Piso {nombre}: {100 * mk.mean():.1f}% de hogares, pobreza {100 * p[mk].mean():.1f}%")

# 3. Nulos estructurales del Módulo 01 (antes de la imputación intra-vivienda)
for yr, folder, sep in [(2024, "2024/enaho/966-Modulo01/Enaho01-2024-100.csv", ","),
                        (2025, "2025/enaho/1031-Modulo01/Enaho01-2025-100.csv", ";")]:
    d = pd.read_csv(ROOT / folder, sep=sep, encoding="latin-1", usecols=["UBIGEO", "RESULT", "HOGAR", "P102"], dtype=str)
    d = d[pd.to_numeric(d.RESULT, errors="coerce").isin([1, 2])]
    d = d[d.UBIGEO.str.zfill(6).str.startswith(("07", "1501"))]
    na = d.P102.str.strip().replace("", np.nan).isna()
    print(f"{yr}: {na.sum()} de {len(d)} hogares ({100 * na.mean():.2f}%) sin datos físicos de vivienda; "
          f"todos secundarios: {bool((d.HOGAR[na].astype(int) != 11).all())}")
