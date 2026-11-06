"""
Script de validación reproducible para el motor de inferencia con el modelo VotingEnsemble real.
Diseñado para ejecutarse tanto en entornos con Python 3.10 / Azure AutoML como en Command Jobs de Azure ML.

Actividades:
1. Resuelve y audita la integridad criptográfica SHA-256 del modelo binario model.pkl.
2. Mide la latencia de inicialización en frío (cold-start) de ModelLoader.
3. Evalúa tres dosificaciones representativas a 7 y 28 días:
   - Mezcla canónica ecológica EcoMix (cemento + escoria + ceniza volante).
   - Mezcla con alta sustitución de SCMs (> 60%).
   - Mezcla patrón de Cemento Portland puro (referencia).
4. Ejecuta inferencia dual a través del motor nuevo (InferenceEngine.predict).
5. Ejecuta inferencia pura directa sobre el estimador (estimator.predict) y compara la paridad numérica.
6. Registra métricas de latencia en caliente (warm inference latency), ratios y advertencias.
7. Emite un informe estructurado JSON auditable en 'reports/real_inference_validation.json'.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import platform
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

# Asegurar que la raíz del proyecto esté en sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.inference.engine import (
    InferenceEngine,
    FEATURE_COLUMNS,
    DEFAULT_AGES,
    get_engine,
    predict_concrete_strength,
)
from src.inference.model_loader import (
    ModelLoader,
    ModelInferenceError,
    ModelNotFoundError,
    ModelIntegrityError,
    IncompatibleRuntimeError,
    OFFICIAL_MODEL_SHA256,
    OFFICIAL_RUN_ID,
    OFFICIAL_ALGORITHM,
)
from src.inference.schemas import ConcreteMixDesign, PredictionRequest, PredictionResponse
from src.inference.validator import validate_mix_design


# =====================================================================
# CASOS DE PRUEBA DE DOSIFICACIÓN REPRESENTATIVOS
# =====================================================================

BENCHMARK_CASES = [
    {
        "case_id": "canonical_ecomix",
        "description": "Dosificación canónica EcoMix con 37.08% de sustitución SCM",
        "mix_design": {
            "cement": 280.0,
            "blast_furnace_slag": 105.0,
            "fly_ash": 60.0,
            "water": 175.0,
            "superplasticizer": 8.5,
            "coarse_aggregate": 1020.0,
            "fine_aggregate": 750.0,
        },
    },
    {
        "case_id": "high_scm_substitution",
        "description": "Dosificación con alta sustitución ecológica de SCMs (64.4%)",
        "mix_design": {
            "cement": 160.0,
            "blast_furnace_slag": 220.0,
            "fly_ash": 70.0,
            "water": 165.0,
            "superplasticizer": 9.0,
            "coarse_aggregate": 1000.0,
            "fine_aggregate": 740.0,
        },
    },
    {
        "case_id": "reference_portland_pure",
        "description": "Dosificación patrón de referencia con 100% Cemento Portland Tipo I (0% SCM)",
        "mix_design": {
            "cement": 380.0,
            "blast_furnace_slag": 0.0,
            "fly_ash": 0.0,
            "water": 180.0,
            "superplasticizer": 4.0,
            "coarse_aggregate": 1020.0,
            "fine_aggregate": 760.0,
        },
    },
]


def run_validation(
    model_path: Optional[str] = None,
    reports_dir: Optional[str] = None,
    output_filename: str = "real_inference_validation.json",
) -> Dict[str, Any]:
    """
    Ejecuta el protocolo completo de validación contra el modelo real.
    """
    start_time = time.perf_counter()
    report: Dict[str, Any] = {
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "project": "ecomix-ia-ml",
        "phase": "5.4-A",
        "environment_diagnostics": {
            "python_version": sys.version,
            "platform": platform.platform(),
            "machine": platform.machine(),
            "processor": platform.processor(),
        },
        "model_artifact": {},
        "cold_start_metrics": {},
        "benchmark_results": [],
        "overall_status": "FAILED",
    }

    try:
        import sklearn
        report["environment_diagnostics"]["sklearn_version"] = sklearn.__version__
    except ImportError:
        report["environment_diagnostics"]["sklearn_version"] = "not_installed"

    try:
        import mlflow
        report["environment_diagnostics"]["mlflow_version"] = mlflow.__version__
    except ImportError:
        report["environment_diagnostics"]["mlflow_version"] = "not_installed"

    try:
        import azureml.training.tabular
        report["environment_diagnostics"]["azureml_training_tabular"] = "present"
    except ImportError:
        report["environment_diagnostics"]["azureml_training_tabular"] = "missing"

    loader = ModelLoader.get_instance()
    loader.reset()

    # 1. Resolución del artefacto y verificación de integridad SHA-256
    print("=" * 70)
    print(" ECOMIX IA — VALIDACIÓN REPRODUCIBLE CON MODELO REAL (FASE 5.4-A)")
    print("=" * 70)

    try:
        bin_path, ml_dir, meta = loader.resolve_artifact(model_path)
    except Exception as e:
        report["error"] = f"No se pudo resolver el artefacto del modelo: {e}"
        print(f"[ERROR] {report['error']}", file=sys.stderr)
        return report

    actual_sha = loader.compute_sha256(bin_path)
    sha_matches = (actual_sha == OFFICIAL_MODEL_SHA256)

    report["model_artifact"] = {
        "binary_path": str(bin_path),
        "mlmodel_dir": str(ml_dir) if ml_dir else None,
        "sha256": actual_sha,
        "official_sha256": OFFICIAL_MODEL_SHA256,
        "sha256_verified": sha_matches,
        "run_id": meta.get("run_id", OFFICIAL_RUN_ID),
        "model_type": OFFICIAL_ALGORITHM,
    }

    print(f" Binario resuelto:     {bin_path.name}")
    print(f" Hash SHA-256:         {actual_sha}")
    print(f" Verificación SHA-256: {'[OK - COINCIDE CON CERTIFICADO]' if sha_matches else '[FALLO]'}")
    if not sha_matches:
        report["error"] = f"Fallo de integridad SHA-256: esperado {OFFICIAL_MODEL_SHA256}, obtenido {actual_sha}"
        return report

    # 2. Medición de Cold Start (Carga y deserialización inicial en memoria)
    t_load_start = time.perf_counter()
    try:
        estimator = loader.load_model(model_path=bin_path, expected_sha256=OFFICIAL_MODEL_SHA256)
        t_load_elapsed = (time.perf_counter() - t_load_start) * 1000.0  # ms
        report["cold_start_metrics"] = {
            "load_time_ms": round(t_load_elapsed, 2),
            "status": "LOADED_SUCCESSFULLY",
        }
        print(f" Cold-Start Load Time: {t_load_elapsed:.2f} ms [MODELO CARGADO EN RAM]")
    except IncompatibleRuntimeError as rt_err:
        report["cold_start_metrics"] = {
            "status": "INCOMPATIBLE_RUNTIME",
            "message": str(rt_err),
        }
        report["overall_status"] = "PENDING_COMPATIBLE_RUNTIME"
        print(f"\n[AVISO DE RUNTIME] {rt_err}")
        print("La verificación con modelo real requiere el contenedor oficial de Azure ML (Python 3.10.19).")
        
        # Guardar reporte de diagnóstico antes de salir
        out_dir = Path(reports_dir) if reports_dir else (PROJECT_ROOT / "reports")
        out_dir.mkdir(parents=True, exist_ok=True)
        out_file = out_dir / output_filename
        with open(out_file, "w", encoding="utf-8") as f:
            json.dump(report, f, indent=2, ensure_ascii=False)
        print(f" Reporte de diagnóstico generado en: {out_file}")
        return report
    except Exception as ex:
        report["cold_start_metrics"] = {
            "status": "LOAD_FAILED",
            "error": f"{type(ex).__name__}: {ex}",
        }
        print(f"[ERROR DE CARGA] {ex}", file=sys.stderr)
        return report

    # 3. Evaluación de Casos de Benchmark
    engine = InferenceEngine(loader)
    all_cases_passed = True

    print("\n" + "-" * 70)
    print(" EVALUACIÓN DE CASOS DE DOSIFICACIÓN Y LATENCIA")
    print("-" * 70)

    for case in BENCHMARK_CASES:
        cid = case["case_id"]
        desc = case["description"]
        mix_data = case["mix_design"]

        # 3.1 Inferencia a través del motor
        t_inf_start = time.perf_counter()
        resp = engine.predict(mix_data)
        t_inf_elapsed = (time.perf_counter() - t_inf_start) * 1000.0  # ms

        # 3.2 Inferencia pura directa sobre el estimador para verificar paridad exacta
        mix_obj = ConcreteMixDesign(**mix_data)
        df_feat = engine.build_feature_dataframe(mix_obj, ages=DEFAULT_AGES)
        raw_direct = estimator.predict(df_feat)
        direct_7d = round(float(raw_direct[0]), 2)
        direct_28d = round(float(raw_direct[1]), 2)

        parity_7d = math.isclose(resp.predictions.strength_7d_mpa, direct_7d, abs_tol=1e-4)
        parity_28d = math.isclose(resp.predictions.strength_28d_mpa, direct_28d, abs_tol=1e-4)

        case_passed = (
            parity_7d
            and parity_28d
            and math.isfinite(resp.predictions.strength_7d_mpa)
            and math.isfinite(resp.predictions.strength_28d_mpa)
            and resp.predictions.strength_7d_mpa > 0.0
            and resp.predictions.strength_28d_mpa > 0.0
        )
        if not case_passed:
            all_cases_passed = False

        case_record = {
            "case_id": cid,
            "description": desc,
            "inputs_kg_m3": mix_data,
            "predictions_engine": {
                "strength_7d_mpa": resp.predictions.strength_7d_mpa,
                "strength_28d_mpa": resp.predictions.strength_28d_mpa,
            },
            "predictions_direct_estimator": {
                "strength_7d_mpa": direct_7d,
                "strength_28d_mpa": direct_28d,
            },
            "numerical_parity_verified": (parity_7d and parity_28d),
            "mix_ratios": resp.mix_ratios.model_dump(),
            "warnings_emitted": [w.model_dump() for w in resp.warnings],
            "inference_latency_ms": round(t_inf_elapsed, 2),
            "status": "PASSED" if case_passed else "FAILED",
        }
        report["benchmark_results"].append(case_record)

        print(f" Caso [{cid}]:")
        print(f"   * Resistencia 7 días:  {resp.predictions.strength_7d_mpa:.2f} MPa (Directo: {direct_7d:.2f} MPa)")
        print(f"   * Resistencia 28 días: {resp.predictions.strength_28d_mpa:.2f} MPa (Directo: {direct_28d:.2f} MPa)")
        print(f"   * Paridad Numérica:    {'[OK - IDÉNTICA]' if (parity_7d and parity_28d) else '[DISCREPANCIA]'}")
        print(f"   * Latencia Inferencia: {t_inf_elapsed:.2f} ms")
        print(f"   * Ratios:              w/b={resp.mix_ratios.water_binder_ratio}, SCM={resp.mix_ratios.scm_replacement_percentage}%")
        print(f"   * Advertencias:        {len(resp.warnings)} emitidas")

    total_elapsed = (time.perf_counter() - start_time) * 1000.0
    report["total_execution_ms"] = round(total_elapsed, 2)
    report["overall_status"] = "SUCCESS" if all_cases_passed else "FAILED"

    print("-" * 70)
    print(f" Estado Final: {'[VALIDADO CON VOTINGENSEMBLE REAL]' if all_cases_passed else '[FALLIDO]'}")
    print(f" Tiempo Total de Ejecución: {total_elapsed:.2f} ms")
    print("=" * 70)

    # 4. Guardar reporte JSON si se especifica directorio
    out_dir = Path(reports_dir) if reports_dir else (PROJECT_ROOT / "reports")
    out_dir.mkdir(parents=True, exist_ok=True)
    out_file = out_dir / output_filename

    with open(out_file, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2, ensure_ascii=False)
    print(f" Reporte generado en: {out_file}")

    return report


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Validación reproducible de inferencia con el modelo VotingEnsemble real."
    )
    parser.add_argument(
        "--model-path",
        type=str,
        default=None,
        help="Ruta al directorio o binario del modelo (por defecto busca en models/).",
    )
    parser.add_argument(
        "--reports-dir",
        type=str,
        default=None,
        help="Directorio donde se almacenará el reporte JSON de validación.",
    )
    parser.add_argument(
        "--output-filename",
        type=str,
        default="real_inference_validation.json",
        help="Nombre del archivo JSON de reporte.",
    )

    args = parser.parse_args()
    res = run_validation(
        model_path=args.model_path,
        reports_dir=args.reports_dir,
        output_filename=args.output_filename,
    )

    status = res.get("overall_status")
    if status == "SUCCESS":
        return 0
    elif status == "PENDING_COMPATIBLE_RUNTIME":
        return 3
    else:
        return 1


if __name__ == "__main__":
    sys.exit(main())
