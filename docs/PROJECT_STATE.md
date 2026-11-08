# Estado Vivo del Proyecto — EcoMix IA (Azure ML)

> **Documento vivo de trazabilidad técnica.**  
> Fuente declarativa: [`config/project_status.json`](../config/project_status.json).  
> Actualizado y verificado mediante: `python scripts/sync_state.py`.

---

## 1. Identificación y Parámetros Generales

- **Identificador del Proyecto:** `ecomix-ia-ml`
- **Repositorio:** `JMedina255/EcoMix-IA-AzureML`
- **Rama Principal:** `main`
- **Fase Actual:** `6.4 — Cierre Documental, Recuperación de CI y Preparación para Integración MVC`
- **Próximo Hito Autorizado:** `Fase 6.1 — Integración con Plataforma Web ASP.NET MVC 5 (consumo de API REST en Azure Container Apps)`
- **Última Validación Registrada:** `2026-11-08` (Origen: *Azure Container Apps & Inferencia Real en la Nube (ca-ecomix-inference-api en chilecentral)*)

---

## 2. Estado de las Fases del Pipeline ML

| Fase | Nombre | Estado | Script / Componente | Evidencia Técnica Comprobada |
| :---: | :--- | :---: | :--- | :--- |
| **1** | Descarga de Datos | ✅ Completado | `data/raw/concrete_raw.csv` | Dataset UCI ID 165 preservado en data/raw/concrete_raw.csv |
| **2** | Preparacion y Validacion | ✅ Completado | `src/prepare_data.py` | Split deterministico 80/20 (824 train, 206 test), 0 nulos, 25 replicas ASTM |
| **3** | Entrenamiento AutoML en Azure | ✅ Completado | `src/train_automl.py` | Job wheat_cheese_4swj34tkjn completado, 12 iteraciones, mejor score NRMSE 0.05859 |
| **4.1** | Inspeccion Segura del Experimento | ✅ Completado | `src/evaluate_model.py --inspect` | Normalizacion de estado canonico y trazabilidad desglosada del experimento |
| **4.2** | Control de Recursos y Validacion de Dataset de Prueba | ✅ Completado | `src/evaluate_model.py (validaciones)` | Validacion de 206 muestras de prueba, deteccion de solapamiento y metricas robustas |
| **4.3** | Descarga Selectiva de Artefactos | ✅ Completado | `src/evaluate_model.py --download` | Descarga directa asegurada mediante Model Asset verificado sin all=True |
| **4.4** | Evaluacion Independiente del Modelo | ✅ Completado | `src/evaluate_model.py --evaluate` | Job stoic_pot_x25ht98nv7 completado exitosamente en Azure ML (2m 35s). 206 observaciones evaluadas (100% validas): R2 0.9121, RMSE 4.7592 MPa, MAE 3.2822 MPa, NRMSE 0.0673. En subconjunto sin solapamiento (195 muestras): R2 0.9174, RMSE 4.587 MPa. Desglose: 7d (R2 0.8841, RMSE 5.1725 MPa), 28d (R2 0.8235, RMSE 5.5930 MPa). |
| **4.5** | Generacion de Reportes y Trazabilidad | ✅ Completado | `src/evaluate_model.py (reporting)` | Reporte JSON oficial 'reports/evaluation_wheat_cheese_4swj34tkjn.json' (9,928 bytes) y grafico de correlacion auditados y consolidados. Documento de evaluacion tecnica generado en 'docs/EVALUATION_REPORT.md', especificacion de inferencia para Fase 5 preparada y estado del repositorio sincronizado. |
| **5** | Servicio de Inferencia ML y API REST (7d y 28d) | ✅ Completado | `src/api/main.py` | Motor de inferencia real VotingEnsemble validado en Azure ML (serene_spinach_sn7khxvkq7) con paridad determinística (|Δ|=0.0 MPa). Microservicio REST FastAPI modular implementado, validado con 18 pruebas y fusionado a main (PR #1, commit 0af7692). |
| **5.6-A** | Endurecimiento DevSecOps y Preparacion de Contenedor | ✅ Completado | `src/api/config.py` | Blindaje DevSecOps completado: mitigacion de timing attacks (secrets.compare_digest), prohibicion de claves publicas, aislamiento por instancia, control de flujo incremental en middleware, y 15 pruebas de endurecimiento aprobadas (commit 174c6dc). |
| **5.6-B** | Verificacion de Contenedor y Plan de Despliegue ACA | ✅ Completado | `docker/Dockerfile` | Especificación declarativa de contenedor y manifest docker/azure-container-app-spec.yaml validado localmente con imagen base curada ai-ml-automl:41 y runtime Python 3.10.19 (Reporte docs/PHASE_5_6_B_CONTAINER_VALIDATION_REPORT.md). |
| **5.6-C** | Despliegue y Validación en la Nube (ACR y Azure Container Apps) | ✅ Completado | `docker/azure-container-app-spec.yaml` | Publicación en ACR crecomixprod.azurecr.io/ecomix-ml-inference:1.0.0 y despliegue exitoso en Azure Container Apps (ca-ecomix-inference-api) en chilecentral con Managed Identity id-ecomix-aca y Scale-to-Zero (minReplicas=0, maxReplicas=1). Inferencia en caliente validada en ~248 ms con paridad exacta contra el VotingEnsemble oficial (Reportes docs/PHASE_5_6_C_2_ACR_PUBLICATION_REPORT.md y docs/PHASE_5_6_C_3_ACA_DEPLOYMENT_REPORT.md). |
| **6.4** | Cierre Documental, Recuperación de CI y Preparación para Integración MVC | 🔄 En progreso | `scripts/sync_state.py` | Auditoría integral, resolución de compatibilidad de dependencias de testing (httpx==0.28.1 en requirements-dev.txt), refactorización declarativa del sincronizador de estado, reescritura de README.md, creación de docs/INDEX.md y runbook operativo (Reporte docs/PHASE_6_4_D_DOCUMENTATION_CLOSURE.md). |
| **6.1** | Integración con Plataforma Web ASP.NET MVC 5 | 🟡 Pendiente | `docs/PHASE_6_1_MVC_INTEGRATION_PLAN.md` | Diseño arquitectónico y contratos HTTP/JSON para consumo desde ASP.NET MVC 5 documentados. Pendiente de implementación por el equipo de desarrollo de la plataforma web. |
| **7** | Simulador Interactivo (Streamlit UI) | 🟡 Pendiente | `app.py` | No iniciado (planificado posterior a la integración MVC). |

---

## 3. Experimento y Modelo Ganador (Datos Comprobados en Azure ML)

Los siguientes datos corresponden a la telemetría oficial de Azure ML Workspace (`ecomix-ia-ml`, Grupo `EcomixIA`):

- **Job Name:** `wheat_cheese_4swj34tkjn`
- **Estado Oficial:** `Completed` (Canónico: `completed`)
- **Métrica Primaria:** `normalized_root_mean_squared_error`
- **Valor de la Métrica:** `0.05859`
- **Algoritmo Ganador:** `VotingEnsemble`
- **Child Run Ganador:** `wheat_cheese_4swj34tkjn_11`
- **Activo de Modelo (Model Asset):**  
  `azureml_wheat_cheese_4swj34tkjn_11_output_mlflow_log_model_873731674:1`
- **Tamaño del Modelo en Disco:** `670,849 bytes` (~655.1 KB)
- **Modelo en Catálogo Manual:** Ninguno registrado manualmente en catálogo (activo local de workspace).
- **Entorno de Entrenamiento Original:**  
  Imagen Curada: `mcr.microsoft.com/azureml/curated/ai-ml-automl:41` (Python 3.10.19).

### 3.1 Despliegue Operativo en la Nube (Azure Container Apps)

- **Servicio Cloud:** `Azure Container Apps (ACA)`
- **Perfil de Cómputo:** `Serverless Consumption`
- **Aplicación:** `ca-ecomix-inference-api` (Región: `chilecentral`)
- **Registro e Imagen:** `crecomixprod.azurecr.io/ecomix-ml-inference:1.0.0`
- **Digest OCI:** `sha256:f50d37251430ad1e42d8df663554e0ea346a8dfffae8799393023d4afbb1d12a`
- **Identidad Administrada:** `id-ecomix-aca` (Rol RBAC: `AcrPull`)
- **Dimensionamiento y Escala:** `1.0 vCPU, 2.0 GiB RAM` | `minReplicas = 0, maxReplicas = 1 (Scale-to-Zero)`
- **Estimador Activo:** `RegressionPipeline (VotingEnsemble real, is_synthetic: false)`
- **Hash SHA-256 Verificado:** `7eaa501c5eeb60135effb6b5861e736518ce969c47afd53727c2451083ff6388`
- **Latencias Observadas:** Arranque en frío (cold start): ~8.4 s | Inferencia en caliente: ~248 ms
- **Costo Computacional ACA:** USD 0.00 (en reposo bajo cuota gratuita de 180k vCPU-s; costo fijo mensual de suscripción: ACR Basic ~USD 5.00/mes)

---

## 4. Incidencias Técnicas y Mitigaciones

### Incidencia ISSUE-SDK-01 (Mitigated)
- **Descripción:** TypeError en BatchGetResolvedUrisDto.__init__() al descargar por output_name='best_model'.
- **Mitigación comprobada:** Descarga directa selectiva via Model Asset (ml_client.models.download) implementada en evaluate_model.py.

### Incidencia ISSUE-ENV-01 (Monitored)
- **Descripción:** El modelo AutoML VotingEnsemble fue generado en Python 3.10.19 con scikit-learn 1.5.1 y mlflow 2.15.1. El entorno de desarrollo general soporta Python 3.10-3.13, pero la deserializacion fiel del modelo binario requiere concordancia de runtime.
- **Recomendación:** Separar el entorno de desarrollo general del runtime de inferencia; utilizar Python 3.10.19 en venv dedicado o ejecucion remota documentada.

### Incidencia ISSUE-SDK-02 (Resolved)
- **Descripción:** ModuleNotFoundError: No module named 'azure.ai' al ejecutar CommandJob en el contenedor curado oficial de Azure AutoML debido a importaciones top-level del SDK de gestion.
- **Mitigación comprobada:** Desacoplamiento arquitectonico mediante 'from __future__ import annotations', TYPE_CHECKING y lazy import de azure.ai.ml y azure.identity exclusivamente en funciones cliente (commit 1491940). Verificado exitosamente con job stoic_pot_x25ht98nv7.

### Incidencia ISSUE-CI-01 (Resolved)
- **Descripción:** Fallo en los 4 jobs de la matriz CI (Run 42295337947) por RuntimeError durante la colección de tests/test_api_hardening.py y tests/test_api_service.py al faltar la dependencia httpx requerida por TestClient en entornos limpios.
- **Mitigación comprobada:** Inclusión de httpx==0.28.1 en requirements-dev.txt y alineación de fastapi>=0.115.6 y starlette>=0.41.3 en requirements.txt.

---

## 5. Pruebas y Cobertura Verificada

- **Suite de Pruebas:** `pytest tests/ -v`
- **Total de Pruebas Automatizadas:** 177 pruebas recopiladas.
- **Resultado en Entorno Local:** 177 passed (100% de la suite automatizada en entorno local con modelo descargado)
- **Resultado en CI (GitHub Actions):** Pendiente de confirmación por GitHub Actions tras la incorporación de httpx==0.28.1 en requirements-dev.txt (anteriormente 4 jobs fallaron por falta de httpx en el entorno limpio de CI).
- **Archivos de Prueba:**
  - `tests/test_api_hardening.py`
  - `tests/test_api_service.py`
  - `tests/test_azure_eval_job.py`
  - `tests/test_doctor.py`
  - `tests/test_evaluation_control.py`
  - `tests/test_evaluation_runtime_decoupling.py`
  - `tests/test_inference_schemas_and_validation.py`
  - `tests/test_inspect_and_download.py`
  - `tests/test_model_loading.py`
  - `tests/test_model_runtime.py`
  - `tests/test_sync_state.py`

---

## 6. Distinción Entre Hechos Comprobados y Plan de Ejecución

### Hechos Comprobados y Pasos Completados
1. Partición de datos determinística 80/20 (824 train, 206 test) con SHA-256 canónico (6484d9f1...)
2. Entrenamiento AutoML exitoso en Azure ML con VotingEnsemble como ganador (NRMSE = 0.05859)
3. Descarga selectiva segura vía Model Asset sin descargar el snapshot completo del experimento (670,849 bytes)
4. Verificación de firma y 8 variables de entrada con verificación offline
5. Desacoplamiento de runtime con lazy imports del SDK de Azure ML
6. Evaluación independiente en Azure ML (Job stoic_pot_x25ht98nv7): R² = 0.9121, RMSE = 4.7592 MPa, NRMSE = 0.0673
7. Consolidación de reportes de evaluación en JSON oficial, visualizaciones y documentación técnica
8. Servicio de inferencia determinística dual a 7 y 28 días con paridad exacta contra el modelo ganador
9. Blindaje DevSecOps de API REST FastAPI: RFC 7807, mitigación de timing attacks, sanitización X-Request-ID, Content-Length y Content-Type control
10. Construcción y verificación local del contenedor Docker con runtime curado de Azure AutoML (Python 3.10.19)
11. Publicación de imagen certificada en Azure Container Registry (crecomixprod.azurecr.io/ecomix-ml-inference:1.0.0)
12. Despliegue operativo en Azure Container Apps (chilecentral) con Managed Identity (id-ecomix-aca) y política Scale-to-Zero
13. Validación de inferencia real en la nube con respuesta exitosa (21.96 MPa a 7d y 31.15 MPa a 28d) y latencia en caliente de ~248 ms

### Plan de Ejecución y Tareas Pendientes
1. Confirmación de ejecución verde en GitHub Actions tras corrección de dependencias de testing
2. Aprobación y fusión del PR de cierre documental hacia la rama main
3. Fase 6.1 — Implementación del cliente de integración HTTP en ASP.NET MVC 5 (consumo de Azure Container Apps)
4. Implementación del cálculo analítico de optimización de costos (S/./m³) y huella de carbono (kg CO2e/m³) en la capa de negocio
5. Fase 7 — Desarrollo de simulador interactivo de mezclas ecológicas (Streamlit UI)
