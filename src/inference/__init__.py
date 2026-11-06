"""
Módulo de inferencia y validación de dosificaciones para EcoMix IA.
Provee esquemas tipados Pydantic v2, validación de dominio físico y experimental,
cálculos determinísticos de ratios de mezcla y serialización JSON para ASP.NET MVC 5.
"""

from .model_loader import (
    ModelLoader,
    ModelInferenceError,
    ModelNotFoundError,
    ModelIntegrityError,
    IncompatibleRuntimeError,
    OFFICIAL_MODEL_SHA256,
    OFFICIAL_RUN_ID,
    OFFICIAL_ALGORITHM,
)
from .engine import (
    InferenceEngine,
    get_engine,
    initialize_engine,
    predict_concrete_strength,
    get_model_status,
    FEATURE_COLUMNS,
    DEFAULT_AGES,
)
from .schemas import (
    ConcreteMixDesign,
    PredictionRequest,
    PredictionResponse,
    StrengthPredictions,
    MixRatios,
    StructuredWarning,
    ModelMetadata,
    InvalidFieldDetail,
    ProblemDetails,
)
from .validator import (
    ValidationResult,
    DomainValidationError,
    validate_mix_design,
    validate_or_raise,
    compute_mix_ratios,
    UCI165_BOUNDS,
    PHYSICAL_BOUNDS,
)

__all__ = [
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
