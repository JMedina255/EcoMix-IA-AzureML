"""
Punto de entrada CLI y fachada pública unificada para el servicio de inferencia de EcoMix IA.
Permite:
- Diagnosticar el estado y disponibilidad del modelo (CLI: --status, --check).
- Ejecutar inferencias determinísticas desde línea de comandos o scripts externos.
- Exponer las interfaces canónicas para consumo de adaptadores web (ASP.NET MVC 5 / FastAPI).
"""

from __future__ import annotations

import sys
from pathlib import Path

# Asegurar que la raíz del repositorio esté en sys.path para ejecución directa CLI
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.inference.cli import main
from src.inference import (
    ConcreteMixDesign,
    PredictionRequest,
    PredictionResponse,
    StrengthPredictions,
    MixRatios,
    StructuredWarning,
    ModelMetadata,
    InvalidFieldDetail,
    ProblemDetails,
    ValidationResult,
    DomainValidationError,
    validate_mix_design,
    validate_or_raise,
    compute_mix_ratios,
    UCI165_BOUNDS,
    PHYSICAL_BOUNDS,
    ModelLoader,
    ModelInferenceError,
    ModelNotFoundError,
    ModelIntegrityError,
    IncompatibleRuntimeError,
    OFFICIAL_MODEL_SHA256,
    OFFICIAL_RUN_ID,
    OFFICIAL_ALGORITHM,
    InferenceEngine,
    get_engine,
    initialize_engine,
    predict_concrete_strength,
    get_model_status,
    FEATURE_COLUMNS,
    DEFAULT_AGES,
)

__all__ = [
    "main",
    "ConcreteMixDesign",
    "PredictionRequest",
    "PredictionResponse",
    "StrengthPredictions",
    "MixRatios",
    "StructuredWarning",
    "ModelMetadata",
    "InvalidFieldDetail",
    "ProblemDetails",
    "ValidationResult",
    "DomainValidationError",
    "validate_mix_design",
    "validate_or_raise",
    "compute_mix_ratios",
    "UCI165_BOUNDS",
    "PHYSICAL_BOUNDS",
    "ModelLoader",
    "ModelInferenceError",
    "ModelNotFoundError",
    "ModelIntegrityError",
    "IncompatibleRuntimeError",
    "OFFICIAL_MODEL_SHA256",
    "OFFICIAL_RUN_ID",
    "OFFICIAL_ALGORITHM",
    "InferenceEngine",
    "get_engine",
    "initialize_engine",
    "predict_concrete_strength",
    "get_model_status",
    "FEATURE_COLUMNS",
    "DEFAULT_AGES",
]

if __name__ == "__main__":
    sys.exit(main())
