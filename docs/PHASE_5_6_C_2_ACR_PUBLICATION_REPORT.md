# Informe Técnico de Publicación en ACR — Fase 5.6-C.2R (Etapa 1 Concluida)

**Proyecto:** EcoMix IA (Azure Machine Learning)  
**Convocatoria:** Reto 2 — Yura S.A. (Hackathon Innova Sur 2026, Universidad Privada de Tacna)  
**Rama activa:** `fix/phase-05-api-hardening`  
**Fecha:** Noviembre 2026  
**Responsable:** Ingeniero DevSecOps y MLOps  
**Veredicto:** **ETAPA 1 CULMINADA EXITOSAMENTE — IMAGEN PUBLICADA Y CERTIFICADA EN AZURE CONTAINER REGISTRY (CHILE CENTRAL)**

---

## 1. Resumen Ejecutivo de la Etapa 1

Conforme a la autorización expresa del usuario, se completó de forma íntegra y segura la **Etapa 1** de publicación en Azure Container Registry, utilizando la región autorizada por la política institucional estudiantil (**`chilecentral`**).

| Parámetro | Valor Certificado |
|---|---|
| **Registro de Contenedores** | `crecomixprod` |
| **Servidor de Inicio de Sesión (Login Server)** | `crecomixprod.azurecr.io` |
| **Región Oficial** | `chilecentral` (Chile Central) |
| **Grupo de Recursos** | `EcomixIA` |
| **SKU del Registro** | `Basic` (con 10 GiB de cuota incluidos) |
| **Cuenta Administradora (`adminUserEnabled`)** | **`false`** (Deshabilitada por DevSecOps) |
| **Modo de Asignación de Roles** | `rbac` (Autenticación exclusiva vía tokens AAD y RBAC) |
| **Repositorio Creado** | `ecomix-ml-inference` |
| **Etiqueta Publicada** | `1.0.0` |
| **Digest OCI Oficial (Manifest List)** | `sha256:f50d37251430ad1e42d8df663554e0ea346a8dfffae8799393023d4afbb1d12a` |
| **Digest de Imagen (Linux/amd64)** | `sha256:592f9704c43b561d8bc98fb838b107141ca9696834efdb329114e3483e7c2972` |
| **Tamaño Comprimido Efectivo en ACR** | **`2,199,084,043` bytes (~2.05 GiB)** |
| **Uso de Cuota en ACR Basic** | **~20.5%** de los 10 GiB incluidos |
| **Hash SHA-256 del Modelo Integrado** | `7eaa501c5eeb60135effb6b5861e736518ce969c47afd53727c2451083ff6388` |
| **Algoritmo Estimador en Imagen** | `RegressionPipeline` (`VotingEnsemble` real, `is_synthetic: false`) |
| **Fecha/Hora de Creación de ACR** | `2026-11-06T19:23:30.915964+00:00` |

---

## 2. Detalle de Ejecución Paso a Paso

### 2.1 Verificaciones Previas Obligatorias
Se validó la suscripción `Azure for Students` (`72d4dc56-4d14-4a13-a9ca-9773ed0ba6eb`, `Enabled`, usuario `joamedina@upt.pe`). Docker Desktop 4.53.0 / Engine 29.0.1 confirmó la presencia de la imagen validada `ecomix-ml-inference:1.0.0` (ID: `f50d37251430`). Se revalidó la integridad del modelo binario de 670,849 bytes y su hash SHA-256 oficial antes del etiquetado.

### 2.2 Creación del Registro en Chile Central
Se aprovisionó el recurso mediante Azure CLI:
```bash
az acr create \
  --resource-group EcomixIA \
  --name crecomixprod \
  --sku Basic \
  --location chilecentral \
  --admin-enabled false \
  --role-assignment-mode rbac
```
**Resultado:** Exit code 0 (`provisioningState: Succeeded`).  
El recurso fue creado bajo el Resource ID:
`/subscriptions/72d4dc56-4d14-4a13-a9ca-9773ed0ba6eb/resourceGroups/EcomixIA/providers/Microsoft.ContainerRegistry/registries/crecomixprod`

### 2.3 Autenticación Segura sin Credenciales de Administrador
Se autenticó el cliente Docker local mediante el token federado de Microsoft Entra ID (Azure AD):
```bash
az acr login --name crecomixprod
```
**Resultado:** `Login Succeeded`. El usuario `joamedina@upt.pe` acreditó permisos de publicación (`AcrPush`) sobre el registro sin necesidad de habilitar claves estáticas ni contraseñas.

### 2.4 Etiquetado y Publicación (`docker push`)
```bash
docker tag ecomix-ml-inference:1.0.0 crecomixprod.azurecr.io/ecomix-ml-inference:1.0.0
docker push crecomixprod.azurecr.io/ecomix-ml-inference:1.0.0
```
**Resultado:** Exit code 0.  
Todas las capas se transfirieron y consolidaron en el registro privado.

---

## 3. Verificación de la Publicación y Auditoría del Repositorio

La consulta de metadatos OCI (`az acr manifest list-metadata`) arrojó:

1. **Manifest List Index:**
   - **Digest:** `sha256:f50d37251430ad1e42d8df663554e0ea346a8dfffae8799393023d4afbb1d12a`
   - **Tags:** `["1.0.0"]`
   - **Media Type:** `application/vnd.oci.image.index.v1+json`
2. **Capa Ejecutable Linux amd64:**
   - **Digest:** `sha256:592f9704c43b561d8bc98fb838b107141ca9696834efdb329114e3483e7c2972`
   - **Tamaño:** `2,199,084,043 bytes` (~2.05 GiB)
   - **Arquitectura:** `amd64`, SO: `linux`
3. **Seguridad del Registro:**
   - `adminUserEnabled`: **`false`**
   - Acceso público anónimo: `disabled`
   - Autenticación: Azure AD / RBAC únicamente.
4. **Gobernanza Git y Secretos:**
   - Se verificó que `models/` y los binarios `.pkl` continúan excluidos en `.gitignore`.
   - Ningún artefacto confidencial, credencial o dataset ha sido enviado a GitHub.

---

## 4. Control Presupuestario y de Costos

> [!NOTE]
> **Descargo de responsabilidad de facturación:**  
> Microsoft Cost Management presenta una latencia habitual de 8 a 24 horas para reflejar los consumos en los portales analíticos. Las cifras a continuación corresponden a las tarifas oficiales minoristas vigentes en Azure para `chilecentral`.

- **Presupuesto Total Suscripción:** **USD 20.00**
- **Cómputo en la Nube:** **USD 0.00** (el build se realizó localmente en la estación de trabajo, ahorrando costos de ACR Tasks).
- **Tráfico de Red Entrante (Ingress):** **USD 0.00** (la subida de imágenes a Azure es gratuita en todas las regiones).
- **Tarifa Fija de Almacenamiento ACR Basic:** **~$0.167 USD/día** (~$5.00 USD/mes).
- **Gasto Estimado de Etapa 1:** **~$0.17 a USD 0.34** (para un periodo de prueba de 1 a 2 días).
- **Saldo Disponible Remanente:** **> USD 19.65** (más del 98% del crédito protegido para la Etapa 2 y pruebas con la plataforma web).

### Procedimiento de Eliminación Inmediata (En caso de abortar o limpiar):
Para cancelar inmediatamente la facturación diaria del registro:
```bash
az acr delete --name crecomixprod --resource-group EcomixIA --yes
```

---

## 5. Cumplimiento de Restricciones y Detención

En estricta conformidad con las directrices vigentes:
- **NO** se creó Azure Container Apps.
- **NO** se registró `Microsoft.App` ni se crearon identidades administradas.
- **NO** se desplegó la API FastAPI como servicio público.
- **NO** se realizaron modificaciones al plan estudiantil ni se ejecutaron trabajos de Azure ML.
- **NO** se realizó push o merge a GitHub.
- El registro `crecomixprod` contiene únicamente la imagen inmutable oficial de inferencia predictiva.

**El agente se detiene aquí al concluir satisfactoriamente la Etapa 1. El inicio de la Etapa 2 (Despliegue en Azure Container Apps) requerirá una nueva autorización expresa.**
