"""
Pruebas automatizadas para inspección segura, normalización de estado,
resolución de outputs y descarga selectiva de modelos AutoML en Azure ML.
Todas las pruebas se ejecutan con clientes simulados (mocks) sin requerir credenciales reales ni conexión de red.
"""

from collections.abc import Mapping
from pathlib import Path
from unittest.mock import MagicMock, patch
import pytest

from src.evaluate_model import (
    JobStatus,
    normalize_job_status,
    normalize_job_outputs,
    inspect_automl_job,
    download_winner_model,
    resolve_winner_model,
    parse_args,
    main,
)


# ==============================================================================
# 1. Pruebas de Normalización de JobStatus
# ==============================================================================

def test_normalize_job_status_canonical_outputs():
    """Comprueba que normalize_job_status produce siempre strings canónicos en minúsculas."""
    assert normalize_job_status(JobStatus.COMPLETED) == "completed"
    assert normalize_job_status("Completed") == "completed"
    assert normalize_job_status("completed") == "completed"
    assert normalize_job_status("COMPLETED") == "completed"

    assert normalize_job_status(JobStatus.FAILED) == "failed"
    assert normalize_job_status("Failed") == "failed"
    assert normalize_job_status("failed") == "failed"

    assert normalize_job_status(JobStatus.RUNNING) == "running"
    assert normalize_job_status("Running") == "running"
    assert normalize_job_status("running") == "running"

    assert normalize_job_status(JobStatus.CANCELED) == "canceled"
    assert normalize_job_status("Canceled") == "canceled"

    # Objetos con prefijos o atributos
    class DummyEnum:
        value = "Completed"
    assert normalize_job_status(DummyEnum()) == "completed"

    assert normalize_job_status(None) == "unknown"


# ==============================================================================
# 2. Pruebas de Normalización de job.outputs
# ==============================================================================

class CustomMapping(Mapping):
    """Implementación de Mapping para simular objetos estructurados del SDK."""
    def __init__(self, data):
        self._data = data

    def __getitem__(self, key):
        return self._data[key]

    def __len__(self):
        return len(self._data)

    def __iter__(self):
        return iter(self._data)


class ObjectWithAsDict:
    """Simula objeto con método público as_dict()."""
    def __init__(self, data):
        self.data = data

    def as_dict(self):
        return self.data


class ObjectWithToDictPrivate:
    """Simula objeto con método _to_dict()."""
    def __init__(self, data):
        self.data = data

    def _to_dict(self):
        return self.data


def test_normalize_job_outputs_various_formats():
    """Comprueba que normalize_job_outputs maneja dict, Mapping, as_dict() y _to_dict()."""
    expected = {"best_model": "mock_output_obj"}

    # Caso 1: Dict estándar
    assert normalize_job_outputs({"best_model": "mock_output_obj"}) == expected

    # Caso 2: Objeto Mapping
    mapping_obj = CustomMapping({"best_model": "mock_output_obj"})
    assert normalize_job_outputs(mapping_obj) == expected

    # Caso 3: Iterable convertible vía dict(...)
    pairs = [("best_model", "mock_output_obj")]
    assert normalize_job_outputs(pairs) == expected

    # Caso 4: Método público as_dict()
    assert normalize_job_outputs(ObjectWithAsDict(expected)) == expected

    # Caso 5: Método _to_dict()
    assert normalize_job_outputs(ObjectWithToDictPrivate(expected)) == expected

    # Caso 6: None / vacío
    assert normalize_job_outputs(None) == {}
    assert normalize_job_outputs({}) == {}


# ==============================================================================
# 3. Casos Reales del Experimento AutoML (Casos A, B, C, D)
# ==============================================================================

def test_caso_a_parent_best_model_without_winner_id_allows_download(tmp_path):
    """
    CASO A:
    status = JobStatus.COMPLETED
    outputs = {'best_model': ...}
    winner_id = None
    Resultado: Descarga permitida del parent/best_model directamente.
    """
    mock_ml_client = MagicMock()
    mock_job = MagicMock()
    mock_job.name = "wheat_cheese_4swj34tkjn"
    mock_job.status = JobStatus.COMPLETED
    mock_job.properties = {
        "primary_metric": "normalized_root_mean_squared_error",
        "metric_value": "0.05859",
        "run_algorithm": "VotingEnsemble"
    }
    # outputs como Mapping estructurado conteniendo 'best_model'
    mock_best_model_output = MagicMock()
    mock_best_model_output.path = "azureml://datastores/workspaceblobstore/paths/best_model"
    mock_job.outputs = CustomMapping({"best_model": mock_best_model_output})
    mock_ml_client.jobs.get.return_value = mock_job

    target_dir = tmp_path / "wheat_cheese_4swj34tkjn"
    target_dir.mkdir(parents=True, exist_ok=True)
    fake_model = target_dir / "best_model" / "model.pkl"
    fake_model.parent.mkdir(parents=True, exist_ok=True)
    fake_model.write_bytes(b"dummy_voting_ensemble_model")

    # Ejecutar descarga
    model_path = download_winner_model(
        mock_ml_client,
        job_name="wheat_cheese_4swj34tkjn",
        download_dir=target_dir
    )

    # Verificar que descargó directamente el output del parent job sin necesidad de winner_id
    mock_ml_client.jobs.download.assert_called_once()
    _, kwargs = mock_ml_client.jobs.download.call_args
    assert kwargs.get("output_name") == "best_model"
    assert kwargs.get("all") is False
    assert model_path.exists()


def test_caso_b_completed_string_recognized_correctly():
    """
    CASO B:
    status = 'Completed'
    best_model presente
    Resultado: 'Completed' reconocido canónicamente como 'completed'.
    """
    mock_ml_client = MagicMock()
    mock_job = MagicMock()
    mock_job.name = "wheat_cheese_4swj34tkjn"
    mock_job.status = "Completed"
    mock_job.properties = {
        "primary_metric": "normalized_root_mean_squared_error",
        "metric_value": "0.05859"
    }
    mock_job.outputs = {"best_model": MagicMock()}
    mock_ml_client.jobs.get.return_value = mock_job

    result = inspect_automl_job(mock_ml_client, "wheat_cheese_4swj34tkjn")

    assert result["status"] == "completed"
    assert result["output_name"] == "best_model"
    assert result["parent_winner_output"] == "best_model"


def test_caso_c_fallback_to_unequivocal_winner_child(tmp_path):
    """
    CASO C:
    best_model ausente en parent
    winner child inequívoco en metadatos
    Resultado: Usar fallback de child run.
    """
    mock_ml_client = MagicMock()
    mock_job = MagicMock()
    mock_job.name = "wheat_cheese_4swj34tkjn"
    mock_job.status = "completed"
    mock_job.properties = {
        "best_child_run_id": "wheat_cheese_4swj34tkjn_11",
        "primary_metric": "normalized_root_mean_squared_error",
    }
    # Sin best_model en el parent
    mock_job.outputs = {}

    # Mock del child run ganador
    mock_child_job = MagicMock()
    mock_child_job.name = "wheat_cheese_4swj34tkjn_11"
    mock_child_job.outputs = {"outputs": MagicMock()}

    def get_job_side_effect(name):
        if name == "wheat_cheese_4swj34tkjn":
            return mock_job
        if name == "wheat_cheese_4swj34tkjn_11":
            return mock_child_job
        raise ValueError(f"Job no encontrado: {name}")

    mock_ml_client.jobs.get.side_effect = get_job_side_effect

    target_dir = tmp_path / "wheat_cheese_4swj34tkjn"
    target_dir.mkdir(parents=True, exist_ok=True)
    fake_model = target_dir / "outputs" / "model.pkl"
    fake_model.parent.mkdir(parents=True, exist_ok=True)
    fake_model.write_bytes(b"dummy_child_model")

    model_path = download_winner_model(
        mock_ml_client,
        job_name="wheat_cheese_4swj34tkjn",
        download_dir=target_dir
    )

    mock_ml_client.jobs.download.assert_called_once()
    args, kwargs = mock_ml_client.jobs.download.call_args
    # Debe descargar desde el child run
    assert kwargs.get("name") == "wheat_cheese_4swj34tkjn_11" or (args and args[0] == "wheat_cheese_4swj34tkjn_11")
    assert kwargs.get("output_name") == "outputs"
    assert kwargs.get("all") is False


def test_caso_d_best_model_absent_and_child_ambiguous_halts_download(tmp_path):
    """
    CASO D:
    best_model ausente en parent
    winner child ambiguo / no determinable
    Resultado: Detener descarga con mensaje explicativo.
    """
    mock_ml_client = MagicMock()
    mock_job = MagicMock()
    mock_job.name = "wheat_cheese_4swj34tkjn"
    mock_job.status = "Completed"
    mock_job.properties = {}  # Sin best_child_run_id
    mock_job.outputs = {}     # Sin best_model

    # Dos child runs sin ganador claro
    child_1 = MagicMock(name="child_1", properties={}, tags={})
    child_2 = MagicMock(name="child_2", properties={}, tags={})
    mock_ml_client.jobs.get.return_value = mock_job
    mock_ml_client.jobs.list.return_value = [child_1, child_2]

    with pytest.raises(ValueError) as exc_info:
        download_winner_model(
            mock_ml_client,
            job_name="wheat_cheese_4swj34tkjn",
            download_dir=tmp_path
        )

    error_msg = str(exc_info.value).lower()
    assert "no es posible descargar el modelo" in error_msg
    mock_ml_client.jobs.download.assert_not_called()


# ==============================================================================
# 4. Pruebas de CLI y Trazabilidad General
# ==============================================================================

def test_cli_default_mode_is_inspect():
    """Comprueba que el modo predeterminado de la CLI es --inspect, no --download."""
    args = parse_args([])
    assert args.job_name == "wheat_cheese_4swj34tkjn"
    assert args.download is False
    assert args.evaluate is False
    assert args.model_path is None


def test_inspect_does_not_download_files():
    """Comprueba que la inspección no invoca ningún método de descarga."""
    mock_ml_client = MagicMock()
    mock_job = MagicMock()
    mock_job.name = "wheat_cheese_4swj34tkjn"
    mock_job.status = "Completed"
    mock_job.properties = {
        "best_child_run_id": "wheat_cheese_4swj34tkjn_11",
        "primary_metric": "normalized_root_mean_squared_error",
        "metric_value": "0.05859",
        "run_algorithm": "VotingEnsemble"
    }
    mock_job.outputs = {"best_model": MagicMock()}
    mock_ml_client.jobs.get.return_value = mock_job

    result = inspect_automl_job(mock_ml_client, "wheat_cheese_4swj34tkjn")

    assert result["status"] == "completed"
    assert result["primary_metric"] == "normalized_root_mean_squared_error"
    assert result["winner_algorithm"] == "VotingEnsemble"
    mock_ml_client.jobs.download.assert_not_called()


def test_inexistent_job_raises_controlled_error():
    """Comprueba que un trabajo no existente en Azure genera un error controlado."""
    mock_ml_client = MagicMock()
    mock_ml_client.jobs.get.side_effect = Exception("Job not found in workspace")

    with pytest.raises(RuntimeError) as exc_info:
        inspect_automl_job(mock_ml_client, "trabajo_fantasma_123")

    error_msg = str(exc_info.value).lower()
    assert "no se pudo consultar el trabajo 'trabajo_fantasma_123'" in error_msg
    mock_ml_client.jobs.download.assert_not_called()


def test_incomplete_job_prevents_download(tmp_path):
    """Comprueba que un trabajo que aún no finaliza (Running, Failed) impide la descarga."""
    mock_ml_client = MagicMock()
    mock_job = MagicMock()
    mock_job.name = "wheat_cheese_4swj34tkjn"
    mock_job.status = JobStatus.RUNNING
    mock_job.properties = {}
    mock_job.outputs = {"best_model": MagicMock()}
    mock_ml_client.jobs.get.return_value = mock_job

    with pytest.raises(ValueError) as exc_info:
        download_winner_model(mock_ml_client, "wheat_cheese_4swj34tkjn", download_dir=tmp_path)

    assert "no ha finalizado exitosamente" in str(exc_info.value).lower()
    assert "running" in str(exc_info.value).lower()
    mock_ml_client.jobs.download.assert_not_called()


def test_model_selection_respects_experiment_provenance():
    """Comprueba que si el child run reportado pertenece a otro experimento ajeno, no se asume."""
    mock_ml_client = MagicMock()
    mock_job = MagicMock()
    mock_job.name = "wheat_cheese_4swj34tkjn"
    mock_job.status = "Completed"
    mock_job.properties = {
        "best_child_run_id": "experimento_ajeno_99"
    }
    # Sin best_model en parent
    mock_job.outputs = {}
    mock_ml_client.jobs.get.return_value = mock_job

    winner_id, output_name, metadata = resolve_winner_model(mock_ml_client, mock_job)

    assert winner_id is None, "Debe rechazar un child run que no coincida con el experimento actual"
    assert "no corresponde" in metadata.get("ambiguity_reason", "").lower()


def test_download_handles_batch_get_resolved_uris_dto_type_error(tmp_path, capsys):
    """
    Test de regresión: Simula la excepción interna de Azure ML SDK
    'TypeError: BatchGetResolvedUrisDto.__init__() got an unexpected keyword argument values'
    Comprueba que la aplicación:
    1. Entrega diagnóstico claro e instrucciones útiles de alternativa (az ml job download).
    2. No oculta el error (raise ... from e).
    3. Mantiene all=False.
    """
    mock_ml_client = MagicMock()
    mock_job = MagicMock()
    mock_job.name = "wheat_cheese_4swj34tkjn"
    mock_job.status = "Completed"
    mock_job.properties = {
        "primary_metric": "normalized_root_mean_squared_error",
        "metric_value": "0.05859",
    }
    mock_job.outputs = {"best_model": MagicMock()}
    mock_ml_client.jobs.get.return_value = mock_job
    mock_ml_client.resource_group_name = "EcomixIA"
    mock_ml_client.workspace_name = "ecomix-ia-ml"

    # Simular la excepción producida por azure-ai-ml 1.35.x
    mock_ml_client.jobs.download.side_effect = TypeError(
        "BatchGetResolvedUrisDto.__init__() got an unexpected keyword argument 'values'"
    )

    with pytest.raises(RuntimeError) as exc_info:
        download_winner_model(
            mock_ml_client,
            job_name="wheat_cheese_4swj34tkjn",
            download_dir=tmp_path
        )

    # 1. Error preservado (no ocultado)
    assert isinstance(exc_info.value.__cause__, TypeError)
    assert "BatchGetResolvedUrisDto" in str(exc_info.value.__cause__)

    # 2. Instrucciones útiles impresas en consola (excluyendo Azure CLI por presentar idéntico fallo)
    captured = capsys.readouterr().out
    assert "ml_client.models.download" in captured
    assert "Azure ML Studio" in captured
    assert "best_model" in captured
    assert "BatchGetResolvedUrisDto" in captured
    assert "ERROR DE COMPATIBILIDAD INTERNA DEL SDK AZURE ML" in captured
    assert "Azure CLI (extensión 'ml' 2.45.2) presenta la misma" in captured

    # 3. Descarga invocada con all=False
    mock_ml_client.jobs.download.assert_called_once()
    _, kwargs = mock_ml_client.jobs.download.call_args
    assert kwargs.get("all") is False
    assert kwargs.get("output_name") == "best_model"


def test_download_does_not_declare_success_if_files_missing(tmp_path):
    """
    Comprueba que la aplicación nunca declara éxito si la descarga no depositó
    archivos de modelo válidos (.pkl o MLmodel) en disco.
    """
    mock_ml_client = MagicMock()
    mock_job = MagicMock()
    mock_job.name = "wheat_cheese_4swj34tkjn"
    mock_job.status = "Completed"
    mock_job.properties = {}
    mock_job.outputs = {"best_model": MagicMock()}
    mock_ml_client.jobs.get.return_value = mock_job

    # Simular que download() no descarga ningún archivo en tmp_path
    mock_ml_client.jobs.download.return_value = None

    with pytest.raises(FileNotFoundError) as exc_info:
        download_winner_model(
            mock_ml_client,
            job_name="wheat_cheese_4swj34tkjn",
            download_dir=tmp_path
        )

    assert "no se localizaron archivos válidos" in str(exc_info.value).lower()


# ==============================================================================
# 5. Pruebas de Descarga Directa vía Model Asset (Fase 4.3)
# ==============================================================================

def test_download_via_model_asset_preferred_when_available(tmp_path):
    """
    Comprueba que cuando el job AutoML identifica un Model Asset verificado,
    download_winner_model prefiere ml_client.models.download en lugar de ml_client.jobs.download.
    """
    mock_ml_client = MagicMock()
    mock_job = MagicMock()
    mock_job.name = "wheat_cheese_4swj34tkjn"
    mock_job.status = "Completed"
    mock_job.tags = {
        "automl_best_child_run_id": "wheat_cheese_4swj34tkjn_11"
    }
    mock_job.properties = {
        "primary_metric": "normalized_root_mean_squared_error",
        "metric_value": "0.05859",
    }
    mock_job.outputs = {"best_model": MagicMock()}
    mock_ml_client.jobs.get.return_value = mock_job

    # Mock del Model Asset en el workspace
    mock_model = MagicMock()
    mock_model.name = "azureml_wheat_cheese_4swj34tkjn_11_output_mlflow_log_model_873731674"
    mock_model.version = "1"
    mock_ml_client.models.list.return_value = [mock_model]

    # Simular que models.download deposita el archivo model.pkl en tmp_path
    target_dir = tmp_path / "wheat_cheese_4swj34tkjn"
    target_dir.mkdir(parents=True, exist_ok=True)
    fake_model = target_dir / "mlflow-model" / "model.pkl"
    fake_model.parent.mkdir(parents=True, exist_ok=True)
    fake_model.write_bytes(b"dummy_model_asset_content")

    res_path = download_winner_model(
        mock_ml_client,
        job_name="wheat_cheese_4swj34tkjn",
        download_dir=target_dir
    )

    # Debe invocar models.download y NO jobs.download
    mock_ml_client.models.download.assert_called_once_with(
        name="azureml_wheat_cheese_4swj34tkjn_11_output_mlflow_log_model_873731674",
        version="1",
        download_path=str(target_dir)
    )
    mock_ml_client.jobs.download.assert_not_called()
    assert res_path.exists()
    assert res_path.name == "model.pkl"


def test_download_via_model_asset_fallback_to_jobs_download_on_failure(tmp_path):
    """
    Comprueba que si la descarga directa de Model Asset arroja una excepción,
    se recurre automáticamente a jobs.download como alternativa.
    """
    mock_ml_client = MagicMock()
    mock_job = MagicMock()
    mock_job.name = "wheat_cheese_4swj34tkjn"
    mock_job.status = "Completed"
    mock_job.tags = {
        "automl_best_child_run_id": "wheat_cheese_4swj34tkjn_11"
    }
    mock_job.properties = {}
    mock_job.outputs = {"best_model": MagicMock()}
    mock_ml_client.jobs.get.return_value = mock_job

    mock_model = MagicMock()
    mock_model.name = "azureml_wheat_cheese_4swj34tkjn_11_output_mlflow_log_model_873731674"
    mock_model.version = "1"
    mock_ml_client.models.list.return_value = [mock_model]

    # Simular que models.download falla (ej. error de permisos temporales en Model Container)
    mock_ml_client.models.download.side_effect = Exception("Storage read timeout")

    target_dir = tmp_path / "wheat_cheese_4swj34tkjn"
    target_dir.mkdir(parents=True, exist_ok=True)
    fake_model = target_dir / "best_model" / "model.pkl"
    fake_model.parent.mkdir(parents=True, exist_ok=True)
    fake_model.write_bytes(b"dummy_job_output_model")

    res_path = download_winner_model(
        mock_ml_client,
        job_name="wheat_cheese_4swj34tkjn",
        download_dir=target_dir
    )

    # Intentó models.download y luego ejecutó jobs.download
    mock_ml_client.models.download.assert_called_once()
    mock_ml_client.jobs.download.assert_called_once()
    assert res_path.exists()


def test_model_asset_resolution_respects_provenance():
    """
    Comprueba que si el child run reportado no coincide con el prefijo del experimento,
    no se resuelve ningún Model Asset espurio ni se confunde con otros experimentos.
    """
    from src.evaluate_model import resolve_model_asset

    mock_ml_client = MagicMock()
    # Child run de otro experimento ajeno
    name, ver = resolve_model_asset(
        mock_ml_client,
        winner_child_id="experimento_ajeno_11",
        job_name="wheat_cheese_4swj34tkjn"
    )
    assert name is None
    assert ver is None
    mock_ml_client.models.list.assert_not_called()
