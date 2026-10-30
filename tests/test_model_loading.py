#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
tests/test_model_loading.py — Pruebas automatizadas de carga controlada de modelos MLflow.
"""

from __future__ import annotations

import json
from pathlib import Path
import subprocess
import sys

import mlflow.sklearn
import numpy as np
import pandas as pd
import pytest
from sklearn.ensemble import VotingRegressor
from sklearn.linear_model import LinearRegression, Ridge
import yaml

from scripts.verify_model_load import (
    BASE_DIR,
    DEFAULT_MODELS_DIR,
    EXPECTED_FEATURES,
    create_dummy_sample,
    find_mlmodel_dir,
    load_and_verify_model,
    run_verification_pipeline,
    verify_model_signature,
)


@pytest.fixture
def simulated_mlflow_model(tmp_path: Path) -> Path:
    """Crea y guarda un modelo VotingRegressor sintético con las 8 variables predictoras."""
    model_dir = tmp_path / "simulated_model"

    # Crear ensamble scikit-learn
    reg1 = LinearRegression()
    reg2 = Ridge(random_state=42)
    ensemble = VotingRegressor([("lr", reg1), ("ridge", reg2)])

    # Datos sintéticos con las 8 características
    X = pd.DataFrame(
        np.random.rand(10, 8) * 100,
        columns=EXPECTED_FEATURES
    )
    y = np.random.rand(10) * 50

    ensemble.fit(X, y)

    # Guardar usando mlflow.sklearn con formato pickle (idéntico al modelo de Azure)
    mlflow.sklearn.save_model(
        sk_model=ensemble,
        path=str(model_dir),
        input_example=X.iloc[:1],
        serialization_format=mlflow.sklearn.SERIALIZATION_FORMAT_PICKLE
    )

    return model_dir


def test_verify_model_signature_success_on_real_or_valid_model():
    real_dir = find_mlmodel_dir(DEFAULT_MODELS_DIR)
    if real_dir:
        ok, features, err = verify_model_signature(real_dir)
        assert ok is True
        assert err is None
        assert len(features) == 8
        assert set(features) == set(EXPECTED_FEATURES)


def test_verify_model_signature_detects_missing_features(tmp_path: Path):
    model_dir = tmp_path / "bad_model"
    model_dir.mkdir()
    # Solo 2 variables en la firma
    mlmodel_data = {
        "signature": {
            "inputs": json.dumps([
                {"name": "cement", "type": "double"},
                {"name": "water", "type": "double"}
            ]),
            "outputs": json.dumps([{"type": "tensor"}])
        }
    }
    with open(model_dir / "MLmodel", "w", encoding="utf-8") as f:
        yaml.dump(mlmodel_data, f)

    ok, features, err = verify_model_signature(model_dir)
    assert ok is False
    assert "Discrepancia" in str(err)
    assert "blast_furnace_slag" in str(err)


def test_load_and_verify_simulated_model_end_to_end(simulated_mlflow_model: Path):
    """Verifica que un modelo compatible se cargue, confirme tipo y ejecute predict()."""
    report = load_and_verify_model(simulated_mlflow_model, dry_run_predict=True)

    assert report["signature_verified"] is True
    assert report["load_successful"] is True
    assert report["estimator_type"] == "VotingRegressor"
    assert report["has_predict_method"] is True
    assert report["status"] == "verified"
    assert isinstance(report["dry_run_prediction"], float)


def test_load_real_automl_model_handles_missing_runtime_gracefully():
    """Comprueba que el modelo real capture la dependencia especializada sin lanzar excepciones no controladas."""
    real_dir = find_mlmodel_dir(DEFAULT_MODELS_DIR)
    if not real_dir:
        pytest.skip("Modelo real no descargado en models/")

    report = load_and_verify_model(real_dir, dry_run_predict=False)
    assert report["signature_verified"] is True

    # En este entorno de desarrollo (Python 3.13 en Windows sin azureml-training-tabular)
    # debe reportar blocked_by_missing_dependency o cargar si la dependencia estuviera disponible
    if not report["load_successful"]:
        assert report["status"] == "blocked_by_missing_dependency"
        assert "azureml" in report["error"]
        assert report["environment_recommendation"] is not None


def test_create_dummy_sample_has_correct_columns_and_types():
    df = create_dummy_sample()
    assert list(df.columns) == EXPECTED_FEATURES
    assert len(df) == 1
    assert df["cement"].iloc[0] == 300.0
    assert df["age"].iloc[0] == 28


def test_cli_execution_with_check_flag(simulated_mlflow_model: Path):
    proc = subprocess.run(
        [sys.executable, "scripts/verify_model_load.py", "--check", "--model-dir", str(simulated_mlflow_model)],
        cwd=str(BASE_DIR),
        capture_output=True,
        text=True,
        timeout=60,
        check=False
    )
    assert proc.returncode == 0


def test_signature_only_mode_does_not_attempt_loading(simulated_mlflow_model: Path):
    report = run_verification_pipeline(
        simulated_mlflow_model,
        check_signature=True,
        attempt_load=False,
        test_predict=False
    )
    assert report["signature_verified"] is True
    assert report["load_attempted"] is False
    assert report["load_successful"] is False
    assert report["status"] == "signature_verified_only"


def test_cli_signature_only_flag(simulated_mlflow_model: Path):
    proc = subprocess.run(
        [sys.executable, "scripts/verify_model_load.py", "--signature-only", "--model-dir", str(simulated_mlflow_model)],
        cwd=str(BASE_DIR),
        capture_output=True,
        text=True,
        timeout=60,
        check=False
    )
    assert proc.returncode == 0


def test_cli_require_load_flag_success_on_compatible_model(simulated_mlflow_model: Path):
    proc = subprocess.run(
        [sys.executable, "scripts/verify_model_load.py", "--require-load", "--model-dir", str(simulated_mlflow_model)],
        cwd=str(BASE_DIR),
        capture_output=True,
        text=True,
        timeout=60,
        check=False
    )
    assert proc.returncode == 0


def test_cli_require_load_flag_failure_on_incompatible_runtime():
    real_dir = find_mlmodel_dir(DEFAULT_MODELS_DIR)
    if not real_dir:
        pytest.skip("Modelo real no descargado en models/")

    proc = subprocess.run(
        [sys.executable, "scripts/verify_model_load.py", "--require-load", "--model-dir", str(real_dir)],
        cwd=str(BASE_DIR),
        capture_output=True,
        text=True,
        timeout=60,
        check=False
    )
    # En Python 3.13 sin azureml-training-tabular, la carga debe fallar con código 2
    assert proc.returncode == 2

