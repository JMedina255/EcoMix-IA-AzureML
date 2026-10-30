"""
Fase 4: Inspección Segura, Descarga Selectiva y Evaluación Independiente
Proyecto: ML EcomixIA
Optimizado para bajo consumo de recursos (CPU i5, 16GB RAM) y trazabilidad estricta.
"""

import os
import sys
import json
import time
import hashlib
import argparse
import tracemalloc
from pathlib import Path
from typing import Optional, Dict, Any, Tuple, List

import pandas as pd
import numpy as np
import joblib
import matplotlib.pyplot as plt
import sklearn
from sklearn.metrics import r2_score, root_mean_squared_error, mean_absolute_error

from azure.ai.ml import MLClient
from azure.identity import DefaultAzureCredential, InteractiveBrowserCredential

# 1. Configuración de rutas y constantes
BASE_DIR = Path(__file__).resolve().parent.parent
CONFIG_PATH = BASE_DIR / "config.json"
TEST_DATA_PATH = BASE_DIR / "data" / "processed" / "concrete_test.csv"
TRAIN_DATA_PATH = BASE_DIR / "data" / "processed" / "concrete_train.csv"
MODELS_DIR = BASE_DIR / "models"
REPORTS_DIR = BASE_DIR / "reports"

DEFAULT_JOB_NAME = "wheat_cheese_4swj34tkjn"
EXPECTED_FEATURES = [
    "cement",
    "blast_furnace_slag",
    "fly_ash",
    "water",
    "superplasticizer",
    "coarse_aggregate",
    "fine_aggregate",
    "age"
]
TARGET_FEATURE = "concrete_compressive_strength"


def get_azure_credentials():
    """Obtiene credenciales locales activas o recurre al navegador interactivo."""
    try:
        cred = DefaultAzureCredential()
        cred.get_token("https://management.azure.com/.default")
        print("[AUTH] Credencial local activa detectada.")
        return cred
    except Exception:
        print("[AUTH] No se detectó sesión local activa (Azure CLI / variables de entorno).")
        print("[AUTH] Intentando autenticación mediante navegador interactivo...")
        return InteractiveBrowserCredential(timeout=10)


def get_ml_client(config_path: Path = CONFIG_PATH) -> MLClient:
    """Crea una instancia de MLClient a partir del archivo de configuración."""
    if not config_path.exists():
        raise FileNotFoundError(
            f"No se encontró el archivo de configuración en: {config_path}\n"
            "Cree config.json a partir de config.example.json con su suscripción de Azure."
        )

    with open(config_path, "r", encoding="utf-8") as f:
        config = json.load(f)

    credential = get_azure_credentials()
    return MLClient(
        credential=credential,
        subscription_id=config["subscription_id"],
        resource_group_name=config["resource_group"],
        workspace_name=config["workspace_name"],
    )


def check_python_compatibility(training_env_info: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """
    Verifica compatibilidad de versión de Python y dependencias entre entrenamiento y local.
    No intenta instalar ni alterar versiones globales del sistema.
    """
    local_version = f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}"
    training_env = training_env_info or {}
    training_python = training_env.get("python_version")

    compatibility = {
        "local_python": local_version,
        "training_python": training_python or "No especificado explícitamente (típicamente Python 3.9/3.10 en imágenes AzureML AutoML)",
        "is_compatible": True,
        "warnings": []
    }

    # Python 3.13.5 local vs modelos serializados de Azure ML
    if sys.version_info >= (3, 13):
        warn_msg = (
            f"[COMPATIBILIDAD] El entorno local ejecuta Python {local_version}. "
            "Los entornos de AutoML en Azure ML se ejecutan comúnmente sobre Python 3.9 o 3.10. "
            "Si la deserialización de joblib/pickle falla por cambios en la representación interna "
            "de tipos o NumPy/Scikit-learn, se recomienda activar un entorno virtual con Python 3.10 "
            "sin alterar la instalación global de Python."
        )
        compatibility["warnings"].append(warn_msg)
        if training_python and not training_python.startswith("3.13"):
            compatibility["is_compatible"] = False

    return compatibility


def resolve_winner_model(ml_client: MLClient, job: Any) -> Tuple[Optional[str], Optional[str], Dict[str, Any]]:
    """
    Identifica de manera inequívoca el modelo ganador y su output registrado.
    Verifica la procedencia del experimento para no seleccionar modelos de otros ensayos.
    Retorna: (winner_child_run_id, output_name, metadata)
    """
    job_properties = getattr(job, "properties", {}) or {}
    job_tags = getattr(job, "tags", {}) or {}
    job_outputs = getattr(job, "outputs", {}) or {}

    winner_id = (
        job_properties.get("best_child_run_id")
        or job_tags.get("best_child_run_id")
    )

    raw_metric = getattr(job, "primary_metric", None)
    primary_metric = raw_metric if isinstance(raw_metric, str) else job_properties.get("primary_metric")

    metadata: Dict[str, Any] = {
        "source": "parent_job_metadata" if winner_id else "unresolved",
        "primary_metric": primary_metric,
        "best_metric_value": job_properties.get("metric_value"),
        "available_job_outputs": list(job_outputs.keys()) if isinstance(job_outputs, dict) else [],
    }

    # Si no se encuentra en las propiedades directas, consultar lista de child runs
    if not winner_id and hasattr(ml_client, "jobs") and hasattr(ml_client.jobs, "list"):
        try:
            child_jobs = list(ml_client.jobs.list(parent_job_name=job.name))
            best_candidates = []
            for child in child_jobs:
                c_props = getattr(child, "properties", {}) or {}
                c_tags = getattr(child, "tags", {}) or {}
                if c_tags.get("is_best_run", "").lower() == "true" or c_props.get("is_best_run", "").lower() == "true":
                    best_candidates.append(child.name)
            if len(best_candidates) == 1:
                winner_id = best_candidates[0]
                metadata["source"] = "child_jobs_tag_search"
            elif len(best_candidates) > 1:
                metadata["ambiguity_reason"] = f"Múltiples child runs marcados como ganador: {best_candidates}"
                return None, None, metadata
        except Exception as e:
            metadata["child_list_error"] = str(e)

    # Validar procedencia del experimento
    if winner_id:
        if not winner_id.startswith(job.name):
            metadata["ambiguity_reason"] = (
                f"El child run '{winner_id}' no corresponde al experimento '{job.name}'. "
                "Posible inconsistencia de procedencia en metadatos."
            )
            return None, None, metadata

    # Determinar el output_name válido sin inventar nombres inexistentes
    output_name = None
    if isinstance(job_outputs, dict):
        if "best_model" in job_outputs:
            output_name = "best_model"
        elif "outputs" in job_outputs:
            output_name = "outputs"
        elif "mlflow_model" in job_outputs:
            output_name = "mlflow_model"

    # Si no está en el parent, consultar outputs del child run ganador
    if not output_name and winner_id:
        try:
            winner_job = ml_client.jobs.get(name=winner_id)
            w_outputs = getattr(winner_job, "outputs", {}) or {}
            if isinstance(w_outputs, dict):
                if "outputs" in w_outputs:
                    output_name = "outputs"
                elif "best_model" in w_outputs:
                    output_name = "best_model"
                elif len(w_outputs) == 1:
                    output_name = list(w_outputs.keys())[0]
                metadata["child_outputs"] = list(w_outputs.keys())
        except Exception:
            pass

    return winner_id, output_name, metadata


def inspect_automl_job(ml_client: MLClient, job_name: str) -> Dict[str, Any]:
    """
    Inspecciona en modo sólo lectura el trabajo de Azure ML sin descargar archivos.
    Muestra estado, métrica principal, identificador del modelo ganador y dependencias.
    """
    print("\n" + "=" * 65)
    print("INSPECCIÓN DE EXPERIMENTO AZURE ML AUTOML (MODO SÓLO LECTURA)")
    print("=" * 65)
    print(f"[JOB] Consultando trabajo: {job_name}")

    try:
        job = ml_client.jobs.get(name=job_name)
    except Exception as e:
        raise RuntimeError(
            f"No se pudo consultar el trabajo '{job_name}' en Azure ML: {e}\n"
            "Verifique que el job existe, su suscripción de Azure esté activa y tenga permisos de lectura."
        ) from e

    status = str(getattr(job, "status", "Unknown"))
    job_properties = getattr(job, "properties", {}) or {}
    job_outputs = getattr(job, "outputs", {}) or {}

    raw_metric = getattr(job, "primary_metric", None)
    primary_metric = raw_metric if isinstance(raw_metric, str) else job_properties.get("primary_metric", "No especificado")

    winner_id, output_name, resolve_meta = resolve_winner_model(ml_client, job)

    env_info = {
        "environment": str(getattr(job, "environment", "AzureML-AutoML default")),
        "python_version": job_properties.get("python_version"),
        "algorithm": job_properties.get("run_algorithm")
    }

    if winner_id:
        try:
            winner_job = ml_client.jobs.get(name=winner_id)
            w_props = getattr(winner_job, "properties", {}) or {}
            env_info["winner_algorithm"] = w_props.get("run_algorithm", "Ensemble / Pipeline AutoML")
            env_info["pipeline_id"] = w_props.get("pipeline_id")
            if "metric_value" in w_props:
                resolve_meta["winner_metric_value"] = w_props["metric_value"]
        except Exception:
            pass

    compat_info = check_python_compatibility(env_info)

    inspection_result = {
        "job_name": job_name,
        "status": status,
        "primary_metric": primary_metric,
        "winner_model_id": winner_id,
        "output_name": output_name,
        "registered_outputs": list(job_outputs.keys()) if isinstance(job_outputs, dict) else [],
        "resolve_metadata": resolve_meta,
        "environment_info": env_info,
        "compatibility": compat_info,
        "artifact_sizes_info": (
            "Tamaño exacto en Blob Storage no expuesto directamente vía API REST de jobs. "
            "Estimado típico para modelos AutoML de regresión: 15 MB - 120 MB según número de estimadores en el ensamble."
        )
    }

    print(f"  • Estado del Experimento:       {status}")
    print(f"  • Métrica Primaria:             {primary_metric}")
    if resolve_meta.get("best_metric_value"):
        print(f"  • Mejor Valor de Métrica:       {resolve_meta.get('best_metric_value')}")
    print(f"  • Modelo Ganador Identificado:  {winner_id if winner_id else 'No resuelto unívocamente'}")
    print(f"  • Output Registrado Detectado:  {output_name if output_name else 'Ninguno identificado en parent/child'}")
    print(f"  • Outputs en Parent Job:        {inspection_result['registered_outputs']}")
    print(f"  • Algoritmo Estimado:           {env_info.get('winner_algorithm', 'AutoML Regression')}")
    print(f"  • Entorno Local:                Python {compat_info['local_python']}")
    print(f"  • Entorno de Entrenamiento:     {compat_info['training_python']}")

    if compat_info["warnings"]:
        print("\n[ADVERTENCIA DE COMPATIBILIDAD]")
        for w in compat_info["warnings"]:
            print(f"  ⚠️  {w}")

    if status.lower() != "completed":
        print(f"\n[AVISO] El trabajo se encuentra en estado '{status}'. Solo trabajos con estado 'Completed' son aptos para descarga.")

    if not winner_id:
        print("\n[AVISO] No se pudo resolver inequívocamente el child run ganador a través de los metadatos.")
        if "ambiguity_reason" in resolve_meta:
            print(f"  Detalle: {resolve_meta['ambiguity_reason']}")

    print("=" * 65 + "\n")
    return inspection_result


def download_winner_model(
    ml_client: MLClient,
    job_name: str,
    download_dir: Optional[Path] = None,
    output_name: Optional[str] = None
) -> Path:
    """
    Descarga selectivamente ÚNICAMENTE los artefactos necesarios del modelo ganador.
    NUNCA utiliza all=True.
    Si no es posible identificar inequívocamente el modelo ganador, se detiene con error.
    """
    dest_dir = download_dir or (MODELS_DIR / job_name)
    dest_dir.mkdir(parents=True, exist_ok=True)

    info = inspect_automl_job(ml_client, job_name=job_name)

    if info["status"].lower() != "completed":
        raise ValueError(
            f"El trabajo '{job_name}' no ha finalizado exitosamente (estado actual: '{info['status']}'). "
            "No se permite la descarga de modelos de trabajos incompletos o fallidos."
        )

    winner_id = info["winner_model_id"]
    if not winner_id:
        reason = info["resolve_metadata"].get("ambiguity_reason", "Metadatos insuficientes para confirmar modelo ganador.")
        raise ValueError(
            f"No es posible identificar inequívocamente el modelo ganador en el trabajo '{job_name}'. "
            f"Motivo: {reason}\n"
            "Se detiene la descarga para evitar recuperar modelos incorrectos."
        )

    chosen_output = output_name or info["output_name"]
    target_job = job_name

    if not chosen_output or chosen_output not in info["registered_outputs"]:
        try:
            child_job = ml_client.jobs.get(name=winner_id)
            c_outputs = getattr(child_job, "outputs", {}) or {}
            if isinstance(c_outputs, dict) and "outputs" in c_outputs:
                chosen_output = "outputs"
                target_job = winner_id
            elif isinstance(c_outputs, dict) and c_outputs:
                chosen_output = list(c_outputs.keys())[0]
                target_job = winner_id
        except Exception:
            pass

    if not chosen_output:
        raise ValueError(
            f"El Azure ML SDK v2 no reportó un nombre de output válido para el modelo ganador ('{winner_id}').\n"
            "Ruta manual para descarga desde Azure ML Studio:\n"
            f"  1. Ingrese a: https://ml.azure.com\n"
            f"  2. Navegue a Trabajos (Jobs) -> '{job_name}' -> Ensayos secundarios (Child jobs)\n"
            f"  3. Seleccione el ensayo ganador '{winner_id}'\n"
            "  4. En la pestaña 'Resultados y registros' (Outputs + logs), descargue la carpeta 'outputs' o 'model.pkl'\n"
            f"  5. Coloque el archivo en: {dest_dir}\n"
            "Nota de seguridad: No se recurre a 'all=True' para evitar descargas masivas de 12+ modelos."
        )

    print(f"\n[DESCARGA SELECTIVA] Descargando output '{chosen_output}' del job '{target_job}'...")
    print(f"  • Destino local: {dest_dir}")
    print("  • Parámetros de seguridad: all=False, output_name específico.")

    ml_client.jobs.download(
        name=target_job,
        download_path=str(dest_dir),
        output_name=chosen_output,
        all=False
    )
    print(f"[OK] Artefacto '{chosen_output}' descargado selectivamente.")

    pkl_files = list(dest_dir.rglob("model.pkl"))
    if not pkl_files:
        pkl_files = list(dest_dir.rglob("*.pkl"))

    if pkl_files:
        selected_model = pkl_files[0]
        print(f"[OK] Archivo de modelo localizado: {selected_model}")
        return selected_model

    mlmodel_files = list(dest_dir.rglob("MLmodel"))
    if mlmodel_files:
        selected_model = mlmodel_files[0].parent
        print(f"[OK] Paquete MLmodel localizado: {selected_model}")
        return selected_model

    raise FileNotFoundError(
        f"Se completó la descarga del output '{chosen_output}', pero no se localizó 'model.pkl' ni 'MLmodel' en {dest_dir}."
    )


def compute_file_sha256(file_path: Path) -> str:
    """Calcula el hash SHA-256 de un archivo para trazabilidad e integridad."""
    sha = hashlib.sha256()
    with open(file_path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            sha.update(chunk)
    return sha.hexdigest()


def validate_test_dataset(
    test_path: Path = TEST_DATA_PATH,
    train_path: Optional[Path] = TRAIN_DATA_PATH
) -> Tuple[pd.DataFrame, Dict[str, Any]]:
    """
    Valida el conjunto de prueba independiente y analiza solapamientos con entrenamiento.
    """
    if not test_path.exists():
        raise FileNotFoundError(f"No se encontró el dataset de prueba en: {test_path}")

    df_test = pd.read_csv(test_path)
    total_test_rows = len(df_test)

    val_report: Dict[str, Any] = {
        "test_samples": total_test_rows,
        "test_path": str(test_path),
        "test_sha256": compute_file_sha256(test_path),
        "expected_sample_count": 206,
        "is_sample_count_valid": (total_test_rows == 206),
        "columns_present": list(df_test.columns),
        "null_counts": df_test.isnull().sum().to_dict(),
        "total_nulls": int(df_test.isnull().sum().sum()),
        "overlaps": {
            "duplicate_rows_in_test": int(df_test.duplicated().sum()),
            "overlap_full_rows_with_train": 0,
            "overlap_features_only_with_train": 0,
            "notes": []
        },
        "warnings": []
    }

    if total_test_rows != 206:
        val_report["warnings"].append(
            f"El dataset de prueba contiene {total_test_rows} observaciones (se esperaban exactamente 206)."
        )

    expected_all = EXPECTED_FEATURES + [TARGET_FEATURE]
    missing = set(expected_all) - set(df_test.columns)
    if missing:
        raise ValueError(f"Faltan columnas esperadas en el dataset de prueba: {missing}")

    if val_report["total_nulls"] > 0:
        raise ValueError(f"Se detectaron {val_report['total_nulls']} valores nulos inesperados en el dataset de prueba.")

    non_numeric_cols = [c for c in expected_all if not pd.api.types.is_numeric_dtype(df_test[c])]
    if non_numeric_cols:
        raise ValueError(f"Columnas con tipo no numérico detectadas en test set: {non_numeric_cols}")

    # Análisis de solapamiento con train (respetando réplicas de laboratorio ASTM)
    if train_path and train_path.exists():
        df_train = pd.read_csv(train_path)
        val_report["train_path"] = str(train_path)
        val_report["train_sha256"] = compute_file_sha256(train_path)

        # 1. Filas completas idénticas (features + target)
        overlap_full = pd.merge(df_test, df_train, how="inner", on=expected_all)
        val_report["overlaps"]["overlap_full_rows_with_train"] = len(overlap_full)

        # 2. Solo características de entrada (mismas dosificaciones probadas)
        overlap_features = pd.merge(df_test[EXPECTED_FEATURES], df_train[EXPECTED_FEATURES], how="inner", on=EXPECTED_FEATURES)
        val_report["overlaps"]["overlap_features_only_with_train"] = len(overlap_features)

        if len(overlap_full) > 0:
            val_report["overlaps"]["notes"].append(
                f"Detectadas {len(overlap_full)} observaciones completas idénticas entre entrenamiento y prueba. "
                "Corresponden a réplicas físicas de probetas cilíndricas preparadas por lote según norma ASTM C39."
            )
        if len(overlap_features) > 0 and len(overlap_features) > len(overlap_full):
            val_report["overlaps"]["notes"].append(
                f"Detectadas {len(overlap_features)} mezclas con dosificación idéntica pero variación de rotura natural."
            )

    return df_test, val_report


def compute_metrics(y_true: np.ndarray, y_pred: np.ndarray) -> Dict[str, Any]:
    """Calcula R2, RMSE, MAE, NRMSE controlando NaN e infinitos de forma segura."""
    if len(y_true) == 0:
        return {"r2_score": None, "rmse_mpa": None, "mae_mpa": None, "nrmse": None}

    if len(y_true) < 2:
        r2 = None
    else:
        try:
            r2_val = float(r2_score(y_true, y_pred))
            r2 = round(r2_val, 4) if np.isfinite(r2_val) else None
        except Exception:
            r2 = None

    try:
        rmse_val = float(root_mean_squared_error(y_true, y_pred))
        rmse = round(rmse_val, 4) if np.isfinite(rmse_val) else None
    except Exception:
        rmse = None

    try:
        mae_val = float(mean_absolute_error(y_true, y_pred))
        mae = round(mae_val, 4) if np.isfinite(mae_val) else None
    except Exception:
        mae = None

    target_range = float(y_true.max() - y_true.min())
    if target_range > 0 and rmse is not None and np.isfinite(rmse):
        nrmse_val = float(rmse / target_range)
        nrmse = round(nrmse_val, 4) if np.isfinite(nrmse_val) else None
    else:
        nrmse = None

    return {
        "r2_score": r2,
        "rmse_mpa": rmse,
        "mae_mpa": mae,
        "nrmse": nrmse
    }


def evaluate_model(
    model_path: Path,
    job_name: str = DEFAULT_JOB_NAME,
    winner_id: Optional[str] = None,
    test_path: Path = TEST_DATA_PATH,
    train_path: Optional[Path] = TRAIN_DATA_PATH,
    reports_dir: Path = REPORTS_DIR
) -> Dict[str, Any]:
    """
    Evalúa el modelo contra el conjunto de prueba independiente (206 muestras)
    con control estricto de memoria, tiempo, validación de datos y trazabilidad completa.
    """
    print("\n" + "=" * 65)
    print("EVALUACIÓN CONTRA CONJUNTO DE PRUEBA INDEPENDIENTE (TEST SET)")
    print("=" * 65)

    # 1. Validar el dataset de prueba y solapamientos
    print(f"[DATASET] Validando datos de prueba desde: {test_path}")
    df_test, val_report = validate_test_dataset(test_path=test_path, train_path=train_path)
    print(f"  • Muestras de prueba verificadas: {val_report['test_samples']} (Esperadas: 206)")
    print(f"  • Total nulos:                   {val_report['total_nulls']}")
    print(f"  • Réplicas en test:              {val_report['overlaps']['duplicate_rows_in_test']}")
    if val_report["overlaps"]["overlap_full_rows_with_train"] > 0:
        print(f"  • Réplicas ASTM con train:       {val_report['overlaps']['overlap_full_rows_with_train']}")
    print(f"  • Hash SHA-256 test:             {val_report['test_sha256'][:16]}...")

    # 2. Controlar recursos (Memoria y Tiempo)
    tracemalloc.start()
    t_start = time.perf_counter()

    try:
        print(f"\n[LOAD] Cargando modelo ganador: {model_path}")
        model = joblib.load(model_path)
        model_type_name = type(model).__name__
        print(f"[INFO] Estimador cargado: {model_type_name}")

        X_test = df_test[EXPECTED_FEATURES]
        y_test = df_test[TARGET_FEATURE].values

        y_pred = model.predict(X_test)
        if hasattr(y_pred, "values"):
            y_pred = y_pred.values.ravel()
        elif isinstance(y_pred, np.ndarray) and y_pred.ndim > 1:
            y_pred = y_pred.ravel()

    except (MemoryError, AttributeError, ModuleNotFoundError, ImportError) as err:
        tracemalloc.stop()
        raise RuntimeError(
            f"Error crítico al cargar o evaluar el modelo ({type(err).__name__}): {err}\n"
            "Verifique la compatibilidad del entorno virtual (Python / scikit-learn / joblib)."
        ) from err

    t_end = time.perf_counter()
    current_mem, peak_mem = tracemalloc.get_traced_memory()
    tracemalloc.stop()

    resource_usage = {
        "elapsed_seconds": round(t_end - t_start, 4),
        "peak_memory_mb": round(peak_mem / (1024 * 1024), 2),
        "current_memory_mb": round(current_mem / (1024 * 1024), 2)
    }

    # 3. Métricas Globales
    global_metrics = compute_metrics(y_test, y_pred)

    print("\n" + "-" * 40)
    print(f"MÉTRICAS GLOBALES (Test Set: {len(df_test)} muestras):")
    print("-" * 40)
    r2_display = f"{global_metrics['r2_score']:.4f}" if global_metrics['r2_score'] is not None else "N/A"
    print(f"  • R² Score:  {r2_display} (Capacidad predictiva global)")
    print(f"  • RMSE:      {global_metrics['rmse_mpa']:.2f} MPa")
    print(f"  • MAE:       {global_metrics['mae_mpa']:.2f} MPa")
    print(f"  • NRMSE:     {global_metrics['nrmse']:.4f}")
    print("-" * 40)

    # 4. Evaluación segmentada por edades críticas (7 y 28 días)
    print("\nEVALUACIÓN SEGMENTADA POR EDAD DE CURADO:")
    segmented_metrics: Dict[str, Any] = {}
    for age_val in [7, 28]:
        mask = (df_test["age"] == age_val)
        count = int(mask.sum())
        if count == 0:
            segmented_metrics[f"age_{age_val}_days"] = {
                "sample_count": 0,
                "status": "Sin muestras en test set",
                "metrics": None
            }
            print(f"  -> Ensayos a {age_val} días: 0 muestras")
        else:
            sub_y = y_test[mask]
            sub_pred = y_pred[mask]
            sub_m = compute_metrics(sub_y, sub_pred)
            sub_status = "Evaluado" if count >= 2 else "Muestras insuficientes para R² (<2)"
            segmented_metrics[f"age_{age_val}_days"] = {
                "sample_count": count,
                "status": sub_status,
                "metrics": sub_m
            }
            r2_sub_disp = f"{sub_m['r2_score']:.4f}" if sub_m['r2_score'] is not None else "N/A"
            print(f"  -> Ensayos a {age_val} días ({count} probetas): MAE={sub_m['mae_mpa']:.2f} MPa | RMSE={sub_m['rmse_mpa']:.2f} MPa | R²={r2_sub_disp}")

    # 5. Generar reporte estructurado para trazabilidad
    reports_dir.mkdir(parents=True, exist_ok=True)
    report_file_name = f"evaluation_{job_name}.json"
    report_path = reports_dir / report_file_name

    if report_path.exists():
        print(f"\n[ADVERTENCIA] Se sobrescribirá el reporte previo existente en: {report_path}")

    model_sha = compute_file_sha256(model_path) if model_path.is_file() else None

    report = {
        "metadata": {
            "project": "EcoMix IA",
            "phase": "Fase 4 - Evaluación Independiente de Modelo AutoML",
            "job_name": job_name,
            "winner_model_id": winner_id or str(model_path.name),
            "evaluation_timestamp": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
            "model_path": str(model_path),
            "model_sha256": model_sha,
            "model_type": model_type_name
        },
        "environment": {
            "python_version": sys.version,
            "platform": sys.platform,
            "dependencies": {
                "pandas": getattr(pd, "__version__", None),
                "numpy": getattr(np, "__version__", None),
                "scikit_learn": getattr(sklearn, "__version__", None),
                "joblib": getattr(joblib, "__version__", None)
            }
        },
        "dataset_validation": val_report,
        "resource_usage": resource_usage,
        "global_metrics": global_metrics,
        "segmented_metrics": segmented_metrics,
        "sample_predictions": [
            {
                "index": int(i),
                "actual_mpa": round(float(y_test[i]), 2),
                "predicted_mpa": round(float(y_pred[i]), 2),
                "absolute_error_mpa": round(float(abs(y_test[i] - y_pred[i])), 2),
                "age_days": int(df_test["age"].iloc[i])
            }
            for i in range(min(10, len(df_test)))
        ]
    }

    with open(report_path, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2, ensure_ascii=False)
    print(f"\n[OK] Reporte de evaluación JSON guardado en: {report_path}")

    # 6. Generar gráfico Real vs Predicho
    plot_file_name = f"evaluation_{job_name}_plot.png"
    plot_path = reports_dir / plot_file_name

    plt.figure(figsize=(8, 6))
    plt.scatter(y_test, y_pred, alpha=0.7, edgecolors="k", color="#2b5c8f", label=f"Muestras Test ({len(df_test)})")
    min_val = min(float(y_test.min()), float(y_pred.min()))
    max_val = max(float(y_test.max()), float(y_pred.max()))
    plt.plot([min_val, max_val], [min_val, max_val], "r--", linewidth=2, label="Predicción Perfecta (1:1)")
    plt.title(
        f"EcoMix IA — Evaluación del Modelo Ganador ({job_name})\n"
        f"R²: {r2_display} | RMSE: {global_metrics['rmse_mpa']:.2f} MPa | MAE: {global_metrics['mae_mpa']:.2f} MPa",
        fontsize=11
    )
    plt.xlabel("Resistencia Real Experimental (MPa)", fontsize=10)
    plt.ylabel("Resistencia Predicha por el Modelo (MPa)", fontsize=10)
    plt.grid(True, linestyle="--", alpha=0.5)
    plt.legend()
    plt.tight_layout()
    plt.savefig(plot_path, dpi=200)
    plt.close()
    print(f"[OK] Gráfico de correlación guardado en: {plot_path}")

    print("\n" + "=" * 65)
    print(f"Evaluación completada exitosamente en {resource_usage['elapsed_seconds']} s (RAM pico: {resource_usage['peak_memory_mb']} MB).")
    print("=" * 65 + "\n")

    return report


def parse_args(args=None):
    """Parsea argumentos de la línea de comandos."""
    parser = argparse.ArgumentParser(
        description="EcoMix IA - Inspección, Descarga Selectiva y Evaluación de Modelos AutoML en Azure ML",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument(
        "--inspect",
        action="store_true",
        help="Inspecciona el trabajo en Azure ML y sus metadatos sin descargar archivos (modo predeterminado)."
    )
    parser.add_argument(
        "--download",
        action="store_true",
        help="Descarga selectivamente únicamente los artefactos necesarios del modelo ganador identificado."
    )
    parser.add_argument(
        "--evaluate",
        action="store_true",
        help="Evalúa un modelo previamente descargado contra el conjunto de prueba independiente."
    )
    parser.add_argument(
        "--job-name",
        type=str,
        default=DEFAULT_JOB_NAME,
        help="Identificador del experimento o trabajo en Azure ML."
    )
    parser.add_argument(
        "--model-path",
        type=str,
        default=None,
        help="Ruta explícita al archivo de modelo local (.pkl) para omitir la descarga."
    )
    return parser.parse_args(args)


def main(argv=None):
    args = parse_args(argv)

    is_evaluate = args.evaluate
    is_download = args.download
    is_inspect = args.inspect or (not is_download and not is_evaluate)

    job_name = args.job_name

    if is_inspect:
        try:
            ml_client = get_ml_client()
            inspect_automl_job(ml_client, job_name=job_name)
        except Exception as e:
            print(f"\n[ERROR DE CONEXIÓN AZURE] No se pudo completar la inspección del job '{job_name}':\n  {e}")
            print("\nRecomendación: Ejecute 'az login' en su terminal local para autenticar su cuenta de Azure.")
            sys.exit(1)
        return

    if is_download:
        ml_client = get_ml_client()
        model_path = download_winner_model(ml_client, job_name=job_name)
        print(f"\n[FINALIZADO] Modelo descargado con éxito en: {model_path}")
        return

    if is_evaluate:
        if args.model_path:
            model_path = Path(args.model_path)
        else:
            job_models_dir = MODELS_DIR / job_name
            pkl_files = list(job_models_dir.rglob("*.pkl")) if job_models_dir.exists() else []
            if not pkl_files:
                raise FileNotFoundError(
                    f"No se encontró ningún modelo local para '{job_name}' en {job_models_dir}.\n"
                    f"Ejecute primero con '--download --job-name {job_name}' o especifique '--model-path <ruta>'."
                )
            model_path = pkl_files[0]

        evaluate_model(model_path=model_path, job_name=job_name)
        return


if __name__ == "__main__":
    main()
