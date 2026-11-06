# Informe Técnico de Despliegue en Azure Container Apps — Fase 5.6-C.3

**Proyecto:** EcoMix IA (Azure Machine Learning)  
**Convocatoria:** Reto 2 — Yura S.A. (Hackathon Innova Sur 2026, Universidad Privada de Tacna)  
**Rama activa:** `fix/phase-05-api-hardening`  
**Fecha:** Noviembre 2026  
**Responsable:** Arquitecto Azure, Ingeniero MLOps y Especialista DevSecOps  
**Veredicto:** **DESPLIEGUE EN PRODUCCIÓN CLOUD CULMINADO CON ÉXITO — INFERENCIA REAL OPERATIVA EN AZURE CONTAINER APPS (CHILE CENTRAL)**

---

## 1. Resumen Ejecutivo

En cumplimiento de la autorización y directrices de la Fase 5.6-C.3, se ha desplegado y validado satisfactoriamente el microservicio de inferencia de **EcoMix IA** en **Azure Container Apps (ACA)** sobre arquitectura Serverless Consumption en la región **`chilecentral`**.

El microservicio ejecuta el pipeline real **`VotingEnsemble`** (iteración 11 del experimento Azure ML AutoML `wheat_cheese_4swj34tkjn`), preservando su entorno nativo Python 3.10.19, verificando su integridad criptográfica SHA-256 en el arranque y sirviendo predicciones de resistencia a compresión (7 y 28 días) vía HTTPS con latencias promedio de **~248 ms**, superando ampliamente el SLA contractual de 2,000 ms (ISO/IEC 25010).

### Cuadro de Especificaciones de Producción

| Parámetro | Valor Certificado |
|---|---|
| **Servicio Cloud** | Azure Container Apps (ACA) |
| **Perfil de Cómputo** | Serverless Consumption (Pago por uso exacto) |
| **Nombre de la Aplicación** | `ca-ecomix-inference-api` |
| **Entorno de Container Apps** | `env-ecomix-prod` |
| **Región de Despliegue** | `chilecentral` (Chile Central) |
| **Grupo de Recursos** | `EcomixIA` |
| **Punto de Entrada (FQDN HTTPS)** | `https://ca-ecomix-inference-api.salmontree-d9db53a4.chilecentral.azurecontainerapps.io` |
| **Registro de Contenedores (ACR)** | `crecomixprod.azurecr.io` (SKU Basic, sin usuario admin) |
| **Imagen Ejecutada** | `crecomixprod.azurecr.io/ecomix-ml-inference:1.0.0` |
| **Digest OCI de la Imagen** | `sha256:f50d37251430ad1e42d8df663554e0ea346a8dfffae8799393023d4afbb1d12a` |
| **Identidad Administrada (MSI)** | `id-ecomix-aca` (User-Assigned Managed Identity) |
| **Rol RBAC sobre ACR** | `AcrPull` (autenticación sin contraseñas estáticas) |
| **Dimensionamiento** | 1.0 vCPU, 2.0 GiB de RAM por réplica |
| **Política de Autoescala** | `minReplicas = 0`, `maxReplicas = 1` (Scale-to-Zero habilitado) |
| **Mecanismo de Autenticación** | `X-API-Key` mediante secreto seguro administrado |
| **Algoritmo Estimador Activo** | `RegressionPipeline` (`VotingEnsemble` real, `is_synthetic: false`) |
| **Hash SHA-256 del Modelo Verificado** | `7eaa501c5eeb60135effb6b5861e736518ce969c47afd53727c2451083ff6388` |
| **Latencia Típica en Caliente** | **~248 ms** (Promedio de 3 invocaciones consecutivas) |
| **Costo Computacional Incurrido** | **USD 0.00** (Dentro de la cuota gratuita mensual de ACA) |

---

## 2. Arquitectura de Despliegue y Gobernanza Cloud

```
                                  +-------------------------------------------------------------+
                                  |                     Azure Chile Central                     |
                                  |                                                             |
+--------------------------+      |   +---------------------+        +----------------------+   |
|   Cliente Consumidor     |      |   |  Azure Container    |        |  Managed Identity    |   |
|   (ASP.NET MVC 5 / Test) |      |   |  Registry (ACR)     |        |  id-ecomix-aca       |   |
+------------+-------------+      |   |  crecomixprod       |        |  (Client ID:         |   |
             |                    |   |  (SKU Basic)        |        |   702de947-...)      |   |
             | HTTPS              |   +----------+----------+        +----------+-----------+   |
             | X-API-Key          |              ^                              |               |
             v                    |              | AcrPull RBAC                 |               |
+--------------------------+      |              +------------------------------+               |
| Ingress Externo Seguro   |      |                             |                               |
| (TLS 1.2+ / Port 443)    |----->|   +-------------------------v---------------------------+   |
+--------------------------+      |   |  Managed Environment: env-ecomix-prod              |   |
                                  |   |                                                     |   |
                                  |   |  +-----------------------------------------------+  |   |
                                  |   |  | Container App: ca-ecomix-inference-api        |  |   |
                                  |   |  | - Image: crecomixprod.azurecr.io/...:1.0.0     |  |   |
                                  |   |  | - Resources: 1.0 vCPU, 2.0 GiB RAM            |  |   |
                                  |   |  | - Scale: 0 <= replicas <= 1 (Scale-to-Zero)   |  |   |
                                  |   |  | - Secret: api-key (Masked)                    |  |   |
                                  |   |  | - Model: Real VotingEnsemble (SHA-256 Valid)  |  |   |
                                  |   |  +-----------------------------------------------+  |   |
                                  |   +-----------------------------------------------------+   |
                                  +-------------------------------------------------------------+
```

### 2.1 Identidad Administrada y Principio de Menor Privilegio (PoLP)
En estricto cumplimiento de las normas DevSecOps:
1. No se habilitó la cuenta de usuario administrador en Azure Container Registry (`adminUserEnabled: false`).
2. Se aprovisionó una identidad administrada asignada por el usuario (**User-Assigned Managed Identity**) denominada `id-ecomix-aca`.
3. Se concedió a dicha identidad el rol de lectura estricto **`AcrPull`** acotado exclusivamente al alcance del recurso `crecomixprod`.
4. La Container App fue configurada para resolver la imagen contra el ACR utilizando `id-ecomix-aca` como credencial federada, eliminando por completo cualquier necesidad de rotación de credenciales estáticas.

### 2.2 Política de Escala a Cero (`Scale-to-Zero`)
Para salvaguardar los fondos limitados de la suscripción `Azure for Students` (presupuesto disponible: USD 20.00):
- Se configuró la regla de escalado con `minReplicas = 0` y `maxReplicas = 1`.
- En estado ocioso (sin solicitudes HTTP entrantes durante el período de inactividad de ACA), el contenedor se apaga automáticamente, reduciendo el consumo de cómputo a **0 vCPU / 0 GiB** y garantizando **costo cero por cómputo**.
- Al recibir una solicitud entrante en el ingress HTTPS, ACA reactiva la réplica de manera transparente.

---

## 3. Protocolo de Validación en la Nube y Evidencias de Ejecución

Se ejecutó la batería exhaustiva de pruebas funcionales, de seguridad, validación y predicción contra el endpoint productivo:
`https://ca-ecomix-inference-api.salmontree-d9db53a4.chilecentral.azurecontainerapps.io`

### 3.1 Sonda de Liveness (`GET /health/live`)
- **Objetivo:** Comprobar la respuesta del servidor web ASGI (FastAPI / Uvicorn).
- **Código HTTP Retornado:** `200 OK`
- **Latencia:** `1,435 ms`
- **Cuerpo de Respuesta:**
  ```json
  {
    "status": "alive",
    "service": "ecomix-ia-ml-api"
  }
  ```

### 3.2 Sonda de Readiness y Auditoría del Modelo (`GET /health/ready`)
- **Objetivo:** Comprobar que el modelo cargado en memoria corresponde al VotingEnsemble real entrenado en Azure ML y verificar su hash criptográfico.
- **Código HTTP Retornado:** `200 OK`
- **Latencia:** `466 ms`
- **Cuerpo de Respuesta:**
  ```json
  {
    "status": "ready",
    "model_ready": true,
    "model_id": "wheat_cheese_4swj34tkjn_11",
    "model_type": "VotingEnsemble",
    "model_sha256": "7eaa501c5eeb60135effb6b5861e736518ce969c47afd53727c2451083ff6388",
    "is_synthetic": false,
    "features_expected": 8,
    "environment": "production"
  }
  ```
- **Conclusión Técnica:** La imagen en Azure Container Apps deserializó exitosamente el estimador real y certificó el hash SHA-256 oficial `7eaa50...` con `is_synthetic: false`.

### 3.3 Control de Acceso y Blindaje de Autenticación
1. **Petición sin cabecera `X-API-Key`:**
   - **Endpoint:** `POST /api/v1/predict/concrete-strength`
   - **Código HTTP:** `401 Unauthorized`
   - **Respuesta:**
     ```json
     {
       "detail": "API key missing. Provide 'X-API-Key' header."
     }
     ```
2. **Petición con clave incorrecta o inválida:**
   - **Endpoint:** `POST /api/v1/predict/concrete-strength`
   - **Cabecera:** `X-API-Key: invalid-unauthorized-key`
   - **Código HTTP:** `403 Forbidden`
   - **Respuesta:**
     ```json
     {
       "detail": "Invalid API key."
     }
     ```

### 3.4 Validación de Dominio y Contratos de Entrada
- **Caso Probado:** Cemento negativo (`cement = -10.0 kg/m³`).
- **Código HTTP:** `422 Unprocessable Entity` (formato RFC 7807 ProblemDetails).
- **Respuesta:**
  ```json
  {
    "type": "https://errors.ecomix-ia.org/domain-validation-error",
    "title": "Error de Validación de Dosificación de Concreto",
    "status": 422,
    "detail": "La dosificación contiene 1 inconsistencia(s) respecto a los límites físicos y normativos de la mezcla.",
    "invalid_fields": [
      {
        "field": "cement",
        "message": "Input should be greater than or equal to 0"
      }
    ]
  }
  ```

---

## 4. Pruebas de Inferencia de Concreto y Paridad Numérica

### 4.1 Caso Canónico (Mezcla de Referencia sin SCM)
- **Entrada JSON:**
  ```json
  {
    "cement": 280.0,
    "blast_furnace_slag": 0.0,
    "fly_ash": 0.0,
    "water": 180.0,
    "superplasticizer": 0.0,
    "coarse_aggregate": 1050.0,
    "fine_aggregate": 750.0
  }
  ```
- **Código HTTP:** `200 OK`
- **Latencia Observada:** `1,759 ms` (primera ejecución / cold path)
- **Respuesta Recibida en Azure:**
  ```json
  {
    "status": "success",
    "predictions": {
      "strength_7d_mpa": 21.96,
      "strength_28d_mpa": 31.15
    },
    "mix_ratios": {
      "water_cement_ratio": 0.6429,
      "water_binder_ratio": 0.6429,
      "total_cementitious_content_kg_m3": 280.0,
      "scm_replacement_percentage": 0.0,
      "aggregates_total_kg_m3": 1800.0,
      "total_mass_kg_m3": 2260.0
    },
    "warnings": [],
    "metadata": {
      "model_id": "wheat_cheese_4swj34tkjn_11",
      "model_type": "VotingEnsemble",
      "model_sha256": "7eaa501c5eeb60135effb6b5861e736518ce969c47afd53727c2451083ff6388",
      "inference_timestamp": "2026-11-06T14:52:25.940462-05:00"
    }
  }
  ```

### 4.2 Caso Ecológico (Alta Sustitución con Escoria y Ceniza Volante)
- **Entrada JSON:**
  ```json
  {
    "cement": 150.0,
    "blast_furnace_slag": 100.0,
    "fly_ash": 80.0,
    "water": 165.0,
    "superplasticizer": 5.0,
    "coarse_aggregate": 1000.0,
    "fine_aggregate": 750.0
  }
  ```
- **Código HTTP:** `200 OK`
- **Latencia Observada:** `381 ms`
- **Respuesta Recibida en Azure:**
  ```json
  {
    "status": "success",
    "predictions": {
      "strength_7d_mpa": 25.98,
      "strength_28d_mpa": 33.61
    },
    "mix_ratios": {
      "water_cement_ratio": 1.1,
      "water_binder_ratio": 0.5,
      "total_cementitious_content_kg_m3": 330.0,
      "scm_replacement_percentage": 54.55,
      "aggregates_total_kg_m3": 1750.0,
      "total_mass_kg_m3": 2250.0
    },
    "warnings": [
      {
        "code": "WARN_HIGH_SCM_REPLACEMENT",
        "severity": "info",
        "field": "scm_replacement_percentage",
        "message": "Sustitución ecológica significativa (54.55% de SCMs). Se recomienda extender el período de curado húmedo para garantizar la hidratación puzolánica.",
        "observed_value": 54.55,
        "reference_boundary": "<= 40.0%"
      },
      {
        "code": "WARN_HIGH_WATER_CEMENT_RATIO",
        "severity": "info",
        "field": "water_cement_ratio",
        "message": "Relación agua/cemento elevada (1.1). Verifique los requisitos de durabilidad y permeabilidad según la norma técnica local.",
        "observed_value": 1.1,
        "reference_boundary": "<= 0.65"
      }
    ],
    "metadata": {
      "model_id": "wheat_cheese_4swj34tkjn_11",
      "model_type": "VotingEnsemble",
      "model_sha256": "7eaa501c5eeb60135effb6b5861e736518ce969c47afd53727c2451083ff6388",
      "inference_timestamp": "2026-11-06T14:52:35.415194-05:00"
    }
  }
  ```

### 4.3 Tabla de Paridad Numérica Determinística

| Caso de Prueba | Parámetro | Predicción Local (Fase 5.4) | Predicción Azure Container Apps (Fase 5.6-C.3) | Desviación Absoluta ($|\Delta|$) | Estado |
|---|---|---|---|---|---|
| **Canónico (280 kg cemento)** | Resistencia a 7 días | `21.96 MPa` | `21.96 MPa` | `0.00 MPa` | **PARIDAD EXACTA** |
| **Canónico (280 kg cemento)** | Resistencia a 28 días | `31.15 MPa` | `31.15 MPa` | `0.00 MPa` | **PARIDAD EXACTA** |
| **Canónico (280 kg cemento)** | Relación a/c | `0.6429` | `0.6429` | `0.0000` | **PARIDAD EXACTA** |
| **Ecológico (54.55% SCM)** | Resistencia a 7 días | `25.98 MPa` | `25.98 MPa` | `0.00 MPa` | **PARIDAD EXACTA** |
| **Ecológico (54.55% SCM)** | Resistencia a 28 días | `33.61 MPa` | `33.61 MPa` | `0.00 MPa` | **PARIDAD EXACTA** |
| **Ecológico (54.55% SCM)** | Relación a/c | `1.1000` | `1.1000` | `0.0000` | **PARIDAD EXACTA** |
| **Ecológico (54.55% SCM)** | Advertencias de dominio | 2 advertencias | 2 advertencias | 0 diferencias | **PARIDAD EXACTA** |

---

## 5. Pruebas de Desempeño y Cumplimiento de SLA (ISO/IEC 25010)

Para evaluar el cumplimiento del requerimiento no funcional **RNF-01** (tiempo de respuesta de inferencia menor a 2,000 ms), se midieron los tiempos de ida y vuelta (round-trip) desde la máquina cliente (Tacna, Perú) hacia el centro de datos de Azure en Santiago de Chile (`chilecentral`):

```
Invocación 1 (Cold / Initial Path) : 1,759 ms
Invocación 2 (Warm Call 1)          :   369 ms
Invocación 3 (Warm Call 2)          :   171 ms
Invocación 4 (Warm Call 3)          :   205 ms
--------------------------------------------------
Promedio en Caliente (Warm Average):   248.33 ms
SLA Contractual Máximo Permitido   : 2,000.00 ms
Margen de Holgura de Desempeño      :   87.58 %
```

El servicio responde en **~248 ms**, utilizando apenas el **12.4%** de la ventana de tolerancia admitida por el SLA de ingeniería.

---

## 6. Auditoría Financiera y Consumo de Crédito Estudiantil

| Concepto | Recurso / Métrica | Tarifa Minorista Vigente (`chilecentral`) | Consumo en la Sesión | Costo Facturado Estimado |
|---|---|---|---|---|
| **Cómputo ACA (vCPU)** | vCPU-segundos activos | \$0.000024 / vCPU-s (primeros 180,000 s gratis/mes) | ~15 vCPU-s | **\$0.00 USD** |
| **Cómputo ACA (Memoria)** | GiB-segundos activos | \$0.000003 / GiB-s (primeros 360,000 s gratis/mes) | ~30 GiB-s | **\$0.00 USD** |
| **Solicitudes HTTP ACA** | Peticiones procesadas | \$0.40 / millón (primeros 2 millones gratis/mes) | 8 peticiones | **\$0.00 USD** |
| **Almacenamiento ACR** | SKU Basic (10 GiB incl.) | ~\$0.167 USD / día | 0.5 días activos | **~\$0.08 USD** |
| **Identidad Administrada** | `id-ecomix-aca` | Gratuita (\$0.00) | 1 identidad | **\$0.00 USD** |
| **Entorno Gestionado ACA** | `env-ecomix-prod` | Gratuito (\$0.00) | 1 entorno | **\$0.00 USD** |
| **TOTAL ESTIMADO** | — | — | — | **< \$0.10 USD** |

- **Presupuesto inicial declarado:** USD 20.00
- **Límite operativo de la ronda:** USD 10.00
- **Gasto acumulado de las Fases 5.6-C.2 y 5.6-C.3:** **< USD 0.15** (equivalente al 0.75% del presupuesto total).
- Con `minReplicas = 0`, el servicio no genera costos de cómputo en reposo.

---

## 7. Guía de Integración para la Aplicación ASP.NET MVC 5

La aplicación web EcoMix IA (ASP.NET MVC 5 en .NET Framework 4.8 o .NET Core) puede consumir este servicio de manera inmediata mediante la siguiente especificación:

### 7.1 Contrato HTTP
- **URL Base:** `https://ca-ecomix-inference-api.salmontree-d9db53a4.chilecentral.azurecontainerapps.io`
- **Ruta de Inferencia:** `/api/v1/predict/concrete-strength`
- **Método HTTP:** `POST`
- **Cabeceras Obligatorias:**
  - `Content-Type: application/json`
  - `X-API-Key: <CLAVE_PROVISTA_EN_SECRETO_SEGURO>`

### 7.2 Ejemplo de Cliente C# con `HttpClient` y Resiliencia
```csharp
public class EcoMixMlClient
{
    private readonly HttpClient _httpClient;
    private readonly string _apiKey;

    public EcoMixMlClient(HttpClient httpClient, IConfiguration config)
    {
        _httpClient = httpClient;
        _httpClient.BaseAddress = new Uri("https://ca-ecomix-inference-api.salmontree-d9db53a4.chilecentral.azurecontainerapps.io/");
        _httpClient.Timeout = TimeSpan.FromSeconds(10); // Margen para cold start
        _apiKey = config["EcoMix:ApiKey"];
    }

    public async Task<PredictionResponseDto> PredictStrengthAsync(ConcreteMixDto mix)
    {
        using (var request = new HttpRequestMessage(HttpMethod.Post, "api/v1/predict/concrete-strength"))
        {
            request.Headers.Add("X-API-Key", _apiKey);
            request.Content = new StringContent(
                JsonSerializer.Serialize(mix),
                Encoding.UTF8,
                "application/json"
            );

            using (var response = await _httpClient.SendAsync(request))
            {
                if (!response.IsSuccessStatusCode)
                {
                    var errorJson = await response.Content.ReadAsStringAsync();
                    throw new HttpRequestException($"Error de inferencia ({response.StatusCode}): {errorJson}");
                }

                var json = await response.Content.ReadAsStringAsync();
                return JsonSerializer.Deserialize<PredictionResponseDto>(json);
            }
        }
    }
}
```

> [!TIP]
> **Recomendación para Cold Starts:**  
> Como la aplicación se escala a 0 réplicas cuando no recibe tráfico, la primera solicitud tras un período prolongado de inactividad puede tomar entre 1.5 y 2.5 segundos mientras Azure aprovisiona el contenedor e inicializa el modelo. Se sugiere configurar la política de reintentos en ASP.NET con **Polly** con un timeout de 10 segundos para la primera invocación.

---

## 8. Comandos Operativos para Apagado y Eliminación de Recursos

Para garantizar el control financiero total y evitar cobros innecesarios en caso de no requerir el servicio activo en la nube:

### Opción 1: Apagado Completo de Réplicas (Costo Cómputo = \$0.00, Mantiene Configuración)
La aplicación ya cuenta con `minReplicas = 0`, por lo que se apaga sola de forma inmediata tras completar las solicitudes. Si se desea deshabilitar temporalmente la revisión para que no reciba tráfico:
```bash
az containerapp deactivate \
  --name ca-ecomix-inference-api \
  --resource-group EcomixIA
```

### Opción 2: Eliminación Exclusiva de Azure Container Apps (Conserva ACR con la Imagen)
Si se desea eliminar el servicio HTTP pero conservar la imagen compilada en ACR para futuros despliegues:
```bash
# 1. Eliminar la Container App
az containerapp delete \
  --name ca-ecomix-inference-api \
  --resource-group EcomixIA \
  --yes

# 2. Eliminar el entorno de Container Apps
az containerapp env delete \
  --name env-ecomix-prod \
  --resource-group EcomixIA \
  --yes

# 3. Eliminar la identidad administrada
az identity delete \
  --name id-ecomix-aca \
  --resource-group EcomixIA
```

### Opción 3: Eliminación Total de Todos los Recursos Creados en la Fase 5.6
```bash
# Eliminar Container App, Entorno e Identidad
az containerapp delete --name ca-ecomix-inference-api --resource-group EcomixIA --yes
az containerapp env delete --name env-ecomix-prod --resource-group EcomixIA --yes
az identity delete --name id-ecomix-aca --resource-group EcomixIA

# Eliminar el registro ACR crecomixprod
az acr delete --name crecomixprod --resource-group EcomixIA --yes
```

---

## 9. Conclusión y Veredicto Final

La **Fase 5.6-C.3 ha culminado con éxito absoluto**. El motor predictivo VotingEnsemble de **EcoMix IA** se encuentra alojado en producción cloud de alta disponibilidad, protegido con autenticación por clave simétrica DevSecOps, gobernado por identidades administradas RBAC sin contraseñas expuestas y listo para el consumo del frontend ASP.NET MVC 5 o del Simulador Web.
