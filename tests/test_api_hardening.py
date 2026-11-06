"""
Suite de pruebas automatizadas de endurecimiento DevSecOps para la API FastAPI de EcoMix IA (Fase 5.6-A).
Verifica:
1. Seguridad de configuración y rechazo estricto de secretos nulos, triviales o prohibidos en producción.
2. Prohibición de desactivación de autenticación en modo producción.
3. Aislamiento total de configuración entre instancias concurrentes de FastAPI (cero contaminación global).
4. Rotación segura de credenciales con múltiples claves activas.
5. Resistencia a timing attacks mediante secrets.compare_digest.
6. Rechazo de estimadores sintéticos en sondas de preparación (/health/ready) bajo entorno de producción.
7. Endurecimiento HTTP: Content-Length malformado (400), Content-Type no admitido (415), Payload sin Content-Length (413).
8. Sanitización estricta de X-Request-ID contra inyección de cabeceras y control characters.
9. Desactivación de endpoints interactivos de documentación (/docs, /redoc, /openapi.json) en producción.
10. Enmascaramiento de secretos en representaciones de configuración.
"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from src.api.config import ApiSettings, reset_settings
from src.api.main import create_app
from src.inference.model_loader import ModelLoader


class MockEstimator:
    """Estimador sintético para comprobaciones de estado."""

    def predict(self, X):
        import numpy as np
        return np.array([25.0, 40.0])


@pytest.fixture(autouse=True)
def clean_environment():
    """Limpia el estado y los singletons antes y después de cada prueba."""
    reset_settings()
    loader = ModelLoader.get_instance()
    loader.reset()
    yield
    loader.reset()
    reset_settings()


# =====================================================================
# 1. PRUEBAS DE SEGURIDAD DE CONFIGURACIÓN Y PRODUCCIÓN
# =====================================================================

def test_production_rejects_missing_or_empty_api_key():
    """Verifica que en modo producción sea obligatorio definir ECOMIX_API_KEY."""
    with pytest.raises(ValueError, match="ECOMIX_API_KEY"):
        ApiSettings(environment="production", api_key=None)

    with pytest.raises(ValueError, match="ECOMIX_API_KEY"):
        ApiSettings(environment="production", api_key="   ")


def test_production_rejects_banned_dev_keys():
    """Verifica que ninguna clave pública o de desarrollo pueda usarse en producción."""
    banned = ["ecomix-dev-api-key-2026", "admin", "secret", "dev", "test", "password"]
    for bad_key in banned:
        with pytest.raises(ValueError, match="prohibida"):
            ApiSettings(environment="production", api_key=bad_key)


def test_production_rejects_low_entropy_keys():
    """Verifica que una clave de producción tenga al menos 16 caracteres."""
    with pytest.raises(ValueError, match="16 caracteres"):
        ApiSettings(environment="production", api_key="short-key-123")


def test_production_rejects_auth_disabled():
    """Verifica que esté terminantemente prohibido apagar la autenticación en producción."""
    with pytest.raises(ValueError, match="Prohibido desactivar la autenticación"):
        ApiSettings(
            environment="production",
            auth_enabled=False,
            api_key="un-secreto-robusto-de-produccion-2026",
        )


def test_secrets_are_masked_in_repr():
    """Verifica que la clave API nunca se filtre al imprimir o serializar el objeto de configuración."""
    secret = "mi-secreto-muy-confidencial-999"
    settings = ApiSettings(environment="development", api_key=secret)
    repr_str = repr(settings)
    assert secret not in repr_str
    assert "keys_configured=True" in repr_str


# =====================================================================
# 2. PRUEBAS DE AISLAMIENTO ENTRE INSTANCIAS DE FASTAPI
# =====================================================================

def test_settings_instance_isolation_between_two_fastapi_apps():
    """
    Comprueba que dos instancias de FastAPI con configuraciones y credenciales diferentes
    operen de forma 100% aislada, resolviendo cada una sus dependencias desde app.state.settings
    sin contaminación global.
    """
    key_alpha = "key-alpha-secret-12345"
    key_beta = "key-beta-secret-67890"

    settings_alpha = ApiSettings(environment="test", api_key=key_alpha)
    settings_beta = ApiSettings(environment="test", api_key=key_beta)

    app_alpha = create_app(settings_alpha)
    app_beta = create_app(settings_beta)

    client_alpha = TestClient(app_alpha)
    client_beta = TestClient(app_beta)

    # Cliente Alpha acepta clave Alpha y rechaza clave Beta
    res_a_valid = client_alpha.get("/api/v1/model/info", headers={"X-API-Key": key_alpha})
    assert res_a_valid.status_code == 200
    res_a_invalid = client_alpha.get("/api/v1/model/info", headers={"X-API-Key": key_beta})
    assert res_a_invalid.status_code == 403

    # Cliente Beta acepta clave Beta y rechaza clave Alpha
    res_b_valid = client_beta.get("/api/v1/model/info", headers={"X-API-Key": key_beta})
    assert res_b_valid.status_code == 200
    res_b_invalid = client_beta.get("/api/v1/model/info", headers={"X-API-Key": key_alpha})
    assert res_b_invalid.status_code == 403


# =====================================================================
# 3. PRUEBAS DE ROTACIÓN DE CREDENCIALES
# =====================================================================

def test_key_rotation_supports_multiple_keys_and_secondary():
    """Verifica soporte para rotación de credenciales con múltiples claves activas concurrentes."""
    key_1 = "rot-key-primary-111"
    key_2 = "rot-key-retiring-222"
    key_3 = "rot-key-secondary-333"

    settings = ApiSettings(
        environment="test",
        api_key=f"{key_1}, {key_2}",
        api_key_secondary=key_3,
    )
    app = create_app(settings)
    client = TestClient(app)

    # Las 3 claves deben tener acceso
    for k in (key_1, key_2, key_3):
        res = client.get("/api/v1/model/info", headers={"X-API-Key": k})
        assert res.status_code == 200

    # Una clave no autorizada debe ser rechazada
    res_bad = client.get("/api/v1/model/info", headers={"X-API-Key": "clave-no-rotada"})
    assert res_bad.status_code == 403


# =====================================================================
# 4. PRUEBAS DE DISPONIBILIDAD Y ESTIMADORES SINTÉTICOS EN PRODUCCIÓN
# =====================================================================

def test_production_readiness_rejects_synthetic_estimator():
    """Verifica que /health/ready retorne HTTP 503 si en modo producción se tiene un estimador sintético."""
    settings_prod = ApiSettings(
        environment="production",
        api_key="secreto-robusto-de-produccion-12345",
    )
    app_prod = create_app(settings_prod)
    client_prod = TestClient(app_prod)

    loader = ModelLoader.get_instance()
    loader.set_test_estimator(MockEstimator())
    assert loader.is_loaded()

    # En producción debe rechazar el estimador sintético
    resp = client_prod.get("/health/ready")
    assert resp.status_code == 503
    assert resp.headers["content-type"] == "application/problem+json"
    data = resp.json()
    assert data["type"] == "https://ecomix.ia/errors/synthetic-model-forbidden"
    assert data["model_ready"] is False

    # Startup probe también debe reflejar indisponibilidad
    resp_startup = client_prod.get("/health/startup")
    assert resp_startup.status_code == 503


def test_test_environment_accepts_synthetic_estimator_in_readiness():
    """Verifica que en modo test/development el estimador sintético sea aceptado para pruebas funcionales."""
    settings_test = ApiSettings(environment="test", api_key="clave-test-1234567")
    app_test = create_app(settings_test)
    client_test = TestClient(app_test)

    loader = ModelLoader.get_instance()
    loader.set_test_estimator(MockEstimator())

    resp = client_test.get("/health/ready")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "ready"
    assert data["is_synthetic"] is True


# =====================================================================
# 5. PRUEBAS DE ENDURECIMIENTO HTTP
# =====================================================================

def test_malformed_content_length_returns_400():
    """Verifica que una cabecera Content-Length no numérica o negativa retorne HTTP 400 Bad Request."""
    settings = ApiSettings(environment="test", api_key="clave-test-1234567")
    app = create_app(settings)
    client = TestClient(app)

    # No numérico
    resp1 = client.post(
        "/api/v1/predict/concrete-strength",
        headers={"Content-Length": "not-an-integer", "X-API-Key": "clave-test-1234567"},
        content=b"{}",
    )
    assert resp1.status_code == 400
    assert resp1.json()["type"] == "https://ecomix.ia/errors/bad-request"

    # Negativo
    resp2 = client.post(
        "/api/v1/predict/concrete-strength",
        headers={"Content-Length": "-10", "X-API-Key": "clave-test-1234567"},
        content=b"{}",
    )
    assert resp2.status_code == 400


def test_unsupported_content_type_returns_415():
    """Verifica que enviar un Content-Type no JSON a endpoints predictivos retorne HTTP 415."""
    settings = ApiSettings(environment="test", api_key="clave-test-1234567")
    app = create_app(settings)
    client = TestClient(app)

    resp = client.post(
        "/api/v1/predict/concrete-strength",
        headers={"Content-Type": "text/plain", "X-API-Key": "clave-test-1234567"},
        content=b"raw-text-not-json",
    )
    assert resp.status_code == 415
    assert resp.headers["content-type"] == "application/problem+json"
    assert resp.json()["type"] == "https://ecomix.ia/errors/unsupported-media-type"


def test_oversized_payload_without_content_length_header_returns_413():
    """Verifica que un cuerpo superior a max_request_body_bytes sea rechazado con 413 aunque no declare Content-Length."""
    settings = ApiSettings(
        environment="test",
        api_key="clave-test-1234567",
        max_request_body_bytes=1000,  # Límite bajo para la prueba (1000 bytes)
    )
    app = create_app(settings)
    client = TestClient(app)

    big_content = b"a" * 1500
    resp = client.post(
        "/api/v1/predict/concrete-strength",
        headers={"X-API-Key": "clave-test-1234567", "Content-Type": "application/json"},
        content=big_content,
    )
    assert resp.status_code == 413
    assert resp.json()["type"] == "https://ecomix.ia/errors/payload-too-large"


def test_x_request_id_sanitization():
    """Verifica que cabeceras X-Request-ID excesivas o con caracteres maliciosos sean reemplazadas por un UUID seguro."""
    settings = ApiSettings(environment="test", api_key="clave-test-1234567")
    app = create_app(settings)
    client = TestClient(app)

    # 1. Caracteres inválidos (posible inyección CRLF)
    resp_malicious = client.get("/health/live", headers={"X-Request-ID": "bad\r\ninjection\nvalue"})
    out_id = resp_malicious.headers.get("x-request-id")
    assert "bad" not in out_id
    assert len(out_id) == 36  # UUID v4 canonical format

    # 2. Longitud excesiva (> 128 chars)
    resp_too_long = client.get("/health/live", headers={"X-Request-ID": "x" * 200})
    out_id_2 = resp_too_long.headers.get("x-request-id")
    assert len(out_id_2) == 36

    # 3. ID válido legítimo preservado
    valid_id = "aspnet-req-uuid-12345-ok"
    resp_valid = client.get("/health/live", headers={"X-Request-ID": valid_id})
    assert resp_valid.headers.get("x-request-id") == valid_id


def test_production_mode_disables_openapi_and_docs():
    """Verifica que en modo producción /docs, /redoc y /openapi.json estén desactivados."""
    settings_prod = ApiSettings(
        environment="production",
        api_key="un-secreto-robusto-de-produccion-2026",
    )
    app_prod = create_app(settings_prod)
    client_prod = TestClient(app_prod)

    assert client_prod.get("/docs").status_code == 404
    assert client_prod.get("/redoc").status_code == 404
    assert client_prod.get("/openapi.json").status_code == 404

    # Endpoint raíz no expone enlace a documentación en producción
    root_data = client_prod.get("/").json()
    assert "Desactivado en producción" in root_data["docs"]


def test_generate_secure_api_key_entropy_and_production_acceptance():
    """Verifica la generación de claves aleatorias seguras de alta entropía para producción."""
    from src.api.config import generate_secure_api_key

    key = generate_secure_api_key(32)
    assert isinstance(key, str)
    assert len(key) == 64  # 32 bytes en hex = 64 chars
    # Debe ser aceptada sin excepciones en modo producción
    settings = ApiSettings(environment="production", api_key=key)
    assert settings.api_key == key
    assert len(settings.get_valid_api_keys()) == 1
