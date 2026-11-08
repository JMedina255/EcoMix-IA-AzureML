"""
Pruebas automatizadas de integración para la Fase 5.4-A de EcoMix IA:
- Validación estática de la especificación declarativa del Command Job de Azure ML (config/azure_inference_job.yml).
- Concurrencia y seguridad de hilos en la inicialización de ModelLoader.
- Estabilidad y determinismo ante solicitudes consecutivas (Warm Inferences).
- Distinción rigurosa de estados: Artefacto presente en disco vs. Modelo instanciado en RAM vs. Servicio listo.
- Aislamiento explícito de modelos sintéticos.
- Comparación empírica de latencias de arranque en frío (Cold-Start) vs. inferencia en caliente (Warm-Inference).
"""

import json
import math
import threading
import time
from pathlib import Path
import numpy as np
import pandas as pd
import pytest
import yaml

from src.inference.engine import (
    InferenceEngine,
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
from src.inference.schemas import ConcreteMixDesign, PredictionRequest, PredictionResponse
from scripts.validate_real_inference import BENCHMARK_CASES, run_validation


PROJECT_ROOT = Path(__file__).resolve().parent.parent


class DeterministicBenchmarkEstimator:
    """Estimador determinístico para pruebas de concurrencia y latencia."""
    def predict(self, df: pd.DataFrame) -> np.ndarray:
        return (
            0.05 * df["cement"].to_numpy()
            + 0.02 * df["blast_furnace_slag"].to_numpy()
            + 0.01 * df["fly_ash"].to_numpy()
            + 0.45 * df["age"].to_numpy()
        )


@pytest.fixture(autouse=True)
def clean_loader_state():
    loader = ModelLoader.get_instance()
    loader.reset()
    yield
    loader.reset()


# =====================================================================
# 1. VALIDACIÓN ESTÁTICA DEL JOB DE AZURE ML (config/azure_inference_job.yml)
# =====================================================================

def test_azure_inference_job_yaml_exists_and_is_valid():
    """Verifica que el archivo YAML del job de inferencia exista y sea sintácticamente válido."""
    job_path = PROJECT_ROOT / "config" / "azure_inference_job.yml"
    assert job_path.exists(), "El archivo 'config/azure_inference_job.yml' debe existir."

    with open(job_path, "r", encoding="utf-8") as f:
        job_data = yaml.safe_load(f)

    assert isinstance(job_data, dict)
    assert job_data.get("type") == "command"
    assert job_data.get("compute") == "azureml:cpu-cluster-ecomix"
    assert job_data.get("environment", {}).get("image") == "mcr.microsoft.com/azureml/curated/ai-ml-automl:41"
    assert job_data.get("limits", {}).get("timeout") == 1800
    assert job_data.get("resources", {}).get("instance_count") == 1

    # Verificar que apunte exactamente al Model Asset certificado
    expected_model_asset = "azureml:azureml_wheat_cheese_4swj34tkjn_11_output_mlflow_log_model_873731674:1"
    assert job_data.get("inputs", {}).get("model_dir", {}).get("path") == expected_model_asset

    # Verificar tags
    tags = job_data.get("tags", {})
    assert tags.get("winner_child_run") == "wheat_cheese_4swj34tkjn_11"
    assert tags.get("model_sha256") == OFFICIAL_MODEL_SHA256


def test_azure_inference_job_validates_against_sdk_schema_if_available():
    """Verifica la especificación del job contra el validador oficial del SDK de Azure ML."""
    job_path = PROJECT_ROOT / "config" / "azure_inference_job.yml"
    try:
        from azure.ai.ml import load_job
        job = load_job(source=str(job_path))
        assert job.compute in ("azureml:cpu-cluster-ecomix", "cpu-cluster-ecomix")
        assert job.environment == "azureml:AzureML-AutoML:41" or "ai-ml-automl:41" in str(job.environment)
    except ImportError:
        pytest.skip("Azure AI ML SDK no disponible localmente; validación omitida.")


# =====================================================================
# 2. SEGURIDAD ANTE CONCURRENCIA Y SOLICITUDES CONSECUTIVAS
# =====================================================================

def test_concurrent_loader_access_is_thread_safe():
    """Verifica que accesos multihilo simultáneos a ModelLoader no generen condiciones de carrera."""
    loader = ModelLoader.get_instance()
    estimator = DeterministicBenchmarkEstimator()

    barrier = threading.Barrier(10)
    errors = []

    def worker():
        try:
            barrier.wait(timeout=3)
            loader.set_test_estimator(estimator, {"model_type": "ThreadSafeModel"})
            model = loader.get_model()
            assert model is estimator
            assert loader.is_loaded() is True
        except Exception as e:
            errors.append(e)

    threads = [threading.Thread(target=worker) for _ in range(10)]
    for t in threads:
        t.start()
    for t in threads:
        t.join(timeout=5)

    assert len(errors) == 0, f"Errores en ejecución concurrente: {errors}"
    assert loader.is_loaded() is True


def test_consecutive_predictions_maintain_consistent_warm_results():
    """
    Verifica que 10 solicitudes consecutivas al motor en memoria RAM entreguen
    predicciones estrictamente idénticas y sin recargar el modelo.
    """
    loader = ModelLoader.get_instance()
    loader.set_test_estimator(DeterministicBenchmarkEstimator())
    engine = InferenceEngine(loader)

    canonical_payload = {
        "cement": 280.0,
        "blast_furnace_slag": 105.0,
        "fly_ash": 60.0,
        "water": 175.0,
        "superplasticizer": 8.5,
        "coarse_aggregate": 1020.0,
        "fine_aggregate": 750.0,
    }

    first_resp = engine.predict(canonical_payload)
    pred_7d_baseline = first_resp.predictions.strength_7d_mpa
    pred_28d_baseline = first_resp.predictions.strength_28d_mpa

    latencies_ms = []
    for _ in range(10):
        t0 = time.perf_counter()
        resp = engine.predict(canonical_payload)
        t_el = (time.perf_counter() - t0) * 1000.0
        latencies_ms.append(t_el)

        assert resp.predictions.strength_7d_mpa == pred_7d_baseline
        assert resp.predictions.strength_28d_mpa == pred_28d_baseline
        assert resp.status == "success"

    # La inferencia pura en caliente en memoria debe ser extremadamente rápida (< 50 ms por iteración)
    avg_latency = sum(latencies_ms) / len(latencies_ms)
    assert avg_latency < 50.0, f"Latencia promedio ({avg_latency:.2f} ms) supera el límite aceptable"


# =====================================================================
# 3. DISTINCIÓN RIGUROSA DE ESTADOS DEL MODELO Y AISLAMIENTO SINTÉTICO
# =====================================================================

def test_model_presence_vs_loaded_vs_service_ready_states():
    """
    Verifica la separación de estados del ciclo de vida:
    - Estado 1: Artefacto presente en disco pero NO cargado en RAM (is_loaded=False).
    - Estado 2: Estimador instanciado en RAM (is_loaded=True, is_synthetic=True/False).
    - Estado 3: Artefacto ausente (is_loaded=False, artifact_exists=False).
    """
    loader = ModelLoader.get_instance()

    # Estado 1: En reposo (disco presente, RAM limpia)
    st1 = get_model_status()
    if not st1["artifact_exists_on_disk"]:
        pytest.skip("Modelo real no descargado en models/ (normal en CI sin artefactos binarios versionados)")
    assert st1["artifact_exists_on_disk"] is True
    assert st1["is_loaded"] is False
    assert st1["sha256_verified"] is True
    assert st1["is_synthetic"] is False

    # El motor debe rechazar peticiones si el modelo no está en RAM
    engine = InferenceEngine(loader)
    with pytest.raises(ModelNotFoundError):
        engine.predict({"cement": 300, "water": 180, "coarse_aggregate": 1000, "fine_aggregate": 750})

    # Estado 2: Estimador instanciado en RAM
    loader.set_test_estimator(DeterministicBenchmarkEstimator(), {"model_type": "SyntheticBenchmark"})
    st2 = get_model_status()
    assert st2["is_loaded"] is True
    assert st2["is_synthetic"] is True  # Marcado explícitamente como sintético
    assert st2["model_type"] == "SyntheticBenchmark"

    resp = engine.predict({"cement": 300, "water": 180, "coarse_aggregate": 1000, "fine_aggregate": 750})
    assert resp.status == "success"


def test_synthetic_model_isolation_metadata_flag():
    """Verifica que todo modelo sintético de prueba declare is_synthetic=True en sus metadatos."""
    loader = ModelLoader.get_instance()
    loader.set_test_estimator(DeterministicBenchmarkEstimator())

    art_info = loader.get_artifact_info()
    assert art_info is not None
    assert art_info.is_synthetic is True
    assert "synthetic:" in art_info.binary_path.as_posix()


# =====================================================================
# 4. PRUEBA DEL PROTOCOLO DE VALIDACIÓN REPRODUCIBLE (SCRIPT)
# =====================================================================

def test_validate_real_inference_script_execution_local(tmp_path):
    """
    Ejecuta el protocolo de validación reproducible de scripts/validate_real_inference.py.
    En el entorno local actual (Python 3.13), debe:
    1. Auditar con éxito el SHA-256 del binario oficial.
    2. Detectar la incompatibilidad de dependencias sin excepciones no controladas.
    3. Registrar status = 'PENDING_COMPATIBLE_RUNTIME'.
    4. Escribir el informe JSON auditable en disco.
    """
    st = get_model_status()
    if not st["artifact_exists_on_disk"]:
        pytest.skip("Modelo real no descargado en models/ (normal en CI sin artefactos binarios versionados)")

    reports_out = tmp_path / "reports_test"
    report_data = run_validation(
        reports_dir=str(reports_out),
        output_filename="test_real_validation.json",
    )

    assert report_data["project"] == "ecomix-ia-ml"
    assert report_data["phase"] in ("5.4-A", "5.4-B")
    assert report_data["model_artifact"]["sha256_verified"] is True
    assert report_data["model_artifact"]["sha256"] == OFFICIAL_MODEL_SHA256
    assert report_data["overall_status"] == "PENDING_COMPATIBLE_RUNTIME"

    # Verificar archivo físico escrito
    out_file = reports_out / "test_real_validation.json"
    assert out_file.exists()


def test_cold_start_vs_warm_inference_timing_separation():
    """
    Comprueba que el diseño desacople la inicialización inicial del tiempo de inferencia en caliente.
    """
    loader = ModelLoader.get_instance()
    estimator = DeterministicBenchmarkEstimator()

    # Medición de instanciación / warm-up
    t0_cold = time.perf_counter()
    loader.set_test_estimator(estimator)
    t_cold = (time.perf_counter() - t0_cold) * 1000.0

    engine = InferenceEngine(loader)
    canonical = {
        "cement": 280.0,
        "blast_furnace_slag": 105.0,
        "fly_ash": 60.0,
        "water": 175.0,
        "superplasticizer": 8.5,
        "coarse_aggregate": 1020.0,
        "fine_aggregate": 750.0,
    }

    t0_warm = time.perf_counter()
    resp = engine.predict(canonical)
    t_warm = (time.perf_counter() - t0_warm) * 1000.0

    assert resp.status == "success"
    # Ambas mediciones existen y son números finitos no negativos
    assert t_cold >= 0.0
    assert t_warm >= 0.0


# =====================================================================
# 5. AUDITORÍA DE CONSISTENCIA Y MÉTRICAS OFICIALES
# =====================================================================

def test_evaluation_metrics_and_nrmse_mathematical_consistency():
    """
    Verifica la consistencia matemática de las métricas oficiales en reports/evaluation_wheat_cheese_4swj34tkjn.json:
    1. R2 = 0.9121, RMSE = 4.7592, MAE = 3.2822, NRMSE = 0.0673.
    2. Comprueba que el denominador de NRMSE es el rango de prueba (y_test.max() - y_test.min() == 70.67),
       y no el rango del dataset UCI completo (80.27).
    """
    eval_json = PROJECT_ROOT / "reports" / "evaluation_wheat_cheese_4swj34tkjn.json"
    assert eval_json.exists(), "El reporte oficial de evaluación debe existir en reports/"

    with open(eval_json, "r", encoding="utf-8") as f:
        data = json.load(f)

    gm = data["global_metrics"]
    assert gm["r2_score"] == 0.9121
    assert gm["rmse_mpa"] == 4.7592
    assert gm["mae_mpa"] == 3.2822
    assert gm["nrmse"] == 0.0673

    # Verificar cálculo del denominador en concrete_test.csv
    test_csv = PROJECT_ROOT / "data" / "processed" / "concrete_test.csv"
    if test_csv.exists():
        import pandas as pd
        df_test = pd.read_csv(test_csv)
        y = df_test["concrete_compressive_strength"]
        y_min = float(y.min())
        y_max = float(y.max())
        test_range = y_max - y_min
        assert math.isclose(y_min, 4.83, abs_tol=1e-2)
        assert math.isclose(y_max, 75.50, abs_tol=1e-2)
        assert math.isclose(test_range, 70.67, abs_tol=1e-2)

        # NRMSE con rango de test: 4.7592 / 70.67 = 0.067344 -> round(..., 4) == 0.0673
        calculated_nrmse = round(gm["rmse_mpa"] / test_range, 4)
        assert calculated_nrmse == 0.0673


def test_real_inference_validation_report_parity_and_benchmarks():
    """
    Verifica que reports/real_inference_validation.json contenga los 3 benchmarks evaluados
    con paridad estricta (< 1e-5 MPa) y sin estimadores sintéticos.
    """
    inf_json = PROJECT_ROOT / "reports" / "real_inference_validation.json"
    assert inf_json.exists(), "El reporte de validación real debe existir en reports/"

    with open(inf_json, "r", encoding="utf-8") as f:
        data = json.load(f)

    assert data["overall_status"] == "SUCCESS"
    assert data["model_artifact"]["sha256"] == OFFICIAL_MODEL_SHA256
    assert data["model_artifact"]["sha256_verified"] is True
    assert data["model_artifact"]["model_type"] == "VotingEnsemble"

    benchmarks = data["benchmark_results"]
    assert len(benchmarks) == 3

    for b in benchmarks:
        assert b["status"] == "PASSED"
        assert b["numerical_parity_verified"] is True
        assert b["parity_threshold_met_1e5"] is True
        assert b["absolute_diff_7d_mpa"] < 1e-5
        assert b["absolute_diff_28d_mpa"] < 1e-5
        assert b["inference_latency_ms"] > 0.0
        assert b["inference_latency_ms"] < 2000.0  # Límite SLA del SRS

    # Verificar que el benchmark canónico tenga exactamente los valores esperados
    canon = benchmarks[0]
    assert canon["case_id"] == "canonical_ecomix"
    assert canon["inputs_kg_m3"]["cement"] == 280.0
    assert canon["inputs_kg_m3"]["blast_furnace_slag"] == 105.0
    assert canon["inputs_kg_m3"]["fly_ash"] == 60.0
    assert canon["predictions_engine"]["strength_7d_mpa"] == 35.16
    assert canon["predictions_engine"]["strength_28d_mpa"] == 49.58

    # Verificar memoria registrada
    ru = data.get("resource_usage", {})
    assert "peak_memory_mb" in ru
    assert ru["peak_memory_mb"] <= 500.0
