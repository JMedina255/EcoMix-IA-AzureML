# Informe de Correcciones Finales Previas a ACR — Fase 5.6-C.0R

**Proyecto:** EcoMix IA (Azure Machine Learning)  
**Convocatoria:** Reto 2 — Yura S.A. (Hackathon Innova Sur 2026, Universidad Privada de Tacna)  
**Línea base integrada:** `0af76921bc62ce36df613a968652033bc8939c38` (Merge de PR #1 en `main`)  
**Rama activa:** `fix/phase-05-api-hardening`  
**Fecha:** Noviembre 2026  
**Responsable:** Ingeniero DevSecOps y MLOps  
**Veredicto:** **CORRECCIONES IMPLEMENTADAS Y VERIFICADAS — EN ESPERA DE AUTORIZACIÓN EXPRESA DEL USUARIO PARA LA ETAPA 1**

---

## 1. Resumen de Riesgos Detectados y Correcciones Implementadas

En la auditoría preliminar de la Fase 5.6-C.0 se identificaron tres riesgos de seguridad, empaquetado y gobernanza que debían subsanarse antes de ejecutar cualquier comando en la suscripción de Azure:

| Riesgo Auditado | Causa Raíz | Corrección Implementada | Archivos Modificados |
|---|---|---|---|
| **1. Fuga de contexto Docker en `az acr build`** | El archivo `.dockerignore` existía únicamente dentro de `docker/`, por lo que un build desde la raíz (`.`) empaquetaría todo el workspace (incluyendo `.git/`, datasets y tests). | Se desplegó `.dockerignore` en la raíz del repositorio (`./.dockerignore`) y `docker/Dockerfile.dockerignore`. Se excluyen `.git/`, `data/`, `tests/`, `scripts/`, `reports/`, `docs/`, `.venv/` y secretos (`config.json`, `.env`), manteniendo exclusivamente el código fuente en `src/`, configuración declarativa y el artefacto MLflow oficial. | [`.dockerignore`](../.dockerignore), [`docker/Dockerfile.dockerignore`](../docker/Dockerfile.dockerignore), [`docker/.dockerignore`](../docker/.dockerignore) |
| **2. Desalineación de ruta en carga de modelo** | La especificación de Container Apps referenciaba una subcarpeta redundante (`/app/models/.../mlflow-model`), mientras que la directiva `COPY` aplana los archivos directamente en `/app/models/`. | Se unificó `ECOMIX_MODEL_PATH: /app/models` en [`docker/azure-container-app-spec.yaml`](../docker/azure-container-app-spec.yaml). El cargador [`ModelLoader`](../src/inference/model_loader.py) encuentra directamente `MLmodel` y `model.pkl` en `/app/models`, validando el hash SHA-256 oficial antes de deserializar. | [`docker/azure-container-app-spec.yaml`](../docker/azure-container-app-spec.yaml), [`docker/Dockerfile`](../docker/Dockerfile) |
| **3. Uso de cuenta de administración en ACR** | El comando original incluía `--admin-enabled true`, lo que habilita credenciales maestras estáticas y vulnera el principio de privilegio mínimo. | Se modificó el comando de aprovisionamiento a `--admin-enabled false`. Se diseñó la autenticación desacoplada mediante una **Identidad Administrada Asignada por el Usuario (`id-ecomix-aca`)** con rol RBAC `AcrPull`, verificando soporte completo y gratuito en Azure for Students. | [`docker/azure-container-app-spec.yaml`](../docker/azure-container-app-spec.yaml), [`docs/PHASE_5_6_C_0R_ACR_PREP_REPORT.md`](PHASE_5_6_C_0R_ACR_PREP_REPORT.md) |

---

## 2. Auditoría del Contexto Docker y del Artefacto Predictivo

### 2.1 Política de Exclusión Efectiva en ACR Tasks
Al ejecutar `az acr build --file docker/Dockerfile .`, Azure CLI empaqueta el directorio actual respetando el archivo `.dockerignore` del contexto raíz:
- **Exclusiones críticas:** `.git/`, `data/`, `tests/`, `scripts/`, `reports/`, `docs/`, `.gemini/`, `.venv/`, `config.json`, `.env*`.
- **Inclusiones estrictas:**
  * `docker/requirements-inference.txt`
  * `docker/Dockerfile`
  * `src/` (servicios de inferencia y validación)
  * `config/` (configuraciones declarativas no secretas)
  * `models/wheat_cheese_4swj34tkjn/.../mlflow-model/` (los 5 archivos del modelo certificado)
- **Tamaño de transferencia estimado:** $< 2.5\text{ MB}$, optimizando el tiempo de compresión y subida hacia ACR Tasks a menos de 5 segundos.

### 2.2 Integridad del Modelo Incorporado
El artefacto MLflow incorporado contiene:
- `model.pkl` (`670,849 bytes`, SHA-256 `7eaa501c5eeb60135effb6b5861e736518ce969c47afd53727c2451083ff6388`)
- `MLmodel` (especificación de sabores `sklearn` y `python_function`)
- `conda.yaml` (dependencias del entorno `amlenv`)
- `python_env.yaml` (versión del intérprete 3.10.19)
- `requirements.txt` (especificación pip)

El componente `ModelLoader` en `/app/models`:
1. Resuelve `/app/models/MLmodel` de manera determinista.
2. Verifica criptográficamente el hash SHA-256 de `/app/models/model.pkl` contra la constante inmutable del proyecto.
3. Deserializa el estimador en memoria bajo el entorno curado `amlenv` (Python 3.10.19, `azureml-training-tabular 1.61.0`, `scikit-learn 1.5.1`).

---

## 3. Diagnóstico de Permisos, Cuotas y Proveedores en Azure

Mediante consultas estrictamente de solo lectura a través de Azure CLI:

- **Suscripción:** `Azure for Students` (`72d4dc56-4d14-4a13-a9ca-9773ed0ba6eb`)
- **Estado:** `Enabled`
- **Crédito Remanente Disponible:** **USD 20.00**
- **Usuario Autenticado:** `joamedina@upt.pe`
- **Grupo de Recursos:** `EcomixIA` (Región: `eastus2`)

### 3.1 Estado de Proveedores de Recursos
| Proveedor de Recursos | Estado | Impacto para Despliegue |
|---|---|---|
| `Microsoft.ContainerRegistry` | **`Registered`** | Inmediatamente disponible para crear ACR y ejecutar ACR Tasks. |
| `Microsoft.ManagedIdentity` | **`Registered`** | Inmediatamente disponible para crear identidades administradas (USD 0.00). |
| `Microsoft.Authorization` | **`Registered`** | Inmediatamente disponible para asignar el rol `AcrPull` (USD 0.00). |
| `Microsoft.OperationalInsights` | **`Registered`** | Disponible para auditoría de logs. |
| `Microsoft.App` | **`NotRegistered`** | **Prerrequisito gratuito:** Debe ejecutarse `az provider register --namespace Microsoft.App` al inicio de la Etapa 2 antes de crear el entorno ACA. |

### 3.2 Cuotas de ACR Tasks en SKU Basic
- Cómputo Linux estándar: 2 vCPUs por tarea.
- Concurrencia: 1 tarea de compilación activa simultánea.
- Soporte en `eastus2`: Confirmado.
- Tarifa de compilación: $0.00005 USD/segundo (~$0.003 USD/minuto). Un build de 3 a 4 minutos tiene un costo estimado de ~$0.012 USD.

---

## 4. Separación Estricta de Fases y Declaración de Costos

> [!NOTE]
> **Descargo de responsabilidad de costos:**  
> Todas las cifras monetarias presentadas corresponden a **estimaciones de ingeniería** basadas en las tarifas minoristas públicas de Microsoft Azure en la región `East US 2` para suscripciones `Azure for Students`. No constituyen una garantía contractual de facturación. Los costos reales dependerán del tiempo de existencia de los recursos y de los segundos exactos de cómputo consumidos.

### Parámetros Presupuestarios:
- **Presupuesto Total Disponible en la Suscripción:** **USD 20.00**
- **Límite Máximo Autoimpuesto para la Ronda 1 Completa:** **USD 10.00**
- **Límite Objetivo para la Etapa 1 (ACR Build y Almacenamiento 1-2 días):** **USD 2.00**

---

### ETAPA 1: Creación de ACR y Construcción Remota (ACR Tasks)
*Objetivo:* Crear el registro privado con administrador deshabilitado y compilar la imagen inmutable que contiene el modelo oficial.

| Servicio a Crear | Región | SKU | Consumo Estimado | Costo Estimado | Cuota / Límite | Comando Exacto Propuesto (NO EJECUTADO) | Riesgo y Eliminación Inmediata |
|---|---|---|---|---|---|---|---|
| **Azure Container Registry (ACR)** | `eastus2` | `Basic` | 1 registro privado, almacenamiento ~2.5 GiB | **~$0.167 USD/día** (~$5.00/mes) | 10 GiB incluidos. Cuenta admin deshabilitada. | `az acr create --resource-group EcomixIA --name crecomixprod --sku Basic --location eastus2 --admin-enabled false` | **Costo fijo diario recurrente:** Factura mientras exista el recurso.<br>**Eliminación:** `az acr delete --name crecomixprod --resource-group EcomixIA --yes` |
| **ACR Tasks (Compilación remota)** | `eastus2` | Linux 2 vCPUs | 1 build de ~3 a 4 minutos | **~$0.012 USD** ($0.00005/s) | 1 tarea concurrente. | `az acr build --registry crecomixprod --image ecomix-ml-inference:1.0.0 --file docker/Dockerfile .` | **Costo único variable:** Factura solo durante la ejecución. No genera cargos posteriores. |

**Comandos de inspección de la Etapa 1 tras la compilación:**
```bash
az acr repository show --name crecomixprod --image ecomix-ml-inference:1.0.0
az acr repository show-manifests --name crecomixprod --repository ecomix-ml-inference -o table
```

---

### ETAPA 2: Configuración de Identidad y Despliegue en Azure Container Apps
*Objetivo:* Crear la identidad administrada con rol `AcrPull`, el entorno ACA y desplegar el microservicio FastAPI con política de escala a cero (`minReplicas=0`).

> [!IMPORTANT]
> Los comandos de la Etapa 2 **NO se ejecutarán en conjunto con la Etapa 1**. Requieren autorización expresa independiente tras verificar el éxito de la imagen compilada.

| Servicio a Crear | Región | SKU | Consumo Estimado | Costo Estimado | Cuota / Límite | Comando Exacto Propuesto (NO EJECUTADO) | Riesgo y Eliminación Inmediata |
|---|---|---|---|---|---|---|---|
| **Registro de Proveedor `Microsoft.App`** | Global | N/A | 1 registro | **USD 0.00** | Gratuito | `az provider register --namespace Microsoft.App` | Sin costo ni riesgo. |
| **Identidad Administrada (`id-ecomix-aca`)** | `eastus2` | UserAssigned | 1 identidad | **USD 0.00** | Gratuita | `az identity create --name id-ecomix-aca --resource-group EcomixIA --location eastus2` | Sin costo recurrente.<br>**Eliminación:** `az identity delete --name id-ecomix-aca --resource-group EcomixIA` |
| **Asignación de Rol `AcrPull`** | `eastus2` | RBAC | 1 asignación sobre el ACR | **USD 0.00** | Gratuita | `az role assignment create --assignee-object-id $PRINCIPAL_ID --assignee-principal-type ServicePrincipal --role AcrPull --scope $ACR_ID` | Sin costo.<br>Elimina la necesidad de credenciales de admin. |
| **Entorno Administrado ACA (`me-ecomix-prod`)** | `eastus2` | Consumption | 1 entorno | **USD 0.00** (en reposo) | Serverless | `az containerapp env create --name me-ecomix-prod --resource-group EcomixIA --location eastus2` | Se elimina con: `az containerapp env delete --name me-ecomix-prod --resource-group EcomixIA --yes` |
| **Container App (`ca-ecomix-inference-api`)** | `eastus2` | Consumption | 1.0 vCPU, 2.0 GiB RAM.<br>`minReplicas=0`, `maxReplicas=1`. | **USD 0.00** *(Cubierto por el Free Tier mensual de ACA: 180 000 vCPU-s gratis)* | 1 réplica máx. Apagado automático en inactividad. | `az containerapp create --name ca-ecomix-inference-api --resource-group EcomixIA --environment me-ecomix-prod --image crecomixprod.azurecr.io/ecomix-ml-inference:1.0.0 --target-port 8000 --ingress external --min-replicas 0 --max-replicas 1 --cpu 1.0 --memory 2.0Gi --user-assigned $IDENTITY_ID --registry-server crecomixprod.azurecr.io --registry-identity $IDENTITY_ID --env-vars ECOMIX_ENV=production ECOMIX_MODEL_PATH=/app/models ECOMIX_API_KEY=secretref:api-key --secrets api-key="<GENERATED_API_KEY>"` | **Costo en reposo: USD 0.00.**<br>Eliminación: `az containerapp delete --name ca-ecomix-inference-api --resource-group EcomixIA --yes` |

---

## 5. Verificación de la Suite de Pruebas Automatizadas

Se ejecutó la suite completa de pruebas unitarias y de integración previa a la formalización de este reporte:

- **Total de pruebas ejecutadas:** 177
- **Pruebas aprobadas:** 177 (100% de éxito)
- **Tiempo de ejecución:** 113.49 segundos
- **Estado de sincronización documental (`sync_state.py --check`):** Correcto e idéntico.

---

## 6. Declaración de Detención y Solicitud de Instrucciones

En estricto cumplimiento de las directrices del proyecto y las restricciones de gobernanza:

1. **NO se ha creado ningún recurso en Microsoft Azure.**
2. **NO se ha ejecutado `az acr create` ni `az acr build`.**
3. **NO se ha registrado `Microsoft.App` ni modificado el estado de la suscripción.**
4. **NO se han subido binarios ni secretos al control de versiones Git.**
5. El saldo de **USD 20.00** de la suscripción `Azure for Students` permanece **100% intacto**.

El agente se detiene aquí a la espera de la instrucción expresa del usuario para autorizar la **Etapa 1 (Creación de ACR y compilación remota)**.
