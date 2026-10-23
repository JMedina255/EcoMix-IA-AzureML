"""
Fase 4: Descarga del Mejor Modelo de AutoML y Evaluación Independiente
Proyecto: ML EcomixIA
Evalúa el modelo ganador contra el conjunto de prueba independiente (206 filas).
"""

import os
import sys
import json
import glob
from pathlib import Path
import pandas as pd
import numpy as np
import joblib
import matplotlib.pyplot as plt
from sklearn.metrics import r2_score, root_mean_squared_error, mean_absolute_error

from azure.ai.ml import MLClient
from azure.identity import DefaultAzureCredential, InteractiveBrowserCredential

# 1. Configuración de rutas
BASE_DIR = Path(__file__).resolve().parent.parent
CONFIG_PATH = BASE_DIR / "config.json"
TEST_DATA_PATH = BASE_DIR / "data" / "processed" / "concrete_test.csv"
MODELS_DIR = BASE_DIR / "models"
REPORTS_DIR = BASE_DIR / "reports"

DEFAULT_JOB_NAME = "wheat_cheese_4swj34tkjn"


def get_azure_credentials():
    """Obtiene credenciales activas o recurre al navegador interactivo."""
    try:
        cred = DefaultAzureCredential()
        cred.get_token("https://management.azure.com/.default")
        print("[AUTH] Credencial local detectada.")
        return cred
    except Exception:
        print("[AUTH] Abriendo navegador para autenticación en Azure...")
        return InteractiveBrowserCredential()


def download_best_model(ml_client: MLClient, job_name: str) -> Path:
    """
    Descarga los artefactos del trabajo completado de Azure ML y localiza el archivo model.pkl.
    """
    download_dir = MODELS_DIR / job_name
    download_dir.mkdir(parents=True, exist_ok=True)

    print(f"\n[DOWNLOAD] Descargando artefactos del job '{job_name}' desde Azure ML...")
    ml_client.jobs.download(
        name=job_name,
        download_path=str(download_dir),
        all=True
    )
    print(f"[OK] Artefactos descargados en: {download_dir}")

    # Buscar el archivo model.pkl o MLmodel recursivamente
    pkl_files = list(download_dir.rglob("model.pkl"))
    if not pkl_files:
        # Buscar en subdirectorios
        pkl_files = list(download_dir.rglob("*.pkl"))

    if not pkl_files:
        raise FileNotFoundError(f"No se encontró 'model.pkl' dentro de {download_dir}")

    # Priorizar modelos en 'best_model' o 'outputs'
    best_file = pkl_files[0]
    for p in pkl_files:
        if "best" in str(p).lower() or "output" in str(p).lower():
            best_file = p
            break

    print(f"[OK] Modelo seleccionado localizado: {best_file}")
    return best_file


def evaluate_model(model_path: Path):
    """
    Carga el modelo y evalúa su desempeño contra el conjunto de prueba independiente.
    """
    print("\n" + "=" * 60)
    print("EVALUACIÓN CONTRA CONJUNTO DE PRUEBA INDEPENDIENTE (TEST SET)")
    print("=" * 60)

    # 1. Cargar el modelo
    print(f"[LOAD] Cargando modelo desde: {model_path}")
    model = joblib.load(model_path)
    print(f"[INFO] Tipo de modelo: {type(model).__name__}")

    # 2. Cargar datos de prueba
    if not TEST_DATA_PATH.exists():
        raise FileNotFoundError(f"No se encontró el dataset de prueba en: {TEST_DATA_PATH}")

    df_test = pd.read_csv(TEST_DATA_PATH)
    target_col = "concrete_compressive_strength"
    X_test = df_test.drop(columns=[target_col])
    y_test = df_test[target_col]

    print(f"[INFO] Datos de prueba cargados: {len(df_test)} observaciones independientes.")

    # 3. Realizar predicciones
    y_pred = model.predict(X_test)

    # Si la salida es 2D o DataFrame, aplanar
    if hasattr(y_pred, "values"):
        y_pred = y_pred.values.ravel()
    elif isinstance(y_pred, np.ndarray) and y_pred.ndim > 1:
        y_pred = y_pred.ravel()

    # 4. Métricas globales
    r2 = float(r2_score(y_test, y_pred))
    rmse = float(root_mean_squared_error(y_test, y_pred))
    mae = float(mean_absolute_error(y_test, y_pred))
    nrmse = float(rmse / (y_test.max() - y_test.min()))

    print("\n" + "-" * 40)
    print("MÉTRICAS GLOBALES EN TEST SET (206 muestras):")
    print("-" * 40)
    print(f"  • R² Score (Capacidad predictiva):  {r2:.4f}  (Ideal > 0.85)")
    print(f"  • RMSE (Error cuadrático medio):   {rmse:.2f} MPa")
    print(f"  • MAE (Error absoluto medio):      {mae:.2f} MPa")
    print(f"  • NRMSE (RMSE Normalizado):        {nrmse:.4f}")
    print("-" * 40)

    # 5. Evaluación segmentada por edades críticas (7 y 28 días)
    print("\nEVALUACIÓN SEGMENTADA POR EDAD DE CURADO:")
    for age_val in [7, 28]:
        mask = (df_test["age"] == age_val)
        count = int(mask.sum())
        if count > 0:
            sub_r2 = float(r2_score(y_test[mask], y_pred[mask])) if count > 1 else float("nan")
            sub_mae = float(mean_absolute_error(y_test[mask], y_pred[mask]))
            sub_rmse = float(root_mean_squared_error(y_test[mask], y_pred[mask]))
            print(f"  -> Ensayos a {age_val} días ({count} probetas en test): MAE={sub_mae:.2f} MPa | RMSE={sub_rmse:.2f} MPa")

    # 6. Guardar reporte y resultados
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    report = {
        "job_name": DEFAULT_JOB_NAME,
        "model_file": str(model_path.name),
        "test_samples_count": len(df_test),
        "metrics": {
            "r2_score": round(r2, 4),
            "rmse_mpa": round(rmse, 2),
            "mae_mpa": round(mae, 2),
            "nrmse": round(nrmse, 4)
        },
        "sample_predictions": [
            {
                "index": int(i),
                "actual_mpa": round(float(y_test.iloc[i]), 2),
                "predicted_mpa": round(float(y_pred[i]), 2),
                "absolute_error_mpa": round(float(abs(y_test.iloc[i] - y_pred[i])), 2),
                "age_days": int(df_test["age"].iloc[i])
            }
            for i in range(min(10, len(df_test)))
        ]
    }

    report_json_path = REPORTS_DIR / "evaluation_results.json"
    with open(report_json_path, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2, ensure_ascii=False)
    print(f"\n[OK] Reporte de evaluación guardado en: {report_json_path}")

    # 7. Generar gráfico Real vs Predicho
    plot_path = REPORTS_DIR / "evaluation_plot.png"
    plt.figure(figsize=(8, 6))
    plt.scatter(y_test, y_pred, alpha=0.7, edgecolors="k", color="#2b5c8f", label="Muestras de Test")
    min_val = min(y_test.min(), y_pred.min())
    max_val = max(y_test.max(), y_pred.max())
    plt.plot([min_val, max_val], [min_val, max_val], "r--", linewidth=2, label="Predicción Perfecta (1:1)")
    plt.title(f"EcoMix IA - Evaluación del Mejor Modelo\nR²: {r2:.4f} | RMSE: {rmse:.2f} MPa | MAE: {mae:.2f} MPa", fontsize=12)
    plt.xlabel("Resistencia Real Experimental (MPa)", fontsize=11)
    plt.ylabel("Resistencia Predicha por el Modelo (MPa)", fontsize=11)
    plt.grid(True, linestyle="--", alpha=0.5)
    plt.legend()
    plt.tight_layout()
    plt.savefig(plot_path, dpi=200)
    plt.close()
    print(f"[OK] Gráfico de correlación guardado en: {plot_path}")

    print("\n" + "=" * 60)
    print("Fase 4 completada con éxito.")
    print("=" * 60)


def main():
    job_name = sys.argv[1] if len(sys.argv) > 1 else DEFAULT_JOB_NAME

    with open(CONFIG_PATH, "r", encoding="utf-8") as f:
        config = json.load(f)

    credential = get_azure_credentials()
    ml_client = MLClient(
        credential=credential,
        subscription_id=config["subscription_id"],
        resource_group_name=config["resource_group"],
        workspace_name=config["workspace_name"],
    )

    model_path = download_best_model(ml_client, job_name=job_name)
    evaluate_model(model_path)


if __name__ == "__main__":
    main()
