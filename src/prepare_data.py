"""
Fase 2: Preparación y Validación del Dataset UCI Concrete Compressive Strength
Proyecto: ML EcomixIA
"""

import os
import json
import shutil
import pandas as pd
from sklearn.model_selection import train_test_split

# Configuración de rutas y semilla
SEED = 42
TEST_SIZE = 0.20
RAW_DATA_PATH = "data/raw/concrete_raw.csv"
CLEAN_DATA_PATH = "data/processed/concrete_clean.csv"
TRAIN_DATA_PATH = "data/processed/concrete_train.csv"
TEST_DATA_PATH = "data/processed/concrete_test.csv"
METADATA_PATH = "data/processed/metadata.json"

# Mapeo de columnas y unidades documentadas en UCI (ID 165)
COLUMNS_METADATA = {
    "Cement": {
        "clean_name": "cement",
        "type": "input",
        "unit": "kg/m^3",
        "description": "Cantidad de cemento en la mezcla"
    },
    "Blast Furnace Slag": {
        "clean_name": "blast_furnace_slag",
        "type": "input",
        "unit": "kg/m^3",
        "description": "Escoria de alto horno"
    },
    "Fly Ash": {
        "clean_name": "fly_ash",
        "type": "input",
        "unit": "kg/m^3",
        "description": "Ceniza volante"
    },
    "Water": {
        "clean_name": "water",
        "type": "input",
        "unit": "kg/m^3",
        "description": "Agua de mezclado"
    },
    "Superplasticizer": {
        "clean_name": "superplasticizer",
        "type": "input",
        "unit": "kg/m^3",
        "description": "Aditivo superplastificante"
    },
    "Coarse Aggregate": {
        "clean_name": "coarse_aggregate",
        "type": "input",
        "unit": "kg/m^3",
        "description": "Agregado grueso (grava)"
    },
    "Fine Aggregate": {
        "clean_name": "fine_aggregate",
        "type": "input",
        "unit": "kg/m^3",
        "description": "Agregado fino (arena)"
    },
    "Age": {
        "clean_name": "age",
        "type": "input",
        "unit": "days",
        "description": "Edad de curado del concreto (1-365 días)"
    },
    "Concrete compressive strength": {
        "clean_name": "concrete_compressive_strength",
        "type": "target",
        "unit": "MPa",
        "description": "Resistencia a la compresión del concreto (variable objetivo)"
    }
}


def prepare_dataset():
    print("=" * 60)
    print("FASE 2: PREPARACIÓN Y VALIDACIÓN DEL DATASET")
    print("=" * 60)

    # 1. Crear directorios organizados
    os.makedirs("data/raw", exist_ok=True)
    os.makedirs("data/processed", exist_ok=True)

    # 2. Asegurar y conservar copia original sin modificar
    if not os.path.exists("concrete_data.csv"):
        raise FileNotFoundError("No se encontró 'concrete_data.csv'. Ejecuta primero dataset.py.")

    if not os.path.exists(RAW_DATA_PATH):
        shutil.copy("concrete_data.csv", RAW_DATA_PATH)
        print(f"[OK] Copia original conservada en: {RAW_DATA_PATH}")
    else:
        print(f"[INFO] Copia original existente en: {RAW_DATA_PATH}")

    # Cargar datos originales
    df_raw = pd.read_csv(RAW_DATA_PATH)
    total_raw_rows, total_raw_cols = df_raw.shape
    print(f"[INFO] Datos crudos cargados: {total_raw_rows} observaciones, {total_raw_cols} columnas.")

    # 3. Verificaciones de integridad
    # 3.1 Valores nulos
    null_counts = df_raw.isnull().sum().to_dict()
    total_nulls = df_raw.isnull().sum().sum()
    print(f"[VALIDACIÓN] Total de valores nulos: {total_nulls}")

    # 3.2 Duplicados
    num_duplicates = int(df_raw.duplicated().sum())
    num_duplicate_rows_total = int(df_raw.duplicated(keep=False).sum())
    print(f"[VALIDACIÓN] Filas duplicadas idénticas detectadas: {num_duplicates} (total involucradas en repeticiones: {num_duplicate_rows_total})")
    print("  -> Nota: En ensayos de compresión de concreto (ASTM C39), es común preparar")
    print("     probetas cilíndricas en duplicado o triplicado por lote de ensayo.")
    print("     Se conservan las 1.030 observaciones completas para consistencia con benchmarks.")

    # 3.3 Verificación de tipos de datos y columnas esperadas
    expected_cols = list(COLUMNS_METADATA.keys())
    missing_cols = set(expected_cols) - set(df_raw.columns)
    if missing_cols:
        raise ValueError(f"Faltan columnas esperadas en el dataset: {missing_cols}")
    print("[VALIDACIÓN] Todas las 9 columnas esperadas están presentes.")

    # 4. Normalización de nombres de columnas
    rename_mapping = {col: info["clean_name"] for col, info in COLUMNS_METADATA.items()}
    df_clean = df_raw.rename(columns=rename_mapping).copy()

    # Asegurar tipo de Age (entero / numérico)
    df_clean["age"] = df_clean["age"].astype(int)

    # 5. Comprobación funcional de variable Age y variable Objetivo
    age_dist = df_clean["age"].value_counts().sort_index().to_dict()
    target_stats = {
        "min": float(df_clean["concrete_compressive_strength"].min()),
        "max": float(df_clean["concrete_compressive_strength"].max()),
        "mean": float(df_clean["concrete_compressive_strength"].mean()),
        "std": float(df_clean["concrete_compressive_strength"].std())
    }
    print(f"[VALIDACIÓN] 'age' verificado: Rango {df_clean['age'].min()} a {df_clean['age'].max()} días.")
    print(f"  -> Ensayos a 7 días: {age_dist.get(7, 0)} muestras")
    print(f"  -> Ensayos a 28 días: {age_dist.get(28, 0)} muestras")
    print(f"[VALIDACIÓN] Objetivo 'concrete_compressive_strength': Min={target_stats['min']:.2f} MPa, Max={target_stats['max']:.2f} MPa, Media={target_stats['mean']:.2f} MPa")

    # Guardar versión limpia completa
    df_clean.to_csv(CLEAN_DATA_PATH, index=False)
    print(f"[OK] Dataset normalizado guardado en: {CLEAN_DATA_PATH}")

    # 6. Partición de entrenamiento y prueba (80% / 20%)
    train_df, test_df = train_test_split(
        df_clean,
        test_size=TEST_SIZE,
        random_state=SEED,
        shuffle=True
    )

    train_df.to_csv(TRAIN_DATA_PATH, index=False)
    test_df.to_csv(TEST_DATA_PATH, index=False)
    print(f"[OK] Conjunto de Entrenamiento (80%): {train_df.shape[0]} filas -> {TRAIN_DATA_PATH}")
    print(f"[OK] Conjunto de Prueba independiente (20%): {test_df.shape[0]} filas -> {TEST_DATA_PATH}")

    # 7. Generar reporte de metadatos
    metadata = {
        "dataset_name": "UCI Concrete Compressive Strength",
        "dataset_id_uci": 165,
        "random_seed": SEED,
        "split_ratio": {
            "train": 1.0 - TEST_SIZE,
            "test": TEST_SIZE
        },
        "total_observations": total_raw_rows,
        "train_observations": len(train_df),
        "test_observations": len(test_df),
        "columns_count": total_raw_cols,
        "null_values_count": null_counts,
        "duplicated_rows_count": num_duplicates,
        "input_features": [
            info["clean_name"] for info in COLUMNS_METADATA.values() if info["type"] == "input"
        ],
        "target_variable": "concrete_compressive_strength",
        "target_unit": "MPa",
        "age_distribution": age_dist,
        "target_statistics": target_stats,
        "column_dictionary": COLUMNS_METADATA,
        "functional_decision_age": (
            "La edad del concreto ('age') es una variable de entrada esencial del modelo. "
            "Para estimar la resistencia a 7 y 28 días, el sistema debe evaluar la misma mezcla "
            "configurando age=7 y age=28 respectivamente. No representa una garantía estructural, "
            "sino una estimación estadística basada en el histórico experimental."
        )
    }

    with open(METADATA_PATH, "w", encoding="utf-8") as f:
        json.dump(metadata, f, indent=2, ensure_ascii=False)
    print(f"[OK] Metadatos y registro de semilla guardados en: {METADATA_PATH}")

    print("=" * 60)
    print("Fase 2 completada exitosamente.")
    print("=" * 60)


if __name__ == "__main__":
    prepare_dataset()
