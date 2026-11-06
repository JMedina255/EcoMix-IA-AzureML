"""
Motor de inferencia y orquestador predictivo para EcoMix IA (Fase 5.3).
Recibe dosificaciones validadas, genera las matrices vectorizadas para 7 y 28 días
en el orden exacto de la firma MLflow y ejecuta la predicción mediante el estimador
en memoria retenido por ModelLoader.
"""

from __future__ import annotations

import math
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union
import numpy as np
import pandas as pd

from .model_loader import (
    ModelLoader,
    ModelInferenceError,
    ModelNotFoundError,
    ModelIntegrityError,
    IncompatibleRuntimeError,
    OFFICIAL_MODEL_SHA256,
    OFFICIAL_RUN_ID,
    OFFICIAL_ALGORITHM,
)
from .schemas import (
    ConcreteMixDesign,
    PredictionRequest,
    PredictionResponse,
    StrengthPredictions,
    MixRatios,
    StructuredWarning,
    ModelMetadata,
)
from .validator import (
    DomainValidationError,
    validate_mix_design,
    validate_or_raise,
)


# =====================================================================
# CONSTANTES DE FIRMA MLFLOW
# =====================================================================

# Orden estricto de las 8 variables exigidas por la firma oficial de MLflow
FEATURE_COLUMNS: List[str] = [
    "cement",
    "blast_furnace_slag",
    "fly_ash",
    "water",
    "superplasticizer",
    "coarse_aggregate",
    "fine_aggregate",
    "age",
]

DEFAULT_AGES: Tuple[int, int] = (7, 28)


# =====================================================================
# MOTOR DE INFERENCIA PREDICTIVO
# =====================================================================

class InferenceEngine:
    """
    Orquestador de inferencia desacoplado de la infraestructura de red o HTTP.
    Gestiona la validación de entrada, vectorización de características y
    evaluación del modelo VotingEnsemble sin re-deserializaciones por solicitud.
    """

    def __init__(self, loader: Optional[ModelLoader] = None) -> None:
        self._loader = loader or ModelLoader.get_instance()

    @property
    def loader(self) -> ModelLoader:
        """Retorna el cargador de modelo asociado."""
        return self._loader

    # -------------------------------------------------------------
    # 1. Preparación de Matriz de Características (Firma MLflow)
    # -------------------------------------------------------------
    @staticmethod
    def build_feature_dataframe(
        mix: ConcreteMixDesign,
        ages: Tuple[int, int] = DEFAULT_AGES,
    ) -> pd.DataFrame:
        """
        Construye el DataFrame de evaluación con exactamente las 8 variables requeridas
        en el orden de la firma de MLflow, duplicando la dosificación para las edades de 7 y 28 días.

        Args:
            mix: Dosificación validada de 7 materiales en kg/m³.
            ages: Tupla con las edades de curado (por defecto 7 y 28 días).

        Returns:
            DataFrame con 2 filas y las 8 columnas en orden exacto.
        """
        rows = []
        for age in ages:
            row = {
                "cement": float(mix.cement),
                "blast_furnace_slag": float(mix.blast_furnace_slag),
                "fly_ash": float(mix.fly_ash),
                "water": float(mix.water),
                "superplasticizer": float(mix.superplasticizer),
                "coarse_aggregate": float(mix.coarse_aggregate),
                "fine_aggregate": float(mix.fine_aggregate),
                "age": int(age),
            }
            rows.append(row)

        df = pd.DataFrame(rows, columns=FEATURE_COLUMNS)
        # Asegurar tipos canónicos: float64 para insumos, int64 para edad
        for col in FEATURE_COLUMNS[:7]:
            df[col] = df[col].astype(np.float64)
        df["age"] = df["age"].astype(np.int64)

        return df

    # -------------------------------------------------------------
    # 2. Inferencia Predictiva Dual
    # -------------------------------------------------------------
    def predict(
        self,
        request_or_data: Union[PredictionRequest, ConcreteMixDesign, Dict[str, Any]],
    ) -> PredictionResponse:
        """
        Ejecuta el ciclo de inferencia dual completo para 7 y 28 días:
        1. Valida el dominio y formato de la dosificación (lanza DomainValidationError si es inválida).
        2. Obtiene el estimador en memoria desde el ModelLoader singleton.
        3. Construye el DataFrame en el orden estricto de la firma MLflow.
        4. Ejecuta inferencia vectorizada de ambas edades en una sola llamada.
        5. Verifica que las predicciones sean números finitos en MPa.
        6. Devuelve PredictionResponse con predicciones, ratios, advertencias y metadatos.

        Args:
            request_or_data: Instancia de PredictionRequest, ConcreteMixDesign o dict.

        Returns:
            PredictionResponse con predicciones determinísticas de resistencia a 7 y 28 días.

        Raises:
            DomainValidationError: Si la mezcla viola restricciones duras de dosificación.
            ModelNotFoundError: Si el modelo no ha sido cargado.
            IncompatibleRuntimeError: Si el entorno no puede deserializar el modelo.
            ModelInferenceError: Si ocurre un error numérico o de predicción inesperado.
        """
        # Extraer y validar datos sin modificar el objeto de solicitud original (inmutabilidad)
        if isinstance(request_or_data, PredictionRequest):
            raw_mix = request_or_data.mix_design
        elif isinstance(request_or_data, dict) and "mix_design" in request_or_data:
            raw_mix = request_or_data["mix_design"]
        else:
            raw_mix = request_or_data

        # 1. Validación de dominio
        mix_design, ratios, warnings = validate_or_raise(raw_mix)

        # 2. Acceso al estimador en memoria
        estimator = self._loader.get_model()

        # 3. Construcción del DataFrame conforme a la firma MLflow
        df_features = self.build_feature_dataframe(mix_design, ages=DEFAULT_AGES)

        # 4. Inferencia vectorizada
        try:
            raw_predictions = estimator.predict(df_features)
        except Exception as pred_err:
            raise ModelInferenceError(
                f"Error al ejecutar la inferencia sobre el estimador: {pred_err}"
            ) from pred_err

        # Normalizar salida a array NumPy unidimensional
        if hasattr(raw_predictions, "to_numpy"):
            preds_array = raw_predictions.to_numpy()
        elif isinstance(raw_predictions, (list, tuple)):
            preds_array = np.array(raw_predictions, dtype=np.float64)
        else:
            preds_array = np.asarray(raw_predictions, dtype=np.float64)

        preds_array = preds_array.flatten()
        if len(preds_array) < 2:
            raise ModelInferenceError(
                f"El estimador devolvió {len(preds_array)} predicciones; se esperaban exactamente 2 (7d y 28d)."
            )

        val_7d = float(preds_array[0])
        val_28d = float(preds_array[1])

        # 5. Verificación de finitud numérica
        if not math.isfinite(val_7d) or not math.isfinite(val_28d):
            raise ModelInferenceError(
                f"El modelo generó valores no finitos de resistencia (7d: {val_7d}, 28d: {val_28d})."
            )

        # 6. Metadatos de procedencia
        art_info = self._loader.get_artifact_info()
        if art_info is not None:
            model_id = art_info.run_id
            model_type = art_info.model_type
            model_sha = art_info.sha256
        else:
            model_id = OFFICIAL_RUN_ID
            model_type = OFFICIAL_ALGORITHM
            model_sha = OFFICIAL_MODEL_SHA256

        metadata = ModelMetadata(
            model_id=model_id,
            model_type=model_type,
            model_sha256=model_sha,
            inference_timestamp=datetime.now(timezone.utc).isoformat(),
        )

        # 7. Respuesta consolidada
        return PredictionResponse(
            status="success",
            predictions=StrengthPredictions(
                strength_7d_mpa=round(val_7d, 2),
                strength_28d_mpa=round(val_28d, 2),
            ),
            mix_ratios=ratios,
            warnings=warnings,
            metadata=metadata,
        )


# =====================================================================
# FACHADA PÚBLICA DEL SERVICIO DE INFERENCIA
# =====================================================================

_engine_instance: Optional[InferenceEngine] = None


def get_engine() -> InferenceEngine:
    """Retorna la instancia global del motor de inferencia."""
    global _engine_instance
    if _engine_instance is None:
        _engine_instance = InferenceEngine(ModelLoader.get_instance())
    return _engine_instance


def initialize_engine(
    model_path: Optional[Union[str, Path]] = None,
    expected_sha256: Optional[str] = OFFICIAL_MODEL_SHA256,
    force_reload: bool = False,
) -> bool:
    """
    Inicializa el motor precargando el estimador en memoria una sola vez.

    Returns:
        True si el modelo fue cargado exitosamente.

    Raises:
        ModelNotFoundError: Si el archivo no existe.
        ModelIntegrityError: Si el hash SHA-256 no coincide.
        IncompatibleRuntimeError: Si el entorno actual no soporta el modelo.
    """
    engine = get_engine()
    engine.loader.load_model(
        model_path=model_path,
        expected_sha256=expected_sha256,
        force_reload=force_reload,
    )
    return engine.loader.is_loaded()


def predict_concrete_strength(
    request_or_data: Union[PredictionRequest, ConcreteMixDesign, Dict[str, Any]],
) -> PredictionResponse:
    """
    Punto de entrada de alto nivel para consumir inferencias de resistencia a 7 y 28 días.
    Utilizable directamente por clientes Python o futuros adaptadores HTTP (FastAPI / ASP.NET).
    """
    engine = get_engine()
    return engine.predict(request_or_data)


def get_model_status() -> Dict[str, Any]:
    """
    Consulta el estado de disponibilidad, integridad y procedencia del modelo.
    Permite a los adaptadores de salud (/health) diagnosticar el estado del servicio.
    """
    loader = ModelLoader.get_instance()
    is_loaded = loader.is_loaded()
    art_info = loader.get_artifact_info()

    # Comprobar presencia física del artefacto
    artifact_exists = False
    resolved_path: Optional[str] = None
    sha_matches = False
    try:
        bin_path, _, _ = loader.resolve_artifact()
        artifact_exists = bin_path.exists()
        resolved_path = str(bin_path)
        sha_matches = loader.compute_sha256(bin_path) == OFFICIAL_MODEL_SHA256
    except Exception:
        pass

    return {
        "is_loaded": is_loaded,
        "artifact_exists_on_disk": artifact_exists,
        "resolved_binary_path": resolved_path,
        "official_sha256": OFFICIAL_MODEL_SHA256,
        "sha256_verified": sha_matches,
        "is_synthetic": getattr(loader, "_is_synthetic", False),
        "run_id": art_info.run_id if art_info else OFFICIAL_RUN_ID,
        "model_type": art_info.model_type if art_info else OFFICIAL_ALGORITHM,
        "python_runtime": art_info.python_version if art_info else "3.10.19",
        "sklearn_runtime": art_info.sklearn_version if art_info else "1.5.1",
    }
