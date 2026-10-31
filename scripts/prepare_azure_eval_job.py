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
EXPECTED_WINNER_CHILD_RUN = "wheat_cheese_4swj34tkjn_11"
EXPECTED_ENVIRONMENT_IMAGE = "mcr.microsoft.com/azureml/curated/ai-ml-automl:41"
EXPECTED_COMPUTE_CLUSTER = "azureml:cpu-cluster-ecomix"
EXPECTED_TIMEOUT_SECONDS = 1800
EXPECTED_INSTANCE_COUNT = 1

PROBE_FORBIDDEN_FILES = [
    # 1. Credenciales y secretos
    "config.json",
    ".env",
    ".env.local",
    "prod.env",
    "secrets/credentials.key",
    "id_rsa.pem",
    "tokens/access.token",
    # 2. Entornos virtuales
    ".venv/bin/python",
    ".venv/Scripts/python.exe",
    ".venv/Lib/site-packages/sklearn.py",
    "venv/bin/activate",
    "env/bin/python",
    "ENV/bin/python",
    # 3. Modelos binarios locales
    "models/model.pkl",
    "models/winner/model.pkl",
    "nested/models/estimator.joblib",
    "models/weights.onnx",
    "model.pkl",
    "weights.joblib",
    # 4. Datasets (se proveen vía Data Assets e Inputs independientes)
    "data/raw/concrete_raw.csv",
    "data/processed/concrete_test.csv",
    "data/processed/concrete_train.csv",
    "dataset/concrete.csv",
]

PROBE_REQUIRED_FILES = [
    "src/evaluate_model.py",
    "src/utils.py",
    "src/__init__.py",
]


class SnapshotExclusionEvaluator:
    """
    Evaluador no destructivo de reglas de exclusión para empaquetado de código en Azure ML.
    Utiliza el mecanismo oficial del Azure ML SDK (azure.ai.ml._artifacts._artifact_utilities.get_ignore_file)
    cuando está disponible, y dispone de un evaluador gitignore puro en Python como respaldo garantizado.
    """
    def __init__(self, repo_root: Path):
        self.repo_root = Path(repo_root).resolve()
        self.amlignore_path = self.repo_root / ".amlignore"
        self.sdk_ignore_file = None
        self.patterns: List[str] = []
        self.engine_name = "fallback_pure_python"

        if self.amlignore_path.exists():
            try:
                from azure.ai.ml._artifacts._artifact_utilities import get_ignore_file
                ignore_obj = get_ignore_file(self.repo_root)
                if ignore_obj and ignore_obj.exists():
                    self.sdk_ignore_file = ignore_obj
                    self.engine_name = "azure_ml_sdk"
            except Exception:
                pass

            try:
                content = self.amlignore_path.read_text(encoding="utf-8")
                for line in content.splitlines():
                    line = line.strip()
                    if line and not line.startswith("#"):
                        self.patterns.append(line)
            except Exception:
                pass

    def is_path_excluded(self, rel_or_abs_path: Union[str, Path]) -> bool:
        """Determina si una ruta relativa o absoluta es excluida del paquete de código."""
        p = Path(rel_or_abs_path)
        if not p.is_absolute():
            abs_p = (self.repo_root / p).resolve()
            rel_str = str(p).replace("\\", "/")
        else:
            abs_p = p.resolve()
            try:
                rel_str = str(abs_p.relative_to(self.repo_root)).replace("\\", "/")
            except ValueError:
                rel_str = str(p).replace("\\", "/")

        # 1. Usar Azure ML SDK si está disponible
        if self.sdk_ignore_file is not None:
            try:
                return bool(self.sdk_ignore_file.is_file_excluded(abs_p))
            except Exception:
                pass

        # 2. Respaldo determinístico puro en Python conforme a reglas de gitignore/.amlignore
        return self._pure_python_is_excluded(rel_str)

    def _pure_python_is_excluded(self, rel_str: str) -> bool:
        import fnmatch
        rel_str = rel_str.strip("/")
        parts = rel_str.split("/")

        for pat in self.patterns:
            pat = pat.strip()
            if not pat or pat.startswith("#"):
                continue

            # Regla de directorio (termina con /)
            if pat.endswith("/"):
                clean_dir = pat.rstrip("/")
                for part in parts:
                    if fnmatch.fnmatch(part, clean_dir):
                        return True
                continue

            # Regla con separador de ruta interno
            if "/" in pat:
                if fnmatch.fnmatch(rel_str, pat) or fnmatch.fnmatch(rel_str, "*/" + pat):
                    return True
            else:
                # Coincidencia con nombre de archivo o cualquier componente de ruta
                for part in parts:
                    if fnmatch.fnmatch(part, pat):
                        return True

        return False


def audit_code_snapshot_exclusions(repo_root: Path) -> Tuple[bool, List[str], Dict[str, Any]]:
    """
    Auditoría no destructiva del empaquetado de código para Azure ML Command Job.
    Valida:
      1. Presencia física de '.amlignore'.
      2. Que ningún archivo confidencial (config.json, .env, *.key, *.token) sea empaquetado.
      3. Que los entornos virtuales (.venv, venv, env) sean excluidos.
      4. Que los modelos binarios locales (models/, *.pkl, *.joblib, *.onnx) sean excluidos.
      5. Que los datasets locales (data/, dataset/) sean excluidos (se entregan vía Data Assets).
      6. Que los scripts esenciales de código fuente ('src/evaluate_model.py', 'src/utils.py')
         permanezcan estrictamente incluidos.
      7. Inspección de archivos reales existentes en el workspace.
    """
    issues: List[str] = []
    repo_root = Path(repo_root).resolve()
    amlignore_path = repo_root / ".amlignore"

    if not amlignore_path.exists():
        issues.append(
            "Falta el archivo '.amlignore' en la raíz del proyecto. "
            "Es indispensable para evitar la carga accidental de secretos y modelos locales en Azure ML."
        )
        return False, issues, {
            "amlignore_exists": False,
            "engine_used": "none",
            "forbidden_probes_tested": 0,
            "required_probes_tested": 0
        }

    evaluator = SnapshotExclusionEvaluator(repo_root)

    # Comprobación de contenido básico de .amlignore
    try:
        amlignore_content = amlignore_path.read_text(encoding="utf-8")
        required_patterns = ["config.json", ".env", "models/", ".venv", "*.pkl"]
        for req in required_patterns:
            if req not in amlignore_content:
                issues.append(
                    f"La regla de exclusión obligatoria '{req}' no se encuentra definida en '.amlignore'."
                )
    except Exception as e:
        issues.append(f"Error al leer '.amlignore': {e}")

    # Auditoría con sondas controladas de archivos prohibidos
    forbidden_failures = []
    for probe in PROBE_FORBIDDEN_FILES:
        if not evaluator.is_path_excluded(probe):
            forbidden_failures.append(probe)
            issues.append(
                f"Fallo de empaquetado: El archivo sensible o binario '{probe}' sería incluido en el snapshot de Azure ML."
            )

    # Auditoría con sondas controladas de archivos requeridos (código fuente)
    required_failures = []
    for req in PROBE_REQUIRED_FILES:
        if evaluator.is_path_excluded(req):
            required_failures.append(req)
            issues.append(
                f"Fallo de empaquetado: El código fuente esencial '{req}' sería erróneamente excluido del snapshot de Azure ML."
            )

    # Auditoría de archivos reales presentes en el workspace
    real_files_audited = 0
    real_forbidden_leaks = []

    # 1. config.json y .env locales reales
    for real_name in ["config.json", ".env"]:
        p = repo_root / real_name
        if p.exists():
            real_files_audited += 1
            if not evaluator.is_path_excluded(p):
                real_forbidden_leaks.append(real_name)
                issues.append(f"Fuga detectada: Archivo real local '{real_name}' no está excluido por .amlignore.")

    # 2. Binarios en models/ reales
    models_dir = repo_root / "models"
    if models_dir.exists():
        for b in models_dir.rglob("*"):
            if b.is_file():
                real_files_audited += 1
                if not evaluator.is_path_excluded(b):
                    rel = str(b.relative_to(repo_root)).replace("\\", "/")
                    real_forbidden_leaks.append(rel)
                    issues.append(f"Fuga de modelo detectada: '{rel}' sería subido en el snapshot de código.")

    # 3. Datasets en data/ reales
    data_dir = repo_root / "data"
    if data_dir.exists():
        for d in data_dir.rglob("*"):
            if d.is_file():
                real_files_audited += 1
                if not evaluator.is_path_excluded(d):
                    rel = str(d.relative_to(repo_root)).replace("\\", "/")
                    real_forbidden_leaks.append(rel)
                    issues.append(f"Fuga de dataset detectada: '{rel}' sería subido en el snapshot de código.")

    is_valid = len(issues) == 0
    audit_details = {
        "amlignore_exists": True,
        "engine_used": evaluator.engine_name,
        "forbidden_probes_tested": len(PROBE_FORBIDDEN_FILES),
        "forbidden_probes_excluded": len(forbidden_failures) == 0,
        "required_probes_tested": len(PROBE_REQUIRED_FILES),
        "required_probes_included": len(required_failures) == 0,
        "real_workspace_files_audited": real_files_audited,
        "real_workspace_leaks_detected": len(real_forbidden_leaks)
    }

    return is_valid, issues, audit_details


def check_code_snapshot_security(repo_root: Path) -> Tuple[bool, List[str]]:
    """
    Función de compatibilidad que verifica que el empaquetado del código ('code: ../')
    no incluya secretos, modelos binarios ni entornos virtuales.
    """
    is_valid, issues, _ = audit_code_snapshot_exclusions(repo_root)
    return is_valid, issues


def compute_file_sha256(file_path: Path, normalize_newlines: bool = True) -> str:
    """
    Calcula el hash SHA-256 de un archivo para verificación de integridad.
    Para archivos de datos/texto (.csv, .txt, .json, .yml, .yaml, .md, .py), normaliza saltos de línea
    (CRLF -> LF) garantizando un hash determinístico idéntico en Windows, Linux y macOS.
    Para binarios (.pkl, .joblib, etc.), procesa los bytes brutos sin alteración.
    """
    p = Path(file_path)
    text_extensions = {".csv", ".txt", ".json", ".yml", ".yaml", ".md", ".py"}
    is_text = p.suffix.lower() in text_extensions

    if normalize_newlines and is_text:
        content = p.read_bytes().replace(b"\r\n", b"\n")
        return hashlib.sha256(content).hexdigest()

    sha = hashlib.sha256()
    with open(p, "rb") as f:
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

    # 0. Verificación de seguridad del empaquetado de código (code: ../)
    code_val = job_spec.get("code", "")
    code_dir = (job_yaml_path.parent / code_val).resolve()
    sec_ok, sec_issues, audit_details = audit_code_snapshot_exclusions(code_dir)
    metadata["code_snapshot_security_valid"] = sec_ok
    metadata["code_snapshot_audit"] = audit_details
    if not sec_ok:
        errors.extend(sec_issues)

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

        # Tag de procedencia del ganador
        tags = job_spec.get("tags", {})
        winner_tag = tags.get("winner_child_run")
        if winner_tag != EXPECTED_WINNER_CHILD_RUN:
            errors.append(f"Tag 'winner_child_run' inesperado: '{winner_tag}' (se esperaba '{EXPECTED_WINNER_CHILD_RUN}').")

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

    if train_data_path is not None:
        if train_data_path.exists():
            actual_train_sha = compute_file_sha256(train_data_path)
            metadata["actual_train_sha256"] = actual_train_sha
        else:
            errors.append(f"No existe el archivo de entrenamiento local en: {train_data_path} para auditoría de solapamiento.")

    # 6. Command
    command = job_spec.get("command", "")
    if "evaluate_model.py" not in command or "--evaluate" not in command or "--strict-checksums" not in command:
        errors.append(f"El comando debe invocar 'evaluate_model.py --evaluate --strict-checksums': '{command}'.")
    metadata["command"] = command

    # 7. Limits & Resources (Esquema oficial: limits.timeout en segundos)
    limits = job_spec.get("limits", {})
    if not isinstance(limits, dict):
        errors.append("La sección 'limits' debe ser un diccionario.")
    else:
        if "timeout_minutes" in limits:
            errors.append(
                "Campo obsoleto/no oficial 'timeout_minutes' detectado en limits. "
                "El esquema oficial de Azure ML Command Job requiere 'limits.timeout' en segundos (ej. 1800)."
            )
        timeout_seconds = limits.get("timeout")
        if timeout_seconds != EXPECTED_TIMEOUT_SECONDS:
            errors.append(
                f"Límite de tiempo inesperado: {timeout_seconds} segundos (se esperaba {EXPECTED_TIMEOUT_SECONDS} s / 30 min)."
            )
        metadata["timeout_seconds"] = timeout_seconds

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

    # 9. Validación con el esquema oficial de Azure ML SDK (si la biblioteca está disponible)
    try:
        from azure.ai.ml import load_job
        try:
            sdk_job = load_job(source=str(job_yaml_path))
            metadata["sdk_schema_validated"] = True
            metadata["sdk_job_type"] = type(sdk_job).__name__
        except Exception as sdk_err:
            metadata["sdk_schema_validated"] = False
            errors.append(f"Fallo en validación de esquema oficial Azure ML SDK: {sdk_err}")
    except ImportError:
        metadata["sdk_schema_validated"] = None

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
    timeout_s = metadata.get("timeout_seconds")
    timeout_str = f"{timeout_s} s ({timeout_s // 60} min)" if timeout_s else "No definido"
    print(f" Timeout Máximo:       {timeout_str}")
    print(f" Instancias Cómputo:   {metadata.get('instance_count')} (CPU única)")
    print(f" Outputs Definidos:    {', '.join(metadata.get('outputs', []))}")
    if metadata.get("sdk_schema_validated") is True:
        print(f" Validación SDK:       Compatible con esquema oficial Azure ML CommandJob")
    if "code_snapshot_audit" in metadata:
        audit = metadata["code_snapshot_audit"]
        sec_label = "[PROTEGIDO]" if metadata.get("code_snapshot_security_valid") else "[VULNERABILIDAD DETECTADA]"
        print(f" Seguridad Snapshot:   {sec_label}")
        print(f"   * Motor de Reglas:  {audit.get('engine_used')}")
        print(f"   * Sondas Secretos:  {audit.get('forbidden_probes_tested')} probadas ({'100% excluidas' if audit.get('forbidden_probes_excluded') else 'FALLO DE EXCLUSIÓN'})")
        print(f"   * Código Esencial:  {audit.get('required_probes_tested')} verificados ({'100% incluidos' if audit.get('required_probes_included') else 'FALLO DE INCLUSIÓN'})")
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
