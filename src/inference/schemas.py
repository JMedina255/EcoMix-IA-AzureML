"""
Esquemas Pydantic v2 para el servicio de inferencia de EcoMix IA.
Define los contratos de datos para la plataforma web ASP.NET MVC 5:
- Dosificación de 7 insumos (kg/m³).
- Solicitud de predicción dual (7 y 28 días).
- Respuesta con predicciones de resistencia y ratios de mezcla.
- Advertencias estructuradas (OOD y buenas prácticas).
- Estructura de errores conforme a RFC 7807 (Problem Details).
"""

from __future__ import annotations

import math
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, ConfigDict, Field, field_validator


class ConcreteMixDesign(BaseModel):
    """
    Dosificación de materiales para 1 m³ de concreto fresco.
    Todos los insumos se especifican en kilogramos por metro cúbico (kg/m³).
    """

    model_config = ConfigDict(
        extra="ignore",
        populate_by_name=True,
        allow_inf_nan=False,
        str_strip_whitespace=True,
        validate_assignment=True,
    )

    cement: float = Field(
        ...,
        ge=0.0,
        description="Contenido de Cemento Portland en kg/m³.",
        examples=[280.0],
    )
    blast_furnace_slag: float = Field(
        default=0.0,
        ge=0.0,
        description="Contenido de Escoria granulada de alto horno (GGBFS) en kg/m³.",
        examples=[105.0],
    )
    fly_ash: float = Field(
        default=0.0,
        ge=0.0,
        description="Contenido de Ceniza volante o Puzolana en kg/m³.",
        examples=[60.0],
    )
    water: float = Field(
        ...,
        ge=0.0,
        description="Contenido de agua de mezclado en kg/m³ (o litros/m³).",
        examples=[175.0],
    )
    superplasticizer: float = Field(
        default=0.0,
        ge=0.0,
        description="Contenido de aditivo superplastificante / reductor de agua en kg/m³.",
        examples=[8.5],
    )
    coarse_aggregate: float = Field(
        ...,
        ge=0.0,
        description="Contenido de agregado grueso (grava/piedra chancada) en kg/m³.",
        examples=[1020.0],
    )
    fine_aggregate: float = Field(
        ...,
        ge=0.0,
        description="Contenido de agregado fino (arena) en kg/m³.",
        examples=[750.0],
    )

    @field_validator(
        "cement",
        "blast_furnace_slag",
        "fly_ash",
        "water",
        "superplasticizer",
        "coarse_aggregate",
        "fine_aggregate",
        mode="after",
    )
    @classmethod
    def validate_non_negative_and_finite(cls, value: float, info) -> float:
        """Valida que los componentes sean números finitos y no negativos."""
        if not math.isfinite(value):
            raise ValueError(f"El campo '{info.field_name}' debe ser un número real finito.")
        if value < 0.0:
            raise ValueError(
                f"El campo '{info.field_name}' no puede ser negativo (recibido: {value} kg/m³)."
            )
        return float(value)


class PredictionRequest(BaseModel):
    """
    Solicitud de inferencia de resistencia a compresión.
    El campo $schema no es obligatorio y es ignorado si es enviado por ASP.NET MVC 5.
    """

    model_config = ConfigDict(
        extra="ignore",
        populate_by_name=True,
    )

    mix_design: ConcreteMixDesign = Field(
        ...,
        description="Dosificación de los 7 componentes en kg/m³ para 1 m³ de concreto.",
    )
    request_id: Optional[str] = Field(
        default=None,
        description="Identificador correlativo opcional para trazabilidad en ASP.NET MVC 5.",
    )
    options: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Opciones avanzadas opcionales para módulos desacoplados futuros.",
    )


class StrengthPredictions(BaseModel):
    """
    Predicciones puntuales determinísticas de resistencia a compresión (MPa).
    Generadas por el modelo VotingEnsemble para 7 y 28 días de curado.
    """

    model_config = ConfigDict(
        extra="ignore",
        populate_by_name=True,
    )

    strength_7d_mpa: float = Field(
        ...,
        description="Resistencia a compresión estimada a 7 días de curado (MPa).",
        examples=[24.18],
    )
    strength_28d_mpa: float = Field(
        ...,
        description="Resistencia a compresión estimada a 28 días de curado (MPa).",
        examples=[38.65],
    )


class MixRatios(BaseModel):
    """
    Relaciones de dosificación calculadas analíticamente para el diseño de mezclas.
    """

    model_config = ConfigDict(
        extra="ignore",
        populate_by_name=True,
    )

    water_cement_ratio: Optional[float] = Field(
        default=None,
        description="Relación agua/cemento en masa (w/c). Nulo si cemento es 0.",
        examples=[0.625],
    )
    water_binder_ratio: float = Field(
        ...,
        description="Relación agua/material cementante total (w/b o a/mc).",
        examples=[0.393],
    )
    total_cementitious_content_kg_m3: float = Field(
        ...,
        description="Masa total de materiales cementantes (cemento + escoria + ceniza) en kg/m³.",
        examples=[445.0],
    )
    scm_replacement_percentage: float = Field(
        ...,
        description="Porcentaje de sustitución de cemento por SCMs (escoria + puzolana) (%).",
        examples=[37.08],
    )
    aggregates_total_kg_m3: float = Field(
        ...,
        description="Masa combinada de agregados (grueso + fino) en kg/m³.",
        examples=[1770.0],
    )
    total_mass_kg_m3: float = Field(
        ...,
        description="Masa volumétrica total estimada de la mezcla fresca en kg/m³.",
        examples=[2398.5],
    )


class StructuredWarning(BaseModel):
    """
    Advertencia estructurada no bloqueante (HTTP 200) generada por el motor de dominio.
    Indica extrapolación del espacio muestral UCI 165 o recomendaciones tecnológicas.
    """

    model_config = ConfigDict(
        extra="ignore",
        populate_by_name=True,
    )

    code: str = Field(
        ...,
        description="Código identificador estandarizado de la advertencia.",
        examples=["WARN_OOD_WATER", "WARN_HIGH_SCM_REPLACEMENT"],
    )
    severity: str = Field(
        default="warning",
        description="Nivel de severidad de la advertencia ('info' o 'warning').",
        examples=["warning"],
    )
    field: Optional[str] = Field(
        default=None,
        description="Nombre del campo o parámetro relacionado.",
        examples=["water"],
    )
    message: str = Field(
        ...,
        description="Descripción detallada de la advertencia en lenguaje de ingeniería.",
    )
    observed_value: Optional[float] = Field(
        default=None,
        description="Valor numérico detectado en la entrada.",
    )
    reference_boundary: Optional[str] = Field(
        default=None,
        description="Límite o rango de referencia experimental del dataset UCI 165.",
    )


class ModelMetadata(BaseModel):
    """
    Metadatos de procedencia y trazabilidad del modelo de Machine Learning.
    """

    model_config = ConfigDict(
        extra="ignore",
        populate_by_name=True,
    )

    model_id: str = Field(
        default="wheat_cheese_4swj34tkjn_11",
        description="Identificador del Child Run ganador en Azure ML AutoML.",
    )
    model_type: str = Field(
        default="VotingEnsemble",
        description="Algoritmo de ensamble optimizado en Azure ML.",
    )
    model_sha256: Optional[str] = Field(
        default="7eaa501c5eeb60135effb6b5861e736518ce969c47afd53727c2451083ff6388",
        description="Hash SHA-256 del artefacto binario model.pkl.",
    )
    inference_timestamp: Optional[str] = Field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat(),
        description="Marca de tiempo UTC de la evaluación del modelo.",
    )


class PredictionResponse(BaseModel):
    """
    Respuesta exitosa (HTTP 200) del servicio de inferencia de EcoMix IA.
    Entrega predicciones puntuales a 7 y 28 días, relaciones de dosificación y advertencias.
    """

    model_config = ConfigDict(
        extra="ignore",
        populate_by_name=True,
    )

    status: str = Field(
        default="success",
        description="Estado general de la operación ('success').",
    )
    predictions: StrengthPredictions = Field(
        ...,
        description="Predicciones determinísticas de resistencia a compresión (MPa).",
    )
    mix_ratios: MixRatios = Field(
        ...,
        description="Relaciones y parámetros derivados de dosificación.",
    )
    warnings: List[StructuredWarning] = Field(
        default_factory=list,
        description="Lista de advertencias estructuradas por extrapolación de dominio.",
    )
    metadata: ModelMetadata = Field(
        default_factory=ModelMetadata,
        description="Metadatos de trazabilidad del modelo y tiempo de inferencia.",
    )


class InvalidFieldDetail(BaseModel):
    """
    Detalle específico de un campo inválido en una solicitud rechazada.
    """

    model_config = ConfigDict(
        extra="ignore",
        populate_by_name=True,
    )

    field: str = Field(
        ...,
        description="Nombre del campo afectado en la solicitud.",
        examples=["mix_design.water"],
    )
    value: Any = Field(
        ...,
        description="Valor no válido recibido.",
        examples=[-5.0],
    )
    constraint: str = Field(
        ...,
        description="Restricción física o de formato violada.",
        examples=["non_negative", "finite_number", "physical_minimum"],
    )
    limit: Optional[Any] = Field(
        default=None,
        description="Límite físico o regla esperada.",
        examples=[0.0],
    )
    unit: Optional[str] = Field(
        default="kg/m3",
        description="Unidad de medida aplicable.",
    )
    message: str = Field(
        ...,
        description="Mensaje explicativo del error para el usuario de la aplicación web.",
    )


class ProblemDetails(BaseModel):
    """
    Estructura de error de validación conforme al estándar RFC 7807 (Problem Details for HTTP APIs).
    Retornada con código HTTP 422 cuando la dosificación es físicamente imposible o inválida.
    """

    model_config = ConfigDict(
        extra="ignore",
        populate_by_name=True,
    )

    type: str = Field(
        default="https://ecomixia.yura.com.pe/errors/validation-error",
        description="URI de referencia sobre el tipo de error.",
    )
    title: str = Field(
        default="Error de Validación de Dosificación",
        description="Resumen breve y legible del problema.",
    )
    status: int = Field(
        default=422,
        description="Código de estado HTTP aplicable (422 Unprocessable Entity).",
    )
    detail: str = Field(
        ...,
        description="Explicación detallada y legible del error detectado.",
    )
    instance: Optional[str] = Field(
        default="/api/v1/predict/concrete-strength",
        description="URI del endpoint invocado.",
    )
    invalid_fields: List[InvalidFieldDetail] = Field(
        default_factory=list,
        description="Colección de campos específicos que violaron restricciones duras.",
    )
    timestamp: str = Field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat(),
        description="Marca de tiempo UTC del evento de error.",
    )
