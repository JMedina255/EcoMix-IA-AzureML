"""
Pruebas automatizadas para esquemas de datos y validación de dominio de EcoMix IA (Fase 5.2).
Valida contratos Pydantic v2, límites físicos universales, detección de extrapolación UCI 165,
cálculos determinísticos de ratios, serialización JSON y compatibilidad con ASP.NET MVC 5.
"""

import json
import math
import pytest
from pydantic import ValidationError

from src.inference.schemas import (
    ConcreteMixDesign,
    PredictionRequest,
    PredictionResponse,
    StrengthPredictions,
    MixRatios,
    StructuredWarning,
    ModelMetadata,
    InvalidFieldDetail,
    ProblemDetails,
)
from src.inference.validator import (
    ValidationResult,
    DomainValidationError,
    validate_mix_design,
    validate_or_raise,
    compute_mix_ratios,
    UCI165_BOUNDS,
    PHYSICAL_BOUNDS,
    WARNING_THRESHOLDS,
)


@pytest.fixture
def canonical_mix_dict():
    """Dosificación canónica balanceada para 1 m³ de concreto ecológico."""
    return {
        "cement": 280.0,
        "blast_furnace_slag": 105.0,
        "fly_ash": 60.0,
        "water": 175.0,
        "superplasticizer": 8.5,
        "coarse_aggregate": 1020.0,
        "fine_aggregate": 750.0,
    }


# =====================================================================
# 1. PRUEBAS DE DOSIFICACIONES VÁLIDAS Y CÁLCULOS DETERMINÍSTICOS
# =====================================================================

def test_canonical_mix_design_is_valid_and_ratios_accurate(canonical_mix_dict):
    """Verifica que una mezcla canónica sea declarada válida y calcule ratios exactos."""
    res = validate_mix_design(canonical_mix_dict)

    assert res.is_valid is True
    assert res.mix_design is not None
    assert res.ratios is not None
    assert len(res.errors) == 0
    assert res.problem_details is None

    # Verificación determinística de relaciones de mezcla
    ratios = res.ratios
    assert ratios.total_cementitious_content_kg_m3 == 445.0  # 280 + 105 + 60
    assert ratios.water_cement_ratio == round(175.0 / 280.0, 4)  # 0.625
    assert ratios.water_binder_ratio == round(175.0 / 445.0, 4)  # 0.3933
    assert ratios.scm_replacement_percentage == round((165.0 / 445.0) * 100.0, 2)  # 37.08%
    assert ratios.aggregates_total_kg_m3 == 1770.0  # 1020 + 750
    assert ratios.total_mass_kg_m3 == 2398.5  # 445 + 175 + 8.5 + 1770


def test_pure_portland_mix_without_scms_calculates_zero_replacement():
    """Verifica que una mezcla convencional sin adiciones tenga 0% de sustitución SCM."""
    mix_data = {
        "cement": 380.0,
        "blast_furnace_slag": 0.0,
        "fly_ash": 0.0,
        "water": 180.0,
        "superplasticizer": 4.0,
        "coarse_aggregate": 1000.0,
        "fine_aggregate": 800.0,
    }
    res = validate_mix_design(mix_data)
    assert res.is_valid is True
    assert res.ratios.scm_replacement_percentage == 0.0
    assert res.ratios.total_cementitious_content_kg_m3 == 380.0
    assert res.ratios.water_cement_ratio == res.ratios.water_binder_ratio


def test_zero_cement_mix_with_scms_handles_none_water_cement_ratio():
    """Verifica que una mezcla 100% SCM maneje water_cement_ratio como None sin división por cero."""
    mix_data = {
        "cement": 0.0,
        "blast_furnace_slag": 300.0,
        "fly_ash": 120.0,
        "water": 180.0,
        "superplasticizer": 5.0,
        "coarse_aggregate": 1000.0,
        "fine_aggregate": 750.0,
    }
    res = validate_mix_design(mix_data)
    assert res.is_valid is True
    assert res.ratios.water_cement_ratio is None
    assert res.ratios.total_cementitious_content_kg_m3 == 420.0
    assert res.ratios.scm_replacement_percentage == 100.0


# =====================================================================
# 2. PRUEBAS DE ERRORES ESTRICTOS (RECHAZO HTTP 422)
# =====================================================================

def test_missing_required_components_fails_validation():
    """Verifica que omitir campos obligatorios genere errores de validación estructurados."""
    # Omitir 'cement' y 'water'
    partial_data = {
        "blast_furnace_slag": 100.0,
        "fly_ash": 50.0,
        "superplasticizer": 5.0,
        "coarse_aggregate": 1000.0,
        "fine_aggregate": 750.0,
    }
    res = validate_mix_design(partial_data)
    assert res.is_valid is False
    assert res.ratios is None
    assert res.problem_details is not None
    assert res.problem_details.status == 422

    error_fields = [e.field for e in res.errors]
    assert any("cement" in f for f in error_fields)
    assert any("water" in f for f in error_fields)


@pytest.mark.parametrize(
    "component",
    [
        "cement",
        "blast_furnace_slag",
        "fly_ash",
        "water",
        "superplasticizer",
        "coarse_aggregate",
        "fine_aggregate",
    ],
)
def test_negative_values_rejected_for_all_components(canonical_mix_dict, component):
    """Verifica que ningún componente acepte valores negativos."""
    data = dict(canonical_mix_dict)
    data[component] = -15.0

    res = validate_mix_design(data)
    assert res.is_valid is False
    assert any(
        e.constraint == "non_negative"
        or "negativo" in e.message.lower()
        or "negative" in e.message.lower()
        for e in res.errors
    )


@pytest.mark.parametrize("bad_val", [float("nan"), float("inf"), float("-inf")])
def test_nan_and_infinite_values_rejected(canonical_mix_dict, bad_val):
    """Verifica que NaN e infinitos sean rechazados categóricamente."""
    data = dict(canonical_mix_dict)
    data["water"] = bad_val

    res = validate_mix_design(data)
    assert res.is_valid is False
    assert res.problem_details is not None
    assert any(e.constraint == "finite_number" or "finito" in e.message.lower() for e in res.errors)


def test_zero_total_binder_rejected_as_physical_impossibility():
    """Verifica que una mezcla sin ningún material cementante sea rechazada por denominador nulo."""
    mix_data = {
        "cement": 0.0,
        "blast_furnace_slag": 0.0,
        "fly_ash": 0.0,
        "water": 175.0,
        "superplasticizer": 0.0,
        "coarse_aggregate": 1000.0,
        "fine_aggregate": 800.0,
    }
    res = validate_mix_design(mix_data)
    assert res.is_valid is False
    assert any(e.constraint == "zero_binder_denominator" for e in res.errors)


def test_zero_total_aggregates_rejected_as_physical_impossibility():
    """Verifica que una mezcla sin agregados sea rechazada por carecer de esqueleto granular."""
    mix_data = {
        "cement": 400.0,
        "blast_furnace_slag": 0.0,
        "fly_ash": 0.0,
        "water": 175.0,
        "superplasticizer": 2.0,
        "coarse_aggregate": 0.0,
        "fine_aggregate": 0.0,
    }
    res = validate_mix_design(mix_data)
    assert res.is_valid is False
    assert any(e.constraint == "zero_aggregate_denominator" for e in res.errors)


def test_physically_impossible_water_bounds_rejected(canonical_mix_dict):
    """Verifica rechazo cuando el agua es menor a 50 kg/m³ o mayor a 350 kg/m³."""
    # Menor a 50 kg/m³
    data_low = dict(canonical_mix_dict)
    data_low["water"] = 40.0
    res_low = validate_mix_design(data_low)
    assert res_low.is_valid is False
    assert any(e.constraint == "physical_minimum" for e in res_low.errors)

    # Mayor a 350 kg/m³
    data_high = dict(canonical_mix_dict)
    data_high["water"] = 380.0
    res_high = validate_mix_design(data_high)
    assert res_high.is_valid is False
    assert any(e.constraint == "physical_maximum" for e in res_high.errors)


def test_physically_impossible_water_binder_ratio_rejected(canonical_mix_dict):
    """Verifica rechazo si w/b es menor a 0.15 o mayor a 1.20."""
    # w/b < 0.15 (ej: cemento 600, agua 70 -> w/b = 0.116)
    data_low = dict(canonical_mix_dict)
    data_low["cement"] = 600.0
    data_low["water"] = 70.0  # w/b = 70 / (600 + 105 + 60) = 0.0915
    res_low = validate_mix_design(data_low)
    assert res_low.is_valid is False
    assert any(e.constraint == "physical_minimum_wb" for e in res_low.errors)

    # w/b > 1.20 (ej: cemento 120, agua 200 -> w/b = 1.66)
    data_high = dict(canonical_mix_dict)
    data_high["cement"] = 120.0
    data_high["blast_furnace_slag"] = 0.0
    data_high["fly_ash"] = 0.0
    data_high["water"] = 200.0
    res_high = validate_mix_design(data_high)
    assert res_high.is_valid is False
    assert any(e.constraint == "physical_maximum_wb" for e in res_high.errors)


def test_abnormal_total_mass_rejected(canonical_mix_dict):
    """Verifica que masas volumétricas menores a 1800 kg/m³ o mayores a 2800 kg/m³ sean rechazadas."""
    # Masa muy baja (ej: 1400 kg/m³)
    data_light = dict(canonical_mix_dict)
    data_light["coarse_aggregate"] = 400.0
    data_light["fine_aggregate"] = 400.0
    res_light = validate_mix_design(data_light)
    assert res_light.is_valid is False
    assert any(e.constraint == "physical_minimum_density" for e in res_light.errors)

    # Masa excesiva (ej: 3200 kg/m³)
    data_heavy = dict(canonical_mix_dict)
    data_heavy["coarse_aggregate"] = 1500.0
    data_heavy["fine_aggregate"] = 1300.0
    res_heavy = validate_mix_design(data_heavy)
    assert res_heavy.is_valid is False
    assert any(e.constraint == "physical_maximum_density" for e in res_heavy.errors)


# =====================================================================
# 3. PRUEBAS DE ADVERTENCIAS DE DOMINIO (OOD Y BUENAS PRÁCTICAS - HTTP 200)
# =====================================================================

def test_ood_water_outside_uci165_bounds_generates_warning_not_rejection(canonical_mix_dict):
    """
    Verifica que un valor fuera de UCI 165 pero físicamente válido (ej. agua = 260 kg/m³)
    sea aceptado (is_valid=True) pero genere una advertencia WARN_OOD_WATER.
    """
    data = dict(canonical_mix_dict)
    data["water"] = 260.0  # UCI 165 máx es 247.0, pero físico máx es 350.0

    res = validate_mix_design(data)
    assert res.is_valid is True
    assert len(res.errors) == 0

    warn_codes = [w.code for w in res.warnings]
    assert "WARN_OOD_WATER" in warn_codes
    warn_obj = next(w for w in res.warnings if w.code == "WARN_OOD_WATER")
    assert warn_obj.observed_value == 260.0
    assert "[121.8, 247.0]" in warn_obj.reference_boundary


def test_ood_cement_outside_uci165_bounds_generates_warning(canonical_mix_dict):
    """Verifica advertencia cuando el cemento supera 540 kg/m³ (límite UCI 165)."""
    data = dict(canonical_mix_dict)
    data["cement"] = 560.0

    res = validate_mix_design(data)
    assert res.is_valid is True
    warn_codes = [w.code for w in res.warnings]
    assert "WARN_OOD_CEMENT" in warn_codes


def test_high_scm_replacement_generates_info_warning(canonical_mix_dict):
    """Verifica que una sustitución SCM entre 40% y 65% genere WARN_HIGH_SCM_REPLACEMENT."""
    data = dict(canonical_mix_dict)
    data["cement"] = 200.0
    data["blast_furnace_slag"] = 150.0
    data["fly_ash"] = 50.0  # SCM = 200 / 400 = 50%

    res = validate_mix_design(data)
    assert res.is_valid is True
    warn_codes = [w.code for w in res.warnings]
    assert "WARN_HIGH_SCM_REPLACEMENT" in warn_codes
    warn_obj = next(w for w in res.warnings if w.code == "WARN_HIGH_SCM_REPLACEMENT")
    assert warn_obj.severity == "info"


def test_extreme_scm_replacement_generates_warning_severity(canonical_mix_dict):
    """Verifica que una sustitución SCM superior a 65% genere WARN_EXTREME_SCM_REPLACEMENT con severidad warning."""
    data = dict(canonical_mix_dict)
    data["cement"] = 110.0
    data["blast_furnace_slag"] = 220.0
    data["fly_ash"] = 80.0  # SCM = 300 / 410 = 73.17%

    res = validate_mix_design(data)
    assert res.is_valid is True
    warn_codes = [w.code for w in res.warnings]
    assert "WARN_EXTREME_SCM_REPLACEMENT" in warn_codes
    warn_obj = next(w for w in res.warnings if w.code == "WARN_EXTREME_SCM_REPLACEMENT")
    assert warn_obj.severity == "warning"


def test_high_superplasticizer_with_high_water_generates_warning(canonical_mix_dict):
    """Verifica que aditivo > 15 kg/m³ con agua > 200 kg/m³ genere WARN_SUPERPLASTICIZER_HIGH_WATER."""
    data = dict(canonical_mix_dict)
    data["superplasticizer"] = 18.0
    data["water"] = 210.0

    res = validate_mix_design(data)
    assert res.is_valid is True
    warn_codes = [w.code for w in res.warnings]
    assert "WARN_SUPERPLASTICIZER_HIGH_WATER" in warn_codes


# =====================================================================
# 4. PRUEBAS DE SERIALIZACIÓN JSON Y COMPATIBILIDAD ASP.NET MVC 5
# =====================================================================

def test_prediction_request_deserialization_from_asp_net_payload():
    """
    Verifica que un payload JSON típico generado por C# / ASP.NET MVC 5
    con campos extra o $schema sea parseado limpiamente sin errores.
    """
    aspnet_json = json.dumps({
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "mix_design": {
            "cement": 280.0,
            "blast_furnace_slag": 105.0,
            "fly_ash": 60.0,
            "water": 175.0,
            "superplasticizer": 8.5,
            "coarse_aggregate": 1020.0,
            "fine_aggregate": 750.0,
        },
        "request_id": "REQ-MVC5-20261106-001",
        "client_metadata": {
            "user_id": 42,
            "source_controller": "ConcreteMixController",
        },
    })

    req = PredictionRequest.model_validate_json(aspnet_json)
    assert req.mix_design.cement == 280.0
    assert req.request_id == "REQ-MVC5-20261106-001"
    assert req.mix_design.blast_furnace_slag == 105.0


def test_prediction_response_serialization_to_json():
    """Verifica que la respuesta PredictionResponse se serialice en JSON estándar conforme al contrato."""
    response = PredictionResponse(
        predictions=StrengthPredictions(strength_7d_mpa=24.18, strength_28d_mpa=38.65),
        mix_ratios=MixRatios(
            water_cement_ratio=0.625,
            water_binder_ratio=0.3933,
            total_cementitious_content_kg_m3=445.0,
            scm_replacement_percentage=37.08,
            aggregates_total_kg_m3=1770.0,
            total_mass_kg_m3=2398.5,
        ),
        warnings=[
            StructuredWarning(
                code="WARN_HIGH_SCM_REPLACEMENT",
                severity="info",
                field="scm_replacement_percentage",
                message="Sustitución moderada de cemento.",
            )
        ],
        metadata=ModelMetadata(
            model_id="wheat_cheese_4swj34tkjn_11",
            model_type="VotingEnsemble",
            model_sha256="7eaa501c5eeb60135effb6b5861e736518ce969c47afd53727c2451083ff6388",
        ),
    )

    json_str = response.model_dump_json(indent=2)
    parsed = json.loads(json_str)

    assert parsed["status"] == "success"
    assert parsed["predictions"]["strength_7d_mpa"] == 24.18
    assert parsed["predictions"]["strength_28d_mpa"] == 38.65
    assert parsed["mix_ratios"]["water_binder_ratio"] == 0.3933
    assert len(parsed["warnings"]) == 1
    assert parsed["metadata"]["model_type"] == "VotingEnsemble"


def test_problem_details_rfc7807_serialization():
    """Verifica que la respuesta de error ProblemDetails cumpla la estructura RFC 7807 para ASP.NET."""
    problem = ProblemDetails(
        detail="Dosificación físicamente inválida.",
        invalid_fields=[
            InvalidFieldDetail(
                field="mix_design.water",
                value=-10.0,
                constraint="non_negative",
                limit=0.0,
                unit="kg/m3",
                message="El agua no puede ser negativa.",
            )
        ],
    )

    json_str = problem.model_dump_json()
    parsed = json.loads(json_str)

    assert parsed["status"] == 422
    assert parsed["type"] == "https://ecomixia.yura.com.pe/errors/validation-error"
    assert parsed["title"] == "Error de Validación de Dosificación"
    assert len(parsed["invalid_fields"]) == 1
    assert parsed["invalid_fields"][0]["constraint"] == "non_negative"


# =====================================================================
# 5. PRUEBAS DE LA FUNCIÓN validate_or_raise
# =====================================================================

def test_validate_or_raise_returns_tuple_on_success(canonical_mix_dict):
    """Verifica que validate_or_raise retorne (mix, ratios, warnings) cuando la mezcla es válida."""
    mix, ratios, warnings = validate_or_raise(canonical_mix_dict)
    assert isinstance(mix, ConcreteMixDesign)
    assert isinstance(ratios, MixRatios)
    assert isinstance(warnings, list)
    assert ratios.total_cementitious_content_kg_m3 == 445.0


def test_validate_or_raise_throws_domain_validation_error_on_failure(canonical_mix_dict):
    """Verifica que validate_or_raise lance DomainValidationError con ProblemDetails al fallar."""
    data = dict(canonical_mix_dict)
    data["water"] = -5.0

    with pytest.raises(DomainValidationError) as exc_info:
        validate_or_raise(data)

    err = exc_info.value
    assert isinstance(err.problem_details, ProblemDetails)
    assert err.problem_details.status == 422
    assert len(err.problem_details.invalid_fields) > 0
