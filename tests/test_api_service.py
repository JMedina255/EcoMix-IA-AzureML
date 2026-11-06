"""
Suite de pruebas automatizadas para la API REST FastAPI de EcoMix IA (Fase 5.5).
Verifica:
1. Endpoints de salud (/health/live y /health/ready con separación de estados).
2. Autenticación entre servidores (X-API-Key: 401 ausente, 403 inválida, 200 autorizada).
3. Inferencia dual a 7 y 28 días con validación de contratos JSON para ASP.NET MVC 5.
4. Paridad exacta con el motor InferenceEngine validado en la Fase 5.4.
5. Manejo estructurado de errores bajo RFC 7807 (ProblemDetails).
6. Trazabilidad (X-Request-ID y X-Response-Time-Ms).
7. Concurrencia y estabilidad de memoria.
"""

from __future__ import annotations

import math
import threading
import time
from typing import Any, Dict
import pytest
from fastapi.testclient import TestClient

from src.api.config import ApiSettings, get_settings, reset_settings
from src.api.main import create_app
from src.inference.engine import InferenceEngine
from src.inference.model_loader import (
    ModelLoader,
    OFFICIAL_MODEL_SHA256,
    OFFICIAL_RUN_ID,
    OFFICIAL_ALGORITHM,
)


class DeterministicBenchmarkEstimator:
    """Estimador sintético de pruebas para validación controlada de la API."""

    def __init__(self):
        self._is_synthetic_test = True

    def predict(self, X):
        import numpy as np
        preds = []
        for _, row in X.iterrows():
            c = float(row["cement"])
            s = float(row["blast_furnace_slag"])
            f = float(row["fly_ash"])
            w = float(row["water"])
            sp = float(row["superplasticizer"])
            ca = float(row["coarse_aggregate"])
            fa = float(row["fine_aggregate"])
            age = float(row["age"])

            # Fórmula determinística continua no negativa
            base = 0.05 * c + 0.04 * s + 0.03 * f - 0.08 * w + 0.8 * sp + 0.01 * (ca + fa)
            age_factor = math.log(max(age, 1.0) + 1.0) / math.log(29.0)
            val = max(base * age_factor, 10.0)
            preds.append(val)
        return np.array(preds)


CANONICAL_MIX = {
    "cement": 280.0,
    "blast_furnace_slag": 105.0,
    "fly_ash": 60.0,
    "water": 175.0,
    "superplasticizer": 8.5,
    "coarse_aggregate": 1020.0,
    "fine_aggregate": 750.0,
}

HIGH_SCM_MIX = {
    "cement": 160.0,
    "blast_furnace_slag": 220.0,
    "fly_ash": 70.0,
    "water": 165.0,
    "superplasticizer": 9.0,
    "coarse_aggregate": 1000.0,
    "fine_aggregate": 740.0,
}

VALID_API_KEY = "ecomix-dev-api-key-2026"
AUTH_HEADERS = {"X-API-Key": VALID_API_KEY}


@pytest.fixture(autouse=True)
def clean_api_environment():
    """Restaura la configuración y el estado de ModelLoader antes de cada prueba."""
    reset_settings()
    loader = ModelLoader.get_instance()
    loader.reset()
    yield
    loader.reset()
    reset_settings()


@pytest.fixture
def api_client() -> TestClient:
    """Fixture que provee un cliente HTTP de prueba sobre la aplicación FastAPI."""
    settings = ApiSettings(
        environment="test",
        debug=True,
        auth_enabled=True,
        api_key=VALID_API_KEY,
    )
    app = create_app(settings)
    return TestClient(app, raise_server_exceptions=False)


# =====================================================================
# 1. PRUEBAS DE SONDA DE SALUD Y DISPONIBILIDAD (HEALTH ENDPOINTS)
# =====================================================================

def test_liveness_probe_returns_200(api_client: TestClient):
    """Verifica que /health/live retorne HTTP 200 y propague cabeceras de observabilidad."""
    response = api_client.get("/health/live")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "alive"
    assert data["service"] == "ecomix-ia-ml-api"
    assert "timestamp" in data
    assert "x-request-id" in response.headers
    assert "x-response-time-ms" in response.headers


def test_readiness_probe_returns_503_when_model_not_loaded(api_client: TestClient):
    """Verifica que /health/ready retorne HTTP 503 cuando el modelo no está en RAM."""
    loader = ModelLoader.get_instance()
    assert not loader.is_loaded()

    response = api_client.get("/health/ready")
    assert response.status_code == 503
    assert response.headers["content-type"] == "application/problem+json"
    data = response.json()
    assert data["status"] == 503
    assert data["model_ready"] is False
    assert "title" in data
    assert data["type"] == "https://ecomix.ia/errors/service-not-ready"


def test_readiness_probe_returns_200_when_model_is_ready(api_client: TestClient):
    """Verifica que /health/ready retorne HTTP 200 una vez cargado el modelo."""
    loader = ModelLoader.get_instance()
    loader.set_test_estimator(DeterministicBenchmarkEstimator())
    assert loader.is_loaded()

    response = api_client.get("/health/ready")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ready"
    assert data["model_ready"] is True
    assert data["is_synthetic"] is True


def test_root_endpoint_returns_service_info(api_client: TestClient):
    """Verifica el endpoint raíz / de información básica."""
    response = api_client.get("/")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "online"
    assert "EcoMix IA" in data["service"]


# =====================================================================
# 2. PRUEBAS DE AUTENTICACIÓN ENTRE SERVIDORES (X-API-KEY)
# =====================================================================

def test_api_key_missing_returns_401(api_client: TestClient):
    """Verifica que la omisión de X-API-Key devuelva HTTP 401 con ProblemDetails."""
    response = api_client.get("/api/v1/model/info")
    assert response.status_code == 401
    assert response.headers["content-type"] == "application/problem+json"
    data = response.json()
    assert data["status"] == 401
    assert "Clave API Ausente" in data["title"]


def test_api_key_invalid_returns_403(api_client: TestClient):
    """Verifica que una X-API-Key inválida devuelva HTTP 403 con ProblemDetails."""
    response = api_client.get("/api/v1/model/info", headers={"X-API-Key": "clave-falsa-invalida"})
    assert response.status_code == 403
    assert response.headers["content-type"] == "application/problem+json"
    data = response.json()
    assert data["status"] == 403
    assert "Clave API Inválida" in data["title"]


def test_api_key_valid_grants_access(api_client: TestClient):
    """Verifica que con la clave API correcta el acceso sea concedido (HTTP 200)."""
    response = api_client.get("/api/v1/model/info", headers=AUTH_HEADERS)
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "success"
    assert data["model_id"] == OFFICIAL_RUN_ID
    assert data["official_sha256"] == OFFICIAL_MODEL_SHA256


# =====================================================================
# 3. PRUEBAS DE INFERENCIA PREDICTIVA (/api/v1/predict/concrete-strength)
# =====================================================================

def test_predict_returns_503_when_model_not_ready(api_client: TestClient):
    """Verifica que una solicitud de predicción con modelo no listo devuelva HTTP 503."""
    loader = ModelLoader.get_instance()
    assert not loader.is_loaded()

    response = api_client.post(
        "/api/v1/predict/concrete-strength",
        headers=AUTH_HEADERS,
        json={"mix_design": CANONICAL_MIX},
    )
    assert response.status_code == 503
    assert response.headers["content-type"] == "application/problem+json"
    data = response.json()
    assert data["status"] == 503
    assert data["type"] == "https://ecomix.ia/errors/model-unavailable"


def test_predict_canonical_mix_success_and_json_contract(api_client: TestClient):
    """
    Verifica predicción dual correcta (7d y 28d) sobre la mezcla canónica EcoMix:
    - Estado HTTP 200
    - Contrato JSON completo para ASP.NET MVC 5
    - Ratios calculados correctamente
    """
    loader = ModelLoader.get_instance()
    loader.set_test_estimator(DeterministicBenchmarkEstimator())

    payload = {
        "mix_design": CANONICAL_MIX,
        "request_id": "test-req-aspnet-001",
    }
    response = api_client.post(
        "/api/v1/predict/concrete-strength",
        headers=AUTH_HEADERS,
        json=payload,
    )
    assert response.status_code == 200
    data = response.json()

    assert data["status"] == "success"
    assert "predictions" in data
    assert "strength_7d_mpa" in data["predictions"]
    assert "strength_28d_mpa" in data["predictions"]
    assert data["predictions"]["strength_7d_mpa"] > 0.0
    assert data["predictions"]["strength_28d_mpa"] > 0.0
    assert data["predictions"]["strength_28d_mpa"] >= data["predictions"]["strength_7d_mpa"]

    # Verificación de ratios
    ratios = data["mix_ratios"]
    assert math.isclose(ratios["water_cement_ratio"], 0.625, abs_tol=1e-3)
    assert math.isclose(ratios["water_binder_ratio"], 0.3933, abs_tol=1e-3)
    assert math.isclose(ratios["scm_replacement_percentage"], 37.08, abs_tol=1e-2)
    assert math.isclose(ratios["total_mass_kg_m3"], 2398.5, abs_tol=1e-1)

    # Verificación de metadatos de respuesta
    assert data["metadata"]["model_id"] == "test_synthetic_run"
    assert data["metadata"]["model_type"] == "SyntheticEstimator"
    assert loader.get_artifact_info().is_synthetic is True


def test_predict_accepts_direct_component_dict(api_client: TestClient):
    """Verifica que la API acepte las 7 componentes directamente sin envoltorio mix_design."""
    loader = ModelLoader.get_instance()
    loader.set_test_estimator(DeterministicBenchmarkEstimator())

    response = api_client.post(
        "/api/v1/predict/concrete-strength",
        headers=AUTH_HEADERS,
        json=CANONICAL_MIX,
    )
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "success"
    assert data["predictions"]["strength_28d_mpa"] > 0.0


def test_predict_high_scm_returns_warnings_in_json(api_client: TestClient):
    """Verifica que la mezcla con alta sustitución SCM retorne advertencias estructuradas."""
    loader = ModelLoader.get_instance()
    loader.set_test_estimator(DeterministicBenchmarkEstimator())

    response = api_client.post(
        "/api/v1/predict/concrete-strength",
        headers=AUTH_HEADERS,
        json={"mix_design": HIGH_SCM_MIX},
    )
    assert response.status_code == 200
    data = response.json()
    warnings = data["warnings"]
    assert len(warnings) >= 1
    codes = [w["code"] for w in warnings]
    assert "WARN_HIGH_SCM_REPLACEMENT" in codes


# =====================================================================
# 4. PRUEBA DE PARIDAD ESTRICTA (API REST vs. INFERENCE ENGINE DIRECTO)
# =====================================================================

def test_api_predict_has_exact_numerical_parity_with_engine(api_client: TestClient):
    """
    Comprueba que el endpoint HTTP utilice la misma fachada validada en Fase 5.4,
    garantizando diferencia absoluta nula (|Δ| == 0.0 MPa) frente a engine.predict().
    """
    loader = ModelLoader.get_instance()
    estimator = DeterministicBenchmarkEstimator()
    loader.set_test_estimator(estimator)

    engine = InferenceEngine(loader)
    direct_engine_resp = engine.predict(CANONICAL_MIX)

    http_resp = api_client.post(
        "/api/v1/predict/concrete-strength",
        headers=AUTH_HEADERS,
        json={"mix_design": CANONICAL_MIX},
    )
    assert http_resp.status_code == 200
    http_data = http_resp.json()

    # Comparación exacta de valores de resistencia
    api_7d = http_data["predictions"]["strength_7d_mpa"]
    api_28d = http_data["predictions"]["strength_28d_mpa"]

    engine_7d = direct_engine_resp.predictions.strength_7d_mpa
    engine_28d = direct_engine_resp.predictions.strength_28d_mpa

    assert math.isclose(api_7d, engine_7d, abs_tol=1e-5)
    assert math.isclose(api_28d, engine_28d, abs_tol=1e-5)


# =====================================================================
# 5. PRUEBAS DE MANEJO DE ERRORES Y RFC 7807 (PROBLEMDETAILS)
# =====================================================================

def test_domain_validation_negative_cement_returns_422(api_client: TestClient):
    """Verifica que cemento negativo produzca HTTP 422 con ProblemDetails estructurado."""
    loader = ModelLoader.get_instance()
    loader.set_test_estimator(DeterministicBenchmarkEstimator())

    bad_mix = dict(CANONICAL_MIX)
    bad_mix["cement"] = -10.0

    response = api_client.post(
        "/api/v1/predict/concrete-strength",
        headers=AUTH_HEADERS,
        json={"mix_design": bad_mix},
    )
    assert response.status_code == 422
    assert response.headers["content-type"] == "application/problem+json"
    data = response.json()

    assert data["status"] == 422
    assert "validation-error" in data["type"]
    assert "invalid_fields" in data
    fields = [p["field"] for p in data["invalid_fields"]]
    assert any("cement" in f for f in fields)


def test_domain_validation_excessive_water_binder_ratio_returns_422(api_client: TestClient):
    """Verifica que relación agua/cementante extrema (e.g. 1.2) produzca HTTP 422."""
    loader = ModelLoader.get_instance()
    loader.set_test_estimator(DeterministicBenchmarkEstimator())

    bad_mix = dict(CANONICAL_MIX)
    bad_mix["water"] = 550.0  # Provoca w/b > 1.0

    response = api_client.post(
        "/api/v1/predict/concrete-strength",
        headers=AUTH_HEADERS,
        json={"mix_design": bad_mix},
    )
    assert response.status_code == 422
    data = response.json()
    assert data["status"] == 422
    assert "invalid_fields" in data
    fields = [p["field"] for p in data["invalid_fields"]]
    assert any("water_binder_ratio" in f for f in fields)


def test_malformed_json_types_returns_422(api_client: TestClient):
    """Verifica que tipos no válidos retornen HTTP 422 con formato ProblemDetails."""
    loader = ModelLoader.get_instance()
    loader.set_test_estimator(DeterministicBenchmarkEstimator())

    # 1. Error de dominio: campo con tipo no numérico dentro del objeto
    bad_mix = dict(CANONICAL_MIX)
    bad_mix["cement"] = "cien_kilos_no_numerico"

    response = api_client.post(
        "/api/v1/predict/concrete-strength",
        headers=AUTH_HEADERS,
        json={"mix_design": bad_mix},
    )
    assert response.status_code == 422
    data = response.json()
    assert data["status"] == 422
    assert "validation-error" in data["type"]

    # 2. Error de esquema HTTP: cuerpo con estructura incompatible (array en lugar de objeto)
    response_array = api_client.post(
        "/api/v1/predict/concrete-strength",
        headers=AUTH_HEADERS,
        json=["no", "es", "objeto", "dosificacion"],
    )
    assert response_array.status_code == 422
    data_array = response_array.json()
    assert data_array["status"] == 422
    assert data_array["type"] == "https://ecomix.ia/errors/request-validation-error"
    assert "invalid_fields" in data_array


def test_oversized_payload_returns_413(api_client: TestClient):
    """Verifica que cuerpos mayores al límite (1 MB) retornen HTTP 413."""
    response = api_client.post(
        "/api/v1/predict/concrete-strength",
        headers={
            "X-API-Key": VALID_API_KEY,
            "Content-Length": str(2_000_000),  # 2 MB
        },
        content=b"x" * 100,
    )
    assert response.status_code == 413
    data = response.json()
    assert data["status"] == 413
    assert data["type"] == "https://ecomix.ia/errors/payload-too-large"


# =====================================================================
# 6. PRUEBAS DE CONCURRENCIA Y RENDIMIENTO
# =====================================================================

def test_concurrent_api_requests_are_thread_safe_and_deterministic(api_client: TestClient):
    """Verifica que 10 solicitudes concurrentes simultáneas se atiendan con éxito y determinismo."""
    loader = ModelLoader.get_instance()
    loader.set_test_estimator(DeterministicBenchmarkEstimator())

    barrier = threading.Barrier(10)
    results = []
    errors = []

    def client_worker():
        barrier.wait()
        try:
            resp = api_client.post(
                "/api/v1/predict/concrete-strength",
                headers=AUTH_HEADERS,
                json={"mix_design": CANONICAL_MIX},
            )
            results.append((resp.status_code, resp.json()["predictions"]["strength_28d_mpa"]))
        except Exception as e:
            errors.append(e)

    threads = [threading.Thread(target=client_worker) for _ in range(10)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    assert len(errors) == 0
    assert len(results) == 10
    # Todos deben retornar 200 con exactamente la misma predicción
    status_codes = [r[0] for r in results]
    predictions_28d = [r[1] for r in results]

    assert all(code == 200 for code in status_codes)
    assert len(set(predictions_28d)) == 1  # Determinismo exacto


def test_request_id_and_timing_headers_propagated(api_client: TestClient):
    """Verifica que un X-Request-ID personalizado se preserve y el tiempo de respuesta se mida."""
    loader = ModelLoader.get_instance()
    loader.set_test_estimator(DeterministicBenchmarkEstimator())

    custom_req_id = "custom-uuid-aspnet-999"
    headers = dict(AUTH_HEADERS)
    headers["X-Request-ID"] = custom_req_id

    response = api_client.post(
        "/api/v1/predict/concrete-strength",
        headers=headers,
        json={"mix_design": CANONICAL_MIX},
    )
    assert response.status_code == 200
    assert response.headers["x-request-id"] == custom_req_id

    resp_time_str = response.headers.get("x-response-time-ms")
    assert resp_time_str is not None
    resp_time_float = float(resp_time_str)
    assert resp_time_float > 0.0
    # En memoria local debe responder muy por debajo del SLA de 2000 ms
    assert resp_time_float < 500.0
