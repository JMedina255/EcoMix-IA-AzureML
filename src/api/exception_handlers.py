"""
Manejadores globales de excepciones para la API REST de EcoMix IA.
Garantiza respuestas estructuradas bajo el estándar RFC 7807 (ProblemDetails),
sin exponer rutas internas, trazas de pila (stack traces) ni credenciales.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List
from fastapi import Request, HTTPException, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from src.inference.schemas import ProblemDetails, InvalidFieldDetail
from src.inference.validator import DomainValidationError
from src.inference.model_loader import (
    IncompatibleRuntimeError,
    ModelNotFoundError,
    ModelIntegrityError,
    ModelInferenceError,
)

logger = logging.getLogger("ecomix.api")


async def domain_validation_exception_handler(
    request: Request, exc: DomainValidationError
) -> JSONResponse:
    """Maneja violaciones de reglas de negocio y límites físicos del concreto (HTTP 422)."""
    req_id = getattr(request.state, "request_id", None)
    details = exc.problem_details.model_dump()
    if req_id and not details.get("request_id"):
        details["request_id"] = req_id
    if not details.get("instance"):
        details["instance"] = str(request.url.path)

    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content=details,
        headers={"Content-Type": "application/problem+json"},
    )


async def request_validation_exception_handler(
    request: Request, exc: RequestValidationError
) -> JSONResponse:
    """Maneja errores de validación de sintaxis o tipos Pydantic en la solicitud (HTTP 422)."""
    req_id = getattr(request.state, "request_id", None)
    invalid_fields: List[InvalidFieldDetail] = []

    for err in exc.errors():
        field_loc = ".".join(str(loc) for loc in err.get("loc", []) if loc != "body")
        invalid_fields.append(
            InvalidFieldDetail(
                field=field_loc or "body",
                value=str(err.get("input", "")),
                constraint="json_schema_error",
                limit=None,
                unit=None,
                message=err.get("msg", "Dato o tipo inválido."),
            )
        )

    problem = ProblemDetails(
        type="https://ecomix.ia/errors/request-validation-error",
        title="Error de Validación de Esquema JSON",
        status=status.HTTP_422_UNPROCESSABLE_ENTITY,
        detail="La estructura de la solicitud contiene tipos o campos no válidos.",
        instance=str(request.url.path),
        invalid_fields=invalid_fields,
    )

    details = problem.model_dump()
    if req_id:
        details["request_id"] = req_id

    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content=details,
        headers={"Content-Type": "application/problem+json"},
    )


async def model_availability_exception_handler(
    request: Request,
    exc: IncompatibleRuntimeError | ModelNotFoundError | ModelIntegrityError,
) -> JSONResponse:
    """Maneja indisponibilidad o incompatibilidad del modelo en tiempo de ejecución (HTTP 503)."""
    req_id = getattr(request.state, "request_id", None)
    logger.warning("Modelo no disponible para inferencia: %s (Request: %s)", exc, req_id)

    problem = ProblemDetails(
        type="https://ecomix.ia/errors/model-unavailable",
        title="Modelo Predictivo No Disponible",
        status=status.HTTP_503_SERVICE_UNAVAILABLE,
        detail=(
            "El modelo predictivo no se encuentra cargado o el runtime actual es incompatible. "
            "El servicio se encuentra en espera de un entorno certificado."
        ),
        instance=str(request.url.path),
    )

    details = problem.model_dump()
    if req_id:
        details["request_id"] = req_id

    return JSONResponse(
        status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        content=details,
        headers={"Content-Type": "application/problem+json"},
    )


async def model_inference_exception_handler(
    request: Request, exc: ModelInferenceError
) -> JSONResponse:
    """Maneja errores ocurridos durante la ejecución del estimador (HTTP 500)."""
    req_id = getattr(request.state, "request_id", None)
    logger.error("Error durante inferencia del modelo: %s (Request: %s)", exc, req_id, exc_info=True)

    problem = ProblemDetails(
        type="https://ecomix.ia/errors/inference-computation-failed",
        title="Fallo en Cómputo de Inferencia",
        status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        detail="Ocurrió un error al procesar el modelo de Machine Learning con los datos suministrados.",
        instance=str(request.url.path),
    )

    details = problem.model_dump()
    if req_id:
        details["request_id"] = req_id

    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content=details,
        headers={"Content-Type": "application/problem+json"},
    )


async def http_exception_handler(request: Request, exc: HTTPException) -> JSONResponse:
    """Normaliza excepciones HTTP estándar (401, 403, 404, etc.) al formato ProblemDetails."""
    req_id = getattr(request.state, "request_id", None)
    detail_content: Any = exc.detail

    if isinstance(detail_content, dict) and "title" in detail_content:
        content = detail_content
        if req_id and "request_id" not in content:
            content["request_id"] = req_id
        if "instance" not in content:
            content["instance"] = str(request.url.path)
    else:
        content = {
            "type": f"https://ecomix.ia/errors/http-{exc.status_code}",
            "title": "Error HTTP",
            "status": exc.status_code,
            "detail": str(detail_content),
            "instance": str(request.url.path),
            "request_id": req_id,
        }

    return JSONResponse(
        status_code=exc.status_code,
        content=content,
        headers={"Content-Type": "application/problem+json"},
    )


async def generic_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """Manejador de captura general para cualquier error inesperado (HTTP 500)."""
    req_id = getattr(request.state, "request_id", None)
    logger.exception("Excepción no controlada en la API: %s (Request: %s)", exc, req_id)

    problem = ProblemDetails(
        type="https://ecomix.ia/errors/internal-server-error",
        title="Error Interno del Servidor",
        status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        detail="Se produjo un error inesperado al procesar la solicitud. Contacte al administrador con el identificador provisto.",
        instance=str(request.url.path),
        request_id=req_id,
    )

    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content=problem.model_dump(),
        headers={"Content-Type": "application/problem+json"},
    )
