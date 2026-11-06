"""
Fábrica de aplicación y punto de entrada para la API REST FastAPI de EcoMix IA.
Orquesta el ciclo de vida (lifespan), middlewares, enrutadores y manejadores de error.
"""

from __future__ import annotations

import logging
import sys
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any, AsyncGenerator, Dict

from fastapi import FastAPI, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
import uvicorn

# Asegurar que la raíz del repositorio esté en sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.api.config import ApiSettings, get_settings
from src.api.middleware import ObservabilityMiddleware
from src.api.routes import health_router, model_router, prediction_router
from src.api.exception_handlers import (
    domain_validation_exception_handler,
    request_validation_exception_handler,
    model_availability_exception_handler,
    model_inference_exception_handler,
    http_exception_handler,
    generic_exception_handler,
)
from src.inference.model_loader import (
    ModelLoader,
    IncompatibleRuntimeError,
    ModelNotFoundError,
    ModelIntegrityError,
    ModelInferenceError,
    OFFICIAL_MODEL_SHA256,
)
from src.inference.validator import DomainValidationError

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("ecomix.api")


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """
    Gestión del ciclo de vida de la aplicación:
    1. Arranque (Startup): Inicializa y carga en memoria RAM el modelo VotingEnsemble una sola vez.
       En caso de runtime incompatible (e.g. desarrollo local bajo Python 3.13), registra la advertencia
       sin abortar el proceso, permitiendo responder a sondas de vida y pruebas.
    2. Parada (Shutdown): Libera recursos de forma segura.
    """
    settings: ApiSettings = app.state.settings
    loader = ModelLoader.get_instance()

    logger.info("Inicializando servicio EcoMix IA (Entorno: %s)...", settings.environment)

    # Intentar carga en memoria del modelo oficial si existe en disco
    try:
        if not loader.is_loaded():
            logger.info("Cargando artefacto VotingEnsemble en memoria RAM...")
            loader.load_model(
                model_path=settings.model_path,
                expected_sha256=OFFICIAL_MODEL_SHA256,
            )
            logger.info("Modelo VotingEnsemble cargado exitosamente en memoria RAM.")
    except IncompatibleRuntimeError as rt_err:
        logger.warning(
            "Aviso de Runtime: %s. La API operará con sondas de preparación en 503 hasta contar con un runtime compatible.",
            rt_err,
        )
    except ModelNotFoundError as fnf_err:
        logger.warning("Modelo no encontrado en disco: %s. Verifique la ruta configurada.", fnf_err)
    except Exception as ex:
        logger.error("Error durante la inicialización del modelo: %s", ex, exc_info=True)

    yield

    logger.info("Deteniendo servicio EcoMix IA y liberando recursos...")


def create_app(settings: ApiSettings | None = None) -> FastAPI:
    """Fábrica de aplicación FastAPI."""
    current_settings = settings or get_settings()

    app = FastAPI(
        title=current_settings.app_name,
        version=current_settings.app_version,
        description=current_settings.app_description,
        lifespan=lifespan,
        docs_url="/docs" if current_settings.debug or current_settings.environment != "production" else None,
        redoc_url="/redoc" if current_settings.debug or current_settings.environment != "production" else None,
        openapi_url="/openapi.json" if current_settings.debug or current_settings.environment != "production" else None,
    )

    app.state.settings = current_settings

    # 1. Registrar Middlewares
    app.add_middleware(ObservabilityMiddleware)

    # 2. Registrar Manejadores de Excepciones RFC 7807 (ProblemDetails)
    app.add_exception_handler(DomainValidationError, domain_validation_exception_handler)
    app.add_exception_handler(RequestValidationError, request_validation_exception_handler)
    app.add_exception_handler(IncompatibleRuntimeError, model_availability_exception_handler)
    app.add_exception_handler(ModelNotFoundError, model_availability_exception_handler)
    app.add_exception_handler(ModelIntegrityError, model_availability_exception_handler)
    app.add_exception_handler(ModelInferenceError, model_inference_exception_handler)
    from fastapi import HTTPException
    app.add_exception_handler(HTTPException, http_exception_handler)
    app.add_exception_handler(Exception, generic_exception_handler)

    # 3. Registrar Enrutadores
    app.include_router(health_router)
    app.include_router(model_router)
    app.include_router(prediction_router)

    # 4. Endpoint Raíz
    @app.get(
        "/",
        summary="Información General del Servicio",
        include_in_schema=False,
    )
    async def root_info() -> Dict[str, Any]:
        return {
            "service": current_settings.app_name,
            "version": current_settings.app_version,
            "status": "online",
            "documentation": "/docs" if app.docs_url else "disabled_in_production",
        }

    return app


# Instancia por defecto de la aplicación para servidores ASGI (Uvicorn / Gunicorn)
app = create_app()


def main() -> int:
    """Punto de entrada para ejecución directa CLI."""
    settings = get_settings()
    uvicorn.run(
        "src.api.main:app",
        host=settings.host,
        port=settings.port,
        reload=settings.debug,
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
