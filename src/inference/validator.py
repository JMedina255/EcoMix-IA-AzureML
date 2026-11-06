"""
Motor de validación de dominio y cálculo de ratios de dosificación para EcoMix IA.
Separa estrictamente:
1. Errores estrictos (Hard Constraints - HTTP 422):
   - Valores negativos, no finitos (NaN, Inf) o ausentes.
   - Denominadores nulos en ratios físicos (material cementante = 0, agregados = 0).
   - Incoherencias físicas documentadas (agua imposible, ratios extremos, masa volumétrica anómala).
2. Advertencias de dominio (Soft Constraints / OOD - HTTP 200 con warnings):
   - Extrapolación del espacio muestral experimental de UCI 165.
   - Relación agua/cementante fuera del rango de calibración.
   - Porcentajes elevados de sustitución de cemento por SCMs (escoria y ceniza).
   - Dosificaciones con riesgo tecnológico de segregación o fraguado lento.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple, Union
from pydantic import ValidationError

from src.inference.schemas import (
    ConcreteMixDesign,
    InvalidFieldDetail,
    MixRatios,
    ProblemDetails,
    StructuredWarning,
)


# =====================================================================
# CONSTANTES DE DOMINIO Y LÍMITES FÍSICOS Y EXPERIMENTALES
# =====================================================================

# Límites del hipervolumen experimental observado en UCI Machine Learning Repository (ID 165).
# Representan el dominio donde el ensamble de ML (VotingEnsemble) fue entrenado y evaluado.
# Valores fuera de este rango NO se prohíben físicamente, pero generan advertencias OOD por riesgo de extrapolación.
UCI165_BOUNDS: Dict[str, Dict[str, Any]] = {
    "cement": {
        "min": 102.0,
        "max": 540.0,
        "unit": "kg/m3",
        "description": "Contenido de Cemento Portland",
    },
    "blast_furnace_slag": {
        "min": 0.0,
        "max": 359.4,
        "unit": "kg/m3",
        "description": "Escoria granulada de alto horno (GGBFS)",
    },
    "fly_ash": {
        "min": 0.0,
        "max": 200.1,
        "unit": "kg/m3",
        "description": "Ceniza volante / Puzolana",
    },
    "water": {
        "min": 121.8,
        "max": 247.0,
        "unit": "kg/m3",
        "description": "Agua de mezclado",
    },
    "superplasticizer": {
        "min": 0.0,
        "max": 32.2,
        "unit": "kg/m3",
        "description": "Aditivo superplastificante",
    },
    "coarse_aggregate": {
        "min": 801.0,
        "max": 1145.0,
        "unit": "kg/m3",
        "description": "Agregado grueso (grava)",
    },
    "fine_aggregate": {
        "min": 594.0,
        "max": 992.6,
        "unit": "kg/m3",
        "description": "Agregado fino (arena)",
    },
}

# Límites físicos universales de la tecnología del concreto hidráulico.
# Cualquier mezcla que viole estos límites es físicamente defectuosa o imposible de elaborar como concreto estructural.
PHYSICAL_BOUNDS = {
    "min_water_kg_m3": 50.0,
    "max_water_kg_m3": 350.0,
    "min_water_binder_ratio": 0.15,
    "max_water_binder_ratio": 1.20,
    "min_total_mass_kg_m3": 1800.0,
    "max_total_mass_kg_m3": 2800.0,
}

# Límites de buenas prácticas y directrices tecnológicas para generación de advertencias informativas
WARNING_THRESHOLDS = {
    "min_water_binder_ratio": 0.25,
    "max_water_binder_ratio": 0.70,
    "high_water_cement_ratio": 0.65,
    "high_scm_replacement_pct": 40.0,
    "extreme_scm_replacement_pct": 65.0,
    "high_sp_dose_kg_m3": 15.0,
    "high_sp_water_threshold_kg_m3": 200.0,
}


# =====================================================================
# RESULTADOS Y EXCEPCIONES DE VALIDACIÓN
# =====================================================================

@dataclass
class ValidationResult:
    """
    Contenedor exhaustivo del resultado de validación de una dosificación.
    """

    is_valid: bool
    mix_design: Optional[ConcreteMixDesign]
    ratios: Optional[MixRatios]
    errors: List[InvalidFieldDetail]
    warnings: List[StructuredWarning]
    problem_details: Optional[ProblemDetails] = None


class DomainValidationError(Exception):
    """
    Excepción tipada lanzada cuando una dosificación viola restricciones duras.
    Contiene la estructura ProblemDetails conforme a RFC 7807.
    """

    def __init__(self, problem_details: ProblemDetails):
        self.problem_details = problem_details
        message = (
            f"Error de validación ({problem_details.status}): {problem_details.detail} "
            f"[{len(problem_details.invalid_fields)} campos inválidos]"
        )
        super().__init__(message)


# =====================================================================
# CÁLCULOS DETERMINÍSTICOS DE RATIOS DE DOSIFICACIÓN
# =====================================================================

def compute_mix_ratios(mix: ConcreteMixDesign) -> MixRatios:
    """
    Calcula de manera determinística las relaciones de dosificación para 1 m³ de concreto:
    - Contenido cementante total (cemento + escoria + ceniza).
    - Relación agua/cemento (w/c).
    - Relación agua/material cementante total (w/b o a/mc).
    - Porcentaje de sustitución de cemento por SCMs.
    - Masa combinada de agregados.
    - Masa volumétrica total de la mezcla fresca.

    Args:
        mix: Instancia validada de ConcreteMixDesign.

    Returns:
        MixRatios con precisión numérica estandarizada y unidades explícitas.
    """
    total_cementitious = float(mix.cement + mix.blast_furnace_slag + mix.fly_ash)
    aggregates_total = float(mix.coarse_aggregate + mix.fine_aggregate)
    total_mass = float(
        mix.cement
        + mix.blast_furnace_slag
        + mix.fly_ash
        + mix.water
        + mix.superplasticizer
        + mix.coarse_aggregate
        + mix.fine_aggregate
    )

    # Relación agua/cemento (w/c): None si cemento es 0 (mezcla 100% SCM activada alcalinamente)
    if mix.cement > 0.0:
        water_cement = round(mix.water / mix.cement, 4)
    else:
        water_cement = None

    # Relación agua/material cementante (w/b): con protección ante denominador nulo
    if total_cementitious > 0.0:
        water_binder = round(mix.water / total_cementitious, 4)
        scm_mass = float(mix.blast_furnace_slag + mix.fly_ash)
        scm_pct = round((scm_mass / total_cementitious) * 100.0, 2)
    else:
        water_binder = 0.0
        scm_pct = 0.0

    return MixRatios(
        water_cement_ratio=water_cement,
        water_binder_ratio=water_binder,
        total_cementitious_content_kg_m3=round(total_cementitious, 2),
        scm_replacement_percentage=scm_pct,
        aggregates_total_kg_m3=round(aggregates_total, 2),
        total_mass_kg_m3=round(total_mass, 2),
    )


# =====================================================================
# MOTOR DE VALIDACIÓN DE DOMINIO Y REGLAS FÍSICAS
# =====================================================================

def validate_mix_design(
    data: Union[ConcreteMixDesign, Dict[str, Any]],
) -> ValidationResult:
    """
    Valida exhaustivamente una dosificación de concreto según restricciones duras y advertencias de dominio.

    Procedimiento:
    1. Parseo y tipado estricto mediante Pydantic v2 (captura nulos, faltantes, negativos, NaN e Inf).
    2. Validación de denominadores nulos y restricciones físicas de dosificación.
    3. Cálculo de ratios determinísticos de mezcla.
    4. Evaluación de advertencias estructuradas por extrapolación fuera del dataset UCI 165 o buenas prácticas.

    Args:
        data: Instancia de ConcreteMixDesign o diccionario con los insumos en kg/m³.

    Returns:
        ValidationResult indicando si es válida, errores detallados, advertencias y ratios calculados.
    """
    errors: List[InvalidFieldDetail] = []
    warnings: List[StructuredWarning] = []
    mix_design: Optional[ConcreteMixDesign] = None
    ratios: Optional[MixRatios] = None

    # -------------------------------------------------------------
    # 1. Validación de Formato, Tipos y Valores Negativos / Finitos
    # -------------------------------------------------------------
    if isinstance(data, ConcreteMixDesign):
        mix_design = data
    elif isinstance(data, dict):
        try:
            mix_design = ConcreteMixDesign(**data)
        except ValidationError as val_err:
            for err in val_err.errors():
                loc = ".".join(str(p) for p in err["loc"])
                field_name = f"mix_design.{loc}" if loc else "mix_design"
                err_type = err.get("type", "value_error")
                err_msg = err.get("msg", "Valor inválido")

                constraint = "format_error"
                err_msg_lower = err_msg.lower()
                if "nan" in err_type or "finite" in err_msg_lower or "finito" in err_msg_lower:
                    constraint = "finite_number"
                elif (
                    "negative" in err_msg_lower
                    or "negativo" in err_msg_lower
                    or "greater_than_equal" in err_type
                    or "greater_than" in err_type
                ):
                    constraint = "non_negative"
                elif "missing" in err_type:
                    constraint = "required_field"

                errors.append(
                    InvalidFieldDetail(
                        field=field_name,
                        value=err.get("input", None),
                        constraint=constraint,
                        limit=0.0 if constraint == "non_negative" else None,
                        unit="kg/m3",
                        message=err_msg,
                    )
                )
            return ValidationResult(
                is_valid=False,
                mix_design=None,
                ratios=None,
                errors=errors,
                warnings=[],
                problem_details=ProblemDetails(
                    detail="La solicitud contiene campos faltantes, tipos incompatibles o valores no numéricos.",
                    invalid_fields=errors,
                ),
            )
        except Exception as ex:
            errors.append(
                InvalidFieldDetail(
                    field="mix_design",
                    value=None,
                    constraint="unparseable_payload",
                    limit=None,
                    unit="kg/m3",
                    message=f"No se pudo procesar la carga útil de dosificación: {str(ex)}",
                )
            )
            return ValidationResult(
                is_valid=False,
                mix_design=None,
                ratios=None,
                errors=errors,
                warnings=[],
                problem_details=ProblemDetails(
                    detail="Error fatal al decodificar la carga útil de dosificación.",
                    invalid_fields=errors,
                ),
            )
    else:
        errors.append(
            InvalidFieldDetail(
                field="mix_design",
                value=type(data).__name__,
                constraint="invalid_type",
                limit="ConcreteMixDesign o dict",
                unit=None,
                message="El formato de entrada debe ser un objeto ConcreteMixDesign o un diccionario.",
            )
        )
        return ValidationResult(
            is_valid=False,
            mix_design=None,
            ratios=None,
            errors=errors,
            warnings=[],
            problem_details=ProblemDetails(
                detail="Tipo de dato de dosificación no admitido.",
                invalid_fields=errors,
            ),
        )

    # -------------------------------------------------------------
    # 2. Validación de Denominadores Nulos y Reglas Físicas Duras
    # -------------------------------------------------------------
    total_cementitious = mix_design.cement + mix_design.blast_furnace_slag + mix_design.fly_ash
    total_aggregates = mix_design.coarse_aggregate + mix_design.fine_aggregate
    total_mass = (
        total_cementitious
        + mix_design.water
        + mix_design.superplasticizer
        + total_aggregates
    )

    # 2.1 Denominador nulo: Contenido cementante total
    if total_cementitious <= 0.0:
        errors.append(
            InvalidFieldDetail(
                field="mix_design.cementitious_total",
                value=total_cementitious,
                constraint="zero_binder_denominator",
                limit=100.0,
                unit="kg/m3",
                message=(
                    "El contenido cementante total (cemento + escoria + ceniza) es nulo o cero. "
                    "Es físicamente imposible conformar pasta aglutinante sin material cementante."
                ),
            )
        )

    # 2.2 Denominador nulo: Agregados totales
    if total_aggregates <= 0.0:
        errors.append(
            InvalidFieldDetail(
                field="mix_design.aggregates_total",
                value=total_aggregates,
                constraint="zero_aggregate_denominator",
                limit=1000.0,
                unit="kg/m3",
                message=(
                    "El contenido total de agregados (grueso + fino) es cero. "
                    "Una mezcla sin esqueleto granular no constituye concreto hidráulico."
                ),
            )
        )

    # 2.3 Contenido de agua físicamente imposible
    if mix_design.water < PHYSICAL_BOUNDS["min_water_kg_m3"]:
        errors.append(
            InvalidFieldDetail(
                field="mix_design.water",
                value=mix_design.water,
                constraint="physical_minimum",
                limit=PHYSICAL_BOUNDS["min_water_kg_m3"],
                unit="kg/m3",
                message=(
                    f"El contenido de agua ({mix_design.water} kg/m³) es inferior al mínimo físico "
                    f"requerido para permitir la hidratación de la pasta ({PHYSICAL_BOUNDS['min_water_kg_m3']} kg/m³)."
                ),
            )
        )
    elif mix_design.water > PHYSICAL_BOUNDS["max_water_kg_m3"]:
        errors.append(
            InvalidFieldDetail(
                field="mix_design.water",
                value=mix_design.water,
                constraint="physical_maximum",
                limit=PHYSICAL_BOUNDS["max_water_kg_m3"],
                unit="kg/m3",
                message=(
                    f"El contenido de agua ({mix_design.water} kg/m³) supera el límite admisible para mezclas "
                    f"estructurales ({PHYSICAL_BOUNDS['max_water_kg_m3']} kg/m³). Provocaría lavado, segregación "
                    "y anulación de la resistencia mecánica."
                ),
            )
        )

    # 2.4 Relación agua/cementante fuera de límites físicos plausibles
    if total_cementitious > 0.0:
        raw_wb = mix_design.water / total_cementitious
        if raw_wb < PHYSICAL_BOUNDS["min_water_binder_ratio"]:
            errors.append(
                InvalidFieldDetail(
                    field="mix_design.water_binder_ratio",
                    value=round(raw_wb, 4),
                    constraint="physical_minimum_wb",
                    limit=PHYSICAL_BOUNDS["min_water_binder_ratio"],
                    unit="ratio",
                    message=(
                        f"La relación agua/cementante ({raw_wb:.3f}) es físicamente insuficiente para la "
                        f"hidratación estequiométrica del cemento (mínimo físico: {PHYSICAL_BOUNDS['min_water_binder_ratio']})."
                    ),
                )
            )
        elif raw_wb > PHYSICAL_BOUNDS["max_water_binder_ratio"]:
            errors.append(
                InvalidFieldDetail(
                    field="mix_design.water_binder_ratio",
                    value=round(raw_wb, 4),
                    constraint="physical_maximum_wb",
                    limit=PHYSICAL_BOUNDS["max_water_binder_ratio"],
                    unit="ratio",
                    message=(
                        f"La relación agua/cementante ({raw_wb:.3f}) excede el límite máximo estructural "
                        f"({PHYSICAL_BOUNDS['max_water_binder_ratio']}). Destruye la microestructura de los silicatos hidratados."
                    ),
                )
            )

    # 2.5 Masa volumétrica total fuera del rango físico de concreto convencional
    if total_mass < PHYSICAL_BOUNDS["min_total_mass_kg_m3"]:
        errors.append(
            InvalidFieldDetail(
                field="mix_design.total_mass",
                value=round(total_mass, 2),
                constraint="physical_minimum_density",
                limit=PHYSICAL_BOUNDS["min_total_mass_kg_m3"],
                unit="kg/m3",
                message=(
                    f"La masa volumétrica total ({total_mass:.1f} kg/m³) es menor al límite físico de "
                    f"un concreto convencional ({PHYSICAL_BOUNDS['min_total_mass_kg_m3']} kg/m³)."
                ),
            )
        )
    elif total_mass > PHYSICAL_BOUNDS["max_total_mass_kg_m3"]:
        errors.append(
            InvalidFieldDetail(
                field="mix_design.total_mass",
                value=round(total_mass, 2),
                constraint="physical_maximum_density",
                limit=PHYSICAL_BOUNDS["max_total_mass_kg_m3"],
                unit="kg/m3",
                message=(
                    f"La masa volumétrica total ({total_mass:.1f} kg/m³) supera la densidad admisible para "
                    f"concreto de peso normal ({PHYSICAL_BOUNDS['max_total_mass_kg_m3']} kg/m³)."
                ),
            )
        )

    # Si hay errores duros, retornar inmediatamente con estado inválido y ProblemDetails
    if errors:
        return ValidationResult(
            is_valid=False,
            mix_design=mix_design,
            ratios=None,
            errors=errors,
            warnings=[],
            problem_details=ProblemDetails(
                detail="La dosificación viola restricciones físicas o matemáticas fundamentales de la tecnología del concreto.",
                invalid_fields=errors,
            ),
        )

    # -------------------------------------------------------------
    # 3. Cálculo de Ratios Determinísticos
    # -------------------------------------------------------------
    ratios = compute_mix_ratios(mix_design)

    # -------------------------------------------------------------
    # 4. Evaluación de Advertencias Estructuradas (OOD y Buenas Prácticas)
    # -------------------------------------------------------------
    # 4.1 Advertencias por límites observados en UCI 165 (Extrapolación del modelo ML)
    components = [
        ("cement", mix_design.cement, "WARN_OOD_CEMENT"),
        ("blast_furnace_slag", mix_design.blast_furnace_slag, "WARN_OOD_SLAG"),
        ("fly_ash", mix_design.fly_ash, "WARN_OOD_FLY_ASH"),
        ("water", mix_design.water, "WARN_OOD_WATER"),
        ("superplasticizer", mix_design.superplasticizer, "WARN_OOD_SUPERPLASTICIZER"),
        ("coarse_aggregate", mix_design.coarse_aggregate, "WARN_OOD_COARSE_AGG"),
        ("fine_aggregate", mix_design.fine_aggregate, "WARN_OOD_FINE_AGG"),
    ]

    for comp_name, val, warn_code in components:
        bounds = UCI165_BOUNDS[comp_name]
        min_val = bounds["min"]
        max_val = bounds["max"]
        desc = bounds["description"]

        if val < min_val:
            warnings.append(
                StructuredWarning(
                    code=warn_code,
                    severity="warning",
                    field=comp_name,
                    observed_value=float(val),
                    reference_boundary=f"[{min_val}, {max_val}] kg/m3",
                    message=(
                        f"El componente '{desc}' ({val} kg/m³) está por debajo del rango experimental "
                        f"de UCI 165 (mínimo observado: {min_val} kg/m³). Existe riesgo de extrapolación en el modelo ML."
                    ),
                )
            )
        elif val > max_val:
            warnings.append(
                StructuredWarning(
                    code=warn_code,
                    severity="warning",
                    field=comp_name,
                    observed_value=float(val),
                    reference_boundary=f"[{min_val}, {max_val}] kg/m3",
                    message=(
                        f"El componente '{desc}' ({val} kg/m³) supera el límite superior experimental "
                        f"de UCI 165 (máximo observado: {max_val} kg/m³). El modelo ML operará en extrapolación."
                    ),
                )
            )

    # 4.2 Advertencias por Relación Agua/Material Cementante (w/b)
    if (
        ratios.water_binder_ratio < WARNING_THRESHOLDS["min_water_binder_ratio"]
        or ratios.water_binder_ratio > WARNING_THRESHOLDS["max_water_binder_ratio"]
    ):
        warnings.append(
            StructuredWarning(
                code="WARN_OOD_WATER_BINDER_RATIO",
                severity="warning",
                field="water_binder_ratio",
                observed_value=ratios.water_binder_ratio,
                reference_boundary=f"[{WARNING_THRESHOLDS['min_water_binder_ratio']}, {WARNING_THRESHOLDS['max_water_binder_ratio']}]",
                message=(
                    f"La relación agua/cementante ({ratios.water_binder_ratio}) se encuentra fuera del rango "
                    f"típico de calibración de UCI 165 ([{WARNING_THRESHOLDS['min_water_binder_ratio']}, "
                    f"{WARNING_THRESHOLDS['max_water_binder_ratio']}]). La estimación puede presentar mayor dispersión."
                ),
            )
        )

    # 4.3 Advertencias por Alta Sustitución de Cemento por SCMs
    if ratios.scm_replacement_percentage > WARNING_THRESHOLDS["extreme_scm_replacement_pct"]:
        warnings.append(
            StructuredWarning(
                code="WARN_EXTREME_SCM_REPLACEMENT",
                severity="warning",
                field="scm_replacement_percentage",
                observed_value=ratios.scm_replacement_percentage,
                reference_boundary=f"<= {WARNING_THRESHOLDS['extreme_scm_replacement_pct']}%",
                message=(
                    f"Nivel extremo de sustitución de cemento por SCMs ({ratios.scm_replacement_percentage}%). "
                    "Se anticipa un desarrollo sumamente lento de resistencia inicial (< 7 días). "
                    "Se exige estricto curado húmedo continuo y ensayo a 56 días para verificación."
                ),
            )
        )
    elif ratios.scm_replacement_percentage > WARNING_THRESHOLDS["high_scm_replacement_pct"]:
        warnings.append(
            StructuredWarning(
                code="WARN_HIGH_SCM_REPLACEMENT",
                severity="info",
                field="scm_replacement_percentage",
                observed_value=ratios.scm_replacement_percentage,
                reference_boundary=f"<= {WARNING_THRESHOLDS['high_scm_replacement_pct']}%",
                message=(
                    f"Sustitución ecológica significativa ({ratios.scm_replacement_percentage}% de SCMs). "
                    "Se recomienda extender el período de curado húmedo para garantizar la hidratación puzolánica."
                ),
            )
        )

    # 4.4 Advertencia por Superplastificante Alto sin Reducción de Agua
    if (
        mix_design.superplasticizer > WARNING_THRESHOLDS["high_sp_dose_kg_m3"]
        and mix_design.water > WARNING_THRESHOLDS["high_sp_water_threshold_kg_m3"]
    ):
        warnings.append(
            StructuredWarning(
                code="WARN_SUPERPLASTICIZER_HIGH_WATER",
                severity="warning",
                field="superplasticizer",
                observed_value=mix_design.superplasticizer,
                reference_boundary=f"sp <= {WARNING_THRESHOLDS['high_sp_dose_kg_m3']} kg/m3 cuando agua > {WARNING_THRESHOLDS['high_sp_water_threshold_kg_m3']} kg/m3",
                message=(
                    f"Dosis elevada de superplastificante ({mix_design.superplasticizer} kg/m³) combinada con alto "
                    f"contenido de agua ({mix_design.water} kg/m³). Elevado riesgo de exudación, retardo de fraguado o segregación."
                ),
            )
        )

    # 4.5 Advertencia por Alta Relación Agua/Cemento
    if (
        ratios.water_cement_ratio is not None
        and ratios.water_cement_ratio > WARNING_THRESHOLDS["high_water_cement_ratio"]
    ):
        warnings.append(
            StructuredWarning(
                code="WARN_HIGH_WATER_CEMENT_RATIO",
                severity="info",
                field="water_cement_ratio",
                observed_value=ratios.water_cement_ratio,
                reference_boundary=f"<= {WARNING_THRESHOLDS['high_water_cement_ratio']}",
                message=(
                    f"Relación agua/cemento elevada ({ratios.water_cement_ratio}). "
                    "Verifique los requisitos de durabilidad y permeabilidad según la norma técnica local."
                ),
            )
        )

    return ValidationResult(
        is_valid=True,
        mix_design=mix_design,
        ratios=ratios,
        errors=[],
        warnings=warnings,
        problem_details=None,
    )


def validate_or_raise(
    data: Union[ConcreteMixDesign, Dict[str, Any]],
) -> Tuple[ConcreteMixDesign, MixRatios, List[StructuredWarning]]:
    """
    Valida la dosificación y retorna una tupla (mix_design, ratios, warnings).
    Si se detectan errores duros, lanza una excepción tipada DomainValidationError.

    Args:
        data: ConcreteMixDesign o dict.

    Returns:
        Tupla con (mix_design, ratios, warnings).

    Raises:
        DomainValidationError: Si la dosificación no es válida.
    """
    result = validate_mix_design(data)
    if not result.is_valid:
        assert result.problem_details is not None
        raise DomainValidationError(result.problem_details)

    assert result.mix_design is not None
    assert result.ratios is not None
    return result.mix_design, result.ratios, result.warnings
