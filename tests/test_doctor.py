#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
tests/test_doctor.py — Pruebas unitarias para scripts/doctor.py.
"""

from __future__ import annotations

import json
from pathlib import Path
import subprocess
import sys
from unittest.mock import patch

import pytest

from scripts.doctor import (
    BASE_DIR,
    check_module,
    diagnose_azure,
    diagnose_development,
    diagnose_evaluation,
    diagnose_inference,
    run_cmd,
    run_doctor,
)


def test_check_module_returns_true_for_installed_lib():
    ok, ver = check_module("sys")
    assert ok is True
    # pytest itself should be installed in the test environment
    ok_pytest, ver_pytest = check_module("pytest")
    assert ok_pytest is True
    assert ver_pytest is not None


def test_check_module_returns_false_for_nonexistent_lib():
    ok, ver = check_module("nonexistent_module_xyz_12345")
    assert ok is False
    assert ver is None


def test_diagnose_development_structure():
    result = diagnose_development(BASE_DIR)
    assert "ready" in result
    assert "details" in result
    assert "failures" in result
    assert "actions" in result
    assert "python_version" in result["details"]
    assert "git_repo" in result["details"]


def test_diagnose_azure_masks_subscription(tmp_path: Path):
    # Crear un config.json simulado con credencial ficticia
    config_file = tmp_path / "config.json"
    fake_sub = "12345678-abcd-1234-abcd-123456789abc"
    config_file.write_text(
        json.dumps({
            "subscription_id": fake_sub,
            "resource_group": "rg-test",
            "workspace_name": "ws-test"
        }),
        encoding="utf-8"
    )

    result = diagnose_azure(tmp_path)
    # Debe enmascarar la suscripción y no exponerla en texto plano
    assert result["details"]["subscription_masked"] == "...9abc"
    assert fake_sub not in str(result["details"]["subscription_masked"])


def test_diagnose_azure_detects_template_config(tmp_path: Path):
    config_file = tmp_path / "config.json"
    config_file.write_text(
        json.dumps({
            "subscription_id": "TU_SUBSCRIPTION_ID",
            "resource_group": "TU_RESOURCE_GROUP",
            "workspace_name": "TU_WORKSPACE"
        }),
        encoding="utf-8"
    )

    result = diagnose_azure(tmp_path)
    assert result["details"]["config_configured"] is False
    assert any("plantilla" in f.lower() for f in result["failures"])


def test_diagnose_azure_detects_missing_config(tmp_path: Path):
    result = diagnose_azure(tmp_path)
    assert result["details"]["config_present"] is False
    assert result["ready"] is False
    assert any("config.json" in f.lower() for f in result["failures"])


def test_diagnose_evaluation_detects_missing_model(tmp_path: Path):
    # Simular estructura sin modelos
    data_dir = tmp_path / "data" / "processed"
    data_dir.mkdir(parents=True)
    test_file = data_dir / "concrete_test.csv"
    test_file.write_text("cement,age,concrete_compressive_strength\n300,28,45.2\n", encoding="utf-8")

    result = diagnose_evaluation(tmp_path)
    assert result["ready"] is False
    assert result["details"]["model_files_count"] == 0
    assert any("modelo binario" in f.lower() for f in result["failures"])
    assert any("evaluate_model.py --download" in act for act in result["actions"])


def test_diagnose_inference_detects_missing_script(tmp_path: Path):
    result = diagnose_inference(tmp_path)
    assert result["details"]["inference_script_exists"] is False
    assert result["ready"] is False
    assert any("inference.py" in f for f in result["failures"])


def test_run_doctor_complete_structure():
    report = run_doctor(BASE_DIR)
    assert "system" in report
    assert "environments" in report
    assert "all_ready" in report
    assert "development" in report["environments"]
    assert "azure" in report["environments"]
    assert "evaluation" in report["environments"]
    assert "inference" in report["environments"]


def test_doctor_cli_json_mode():
    proc = subprocess.run(
        [sys.executable, "scripts/doctor.py", "--json"],
        cwd=str(BASE_DIR),
        capture_output=True,
        text=True,
        timeout=15,
        check=False
    )
    assert proc.returncode == 0
    data = json.loads(proc.stdout)
    assert "system" in data
    assert "environments" in data
