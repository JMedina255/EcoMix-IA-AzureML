"""
Middlewares HTTP para observabilidad, trazabilidad y seguridad en EcoMix IA.
"""

from __future__ import annotations

import time
import uuid
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response, JSONResponse

from src.api.config import get_settings


class ObservabilityMiddleware(BaseHTTPMiddleware):
    """
    Middleware que:
    1. Propaga o genera un identificador único de solicitud (X-Request-ID).
    2. Registra el tiempo de procesamiento en milisegundos (X-Response-Time-Ms).
    3. Valida el tamaño máximo del cuerpo de la solicitud (1 MB).
    """

    async def dispatch(self, request: Request, call_next) -> Response:
        settings = get_settings()

        # 1. Trazabilidad de Request ID
        request_id = request.headers.get("X-Request-ID", str(uuid.uuid4()))
        request.state.request_id = request_id

        # 2. Control de tamaño de solicitud
        content_length = request.headers.get("content-length")
        if content_length and int(content_length) > settings.max_request_body_bytes:
            return JSONResponse(
                status_code=413,
                content={
                    "type": "https://ecomix.ia/errors/payload-too-large",
                    "title": "Cuerpo de Solicitud Excesivo",
                    "status": 413,
                    "detail": f"El tamaño del cuerpo excede el límite permitido de {settings.max_request_body_bytes} bytes.",
                    "instance": str(request.url.path),
                },
                headers={"X-Request-ID": request_id},
            )

        # 3. Medición de tiempo de respuesta
        t0 = time.perf_counter()
        try:
            response: Response = await call_next(request)
        except Exception:
            # En caso de excepción no controlada, permitir que los exception handlers operen
            raise
        finally:
            elapsed_ms = (time.perf_counter() - t0) * 1000.0

        # Inyectar cabeceras estándar
        response.headers["X-Request-ID"] = request_id
        response.headers["X-Response-Time-Ms"] = f"{elapsed_ms:.2f}"
        return response
