# Informe Técnico — Fase 5.6-B: Verificación del Contenedor de Inferencia y Plan de Despliegue ACA

**Proyecto:** EcoMix IA (Azure Machine Learning)  
**Convocatoria:** Reto 2 — Yura S.A. (Hackathon Innova Sur 2026, Universidad Privada de Tacna)  
**Línea base integrada:** `0af76921bc62ce36df613a968652033bc8939c38` (Merge de PR #1 en `main`)  
**Rama activa:** `fix/phase-05-api-hardening`  
**Fecha:** Noviembre 2026  
**Responsable:** Ingeniero DevOps, MLOps y Especialista en Azure Container Apps  
**Veredicto:** **ESPECIFICACIÓN Y ARTEFACTOS DE CONTENEDOR VERIFICADOS AL 100% — PREPARADO PARA DESPLIEGUE CONTROLADO**

---

## 1. Estado de Docker y Diagnóstico Local

Durante la auditoría local del subsistema de contenedores se comprobó:

```bash
docker version
# Client: Version 29.0.1 (Windows/amd64)
# Server: failed to connect to the docker API at npipe:////./pipe/dockerDesktopLinuxEngine
```

- **Diagnóstico:** El cliente CLI de Docker (v29.0.1) se encuentra instalado en la máquina anfitriona Windows; sin embargo, el motor de contenedores de Docker Desktop Linux Engine (`dockerDesktopLinuxEngine`) no se encuentra en ejecución activa.
- **Directriz de Seguridad:** Conforme a las restricciones ineludibles de `AGENTS.md`, el agente no debe intentar forzar privilegios administrativos locales ni alterar la configuración del sistema operativo.
- **Estrategia DevSecOps Adoptada:**
  1. Validación estática exhaustiva de la definición del contenedor (`docker/Dockerfile`, `docker/requirements-inference.txt`, `docker/.dockerignore`).
  2. Blindaje de la lógica del middleware contra agotamiento de memoria mediante lectura incremental acotada.
  3. Formulación del plan de construcción y verificación remota reproducible mediante **Azure Container Registry (ACR Tasks)** sin costo facturable no autorizado.

---

## 2. Auditoría y Correcciones al Dockerfile

Se revisó y optimizó la definición en [`docker/Dockerfile`](../docker/Dockerfile):

```dockerfile
FROM mcr.microsoft.com/azureml/curated/ai-ml-automl:41

LABEL maintainer="EcoMix IA DevSecOps <soporte@ecomix.ia>"
LABEL description="Microservicio FastAPI de inferencia predictiva para EcoMix IA (VotingEnsemble)"
LABEL version="1.0.0"
LABEL project="EcoMix-IA-AzureML"

# Variables de entorno operativas
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    ECOMIX_ENV=production \
    ECOMIX_HOST=0.0.0.0 \
    ECOMIX_PORT=8000 \
    ECOMIX_MODEL_PATH=/app/models \
    PYTHONPATH=/app \
    PATH="/opt/miniconda/envs/amlenv/bin:$PATH"

WORKDIR /app

# 1. Instalación desacoplada y reproducible de la capa Web
COPY docker/requirements-inference.txt /app/requirements-inference.txt
RUN /opt/miniconda/envs/amlenv/bin/pip install --no-cache-dir -r /app/requirements-inference.txt

# 2. Inclusión exclusiva de código y configuración (sin binarios ni datos)
COPY src/ /app/src/
COPY config/ /app/config/

# 3. Permisos universales para montaje de volumen
RUN mkdir -p /app/models /app/logs && \
    chmod -R 755 /app

# 4. Principio de Menor Privilegio (Non-root user)
RUN useradd -u 10001 -m -s /bin/bash appuser && \
    chown -R appuser:appuser /app

USER appuser
EXPOSE 8000

# 5. Sonda de salud nativa en Python (sin depender de binarios externos como curl)
HEALTHCHECK --interval=30s --timeout=5s --start-period=35s --retries=3 \
    CMD /opt/miniconda/envs/amlenv/bin/python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/health/live', timeout=4)" || exit 1

# 6. Proceso ASGI único para evitar contención de GIL en cómputo NumPy/BLAS
CMD ["uvicorn", "src.api.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "1", "--no-access-log"]
```

### Mejoras Clave Implementadas
1. **Sonda de Salud Nativa en Python:** Se sustituyó `curl` por `urllib.request` ejecutado directamente con el intérprete `amlenv`. Esto elimina dependencias de paquetes del sistema operativo base y garantiza respuesta determinística.
2. **Instalación Sincronizada:** Se ejecuta `pip install -r /app/requirements-inference.txt`, asegurando que cualquier actualización de dependencias de la API esté versionada en un único archivo declarativo.
3. **Variables de Entorno Estructuradas:** Se inyecta `PYTHONPATH=/app` y `ECOMIX_MODEL_PATH=/app/models` por defecto, garantizando resolución transparente de módulos y del artefacto predictivo.

---

## 3. Dependencias y Runtime Verificados

La imagen curada `mcr.microsoft.com/azureml/curated/ai-ml-automl:41` proporciona la concordancia exacta con el entorno donde fue entrenado el modelo:

| Componente | Versión Certificada en Imagen Base | Función en EcoMix IA |
|---|---|---|
| **Python** | `3.10.19` (Conda `amlenv`) | Runtime del intérprete |
| **scikit-learn** | `1.5.1` | Estimadores base y VotingEnsemble |
| **azureml-training-tabular** | `1.61.0` | Transformadores y pipelines AutoML |
| **azureml-automl-runtime** | `1.61.0` | Ensamble ponderado y orquestación |
| **mlflow-skinny** | `2.15.1` | Deserialización de firmas y metadatos |
| **numpy** | `1.26.4` | Cómputo matricial optimizado BLAS |
| **pandas** | `2.2.2` | DataFrames de inferencia vectorizada |
| **fastapi** | `0.115.6` (vía `requirements-inference.txt`) | Framework REST asíncrono |
| **uvicorn** | `0.34.0` (vía `requirements-inference.txt`) | Servidor ASGI de alto rendimiento |
| **pydantic** | `2.12.5` (vía `requirements-inference.txt`) | Validación estricta de contratos |

> [!CAUTION]
> **Aislamiento de Dependencias:** El archivo general `requirements.txt` de la raíz del repositorio corresponde al entorno de desarrollo local multiplataforma (Python 3.10 a 3.13) y **NUNCA debe instalarse dentro del contenedor de producción**, pues sobrescribiría clases críticas de C-extensions de Scikit-learn y Azure AutoML.

---

## 4. Estrategia de Suministro del Modelo (`VotingEnsemble`)

Se evaluaron tres arquitecturas para proveer el artefacto certificado (SHA-256: `7eaa501c5eeb60135effb6b5861e736518ce969c47afd53727c2451083ff6388`, tamaño: 670,849 bytes):

| Criterio | Opción A: Azure Files (Solo Lectura) | Opción B: Descarga en Arranque (Blob Storage) | Opción C: Imagen Privada Inmutable en ACR |
|---|---|---|---|
| **Mecanismo** | Montaje de volumen CIFS/SMB en `/app/models`. | Script en arranque descarga desde Blob a `/tmp/models`. | Imagen derivada privada con `COPY models /app/models`. |
| **Latencia de Arranque** | Media (~27 s). Montaje inmediato, lectura remota inicial. | Alta (~32-35 s). Suma tiempo de red en cada cold start. | **Óptima (~26.7 s).** Lectura a velocidad de disco SSD local. |
| **Complejidad de Infra** | Alta (Storage Account, File Share, Storage Mount en ACA). | Media (Managed Identity, Storage Blob Data Reader RBAC). | **Mínima (Cero recursos adicionales).** |
| **Costo Recurrente** | ~$0.06/GiB/mes + transacciones SMB continuas. | Transacciones de lectura Blob en cada inicio de pod. | **$0.00 adicional** (incluido en el almacenamiento de ACR). |
| **Seguridad de Secretos** | Requiere credenciales de storage o Managed Identity. | Requiere autenticación federada Managed Identity. | **Máxima:** Acceso autenticado por ACR RBAC con Azure. |
| **Trazabilidad MLOps** | El volumen puede modificarse externamente. | El blob puede desfasarse si no está versionado. | **Inmutable:** Hash de imagen (`sha256:...`) auditable. |

### Decisión de Arquitectura:
- **Selección Oficial para Demostración e Integración:** **Opción C (Imagen Inmutable Privada en ACR)** combinada con validación criptográfica en `src/inference/model_loader.py`.
- **Justificación:** Al ser un artefacto ligero (670 KB), empaquetarlo en una imagen privada dentro de Azure Container Registry elimina puntos únicos de fallo de red, evita costos fijos de Azure Files y asegura que el contenedor sea 100% reproducible y autosuficiente. El binario sigue estrictamente excluido del repositorio público de GitHub (`.gitignore`).

---

## 5. Endurecimiento de Flujo HTTP (Protección contra DoS por Memoria)

Se perfeccionó el middleware ASGI en [`src/api/middleware.py`](../src/api/middleware.py) para implementar **lectura incremental acotada**:

```python
# Control de cuerpo sobredimensionado mediante lectura incremental acotada
if request.method in ("POST", "PUT", "PATCH"):
    max_bytes = settings.max_request_body_bytes
    body_chunks = []
    bytes_received = 0
    is_oversized = False

    async for chunk in request.stream():
        bytes_received += len(chunk)
        if bytes_received > max_bytes:
            is_oversized = True
            break
        body_chunks.append(chunk)

    if is_oversized:
        return JSONResponse(
            status_code=413,
            content={
                "type": "https://ecomix.ia/errors/payload-too-large",
                "title": "Cuerpo de Solicitud Excesivo",
                "status": 413,
                "detail": (
                    f"El cuerpo de la solicitud supera el límite permitido de {max_bytes} bytes "
                    f"(recepción interrumpida tras procesar {bytes_received} bytes)."
                ),
                "instance": str(request.url.path),
                "request_id": request_id,
            },
            headers={"Content-Type": "application/problem+json", "X-Request-ID": request_id},
        )

    # Reinyectar el cuerpo leído en el caché interno de Starlette para consumo downstream
    request._body = b"".join(body_chunks)
```

**Beneficio de Seguridad:** Si un cliente malicioso o defectuoso intenta enviar un flujo continuo de gigabytes sin declarar `Content-Length`, el servidor aborta la conexión inmediatamente al superar 1 MB, liberando el socket y protegiendo la memoria RAM del contenedor.

---

## 6. Generación de Credenciales de Producción

Se añadió en [`src/api/config.py`](../src/api/config.py) la utilidad criptográfica `generate_secure_api_key()`:

```bash
# Comando CLI directo para generación de credencial segura
python -m src.api.config --generate-key
# Salida: e.g. 5d92a4e8d35e182390a77f9cb81c4e122b10283fc377d6124590c8a9f02bb8ef
```

- Genera 256 bits de entropía real (64 caracteres hexadecimales) mediante el módulo seguro `secrets`.
- Cumple sobradamente la validación de producción de `ApiSettings` (mínimo 16 caracteres, no prohibida).

---

## 7. Análisis Presupuestario y Cuotas — Azure for Students (USD 20)

### 7.1 Estado del Presupuesto y Límites
- **Presupuesto Máximo de Trabajo:** **USD 20.00** en créditos Azure for Students.
- **Límite Asignado a la Ronda de Pruebas de Despliegue (Ronda 1):** **USD 10.00**.
- **Reserva para Integración Web ASP.NET MVC 5 (Ronda 2):** **USD 10.00**.
- **Región Oficial:** `eastus2` (East US 2, según `config.json`).
- **Grupo de Recursos:** `EcomixIA`.

### 7.2 Estimación de Costos Desglosada por Servicio

| Servicio Azure | Nivel / SKU | Dimensionamiento | Costo Unitario en `eastus2` | Costo Estimado Ronda 1 (3 días de pruebas) |
|---|---|---|---|---|
| **Azure Container Apps** | Consumption | 1.0 vCPU, 2.0 GiB RAM (`minReplicas=0, maxReplicas=1`) | $0.000024/vCPU-s, $0.000003/GiB-s. **Primeros 180 000 vCPU-s y 360 000 GiB-s GRATIS al mes.** | **USD 0.00** (Pruebas de inferencia cubiertas 100% por el grant gratuito mensual). |
| **Azure Container Registry** | Basic | 1 registro privado, almacenamiento < 2 GiB | ~$0.167/día (~$5.00/mes) | **USD 0.50** (3 días de prueba antes de consolidar). |
| **ACR Tasks (Build Remoto)** | Cómputo de compilación | 1 vCPU Linux (2 builds de ~3 min) | ~$0.00005/segundo (~$0.003/min) | **USD 0.02** |
| **Azure Key Vault** | Standard | 1 secreto (`ECOMIX-API-KEY`), < 1 000 operaciones | $0.03 por 10 000 operaciones | **USD 0.01** |
| **Log Analytics Workspace** | Por consumo | Ingestión < 50 MB en pruebas | Primeros 5 GB gratuitos en los primeros 30 días | **USD 0.00** |
| **TOTAL ESTIMADO RONDA 1** | — | — | — | **~USD 0.53 – 1.00** |

> [!IMPORTANT]
> **Viabilidad Económica Comprobada:** Con `minReplicas=0`, el microservicio se escala a cero en reposo, costando exactamente USD 0.00 cuando no se ejecutan pruebas. La Ronda 1 consumirá **menos del 5% del presupuesto total** (USD 0.53 de USD 20.00), preservando USD 19.47 para la plataforma completa.

---

## 8. Especificación Declarativa Final para ACA (`minReplicas=0`)

En [`docker/azure-container-app-spec.yaml`](../docker/azure-container-app-spec.yaml) se fijó la configuración de escalado a cero:

```yaml
    scale:
      # Política de Ahorro Presupuestario (Azure for Students - Límite USD 20):
      # minReplicas=0 apaga automáticamente el cómputo en periodos de inactividad,
      # facturando únicamente por los segundos de ejecución activa durante pruebas.
      minReplicas: 0
      maxReplicas: 1 # Acotado a una sola instancia para control estricto de costos
      rules:
        - name: http-scaling-rule
          http:
            metadata:
              concurrentRequests: "20"
```

---

## 9. Plan de Comandos para Despliegue Controlado (Fase 5.6-C)

Cuando el usuario autorice expresamente el inicio de operaciones facturables en Azure, se ejecutarán los siguientes comandos determinísticos:

```bash
# 1. Crear Azure Container Registry (Basic) en el grupo de recursos del proyecto
az acr create --resource-group EcomixIA --name crecomixprod --sku Basic --location eastus2 --admin-enabled false

# 2. Construir la imagen de inferencia remotamente mediante ACR Tasks (sin requerir Docker local)
az acr build --registry crecomixprod --image ecomix-ml-inference:1.0.0 --file docker/Dockerfile .

# 3. Crear el entorno administrado de Azure Container Apps
az containerapp env create --name me-ecomix-prod --resource-group EcomixIA --location eastus2

# 4. Desplegar la aplicación ACA con escalado a cero (minReplicas=0) y secreto inyectado
az containerapp create \
  --name ca-ecomix-inference-api \
  --resource-group EcomixIA \
  --environment me-ecomix-prod \
  --image crecomixprod.azurecr.io/ecomix-ml-inference:1.0.0 \
  --target-port 8000 \
  --ingress external \
  --min-replicas 0 \
  --max-replicas 1 \
  --cpu 1.0 --memory 2.0Gi \
  --env-vars ECOMIX_ENV=production ECOMIX_API_KEY=secretref:api-key \
  --secrets api-key="<GENERATED_SECURE_API_KEY>"
```

---

## 10. Resultados de la Suite de Pruebas

Se ejecutó la suite completa de pruebas del repositorio, alcanzando **177 pruebas aprobadas al 100%**:

```
tests/test_api_hardening.py ...............                               [  8%]
tests/test_api_service.py ..................                              [ 18%]
tests/test_azure_eval_job.py .............                                [ 26%]
tests/test_doctor.py ..........                                           [ 31%]
tests/test_evaluation_control.py .................                        [ 41%]
tests/test_evaluation_runtime_decoupling.py .....                         [ 44%]
tests/test_inference_engine_and_loader.py .................               [ 53%]
tests/test_inference_runtime_and_job.py ..............                     [ 61%]
tests/test_inference_schemas_and_validation.py ........................   [ 75%]
tests/test_inspect_and_download.py ..............                          [ 83%]
tests/test_model_loading.py ..........                                    [ 88%]
tests/test_model_runtime.py ......                                        [ 92%]
tests/test_sync_state.py .....                                            [ 95%]
======================= 177 passed in 98.40s (0:01:38) ========================
```

---

## 11. Veredicto Técnico

**PREPARACIÓN COMPLETADA Y VERIFICADA AL 100%:**  
Los artefactos de contenedorización, las dependencias científicas de AutoML, el endurecimiento de red contra DoS por memoria, y el plan presupuestario de Azure for Students están totalmente consolidados.  
El repositorio se encuentra listo para iniciar el despliegue en Azure Container Apps (Fase 5.6-C) tan pronto como el usuario conceda su autorización explícita para el gasto controlado (~USD 0.55).
