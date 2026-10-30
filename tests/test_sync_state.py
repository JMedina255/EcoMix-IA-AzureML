"""
Pruebas automatizadas para scripts/sync_state.py.
Comprueba idempotencia, modo --check, detección de inconsistencias y operación offline.
"""

import json
from pathlib import Path
import pytest

from scripts.sync_state import (
    render_markdown_state,
    sync_project_state,
    validate_state_consistency,
    inspect_local_datasets,
    inspect_local_models,
)


@pytest.fixture
def mock_project_tree(tmp_path):
    """Crea una estructura de proyecto simulada con configuración y datasets."""
    config_dir = tmp_path / "config"
    docs_dir = tmp_path / "docs"
    data_raw_dir = tmp_path / "data" / "raw"
    data_proc_dir = tmp_path / "data" / "processed"
    models_dir = tmp_path / "models"
    src_dir = tmp_path / "src"

    for d in (config_dir, docs_dir, data_raw_dir, data_proc_dir, models_dir, src_dir):
        d.mkdir(parents=True, exist_ok=True)

    # Crear dataset dummy
    (data_raw_dir / "concrete_raw.csv").write_text("header\nval1\n", encoding="utf-8")
    (data_proc_dir / "concrete_train.csv").write_text("c1,c2\n" + "1,2\n" * 824, encoding="utf-8")
    (data_proc_dir / "concrete_test.csv").write_text("c1,c2\n" + "1,2\n" * 206, encoding="utf-8")
    (src_dir / "evaluate_model.py").write_text("# dummy", encoding="utf-8")

    status_data = {
        "project_id": "test-project",
        "repository": "user/test-repo",
        "default_branch": "main",
        "current_phase": "4.3",
        "next_authorized_milestone": "4.4",
        "last_validation": {"date": "2026-10-30", "origin": "Test"},
        "azure_experiment": {
            "job_id": "test_job_123",
            "job_status": "completed",
            "primary_metric": "nrmse",
            "metric_value": 0.05,
            "winning_algorithm": "VotingEnsemble",
            "winner_child_run_id": "test_job_123_1",
            "model_asset": {
                "name": "azureml_test_job_123_1_output",
                "version": "1",
                "model_size_bytes": 1000
            },
            "training_environment": {
                "curated_image": "test-image:1",
                "python_version": "3.10"
            }
        },
        "phases": {
            "fase_1": {"name": "Descarga", "status": "completed", "script": "dataset.py", "evidence": "OK"},
            "fase_2": {"name": "Preparacion", "status": "completed", "script": "src/prepare.py", "evidence": "OK"},
            "fase_4_1": {"name": "Inspeccion", "status": "completed", "script": "src/eval.py", "evidence": "OK"},
            "fase_4_3": {"name": "Descarga", "status": "completed", "script": "src/eval.py", "evidence": "OK"},
        },
        "open_issues": [],
        "verified_tests": {"total_tests": 10, "suite": "pytest", "test_files": ["tests/test.py"]}
    }

    config_file = config_dir / "project_status.json"
    with open(config_file, "w", encoding="utf-8") as f:
        json.dump(status_data, f)

    return tmp_path, status_data


def test_sync_state_idempotence(mock_project_tree):
    """Comprueba que dos sincronizaciones consecutivas producen exactamente el mismo contenido."""
    root_dir, _ = mock_project_tree

    # Ejecución 1
    synced_1, warnings_1 = sync_project_state(root_dir=root_dir, check_only=False)
    doc_path = root_dir / "docs" / "PROJECT_STATE.md"
    assert doc_path.exists()
    content_1 = doc_path.read_text(encoding="utf-8")

    # Ejecución 2
    synced_2, warnings_2 = sync_project_state(root_dir=root_dir, check_only=False)
    content_2 = doc_path.read_text(encoding="utf-8")

    assert content_1 == content_2, "La sincronización debe ser estrictamente idempotente"
    assert warnings_1 == warnings_2


def test_sync_state_check_mode_success(mock_project_tree):
    """Comprueba que --check devuelve True cuando el archivo markdown está sincronizado."""
    root_dir, _ = mock_project_tree

    # Primero sincronizar
    sync_project_state(root_dir=root_dir, check_only=False)

    # Luego comprobar
    is_synced, _ = sync_project_state(root_dir=root_dir, check_only=True)
    assert is_synced is True


def test_sync_state_check_mode_detects_outdated_state(mock_project_tree):
    """Comprueba que --check detecta diferencias cuando docs/PROJECT_STATE.md está desactualizado."""
    root_dir, _ = mock_project_tree

    sync_project_state(root_dir=root_dir, check_only=False)
    doc_path = root_dir / "docs" / "PROJECT_STATE.md"

    # Modificar artificialmente el documento
    doc_path.write_text("Contenido desactualizado o corrupto", encoding="utf-8")

    is_synced, _ = sync_project_state(root_dir=root_dir, check_only=True)
    assert is_synced is False


def test_sync_state_detects_missing_dataset_inconsistency(mock_project_tree):
    """Comprueba que si falta un dataset de una fase completada, se emite una advertencia clara."""
    root_dir, status_data = mock_project_tree

    # Eliminar dataset de entrenamiento
    train_p = root_dir / "data" / "processed" / "concrete_train.csv"
    train_p.unlink()

    warnings = validate_state_consistency(status_data, root_dir=root_dir)
    assert any("Fase 2 declarada 'completed' pero faltan datasets" in w for w in warnings)


def test_sync_state_does_not_modify_phases_automatically(mock_project_tree):
    """Comprueba que sync_state nunca altera arbitrariamente el estado de las fases en el JSON."""
    root_dir, _ = mock_project_tree
    config_file = root_dir / "config" / "project_status.json"
    initial_config_hash = hash(config_file.read_text(encoding="utf-8"))

    # Ejecutar sync
    sync_project_state(root_dir=root_dir, check_only=False)

    final_config_hash = hash(config_file.read_text(encoding="utf-8"))
    assert initial_config_hash == final_config_hash, "El JSON declarativo no debe ser modificado por sync_state"
