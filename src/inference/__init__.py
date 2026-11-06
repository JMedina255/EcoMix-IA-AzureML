"""
Módulo de inferencia y validación de dosificaciones para EcoMix IA.
Provee esquemas tipados Pydantic v2, validación de dominio físico y experimental,
cálculos determinísticos de ratios de mezcla y serialización JSON para ASP.NET MVC 5.
"""

from src.inference.schemas import (
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
from src.inference.validator import (
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
]
