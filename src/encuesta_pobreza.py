"""
Script ejecutable de aplicación del modelo ganador (`Stacking_Ensemble` regularizado)
sobre encuestas de hogares en Lima Metropolitana y Callao.

Modos de uso:
  python3 src/encuesta_pobreza.py                     # Entrena/carga el modelo e inicia encuesta interactiva
  python3 src/encuesta_pobreza.py --train             # Reentrena (2024+2025 deduplicado) y exporta models/winner_bundle.joblib
  python3 src/encuesta_pobreza.py --preset all        # Evalúa los 3 hogares demostrativos sin tipeo manual
  python3 src/encuesta_pobreza.py --preset vulnerable_hacinado
"""
import argparse
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from src.inference import (
    DEFAULT_BUNDLE_PATH,
    PRESET_HOUSEHOLDS,
    format_prediction_report,
    load_deployment_bundle,
    predict_single_household,
    run_interactive_survey,
    train_and_export_deployment_bundle,
)


def main():
    parser = argparse.ArgumentParser(
        description="Aplicación interactiva del modelo ganador de focalización de pobreza (ENAHO 2024-2025)."
    )
    parser.add_argument(
        "--train",
        action="store_true",
        help="Reentrena el modelo ganador sobre 2024+2025 (deduplicado) y actualiza models/winner_bundle.joblib.",
    )
    parser.add_argument(
        "--preset",
        choices=["all", *PRESET_HOUSEHOLDS.keys()],
        default=None,
        help="Evalúa escenarios predefinidos en lugar de iniciar la encuesta interactiva.",
    )
    parser.add_argument(
        "--bundle",
        type=Path,
        default=DEFAULT_BUNDLE_PATH,
        help=f"Ruta al artefacto .joblib (por defecto: {DEFAULT_BUNDLE_PATH}).",
    )
    args = parser.parse_args()

    if args.train or not args.bundle.exists():
        bundle, _ = train_and_export_deployment_bundle(
            years=(2024, 2025),
            save_path=args.bundle,
            verbose=True,
        )
    else:
        bundle = load_deployment_bundle(args.bundle)

    if args.preset is not None:
        names = list(PRESET_HOUSEHOLDS.keys()) if args.preset == "all" else [args.preset]
        for name in names:
            ans = PRESET_HOUSEHOLDS[name]
            res = predict_single_household(bundle, ans)
            print("\n" + format_prediction_report(res, label=f"Preset '{name}' — {ans['descripcion']}"))
        return

    run_interactive_survey(bundle)


if __name__ == "__main__":
    main()
