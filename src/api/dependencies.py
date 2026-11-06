"""
Dependencias inyectables para los endpoints de la API FastAPI de EcoMix IA.
Gestiona autenticación segura resistente a timing-attacks, rotación de credenciales
y aislamiento por instancia sin contaminación global.
"""

from __future__ import annotations

import secrets
from typing import Optional
from fastapi import Header, HTTPException, Request, status, Depends

from src.api.config import ApiSettings, get_settings
from src.inference.model_loader import ModelLoader
from src.inference.engine import InferenceEngine


def get_app_settings(request: Request) -> ApiSettings:
    """
    Retorna la configuración asociada estrictamente a la instancia de la aplicación
    FastAPI que atiende la solicitud actual, garantizando aislamiento total entre pruebas
    e instancias concurrentes.
    """
    app_settings = getattr(request.app.state, "settings", None)
    if app_settings is not None:
        return app_settings
    return get_settings()


async def verify_api_key(
    x_api_key: Optional[str] = Header(None, alias="X-API-Key"),
    settings: ApiSettings = Depends(get_app_settings),
) -> str:
    """
    Verifica la clave de autenticación API en la cabecera X-API-Key:
    1. Si auth_enabled es False (solo permitido en desarrollo/test), permite el paso.
    2. Si x_api_key está ausente, rechaza con HTTP 401.
    3. Si el servidor no tiene claves configuradas, rechaza con HTTP 503 (error de configuración).
    4. Compara el token recibido contra todas las claves válidas activas (soportando rotación)
       utilizando secrets.compare_digest para prevenir ataques de canal lateral (timing attacks).
    5. Nunca registra la clave en logs ni volcados.
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

    valid_keys = settings.get_valid_api_keys()
    if not valid_keys:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={
                "type": "https://ecomix.ia/errors/auth-misconfigured",
                "title": "Autenticación No Configurada",
                "status": 503,
                "detail": "El servicio de inferencia no cuenta con credenciales activas configuradas.",
            },
        )

    # Comparación en tiempo constante contra cada clave válida permitida (rotación)
    is_authorized = any(secrets.compare_digest(x_api_key, vk) for vk in valid_keys)

    if not is_authorized:
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
