"""
Endpoints de metadatos, procedencia y diagnóstico del modelo VotingEnsemble de EcoMix IA.
"""

from __future__ import annotations

from typing import Any, Dict
from fastapi import APIRouter, Depends, status

from src.api.dependencies import get_model_loader, verify_api_key
from src.inference.model_loader import (
    ModelLoader,
    OFFICIAL_MODEL_SHA256,
    OFFICIAL_RUN_ID,
    OFFICIAL_ALGORITHM,
)
from src.inference.engine import get_model_status

router = APIRouter(prefix="/api/v1/model", tags=["Metadatos del Modelo"])


@router.get(
    "/info",
    summary="Información y Metadatos del Modelo Certificado",
    description="Devuelve el estado de procedencia, integridad SHA-256 y metadatos del VotingEnsemble.",
    response_description="Detalles técnicos y procedencia del modelo.",
    status_code=status.HTTP_200_OK,
    dependencies=[Depends(verify_api_key)],
)
async def get_model_info(
    loader: ModelLoader = Depends(get_model_loader),
) -> Dict[str, Any]:
    status_info = get_model_status()
    artifact_info = loader.get_artifact_info()

    return {
        "status": "success",
        "model_id": artifact_info.run_id if artifact_info else OFFICIAL_RUN_ID,
        "algorithm": artifact_info.model_type if artifact_info else OFFICIAL_ALGORITHM,
        "official_sha256": OFFICIAL_MODEL_SHA256,
        "is_model_loaded_in_ram": loader.is_loaded(),
        "is_synthetic": artifact_info.is_synthetic if artifact_info else False,
        "artifact_details": status_info,
        "evaluation_benchmark": {
            "r2_score": 0.9121,
            "rmse_mpa": 4.7592,
            "mae_mpa": 3.2822,
            "nrmse": 0.0673,
            "samples_evaluated": 206,
        },
        "curated_runtime": {
            "python": "3.10.19",
            "scikit_learn": "1.5.1",
            "mlflow": "2.15.1",
            "automl_runtime": "1.61.0",
        },
    }
