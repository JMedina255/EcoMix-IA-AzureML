# Informe de Construcción Local y Validación de Contenedor — Fase 5.6-C.1R

**Proyecto:** EcoMix IA (Azure Machine Learning)  
**Convocatoria:** Reto 2 — Yura S.A. (Hackathon Innova Sur 2026, Universidad Privada de Tacna)  
**Rama activa:** `fix/phase-05-api-hardening`  
**Fecha:** Noviembre 2026  
**Responsable:** Ingeniero DevSecOps y MLOps  
**Veredicto:** **CONSTRUCCIÓN LOCAL Y VALIDACIÓN DE INFERENCIA 100% EXITOSAS — ESTRATEGIA ACTUALIZADA PARA PUBLICACIÓN MEDIANTE `docker push`**

---

## 1. Justificación del Cambio de Estrategia: Restricción Oficial de ACR Tasks

La documentación oficial de Microsoft Azure establece una restricción temporal en el servicio **ACR Tasks** para suscripciones basadas en créditos promocionales o gratuitos, incluyendo **Azure for Students**:

> *«La ejecución de tareas de Azure Container Registry (ACR Tasks) se encuentra restringida temporalmente para suscripciones financiadas con créditos gratuitos (incluidas Azure for Students y Free Trial) para prevenir abusos de cómputo en la nube.»*  
> *(Fuente: Microsoft Learn — Container Registry Tasks Overview)*

En consecuencia, el comando `az acr build` fue formalmente **suspendido y descartado** del plan de despliegue para evitar bloqueos por cuotas y fallos de aprovisionamiento en la suscripción estudiantil.

---

## 2. Diagnóstico del Entorno Local y Recursos de Cómputo

Se auditó minuciosamente la infraestructura de la estación de trabajo local:

| Componente | Versión / Estado | Diagnóstico |
|---|---|---|
| **Sistema Operativo** | Windows 11 Pro (AMD64) | Totalmente compatible |
| **Subsistema WSL2** | Kernel 6.18.54.1-microsoft-standard-WSL2 | Distro `docker-desktop` versión 2 |
| **Docker Desktop** | Versión 4.53.0 (211793) | Operativo en espacio de usuario |
| **Docker Engine** | Versión 29.0.1 (API 1.52, Linux x86_64) | Daemon activo y respondiendo |
| **Espacio en Disco (C:)** | **144.76 GB libres** (de 529.80 GB) | Ampliamente suficiente para capas base |
| **Memoria RAM** | **15.85 GB totales**, **4.62 GB libres** | Adecuada para ejecución y deserialización |

---

## 3. Hallazgos Críticos en la Imagen Base Curada de Azure ML

Al descargar e inspeccionar la imagen oficial curada `mcr.microsoft.com/azureml/curated/ai-ml-automl:41`:

1. **Ruta Real del Entorno Científico:**  
   El entorno Conda predeterminado se localiza en `/azureml-envs/azureml-automl` (y no en `/opt/miniconda/envs/amlenv`).
2. **Paridad de Versiones Preinstaladas:**  
   Se comprobó que dicho entorno ya cuenta con las versiones idénticas requeridas por el modelo ganador:
   - **Python:** `3.10.19` (conda-forge)
   - **Scikit-learn:** `1.5.1`
   - **MLflow:** `2.15.1`
   - **AzureML Tabular:** `azureml-training-tabular 1.61.0`
   - **NumPy:** `1.23.5` (versión exacta requerida por `azureml-training-tabular`)
   - **Pydantic:** `2.12.5`
3. **Resolución de Conflicto en `requirements-inference.txt`:**  
   Se ajustó [`docker/requirements-inference.txt`](file:///c:/Users/Admin/Desktop/Proyectos/ML%20EcomixIA/docker/requirements-inference.txt) para instalar **exclusivamente** las librerías HTTP/ASGI de la API (`fastapi==0.115.6`, `uvicorn[standard]==0.34.0`, `starlette==0.41.3`, `httpx==0.28.1`), permitiendo que el gestor `pip` respete intacto el entorno científico sin conflictos con `numpy 1.23.5`.
4. **Actualización de Rutas en [`docker/Dockerfile`](file:///c:/Users/Admin/Desktop/Proyectos/ML%20EcomixIA/docker/Dockerfile):**  
   Se actualizaron `PATH`, la invocación de `pip` y la sonda `HEALTHCHECK` para apuntar a `/azureml-envs/azureml-automl/bin`.

---

## 4. Resultados de la Construcción Local de la Imagen

La imagen de contenedor se compiló localmente mediante:
```bash
docker build -t ecomix-ml-inference:1.0.0 -f docker/Dockerfile .
```

- **Tag local:** `ecomix-ml-inference:1.0.0`
- **Digest del manifiesto:** `sha256:592f9704c43b561d8bc98fb838b107141ca9696834efdb329114e3483e7c2972`
- **Tamaño sin comprimir en disco:** **8.02 GB** (la capa base de Microsoft ocupa 7.99 GB; el código, dependencias web y el modelo de 670 KB añaden únicamente ~30 MB).
- **Tamaño comprimido estimado en ACR:** **~2.2 GB** (con capas de MCR deduplicadas en la infraestructura troncal de Azure).
- **Compatibilidad con cuota de ACR Basic:** El SKU Basic incluye **10 GiB** de almacenamiento sin cargo, por lo que la imagen consumirá únicamente el ~22% del cupo asignado.

---

## 5. Validación Experimental de Inferencia y Endpoints HTTP

Se levantó el contenedor localmente vinculando el puerto `8008:8000` en modo `production` con una clave API segura:

```bash
docker run -d --name ecomix-container-test -p 8008:8000 \
  -e ECOMIX_ENV=production \
  -e ECOMIX_API_KEY=<TEST_KEY> \
  ecomix-ml-inference:1.0.0
```

### 5.1 Registro de Arranque y Deserialización en Memoria
Los logs del contenedor confirmaron la inicialización exitosa:
```text
INFO:     Started server process [1]
INFO:     Waiting for application startup.
2026-11-06 18:13:48,910 [INFO] ecomix.api: Inicializando servicio EcoMix IA (Entorno: production)...
2026-11-06 18:13:48,911 [INFO] ecomix.api: Cargando artefacto VotingEnsemble en memoria RAM...
2026-11-06 18:13:56,164 [INFO] ecomix.api: Modelo VotingEnsemble cargado exitosamente en memoria RAM.
INFO:     Application startup complete.
INFO:     Uvicorn running on http://0.0.0.0:8000
```

### 5.2 Resultados de Pruebas a Endpoints HTTP
1. **Sonda de Vida (`GET /health/live`):**  
   Retornó HTTP 200: `{"status": "alive", "service": "ecomix-ia-ml-api"}`.
2. **Sonda de Preparación (`GET /health/ready`):**  
   Retornó HTTP 200 confirmando:
   - `model_ready`: `true`
   - `model_id`: `wheat_cheese_4swj34tkjn_11`
   - `model_type`: `VotingEnsemble`
   - `model_sha256`: `7eaa501c5eeb60135effb6b5861e736518ce969c47afd53727c2451083ff6388`
   - `is_synthetic`: `false`
3. **Control de Seguridad y Autenticación en `POST /api/v1/predict/concrete-strength`:**  
   - Solicitud sin cabecera `X-API-Key`: Rechazada con **HTTP 401 Unauthorized**.
   - Solicitud con clave inválida: Rechazada con **HTTP 403 Forbidden**.
4. **Predicción Real con Mezcla Canónica:**  
   - Entrada: Cemento 280, Agua 180, Grava 1050, Arena 750 ($a/c = 0.64$).
   - Resultado: **Resistencia a 7 días: 21.96 MPa**, **Resistencia a 28 días: 31.15 MPa**.
5. **Predicción con Mezcla Ecológica de Alta Sustitución:**  
   - Entrada: Cemento 150, Escoria 100, Ceniza volante 80, Superplastificante 5 ($54.55\%$ SCM).
   - Resultado: **Resistencia a 7 días: 25.98 MPa**, **Resistencia a 28 días: 33.61 MPa**.
   - Advertencias de dominio retornadas: `WARN_HIGH_SCM_REPLACEMENT` y `WARN_HIGH_WATER_CEMENT_RATIO`.

El contenedor de prueba fue detenido y eliminado de inmediato (`docker stop` y `docker rm`), dejando el entorno local limpio.

---

## 6. Nueva Secuencia Propuesta de Publicación en ACR (Sin ACR Tasks)

Para la futura **Etapa 1**, la publicación se realizará directamente desde la estación local hacia el ACR privado mediante autenticación basada en tokens de Azure CLI:

```bash
# 1. Crear el registro privado con cuenta administradora deshabilitada
az acr create \
  --resource-group EcomixIA \
  --name crecomixprod \
  --sku Basic \
  --location eastus2 \
  --admin-enabled false

# 2. Iniciar sesión en el registro mediante el token AAD de Azure CLI (sin credenciales de admin)
az acr login --name crecomixprod

# 3. Etiquetar la imagen local ya compilada y probada
docker tag ecomix-ml-inference:1.0.0 crecomixprod.azurecr.io/ecomix-ml-inference:1.0.0

# 4. Subir la imagen al registro privado (Ingress gratuito en Azure)
docker push crecomixprod.azurecr.io/ecomix-ml-inference:1.0.0

# 5. Inspeccionar el repositorio en la nube
az acr repository show --name crecomixprod --image ecomix-ml-inference:1.0.0
az acr repository show-manifests --name crecomixprod --repository ecomix-ml-inference -o table
```

### Beneficios Técnicos y Presupuestarios:
- **Cero riesgo de fallo por cuota estudiantil:** Se evita el bloqueo de ACR Tasks.
- **Costo de cómputo en la nube = USD 0.00:** El build se realizó íntegramente con recursos locales.
- **Ingreso de datos gratuito:** Azure no factura por el tráfico entrante (*ingress*).
- **Costo remanente de Etapa 1:** Únicamente la tarifa fija de almacenamiento de ACR Basic (~$0.167 USD/día).

---

## 7. Actualización del Plan Presupuestario y Límites

- **Presupuesto Total Suscripción:** **USD 20.00**
- **Gasto Real Acumulado:** **USD 0.00**
- **Límite Ronda 1:** **USD 10.00**
- **Límite Objetivo Etapa 1 (1-2 días con ACR Basic):** **USD 0.50 – USD 2.00**

---

## 8. Estado de Detención

En estricto apego a las restricciones establecidas:
- **NO** se ejecutó `az acr create`.
- **NO** se ejecutó `docker push`.
- **NO** se desplegó ningún recurso en Azure Container Apps ni se actualizó a Pay-As-You-Go.
- La imagen probada `ecomix-ml-inference:1.0.0` reside **exclusivamente en el Docker local**.

El agente se detiene aquí a la espera de la confirmación expresa del usuario para autorizar la creación del ACR `crecomixprod` y el `docker push`.
