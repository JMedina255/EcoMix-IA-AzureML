#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
scripts/prepare_azure_eval_job.py — Validador y Preparador del Job de Evaluación en Azure ML.

Valida declarativa y estáticamente la especificación del Command Job en Azure ML
(config/azure_eval_job.yml) para ejecutar la evaluación independiente en la nube bajo
el runtime oficial del modelo ganador (VotingEnsemble), sin enviar ni consumir cómputo.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import sys
from typing import Any, Dict, List, Optional, Tuple
import yaml

BASE_DIR = Path(__file__).resolve().parent.parent
CONFIG_JOB_PATH = BASE_DIR / "config" / "azure_eval_job.yml"
TEST_DATA_PATH = BASE_DIR / "data" / "processed" / "concrete_test.csv"
TRAIN_DATA_PATH = BASE_DIR / "data" / "processed" / "concrete_train.csv"

EXPECTED_WINNER_MODEL_ASSET = "azureml:azureml_wheat_cheese_4swj34tkjn_11_output_mlflow_log_model_873731674:1"
EXPECTED_ENVIRONMENT_IMAGE = "mcr.microsoft.com/azureml/curated/ai-ml-automl:41"
EXPECTED_COMPUTE_CLUSTER = "azureml:cpu-cluster-ecomix"
EXPECTED_TIMEOUT_MINUTES = 30
EXPECTED_INSTANCE_COUNT = 1


def compute_file_sha256(file_path: Path) -> str:
    """Calcula el hash SHA-256 de un archivo para verificación de integridad."""
    sha = hashlib.sha256()
    with open(file_path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            sha.update(chunk)
    return sha.hexdigest()


def validate_eval_job_specification(
    job_yaml_path: Path = CONFIG_JOB_PATH,
    test_data_path: Path = TEST_DATA_PATH,
    train_data_path: Optional[Path] = TRAIN_DATA_PATH
) -> Tuple[bool, Dict[str, Any], List[str]]:
    """
    Valida exhaustivamente la configuración declarativa del Azure ML Command Job.
    Retorna: (es_valido, metadata_dict, lista_errores)
    """
    errors: List[str] = []
    metadata: Dict[str, Any] = {}

    if not job_yaml_path.exists():
        return False, {}, [f"No existe el archivo de especificación en: {job_yaml_path}"]

    try:
        with open(job_yaml_path, "r", encoding="utf-8") as f:
            job_spec = yaml.safe_load(f)
    except Exception as e:
        return False, {}, [f"Error al parsear YAML ({type(e).__name__}): {e}"]

    if not isinstance(job_spec, dict):
        return False, {}, ["El contenido del archivo YAML debe ser un diccionario raíz."]

    # 1. Tipo de trabajo
    job_type = job_spec.get("type")
    if job_type != "command":
        errors.append(f"Tipo de job incorrecto: '{job_type}' (se esperaba 'command').")

    # 2. Compute
    compute = job_spec.get("compute")
    if compute != EXPECTED_COMPUTE_CLUSTER and compute != "cpu-cluster-ecomix":
        errors.append(f"Clúster de cómputo inesperado: '{compute}' (se esperaba '{EXPECTED_COMPUTE_CLUSTER}').")
    metadata["compute"] = compute

    # 3. Environment
    env = job_spec.get("environment", {})
    image = env.get("image") if isinstance(env, dict) else str(env)
    if image != EXPECTED_ENVIRONMENT_IMAGE:
        errors.append(f"Imagen base inesperada: '{image}' (se esperaba '{EXPECTED_ENVIRONMENT_IMAGE}').")
    metadata["environment_image"] = image

    # 4. Inputs
    inputs = job_spec.get("inputs", {})
    if not isinstance(inputs, dict):
        errors.append("La sección 'inputs' debe ser un diccionario.")
    else:
        # Input del modelo
        model_input = inputs.get("model_dir", {})
        model_path = model_input.get("path") if isinstance(model_input, dict) else str(model_input)
        if model_path != EXPECTED_WINNER_MODEL_ASSET:
            errors.append(f"Activo de modelo inesperado: '{model_path}' (se esperaba '{EXPECTED_WINNER_MODEL_ASSET}').")
        metadata["model_asset"] = model_path

        # Input de test
        test_input = inputs.get("test_data", {})
        metadata["test_data_input"] = test_input

    # 5. Verificación de hash SHA-256 de test y train
    if test_data_path.exists():
        actual_test_sha = compute_file_sha256(test_data_path)
        metadata["actual_test_sha256"] = actual_test_sha
        tags = job_spec.get("tags", {})
        tag_sha = tags.get("test_sha256")
        if tag_sha and tag_sha != actual_test_sha:
            errors.append(f"El hash SHA-256 en tags ({tag_sha}) no coincide con el archivo real ({actual_test_sha}).")
    else:
        errors.append(f"No existe el archivo de prueba local en: {test_data_path}")

    if train_data_path and train_data_path.exists():
        actual_train_sha = compute_file_sha256(train_data_path)
        metadata["actual_train_sha256"] = actual_train_sha

    # 6. Command
    command = job_spec.get("command", "")
    if "evaluate_model.py" not in command or "--evaluate" not in command:
        errors.append(f"El comando no invoca 'evaluate_model.py --evaluate': '{command}'.")
    metadata["command"] = command

    # 7. Limits & Resources
    limits = job_spec.get("limits", {})
    timeout = limits.get("timeout_minutes") if isinstance(limits, dict) else None
    if timeout != EXPECTED_TIMEOUT_MINUTES:
        errors.append(f"Límite de tiempo inesperado: {timeout} min (se esperaba {EXPECTED_TIMEOUT_MINUTES} min).")
    metadata["timeout_minutes"] = timeout

    resources = job_spec.get("resources", {})
    instances = resources.get("instance_count") if isinstance(resources, dict) else None
    if instances != EXPECTED_INSTANCE_COUNT:
        errors.append(f"Concurrencia/instancias inesperada: {instances} (se esperaba {EXPECTED_INSTANCE_COUNT}).")
    metadata["instance_count"] = instances

    # 8. Outputs
    outputs = job_spec.get("outputs", {})
    if "reports_dir" not in outputs:
        errors.append("La sección 'outputs' debe definir 'reports_dir'.")
    metadata["outputs"] = list(outputs.keys())

    is_valid = len(errors) == 0
    metadata["valid"] = is_valid
    metadata["spec_path"] = str(job_yaml_path)

    return is_valid, metadata, errors


def print_validation_report(is_valid: bool, metadata: Dict[str, Any], errors: List[str]) -> None:
    """Imprime el diagnóstico en consola."""
    print("=" * 68)
    print(" ECOMIX IA — ESPECIFICACIÓN DEL JOB DE EVALUACIÓN AZURE ML")
    print("=" * 68)
    print(f" Archivo YAML:         {metadata.get('spec_path')}")
    print(f" Estado de Validación: {'[VÁLIDO Y PREPARADO]' if is_valid else '[ERRORES DETECTADOS]'}")
    print("-" * 68)
    print(f" Clúster Cómputo:      {metadata.get('compute')}")
    print(f" Runtime / Imagen:     {metadata.get('environment_image')}")
    print(f" Activo del Modelo:    {metadata.get('model_asset')}")
    print(f" SHA-256 Test Set:     {metadata.get('actual_test_sha256')}")
    if metadata.get("actual_train_sha256"):
        print(f" SHA-256 Train Set:    {metadata.get('actual_train_sha256')}")
    print(f" Timeout Máximo:       {metadata.get('timeout_minutes')} minutos")
    print(f" Instancias Cómputo:   {metadata.get('instance_count')} (CPU única)")
    print(f" Outputs Definidos:    {', '.join(metadata.get('outputs', []))}")
    print("-" * 68)
    print(" Comando Configurado:")
    print(f"   {metadata.get('command')}")
    print("-" * 68)

    if errors:
        print("[ERRORES DE CONFIGURACIÓN]:")
        for err in errors:
            print(f"  [X] {err}")
    else:
        print("[OK] Especificación completamente validada.")
        print("[AVISO DE GOBERNANZA]:")
        print("  El job está listo para ser despachado cuando el usuario lo autorice explícitamente.")
        print("  Comando CLI sugerido para ejecución futura:")
        print("    az ml job create -f config/azure_eval_job.yml")
    print("=" * 68)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Valida estáticamente el job declarativo de evaluación en Azure ML sin enviar cómputo."
    )
    parser.add_argument(
        "--spec-path",
        type=str,
        default=str(CONFIG_JOB_PATH),
        help="Ruta al archivo YAML de especificación del job."
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Emitir resultado en formato JSON estructurado."
    )
    parser.add_argument(
        "--check",
        action="store_true",
        help="Modo estricto para CI: retorna 0 si la especificación es válida, 1 si tiene errores."
    )

    args = parser.parse_args()

    is_valid, metadata, errors = validate_eval_job_specification(
        job_yaml_path=Path(args.spec_path),
        test_data_path=TEST_DATA_PATH,
        train_data_path=TRAIN_DATA_PATH
    )

    if args.json:
        out = {
            "valid": is_valid,
            "metadata": metadata,
            "errors": errors
        }
        print(json.dumps(out, indent=2, ensure_ascii=False))
    else:
        print_validation_report(is_valid, metadata, errors)

    return 0 if is_valid else 1


if __name__ == "__main__":
    sys.exit(main())
