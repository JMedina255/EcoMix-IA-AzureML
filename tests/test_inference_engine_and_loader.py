"""
Pruebas automatizadas para el cargador seguro y motor de inferencia de EcoMix IA (Fase 5.3).
Verifica:
- Firma MLflow, orden estricto de las 8 variables y construcción de edades (7 y 28 días).
- Patrón Singleton, verificación SHA-256 previa a deserialización y rechazo de artefactos alterados.
- Detección precisa de incompatibilidad de runtime en el entorno actual (Python 3.13 vs 3.10).
- Inferencia dual de prueba con estimador sintético explícito y diferenciado del modelo certificado.
- Inmutabilidad de la solicitud y respuestas JSON estandarizadas.
"""

import math
import numpy as np
import pandas as pd
import pytest

from src.inference.engine import (
    InferenceEngine,
    FEATURE_COLUMNS,
    DEFAULT_AGES,
    get_engine,
    get_model_status,
    predict_concrete_strength,
)
from src.inference.model_loader import (
    ModelLoader,
    ModelInferenceError,
    ModelNotFoundError,
    ModelIntegrityError,
    IncompatibleRuntimeError,
    OFFICIAL_MODEL_SHA256,
    OFFICIAL_RUN_ID,
    OFFICIAL_ALGORITHM,
)
from src.inference.schemas import (
    ConcreteMixDesign,
    PredictionRequest,
    PredictionResponse,
)
from src.inference.validator import DomainValidationError


@pytest.fixture
def canonical_mix():
    """Dosificación estándar de concreto ecológico en kg/m³."""
    return ConcreteMixDesign(
        cement=280.0,
        blast_furnace_slag=105.0,
        fly_ash=60.0,
        water=175.0,
        superplasticizer=8.5,
        coarse_aggregate=1020.0,
        fine_aggregate=750.0,
    )


@pytest.fixture(autouse=True)
def reset_model_loader():
    """Asegura que el singleton ModelLoader quede en estado limpio antes y después de cada prueba."""
    loader = ModelLoader.get_instance()
    loader.reset()
    yield
    loader.reset()


# =====================================================================
# 1. PRUEBAS DE FIRMA MLFLOW Y CONSTRUCCIÓN DE MATRICES
# =====================================================================

def test_feature_dataframe_construction_matches_mlflow_signature_exact_order(canonical_mix):
    """
    Verifica que el DataFrame de entrada contenga exactamente las 8 variables
    en el orden declarado por la firma oficial de MLflow y para las edades 7 y 28.
    """
    df = InferenceEngine.build_feature_dataframe(canonical_mix, ages=DEFAULT_AGES)

    assert isinstance(df, pd.DataFrame)
    assert len(df) == 2  # Fila 0: 7d, Fila 1: 28d

    # Orden estricto de columnas
    expected_columns = [
        "cement",
        "blast_furnace_slag",
        "fly_ash",
        "water",
        "superplasticizer",
        "coarse_aggregate",
        "fine_aggregate",
        "age",
    ]
    assert list(df.columns) == expected_columns
    assert list(df.columns) == FEATURE_COLUMNS

    # Edades
    assert list(df["age"]) == [7, 28]
    assert df["age"].dtype == np.int64

    # Valores de materiales idénticos en ambas filas
    for col in expected_columns[:7]:
        assert df[col].dtype == np.float64
        assert df[col].iloc[0] == getattr(canonical_mix, col)
        assert df[col].iloc[1] == getattr(canonical_mix, col)


# =====================================================================
# 2. PRUEBAS DEL CARGADOR SEGURO (ModelLoader)
# =====================================================================

def test_model_loader_singleton_identity():
    """Verifica que ModelLoader mantenga una sola instancia en el proceso."""
    l1 = ModelLoader()
    l2 = ModelLoader.get_instance()
    assert l1 is l2


def test_model_loader_sha256_verification_success_on_certified_artifact():
    """Verifica que el artefacto binario certificado coincida con el hash oficial."""
    loader = ModelLoader.get_instance()
    try:
        bin_path, _, _ = loader.resolve_artifact()
    except ModelNotFoundError:
        pytest.skip("Modelo real no descargado en models/ (normal en CI sin artefactos binarios versionados)")

    assert bin_path.exists()

    actual_hash = loader.compute_sha256(bin_path)
    assert actual_hash == OFFICIAL_MODEL_SHA256


def test_model_loader_rejects_altered_model_binary(tmp_path):
    """Verifica que un archivo binario alterado sea rechazado con ModelIntegrityError."""
    corrupted_file = tmp_path / "model.pkl"
    corrupted_file.write_bytes(b"CONTENIDO_BINARIO_CORRUPTO_Y_ALTERADO")

    loader = ModelLoader.get_instance()
    with pytest.raises(ModelIntegrityError) as exc_info:
        loader.verify_integrity(corrupted_file, expected_sha256=OFFICIAL_MODEL_SHA256)

    assert "Fallo de integridad criptográfica" in str(exc_info.value)


def test_model_loader_raises_model_not_found_on_nonexistent_path(tmp_path):
    """Verifica que una ruta inexistente lance ModelNotFoundError."""
    loader = ModelLoader.get_instance()
    nonexistent = tmp_path / "inexistente" / "model.pkl"

    with pytest.raises(ModelNotFoundError) as exc_info:
        loader.resolve_artifact(model_path=nonexistent)

    assert "no existe" in str(exc_info.value)


def test_model_loader_raises_incompatible_runtime_error_on_real_automl():
    """
    Verifica que intentar deserializar el artefacto VotingEnsemble en el entorno actual
    (Python 3.13 sin azureml-training-tabular) lance IncompatibleRuntimeError de forma controlada.
    """
    loader = ModelLoader.get_instance()
    try:
        loader.resolve_artifact()
    except ModelNotFoundError:
        pytest.skip("Modelo real no descargado en models/ (normal en CI sin artefactos binarios versionados)")

    with pytest.raises(IncompatibleRuntimeError) as exc_info:
        loader.load_model()

    err_msg = str(exc_info.value)
    assert "Incompatibilidad de dependencias de runtime" in err_msg
    assert "azureml" in err_msg or "3.10.19" in err_msg


# =====================================================================
# 3. PRUEBAS DEL MOTOR PREDICTIVO CON ESTIMADOR SINTÉTICO EXPLÍCITO
# =====================================================================

class SyntheticEstimatorForTesting:
    """
    Estimador sintético de prueba con fórmula determinística simple:
    resistencia = 0.05 * cement + 0.02 * slag + 0.5 * age
    Utilizado exclusivamente para validar el flujo del motor sin sustitución silenciosa.
    """

    def predict(self, df: pd.DataFrame) -> np.ndarray:
        return (
            0.05 * df["cement"].to_numpy()
            + 0.02 * df["blast_furnace_slag"].to_numpy()
            + 0.5 * df["age"].to_numpy()
        )


def test_engine_raises_model_not_found_when_uninitialized(canonical_mix):
    """Verifica que el motor rechace peticiones si no hay modelo cargado en memoria."""
    engine = InferenceEngine()
    with pytest.raises(ModelNotFoundError) as exc_info:
        engine.predict(canonical_mix)

    assert "no ha sido cargado en memoria" in str(exc_info.value)


def test_engine_predict_with_synthetic_estimator_end_to_end(canonical_mix):
    """
    Verifica el flujo predictivo completo (7d y 28d) usando un estimador sintético de prueba.
    """
    loader = ModelLoader.get_instance()
    loader.set_test_estimator(
        SyntheticEstimatorForTesting(),
        metadata={"run_id": "test_synthetic_run_01", "model_type": "SyntheticModel"},
    )

    engine = InferenceEngine(loader)
    request = PredictionRequest(mix_design=canonical_mix, request_id="REQ-TEST-001")

    response = engine.predict(request)

    assert isinstance(response, PredictionResponse)
    assert response.status == "success"

    # Verificación de predicciones esperadas:
    # 7d: 0.05 * 280 (14.0) + 0.02 * 105 (2.1) + 0.5 * 7 (3.5) = 19.6 MPa
    # 28d: 14.0 + 2.1 + 0.5 * 28 (14.0) = 30.1 MPa
    assert response.predictions.strength_7d_mpa == 19.6
    assert response.predictions.strength_28d_mpa == 30.1

    # Verificación de ratios heredados
    assert response.mix_ratios.total_cementitious_content_kg_m3 == 445.0
    assert response.mix_ratios.water_binder_ratio == 0.3933

    # Metadatos del modelo
    assert response.metadata.model_id == "test_synthetic_run_01"
    assert response.metadata.model_type == "SyntheticModel"


def test_engine_preserves_request_immutability(canonical_mix):
    """Verifica que la ejecución de inferencia no altere el objeto de solicitud."""
    loader = ModelLoader.get_instance()
    loader.set_test_estimator(SyntheticEstimatorForTesting())
    engine = InferenceEngine(loader)

    request = PredictionRequest(mix_design=canonical_mix, request_id="REQ-IMMUTABLE")
    original_dict = request.model_dump()

    _ = engine.predict(request)

    assert request.model_dump() == original_dict


def test_engine_enforces_domain_validations_before_predict():
    """Verifica que dosificaciones inválidas sean rechazadas antes de llamar al estimador."""
    loader = ModelLoader.get_instance()
    loader.set_test_estimator(SyntheticEstimatorForTesting())
    engine = InferenceEngine(loader)

    invalid_mix = {
        "cement": -50.0,  # Negativo
        "blast_furnace_slag": 0.0,
        "fly_ash": 0.0,
        "water": 175.0,
        "superplasticizer": 0.0,
        "coarse_aggregate": 1000.0,
        "fine_aggregate": 750.0,
    }

    with pytest.raises(DomainValidationError):
        engine.predict(invalid_mix)


def test_engine_handles_non_finite_predictions_gracefully(canonical_mix):
    """Verifica que el motor capture valores NaN o infinitos generados por un modelo anómalo."""
    class NanEstimator:
        def predict(self, df):
            return np.array([float("nan"), 35.0])

    loader = ModelLoader.get_instance()
    loader.set_test_estimator(NanEstimator())
    engine = InferenceEngine(loader)

    with pytest.raises(ModelInferenceError) as exc_info:
        engine.predict(canonical_mix)

    assert "no finitos" in str(exc_info.value)


def test_engine_normalizes_multidimensional_prediction_arrays(canonical_mix):
    """Verifica que matrices de salida bidimensionales (2, 1) sean aplanadas a 1D."""
    class TwoDimEstimator:
        def predict(self, df):
            return np.array([[22.456], [35.678]])

    loader = ModelLoader.get_instance()
    loader.set_test_estimator(TwoDimEstimator())
    engine = InferenceEngine(loader)

    resp = engine.predict(canonical_mix)
    assert resp.predictions.strength_7d_mpa == 22.46
    assert resp.predictions.strength_28d_mpa == 35.68


# =====================================================================
# 4. PRUEBAS DE LA FACHADA PÚBLICA (Public Facade)
# =====================================================================

def test_get_model_status_reports_accurate_diagnostics():
    """Verifica que la función get_model_status reporte el estado real del artefacto en disco."""
    status = get_model_status()
    if not status["artifact_exists_on_disk"]:
        pytest.skip("Modelo real no descargado en models/ (normal en CI sin artefactos binarios versionados)")
    assert isinstance(status, dict)
    assert status["is_loaded"] is False
    assert status["artifact_exists_on_disk"] is True
    assert status["official_sha256"] == OFFICIAL_MODEL_SHA256
    assert status["sha256_verified"] is True
    assert status["is_synthetic"] is False
    assert status["run_id"] == OFFICIAL_RUN_ID
    assert status["model_type"] == OFFICIAL_ALGORITHM


def test_predict_concrete_strength_facade_function(canonical_mix):
    """Verifica la invocación a través de la función de fachada predict_concrete_strength."""
    loader = ModelLoader.get_instance()
    loader.set_test_estimator(SyntheticEstimatorForTesting())

    resp = predict_concrete_strength(canonical_mix)
    assert resp.status == "success"
    assert resp.predictions.strength_7d_mpa > 0.0
    assert resp.predictions.strength_28d_mpa > 0.0


# =====================================================================
# 5. PRUEBAS DE EJECUCIÓN CLI (src/inference.py)
# =====================================================================

def test_cli_check_flag_executes_successfully():
    """Verifica que 'python src/inference.py --check' audite el artefacto sin deserializar."""
    st = get_model_status()
    if not st["artifact_exists_on_disk"]:
        pytest.skip("Modelo real no descargado en models/ (normal en CI sin artefactos binarios versionados)")
    import subprocess
    import sys

    res = subprocess.run(
        [sys.executable, "src/inference.py", "--check"],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    assert res.returncode == 0
    assert "[PRESENTE]" in res.stdout
    assert "[VALIDO]" in res.stdout or "[VÁLIDO]" in res.stdout
    assert OFFICIAL_MODEL_SHA256 in res.stdout


def test_cli_status_flag_outputs_valid_json():
    """Verifica que 'python src/inference.py --status' emita JSON auditable."""
    st = get_model_status()
    if not st["artifact_exists_on_disk"]:
        pytest.skip("Modelo real no descargado en models/ (normal en CI sin artefactos binarios versionados)")
    import json
    import subprocess
    import sys

    res = subprocess.run(
        [sys.executable, "src/inference.py", "--status"],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    assert res.returncode == 0
    data = json.loads(res.stdout)
    assert data["artifact_exists_on_disk"] is True
    assert data["official_sha256"] == OFFICIAL_MODEL_SHA256
    assert data["sha256_verified"] is True


def test_cli_predict_with_invalid_domain_returns_code_2():
    """Verifica que dosificaciones inválidas pasadas por CLI retornen código 2 con ProblemDetails."""
    import subprocess
    import sys

    bad_json = '{"mix_design": {"cement": -10.0, "water": 175.0, "coarse_aggregate": 1000.0, "fine_aggregate": 750.0}}'
    res = subprocess.run(
        [sys.executable, "src/inference.py", "--predict", bad_json],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    assert res.returncode == 2
    assert "422" in res.stderr
    assert "non_negative" in res.stderr or "negativo" in res.stderr

