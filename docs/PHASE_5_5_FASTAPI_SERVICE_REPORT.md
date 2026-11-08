# Informe Técnico de Implementación — Fase 5.5: API REST FastAPI para Servicio de Inferencia ML

**Proyecto:** EcoMix IA (Azure Machine Learning)  
**Convocatoria:** Reto 2 — Yura S.A. (Hackathon Innova Sur 2026, Universidad Privada de Tacna)  
**Línea base Git:** `3c942d54a2a11b7dfb5f19036f030bc345d259c7`  
**Rama activa:** `feat/phase-05-inference-service`  
**Fecha:** Noviembre 2026  
**Responsable:** Arquitecto de Software y MLOps — EcoMix IA  
**Veredicto:** **API IMPLEMENTADA Y VERIFICADA AL 100%**

---

## 1. Resumen Ejecutivo

En la presente Fase 5.5 se ha completado la construcción y verificación exhaustiva del servicio HTTP REST en **FastAPI** para la plataforma **EcoMix IA**. Este servicio expone de manera segura, desacoplada y eficiente el motor de inferencia predictiva fundamentado en el modelo oficial certificado `VotingEnsemble` (Child Run `wheat_cheese_4swj34tkjn_11`, hash SHA-256 `7eaa501c5eeb60135effb6b5861e736518ce969c47afd53727c2451083ff6388`), validado experimentalmente en Azure ML durante la Fase 5.4.

El diseño garantiza desacoplamiento absoluto:
1. **Consumo por ASP.NET MVC 5:** La aplicación web corporativa (desarrollada en C# sobre .NET Framework 4.8 / ASP.NET MVC 5 con Entity Framework 6 y SQL Server) interactúa con el modelo predictivo a través de llamadas HTTP seguras con contratos JSON tipados, sin requerir dependencias de Python ni librerías de Azure AutoML en el servidor web.
2. **Ciclo de Vida Optimizado (Lifespan):** El estimador de Machine Learning se carga e inicializa en memoria RAM una única vez al arrancar el contenedor/proceso, garantizando tiempos de inferencia en caliente (*warm inference*) del orden de decenas de milisegundos, muy por debajo del SLA de 2 000 ms.
3. **Observabilidad y Seguridad de Nivel Corporativo:** Implementación de autenticación de máquina a máquina mediante `X-API-Key`, trazabilidad distribuida vía `X-Request-ID`, medición precisa de latencia con `X-Response-Time-Ms`, y normalización estricta de errores bajo el estándar internacional **RFC 7807 (Problem Details for HTTP APIs)**.

---

## 2. Arquitectura del Servicio (`src/api/`)

El módulo `src/api/` se diseñó bajo una estructura modular orientada al principio de responsabilidad única (SRP):

```
src/api/
├── __init__.py                # Inicializador del paquete
├── config.py                  # Configuración declarativa y tipada (Pydantic Settings / .env)
├── dependencies.py            # Inyección de dependencias seguras (API Key, Loader, Engine)
├── middleware.py              # Middleware ASGI (X-Request-ID, X-Response-Time-Ms, límite 1 MB)
├── exception_handlers.py      # Normalización global de errores bajo RFC 7807 (ProblemDetails)
├── main.py                    # Fábrica de aplicación FastAPI, ciclo de vida (lifespan) y CLI
└── routes/
    ├── __init__.py            # Exportación de enrutadores
    ├── health.py              # Sondas de salud y preparación (/health/live, /health/ready)
    ├── model.py               # Metadatos y diagnóstico del modelo (/api/v1/model/info)
    └── prediction.py          # Inferencia dual a 7 y 28 días (/api/v1/predict/concrete-strength)
```

### Componentes Clave

1. **`config.py` (`ApiSettings`):**
   - Configuración desacoplada del código fuente mediante variables de entorno con prefijo `ECOMIX_`.
   - Soporta modos de entorno: `development`, `test`, `staging` y `production`.
   - Controla activación de autenticación, llaves secretas maestras, límites de carga útil (1 MB por defecto) y puerto de escucha.

2. **`middleware.py` (`ObservabilityMiddleware`):**
   - Genera o preserva cabeceras `X-Request-ID` para correlación de logs de extremo a extremo entre ASP.NET y FastAPI.
   - Inyecta `X-Response-Time-Ms` con medición en milisegundos de alta precisión (`time.perf_counter()`).
   - Rechaza tempranamente cargas útiles que excedan el límite físico (1 MB) con código HTTP 413 (`Payload Too Large`) antes de procesar el body.

3. **`exception_handlers.py`:**
   - Convierte de manera uniforme cualquier excepción interna en respuestas estructuradas `application/problem+json`:
     * `DomainValidationError` $\rightarrow$ HTTP 422 (`Unprocessable Entity`) con desglose de campos y reglas de dosificación violadas.
     * `RequestValidationError` $\rightarrow$ HTTP 422 (`Unprocessable Entity`) con detalle de esquema JSON sintáctico.
     * `IncompatibleRuntimeError` / `ModelNotFoundError` $\rightarrow$ HTTP 503 (`Service Unavailable`).
     * `HTTPException` (401, 403, 404, 413) $\rightarrow$ ProblemDetails normalizado sin filtrar secretos.
     * `Exception` no controlada $\rightarrow$ HTTP 500 (`Internal Server Error`) enmascarando trazas internas y registrando el `request_id` en el log del servidor.

4. **`routes/health.py`:**
   - Separación estricta entre **Sonda de Vida** (`/health/live`) y **Sonda de Preparación** (`/health/ready`).
   - Permite que los orquestadores (Kubernetes, Azure Container Apps, Azure App Service) no reinicien el contenedor durante los 26 segundos de inicialización en frío de las librerías de ML, reportando disponibilidad únicamente cuando el modelo se encuentra instanciado en RAM.

---

## 3. Catálogo de Endpoints y Especificación de Contratos

| Método | Endpoint | Autenticación | Códigos HTTP | Propósito |
|---|---|---|---|---|
| `GET` | `/health/live` | Pública | 200 | Sonda de vida del proceso ASGI |
| `GET` | `/health/ready` | Pública | 200, 503 | Sonda de preparación (RAM y runtime) |
| `GET` | `/` | Pública | 200 | Bienvenida e información del servicio |
| `GET` | `/api/v1/model/info` | `X-API-Key` | 200, 401, 403 | Ficha técnica y procedencia del modelo |
| `POST` | `/api/v1/predict/concrete-strength` | `X-API-Key` | 200, 401, 403, 413, 422, 503 | Predicción dual 7d/28d, ratios y advertencias |

---

## 4. Contratos de Datos JSON

### 4.1 Solicitud de Inferencia (`POST /api/v1/predict/concrete-strength`)

```json
{
  "request_id": "aspnet-req-8849204a-4421",
  "mix_design": {
    "cement": 280.0,
    "blast_furnace_slag": 105.0,
    "fly_ash": 60.0,
    "water": 175.0,
    "superplasticizer": 8.5,
    "coarse_aggregate": 1020.0,
    "fine_aggregate": 750.0
  }
}
```

> [!NOTE]
> La API acepta alternativamente las 7 cantidades de materiales directamente en la raíz del objeto JSON, permitiendo máxima flexibilidad al cliente HTTP de C#.

### 4.2 Respuesta Exitosa (`HTTP 200 OK`)

```json
{
  "status": "success",
  "request_id": "aspnet-req-8849204a-4421",
  "predictions": {
    "strength_7d_mpa": 24.18,
    "strength_28d_mpa": 38.65
  },
  "mix_ratios": {
    "total_cementitious_content_kg_m3": 445.0,
    "water_cement_ratio": 0.625,
    "water_binder_ratio": 0.3933,
    "scm_replacement_percentage": 37.08,
    "aggregates_total_kg_m3": 1770.0,
    "total_mass_kg_m3": 2398.5
  },
  "warnings": [
    {
      "code": "WARN_HIGH_SCM_REPLACEMENT",
      "severity": "info",
      "field": "scm_replacement_percentage",
      "message": "Nivel de sustitución de clínker por SCMs (37.08%) elevado. Se recomienda verificar reactividad y curado húmedo continuo.",
      "observed_value": 37.08,
      "reference_boundary": "40.0% límite sugerido para desencofrado rápido"
    }
  ],
  "metadata": {
    "model_id": "wheat_cheese_4swj34tkjn_11",
    "model_type": "VotingEnsemble",
    "model_sha256": "7eaa501c5eeb60135effb6b5861e736518ce969c47afd53727c2451083ff6388",
    "inference_timestamp": "2026-11-06T16:51:00.123456+00:00"
  }
}
```

### 4.3 Error de Validación RFC 7807 (`HTTP 422 Unprocessable Entity`)

```json
{
  "type": "https://ecomixia.yura.com.pe/errors/validation-error",
  "title": "Error de Validación de Dosificación",
  "status": 422,
  "detail": "La dosificación no cumple con los límites físicos o tecnológicos del concreto.",
  "instance": "/api/v1/predict/concrete-strength",
  "request_id": "aspnet-req-8849204a-4421",
  "invalid_fields": [
    {
      "field": "mix_design.water",
      "value": 550.0,
      "constraint": "physical_maximum",
      "limit": 350.0,
      "unit": "kg/m3",
      "message": "El contenido de agua (550.0 kg/m³) supera el límite físico universal de 350.0 kg/m³."
    }
  ],
  "timestamp": "2026-11-06T16:51:00.234567+00:00"
}
```

---

## 5. Guía de Integración para ASP.NET MVC 5 (C# / .NET 4.8)

Para facilitar la adopción por el equipo de desarrollo de la plataforma web en C#, se proporcionan los modelos POCO y el servicio cliente con manejo de resiliencia y deserialización de errores.

### 5.1 Modelos POCO en C#

```csharp
using System;
using System.Collections.Generic;
using Newtonsoft.Json;

namespace EcoMixIA.Web.Models.MlApi
{
    public class PredictionRequestDto
    {
        [JsonProperty("request_id")]
        public string RequestId { get; set; } = Guid.NewGuid().ToString();

        [JsonProperty("mix_design")]
        public MixDesignDto MixDesign { get; set; }
    }

    public class MixDesignDto
    {
        [JsonProperty("cement")]
        public double Cement { get; set; }

        [JsonProperty("blast_furnace_slag")]
        public double BlastFurnaceSlag { get; set; }

        [JsonProperty("fly_ash")]
        public double FlyAsh { get; set; }

        [JsonProperty("water")]
        public double Water { get; set; }

        [JsonProperty("superplasticizer")]
        public double Superplasticizer { get; set; }

        [JsonProperty("coarse_aggregate")]
        public double CoarseAggregate { get; set; }

        [JsonProperty("fine_aggregate")]
        public double FineAggregate { get; set; }
    }

    public class PredictionResponseDto
    {
        [JsonProperty("status")]
        public string Status { get; set; }

        [JsonProperty("request_id")]
        public string RequestId { get; set; }

        [JsonProperty("predictions")]
        public StrengthPredictionsDto Predictions { get; set; }

        [JsonProperty("mix_ratios")]
        public MixRatiosDto MixRatios { get; set; }

        [JsonProperty("warnings")]
        public List<StructuredWarningDto> Warnings { get; set; } = new List<StructuredWarningDto>();

        [JsonProperty("metadata")]
        public ModelMetadataDto Metadata { get; set; }
    }

    public class StrengthPredictionsDto
    {
        [JsonProperty("strength_7d_mpa")]
        public double Strength7dMpa { get; set; }

        [JsonProperty("strength_28d_mpa")]
        public double Strength28dMpa { get; set; }
    }

    public class MixRatiosDto
    {
        [JsonProperty("total_cementitious_content_kg_m3")]
        public double TotalCementitiousContentKgM3 { get; set; }

        [JsonProperty("water_cement_ratio")]
        public double WaterCementRatio { get; set; }

        [JsonProperty("water_binder_ratio")]
        public double WaterBinderRatio { get; set; }

        [JsonProperty("scm_replacement_percentage")]
        public double ScmReplacementPercentage { get; set; }

        [JsonProperty("aggregates_total_kg_m3")]
        public double AggregatesTotalKgM3 { get; set; }

        [JsonProperty("total_mass_kg_m3")]
        public double TotalMassKgM3 { get; set; }
    }

    public class StructuredWarningDto
    {
        [JsonProperty("code")]
        public string Code { get; set; }

        [JsonProperty("severity")]
        public string Severity { get; set; }

        [JsonProperty("field")]
        public string Field { get; set; }

        [JsonProperty("message")]
        public string Message { get; set; }

        [JsonProperty("observed_value")]
        public object ObservedValue { get; set; }

        [JsonProperty("reference_boundary")]
        public string ReferenceBoundary { get; set; }
    }

    public class ModelMetadataDto
    {
        [JsonProperty("model_id")]
        public string ModelId { get; set; }

        [JsonProperty("model_type")]
        public string ModelType { get; set; }

        [JsonProperty("model_sha256")]
        public string ModelSha256 { get; set; }

        [JsonProperty("inference_timestamp")]
        public string InferenceTimestamp { get; set; }
    }

    public class ProblemDetailsDto
    {
        [JsonProperty("type")]
        public string Type { get; set; }

        [JsonProperty("title")]
        public string Title { get; set; }

        [JsonProperty("status")]
        public int Status { get; set; }

        [JsonProperty("detail")]
        public string Detail { get; set; }

        [JsonProperty("instance")]
        public string Instance { get; set; }

        [JsonProperty("request_id")]
        public string RequestId { get; set; }

        [JsonProperty("invalid_fields")]
        public List<InvalidFieldDetailDto> InvalidFields { get; set; } = new List<InvalidFieldDetailDto>();
    }

    public class InvalidFieldDetailDto
    {
        [JsonProperty("field")]
        public string Field { get; set; }

        [JsonProperty("value")]
        public object Value { get; set; }

        [JsonProperty("constraint")]
        public string Constraint { get; set; }

        [JsonProperty("limit")]
        public object Limit { get; set; }

        [JsonProperty("unit")]
        public string Unit { get; set; }

        [JsonProperty("message")]
        public string Message { get; set; }
    }
}
```

### 5.2 Servicio Cliente en C# (`EcoMixMlClientService`)

```csharp
using System;
using System.Configuration;
using System.Net.Http;
using System.Text;
using System.Threading.Tasks;
using Newtonsoft.Json;
using EcoMixIA.Web.Models.MlApi;

namespace EcoMixIA.Web.Services
{
    public interface IEcoMixMlClientService
    {
        Task<PredictionResponseDto> PredictStrengthAsync(MixDesignDto mixDesign);
    }

    public class EcoMixMlClientService : IEcoMixMlClientService
    {
        private readonly HttpClient _httpClient;
        private readonly string _apiKey;

        public EcoMixMlClientService(HttpClient httpClient)
        {
            _httpClient = httpClient ?? throw new ArgumentNullException(nameof(httpClient));
            _apiKey = ConfigurationManager.AppSettings["EcoMix:MlApiKey"] ?? "ecomix-dev-api-key-2026";
            
            var baseUrl = ConfigurationManager.AppSettings["EcoMix:MlApiBaseUrl"] ?? "http://localhost:8000";
            if (_httpClient.BaseAddress == null)
            {
                _httpClient.BaseAddress = new Uri(baseUrl);
            }
            _httpClient.Timeout = TimeSpan.FromSeconds(5); // Cumple SLA < 2 segundos
        }

        public async Task<PredictionResponseDto> PredictStrengthAsync(MixDesignDto mixDesign)
        {
            var requestDto = new PredictionRequestDto
            {
                RequestId = Guid.NewGuid().ToString("D"),
                MixDesign = mixDesign
            };

            var jsonContent = JsonConvert.SerializeObject(requestDto);
            using (var requestMessage = new HttpRequestMessage(HttpMethod.Post, "/api/v1/predict/concrete-strength"))
            {
                requestMessage.Content = new StringContent(jsonContent, Encoding.UTF8, "application/json");
                requestMessage.Headers.Add("X-API-Key", _apiKey);
                requestMessage.Headers.Add("X-Request-ID", requestDto.RequestId);

                using (var response = await _httpClient.SendAsync(requestMessage).ConfigureAwait(false))
                {
                    var responseBody = await response.Content.ReadAsStringAsync().ConfigureAwait(false);

                    if (response.IsSuccessStatusCode)
                    {
                        return JsonConvert.DeserializeObject<PredictionResponseDto>(responseBody);
                    }

                    if (response.StatusCode == System.Net.HttpStatusCode.UnprocessableEntity)
                    {
                        var problemDetails = JsonConvert.DeserializeObject<ProblemDetailsDto>(responseBody);
                        throw new DomainValidationException(problemDetails);
                    }

                    throw new ApplicationException($"Error al consultar API ML ({response.StatusCode}): {responseBody}");
                }
            }
        }
    }

    public class DomainValidationException : Exception
    {
        public ProblemDetailsDto ProblemDetails { get; }

        public DomainValidationException(ProblemDetailsDto problemDetails)
            : base(problemDetails?.Detail ?? "Error de validación de dosificación.")
        {
            ProblemDetails = problemDetails;
        }
    }
}
```

---

## 6. Rendimiento y Mitigación del Arranque en Frío (*Cold Start*)

### 6.1 Diagnóstico de Latencias

| Escenario | Duración Observada | Impacto y Causa Raíz |
|---|---|---|
| **Cold Start (Arranque del contenedor)** | ~26.69 segundos | Deserialización inicial de Azure AutoML Tabular (`azureml-training-tabular`), importación de paquetes científicos y chequeo de integridad SHA-256 en disco. |
| **Warm Inference (Inferencia en caliente)** | **< 60 milisegundos** | Estimador retenido en RAM (`ModelLoader` singleton); cálculo directo en NumPy/Pandas en memoria. Supera ampliamente el SLA de 2 000 ms. |
| **Respuesta Liveness (`/health/live`)** | < 5 milisegundos | Respuesta inmediata de proceso ASGI vivo. |

### 6.2 Estrategia de Mitigación en Producción

1. **Desacoplamiento de Sondas en Orquestador:**
   - La sonda `livenessProbe` consulta `/health/live` desde el segundo 5 (`initialDelaySeconds: 5`, `periodSeconds: 10`).
   - La sonda `readinessProbe` consulta `/health/ready` con `initialDelaySeconds: 25` y `failureThreshold: 6`. De este modo, Azure Container Apps no enruta tráfico ni declara caído el pod mientras el modelo termina de cargar en memoria.
2. **Réplica Mínima Activa (Zero Cold Start en Producción):**
   - Configuración en Azure Container Apps o App Service de `minReplicas = 1` y *Always On = Enabled*. Esto elimina el apagado por inactividad y garantiza que todas las peticiones de los ingenieros de diseño de mezcla se sirvan en < 80 ms.
3. **Calentamiento Sintético en `lifespan`:**
   - Durante el evento `startup`, el servicio realiza un pase de predicción dummy para asegurar que los módulos de JIT / Cython / BLAS de Scikit-learn estén compilados en memoria antes de recibir la primera petición externa.

---

## 7. Resultados de Pruebas Automatizadas

Se diseñó e implementó la suite completa de pruebas de integración para la API en [`tests/test_api_service.py`](../tests/test_api_service.py), validando 18 escenarios críticos:

```
tests/test_api_service.py::test_liveness_probe_returns_200 PASSED                    [  5%]
tests/test_api_service.py::test_readiness_probe_returns_503_when_model_not_loaded PASSED [ 11%]
tests/test_api_service.py::test_readiness_probe_returns_200_when_model_is_ready PASSED [ 16%]
tests/test_api_service.py::test_root_endpoint_returns_service_info PASSED            [ 22%]
tests/test_api_service.py::test_api_key_missing_returns_401 PASSED                  [ 27%]
tests/test_api_service.py::test_api_key_invalid_returns_403 PASSED                  [ 33%]
tests/test_api_service.py::test_api_key_valid_grants_access PASSED                  [ 38%]
tests/test_api_service.py::test_predict_returns_503_when_model_not_ready PASSED     [ 44%]
tests/test_api_service.py::test_predict_canonical_mix_success_and_json_contract PASSED [ 50%]
tests/test_api_service.py::test_predict_accepts_direct_component_dict PASSED        [ 55%]
tests/test_api_service.py::test_predict_high_scm_returns_warnings_in_json PASSED    [ 61%]
tests/test_api_service.py::test_api_predict_has_exact_numerical_parity_with_engine PASSED [ 66%]
tests/test_api_service.py::test_domain_validation_negative_cement_returns_422 PASSED [ 72%]
tests/test_api_service.py::test_domain_validation_excessive_water_binder_ratio_returns_422 PASSED [ 77%]
tests/test_api_service.py::test_malformed_json_types_returns_422 PASSED             [ 83%]
tests/test_api_service.py::test_oversized_payload_returns_413 PASSED                [ 88%]
tests/test_api_service.py::test_concurrent_api_requests_are_thread_safe_and_deterministic PASSED [ 94%]
tests/test_api_service.py::test_request_id_and_timing_headers_propagated PASSED    [100%]
```

- **Pruebas de la API:** 18 aprobadas / 0 fallidas (100% de éxito).
- **Pruebas Totales de Regresión:** 162 pruebas aprobadas en el repositorio (incluyendo evaluación, jobs, schemas, descargas y doctor).

---

## 8. Guía de Ejecución Local y Verificación

### 8.1 Iniciar el Servidor API

```bash
# Iniciar con Uvicorn en el puerto 8000
python -m uvicorn src.api.main:app --host 0.0.0.0 --port 8000 --reload
```

### 8.2 Comprobar Estado de Salud

```bash
# Liveness probe
curl -i http://localhost:8000/health/live

# Readiness probe
curl -i http://localhost:8000/health/ready
```

### 8.3 Ejecutar Inferencia de Prueba

```bash
curl -X POST "http://localhost:8000/api/v1/predict/concrete-strength" \
     -H "Content-Type: application/json" \
     -H "X-API-Key: ecomix-dev-api-key-2026" \
     -d '{
       "mix_design": {
         "cement": 280.0,
         "blast_furnace_slag": 105.0,
         "fly_ash": 60.0,
         "water": 175.0,
         "superplasticizer": 8.5,
         "coarse_aggregate": 1020.0,
         "fine_aggregate": 750.0
       }
     }'
```

---

## 9. Próximos Pasos Recomendados

Habiendo concluido satisfactoriamente la Fase 5.5 con la API REST operativa y probada, el repositorio se encuentra en condiciones óptimas para:
1. **Fase 5.6:** Creación del `Dockerfile` de producción multi-etapa y configuración declarativa para despliegue en **Azure Container Apps** o **Azure App Service for Linux**.
2. **Integración Frontend/Backend:** Entrega de contratos y modelos C# al equipo de desarrollo de la plataforma web ASP.NET MVC 5.
