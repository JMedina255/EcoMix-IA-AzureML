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
    EXPECTED_WINNER_CHILD_RUN,
    TEST_DATA_PATH,
    audit_code_snapshot_exclusions,
    check_code_snapshot_security,
    compute_file_sha256,
    validate_eval_job_specification,
    SnapshotExclusionEvaluator,
    PROBE_FORBIDDEN_FILES,
    PROBE_REQUIRED_FILES,
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


def test_code_snapshot_security_verifies_amlignore_and_exclusions(tmp_path):
    """Comprueba que la verificación de empaquetado exige .amlignore y exclusión de secretos."""
    # 1. En el repositorio real debe ser completamente válido
    is_valid, issues = check_code_snapshot_security(BASE_DIR)
    assert is_valid is True, f"Fallo de seguridad en el snapshot del repo: {issues}"

    # 2. En directorio sin .amlignore debe fallar
    mock_dir = tmp_path / "mock_project"
    mock_dir.mkdir()
    bad_valid, bad_issues = check_code_snapshot_security(mock_dir)
    assert bad_valid is False
    assert any(".amlignore" in iss for iss in bad_issues)

    # 3. En directorio con .amlignore incompleto (falta config.json) debe fallar
    (mock_dir / ".amlignore").write_text("models/\n*.pkl\n.venv\n", encoding="utf-8")
    inc_valid, inc_issues = check_code_snapshot_security(mock_dir)
    assert inc_valid is False
    assert any("config.json" in iss for iss in inc_issues)


def test_code_snapshot_audit_passes_on_real_repository():
    """Comprueba que la auditoría completa de exclusión aprueba el repositorio real sin fugas."""
    is_valid, issues, audit_details = audit_code_snapshot_exclusions(BASE_DIR)
    assert is_valid is True, f"Fallo en auditoría de empaquetado del repositorio: {issues}"
    assert audit_details["amlignore_exists"] is True
    assert audit_details["forbidden_probes_excluded"] is True
    assert audit_details["required_probes_included"] is True
    assert audit_details["real_workspace_leaks_detected"] == 0
    assert audit_details["forbidden_probes_tested"] >= 20


def test_code_snapshot_audit_rejects_included_config_json(tmp_path):
    """Comprueba que la auditoría rechaza un empaquetado que incluiría config.json."""
    mock_dir = tmp_path / "leak_config"
    mock_dir.mkdir()
    # amlignore que ignora todo excepto config.json
    (mock_dir / ".amlignore").write_text(".env\n*.key\n*.token\n.venv/\nmodels/\n*.pkl\ndata/\n", encoding="utf-8")
    is_valid, issues, audit = audit_code_snapshot_exclusions(mock_dir)
    assert is_valid is False
    assert any("config.json" in iss for iss in issues)


def test_code_snapshot_audit_rejects_included_env_and_tokens(tmp_path):
    """Comprueba que la auditoría rechaza snapshots que incluirían archivos .env o tokens."""
    mock_dir = tmp_path / "leak_secrets"
    mock_dir.mkdir()
    (mock_dir / ".amlignore").write_text("config.json\n.venv/\nmodels/\n*.pkl\ndata/\n", encoding="utf-8")
    is_valid, issues, audit = audit_code_snapshot_exclusions(mock_dir)
    assert is_valid is False
    assert any(".env" in iss or "token" in iss for iss in issues)


def test_code_snapshot_audit_rejects_included_virtualenvs(tmp_path):
    """Comprueba que la auditoría rechaza snapshots que no excluyen entornos virtuales."""
    mock_dir = tmp_path / "leak_venv"
    mock_dir.mkdir()
    (mock_dir / ".amlignore").write_text("config.json\n.env\n*.key\n*.token\nmodels/\n*.pkl\ndata/\n", encoding="utf-8")
    is_valid, issues, audit = audit_code_snapshot_exclusions(mock_dir)
    assert is_valid is False
    assert any(".venv" in iss for iss in issues)


def test_code_snapshot_audit_rejects_included_models_or_binaries(tmp_path):
    """Comprueba que la auditoría rechaza snapshots que incluirían binarios .pkl o models/."""
    mock_dir = tmp_path / "leak_models"
    mock_dir.mkdir()
    (mock_dir / ".amlignore").write_text("config.json\n.env\n*.key\n*.token\n.venv/\ndata/\n", encoding="utf-8")
    is_valid, issues, audit = audit_code_snapshot_exclusions(mock_dir)
    assert is_valid is False
    assert any("models/" in iss or ".pkl" in iss for iss in issues)


def test_code_snapshot_audit_rejects_included_datasets(tmp_path):
    """Comprueba que la auditoría rechaza snapshots que incluirían datasets locales (data/)."""
    mock_dir = tmp_path / "leak_data"
    mock_dir.mkdir()
    (mock_dir / ".amlignore").write_text("config.json\n.env\n*.key\n*.token\n.venv/\nmodels/\n*.pkl\n", encoding="utf-8")
    is_valid, issues, audit = audit_code_snapshot_exclusions(mock_dir)
    assert is_valid is False
    assert any("data/" in iss or "dataset" in iss for iss in issues)


def test_code_snapshot_audit_rejects_erroneous_source_code_exclusion(tmp_path):
    """Comprueba que la auditoría rechaza una regla que excluya erróneamente el código fuente necesario."""
    mock_dir = tmp_path / "bad_src_rule"
    mock_dir.mkdir()
    (mock_dir / ".amlignore").write_text(
        "config.json\n.env\n*.key\n*.token\n.venv/\nmodels/\n*.pkl\ndata/\nsrc/\n",
        encoding="utf-8"
    )
    is_valid, issues, audit = audit_code_snapshot_exclusions(mock_dir)
    assert is_valid is False
    assert any("código fuente esencial" in iss.lower() for iss in issues)


def test_code_snapshot_pure_python_fallback_matches_expected_behavior(tmp_path):
    """Comprueba que el motor de evaluación de respaldo en Python puro replica las exclusiones sin SDK."""
    mock_dir = tmp_path / "pure_py_test"
    mock_dir.mkdir()
    (mock_dir / ".amlignore").write_text(
        "config.json\n.env\n.env*\n*.env\n*.key\n*.pem\n*.token\n"
        ".venv/\nvenv/\nenv/\nENV/\n"
        "models/\n*.pkl\n*.joblib\n*.onnx\n"
        "data/\ndataset/\n",
        encoding="utf-8"
    )
    evaluator = SnapshotExclusionEvaluator(mock_dir)
    # Forzar el motor a fallback_pure_python
    evaluator.sdk_ignore_file = None
    evaluator.engine_name = "fallback_pure_python"

    for forbidden in PROBE_FORBIDDEN_FILES:
        assert evaluator.is_path_excluded(forbidden) is True, f"Fallo en exclusión fallback de {forbidden}"

    for req in PROBE_REQUIRED_FILES:
        assert evaluator.is_path_excluded(req) is False, f"Fallo en inclusión fallback de {req}"


def test_code_snapshot_detects_real_unexcluded_file_leak(tmp_path):
    """Comprueba que la auditoría detecta archivos sensibles reales existentes en el directorio."""
    mock_dir = tmp_path / "real_leak_dir"
    mock_dir.mkdir()
    (mock_dir / ".amlignore").write_text(
        "config.json\n.env\n.venv/\ndata/\n",  # Falta models/ y *.pkl
        encoding="utf-8"
    )
    # Crear modelo real en models/
    models_dir = mock_dir / "models"
    models_dir.mkdir()
    (models_dir / "leaked_winner.pkl").write_bytes(b"dummy_weights")

    is_valid, issues, audit = audit_code_snapshot_exclusions(mock_dir)
    assert is_valid is False
    assert any("fuga de modelo" in iss.lower() or "leaked_winner.pkl" in iss for iss in issues)


def test_azure_eval_job_specifies_winner_child_run():
    """Comprueba que la especificación referencia explícitamente al ganador wheat_cheese_4swj34tkjn_11."""
    with open(CONFIG_JOB_PATH, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f)

    tags = data.get("tags", {})
    assert tags.get("winner_child_run") == EXPECTED_WINNER_CHILD_RUN
