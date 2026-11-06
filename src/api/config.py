"""
Módulo de configuración para el servicio REST FastAPI de EcoMix IA.
Maneja variables de entorno, autenticación, rutas del modelo y parámetros operativos.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Optional
from pydantic import BaseModel, Field


# Raíz del proyecto
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent


class ApiSettings(BaseModel):
    """Configuración inmutable del servicio API de inferencia."""

    app_name: str = "EcoMix IA - Servicio de Inferencia ML"
    app_version: str = "1.0.0"
    app_description: str = (
        "API REST de inferencia de resistencia de concreto (7 y 28 días) "
        "utilizando el modelo VotingEnsemble certificado de Azure ML."
    )
    environment: str = Field(default_factory=lambda: os.getenv("ECOMIX_ENV", "development"))
    debug: bool = Field(default_factory=lambda: os.getenv("ECOMIX_DEBUG", "false").lower() in ("true", "1"))

    # Servidor HTTP
    host: str = Field(default_factory=lambda: os.getenv("ECOMIX_HOST", "0.0.0.0"))
    port: int = Field(default_factory=lambda: int(os.getenv("ECOMIX_PORT", "8000")))

    # Autenticación Servidor a Servidor (ASP.NET MVC 5 <-> FastAPI)
    api_key_header_name: str = "X-API-Key"
    api_key: Optional[str] = Field(
        default_factory=lambda: os.getenv("ECOMIX_API_KEY", "ecomix-dev-api-key-2026")
    )
    auth_enabled: bool = Field(
        default_factory=lambda: os.getenv("ECOMIX_AUTH_ENABLED", "true").lower() in ("true", "1")
    )

    # Rutas del modelo
    model_path: Optional[str] = Field(default_factory=lambda: os.getenv("ECOMIX_MODEL_PATH", None))

    # Límites operativos
    max_request_body_bytes: int = 1_048_576  # 1 MB
    default_request_timeout_seconds: float = 30.0


_settings: Optional[ApiSettings] = None


def get_settings() -> ApiSettings:
    """Obtiene o inicializa la configuración singleton de la API."""
    global _settings
    if _settings is None:
        _settings = ApiSettings()
    return _settings


def reset_settings() -> None:
    """Reinicia la instancia de configuración (útil para pruebas unitarias)."""
    global _settings
    _settings = None
