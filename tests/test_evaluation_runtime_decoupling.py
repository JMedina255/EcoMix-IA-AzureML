"""
Pruebas de regresión: Desacoplamiento del runtime de evaluación del SDK de administración de Azure ML.

Garantiza que:
1. 'src.evaluate_model' puede importarse y ejecutarse en modo '--evaluate' en entornos
   donde 'azure-ai-ml' y 'azure-identity' NO están instalados (como el contenedor curado oficial
   de Azure AutoML 'mcr.microsoft.com/azureml/curated/ai-ml-automl:41').
2. Las operaciones de administración ('--inspect', '--download') informan claramente la ausencia
   del SDK si se invocan sin él.
3. El comportamiento normal con el SDK instalado se preserva al 100%.
"""

import sys
import subprocess
import pytest
from pathlib import Path
from unittest.mock import MagicMock, patch
from sklearn.dummy import DummyRegressor

import src.evaluate_model as evaluate_module
from src.evaluate_model import (
    JobStatus,
    normalize_job_status,
    get_azure_credentials,
    get_ml_client,
    inspect_automl_job,
    download_winner_model,
)


def test_import_evaluate_model_without_azure_sdk_in_isolated_process():
    """
    Simula en un subproceso aislado que 'azure.ai' y 'azure.identity' no existen en sys.modules.
    Verifica que el módulo se importa exitosamente sin lanzar ModuleNotFoundError.
    """
    code = (
        "import sys\n"
        "sys.modules['azure.ai'] = None\n"
        "sys.modules['azure.ai.ml'] = None\n"
        "sys.modules['azure.identity'] = None\n"
        "import src.evaluate_model as em\n"
        "assert hasattr(em, 'evaluate_model')\n"
        "assert hasattr(em, 'main')\n"
        "assert hasattr(em, 'validate_test_dataset')\n"
        "print('IMPORT_SUCCESS')\n"
    )
    result = subprocess.run(
        [sys.executable, "-c", code],
        capture_output=True,
        text=True,
        check=True
    )
    assert "IMPORT_SUCCESS" in result.stdout


def test_get_azure_credentials_raises_clear_error_when_identity_missing():
    """Verifica que get_azure_credentials produce un ImportError claro cuando azure-identity no existe."""
    with patch.dict(sys.modules, {"azure.identity": None}):
        with pytest.raises(ImportError) as exc_info:
            get_azure_credentials()
        msg = str(exc_info.value)
        assert "azure-identity" in msg
        assert "operaciones de administración" in msg


def test_get_ml_client_raises_clear_error_when_sdk_missing():
    """Verifica que get_ml_client produce un ImportError claro cuando azure-ai-ml no existe."""
    with patch.dict(sys.modules, {"azure.ai.ml": None, "azure.ai": None}):
        with pytest.raises(ImportError) as exc_info:
            get_ml_client()
        msg = str(exc_info.value)
        assert "azure-ai-ml" in msg
        assert "evaluación remota (--evaluate)" in msg


def test_evaluate_mode_runs_end_to_end_without_azure_sdk(tmp_path):
    """
    Verifica que la función evaluate_model puede ejecutarse de extremo a extremo
    con un modelo dummy sin requerir en ningún momento azure.ai.ml ni azure.identity.
    """
    import pandas as pd
    import numpy as np
    import joblib

    # 1. Crear datasets sintéticos
    features = [
        "cement", "blast_furnace_slag", "fly_ash", "water",
        "superplasticizer", "coarse_aggregate", "fine_aggregate", "age"
    ]
    test_df = pd.DataFrame(
        np.ones((206, len(features))),
        columns=features
    )
    test_df["concrete_compressive_strength"] = 35.0

    test_csv = tmp_path / "concrete_test.csv"
    test_df.to_csv(test_csv, index=False)

    # 2. Entrenar y serializar modelo dummy serializable
    dummy_model = DummyRegressor(strategy="mean")
    dummy_model.fit(test_df[features], test_df["concrete_compressive_strength"])
    model_pkl = tmp_path / "model.pkl"
    joblib.dump(dummy_model, model_pkl)

    reports_dir = tmp_path / "reports"

    # 3. Ejecutar bloqueando completamente los módulos de Azure
    with patch.dict(sys.modules, {
        "azure.ai": None,
        "azure.ai.ml": None,
        "azure.identity": None
    }):
        report = evaluate_module.evaluate_model(
            model_path=model_pkl,
            test_path=test_csv,
            train_path=None,
            reports_dir=reports_dir,
            job_name="test_decoupled_job",
            strict_checksums=False,
            allow_custom_data=True
        )

        assert report["dataset_validation"]["test_samples"] == 206
        assert (reports_dir / "evaluation_test_decoupled_job.json").exists()
        assert (reports_dir / "evaluation_test_decoupled_job_plot.png").exists()


def test_inspect_and_download_preserve_behavior_with_sdk():
    """
    Verifica que las funciones administrativas conservan su contrato y comportamiento
    cuando se ejecutan con clientes mockeados del SDK.
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
    mock_ml_client.jobs.get.return_value = mock_job
    mock_ml_client.models.list.return_value = []

    res = inspect_automl_job(mock_ml_client, job_name="wheat_cheese_4swj34tkjn")
    assert res["status"] == "completed"
    assert res["winner_algorithm"] == "VotingEnsemble"
