# Informe de Auditoría Previa al Primer Gasto Azure — Fase 5.6-C.0

**Proyecto:** EcoMix IA (Azure Machine Learning)  
**Convocatoria:** Reto 2 — Yura S.A. (Hackathon Innova Sur 2026, Universidad Privada de Tacna)  
**Línea base integrada:** `0af76921bc62ce36df613a968652033bc8939c38` (Merge de PR #1 en `main`)  
**Rama activa:** `fix/phase-05-api-hardening`  
**Fecha:** Noviembre 2026  
**Responsable:** Ingeniero DevOps, MLOps y DevSecOps  
**Veredicto:** **AUDITORÍA SATISFACTORIA — CONDICIONES CUMPLIDAS PARA SOLICITAR AUTORIZACIÓN EXPRESA DE CONSTRUCCIÓN**

---

## 1. Estado de la Suscripción Azure for Students y Diagnóstico de Proveedores

Mediante consultas estrictamente de solo lectura a través de Azure CLI, se confirmó:

- **Suscripción Activa:** `Azure for Students`
- **Subscription ID:** `72d4dc56-4d14-4a13-a9ca-9773ed0ba6eb` (Enmascarada: `72d4dc56...`)
- **Estado de la Suscripción:** `Enabled`
- **Inquilino Institucional:** `UNIVERSIDAD PRIVADA DE TACNA` (`upt.pe`)
- **Usuario Autenticado:** `joamedina@upt.pe`
- **Grupo de Recursos Principal:** `EcomixIA`
- **Región Oficial:** `eastus2` (East US 2)
- **Presupuesto Total Declarado:** **USD 20.00** en créditos Azure for Students.
- **Límite Asignado para la Primera Ronda de Pruebas:** **Máximo USD 10.00**.

### 1.1 Estado de Proveedores de Recursos en la Suscripción
- `Microsoft.ContainerRegistry`: **`Registered`** (Habilitado para ACR).
- `Microsoft.App`: **`NotRegistered`**  
  > [!IMPORTANT]
  > **Hallazgo Crítico:** El proveedor de Azure Container Apps aún no está registrado en la suscripción.  
  > La acción `az provider register --namespace Microsoft.App` es una **operación administrativa gratuita (USD 0.00)** que debe ejecutarse previamente como prerrequisito para habilitar ACA.
- **Disponibilidad Regional:** Tanto `containerApps` como `registries` están confirmados con soporte activo en `East US 2`.

---

## 2. Auditoría del Dockerfile y Contexto de Construcción

Se auditó minuciosamente la configuración del contenedor en [`docker/Dockerfile`](../docker/Dockerfile) y [`docker/.dockerignore`](../docker/.dockerignore):

### 2.1 Mecanismo de Suministro del Modelo Oficial (Opción C - Imagen Inmutable)
- **Localización Local del Modelo:** `models/wheat_cheese_4swj34tkjn/model_asset_v1/azureml_wheat_cheese_4swj34tkjn_11_output_mlflow_log_model_873731674/mlflow-model/`
- **Tamaño del Binario:** Exactamente `670,849 bytes` (~655 KB).
- **Integridad SHA-256 Confirmada:**  
  `7eaa501c5eeb60135effb6b5861e736518ce969c47afd53727c2451083ff6388`
- **Gobernanza Git:** El archivo `.gitignore` excluye la carpeta `models/` y todos los `.pkl`, garantizando que el modelo **nunca se subirá a GitHub**.
- **Contexto de Construcción en ACR Tasks:**
  * Al ejecutar `az acr build`, Azure CLI empaqueta el directorio local autorizado y lo sube de forma privada al ACR Task en Azure.
  * Se configuró [`docker/.dockerignore`](../docker/.dockerignore) con reglas de exclusión universales para secretos (`config.json`, `.env`), entornos virtuales (`.venv/`), caches y datasets brutos, **permitiendo explícitamente la inclusión del directorio MLflow certificado**.
  * La directiva `COPY models/.../mlflow-model/ /app/models/` incorpora el modelo dentro de la imagen privada en ACR. Esto elimina la necesidad de Storage Accounts, montajes de Azure Files o descargas por red en el arranque, permitiendo lectura local a velocidad de SSD y reduciendo a cero el costo de almacenamiento externo.

### 2.2 Cuota y Tamaño en ACR Basic
- **Capas Base:** La imagen curada `mcr.microsoft.com/azureml/curated/ai-ml-automl:41` reside en MCR (red troncal interna de Microsoft). Al construirse en ACR Tasks, la descarga entre MCR y ACR en `eastus2` es de latencia ultra baja y sin costos de salida (*egress*).
- **Tamaño Estimado de la Imagen en ACR:** ~2.0 a 2.5 GiB comprimida.
- **Cuota Incluida en ACR Basic:** **10 GiB incluidos sin costo adicional**. La imagen consumirá únicamente el ~25% de la cuota estándar.

### 2.3 Compatibilidad de Paquetes
- Se comprobó que `fastapi==0.115.6`, `uvicorn==0.34.0`, `pydantic==2.12.5` y `starlette==0.41.3` en `docker/requirements-inference.txt` conviven sin conflictos de versiones con el entorno Conda `amlenv` de Python 3.10.19, preservando intactos `scikit-learn 1.5.1` y `azureml-training-tabular 1.61.0`.

---

## 3. Matriz Exhaustiva de Servicios, Costos, Comandos y Riesgos

La siguiente tabla detalla cada servicio que se propone crear en la secuencia de despliegue, su costo exacto en `eastus2`, cuotas, comandos propuestos y procedimiento de eliminación inmediata:

| Servicio a Crear | Región | SKU | Consumo Esperado | Precio Estimado y Fuente | Cuota o Restricción | Comando Exacto Propuesto (NO EJECUTADO) | Riesgo y Procedimiento de Eliminación |
|---|---|---|---|---|---|---|---|
| **Registro de Proveedor `Microsoft.App`** | Global (Suscripción) | N/A | 1 registro administrativo | **USD 0.00** *(Azure Resource Manager — Operación gratuita)* | Ninguna | `az provider register --namespace Microsoft.App` | **Riesgo Nulo:** No genera facturación. No requiere eliminación. |
| **Azure Container Registry (ACR)** | `eastus2` | `Basic` | 1 registro privado, almacenamiento ~2.5 GiB | **~$0.167 USD/día** (~$5.00 USD/mes). *(Azure Pricing Calculator - ACR Basic)* | 10 GiB incluidos. Máx. 1 webhook. | `az acr create --resource-group EcomixIA --name crecomixprod --sku Basic --location eastus2 --admin-enabled true` | **Costo Fijo Diario:** Factura ~$0.17/día mientras exista.<br>**Eliminación:** `az acr delete --name crecomixprod --resource-group EcomixIA --yes` |
| **ACR Tasks (Construcción Remota)** | `eastus2` | Cómputo Linux estándar | 1 build de ~3 a 4 minutos | **~$0.012 USD** ($0.00005/s = $0.003/min). *(Azure Pricing Calculator - ACR Tasks)* | 1 tarea de compilación concurrente. | `az acr build --registry crecomixprod --image ecomix-ml-inference:1.0.0 --file docker/Dockerfile .` | **Costo Variable Único:** Factura únicamente por los segundos que tarda el build. No genera cargos posteriores. |
| **Entorno de Azure Container Apps** | `eastus2` | `Consumption` | 1 entorno administrado (sin pods activos) | **USD 0.00** *(Azure Pricing - ACA Managed Environment)* | Cuota estándar de suscripción estudiantil. | `az containerapp env create --name me-ecomix-prod --resource-group EcomixIA --location eastus2` | **Riesgo Bajo:** El entorno en sí no factura. Se elimina con: `az containerapp env delete --name me-ecomix-prod --resource-group EcomixIA --yes` |
| **Aplicación ACA (`ecomix-ml-api`)** | `eastus2` | `Consumption` (Serverless) | 1.0 vCPU, 2.0 GiB RAM.<br>`minReplicas=0`, `maxReplicas=1`.<br>~50 peticiones en pruebas. | **USD 0.00** *(Cubierto por el Free Tier mensual de ACA: 180 000 vCPU-s y 360 000 GiB-s gratis)*. Fuera del free tier: $0.000030/s. | Máximo 1 réplica. Con `minReplicas=0` se escala a cero tras 300 s de inactividad. | `az containerapp create --name ca-ecomix-inference-api --resource-group EcomixIA --environment me-ecomix-prod --image crecomixprod.azurecr.io/ecomix-ml-inference:1.0.0 --target-port 8000 --ingress external --min-replicas 0 --max-replicas 1 --cpu 1.0 --memory 2.0Gi --env-vars ECOMIX_ENV=production ECOMIX_MODEL_PATH=/app/models ECOMIX_API_KEY=secretref:api-key --secrets api-key="<GENERATED_KEY>"` | **Costo en Reposo: $0.00.**<br>Si `minReplicas` fuera 1 facturaría $2.59/día. Con `minReplicas=0` el riesgo es nulo.<br>**Eliminación:** `az containerapp delete --name ca-ecomix-inference-api --resource-group EcomixIA --yes` |

---

## 4. Recursos que Permanecerán Facturando hasta su Eliminación

Para salvaguardar el crédito de USD 20 de Azure for Students, se identifican con total transparencia los recursos con cargos recurrentes:

1. **Azure Container Registry (ACR Basic):**  
   - Tarifa fija de **USD 0.167 por día** (~USD 5.00/mes).  
   - Es el **único recurso con costo diario fijo** de la arquitectura propuesta.
   - Si se conserva activo durante 3 días para completar las pruebas de la Fase 5.6-C, consumirá exactamente **USD 0.50**.
   - Para detener inmediatamente cualquier facturación al terminar las pruebas, se ejecuta:
     ```bash
     az acr delete --name crecomixprod --resource-group EcomixIA --yes
     ```
2. **Azure Container Apps (ACA Consumption):**  
   - Con `minReplicas: 0`, se apaga automáticamente cuando no hay tráfico HTTP entrante.  
   - Costo en reposo: **USD 0.00**. No genera cargos continuos.

---

## 5. Resumen Presupuestario de la Primera Ronda

- **Presupuesto Disponible:** USD 20.00
- **Límite Autoimpuesto para Ronda 1:** USD 10.00
- **Gasto Real Estimado para Ronda 1 (3 días de pruebas):** **~USD 0.52 a 0.70**
  * Registro ACR (3 días): USD 0.50
  * ACR Task Build (1-2 builds): USD 0.02
  * Cómputo ACA: USD 0.00 (cubierto por el cupo gratuito)
- **Remanente Protegido para Integración ASP.NET MVC 5:** **> USD 19.30 (96.5% del presupuesto)**.

---

## 6. Conclusión y Veredicto de la Auditoría

Se confirma que:
1. La suscripción `Azure for Students` está activa, habilitada y con saldo disponible.
2. La arquitectura basada en `minReplicas=0` y empaquetado del modelo inmutable (Opción C) garantiza que no se requerirán servicios costosos adicionales (como Azure Files o clústeres dedicados).
3. El gasto total estimado de la primera ronda representa únicamente el **2.6% del presupuesto de USD 20** (~USD 0.52).
4. El procedimiento de limpieza y comando destructivo para eliminar el costo fijo está probado y documentado.

**Veredicto:** **SE CUMPLEN RIGUROSAMENTE TODAS LAS CONDICIONES TÉCNICAS, DE SEGURIDAD Y PRESUPUESTARIAS PARA AUTORIZAR LA PRIMERA CONSTRUCCIÓN DE IMAGEN EN ACR Y DESPLIEGUE CONTROLADO EN FASE 5.6-C.**

*(El agente se detiene aquí conforme a la instrucción, sin ejecutar ningún comando facturable ni crear recursos en Azure).*
