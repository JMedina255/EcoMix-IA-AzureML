# Informe de Publicación en ACR — Fase 5.6-C.2

**Proyecto:** EcoMix IA (Azure Machine Learning)  
**Convocatoria:** Reto 2 — Yura S.A. (Hackathon Innova Sur 2026, Universidad Privada de Tacna)  
**Rama activa:** `fix/phase-05-api-hardening`  
**Commit base:** `a97f521`  
**Fecha:** Noviembre 2026  
**Responsable:** Ingeniero DevSecOps y MLOps  
**Veredicto:** **EJECUCIÓN DETENIDA SIN GASTO — BLOQUEO POR POLÍTICA DE REGIONES EN SUSCRIPCIÓN ESTUDIANTIL**

---

## 1. Verificaciones Previas Obligatorias

Previo a la creación de recursos, se ejecutaron rigurosamente las 9 comprobaciones requeridas:

| # | Verificación | Resultado | Detalle |
|---|---|---|---|
| **1** | **`AGENTS.md` y Estado Git** | **Aprobado** | Rama `fix/phase-05-api-hardening`, HEAD `a97f521`, árbol 100% limpio. |
| **2** | **Suscripción Azure Activa** | **Aprobado** | `Azure for Students` (`72d4dc56-4d14-4a13-a9ca-9773ed0ba6eb`), estado `Enabled`, usuario `joamedina@upt.pe`. |
| **3** | **Docker Desktop / Engine** | **Aprobado** | Docker Desktop 4.53.0 / Docker Engine 29.0.1 (WSL2 Linux amd64) operativo. |
| **4** | **Presencia de Imagen Local** | **Aprobado** | `ecomix-ml-inference:1.0.0` presente (Image ID: `f50d37251430`, 8.02 GB uncompressed). |
| **5** | **Estimador Real en Imagen** | **Aprobado** | Verificado en contenedor: `Algorithm: RegressionPipeline`, `is_synthetic: False`. |
| **6** | **Integridad SHA-256 del Modelo** | **Aprobado** | `/app/models/model.pkl` (`670,849 bytes`), SHA-256: `7eaa501c5eeb60135effb6b5861e736518ce969c47afd53727c2451083ff6388`. |
| **7** | **Inexistencia Previa de ACR** | **Aprobado** | `crecomixprod` no existe en la suscripción ni en Azure. |
| **8** | **Disponibilidad de Nombre** | **Aprobado** | `az acr check-name --name crecomixprod` confirmó `nameAvailable: true`. |
| **9** | **Ausencia de Secretos en Imagen** | **Aprobado** | Verificado que `/app` no contiene `config.json`, `.env`, `.csv` ni `.git`. |

---

## 2. Intento de Creación y Diagnóstico de Bloqueo por Azure Policy

En cumplimiento de la autorización recibida, se ejecutó el comando solicitado para la región `eastus2`:

```bash
az acr create \
  --resource-group EcomixIA \
  --name crecomixprod \
  --sku Basic \
  --location eastus2 \
  --admin-enabled false \
  --role-assignment-mode rbac
```

### 2.1 Error Observado de Azure Resource Manager
```text
ERROR: (RequestDisallowedByAzure) Resource 'crecomixprod' was disallowed by Azure: 
This policy maintains a set of best available regions where your subscription can deploy resources. 
The objective of this policy is to ensure that your subscription has full access to Azure services 
with optimal performance. Should you need additional or different regions, contact support..
Code: RequestDisallowedByAzure
Target: crecomixprod
```

### 2.2 Auditoría de la Directiva de Gobernanza en la Suscripción
Se consultaron de inmediato las asignaciones de directivas en la suscripción (`az policy assignment show`):

- **Nombre de Directiva:** `sys.regionrestriction`
- **Nombre Descriptivo:** `Allowed resource deployment regions`
- **Ámbito:** `/subscriptions/72d4dc56-4d14-4a13-a9ca-9773ed0ba6eb`
- **Lista de Regiones Exclusivamente Autorizadas (`listOfAllowedLocations`):**
  1. `chilecentral` (Chile Central)
  2. `mexicocentral` (Mexico Central)
  3. `northcentralus` (North Central US)
  4. `westcentralus` (West Central US)
  5. `canadaeast` (Canada East)

La directiva institucional impuesta sobre la suscripción `Azure for Students` **bloquea despliegues en `eastus2`**, limitando la creación de recursos a las 5 regiones anteriores.

---

## 3. Diagnóstico de Compatibilidad en las Regiones Autorizadas

Se verificó el soporte de proveedores en las 5 regiones autorizadas por la política:

| Región Autorizada | Proveedor `Microsoft.ContainerRegistry` | Proveedor `Microsoft.App` (ACA) | Latencia Estimada para Tacna, Perú |
|---|---|---|---|
| **`chilecentral`** (Chile Central) | **Disponible** | **Disponible** | **Mínima (~30-50 ms)** — Recomendada |
| **`mexicocentral`** (México Central) | **Disponible** | **Disponible** | Media (~100-130 ms) |
| **`northcentralus`** (North Central US) | **Disponible** | **Disponible** | Media-Alta (~140-160 ms) |
| **`westcentralus`** (West Central US) | **Disponible** | **Disponible** | Media-Alta (~150-170 ms) |
| **`canadaeast`** (Canadá Este) | **Disponible** | **Disponible** | Alta (~160-190 ms) |

Tanto **Azure Container Registry** como **Azure Container Apps** están plenamente soportados en **`chilecentral`**, lo cual representa una ventaja arquitectónica adicional por proximidad geográfica con el nodo de Tacna (Universidad Privada de Tacna).

---

## 4. Estado del Presupuesto y Recursos

- **Recursos Creados:** Ninguno (el registro no llegó a aprovisionarse).
- **Gasto Real Facturado:** **USD 0.00**.
- **Crédito Remanente en `Azure for Students`:** **USD 20.00 (100% intacto)**.
- **Imagen Local:** Preservada intacta en Docker local (`ecomix-ml-inference:1.0.0`).

---

## 5. Cumplimiento de Restricciones y Detención

En estricta observancia de las reglas del usuario:
- *«Si alguna verificación falla, detener la ejecución.»*
- *«Si el comando falla, no realizar reintentos automáticos.»*

**No se ejecutó ningún reintento automático ni se alteró la región por cuenta propia.** El agente se detiene aquí para solicitar la aprobación explícita del usuario respecto a la nueva región autorizada (`chilecentral`).
