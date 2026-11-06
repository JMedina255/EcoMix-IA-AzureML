"""
Módulo de configuración para el servicio REST FastAPI de EcoMix IA.
Maneja variables de entorno, autenticación, rutas del modelo, endurecimiento
y aislamiento por instancia sin contaminación global.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import List, Optional, Set
from pydantic import BaseModel, Field, model_validator


# Raíz del proyecto
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent

# Claves prohibidas estrictamente en producción
BANNED_PRODUCTION_KEYS: Set[str] = {
    "ecomix-dev-api-key-2026",
    "dev",
    "development",
    "test",
    "testing",
    "secret",
    "admin",
    "password",
    "123456",
    "default",
}


class ApiSettings(BaseModel):
    """Configuración inmutable y endurecida del servicio API de inferencia."""

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
    api_key: Optional[str] = Field(default_factory=lambda: os.getenv("ECOMIX_API_KEY", None))
    api_key_secondary: Optional[str] = Field(default_factory=lambda: os.getenv("ECOMIX_API_KEY_SECONDARY", None))
    auth_enabled: bool = Field(
        default_factory=lambda: os.getenv("ECOMIX_AUTH_ENABLED", "true").lower() in ("true", "1")
    )

    # Rutas del modelo
    model_path: Optional[str] = Field(default_factory=lambda: os.getenv("ECOMIX_MODEL_PATH", None))

    # Límites operativos y de seguridad
    max_request_body_bytes: int = 1_048_576  # 1 MB
    default_request_timeout_seconds: float = 30.0

    @model_validator(mode="after")
    def validate_security_and_production_rules(self) -> ApiSettings:
        """Valida que la configuración en producción cumpla con las normas de seguridad corporativas."""
        env_norm = self.environment.strip().lower()
        self.environment = env_norm

        if env_norm == "production":
            # 1. Prohibido desactivar la autenticación en producción
            if not self.auth_enabled:
                raise ValueError("Prohibido desactivar la autenticación (ECOMIX_AUTH_ENABLED=false) en entorno de producción.")

            # 2. Clave obligatoria y no trivial
            if not self.api_key or not self.api_key.strip():
                raise ValueError(
                    "En entorno 'production', la clave de autenticación API debe configurarse obligatoriamente "
                    "mediante la variable de entorno 'ECOMIX_API_KEY'."
                )

            keys_to_check = [k.strip() for k in self.api_key.split(",") if k.strip()]
            for k in keys_to_check:
                if k.lower() in BANNED_PRODUCTION_KEYS:
                    raise ValueError(
                        f"La clave API configurada '{k}' coincide con una credencial de desarrollo prohibida. "
                        f"Debe utilizar un secreto criptográficamente seguro en producción."
                    )
                if len(k) < 16:
                    raise ValueError(
                        f"La clave API de producción debe tener al menos 16 caracteres de entropía (recibido: {len(k)} caracteres)."
                    )

        return self

    def get_valid_api_keys(self) -> List[str]:
        """
        Retorna la lista de todas las claves API autorizadas actualmente,
        soportando rotación segura con múltiples secretos activos.
        """
        keys: List[str] = []
        if self.api_key:
            # Soporta claves separadas por coma en una sola variable
            for k in self.api_key.split(","):
                k_clean = k.strip()
                if k_clean and k_clean not in keys:
                    keys.append(k_clean)

        if self.api_key_secondary:
            sec_clean = self.api_key_secondary.strip()
            if sec_clean and sec_clean not in keys:
                keys.append(sec_clean)

        return keys

    def __repr__(self) -> str:
        """Enmascara secretos en cualquier representación de texto o volcado de logs."""
        has_keys = bool(self.get_valid_api_keys())
        return (
            f"ApiSettings(environment={self.environment!r}, debug={self.debug}, "
            f"auth_enabled={self.auth_enabled}, keys_configured={has_keys}, "
            f"host={self.host!r}, port={self.port})"
        )


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
