#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
tests/test_model_runtime.py — Pruebas unitarias para scripts/check_model_runtime.py.
"""

from __future__ import annotations

import json
from pathlib import Path
import pickle
import subprocess
import sys

import pytest
import yaml

from scripts.check_model_runtime import (
    BASE_DIR,
    check_python_310_availability,
    classify_dependencies,
    find_model_directory,
    generate_runtime_report,
    inspect_metadata,
    inspect_pickle_classes,
)


def test_find_model_directory_finds_actual_or_mock(tmp_path: Path):
    # Sin modelos
    assert find_model_directory(tmp_path) is None

    # Con modelo simulado
    model_sub = tmp_path / "subjob" / "mlflow-model"
    model_sub.mkdir(parents=True)
    (model_sub / "MLmodel").write_text("artifact_path: outputs\n", encoding="utf-8")

    found = find_model_directory(tmp_path)
    assert found == model_sub


def test_inspect_metadata_parses_mlmodel(tmp_path: Path):
    model_dir = tmp_path / "mock_model"
    model_dir.mkdir(parents=True)

    mlmodel_content = {
        "artifact_path": "outputs/mlflow-model",
        "flavors": {
            "python_function": {
                "loader_module": "mlflow.sklearn",
                "python_version": "3.10.19"
            },
            "sklearn": {
                "sklearn_version": "1.5.1",
                "serialization_format": "pickle"
            }
        },
        "mlflow_version": "2.15.1",
        "model_size_bytes": 12345,
        "run_id": "test_run_123",
        "signature": {
            "inputs": json.dumps([
                {"name": "cement", "type": "double"},
                {"name": "water", "type": "double"}
            ]),
            "outputs": json.dumps([{"type": "tensor"}])
        },
        "metadata": {
            "azureml.base_image": "mcr.microsoft.com/azureml/curated/ai-ml-automl:41"
        }
    }

    with open(model_dir / "MLmodel", "w", encoding="utf-8") as f:
        yaml.dump(mlmodel_content, f)

    meta = inspect_metadata(model_dir)
    assert meta["files_present"]["MLmodel"] is True
    ml = meta["mlmodel"]
    assert ml["run_id"] == "test_run_123"
    assert ml["python_version"] == "3.10.19"
    assert ml["sklearn_version"] == "1.5.1"
    assert ml["loader_module"] == "mlflow.sklearn"
    assert ml["signature_features"] == ["cement", "water"]


def test_inspect_pickle_classes_extracts_symbols_safely(tmp_path: Path):
    # Crear un pickle simulado con una clase estándar de scikit-learn y builtins
    pickle_path = tmp_path / "dummy.pkl"
    from sklearn.preprocessing import StandardScaler
    scaler = StandardScaler()
    with open(pickle_path, "wb") as f:
        pickle.dump(scaler, f)

    diag = inspect_pickle_classes(pickle_path)
    assert "error" not in diag
    assert diag["total_referenced_symbols"] > 0
    scikit_classes = diag["categorized_symbols"]["scikit_learn"]
    assert any("StandardScaler" in c for c in scikit_classes)
    assert diag["requires_azureml_automl_runtime"] is False


def test_check_python_310_availability_structure():
    res = check_python_310_availability()
    assert "available" in res
    assert "details" in res
    assert "current_python" in res
    assert isinstance(res["available"], bool)


def test_classify_dependencies_categorizes_correctly():
    mock_meta = {
        "mlmodel": {
            "python_version": "3.10.19",
            "sklearn_version": "1.5.1"
        }
    }
    diag = classify_dependencies(mock_meta)
    assert "compatible" in diag
    assert "incompatible" in diag
    assert "unverified" in diag
    assert "recommended_alternative" in diag
    assert len(diag["compatible"]) > 0


def test_cli_json_mode(tmp_path: Path):
    # Crear un artefacto simulado en tmp_path para que pase tanto en local como en CI limpio
    mock_dir = tmp_path / "mock_run" / "mlflow-model"
    mock_dir.mkdir(parents=True)
    with open(mock_dir / "MLmodel", "w", encoding="utf-8") as f:
        yaml.dump({
            "artifact_path": "outputs/mlflow-model",
            "flavors": {"sklearn": {"sklearn_version": "1.5.1"}},
            "run_id": "mock_123"
        }, f)

    proc = subprocess.run(
        [sys.executable, "scripts/check_model_runtime.py", "--models-dir", str(tmp_path), "--json"],
        cwd=str(BASE_DIR),
        capture_output=True,
        text=True,
        timeout=60,
        check=False
    )
    assert proc.returncode == 0
    data = json.loads(proc.stdout)
    assert data["status"] == "success"
    assert "model_artifact" in data
    assert "dependency_classification" in data
