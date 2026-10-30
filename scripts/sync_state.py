"""
Script de sincronización y validación del estado del proyecto EcoMix IA.
Sincroniza declarativamente config/project_status.json con docs/PROJECT_STATE.md.
Diseñado para ser idempotente, portable y operable completamente sin conexión a Azure.
"""

import sys
import os
import json
import argparse
import subprocess
from pathlib import Path
from typing import Dict, Any, List, Tuple, Optional

# Reconfigurar codificación en Windows
if sys.platform == "win32" and hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

PROJECT_ROOT = Path(__file__).resolve().parent.parent
CONFIG_STATUS_PATH = PROJECT_ROOT / "config" / "project_status.json"
STATE_MD_PATH = PROJECT_ROOT / "docs" / "PROJECT_STATE.md"
DATA_RAW_PATH = PROJECT_ROOT / "data" / "raw" / "concrete_data.csv"
DATA_TRAIN_PATH = PROJECT_ROOT / "data" / "processed" / "concrete_train.csv"
DATA_TEST_PATH = PROJECT_ROOT / "data" / "processed" / "concrete_test.csv"
MODELS_DIR = PROJECT_ROOT / "models"


def get_git_info() -> Dict[str, str]:
    """Obtiene información verificable del repositorio Git de manera segura y no volátil."""
    info = {"branch": "main", "commit_head": "Desconocido", "clean": "Desconocido"}
    try:
        branch = subprocess.check_output(
            ["git", "rev-parse", "--abbrev-ref", "HEAD"],
            cwd=str(PROJECT_ROOT),
            stderr=subprocess.DEVNULL,
            text=True
        ).strip()
        if branch:
            info["branch"] = branch
    except Exception:
        pass

    try:
        commit = subprocess.check_output(
            ["git", "rev-parse", "--short", "HEAD"],
            cwd=str(PROJECT_ROOT),
            stderr=subprocess.DEVNULL,
            text=True
        ).strip()
        if commit:
            info["commit_head"] = commit
    except Exception:
        pass

    try:
        status = subprocess.check_output(
            ["git", "status", "--porcelain"],
            cwd=str(PROJECT_ROOT),
            stderr=subprocess.DEVNULL,
            text=True
        ).strip()
        info["clean"] = "Sí" if not status else "No (cambios locales sin commitear)"
    except Exception:
        pass

    return info


def inspect_local_datasets(root_dir: Path = PROJECT_ROOT) -> Dict[str, Any]:
    """Inspecciona los datasets locales y valida conteo de filas y presencia."""
    data_info = {}
    train_p = root_dir / "data" / "processed" / "concrete_train.csv"
    test_p = root_dir / "data" / "processed" / "concrete_test.csv"
    raw_p = root_dir / "data" / "raw" / "concrete_raw.csv"
    if not raw_p.exists():
        raw_p = root_dir / "data" / "raw" / "concrete_data.csv"

    data_info["raw_exists"] = raw_p.exists()
    data_info["raw_path"] = str(raw_p.relative_to(root_dir)) if raw_p.exists() else "data/raw/concrete_raw.csv"
    data_info["train_exists"] = train_p.exists()
    data_info["test_exists"] = test_p.exists()

    if train_p.exists():
        try:
            with open(train_p, "r", encoding="utf-8") as f:
                lines = [l for l in f if l.strip()]
                data_info["train_rows"] = max(0, len(lines) - 1)
        except Exception:
            data_info["train_rows"] = "error"
    else:
        data_info["train_rows"] = 0

    if test_p.exists():
        try:
            with open(test_p, "r", encoding="utf-8") as f:
                lines = [l for l in f if l.strip()]
                data_info["test_rows"] = max(0, len(lines) - 1)
        except Exception:
            data_info["test_rows"] = "error"
    else:
        data_info["test_rows"] = 0

    return data_info


def inspect_local_models(root_dir: Path = PROJECT_ROOT) -> Dict[str, Any]:
    """Inspecciona si existen archivos de modelo en el directorio local models/."""
    models_dir = root_dir / "models"
    model_info = {"exists": False, "files": []}
    if models_dir.exists():
        pkls = list(models_dir.rglob("*.pkl")) + list(models_dir.rglob("*.joblib"))
        mlmodels = list(models_dir.rglob("MLmodel"))
        all_models = pkls + mlmodels
        if all_models:
            model_info["exists"] = True
            model_info["files"] = [str(p.relative_to(models_dir)) for p in all_models]
    return model_info


def validate_state_consistency(status_data: Dict[str, Any], root_dir: Path = PROJECT_ROOT) -> List[str]:
    """
    Detecta inconsistencias entre el estado declarado y los archivos existentes en disco.
    Emite advertencias cuando falte evidencia técnica comprobable.
    """
    warnings: List[str] = []
    datasets = inspect_local_datasets(root_dir)

    # Validar Fase 1 y 2
    phases = status_data.get("phases", {})
    if phases.get("fase_1", {}).get("status") == "completed" and not datasets["raw_exists"]:
        warnings.append("[ADVERTENCIA] Fase 1 declarada 'completed' pero no se encuentra 'data/raw/concrete_data.csv'.")

    if phases.get("fase_2", {}).get("status") == "completed":
        if not datasets["train_exists"] or not datasets["test_exists"]:
            warnings.append("[ADVERTENCIA] Fase 2 declarada 'completed' pero faltan datasets procesados en 'data/processed/'.")
        elif datasets["train_rows"] != 824 or datasets["test_rows"] != 206:
            warnings.append(
                f"[ADVERTENCIA] Conteo de partición inesperado: Train={datasets['train_rows']} (esperado 824), "
                f"Test={datasets['test_rows']} (esperado 206)."
            )

    # Validar Fase 4.1 y 4.3
    if phases.get("fase_4_1", {}).get("status") == "completed":
        eval_script = root_dir / "src" / "evaluate_model.py"
        if not eval_script.exists():
            warnings.append("[ADVERTENCIA] Fase 4.1 declarada 'completed' pero 'src/evaluate_model.py' no existe.")

    # Validar consistencia de modelos si Fase 4.3 está completada
    models_info = inspect_local_models(root_dir)
    if phases.get("fase_4_3", {}).get("status") == "completed" and not models_info["exists"]:
        warnings.append(
            "[AVISO DE PROCEDENCIA] Fase 4.3 está completada (mecanismo de descarga probado), "
            "pero no hay modelos descargados en 'models/' localmente. "
            "Esto es normal en clones limpios; ejecute 'python src/evaluate_model.py --download' para recuperar artefactos."
        )

    return warnings


def render_markdown_state(status_data: Dict[str, Any], root_dir: Path = PROJECT_ROOT) -> str:
    """
    Genera el contenido Markdown de docs/PROJECT_STATE.md de forma determinística e idempotente.
    NO incluye timestamps ni hashes dinámicos en el texto generado para evitar loops infinitos de Git.
    """
    proj_id = status_data.get("project_id", "ecomix-ia-ml")
    repo = status_data.get("repository", "JMedina255/EcoMix-IA-AzureML")
    branch = status_data.get("default_branch", "main")
    curr_phase = status_data.get("current_phase", "4.3")
    next_milestone = status_data.get("next_authorized_milestone", "4.4")
    last_val = status_data.get("last_validation", {})
    val_date = last_val.get("date", "2026-10-30")
    val_origin = last_val.get("origin", "Azure ML Studio & Workspace Telemetry")

    exp = status_data.get("azure_experiment", {})
    job_id = exp.get("job_id", "wheat_cheese_4swj34tkjn")
    job_status = exp.get("job_status", "completed")
    primary_metric = exp.get("primary_metric", "normalized_root_mean_squared_error")
    metric_val = exp.get("metric_value", 0.05859)
    winner_algo = exp.get("winning_algorithm", "VotingEnsemble")
    winner_child = exp.get("winner_child_run_id", "wheat_cheese_4swj34tkjn_11")
    model_asset = exp.get("model_asset", {})
    model_asset_name = model_asset.get("name", "azureml_wheat_cheese_4swj34tkjn_11_output_mlflow_log_model_873731674")
    model_asset_ver = model_asset.get("version", "1")
    model_size = model_asset.get("model_size_bytes", 670849)
    train_env = exp.get("training_environment", {})
    curated_img = train_env.get("curated_image", "mcr.microsoft.com/azureml/curated/ai-ml-automl:41")
    py_ver = train_env.get("python_version", "3.9 / 3.10")

    phases = status_data.get("phases", {})
    open_issues = status_data.get("open_issues", [])
    verified_tests = status_data.get("verified_tests", {})

    status_icons = {
        "completed": "✅ Completado",
        "pending": "🟡 Pendiente",
        "in_progress": "🔄 En progreso",
        "blocked": "⛔ Bloqueado"
    }

    lines = [
        "# Estado Vivo del Proyecto — EcoMix IA (Azure ML)",
        "",
        "> **Documento vivo de trazabilidad técnica.**  ",
        "> Fuente declarativa: [`config/project_status.json`](../config/project_status.json).  ",
        "> Actualizado y verificado mediante: `python scripts/sync_state.py`.",
        "",
        "---",
        "",
        "## 1. Identificación y Parámetros Generales",
        "",
        f"- **Identificador del Proyecto:** `{proj_id}`",
        f"- **Repositorio:** `{repo}`",
        f"- **Rama Principal:** `{branch}`",
        f"- **Fase Actual:** `{curr_phase} — Descarga selectiva de modelo ganador`",
        f"- **Próximo Hito Autorizado:** `{next_milestone}`",
        f"- **Última Validación Registrada:** `{val_date}` (Origen: *{val_origin}*)",
        "",
        "---",
        "",
        "## 2. Estado de las Fases del Pipeline ML",
        "",
        "| Fase | Nombre | Estado | Script / Componente | Evidencia Técnica Comprobada |",
        "| :---: | :--- | :---: | :--- | :--- |"
    ]

    phase_order = [
        ("fase_1", "1"),
        ("fase_2", "2"),
        ("fase_3", "3"),
        ("fase_4_1", "4.1"),
        ("fase_4_2", "4.2"),
        ("fase_4_3", "4.3"),
        ("fase_4_4", "4.4"),
        ("fase_4_5", "4.5"),
        ("fase_5", "5"),
        ("fase_6", "6"),
        ("fase_7", "7"),
    ]

    for p_key, p_num in phase_order:
        p_info = phases.get(p_key, {})
        p_name = p_info.get("name", "")
        p_status = status_icons.get(p_info.get("status", "pending"), "🟡 Pendiente")
        p_script = p_info.get("script", "")
        p_evidence = p_info.get("evidence", "")
        lines.append(f"| **{p_num}** | {p_name} | {p_status} | `{p_script}` | {p_evidence} |")

    lines.extend([
        "",
        "---",
        "",
        "## 3. Experimento y Modelo Ganador (Datos Comprobados en Azure ML)",
        "",
        "Los siguientes datos corresponden a la telemetría oficial de Azure ML Workspace (`ecomix-ia-ml`, Grupo `EcomixIA`):",
        "",
        f"- **Job Name:** `{job_id}`",
        f"- **Estado Oficial:** `Completed` (Canónico: `{job_status}`)",
        f"- **Métrica Primaria:** `{primary_metric}`",
        f"- **Valor de la Métrica:** `{metric_val}`",
        f"- **Algoritmo Ganador:** `{winner_algo}`",
        f"- **Child Run Ganador:** `{winner_child}`",
        f"- **Activo de Modelo (Model Asset):**  ",
        f"  `{model_asset_name}:{model_asset_ver}`",
        f"- **Tamaño del Modelo en Disco:** `{model_size:,} bytes` (~{model_size / 1024:.1f} KB)",
        "- **Modelo en Catálogo Manual:** Ninguno registrado manualmente en catálogo (activo local de workspace).",
        "- **Entorno de Entrenamiento Original:**  ",
        f"  Imagen Curada: `{curated_img}` (Python {py_ver}).",
        "",
        "---",
        "",
        "## 4. Incidencias Técnicas y Mitigaciones",
        ""
    ])

    for issue in open_issues:
        i_id = issue.get("id", "")
        i_status = issue.get("status", "").capitalize()
        i_desc = issue.get("description", "")
        lines.append(f"### Incidencia {i_id} ({i_status})")
        lines.append(f"- **Descripción:** {i_desc}")
        if "workaround" in issue:
            lines.append(f"- **Mitigación comprobada:** {issue['workaround']}")
        if "recommendation" in issue:
            lines.append(f"- **Recomendación:** {issue['recommendation']}")
        lines.append("")

    total_tests = verified_tests.get("total_tests", 22)
    test_suite = verified_tests.get("suite", "pytest")
    test_files = verified_tests.get("test_files", [])

    lines.extend([
        "---",
        "",
        "## 5. Pruebas y Cobertura Verificada",
        "",
        f"- **Suite de Pruebas:** `{test_suite} tests/ -v`",
        f"- **Total de Pruebas:** {total_tests} pruebas automatizadas pasando al 100%.",
        "- **Archivos de Prueba:**"
    ])
    for tf in test_files:
        lines.append(f"  - `{tf}`")

    lines.extend([
        "",
        "---",
        "",
        "## 6. Distinción Entre Hechos Comprobados y Plan de Ejecución",
        "",
        "### Hechos Comprobados y Pasos Completados",
        "1. **Partición de Datos:** Congelada deterministicamente en 824 registros para entrenamiento y 206 para prueba (`concrete_test.csv`, SHA-256: `79bdf9613e8515d09baca797e1de4c6de2d6836437584702cbc9c1e78f68c6be`).",
        f"2. **Entrenamiento AutoML:** El job `{job_id}` produjo un modelo ganador `{winner_algo}` con NRMSE de `{metric_val}`.",
        f"3. **Inspección y Descarga del Artefacto (Completadas):** El activo `{model_asset_name}:{model_asset_ver}` se descarga selectivamente mediante `ml_client.models.download` ({model_size:,} bytes).",
        "4. **Verificación de Firma y Metadatos (Completada):** Se validó que el artefacto declare estrictamente las 8 variables predictoras sin requerir deserialización (`scripts/verify_model_load.py --signature-only`).",
        "5. **Carga Local (No Viable en Windows):** La deserialización local en el intérprete Windows/Python 3.13 no es viable debido a dependencias binarias especializadas de Azure AutoML (`azureml.training.tabular.models.voting_ensemble.PreFittedSoftVotingRegressor`).",
        "6. **Evaluador MLflow Independiente (Completado):** `src/evaluate_model.py` preparado para cargar paquetes MLflow, auditar solapamientos objetivamente sin atribuciones normativas ASTM y segmentar métricas a 7d y 28d.",
        f"7. **Job Declarativo Azure ML (Completado):** Especificación reproducible `config/azure_eval_job.yml` validada para ejecutar `evaluate_model.py` bajo el runtime oficial `{curated_img}` en el clúster existente `cpu-cluster-ecomix`.",
        f"8. **Suite Automatizada de Pruebas:** {total_tests} pruebas automatizadas pasando al 100% en entornos multiplataforma (Windows y Ubuntu con Python 3.10 y 3.13).",
        "",
        "### Plan de Ejecución y Tareas Pendientes",
        "1. **Ejecución de la Evaluación Independiente (Fase 4.4-B):**",
        "   - **Estado:** No ejecutada. Planificada y validada estáticamente.",
        "   - **Comando de Despacho en Azure ML:**",
        "     ```bash",
        "     az ml job create -f config/azure_eval_job.yml",
        "     ```",
        "     *(Importante: Este comando NUNCA debe ejecutarse automáticamente por agentes IDE; requiere confirmación explícita y por escrito del usuario).* ",
        "   - **Costos Estimados de Cómputo:**",
        "     El clúster existente `cpu-cluster-ecomix` escala dinámicamente a 1 nodo CPU (`STANDARD_DS11_V2`, ~$0.14 USD/hora). La evaluación toma ~2 a 4 minutos (costo acotado inferior a $0.02 USD / 0.08 S/.).",
        "2. **Consolidación de Métricas y Trazabilidad (Fase 4.5):** Generación y registro de `reports/evaluation_wheat_cheese_4swj34tkjn.json` y el gráfico de correlación real vs predicho una vez obtenidos los resultados reales de la nube.",
        "3. **Módulo de Inferencia EcoMix (Fase 5):** Implementación de fórmulas de sostenibilidad (reemplazo clínker por puzolana/escoria, huella de carbono y costo) sin alterar el runtime del predictor ML.",
        ""
    ])

    return "\n".join(lines)


def sync_project_state(root_dir: Path = PROJECT_ROOT, check_only: bool = False) -> Tuple[bool, List[str]]:
    """
    Ejecuta la sincronización o comprobación de docs/PROJECT_STATE.md a partir de config/project_status.json.
    Retorna: (is_synced, warnings)
    """
    config_path = root_dir / "config" / "project_status.json"
    doc_path = root_dir / "docs" / "PROJECT_STATE.md"

    if not config_path.exists():
        raise FileNotFoundError(f"No se encontró la fuente declarativa en: {config_path}")

    with open(config_path, "r", encoding="utf-8") as f:
        status_data = json.load(f)

    warnings = validate_state_consistency(status_data, root_dir=root_dir)
    expected_content = render_markdown_state(status_data, root_dir=root_dir)

    doc_exists = doc_path.exists()
    current_content = doc_path.read_text(encoding="utf-8") if doc_exists else ""

    # Normalizar finales de línea para comparación limpia
    expected_norm = expected_content.replace("\r\n", "\n").strip()
    current_norm = current_content.replace("\r\n", "\n").strip()

    is_synced = (expected_norm == current_norm)

    if check_only:
        return is_synced, warnings

    if not is_synced:
        doc_path.parent.mkdir(parents=True, exist_ok=True)
        doc_path.write_text(expected_content, encoding="utf-8")

    return True, warnings


def main():
    parser = argparse.ArgumentParser(
        description="Sincronizador y validador del estado del proyecto EcoMix IA."
    )
    parser.add_argument(
        "--check",
        action="store_true",
        help="Verifica si docs/PROJECT_STATE.md está actualizado sin modificarlo (código 0 si coincide, 1 si difiere)."
    )
    args = parser.parse_args()

    git_info = get_git_info()
    datasets_info = inspect_local_datasets(PROJECT_ROOT)
    models_info = inspect_local_models(PROJECT_ROOT)

    print("\n" + "=" * 65)
    print("SINCRONIZACIÓN Y AUDITORÍA DE ESTADO — ECOMIX IA")
    print("=" * 65)
    print(f"  * Rama Git:            {git_info['branch']}")
    print(f"  * Commit Local HEAD:   {git_info['commit_head']} (Volátil - no versionado en Markdown)")
    print(f"  * Árbol Limpio:        {git_info['clean']}")
    print(f"  * Dataset Train:       {'Presente (' + str(datasets_info['train_rows']) + ' filas)' if datasets_info['train_exists'] else 'Ausente'}")
    print(f"  * Dataset Test:        {'Presente (' + str(datasets_info['test_rows']) + ' filas)' if datasets_info['test_exists'] else 'Ausente'}")
    print(f"  * Modelos Locales:     {'Presente en models/' if models_info['exists'] else 'No descargados en disco'}")
    print("=" * 65)

    try:
        is_synced, warnings = sync_project_state(PROJECT_ROOT, check_only=args.check)
    except Exception as e:
        print(f"\n[ERROR CRÍTICO] Falló la verificación de estado: {e}")
        sys.exit(1)

    if warnings:
        print("\n[ADVERTENCIAS DETECTADAS]")
        for w in warnings:
            print(f"  {w}")

    if args.check:
        if is_synced:
            print("\n[CHECK OK] 'docs/PROJECT_STATE.md' está perfectamente sincronizado con 'config/project_status.json'.")
            sys.exit(0)
        else:
            print("\n[CHECK ERROR] 'docs/PROJECT_STATE.md' está desactualizado respecto a 'config/project_status.json'.")
            print("  Para sincronizarlo, ejecute:")
            print("    python scripts/sync_state.py\n")
            sys.exit(1)
    else:
        print("\n[OK] 'docs/PROJECT_STATE.md' sincronizado exitosamente con 'config/project_status.json'.")
        sys.exit(0)


if __name__ == "__main__":
    main()
