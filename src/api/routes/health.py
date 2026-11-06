"""
Endpoints de comprobación de salud, preparación y disponibilidad para orquestadores
(Kubernetes / Azure Container Apps).
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict
from fastapi import APIRouter, Depends, status, Response
from fastapi.responses import JSONResponse

from src.api.config import ApiSettings
from src.api.dependencies import get_model_loader, get_app_settings
from src.inference.model_loader import ModelLoader

router = APIRouter(prefix="/health", tags=["Salud y Disponibilidad"])


@router.get(
    "/live",
    summary="Sonda de Vida (Liveness Probe)",
    description=(
        "Comprueba que el proceso ASGI de la API está en ejecución activa y respondiendo solicitudes HTTP. "
        "En orquestadores de contenedores, si esta sonda falla reiteradamente, el contenedor es reiniciado."
    ),
    response_description="El proceso está vivo y aceptando conexiones.",
    status_code=status.HTTP_200_OK,
)
async def liveness_probe() -> Dict[str, Any]:
    return {
        "status": "alive",
        "service": "ecomix-ia-ml-api",
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


@router.get(
    "/startup",
    summary="Sonda de Arranque (Startup Probe)",
    description=(
        "Comprueba si el contenedor ha completado su fase de arranque inicial e instanciación del modelo. "
        "Permite mitigar el arranque en frío (~26 segundos de importación de AutoML) en Azure Container Apps "
        "otorgando una ventana de espera antes de activar las sondas de liveness y readiness."
    ),
    response_description="El servicio completó el arranque (200) o está inicializando (503).",
)
async def startup_probe(
    loader: ModelLoader = Depends(get_model_loader),
    settings: ApiSettings = Depends(get_app_settings),
) -> Response:
    return await readiness_probe(loader=loader, settings=settings)


@router.get(
    "/ready",
    summary="Sonda de Preparación (Readiness Probe)",
    description=(
        "Comprueba si el modelo de Machine Learning está cargado en memoria RAM y en condiciones de procesar inferencias. "
        "En modo producción, rechaza terminantemente estimadores sintéticos (mocks) para evitar servir datos espurios."
    ),
    response_description="El servicio está preparado para recibir tráfico (200) o no disponible (503).",
)
async def readiness_probe(
    loader: ModelLoader = Depends(get_model_loader),
    settings: ApiSettings = Depends(get_app_settings),
) -> Response:
    is_loaded = loader.is_loaded()
    artifact_info = loader.get_artifact_info()

    if is_loaded:
        # En producción, prohibir terminantemente estimadores sintéticos de test
        if settings.environment == "production" and artifact_info and artifact_info.is_synthetic:
            payload = {
                "type": "https://ecomix.ia/errors/synthetic-model-forbidden",
                "title": "Estimador Sintético No Permitido en Producción",
                "status": status.HTTP_503_SERVICE_UNAVAILABLE,
                "detail": (
                    "El servicio está configurado en entorno de producción pero el modelo en memoria "
                    "es un estimador sintético de pruebas. Se requiere el VotingEnsemble oficial certificado."
                ),
                "model_ready": False,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }
            return JSONResponse(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                content=payload,
                headers={"Content-Type": "application/problem+json"},
            )

        payload = {
            "status": "ready",
            "service": "ecomix-ia-ml-api",
            "model_ready": True,
            "environment": settings.environment,
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
