"""
Pruebas automatizadas para COMMIT 2:
Evaluación local controlada, validación exhaustiva de datasets,
cálculo de métricas segmentadas, medición de recursos y trazabilidad completa en JSON.
Todas las pruebas se ejecutan 100% desconectadas de Azure usando modelos simulados.
"""

import json
import pytest
from pathlib import Path
import pandas as pd
import numpy as np
import joblib
from sklearn.dummy import DummyRegressor

from src.evaluate_model import (
    validate_test_dataset,
    compute_metrics,
    evaluate_model,
    compute_file_sha256,
    EXPECTED_FEATURES,
    TARGET_FEATURE,
)


def create_sample_csv(file_path: Path, n_rows: int = 10, include_overlap_with: pd.DataFrame = None):
    """Genera un archivo CSV sintético válido para pruebas."""
    np.random.seed(42)
    data = {
        "cement": np.random.uniform(100, 500, n_rows),
        "blast_furnace_slag": np.random.uniform(0, 200, n_rows),
        "fly_ash": np.random.uniform(0, 150, n_rows),
        "water": np.random.uniform(120, 240, n_rows),
        "superplasticizer": np.random.uniform(0, 25, n_rows),
        "coarse_aggregate": np.random.uniform(800, 1100, n_rows),
        "fine_aggregate": np.random.uniform(600, 900, n_rows),
        # Incluir edades críticas 7 y 28 días
        "age": np.random.choice([7, 28, 56], n_rows),
        "concrete_compressive_strength": np.random.uniform(10, 80, n_rows),
    }
    df = pd.DataFrame(data)

    if include_overlap_with is not None and len(include_overlap_with) > 0:
        # Copiar las dos primeras filas exactamente para simular réplica ASTM C39
        df.iloc[0] = include_overlap_with.iloc[0]

    df.to_csv(file_path, index=False)
    return df


def test_validate_test_dataset_missing_columns(tmp_path):
    """Comprueba que se rechaza un dataset al que le falta una característica esperada."""
    bad_csv = tmp_path / "bad_test.csv"
    df = pd.DataFrame({"cement": [300], "water": [150], TARGET_FEATURE: [40.0]})
    df.to_csv(bad_csv, index=False)

    with pytest.raises(ValueError) as exc_info:
        validate_test_dataset(test_path=bad_csv)
    assert "faltan columnas esperadas" in str(exc_info.value).lower()


def test_validate_test_dataset_detects_nulls(tmp_path):
    """Comprueba que se rechaza un dataset con valores nulos inesperados."""
    null_csv = tmp_path / "null_test.csv"
    df = create_sample_csv(null_csv, n_rows=5)
    df.loc[1, "cement"] = np.nan
    df.to_csv(null_csv, index=False)

    with pytest.raises(ValueError) as exc_info:
        validate_test_dataset(test_path=null_csv)
    assert "valores nulos inesperados" in str(exc_info.value).lower()


def test_validate_test_dataset_detects_non_numeric(tmp_path):
    """Comprueba que se rechaza un dataset con valores no numéricos."""
    text_csv = tmp_path / "text_test.csv"
    df = create_sample_csv(text_csv, n_rows=5)
    df["cement"] = ["300", "250", "invalido", "400", "500"]
    df.to_csv(text_csv, index=False)

    with pytest.raises(ValueError) as exc_info:
        validate_test_dataset(test_path=text_csv)
    assert "tipo no numérico" in str(exc_info.value).lower()


def test_validate_test_dataset_overlap_detection(tmp_path):
    """Comprueba la detección de réplicas y solapamiento entre train y test."""
    train_path = tmp_path / "train.csv"
    test_path = tmp_path / "test.csv"

    df_train = create_sample_csv(train_path, n_rows=10)
    # Crear test set con una fila idéntica
    df_test = create_sample_csv(test_path, n_rows=10, include_overlap_with=df_train)

    _, report = validate_test_dataset(test_path=test_path, train_path=train_path)

    assert report["overlaps"]["overlap_full_rows_with_train"] >= 1
    assert len(report["overlaps"]["notes"]) > 0
    assert report["test_sha256"] is not None
    assert report["train_sha256"] is not None


def test_compute_metrics_handles_edge_cases():
    """Comprueba que compute_metrics gestiona de forma segura n < 2 y valores finitos."""
    # Caso 1: Vacío
    m_empty = compute_metrics(np.array([]), np.array([]))
    assert m_empty["r2_score"] is None

    # Caso 2: 1 sola muestra (R2 no computable matemáticamente)
    m_single = compute_metrics(np.array([35.0]), np.array([34.0]))
    assert m_single["r2_score"] is None
    assert m_single["mae_mpa"] == 1.0
    assert m_single["rmse_mpa"] == 1.0

    # Caso 3: Muestras normales
    y_true = np.array([20.0, 30.0, 40.0, 50.0])
    y_pred = np.array([21.0, 29.0, 41.0, 49.0])
    m_normal = compute_metrics(y_true, y_pred)
    assert m_normal["r2_score"] > 0.95
    assert m_normal["rmse_mpa"] == 1.0
    assert m_normal["mae_mpa"] == 1.0
    assert m_normal["nrmse"] is not None


def test_evaluate_model_end_to_end_with_dummy_model(tmp_path, capsys):
    """Comprueba el flujo completo de evaluación, medición de recursos y trazabilidad JSON."""
    train_path = tmp_path / "mock_train.csv"
    test_path = tmp_path / "mock_test.csv"
    model_path = tmp_path / "mock_winner_model.pkl"
    reports_dir = tmp_path / "reports"

    df_train = create_sample_csv(train_path, n_rows=20)
    df_test = create_sample_csv(test_path, n_rows=15, include_overlap_with=df_train)

    # Entrenar un modelo simulado offline (DummyRegressor)
    dummy_model = DummyRegressor(strategy="mean")
    dummy_model.fit(df_train[EXPECTED_FEATURES], df_train[TARGET_FEATURE])
    joblib.dump(dummy_model, model_path)

    job_name = "test_experiment_job_123"
    winner_id = "test_experiment_job_123_trial_05"

    report = evaluate_model(
        model_path=model_path,
        job_name=job_name,
        winner_id=winner_id,
        test_path=test_path,
        train_path=train_path,
        reports_dir=reports_dir
    )

    # 1. Comprobar estructura y campos requeridos
    assert report["metadata"]["job_name"] == job_name
    assert report["metadata"]["winner_model_id"] == winner_id
    assert report["metadata"]["model_sha256"] == compute_file_sha256(model_path)
    assert report["metadata"]["evaluation_timestamp"] is not None

    # 2. Comprobar recursos medidos
    assert "elapsed_seconds" in report["resource_usage"]
    assert "peak_memory_mb" in report["resource_usage"]
    assert report["resource_usage"]["peak_memory_mb"] >= 0

    # 3. Comprobar métricas globales y segmentadas
    assert "r2_score" in report["global_metrics"]
    assert "rmse_mpa" in report["global_metrics"]
    assert "age_7_days" in report["segmented_metrics"]
    assert "age_28_days" in report["segmented_metrics"]

    # 4. Comprobar archivo JSON persistido en disco
    expected_json_path = reports_dir / f"evaluation_{job_name}.json"
    assert expected_json_path.exists()

    with open(expected_json_path, "r", encoding="utf-8") as f:
        loaded_json = json.load(f)
    assert loaded_json["metadata"]["job_name"] == job_name

    # 5. Comprobar gráfico generado
    expected_plot_path = reports_dir / f"evaluation_{job_name}_plot.png"
    assert expected_plot_path.exists()

    # 6. Comprobar advertencia al sobrescribir
    evaluate_model(
        model_path=model_path,
        job_name=job_name,
        winner_id=winner_id,
        test_path=test_path,
        train_path=train_path,
        reports_dir=reports_dir
    )
    captured = capsys.readouterr()
    assert "sobrescribirá el reporte previo existente" in captured.out.lower()
