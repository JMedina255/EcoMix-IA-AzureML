"""
Cargador seguro y singleton del modelo VotingEnsemble para EcoMix IA (Fase 5.3).
Provee:
- Resolución del artefacto real mediante metadatos declarativos de MLflow.
- Verificación estricta de identidad criptográfica SHA-256 previa a deserialización.
- Prevención de descargas no autorizadas e inyección de dependencias en caliente.
- Carga única por proceso con exclusión mutua thread-safe.
- Clasificación rigurosa de errores de disponibilidad, integridad y compatibilidad de runtime.
- Prohibición estricta de sustitución silenciosa del modelo certificado.
"""

from __future__ import annotations

import hashlib
import pickle
import sys
import threading
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union

try:
    import yaml
except ImportError:
    yaml = None  # type: ignore


# Hash SHA-256 oficial del artefacto model.pkl certificado en Azure ML (Job wheat_cheese_4swj34tkjn_11)
OFFICIAL_MODEL_SHA256 = "7eaa501c5eeb60135effb6b5861e736518ce969c47afd53727c2451083ff6388"
OFFICIAL_RUN_ID = "wheat_cheese_4swj34tkjn_11"
OFFICIAL_ALGORITHM = "VotingEnsemble"

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent


# =====================================================================
# JERARQUÍA DE EXCEPCIONES CONTROLADAS
# =====================================================================

class ModelInferenceError(Exception):
    """Excepción base para fallos relacionados con el motor de inferencia."""
    pass


class ModelNotFoundError(ModelInferenceError):
    """Lanzada cuando el archivo o directorio del modelo no existe en disco."""
    pass


class ModelIntegrityError(ModelInferenceError):
    """Lanzada cuando el artefacto binario está alterado o su SHA-256 no coincide con el certificado."""
    pass


class IncompatibleRuntimeError(ModelInferenceError):
    """Lanzada cuando el intérprete actual o las librerías no pueden deserializar el modelo oficial."""
    pass


# =====================================================================
# METADATOS Y ESPECIFICACIÓN DEL ARTEFACTO
# =====================================================================

@dataclass
class ModelArtifactInfo:
    """Información auditable del artefacto de modelo resuelto en disco."""
    binary_path: Path
    mlmodel_dir: Optional[Path]
    sha256: str
    run_id: str
    model_type: str
    python_version: Optional[str]
    sklearn_version: Optional[str]
    is_synthetic: bool = False


# =====================================================================
# CARGADOR SEGURO SINGLETON (ModelLoader)
# =====================================================================

class ModelLoader:
    """
    Gestor singleton para carga segura, verificación de integridad y retención en memoria
    del estimador VotingEnsemble.
    """

    _instance: Optional["ModelLoader"] = None
    _lock = threading.Lock()

    def __new__(cls) -> "ModelLoader":
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._initialized = False
        return cls._instance

    def __init__(self) -> None:
        if getattr(self, "_initialized", False):
            return
        self._model: Optional[Any] = None
        self._artifact_info: Optional[ModelArtifactInfo] = None
        self._is_synthetic: bool = False
        self._load_lock = threading.Lock()
        self._initialized = True

    @classmethod
    def get_instance(cls) -> "ModelLoader":
        """Retorna la instancia singleton de ModelLoader."""
        return cls()

    # -------------------------------------------------------------
    # 1. Resolución de Artefacto y Metadatos MLflow
    # -------------------------------------------------------------
    def resolve_artifact(
        self,
        model_path: Optional[Union[str, Path]] = None,
    ) -> Tuple[Path, Optional[Path], Dict[str, Any]]:
        """
        Resuelve la ubicación exacta del archivo binario del modelo a partir de los metadatos
        de MLflow o una ruta explícita.

        Args:
            model_path: Ruta a archivo .pkl, directorio con MLmodel, o None para búsqueda estándar.

        Returns:
            Tupla (binary_path, mlmodel_dir, metadata_dict).

        Raises:
            ModelNotFoundError: Si el modelo no existe o no se encuentra en disco.
            ValueError: Si existen múltiples binarios sin MLmodel rector.
        """
        target_path: Optional[Path] = None

        if model_path is not None:
            p = Path(model_path).resolve()
            if not p.exists():
                raise ModelNotFoundError(f"La ruta del modelo especificada no existe: {p}")
            target_path = p
        else:
            # Buscar en el directorio models/ del proyecto
            models_dir = PROJECT_ROOT / "models"
            if not models_dir.exists():
                raise ModelNotFoundError(f"El directorio de modelos no existe en: {models_dir}")

            # 1. Buscar MLmodel en estructura conocida de Model Asset
            candidate_mlmodels = list(models_dir.rglob("MLmodel"))
            if candidate_mlmodels:
                # Preferir el que corresponda al run ganador si existe
                winner_matches = [
                    m for m in candidate_mlmodels if OFFICIAL_RUN_ID in str(m)
                ]
                target_path = (winner_matches[0] if winner_matches else candidate_mlmodels[0]).parent
            else:
                # Buscar binarios .pkl directamente
                pkls = list(models_dir.rglob("*.pkl"))
                if pkls:
                    winner_pkls = [p for p in pkls if OFFICIAL_RUN_ID in str(p)]
                    target_path = winner_pkls[0] if winner_pkls else pkls[0]
                else:
                    raise ModelNotFoundError(
                        f"No se encontró ningún artefacto MLmodel ni model.pkl en: {models_dir}"
                    )

        mlmodel_dir: Optional[Path] = None
        target_binary: Optional[Path] = None
        meta: Dict[str, Any] = {}

        if target_path.is_dir():
            mlmodel_file = target_path / "MLmodel"
            if not mlmodel_file.exists():
                sub_ml = list(target_path.rglob("MLmodel"))
                if sub_ml:
                    mlmodel_file = sub_ml[0]

            if mlmodel_file.exists():
                mlmodel_dir = mlmodel_file.parent
                if yaml is not None:
                    try:
                        with open(mlmodel_file, "r", encoding="utf-8") as f:
                            meta = yaml.safe_load(f) or {}
                    except Exception as e:
                        raise ValueError(f"Error al parsear '{mlmodel_file}': {e}") from e

                flavors = meta.get("flavors", {})
                sklearn_fl = flavors.get("sklearn", {})
                pyfunc_fl = flavors.get("python_function", {})

                bin_name = (
                    sklearn_fl.get("pickled_model")
                    or sklearn_fl.get("model_data")
                    or pyfunc_fl.get("model_path")
                    or "model.pkl"
                )
                target_binary = mlmodel_dir / bin_name
                if not target_binary.exists():
                    raise ModelNotFoundError(
                        f"El binario '{bin_name}' declarado en '{mlmodel_file}' no existe en '{mlmodel_dir}'."
                    )
            else:
                # Directorio sin MLmodel
                binaries = list(target_path.glob("*.pkl")) + list(target_path.glob("*.joblib"))
                if not binaries:
                    binaries = list(target_path.rglob("*.pkl")) + list(target_path.rglob("*.joblib"))

                if not binaries:
                    raise ModelNotFoundError(f"No se hallaron binarios en: {target_path}")
                elif len(binaries) > 1:
                    raise ValueError(
                        f"Múltiples binarios detectados en '{target_path}' sin archivo MLmodel rector."
                    )
                target_binary = binaries[0]
        else:
            target_binary = target_path
            if target_binary.parent.name == "mlflow-model" and (target_binary.parent / "MLmodel").exists():
                mlmodel_dir = target_binary.parent

        return target_binary, mlmodel_dir, meta

    # -------------------------------------------------------------
    # 2. Verificación Estricta de Integridad Criptográfica (SHA-256)
    # -------------------------------------------------------------
    @staticmethod
    def compute_sha256(file_path: Path) -> str:
        """Calcula el hash SHA-256 de un archivo en bloques de 64 KB."""
        sha256_hash = hashlib.sha256()
        with open(file_path, "rb") as f:
            for byte_block in iter(lambda: f.read(65536), b""):
                sha256_hash.update(byte_block)
        return sha256_hash.hexdigest().lower()

    def verify_integrity(
        self,
        binary_path: Path,
        expected_sha256: Optional[str] = OFFICIAL_MODEL_SHA256,
    ) -> str:
        """
        Verifica que el hash del binario coincida con el hash esperado antes de deserializar.

        Raises:
            ModelIntegrityError: Si el hash no coincide.
        """
        actual_hash = self.compute_sha256(binary_path)
        if expected_sha256 is not None:
            expected_clean = expected_sha256.strip().lower()
            if actual_hash != expected_clean:
                raise ModelIntegrityError(
                    f"Fallo de integridad criptográfica en el modelo '{binary_path.name}'. "
                    f"Hash actual: '{actual_hash}', Hash oficial certificado: '{expected_clean}'."
                )
        return actual_hash

    # -------------------------------------------------------------
    # 3. Deserialización Segura y Retención en Memoria
    # -------------------------------------------------------------
    def load_model(
        self,
        model_path: Optional[Union[str, Path]] = None,
        expected_sha256: Optional[str] = OFFICIAL_MODEL_SHA256,
        force_reload: bool = False,
    ) -> Any:
        """
        Carga el modelo en memoria de forma segura y thread-safe.

        Flujo:
        1. Si ya está cargado y no se solicita recarga, retorna la instancia en RAM.
        2. Resuelve el binario a través de los metadatos MLflow.
        3. Verifica el hash SHA-256.
        4. Deserializa el estimador capturando incompatibilidades de runtime.

        Raises:
            ModelNotFoundError: Si el archivo no existe.
            ModelIntegrityError: Si el hash SHA-256 no coincide.
            IncompatibleRuntimeError: Si faltan librerías como azureml-training-tabular o scikit-learn compatible.
        """
        with self._load_lock:
            if self._model is not None and not force_reload:
                return self._model

            # 1. Resolución
            binary_path, mlmodel_dir, meta = self.resolve_artifact(model_path)

            # 2. Integridad previa a deserialización
            actual_sha = self.verify_integrity(binary_path, expected_sha256)

            # Extraer versiones declaradas
            py_ver = (
                meta.get("flavors", {}).get("python_function", {}).get("python_version")
                or "3.10.19"
            )
            sk_ver = (
                meta.get("flavors", {}).get("sklearn", {}).get("sklearn_version")
                or "1.5.1"
            )
            run_id = meta.get("run_id", OFFICIAL_RUN_ID)

            # 3. Deserialización
            try:
                with open(binary_path, "rb") as f:
                    loaded_estimator = pickle.load(f)
            except (ModuleNotFoundError, ImportError) as imp_err:
                current_py = f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}"
                raise IncompatibleRuntimeError(
                    f"Incompatibilidad de dependencias de runtime al deserializar el modelo oficial: {imp_err}. "
                    f"El artefacto '{binary_path.name}' (SHA-256: {actual_sha}) fue generado bajo Python {py_ver} "
                    f"con scikit-learn {sk_ver} y clases de Azure AutoML Tabular (azureml-training-tabular). "
                    f"El entorno de ejecución actual es Python {current_py}."
                ) from imp_err
            except Exception as ex:
                raise IncompatibleRuntimeError(
                    f"Error no recuperable al deserializar el binario '{binary_path.name}': {type(ex).__name__}: {ex}"
                ) from ex

            self._model = loaded_estimator
            self._is_synthetic = False
            self._artifact_info = ModelArtifactInfo(
                binary_path=binary_path,
                mlmodel_dir=mlmodel_dir,
                sha256=actual_sha,
                run_id=run_id,
                model_type=OFFICIAL_ALGORITHM,
                python_version=py_ver,
                sklearn_version=sk_ver,
                is_synthetic=False,
            )

            return self._model

    # -------------------------------------------------------------
    # 4. Gestión de Estado, Inyección de Pruebas y Reseteo
    # -------------------------------------------------------------
    def is_loaded(self) -> bool:
        """Indica si existe un modelo instanciado en memoria RAM."""
        return self._model is not None

    def get_model(self) -> Any:
        """
        Retorna el estimador cargado en memoria.
        Lanza ModelNotFoundError si no ha sido inicializado.
        """
        if self._model is None:
            raise ModelNotFoundError(
                "El modelo predictivo no ha sido cargado en memoria. "
                "Llame a 'load_model()' o 'initialize_engine()' antes de solicitar inferencias."
            )
        return self._model

    def get_artifact_info(self) -> Optional[ModelArtifactInfo]:
        """Retorna la ficha técnica del artefacto actualmente cargado."""
        return self._artifact_info

    def set_test_estimator(
        self,
        estimator: Any,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> None:
        """
        Inyecta explícitamente un estimador para pruebas unitarias.
        Marca 'is_synthetic = True' para evitar ambigüedades con el modelo certificado.
        """
        with self._load_lock:
            self._model = estimator
            self._is_synthetic = True
            meta = metadata or {}
            self._artifact_info = ModelArtifactInfo(
                binary_path=Path("synthetic://test-estimator"),
                mlmodel_dir=None,
                sha256="0" * 64,
                run_id=meta.get("run_id", "test_synthetic_run"),
                model_type=meta.get("model_type", "SyntheticEstimator"),
                python_version=meta.get("python_version", sys.version.split()[0]),
                sklearn_version=meta.get("sklearn_version", "test"),
                is_synthetic=True,
            )

    def reset(self) -> None:
        """Limpia el estado en memoria para aislamiento entre pruebas."""
        with self._load_lock:
            self._model = None
            self._artifact_info = None
            self._is_synthetic = False
