"""
Endpoints de comprobación de salud y disponibilidad para orquestadores (Kubernetes / Azure Container Apps).
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict
from fastapi import APIRouter, Depends, status, Response
from fastapi.responses import JSONResponse

from src.api.dependencies import get_model_loader
from src.inference.model_loader import ModelLoader

router = APIRouter(prefix="/health", tags=["Salud y Disponibilidad"])


@router.get(
    "/live",
    summary="Sonda de Vida (Liveness Probe)",
    description="Comprueba que el proceso de la API está vivo y aceptando conexiones HTTP.",
    response_description="El proceso está en ejecución activa.",
    status_code=status.HTTP_200_OK,
)
async def liveness_probe() -> Dict[str, Any]:
    return {
        "status": "alive",
        "service": "ecomix-ia-ml-api",
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


@router.get(
    "/ready",
    summary="Sonda de Preparación (Readiness Probe)",
    description="Comprueba si el modelo VotingEnsemble está cargado en memoria RAM y listo para procesar inferencias.",
    response_description="El servicio está listo (200) o aún no está preparado (503).",
)
async def readiness_probe(
    loader: ModelLoader = Depends(get_model_loader),
) -> Response:
    is_loaded = loader.is_loaded()
    artifact_info = loader.get_artifact_info()

    if is_loaded:
        payload = {
            "status": "ready",
            "service": "ecomix-ia-ml-api",
            "model_ready": True,
            "model_id": artifact_info.run_id if artifact_info else "wheat_cheese_4swj34tkjn_11",
            "model_type": artifact_info.model_type if artifact_info else "VotingEnsemble",
            "model_sha256": artifact_info.sha256 if artifact_info else None,
            "is_synthetic": artifact_info.is_synthetic if artifact_info else False,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
        return JSONResponse(status_code=status.HTTP_200_OK, content=payload)
    else:
        payload = {
            "type": "https://ecomix.ia/errors/service-not-ready",
            "title": "Servicio No Preparado",
            "status": status.HTTP_503_SERVICE_UNAVAILABLE,
            "detail": (
                "El modelo de inferencia aún no se encuentra cargado en memoria RAM o el entorno "
                "actual requiere compatibilidad con el runtime de Azure AutoML."
            ),
            "model_ready": False,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
        return JSONResponse(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            content=payload,
            headers={"Content-Type": "application/problem+json"},
        )
