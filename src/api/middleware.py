"""
Middlewares HTTP para observabilidad, trazabilidad, seguridad y endurecimiento en EcoMix IA.
"""

from __future__ import annotations

import re
import time
import uuid
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response, JSONResponse

from src.api.config import ApiSettings, get_settings

# Patrón estricto para X-Request-ID seguro (alfanumérico, guion, punto, dos puntos, guion bajo; máx 128 chars)
REQUEST_ID_REGEX = re.compile(r"^[a-zA-Z0-9_\-\.:]{1,128}$")


class ObservabilityMiddleware(BaseHTTPMiddleware):
    """
    Middleware que:
    1. Propaga o sanitiza el identificador de solicitud (X-Request-ID), previniendo inyección de cabeceras.
    2. Registra el tiempo de procesamiento en milisegundos (X-Response-Time-Ms).
    3. Valida y controla el tamaño máximo del cuerpo de solicitud (incluso sin Content-Length).
    4. Detecta cabeceras Content-Length malformadas devolviendo HTTP 400.
    5. Valida tipos de contenido (Content-Type) en endpoints POST predictivos devolviendo HTTP 415.
    6. Utiliza estrictamente la configuración de la instancia de la aplicación (app.state.settings).
    """

    async def dispatch(self, request: Request, call_next) -> Response:
        settings: ApiSettings = getattr(request.app.state, "settings", None) or get_settings()

        # 1. Trazabilidad y sanitización estricta de X-Request-ID
        raw_request_id = request.headers.get("X-Request-ID")
        if raw_request_id and REQUEST_ID_REGEX.match(raw_request_id):
            request_id = raw_request_id
        else:
            request_id = str(uuid.uuid4())
        request.state.request_id = request_id

        # 2. Control de cabecera Content-Length y detección de malformación
        content_length_header = request.headers.get("content-length")
        declared_length: int | None = None
        if content_length_header is not None:
            try:
                declared_length = int(content_length_header)
                if declared_length < 0:
                    raise ValueError("Content-Length negativo")
            except ValueError:
                return JSONResponse(
                    status_code=400,
                    content={
                        "type": "https://ecomix.ia/errors/bad-request",
                        "title": "Cabecera Content-Length Inválida",
                        "status": 400,
                        "detail": "La cabecera Content-Length debe ser un número entero mayor o igual a cero.",
                        "instance": str(request.url.path),
                        "request_id": request_id,
                    },
                    headers={"Content-Type": "application/problem+json", "X-Request-ID": request_id},
                )

            if declared_length > settings.max_request_body_bytes:
                return JSONResponse(
                    status_code=413,
                    content={
                        "type": "https://ecomix.ia/errors/payload-too-large",
                        "title": "Cuerpo de Solicitud Excesivo",
                        "status": 413,
                        "detail": (
                            f"El tamaño declarado en Content-Length ({declared_length} bytes) "
                            f"excede el límite permitido de {settings.max_request_body_bytes} bytes."
                        ),
                        "instance": str(request.url.path),
                        "request_id": request_id,
                    },
                    headers={"Content-Type": "application/problem+json", "X-Request-ID": request_id},
                )

        # 3. Control de cuerpo sobredimensionado cuando falta Content-Length (ej. chunked transfer)
        if request.method in ("POST", "PUT", "PATCH"):
            # Leer el cuerpo en memoria; Starlette lo cachea internamente en request._body
            body = await request.body()
            if len(body) > settings.max_request_body_bytes:
                return JSONResponse(
                    status_code=413,
                    content={
                        "type": "https://ecomix.ia/errors/payload-too-large",
                        "title": "Cuerpo de Solicitud Excesivo",
                        "status": 413,
                        "detail": (
                            f"El cuerpo de la solicitud ({len(body)} bytes) "
                            f"excede el límite permitido de {settings.max_request_body_bytes} bytes."
                        ),
                        "instance": str(request.url.path),
                        "request_id": request_id,
                    },
                    headers={"Content-Type": "application/problem+json", "X-Request-ID": request_id},
                )

        # 4. Validación de Content-Type en endpoints de inferencia
        if request.method in ("POST", "PUT", "PATCH") and request.url.path.startswith("/api/v1/predict"):
            content_type = request.headers.get("content-type", "")
            if not (content_type.startswith("application/json") or content_type.startswith("application/problem+json")):
                return JSONResponse(
                    status_code=415,
                    content={
                        "type": "https://ecomix.ia/errors/unsupported-media-type",
                        "title": "Tipo de Contenido No Soportado",
                        "status": 415,
                        "detail": (
                            f"El endpoint de inferencia requiere cabecera 'Content-Type: application/json' "
                            f"(recibido: '{content_type or 'vacío'}')."
                        ),
                        "instance": str(request.url.path),
                        "request_id": request_id,
                    },
                    headers={"Content-Type": "application/problem+json", "X-Request-ID": request_id},
                )

        # 5. Medición de tiempo de respuesta
        t0 = time.perf_counter()
        try:
            response: Response = await call_next(request)
        except Exception:
            raise
        finally:
            elapsed_ms = (time.perf_counter() - t0) * 1000.0

        # Inyectar cabeceras estándar
        response.headers["X-Request-ID"] = request_id
        response.headers["X-Response-Time-Ms"] = f"{elapsed_ms:.2f}"
        return response
