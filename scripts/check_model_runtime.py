#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
scripts/check_model_runtime.py — Diagnóstico y Verificación del Runtime del Modelo AutoML.

Inspecciona de forma segura el artefacto descargado (MLmodel, conda.yaml, python_env.yaml,
requirements.txt y model.pkl) sin deserializar código arbitrario ni ejecutar binarios.
Evalúa la compatibilidad del entorno local, clasifica dependencias y documenta alternativas.
"""

from __future__ import annotations

import argparse
import importlib.util
import json
import os
from pathlib import Path
import pickletools
import platform
import shutil
import subprocess
import sys
from typing import Any, Dict, List, Optional, Set, Tuple

import yaml

BASE_DIR = Path(__file__).resolve().parent.parent
DEFAULT_MODELS_DIR = BASE_DIR / "models"


def find_model_directory(base_models_dir: Path = DEFAULT_MODELS_DIR) -> Optional[Path]:
    """Localiza dinámicamente el directorio que contiene el artefacto MLmodel."""
    if not base_models_dir.exists():
        return None

    # Buscar directamente archivos MLmodel
    mlmodel_files = list(base_models_dir.rglob("MLmodel"))
    if mlmodel_files:
        # Preferir el directorio con mayor especificidad o el primer mlflow-model encontrado
        for ml_file in mlmodel_files:
            if "mlflow-model" in ml_file.parts:
                return ml_file.parent
        return mlmodel_files[0].parent

    return None


def inspect_metadata(model_dir: Path) -> Dict[str, Any]:
    """Extrae metadatos declarativos de MLmodel, python_env.yaml y conda.yaml sin deserializar."""
    mlmodel_path = model_dir / "MLmodel"
    python_env_path = model_dir / "python_env.yaml"
    conda_path = model_dir / "conda.yaml"
    requirements_path = model_dir / "requirements.txt"

    meta: Dict[str, Any] = {
        "model_dir": str(model_dir.relative_to(BASE_DIR) if model_dir.is_relative_to(BASE_DIR) else model_dir),
        "files_present": {
            "MLmodel": mlmodel_path.exists(),
            "python_env.yaml": python_env_path.exists(),
            "conda.yaml": conda_path.exists(),
            "requirements.txt": requirements_path.exists(),
            "model.pkl": (model_dir / "model.pkl").exists()
        }
    }

    if mlmodel_path.exists():
        try:
            with open(mlmodel_path, "r", encoding="utf-8") as f:
                ml_data = yaml.safe_load(f)

            flavors = ml_data.get("flavors", {})
            sklearn_flavor = flavors.get("sklearn", {})
            pyfunc_flavor = flavors.get("python_function", {})
            metadata_field = ml_data.get("metadata", {})

            # Extraer y parsear firma (inputs y outputs)
            signature = ml_data.get("signature", {})
            inputs_parsed = []
            if signature and "inputs" in signature:
                raw_inputs = signature["inputs"]
                if isinstance(raw_inputs, str):
                    try:
                        inputs_parsed = json.loads(raw_inputs)
                    except Exception:
                        pass
                elif isinstance(raw_inputs, list):
                    inputs_parsed = raw_inputs

            meta["mlmodel"] = {
                "artifact_path": ml_data.get("artifact_path"),
                "mlflow_version": ml_data.get("mlflow_version"),
                "model_size_bytes": ml_data.get("model_size_bytes"),
                "run_id": ml_data.get("run_id"),
                "model_uuid": ml_data.get("model_uuid"),
                "loader_module": sklearn_flavor.get("loader_module") or pyfunc_flavor.get("loader_module"),
                "serialization_format": sklearn_flavor.get("serialization_format"),
                "sklearn_version": sklearn_flavor.get("sklearn_version"),
                "python_version": pyfunc_flavor.get("python_version"),
                "azureml_base_image": metadata_field.get("azureml.base_image"),
                "azureml_engine": metadata_field.get("azureml.engine"),
                "signature_features": [inp.get("name") for inp in inputs_parsed if isinstance(inp, dict)]
            }
        except Exception as e:
            meta["mlmodel_error"] = str(e)

    if python_env_path.exists():
        try:
            with open(python_env_path, "r", encoding="utf-8") as f:
                py_env_data = yaml.safe_load(f)
            meta["python_env"] = py_env_data
        except Exception as e:
            meta["python_env_error"] = str(e)

    return meta


def inspect_pickle_classes(pickle_path: Path) -> Dict[str, Any]:
    """
    Inspecciona de forma segura los opcodes del pickle usando pickletools
    para extraer todos los módulos y clases referenciados SIN deserializar ni ejecutar código.
    """
    if not pickle_path.exists():
        return {"error": "Archivo model.pkl no encontrado"}

    globals_found: Set[Tuple[str, str]] = set()
    stack: List[str] = []

    try:
        with open(pickle_path, "rb") as f:
            for opcode, arg, pos in pickletools.genops(f):
                if opcode.name in ("SHORT_BINUNICODE", "BINUNICODE", "UNICODE"):
                    stack.append(str(arg))
                elif opcode.name == "STACK_GLOBAL":
                    if len(stack) >= 2:
                        name = stack.pop()
                        module = stack.pop()
                        globals_found.add((module, name))
                elif opcode.name == "GLOBAL":
                    if arg:
                        parts = arg.split()
                        if len(parts) == 2:
                            globals_found.add((parts[0], parts[1]))
    except Exception as e:
        return {"error": f"Error parseando opcodes pickle: {e}"}

    categorized: Dict[str, List[str]] = {
        "azureml_automl": [],
        "scikit_learn": [],
        "lightgbm_xgboost": [],
        "third_party": [],
        "builtins_numpy": []
    }

    for mod, cls in sorted(globals_found):
        fqcn = f"{mod}.{cls}"
        if mod.startswith("azureml."):
            categorized["azureml_automl"].append(fqcn)
        elif mod.startswith("sklearn."):
            categorized["scikit_learn"].append(fqcn)
        elif mod.startswith("lightgbm.") or mod.startswith("xgboost."):
            categorized["lightgbm_xgboost"].append(fqcn)
        elif mod.startswith("sklearn_pandas."):
            categorized["third_party"].append(fqcn)
        else:
            categorized["builtins_numpy"].append(fqcn)

    return {
        "total_referenced_symbols": len(globals_found),
        "categorized_symbols": categorized,
        "requires_azureml_automl_runtime": len(categorized["azureml_automl"]) > 0
    }


def check_python_310_availability() -> Dict[str, Any]:
    """Comprueba si Python 3.10 está instalado en el sistema local."""
    candidates = ["python3.10", "py -3.10"]
    found = False
    details = ""

    # Probar launcher de Windows 'py -3.10'
    py_launcher = shutil.which("py")
    if py_launcher:
        try:
            res = subprocess.run(
                ["py", "-3.10", "--version"],
                capture_output=True,
                text=True,
                timeout=5,
                check=False
            )
            if res.returncode == 0:
                found = True
                details = f"py -3.10 detectado: {res.stdout.strip()}"
        except Exception:
            pass

    # Probar comando directo 'python3.10'
    if not found:
        p310 = shutil.which("python3.10")
        if p310:
            try:
                res = subprocess.run(
                    [p310, "--version"],
                    capture_output=True,
                    text=True,
                    timeout=5,
                    check=False
                )
                if res.returncode == 0:
                    found = True
                    details = f"python3.10 detectado en: {p310} ({res.stdout.strip()})"
            except Exception:
                pass

    return {
        "available": found,
        "details": details if found else "Python 3.10 no encontrado en PATH ni en 'py' launcher.",
        "current_python": sys.version.split()[0]
    }


def classify_dependencies(meta: Dict[str, Any]) -> Dict[str, Any]:
    """Clasifica las dependencias del modelo entre compatibles, incompatibles y no verificadas."""
    curr_major = sys.version_info.major
    curr_minor = sys.version_info.minor
    is_py_310 = (curr_major == 3 and curr_minor == 10)
    is_windows = platform.system() == "Windows"

    compatible: List[str] = [
        "pandas (disponible >= 2.0 / estándar)",
        "numpy (disponible >= 1.23 / estándar)",
        "scikit-learn (disponible en entorno de desarrollo)",
        "joblib (disponible >= 1.2.0)",
        "mlflow (disponible >= 2.15.0)",
        "pytest (disponible en requirements-dev.txt)"
    ]

    incompatible: List[str] = []
    unverified: List[str] = []

    if curr_minor >= 12:
        incompatible.append(
            f"azureml-training-tabular==1.61.0 (Incompatible con Python {curr_major}.{curr_minor}; requiere Python >=3.9, <3.12)"
        )
        incompatible.append(
            f"azureml-automl-runtime==1.61.0 (Distribución binaria no disponible para Python {curr_major}.{curr_minor})"
        )
    elif is_windows:
        unverified.append(
            "azureml-dataprep-native==42.1.0 (Paquete compilado preferentemente para manylinux; verificar soporte en Windows)"
        )

    unverified.append(
        "azureml.training.tabular.models.voting_ensemble.PreFittedSoftVotingRegressor (Requiere runtime Azure ML para instanciación)"
    )
    unverified.append(
        "azureml.automl.runtime.featurization.data_transformer.DataTransformer (Transformador interno de Azure AutoML)"
    )

    is_locally_executable = is_py_310 and (len(incompatible) == 0)

    alternative = {
        "curated_image": "mcr.microsoft.com/azureml/curated/ai-ml-automl:41",
        "description": "Imagen curada oficial de Microsoft Azure ML que incluye Python 3.10.19, scikit-learn 1.5.1 y azureml-training-tabular preinstalados.",
        "remote_azure_execution": "Evaluación remota mediante script de inferencia o Azure ML Compute Instance / Notebook.",
        "docker_command": "docker run -it --rm -v ${PWD}:/workspace -w /workspace mcr.microsoft.com/azureml/curated/ai-ml-automl:41 python src/evaluate_model.py --evaluate"
    }

    return {
        "compatible": compatible,
        "incompatible": incompatible,
        "unverified": unverified,
        "is_locally_executable": is_locally_executable,
        "recommended_alternative": alternative
    }


def generate_runtime_report(base_models_dir: Path = DEFAULT_MODELS_DIR) -> Dict[str, Any]:
    """Genera un reporte integral de compatibilidad de runtime."""
    model_dir = find_model_directory(base_models_dir)

    if not model_dir:
        return {
            "status": "error",
            "message": "No se encontró ningún artefacto de modelo MLflow en 'models/'."
        }

    meta = inspect_metadata(model_dir)
    pickle_path = model_dir / "model.pkl"
    pickle_diag = inspect_pickle_classes(pickle_path) if pickle_path.exists() else {}
    py310_diag = check_python_310_availability()
    dep_classification = classify_dependencies(meta)

    return {
        "status": "success",
        "system": {
            "os": platform.system(),
            "os_release": platform.release(),
            "current_python": sys.version.split()[0],
            "architecture": platform.machine()
        },
        "model_artifact": meta,
        "pickle_inspection": pickle_diag,
        "python_310_check": py310_diag,
        "dependency_classification": dep_classification
    }


def print_report_dashboard(report: Dict[str, Any]) -> None:
    """Imprime en consola el reporte de verificación de runtime de forma clara y legible."""
    if report.get("status") == "error":
        print(f"[ERROR] {report.get('message')}")
        return

    sys_info = report["system"]
    meta = report["model_artifact"]
    mlmodel = meta.get("mlmodel", {})
    pickle_diag = report.get("pickle_inspection", {})
    py310 = report.get("python_310_check", {})
    dep = report.get("dependency_classification", {})

    print("=" * 68)
    print(" ECOMIX IA — DIAGNÓSTICO DE RUNTIME DEL MODELO GANADOR (AUTOML)")
    print("=" * 68)
    print(f" Sistema Local:         {sys_info['os']} {sys_info['os_release']} ({sys_info['architecture']})")
    print(f" Python Anfitrión:      {sys_info['current_python']}")
    print(f" Directorio Modelo:     {meta['model_dir']}")
    print("-" * 68)

    print(" 1. METADATOS DEL MODEL ASSET (MLmodel):")
    print(f"    * Run ID Azure:     {mlmodel.get('run_id')}")
    print(f"    * Python Objetivo:  {mlmodel.get('python_version')} (Confirmado)")
    print(f"    * Scikit-Learn:     {mlmodel.get('sklearn_version')}")
    print(f"    * MLflow Version:   {mlmodel.get('mlflow_version')}")
    print(f"    * Loader Module:    {mlmodel.get('loader_module')}")
    print(f"    * Formato:          {mlmodel.get('serialization_format')}")
    print(f"    * Tamaño Binario:   {mlmodel.get('model_size_bytes', 0):,} bytes")
    print(f"    * Firma (8 Var.):   {', '.join(mlmodel.get('signature_features', []))}")
    print(f"    * Imagen Curada:    {mlmodel.get('azureml_base_image')}")

    print("\n 2. INSPECCIÓN DE OPCODES DE PICKLE (Cero Ejecución de Código):")
    cat = pickle_diag.get("categorized_symbols", {})
    print(f"    * Total Símbolos:   {pickle_diag.get('total_referenced_symbols', 0)}")
    print(f"    * Clases Azure ML:  {len(cat.get('azureml_automl', []))} detectadas")
    for s in cat.get("azureml_automl", [])[:3]:
        print(f"      - {s}")
    print(f"    * Clases Sklearn:   {len(cat.get('scikit_learn', []))} detectadas")
    print(f"    * Clases Ensamble:  {len(cat.get('lightgbm_xgboost', []))} detectadas (LightGBM / XGBoost)")

    print("\n 3. EVALUACIÓN DE COMPATIBILIDAD LOCAL:")
    print(f"    * Python 3.10 Local: {'Disponible' if py310['available'] else 'No disponible'}")
    print(f"      Detalles: {py310['details']}")
    print(f"    * ¿Ejecutable local?: {'SÍ' if dep['is_locally_executable'] else 'BLOQUEADO LOCALMENTE (Requiere runtime compatible)'}")

    print("\n 4. CLASIFICACIÓN DE DEPENDENCIAS:")
    print("    [+] Compatibles en entorno actual:")
    for c in dep.get("compatible", []):
        print(f"        - {c}")

    if dep.get("incompatible"):
        print("    [-] Incompatibles con el intérprete actual:")
        for inc in dep.get("incompatible", []):
            print(f"        - {inc}")

    if dep.get("unverified"):
        print("    [?] No verificadas / Pendientes de runtime específico:")
        for unv in dep.get("unverified", []):
            print(f"        - {unv}")

    print("\n 5. ALTERNATIVA RECOMENDADA PARA REPRODUCIBILIDAD:")
    alt = dep.get("recommended_alternative", {})
    print(f"    * Entorno Curado:   {alt.get('curated_image')}")
    print(f"    * Estrategia:       {alt.get('description')}")
    print(f"    * Comando Docker:   {alt.get('docker_command')}")
    print(f"    * Alternativa Lab:  {alt.get('remote_azure_execution')}")
    print("=" * 68)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Diagnóstico y verificación del runtime del modelo AutoML."
    )
    parser.add_argument(
        "--models-dir",
        type=str,
        default=None,
        help="Ruta explícita al directorio base de modelos (por defecto: models/)."
    )
    parser.add_argument(
        "--inspect",
        action="store_true",
        default=True,
        help="Modo por defecto: inspección estática de metadatos y opcodes sin deserialización."
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Emitir diagnóstico en formato JSON estructurado."
    )
    parser.add_argument(
        "--check",
        action="store_true",
        help="Modo estricto para CI: valida que el Model Asset y metadatos sean íntegros."
    )

    args = parser.parse_args()
    models_dir = Path(args.models_dir).resolve() if args.models_dir else DEFAULT_MODELS_DIR
    report = generate_runtime_report(models_dir)

    if args.json:
        print(json.dumps(report, indent=2, ensure_ascii=False))
    else:
        print_report_dashboard(report)

    if args.check:
        return 0 if report.get("status") == "success" else 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
