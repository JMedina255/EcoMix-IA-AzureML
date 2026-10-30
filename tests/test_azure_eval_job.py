#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
tests/test_azure_eval_job.py — Pruebas automatizadas de la configuración declarativa del job de evaluación.
"""

from __future__ import annotations

import json
from pathlib import Path
import subprocess
import sys

import pytest
import yaml

from scripts.prepare_azure_eval_job import (
    BASE_DIR,
    CONFIG_JOB_PATH,
    EXPECTED_COMPUTE_CLUSTER,
    EXPECTED_ENVIRONMENT_IMAGE,
    EXPECTED_INSTANCE_COUNT,
    EXPECTED_TIMEOUT_SECONDS,
    EXPECTED_WINNER_MODEL_ASSET,
    TEST_DATA_PATH,
    compute_file_sha256,
    validate_eval_job_specification,
)


def test_azure_eval_job_yaml_exists_and_is_valid():
    assert CONFIG_JOB_PATH.exists(), f"No existe {CONFIG_JOB_PATH}"
    with open(CONFIG_JOB_PATH, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f)
    assert isinstance(data, dict)
    assert data.get("type") == "command"


def test_azure_eval_job_matches_specification_contract():
    is_valid, metadata, errors = validate_eval_job_specification(
        job_yaml_path=CONFIG_JOB_PATH,
        test_data_path=TEST_DATA_PATH
    )
    assert is_valid is True, f"Errores en la especificación: {errors}"
    assert metadata["compute"] == EXPECTED_COMPUTE_CLUSTER
    assert metadata["environment_image"] == EXPECTED_ENVIRONMENT_IMAGE
    assert metadata["model_asset"] == EXPECTED_WINNER_MODEL_ASSET
    assert metadata["timeout_seconds"] == EXPECTED_TIMEOUT_SECONDS
    assert metadata["instance_count"] == EXPECTED_INSTANCE_COUNT
    assert "reports_dir" in metadata["outputs"]


def test_azure_eval_job_rejects_timeout_minutes_legacy_field(tmp_path):
    """Comprueba que se rechaza explícitamente el campo no oficial timeout_minutes."""
    with open(CONFIG_JOB_PATH, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f)

    # Introducir el campo no oficial
    data["limits"] = {"timeout_minutes": 30}
    bad_yaml = tmp_path / "bad_timeout_job.yml"
    with open(bad_yaml, "w", encoding="utf-8") as f:
        yaml.dump(data, f)

    is_valid, metadata, errors = validate_eval_job_specification(
        job_yaml_path=bad_yaml,
        test_data_path=TEST_DATA_PATH
    )
    assert is_valid is False
    assert any("timeout_minutes" in err for err in errors)


def test_azure_eval_job_validates_against_official_sdk_schema():
    """Valida la especificación contra el esquema oficial de Azure ML SDK v2."""
    from azure.ai.ml import load_job
    job = load_job(source=str(CONFIG_JOB_PATH))
    assert job.type == "command"
    assert job.compute in ("cpu-cluster-ecomix", "azureml:cpu-cluster-ecomix")
    assert job.limits.timeout == 1800


def test_test_data_sha256_matches_job_tags():
    with open(CONFIG_JOB_PATH, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f)

    tags = data.get("tags", {})
    expected_sha = compute_file_sha256(TEST_DATA_PATH)
    assert tags.get("test_sha256") == expected_sha
    assert tags.get("test_samples") == "206"


def test_cli_execution_with_check_flag():
    proc = subprocess.run(
        [sys.executable, "scripts/prepare_azure_eval_job.py", "--check"],
        cwd=str(BASE_DIR),
        capture_output=True,
        text=True,
        timeout=60,
        check=False
    )
    assert proc.returncode == 0
    assert "ESPECIFICACIÓN DEL JOB DE EVALUACIÓN AZURE ML" in proc.stdout or "ESPECIFICACI" in proc.stdout


def test_cli_execution_with_json_flag():
    proc = subprocess.run(
        [sys.executable, "scripts/prepare_azure_eval_job.py", "--json"],
        cwd=str(BASE_DIR),
        capture_output=True,
        text=True,
        timeout=60,
        check=False
    )
    assert proc.returncode == 0
    payload = json.loads(proc.stdout)
    assert payload["valid"] is True
    assert payload["metadata"]["actual_test_sha256"] is not None
