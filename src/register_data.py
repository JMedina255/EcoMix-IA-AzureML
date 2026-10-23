import os
import json
from pathlib import Path
from azure.ai.ml import MLClient
from azure.ai.ml.entities import Data
from azure.ai.ml.constants import AssetTypes
from azure.identity import DefaultAzureCredential, InteractiveBrowserCredential

# 1. Configuración de rutas del proyecto
BASE_DIR = Path(__file__).resolve().parent.parent
CONFIG_PATH = BASE_DIR / "config.json"
TRAIN_DATA_PATH = BASE_DIR / "data" / "processed" / "concrete_train.csv"
TEST_DATA_PATH = BASE_DIR / "data" / "processed" / "concrete_test.csv"
TRAIN_MLTABLE_PATH = BASE_DIR / "data" / "processed" / "train"
TEST_MLTABLE_PATH = BASE_DIR / "data" / "processed" / "test"


def get_azure_credentials():
    """
    Intenta obtener credenciales locales (CLI, VS Code, variables de entorno).
    Si no encuentra credenciales activas, abre el navegador para inicio de sesión interactivo.
    """
    try:
        cred = DefaultAzureCredential()
        cred.get_token("https://management.azure.com/.default")
        print("[AUTH] Credencial local detectada (Azure CLI / Environment).")
        return cred
    except Exception:
        print("[AUTH] No se detectó sesión local activa. Abriendo navegador para inicio de sesión interactivo...")
        return InteractiveBrowserCredential()


def register_or_get_asset(ml_client: MLClient, asset: Data):
    """
    Registra el Data Asset en Azure ML.
    Si ya existe la versión registrada, la recupera de forma segura
    para evitar el error de inmutabilidad de URIs en Azure ML.
    """
    try:
        existing = ml_client.data.get(name=asset.name, version=asset.version)
        print(f"[OK] El activo '{existing.name}' (versión {existing.version}) ya existe en Azure ML. Se reutiliza.")
        return existing
    except Exception:
        pass

    try:
        created = ml_client.data.create_or_update(asset)
        print(f"[OK] Activo registrado con éxito: {created.name} (versión {created.version})")
        return created
    except Exception as e:
        if "already exists" in str(e).lower():
            print(f"[OK] El activo '{asset.name}' ya existía previamente en Azure ML.")
            return ml_client.data.get(name=asset.name, version=asset.version)
        raise e


def main():
    print("=" * 60)
    print("REGISTRO DE ACTIVOS DE DATOS EN AZURE MACHINE LEARNING")
    print("=" * 60)

    # 2. Cargar configuración desde config.json
    if not CONFIG_PATH.exists():
        raise FileNotFoundError(f"No se encontró el archivo de configuración en: {CONFIG_PATH}")

    with open(CONFIG_PATH, "r", encoding="utf-8") as f:
        config = json.load(f)

    subscription_id = config.get("subscription_id")
    resource_group = config.get("resource_group")
    workspace_name = config.get("workspace_name")

    print(f"[CONFIG] Workspace: {workspace_name}")
    print(f"[CONFIG] Resource Group: {resource_group}")
    print(f"[CONFIG] Subscription ID: {subscription_id}")

    # 3. Conectar a Azure ML
    credential = get_azure_credentials()
    ml_client = MLClient(
        credential=credential,
        subscription_id=subscription_id,
        resource_group_name=resource_group,
        workspace_name=workspace_name,
    )

    # 4. Validar existencia de los archivos locales
    if not TRAIN_DATA_PATH.exists():
        raise FileNotFoundError(f"No se encontró el dataset de entrenamiento en: {TRAIN_DATA_PATH}")

    # 5. Registrar Data Asset de Entrenamiento (CSV URI_FILE)
    print("\n[1/3] Registrando dataset de ENTRENAMIENTO (CSV)...")
    train_asset = Data(
        name="concrete-train-dataset",
        version="1",
        description="Dataset UCI Concrete para entrenamiento EcoMix IA (80% split, 824 filas).",
        path=str(TRAIN_DATA_PATH),
        type=AssetTypes.URI_FILE,
        tags={
            "project": "EcoMix-IA",
            "split": "train",
            "random_state": "42",
            "target": "concrete_compressive_strength",
            "rows": "824"
        }
    )
    register_or_get_asset(ml_client, train_asset)

    # 6. Registrar Data Asset MLTable para AutoML
    if TRAIN_MLTABLE_PATH.exists():
        print("\n[2/3] Registrando MLTable de ENTRENAMIENTO (optimizado para AutoML)...")
        mltable_train_asset = Data(
            name="concrete-train-mltable",
            version="1",
            description="MLTable UCI Concrete listo para trabajos de AutoML Regression (824 filas).",
            path=str(TRAIN_MLTABLE_PATH),
            type=AssetTypes.MLTABLE,
            tags={
                "project": "EcoMix-IA",
                "type": "mltable",
                "target": "concrete_compressive_strength"
            }
        )
        register_or_get_asset(ml_client, mltable_train_asset)

    # 7. Registrar Data Asset de Prueba (Test Set independiente)
    if TEST_DATA_PATH.exists():
        print("\n[3/3] Registrando dataset de PRUEBA INDEPENDIENTE...")
        test_asset = Data(
            name="concrete-test-dataset",
            version="1",
            description="Dataset UCI Concrete reservado para evaluación final independiente (20% split, 206 filas).",
            path=str(TEST_DATA_PATH),
            type=AssetTypes.URI_FILE,
            tags={
                "project": "EcoMix-IA",
                "split": "test",
                "random_state": "42",
                "target": "concrete_compressive_strength",
                "rows": "206"
            }
        )
        register_or_get_asset(ml_client, test_asset)

    print("\n" + "=" * 60)
    print("Proceso de registro finalizado exitosamente en Azure ML.")
    print("=" * 60)


if __name__ == "__main__":
    main()
