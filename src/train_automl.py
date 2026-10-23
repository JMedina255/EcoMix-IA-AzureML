"""
Fase 3: Configuración y Lanzamiento de AutoML Regression en Azure ML
Proyecto: ML EcomixIA
Optimizado para suscripción estudiantil (control estricto de presupuesto y tiempos).
"""

import os
import json
from pathlib import Path
from azure.ai.ml import MLClient, automl, Input
from azure.ai.ml.constants import AssetTypes
from azure.identity import DefaultAzureCredential, InteractiveBrowserCredential

# 1. Rutas del proyecto
BASE_DIR = Path(__file__).resolve().parent.parent
CONFIG_PATH = BASE_DIR / "config.json"
TRAIN_MLTABLE_DIR = BASE_DIR / "data" / "processed" / "train"


def get_azure_credentials():
    """
    Intenta obtener credenciales locales (CLI, VS Code, variables de entorno).
    Si no encuentra credenciales activas, recurre al navegador interactivo.
    """
    try:
        cred = DefaultAzureCredential()
        cred.get_token("https://management.azure.com/.default")
        print("[AUTH] Credencial local detectada (Azure CLI / Environment).")
        return cred
    except Exception:
        print("[AUTH] Abriendo navegador para inicio de sesión interactivo...")
        return InteractiveBrowserCredential()


def build_automl_job(compute_name: str) -> automl.RegressionJob:
    """
    Construye y configura el trabajo de regresión AutoML con límites estrictos de presupuesto.
    """
    # Usar el Data Asset registrado previamente en Azure ML
    training_data = Input(
        type=AssetTypes.MLTABLE,
        path="azureml:concrete-train-mltable:1"
    )

    # Definir el experimento de AutoML Regression
    job = automl.regression(
        compute=compute_name,
        experiment_name="ecomix-ia-automl",
        training_data=training_data,
        target_column_name="concrete_compressive_strength",
        primary_metric="normalized_root_mean_squared_error",
        n_cross_validations=5,  # 5-fold CV para 824 filas de entrenamiento
        tags={
            "project": "EcoMix-IA",
            "phase": "AutoML-Training",
            "target": "concrete_compressive_strength",
            "budget": "student-credit-safe"
        }
    )

    # Límites estrictos para no agotar el crédito de estudiante:
    job.set_limits(
        timeout_minutes=30,        # Límite total: máximo 30 minutos de ejecución (~$0.10 USD)
        trial_timeout_minutes=5,   # Si un modelo tarda más de 5 min, se descarta y pasa al siguiente
        max_trials=12,             # Suficiente para evaluar LightGBM, Random Forest, ElasticNet, etc.
        enable_early_termination=True,
        max_concurrent_trials=1    # 1 modelo a la vez (máximo de 1 nodo en el clúster)
    )

    # Optimización de entrenamiento para ahorro de recursos
    job.set_training(
        enable_onnx_compatible_models=False,
        enable_model_explainability=True,
        enable_vote_ensemble=True,
        enable_stack_ensemble=False  # Stacking consume tiempo excesivo e innecesario en créditos de estudiante
    )

    return job


def main():
    print("=" * 60)
    print("FASE 3: LANZAMIENTO DE AUTOML EN AZURE MACHINE LEARNING")
    print("=" * 60)

    # Cargar configuración
    if not CONFIG_PATH.exists():
        raise FileNotFoundError(f"No se encontró 'config.json' en: {CONFIG_PATH}")

    with open(CONFIG_PATH, "r", encoding="utf-8") as f:
        config = json.load(f)

    subscription_id = config.get("subscription_id")
    resource_group = config.get("resource_group")
    workspace_name = config.get("workspace_name")
    compute_name = config.get("compute_name", "cpu-cluster-ecomix")

    print(f"[CONFIG] Workspace: {workspace_name}")
    print(f"[CONFIG] Resource Group: {resource_group}")
    print(f"[CONFIG] Compute Cluster: {compute_name}")

    # Conectar con Azure ML
    credential = get_azure_credentials()
    ml_client = MLClient(
        credential=credential,
        subscription_id=subscription_id,
        resource_group_name=resource_group,
        workspace_name=workspace_name,
    )

    # Construir el trabajo
    print("\n[JOB] Configurando trabajo de regresión con límites de seguridad...")
    job = build_automl_job(compute_name=compute_name)

    # Enviar el trabajo a Azure ML
    print("\n[SUBMIT] Enviando el trabajo de AutoML a Azure...")
    returned_job = ml_client.jobs.create_or_update(job)

    print("\n" + "=" * 60)
    print(f"[EXITO] Trabajo enviado a Azure ML!")
    print(f"Nombre del Job: {returned_job.name}")
    print(f"Estado inicial: {returned_job.status}")
    if hasattr(returned_job, "services") and "Studio" in returned_job.services:
        print(f"Enlace de seguimiento en Azure Studio:\n{returned_job.services['Studio'].endpoint}")
    print("=" * 60)


if __name__ == "__main__":
    main()
