"""
Punto de entrada CLI y fachada pública unificada para el servicio de inferencia de EcoMix IA.
Permite:
- Diagnosticar el estado y disponibilidad del modelo (CLI: --status, --check).
- Ejecutar inferencias determinísticas desde línea de comandos o scripts externos.
- Exponer las interfaces canónicas para consumo de adaptadores web (ASP.NET MVC 5 / FastAPI).
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Dict, Optional, Union

# Asegurar que la raíz del repositorio esté en sys.path para ejecución directa CLI
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

if sys.platform == "win32" and hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

from src.inference.engine import (
    InferenceEngine,
    get_engine,
    get_model_status,
    initialize_engine,
    predict_concrete_strength,
)
from src.inference.model_loader import (
    ModelLoader,
    ModelInferenceError,
    ModelNotFoundError,
    ModelIntegrityError,
    IncompatibleRuntimeError,
    OFFICIAL_MODEL_SHA256,
    OFFICIAL_RUN_ID,
    OFFICIAL_ALGORITHM,
)
from src.inference.schemas import (
    ConcreteMixDesign,
    PredictionRequest,
    PredictionResponse,
    StrengthPredictions,
    MixRatios,
    ProblemDetails,
)
from src.inference.validator import (
    DomainValidationError,
    validate_mix_design,
    validate_or_raise,
)


def main() -> int:
    """Punto de entrada para ejecución en línea de comandos."""
    parser = argparse.ArgumentParser(
        description="Servicio de inferencia y diagnóstico de modelo EcoMix IA.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "--status",
        action="store_true",
        help="Muestra el diagnóstico de disponibilidad e integridad del modelo en formato JSON.",
    )
    parser.add_argument(
        "--check",
        action="store_true",
        help="Verifica la presencia física y el hash SHA-256 del artefacto oficial sin deserializar.",
    )
    parser.add_argument(
        "--predict",
        type=str,
        help="Cadena JSON o ruta a archivo con la dosificación en kg/m³.",
    )
    parser.add_argument(
        "--indent",
        type=int,
        default=2,
        help="Nivel de indentación para salida JSON (por defecto: 2).",
    )

    args = parser.parse_args()

    # Modo 1: Diagnóstico de Estado
    if args.status or args.check:
        status_info = get_model_status()
        if args.check:
            exists = status_info.get("artifact_exists_on_disk", False)
            sha_ok = status_info.get("sha256_verified", False)
            print("=" * 65)
            print(" ECOMIX IA — VERIFICACIÓN DE ARTEFACTO PREDICTIVO (CHECK)")
            print("=" * 65)
            print(f" Artefacto en disco:   {'[PRESENTE]' if exists else '[AUSENTE]'}")
            print(f" Hash SHA-256 Oficial: {status_info.get('official_sha256')}")
            print(f" Verificación SHA-256: {'[VALIDO]' if sha_ok else '[NO COINCIDE]'}")
            print(f" Algoritmo Certificado: {status_info.get('model_type')} ({status_info.get('run_id')})")
            print(f" Runtime Requerido:    Python {status_info.get('python_runtime')} / scikit-learn {status_info.get('sklearn_runtime')}")
            print("=" * 65)
            return 0 if (exists and sha_ok) else 1

        print(json.dumps(status_info, indent=args.indent))
        return 0

    # Modo 2: Inferencia vía JSON
    if args.predict:
        raw_input = args.predict.strip()
        payload: Dict[str, Any]
        if Path(raw_input).exists():
            with open(raw_input, "r", encoding="utf-8") as f:
                payload = json.load(f)
        else:
            try:
                payload = json.loads(raw_input)
            except Exception as e:
                print(f"Error al decodificar JSON de entrada: {e}", file=sys.stderr)
                return 1

        try:
            resp = predict_concrete_strength(payload)
            print(resp.model_dump_json(indent=args.indent))
            return 0
        except DomainValidationError as d_err:
            print(d_err.problem_details.model_dump_json(indent=args.indent), file=sys.stderr)
            return 2
        except IncompatibleRuntimeError as rt_err:
            print(json.dumps({
                "status": "error",
                "error_type": "IncompatibleRuntimeError",
                "message": str(rt_err),
            }, indent=args.indent), file=sys.stderr)
            return 3
        except ModelInferenceError as m_err:
            print(json.dumps({
                "status": "error",
                "error_type": type(m_err).__name__,
                "message": str(m_err),
            }, indent=args.indent), file=sys.stderr)
            return 4

    parser.print_help()
    return 0


if __name__ == "__main__":
    sys.exit(main())
