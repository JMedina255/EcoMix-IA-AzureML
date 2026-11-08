# 📖 Runbook Operativo de Inferencia Cloud — EcoMix IA

**Servicio:** API REST de Inferencia de Resistencia de Concreto (`ca-ecomix-inference-api`)  
**Plataforma Cloud:** Azure Container Apps (ACA) — Perfil Serverless Consumption  
**Región:** `chilecentral` (Chile Central)  
**Grupo de Recursos:** `EcomixIA`  
**Última Revisión:** Noviembre 2026 — Fase 6.4

---

## 🎯 1. Propósito y Alcance

Este manual operativo (Runbook) establece los procedimientos estándar de administración, monitoreo, mitigación de latencia, rotación de credenciales y resolución de incidencias para el microservicio de inferencia de **EcoMix IA** desplegado en Azure Container Apps.

Está dirigido al Arquitecto MLOps, Ingeniero de Soporte Cloud y a los desarrolladores de la plataforma cliente **ASP.NET MVC 5**.

---

## 🏗️ 2. Topología y Componentes de Producción

| Parámetro | Valor Certificado en Azure |
| :--- | :--- |
| **Nombre de la Container App** | `ca-ecomix-inference-api` |
| **Entorno Administrado** | `env-ecomix-prod` |
| **FQDN Externo HTTPS** | `https://ca-ecomix-inference-api.salmontree-d9db53a4.chilecentral.azurecontainerapps.io` |
| **Registro de Contenedores** | `crecomixprod.azurecr.io` (SKU Basic, sin usuario administrador) |
| **Imagen en Ejecución** | `crecomixprod.azurecr.io/ecomix-ml-inference:1.0.0` |
| **Digest OCI Inmutable** | `sha256:f50d37251430ad1e42d8df663554e0ea346a8dfffae8799393023d4afbb1d12a` |
| **Identidad Administrada** | `id-ecomix-aca` (User-Assigned Managed Identity) |
| **Rol RBAC sobre ACR** | `AcrPull` (autenticación nativa sin contraseñas estáticas) |
| **Dimensionamiento por Réplica** | 1.0 vCPU, 2.0 GiB RAM |
| **Política de Escalado** | `minReplicas = 0`, `maxReplicas = 1` (**Scale-to-Zero**) |
| **Hash SHA-256 del Modelo** | `7eaa501c5eeb60135effb6b5861e736518ce969c47afd53727c2451083ff6388` |

---

## ⚡ 3. Comportamiento de Escalado y Mitigación de Latencia

### 3.1 Política Scale-to-Zero (`minReplicas = 0`)
Para garantizar un **costo computacional nulo (USD 0.00)** dentro de la cuota mensual gratuita de Azure Container Apps (180,000 vCPU-segundos y 360,000 GiB-segundos), el microservicio escala automáticamente a 0 réplicas tras períodos de inactividad de solicitudes HTTP.

### 3.2 Realidad del Arranque en Frío (Cold Start)
* **Comportamiento observado:** Cuando llega una solicitud y no existen réplicas activas, Azure Container Apps aprovisiona el contenedor e inicia el proceso Uvicorn, el cual carga y valida el modelo `VotingEnsemble` de 670 KB.
* **Tiempo de Cold Start medido:** **~8.4 segundos**.
* **Latencia en Caliente (Warm):** **~248 ms** (ampliamente inferior al umbral contractual de 2,000 ms bajo ISO/IEC 25010).

### 3.3 Protocolo de Pre-Calentamiento (Warm-up)
Para demostraciones en vivo, evaluaciones de jurado o ventanas de alta demanda:
1. **Invocación previa (T - 3 minutos):** Realizar una petición GET a la sonda de preparación:
   ```bash
   curl -s -o /dev/null -w "%{http_code} en %{time_total}s\n" \
     https://ca-ecomix-inference-api.salmontree-d9db53a4.chilecentral.azurecontainerapps.io/health/ready
   ```
2. **Efecto:** La Container App levantará la réplica inmediatamente. Las solicitudes posteriores realizadas por la plataforma ASP.NET MVC 5 responderán en régimen caliente (~248 ms).
3. **Persistencia de la réplica:** ACA mantiene la réplica activa durante aproximadamente 3 a 5 minutos después de la última solicitud antes de retornar a cero.

---

## 🔒 4. Seguridad, Autenticación y Rotación de Credenciales

### 4.1 Mecanismo de Autenticación
* Todas las peticiones al endpoint de predicción `/api/v1/predict/concrete-strength` requieren la cabecera `X-API-Key`.
* La validación de la clave se realiza en tiempo constante mediante `secrets.compare_digest` para evitar ataques de temporización (*timing attacks*).

### 4.2 Procedimiento de Rotación de Claves (Zero-Downtime)
El microservicio soporta **múltiples claves activas** concurrentes a través de la variable de entorno `ECOMIX_API_KEY` (separadas por comas):
1. **Generar nueva clave de alta entropía:**
   ```python
   import secrets
   print(secrets.token_urlsafe(32))
   ```
2. **Actualizar el secreto en Azure Container Apps:**  
   Asignar ambas claves temporalmente: `ECOMIX_API_KEY="clave_antigua,nueva_clave_generada"`.
3. **Actualizar la clave en el cliente consumidor (ASP.NET MVC 5 `Web.config`).**
4. **Verificar el tráfico con la nueva clave.**
5. **Retirar la clave antigua:** Actualizar `ECOMIX_API_KEY="nueva_clave_generada"`.

---

## 🩺 5. Sondaje de Salud (Health Checks)

### 5.1 Sonda de Vida (`GET /health/live`)
* **Propósito:** Informa al orquestador que el servidor web Uvicorn responde.
* **Respuesta esperada:** HTTP 200 `{"status": "alive"}`.

### 5.2 Sonda de Preparación (`GET /health/ready`)
* **Propósito:** Informa que el modelo de Machine Learning está cargado en memoria, no es un estimador sintético y su hash criptográfico coincide con el modelo auditado.
* **Comprobación manual:**
  ```bash
  curl -s https://ca-ecomix-inference-api.salmontree-d9db53a4.chilecentral.azurecontainerapps.io/health/ready
  ```
* **Respuesta esperada:**
  ```json
  {
    "status": "ready",
    "model_loaded": true,
    "is_synthetic": false,
    "model_sha256": "7eaa501c5eeb60135effb6b5861e736518ce969c47afd53727c2451083ff6388",
    "algorithm": "RegressionPipeline"
  }
  ```

---

## 📊 6. Monitoreo y Diagnóstico de Telemetría

### 6.1 Consulta de Logs en Azure CLI
Para inspeccionar los logs en tiempo real sin ingresar al portal web:
```bash
az containerapp logs show \
  --name ca-ecomix-inference-api \
  --resource-group EcomixIA \
  --follow \
  --tail 50
```

### 6.2 Consulta en Azure Log Analytics (KQL)
En el Workspace de Log Analytics vinculado a `env-ecomix-prod`:
```kusto
ContainerAppConsoleLogs_CL
| where ContainerAppName_s == "ca-ecomix-inference-api"
| project TimeGenerated, Log_s
| order by TimeGenerated desc
| take 100
```

---

## 🚨 7. Matriz de Resolución de Incidencias (Troubleshooting)

| Código HTTP | Causa Raíz Probable | Diagnóstico Inmediato | Acción de Recuperación |
| :---: | :--- | :--- | :--- |
| **503 Service Unavailable** | El modelo aún no ha culminado la carga en memoria o falló la verificación de firma. | Consultar `GET /health/ready`. Revisar logs por `ModelNotReadyError`. | Esperar el ciclo de inicialización (~8.4 s). Si persiste, verificar permisos de lectura sobre `/app/models/`. |
| **401 Unauthorized** | Falta la cabecera `X-API-Key` en la solicitud HTTP. | Verificar cabeceras de la petición en el cliente C#. | Añadir `X-API-Key: <token>` en el `HttpRequestMessage`. |
| **403 Forbidden** | La clave enviada en `X-API-Key` no coincide con ninguna clave configurada en el secreto. | Verificar que no existan espacios en blanco o caracteres espurios en la clave. | Revisar `Web.config` y sincronizar con el secreto de ACA. |
| **413 Payload Too Large** | El cuerpo JSON excede el límite máximo configurado (`max_request_body_bytes = 65,536`). | Verificar si se está enviando un payload sobredimensionado o con adjuntos no autorizados. | Normalizar el payload al formato DTO estándar ($< 1\text{ KB}$). |
| **415 Unsupported Media Type** | La cabecera `Content-Type` no es `application/json`. | Comprobar cabecera enviada por HttpClient en ASP.NET. | Configurar `request.Content.Headers.ContentType = new MediaTypeHeaderValue("application/json")`. |
| **422 Unprocessable Entity** | Violación de reglas de dominio técnico (cemento negativo, relación $w/c > 1.2$, masa total anómala). | Leer el cuerpo RFC 7807 (`type: https://ecomix.ia/errors/domain-validation`). | Corregir los valores de dosificación en el formulario cliente. |
| **504 Gateway Timeout** | La petición coincidió con un cold start prolongado y el cliente HTTP tenía un timeout inferior a 10 s. | Verificar timeout en `HttpClient` de ASP.NET MVC 5. | Configurar `HttpClient.Timeout = TimeSpan.FromSeconds(30)` y política de reintento Polly. |

---

## 🔄 8. Procedimiento de Contingencia Offline (Docker Local)

Si los servicios de Azure presentaran una indisponibilidad general regional:
1. **Ejecutar la imagen localmente en el puerto 8000:**
   ```bash
   docker run -d --name ecomix-local -p 8000:80 \
     -e ECOMIX_ENVIRONMENT=production \
     -e ECOMIX_API_KEY="clave-contingencia-12345" \
     crecomixprod.azurecr.io/ecomix-ml-inference:1.0.0
   ```
2. **Reconfigurar la plataforma ASP.NET MVC 5:**  
   En `Web.config`, apuntar `EcoMixApiBaseUrl` a `http://localhost:8000/`.
3. **Validar:**
   ```bash
   curl -H "X-API-Key: clave-contingencia-12345" http://localhost:8000/health/ready
   ```
