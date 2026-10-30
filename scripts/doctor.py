#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
scripts/doctor.py — Diagnóstico de Entornos y Componentes de EcoMix IA.

Verifica el estado del entorno de desarrollo, credenciales Azure, datos de evaluación
y componentes de inferencia. No requiere privilegios de administrador y funciona
de forma no destructiva tanto en Windows como en Linux/macOS.
"""

from __future__ import annotations

import argparse
import importlib.util
import json
import os
from pathlib import Path
import platform
import shutil
import subprocess
import sys
from typing import Any, Dict, List, Optional, Tuple

BASE_DIR = Path(__file__).resolve().parent.parent


def check_module(name: str) -> Tuple[bool, Optional[str]]:
    """Comprueba si un módulo está instalado y devuelve su versión si es posible."""
    spec = importlib.util.find_spec(name)
    if spec is None:
        return False, None
    try:
        mod = importlib.import_module(name)
        version = getattr(mod, "__version__", "instalado")
        return True, str(version)
    except Exception:
        return True, "instalado (error al consultar __version__)"


def run_cmd(cmd: List[str], timeout: float = 3.0) -> Tuple[int, str]:
    """Ejecuta un comando de sistema de forma segura sin lanzar excepciones."""
    try:
        proc = subprocess.run(
            cmd,
            cwd=str(BASE_DIR),
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            timeout=timeout,
            check=False
        )
        return proc.returncode, proc.stdout.strip()
    except Exception as e:
        return -1, str(e)


def diagnose_development(base_dir: Path) -> Dict[str, Any]:
    """Evalúa si el entorno está preparado para desarrollo básico y ejecución de tests."""
    py_major, py_minor = sys.version_info.major, sys.version_info.minor
    py_ok = (py_major == 3 and py_minor >= 10)
    
    in_venv = (
        sys.prefix != sys.base_prefix
        or bool(os.environ.get("VIRTUAL_ENV"))
        or bool(os.environ.get("CONDA_PREFIX"))
    )

    git_path = shutil.which("git")
    git_ok = git_path is not None
    git_repo_ok = False
    if git_ok:
        ret, out = run_cmd(["git", "rev-parse", "--is-inside-work-tree"])
        git_repo_ok = (ret == 0 and out.lower() == "true")

    pytest_ok, pytest_ver = check_module("pytest")
    pandas_ok, pandas_ver = check_module("pandas")
    numpy_ok, numpy_ver = check_module("numpy")
    sklearn_ok, sklearn_ver = check_module("sklearn")

    failures = []
    actions = []

    if not py_ok:
        failures.append(f"Versión de Python no compatible: {sys.version.split()[0]} (requerido >= 3.10)")
        actions.append("Instalar Python 3.10, 3.11, 3.12 o 3.13 desde python.org o gestor del sistema.")

    if not in_venv:
        failures.append("No se detectó un entorno virtual activo (.venv o conda).")
        actions.append("Crear y activar un entorno virtual: 'python -m venv .venv' y '.venv\\Scripts\\Activate.ps1'.")

    if not git_ok:
        failures.append("Git no está instalado o no se encuentra en el PATH.")
        actions.append("Instalar Git para mantener trazabilidad y control de versiones.")
    elif not git_repo_ok:
        failures.append("El directorio actual no es un repositorio Git válido.")
        actions.append("Clonar el repositorio o inicializar Git.")

    missing_libs = []
    if not pytest_ok:
        missing_libs.append("pytest")
    if not pandas_ok:
        missing_libs.append("pandas")
    if not numpy_ok:
        missing_libs.append("numpy")
    if not sklearn_ok:
        missing_libs.append("scikit-learn")

    if missing_libs:
        failures.append(f"Bibliotecas esenciales de desarrollo ausentes: {', '.join(missing_libs)}")
        actions.append(f"Instalar dependencias de desarrollo: 'pip install -r requirements.txt'")

    is_ready = (py_ok and git_repo_ok and pytest_ok and pandas_ok and numpy_ok and sklearn_ok)

    return {
        "ready": is_ready,
        "details": {
            "python_version": sys.version.split()[0],
            "in_virtual_env": in_venv,
            "git_available": git_ok,
            "git_repo": git_repo_ok,
            "pytest": pytest_ver if pytest_ok else None,
            "pandas": pandas_ver if pandas_ok else None,
            "numpy": numpy_ver if numpy_ok else None,
            "scikit_learn": sklearn_ver if sklearn_ok else None,
        },
        "failures": failures,
        "actions": actions
    }


def diagnose_azure(base_dir: Path) -> Dict[str, Any]:
    """Evalúa si el entorno está preparado para operar con Azure ML."""
    config_path = base_dir / "config.json"
    example_path = base_dir / "config.example.json"
    
    config_exists = config_path.exists()
    config_valid = False
    masked_sub = None
    workspace_name = None

    if config_exists:
        try:
            with open(config_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            sub = data.get("subscription_id", "")
            ws = data.get("workspace_name", "")
            rg = data.get("resource_group", "")
            if sub and ws and rg and sub != "TU_SUBSCRIPTION_ID":
                config_valid = True
                masked_sub = f"...{sub[-4:]}" if len(sub) > 4 else "***"
                workspace_name = ws
        except Exception:
            pass

    sdk_ok, sdk_ver = check_module("azure.ai.ml")
    identity_ok, identity_ver = check_module("azure.identity")

    failures = []
    actions = []

    if not config_exists:
        failures.append("Archivo 'config.json' ausente.")
        if example_path.exists():
            actions.append("Copiar 'config.example.json' a 'config.json' y configurar credenciales de suscripción Azure.")
        else:
            actions.append("Crear 'config.json' con subscription_id, resource_group y workspace_name.")
    elif not config_valid:
        failures.append("'config.json' contiene valores de plantilla no configurados.")
        actions.append("Actualizar 'config.json' con el subscription_id, resource_group y workspace reales.")

    if not sdk_ok or not identity_ok:
        missing_azure = []
        if not sdk_ok:
            missing_azure.append("azure-ai-ml")
        if not identity_ok:
            missing_azure.append("azure-identity")
        failures.append(f"Paquetes de Azure ML ausentes: {', '.join(missing_azure)}")
        actions.append("Instalar dependencias de Azure: 'pip install azure-ai-ml azure-identity'")

    is_ready = (config_valid and sdk_ok and identity_ok)

    return {
        "ready": is_ready,
        "details": {
            "config_present": config_exists,
            "config_configured": config_valid,
            "subscription_masked": masked_sub,
            "workspace": workspace_name,
            "azure_ai_ml": sdk_ver if sdk_ok else None,
            "azure_identity": identity_ver if identity_ok else None
        },
        "failures": failures,
        "actions": actions
    }


def diagnose_evaluation(base_dir: Path) -> Dict[str, Any]:
    """Evalúa si el entorno cuenta con datos y modelo para la evaluación de Fase 4."""
    test_path = base_dir / "data" / "processed" / "concrete_test.csv"
    train_path = base_dir / "data" / "processed" / "concrete_train.csv"
    models_dir = base_dir / "models"
    
    test_ok = False
    test_rows = 0
    if test_path.exists():
        try:
            import pandas as pd
            df_test = pd.read_csv(test_path)
            test_rows = len(df_test)
            test_ok = (test_rows > 0 and "concrete_compressive_strength" in df_test.columns)
        except Exception:
            pass

    # Buscar archivos de modelo
    model_files = []
    if models_dir.exists():
        model_files = [str(p.relative_to(base_dir)) for p in models_dir.rglob("*.pkl")]

    failures = []
    actions = []

    if not test_path.exists() or not test_ok:
        failures.append(f"Dataset de prueba no encontrado o corrupto en '{test_path.relative_to(base_dir)}'.")
        actions.append("Ejecutar 'python src/prepare_data.py' para regenerar las particiones auditadas de datos.")

    if not model_files:
        failures.append("No se encontró ningún modelo binario (.pkl) en 'models/'.")
        actions.append("Descargar el modelo ganador desde Azure: 'python src/evaluate_model.py --download'.")

    # Advertencia sobre versiones de Python
    py_ver = sys.version.split()[0]
    py_warning = None
    if sys.version_info >= (3, 11):
        py_warning = (
            f"El modelo AutoML fue entrenado bajo Python 3.10.19 (scikit-learn 1.5.1, mlflow 2.15.1). "
            f"El intérprete actual es {py_ver}. Podría requerirse un entorno con Python 3.10.19 "
            "o contenedor Azure ML para deserialización sin advertencias ni discrepancias numéricas."
        )

    is_ready = (test_ok and len(model_files) > 0)

    return {
        "ready": is_ready,
        "details": {
            "test_dataset_path": str(test_path.relative_to(base_dir)) if test_path.exists() else None,
            "test_samples": test_rows,
            "model_files_count": len(model_files),
            "model_files": model_files[:3],
            "python_runtime_warning": py_warning
        },
        "failures": failures,
        "actions": actions
    }


def diagnose_inference(base_dir: Path) -> Dict[str, Any]:
    """Evalúa si las opciones de inferencia (Local, Docker, Remota) están disponibles."""
    inference_script = base_dir / "src" / "inference.py"
    models_dir = base_dir / "models"
    model_exists = models_dir.exists() and any(models_dir.rglob("*.pkl"))

    docker_path = shutil.which("docker")
    docker_ok = docker_path is not None
    docker_running = False
    if docker_ok:
        ret, _ = run_cmd(["docker", "info"], timeout=1.5)
        docker_running = (ret == 0)

    failures = []
    actions = []

    if not inference_script.exists():
        failures.append("Script 'src/inference.py' aún no implementado (Planificado para Fase 5).")
        actions.append("Completar Fase 4 antes de implementar el módulo de inferencia multivariable.")

    if not model_exists:
        failures.append("Modelo local no disponible para inferencia offline.")
        actions.append("Recuperar artefacto con 'python src/evaluate_model.py --download'.")

    is_ready = (inference_script.exists() and model_exists)

    return {
        "ready": is_ready,
        "details": {
            "inference_script_exists": inference_script.exists(),
            "local_model_available": model_exists,
            "docker_available": docker_ok,
            "docker_running": docker_running,
            "remote_execution_supported": True
        },
        "failures": failures,
        "actions": actions
    }


def run_doctor(base_dir: Path = BASE_DIR) -> Dict[str, Any]:
    """Ejecuta todos los diagnósticos y compila un reporte integral."""
    system_info = {
        "os": platform.system(),
        "release": platform.release(),
        "machine": platform.machine(),
        "python_executable": sys.executable,
        "python_version": sys.version.split()[0],
        "working_directory": str(base_dir)
    }

    dev_diag = diagnose_development(base_dir)
    azure_diag = diagnose_azure(base_dir)
    eval_diag = diagnose_evaluation(base_dir)
    infer_diag = diagnose_inference(base_dir)

    all_ready = dev_diag["ready"] and azure_diag["ready"] and eval_diag["ready"] and infer_diag["ready"]

    return {
        "system": system_info,
        "environments": {
            "development": dev_diag,
            "azure": azure_diag,
            "evaluation": eval_diag,
            "inference": infer_diag
        },
        "all_ready": all_ready
    }


def format_status(ready: bool) -> str:
    """Devuelve un distintivo de estado formateado."""
    return "[PREPARADO]" if ready else "[PENDIENTE / INCOMPLETO]"


def print_dashboard(report: Dict[str, Any]) -> None:
    """Imprime en consola un reporte limpio, visual y estructurado."""
    sys_info = report["system"]
    envs = report["environments"]

    print("=" * 65)
    print(" ECOMIX IA — DIAGNÓSTICO DE ENTORNO Y COMPONENTES (DOCTOR)")
    print("=" * 65)
    print(f" Sistema Operativo:   {sys_info['os']} {sys_info['release']} ({sys_info['machine']})")
    print(f" Intérprete Python:   {sys_info['python_version']} ({sys_info['python_executable']})")
    print(f" Directorio Raíz:     {sys_info['working_directory']}")
    print("-" * 65)

    # 1. Desarrollo
    dev = envs["development"]
    print(f" 1. Entorno de Desarrollo:       {format_status(dev['ready'])}")
    det = dev["details"]
    print(f"    * Virtualenv: {'Activo' if det['in_virtual_env'] else 'No detectado'}")
    print(f"    * Git Repo:   {'Válido' if det['git_repo'] else 'No detectado'}")
    print(f"    * Pytest:     {det['pytest'] or 'No instalado'}")
    print(f"    * Pandas:     {det['pandas'] or 'No instalado'}")
    print(f"    * Scikit-L.:  {det['scikit_learn'] or 'No instalado'}")
    if dev["failures"]:
        print("    [!] Observaciones:")
        for f in dev["failures"]:
            print(f"        - {f}")

    # 2. Azure
    az = envs["azure"]
    print(f"\n 2. Entorno para Azure ML:       {format_status(az['ready'])}")
    det = az["details"]
    print(f"    * Config:     {'Válido (Workspace: ' + str(det['workspace']) + ')' if det['config_configured'] else 'Incompleto / Plantilla'}")
    print(f"    * Azure SDK:  {det['azure_ai_ml'] or 'No instalado'}")
    print(f"    * Identity:   {det['azure_identity'] or 'No instalado'}")
    if az["failures"]:
        print("    [!] Observaciones:")
        for f in az["failures"]:
            print(f"        - {f}")

    # 3. Evaluación
    ev = envs["evaluation"]
    print(f"\n 3. Entorno para Evaluación:     {format_status(ev['ready'])}")
    det = ev["details"]
    print(f"    * Dataset Test: {'Presente (' + str(det['test_samples']) + ' filas)' if det['test_samples'] else 'Ausente'}")
    print(f"    * Modelos:      {det['model_files_count']} archivo(s) .pkl detectado(s)")
    if det.get("python_runtime_warning"):
        print(f"    * Advertencia:  {det['python_runtime_warning']}")
    if ev["failures"]:
        print("    [!] Observaciones:")
        for f in ev["failures"]:
            print(f"        - {f}")

    # 4. Inferencia
    inf = envs["inference"]
    print(f"\n 4. Entorno para Inferencia:     {format_status(inf['ready'])}")
    det = inf["details"]
    print(f"    * Script:     {'Presente' if det['inference_script_exists'] else 'Pendiente (Fase 5)'}")
    print(f"    * Docker:     {'Disponible (Daemon activo)' if det['docker_running'] else ('Instalado (Daemon inactivo)' if det['docker_available'] else 'No disponible')}")
    if inf["failures"]:
        print("    [!] Observaciones:")
        for f in inf["failures"]:
            print(f"        - {f}")

    # Siguientes Acciones
    all_actions = []
    for section_name, env_data in envs.items():
        if env_data["actions"]:
            all_actions.extend(env_data["actions"])

    print("\n" + "=" * 65)
    if all_actions:
        print(" SIGUIENTES ACCIONES RECOMENDADAS:")
        print("-" * 65)
        for i, act in enumerate(dict.fromkeys(all_actions), start=1):
            print(f" {i}. {act}")
    else:
        print(" [OK] Todos los componentes del entorno están operativos.")
    print("=" * 65)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Diagnóstico integral de entorno para EcoMix IA (Doctor)."
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Emitir el diagnóstico en formato JSON estructurado."
    )
    parser.add_argument(
        "--check",
        action="store_true",
        help="Modo estricto para CI: retorna 0 si el entorno de desarrollo está listo, 1 si no."
    )
    args = parser.parse_args()

    report = run_doctor(BASE_DIR)

    if args.json:
        print(json.dumps(report, indent=2, ensure_ascii=False))
    else:
        print_dashboard(report)

    if args.check:
        return 0 if report["environments"]["development"]["ready"] else 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
