#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
scripts/verify_model_load.py — Prueba Controlada de Carga y Firma del Modelo AutoML.

Separa explícitamente:
  1. Validación de firma y metadatos (8 variables requeridas).
  2. Carga y deserialización real mediante mlflow.sklearn.load_model().
  3. Comprobación del método predict() y ejecución en seco (dry-run).

Proporciona modos diferenciados:
  --signature-only: valida exclusivamente la firma sin intentar deserializar.
  --require-load: exige carga real exitosa (falla con código != 0 si falta runtime).
"""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import sys
from typing import Any, Dict, List, Optional, Tuple

import mlflow
import mlflow.sklearn
import numpy as np
import pandas as pd
import yaml

# Silenciar mensajes informativos de tracing de MLflow
os.environ["MLFLOW_DISABLE_AGENT_HINT"] = "1"

BASE_DIR = Path(__file__).resolve().parent.parent
DEFAULT_MODELS_DIR = BASE_DIR / "models"

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


def find_mlmodel_dir(base_models_dir: Path = DEFAULT_MODELS_DIR) -> Optional[Path]:
    """Busca dinámicamente el directorio que contiene el archivo MLmodel."""
    if not base_models_dir.exists():
        return None

    mlmodel_files = list(base_models_dir.rglob("MLmodel"))
    if mlmodel_files:
        for ml_file in mlmodel_files:
            if "mlflow-model" in ml_file.parts:
                return ml_file.parent
        return mlmodel_files[0].parent

    return None


def verify_model_signature(model_dir: Path) -> Tuple[bool, List[str], Optional[str]]:
    """
    1. VALIDACIÓN DE FIRMA Y METADATOS:
    Verifica que el archivo MLmodel contenga la firma de entrada con las 8 variables esperadas.
    Retorna (es_valido, variables_encontradas, mensaje_error).
    No deserializa ningún binario.
    """
    mlmodel_path = model_dir / "MLmodel"
    if not mlmodel_path.exists():
        return False, [], f"No se encontró el archivo MLmodel en '{model_dir}'."

    try:
        with open(mlmodel_path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f)

        signature = data.get("signature", {})
        if not signature:
            return False, [], "El archivo MLmodel no contiene la sección 'signature'."

        raw_inputs = signature.get("inputs", [])
        if isinstance(raw_inputs, str):
            inputs_list = json.loads(raw_inputs)
        elif isinstance(raw_inputs, list):
            inputs_list = raw_inputs
        else:
            inputs_list = []

        found_features = [inp.get("name") for inp in inputs_list if isinstance(inp, dict)]

        # Comparar con EXPECTED_FEATURES (ignorando orden para detección de faltantes)
        missing = [f for f in EXPECTED_FEATURES if f not in found_features]
        extra = [f for f in found_features if f not in EXPECTED_FEATURES]

        if missing or extra:
            err_msg = f"Discrepancia en firma del modelo. Faltantes: {missing}, Inesperadas: {extra}."
            return False, found_features, err_msg

        return True, found_features, None
    except Exception as e:
        return False, [], f"Error al parsear MLmodel: {e}"


def load_model_artifact(model_dir: Path) -> Tuple[Optional[Any], Optional[str], Optional[str]]:
    """
    2. CARGA REAL Y DESERIALIZACIÓN:
    Intenta deserializar el modelo usando mlflow.sklearn.load_model().
    Retorna (estimador_cargado, error_string, recomendacion_entorno).
    """
    try:
        loaded_model = mlflow.sklearn.load_model(str(model_dir))
        return loaded_model, None, None
    except ModuleNotFoundError as mnf:
        err = (
            f"Falta el módulo especializado '{mnf.name}'. "
            "El artefacto VotingEnsemble de Azure AutoML contiene clases dependientes de "
            "'azureml.training.tabular' o 'azureml.automl.runtime', las cuales requieren "
            "Python 3.10 y el runtime especializado de Azure ML."
        )
        rec = (
            "Para deserializar este modelo, utilice la imagen curada oficial "
            "'mcr.microsoft.com/azureml/curated/ai-ml-automl:41' o ejecute la evaluación en "
            "Azure ML Workspace (Compute Instance o Job)."
        )
        return None, err, rec
    except Exception as e:
        err = f"Error al deserializar el modelo ({type(e).__name__}): {e}"
        return None, err, None


def create_dummy_sample() -> pd.DataFrame:
    """Crea una observación de prueba con las 8 características numéricas."""
    sample_data = {
        "cement": [300.0],
        "blast_furnace_slag": [50.0],
        "fly_ash": [0.0],
        "water": [180.0],
        "superplasticizer": [2.5],
        "coarse_aggregate": [1000.0],
        "fine_aggregate": [750.0],
        "age": [28]
    }
    return pd.DataFrame(sample_data, columns=EXPECTED_FEATURES)


def verify_model_prediction(
    estimator: Any,
    dummy_df: Optional[pd.DataFrame] = None
) -> Tuple[bool, Optional[float], Optional[str]]:
    """
    3. COMPROBACIÓN DEL MÉTODO PREDICT:
    Verifica que el estimador implemente predict() y responda a una muestra sintética.
    Retorna (exitoso, valor_predicho, mensaje_error).
    """
    if not hasattr(estimator, "predict"):
        return False, None, f"El objeto cargado ({type(estimator).__name__}) no implementa el método predict()."

    if dummy_df is None:
        dummy_df = create_dummy_sample()

    try:
        preds = estimator.predict(dummy_df)
        if isinstance(preds, (np.ndarray, list, pd.Series)) and len(preds) == 1:
            return True, float(preds[0]), None
        return True, None, None
    except Exception as e:
        return False, None, f"Fallo al ejecutar predict(): {e}"


def run_verification_pipeline(
    model_dir: Path,
    check_signature: bool = True,
    attempt_load: bool = True,
    test_predict: bool = True
) -> Dict[str, Any]:
    """
    Ejecuta el pipeline completo o selectivo de verificación.
    """
    report: Dict[str, Any] = {
        "model_dir": str(model_dir),
        "signature_verified": False,
        "features_found": [],
        "signature_error": None,
        "load_attempted": attempt_load,
        "load_successful": False,
        "estimator_type": None,
        "has_predict_method": False,
        "predict_attempted": test_predict if attempt_load else False,
        "predict_successful": False,
        "dry_run_prediction": None,
        "status": "pending",
        "error": None,
        "environment_recommendation": None
    }

    # 1. Validación de firma
    if check_signature:
        sig_ok, features, sig_err = verify_model_signature(model_dir)
        report["signature_verified"] = sig_ok
        report["features_found"] = features
        report["signature_error"] = sig_err

        if not sig_ok:
            report["status"] = "signature_mismatch"
            report["error"] = f"Validación de firma fallida: {sig_err}"
            return report

    # Si solo se solicitó firma, concluir aquí
    if not attempt_load:
        report["status"] = "signature_verified_only"
        return report

    # 2. Carga y deserialización
    estimator, load_err, rec = load_model_artifact(model_dir)
    if load_err:
        report["load_successful"] = False
        report["status"] = "blocked_by_missing_dependency" if rec else "load_failed"
        report["error"] = load_err
        report["environment_recommendation"] = rec
        return report

    report["load_successful"] = True
    report["estimator_type"] = type(estimator).__name__
    report["has_predict_method"] = hasattr(estimator, "predict")

    # 3. Comprobación de predict
    if test_predict:
        pred_ok, pred_val, pred_err = verify_model_prediction(estimator)
        report["predict_successful"] = pred_ok
        report["dry_run_prediction"] = pred_val
        if not pred_ok:
            report["status"] = "predict_failed"
            report["error"] = pred_err
            return report

    report["status"] = "verified"
    return report


def load_and_verify_model(
    model_dir: Path,
    dry_run_predict: bool = True
) -> Dict[str, Any]:
    """
    Función de compatibilidad que invoca run_verification_pipeline con attempt_load=True.
    """
    return run_verification_pipeline(
        model_dir=model_dir,
        check_signature=True,
        attempt_load=True,
        test_predict=dry_run_predict
    )


def print_load_report(report: Dict[str, Any]) -> None:
    """Imprime el resultado de la prueba en consola."""
    print("=" * 68)
    print(" ECOMIX IA — PRUEBA CONTROLADA DE MODELO (Fase 4.4-A)")
    print("=" * 68)
    print(f" Directorio del Modelo: {report['model_dir']}")
    print(f" Firma (8 Variables):   {'[CORRECTA]' if report['signature_verified'] else ('[NO EVALUADA]' if not report['features_found'] else '[FALLO]')}")
    if report["features_found"]:
        print(f" Variables Detectadas:  {', '.join(report['features_found'])}")
    print("-" * 68)

    if not report["load_attempted"]:
        print(f" [OK] MODO: SOLO FIRMA VERIFICADA (Sin deserialización de binarios).")
    elif report["load_successful"]:
        print(" [OK] CARGA EXITOSA DEL ESTIMADOR")
        print(f" Estimador:             {report['estimator_type']}")
        print(f" Método predict():      {'Disponible' if report['has_predict_method'] else 'No disponible'}")
        if report["dry_run_prediction"] is not None:
            print(f" Predicción Sintética:  {report['dry_run_prediction']} MPa (1 muestra sintética)")
        print(f" Estado General:        VERIFICADO ({report['status']})")
    else:
        print(f" [AVISO] ESTADO DE CARGA: {report['status'].upper()}")
        print(f" Detalle:               {report['error']}")
        if report.get("environment_recommendation"):
            print(f"\n [RECOMENDACIÓN TÉCNICA]:")
            print(f" {report['environment_recommendation']}")
    print("=" * 68)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Prueba controlada de carga y firma del modelo AutoML."
    )
    parser.add_argument(
        "--model-dir",
        type=str,
        default=None,
        help="Ruta explícita al directorio que contiene el archivo MLmodel."
    )
    parser.add_argument(
        "--signature-only",
        action="store_true",
        help="Valida únicamente la firma y metadatos sin intentar deserializar el binario."
    )
    parser.add_argument(
        "--require-load",
        action="store_true",
        help="Modo estricto: exige que la deserialización y carga real del estimador sea exitosa (código != 0 si falla)."
    )
    parser.add_argument(
        "--no-predict",
        action="store_true",
        help="Cargar el modelo sin ejecutar predicción sintética de prueba."
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Emitir resultado en formato JSON estructurado."
    )
    parser.add_argument(
        "--check",
        action="store_true",
        help="Modo estricto para CI: valida que la firma coincida exactamente con las 8 variables."
    )

    args = parser.parse_args()

    if args.model_dir:
        model_dir = Path(args.model_dir).resolve()
    else:
        model_dir = find_mlmodel_dir(DEFAULT_MODELS_DIR)

    if not model_dir or not model_dir.exists():
        print(f"[ERROR] No se localizó el directorio del modelo en '{DEFAULT_MODELS_DIR}'.", file=sys.stderr)
        return 1

    # Determinar qué fases ejecutar
    attempt_load = not args.signature_only
    test_predict = attempt_load and not args.no_predict

    report = run_verification_pipeline(
        model_dir,
        check_signature=True,
        attempt_load=attempt_load,
        test_predict=test_predict
    )

    if args.json:
        print(json.dumps(report, indent=2, ensure_ascii=False))
    else:
        print_load_report(report)

    # Determinar código de salida
    if args.require_load:
        # Exige carga exitosa obligatoriamente
        if not report["load_successful"]:
            return 2
        if test_predict and not report["predict_successful"]:
            return 3
        return 0

    if args.signature_only or args.check:
        return 0 if report["signature_verified"] else 1

    # En modo diagnóstico por defecto, retorna 0 si la firma es correcta
    return 0 if report["signature_verified"] else 1


if __name__ == "__main__":
    sys.exit(main())
