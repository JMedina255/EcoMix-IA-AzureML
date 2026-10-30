#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
scripts/verify_model_load.py — Prueba Controlada de Carga y Firma del Modelo AutoML.

Carga el artefacto del modelo ganador mediante mlflow.sklearn.load_model() conforme
al flavor declarado en MLmodel. Verifica la correspondencia de las 8 variables predictoras,
comprueba el tipo del estimador y la disponibilidad del método predict().
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
    Verifica que el archivo MLmodel contenga la firma de entrada con las 8 variables esperadas.
    Retorna (es_valido, variables_encontradas, mensaje_error).
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

        # Comparar con EXPECTED_FEATURES (ignorando orden)
        missing = [f for f in EXPECTED_FEATURES if f not in found_features]
        extra = [f for f in found_features if f not in EXPECTED_FEATURES]

        if missing or extra:
            err_msg = f"Discrepancia en firma del modelo. Faltantes: {missing}, Inesperadas: {extra}."
            return False, found_features, err_msg

        return True, found_features, None
    except Exception as e:
        return False, [], f"Error al parsear MLmodel: {e}"


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


def load_and_verify_model(
    model_dir: Path,
    dry_run_predict: bool = True
) -> Dict[str, Any]:
    """
    Realiza la prueba controlada de carga del modelo mediante mlflow.sklearn.load_model().
    """
    report: Dict[str, Any] = {
        "model_dir": str(model_dir),
        "signature_verified": False,
        "features_found": [],
        "load_successful": False,
        "estimator_type": None,
        "has_predict_method": False,
        "dry_run_prediction": None,
        "status": "pending",
        "error": None,
        "environment_recommendation": None
    }

    # 1. Verificación de firma
    sig_ok, features, sig_err = verify_model_signature(model_dir)
    report["signature_verified"] = sig_ok
    report["features_found"] = features

    if not sig_ok:
        report["status"] = "error"
        report["error"] = f"Validación de firma fallida: {sig_err}"
        return report

    # 2. Carga controlada mediante mlflow.sklearn.load_model
    try:
        loaded_model = mlflow.sklearn.load_model(str(model_dir))
        report["load_successful"] = True
        report["estimator_type"] = type(loaded_model).__name__
        report["has_predict_method"] = hasattr(loaded_model, "predict")

        if not report["has_predict_method"]:
            report["status"] = "error"
            report["error"] = f"El estimador cargado ({report['estimator_type']}) no implementa predict()."
            return report

        # 3. Dry-run con 1 muestra de prueba para verificar compatibilidad de predict()
        if dry_run_predict:
            dummy_df = create_dummy_sample()
            try:
                preds = loaded_model.predict(dummy_df)
                if isinstance(preds, (np.ndarray, list, pd.Series)) and len(preds) == 1:
                    val = float(preds[0])
                    report["dry_run_prediction"] = val
                    report["status"] = "verified"
                else:
                    report["status"] = "verified"
                    report["dry_run_prediction"] = str(preds)
            except Exception as e:
                report["status"] = "load_ok_predict_failed"
                report["error"] = f"Modelo cargó pero predict() falló: {e}"
        else:
            report["status"] = "verified"

    except ModuleNotFoundError as mnf:
        report["load_successful"] = False
        report["status"] = "blocked_by_missing_dependency"
        report["error"] = (
            f"Falta el módulo especializado '{mnf.name}'. "
            "El artefacto VotingEnsemble de Azure AutoML contiene clases dependientes de "
            "'azureml.training.tabular' o 'azureml.automl.runtime', las cuales requieren "
            "Python 3.10 y el runtime especializado de Azure ML."
        )
        report["environment_recommendation"] = (
            "Para deserializar este modelo, utilice la imagen curada oficial "
            "'mcr.microsoft.com/azureml/curated/ai-ml-automl:41' o ejecute la evaluación en "
            "Azure ML Workspace (Compute Instance o Job)."
        )
    except Exception as e:
        report["load_successful"] = False
        report["status"] = "load_failed"
        report["error"] = f"Error al cargar el modelo: {type(e).__name__}: {e}"

    return report


def print_load_report(report: Dict[str, Any]) -> None:
    """Imprime el resultado de la prueba de carga en consola."""
    print("=" * 68)
    print(" ECOMIX IA — PRUEBA CONTROLADA DE CARGA DEL MODELO (Fase 4.4-A)")
    print("=" * 68)
    print(f" Directorio del Modelo: {report['model_dir']}")
    print(f" Firma (8 Variables):   {'[CORRECTA]' if report['signature_verified'] else '[FALLO]'}")
    if report["features_found"]:
        print(f" Variables Detectadas:  {', '.join(report['features_found'])}")
    print("-" * 68)

    if report["load_successful"]:
        print(" [OK] CARGA EXITOSA DEL ESTIMADOR")
        print(f" Estimador:             {report['estimator_type']}")
        print(f" Método predict():      {'Disponible' if report['has_predict_method'] else 'No disponible'}")
        if report["dry_run_prediction"] is not None:
            print(f" Predicción de Prueba:  {report['dry_run_prediction']} MPa (1 muestra sintética)")
        print(f" Estado:                VERIFICADO ({report['status']})")
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
        "--no-predict",
        action="store_true",
        help="Solo cargar el modelo sin ejecutar predicción sintética de prueba."
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

    report = load_and_verify_model(model_dir, dry_run_predict=not args.no_predict)

    if args.json:
        print(json.dumps(report, indent=2, ensure_ascii=False))
    else:
        print_load_report(report)

    if args.check:
        # En modo check, la firma DEBE ser correcta
        return 0 if report["signature_verified"] else 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
