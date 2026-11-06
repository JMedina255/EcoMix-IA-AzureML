"""
Dependencias inyectables para los endpoints de la API FastAPI de EcoMix IA.
Gestiona autenticación entre servidores y acceso al motor de inferencia.
"""

from __future__ import annotations

from typing import Optional
from fastapi import Header, HTTPException, status, Depends

from src.api.config import ApiSettings, get_settings
from src.inference.model_loader import ModelLoader
from src.inference.engine import InferenceEngine, get_engine


async def verify_api_key(
    x_api_key: Optional[str] = Header(None, alias="X-API-Key"),
    settings: ApiSettings = Depends(get_settings),
) -> str:
    """
    Verifica la clave de autenticación API en la cabecera X-API-Key.
    Garantiza que sólo servicios autorizados (como el backend ASP.NET MVC 5) consuman la API.
    """
    if not settings.auth_enabled:
        return "auth_disabled"

    if not x_api_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={
                "type": "https://ecomix.ia/errors/unauthorized",
                "title": "Clave API Ausente",
                "status": 401,
                "detail": "La cabecera 'X-API-Key' es requerida para autenticar la solicitud de inferencia.",
            },
        )

    if x_api_key != settings.api_key:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={
                "type": "https://ecomix.ia/errors/forbidden",
                "title": "Clave API Inválida",
                "status": 403,
                "detail": "La clave API proporcionada no es válida para este servicio.",
            },
        )

    return x_api_key


def get_model_loader() -> ModelLoader:
    """Obtiene la instancia singleton de ModelLoader."""
    return ModelLoader.get_instance()


def get_engine_dependency(
    loader: ModelLoader = Depends(get_model_loader),
) -> InferenceEngine:
    """Obtiene el motor de inferencia asociado al cargador."""
    return InferenceEngine(loader)
