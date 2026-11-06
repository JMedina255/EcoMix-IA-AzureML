"""
Endpoints de inferencia predictiva para dosificaciones de concreto en EcoMix IA.
"""

from __future__ import annotations

from typing import Any, Dict, Union
from fastapi import APIRouter, Depends, Request, status

from src.api.dependencies import get_engine_dependency, verify_api_key
from src.inference.engine import InferenceEngine
from src.inference.schemas import (
    ConcreteMixDesign,
    PredictionRequest,
    PredictionResponse,
    ProblemDetails,
)

router = APIRouter(prefix="/api/v1/predict", tags=["Inferencia Predictiva"])


@router.post(
    "/concrete-strength",
    summary="Predicción Dual de Resistencia a Compresión (7 y 28 días)",
    description=(
        "Recibe las proporciones en kg/m³ de los siete materiales de una mezcla de concreto, "
        "valida los límites de dominio físico y experimental, y computa las resistencias esperadas "
        "a 7 y 28 días utilizando el modelo VotingEnsemble de Azure ML."
    ),
    response_model=PredictionResponse,
    responses={
        200: {
            "description": "Predicción calculada exitosamente con métricas, ratios y advertencias.",
            "model": PredictionResponse,
        },
        401: {
            "description": "Cabecera de autenticación 'X-API-Key' ausente.",
            "model": ProblemDetails,
        },
        403: {
            "description": "Clave API no autorizada o inválida.",
            "model": ProblemDetails,
        },
        422: {
            "description": "Violación de límites físicos o reglas de dominio del concreto.",
            "model": ProblemDetails,
        },
        503: {
            "description": "Modelo no preparado o runtime no compatible.",
            "model": ProblemDetails,
        },
    },
    status_code=status.HTTP_200_OK,
    dependencies=[Depends(verify_api_key)],
)
async def predict_concrete_strength_endpoint(
    payload: Union[PredictionRequest, ConcreteMixDesign, Dict[str, Any]],
    request: Request,
    engine: InferenceEngine = Depends(get_engine_dependency),
) -> PredictionResponse:
    """
    Ejecuta el ciclo de inferencia desacoplado.
    El motor valida los límites, ensambla las características conforme a la firma de MLflow
    y obtiene las resistencias a 7 y 28 días en una sola llamada vectorizada.
    """
    req_id = getattr(request.state, "request_id", None)

    # Inyectar el request_id de la solicitud HTTP si la carga no especificó uno propio
    if isinstance(payload, dict) and req_id and "request_id" not in payload:
        payload["request_id"] = req_id
    elif isinstance(payload, PredictionRequest) and req_id and not payload.request_id:
        payload.request_id = req_id

    response: PredictionResponse = engine.predict(payload)
    return response
