"""
Pruebas automatizadas para COMMIT 1:
Inspección segura y descarga selectiva de modelos AutoML en Azure ML.
Todas las pruebas se ejecutan con clientes simulados (mocks) sin requerir credenciales reales ni conexión de red.
"""

import pytest
from unittest.mock import MagicMock, patch
from pathlib import Path

from src.evaluate_model import (
    inspect_automl_job,
    download_winner_model,
    resolve_winner_model,
    parse_args,
    main,
)


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
        "best_child_run_id": "wheat_cheese_4swj34tkjn_12",
        "primary_metric": "normalized_root_mean_squared_error",
        "metric_value": "0.045",
        "run_algorithm": "VotingEnsemble"
    }
    mock_job.tags = {"project": "EcoMix-IA"}
    mock_job.outputs = {"best_model": MagicMock()}
    mock_ml_client.jobs.get.return_value = mock_job

    result = inspect_automl_job(mock_ml_client, "wheat_cheese_4swj34tkjn")

    assert result["status"] == "Completed"
    assert result["winner_model_id"] == "wheat_cheese_4swj34tkjn_12"
    assert result["primary_metric"] == "normalized_root_mean_squared_error"
    # Asegurar que nunca se llamó a download
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
    mock_job.status = "Running"
    mock_job.properties = {}
    mock_job.tags = {}
    mock_job.outputs = {}
    mock_ml_client.jobs.get.return_value = mock_job

    with pytest.raises(ValueError) as exc_info:
        download_winner_model(mock_ml_client, "wheat_cheese_4swj34tkjn", download_dir=tmp_path)

    assert "no ha finalizado exitosamente" in str(exc_info.value).lower()
    assert "running" in str(exc_info.value).lower()
    mock_ml_client.jobs.download.assert_not_called()


def test_ambiguous_model_selection_prevents_download(tmp_path):
    """Comprueba que si no se puede identificar unívocamente el ganador, se cancela la descarga."""
    mock_ml_client = MagicMock()
    mock_job = MagicMock()
    mock_job.name = "wheat_cheese_4swj34tkjn"
    mock_job.status = "Completed"
    mock_job.properties = {}  # Sin best_child_run_id
    mock_job.tags = {}
    mock_job.outputs = {}
    mock_ml_client.jobs.get.return_value = mock_job

    # Simulamos múltiples child runs donde ninguno tiene marca de ganador
    child_1 = MagicMock(name="child_1", status="Completed", properties={}, tags={})
    child_2 = MagicMock(name="child_2", status="Completed", properties={}, tags={})
    mock_ml_client.jobs.list.return_value = [child_1, child_2]

    with pytest.raises(ValueError) as exc_info:
        download_winner_model(mock_ml_client, "wheat_cheese_4swj34tkjn", download_dir=tmp_path)

    assert "no es posible identificar inequívocamente" in str(exc_info.value).lower()
    mock_ml_client.jobs.download.assert_not_called()


def test_download_never_uses_all_true(tmp_path):
    """Comprueba que --download NUNCA utiliza all=True y pasa output_name específico."""
    mock_ml_client = MagicMock()
    mock_job = MagicMock()
    mock_job.name = "wheat_cheese_4swj34tkjn"
    mock_job.status = "Completed"
    mock_job.properties = {
        "best_child_run_id": "wheat_cheese_4swj34tkjn_12",
        "primary_metric": "normalized_root_mean_squared_error",
    }
    mock_job.tags = {"project": "EcoMix-IA"}
    mock_job.outputs = {"best_model": MagicMock()}
    mock_ml_client.jobs.get.return_value = mock_job

    # Creamos un archivo simulado model.pkl en la carpeta destino para simular descarga
    target_dir = tmp_path / "wheat_cheese_4swj34tkjn"
    target_dir.mkdir(parents=True, exist_ok=True)
    fake_model = target_dir / "best_model" / "model.pkl"
    fake_model.parent.mkdir(parents=True, exist_ok=True)
    fake_model.write_bytes(b"dummy_serialized_model")

    model_path = download_winner_model(
        mock_ml_client,
        job_name="wheat_cheese_4swj34tkjn",
        download_dir=target_dir
    )

    mock_ml_client.jobs.download.assert_called_once()
    call_args, call_kwargs = mock_ml_client.jobs.download.call_args

    # Verificaciones estrictas del contrato de seguridad:
    assert call_kwargs.get("all") is False, "El parámetro 'all' debe ser estrictamente False"
    assert call_kwargs.get("output_name") == "best_model", "Debe descargar un output específico registrado"
    assert model_path.exists()


def test_model_selection_respects_experiment_provenance():
    """Comprueba que si el modelo ganador reportado pertenece a otro experimento, se rechaza."""
    mock_ml_client = MagicMock()
    mock_job = MagicMock()
    mock_job.name = "wheat_cheese_4swj34tkjn"
    mock_job.status = "Completed"
    mock_job.properties = {
        # Child run perteneciente a un experimento completamente ajeno
        "best_child_run_id": "otro_experimento_completamente_distinto_99"
    }
    mock_job.tags = {}
    mock_job.outputs = {}
    mock_ml_client.jobs.get.return_value = mock_job

    winner_id, output_name, metadata = resolve_winner_model(mock_ml_client, mock_job)

    assert winner_id is None, "Debe rechazar un modelo que no coincida con el experimento actual"
    assert "inconsistencia de procedencia" in metadata.get("ambiguity_reason", "").lower()
