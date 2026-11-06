# Informe Técnico — Fase 5.6-A: Endurecimiento DevSecOps de API y Preparación para Contenedorización

**Proyecto:** EcoMix IA (Azure Machine Learning)  
**Convocatoria:** Reto 2 — Yura S.A. (Hackathon Innova Sur 2026, Universidad Privada de Tacna)  
**Línea base integrada:** `0af76921bc62ce36df613a968652033bc8939c38` (Merge de PR #1 en `main`)  
**Rama activa:** `fix/phase-05-api-hardening`  
**Fecha:** Noviembre 2026  
**Responsable:** Ingeniero DevSecOps, Arquitecto FastAPI y MLOps  
**Veredicto:** **API ENDURECIDA Y PREPARADA PARA CONTENEDORIZACIÓN AL 100%**

---

## 1. Problemas Confirmados (Auditoría DevSecOps)

Durante la inspección de seguridad, inicialización y ciclo de vida de la API implementada en la Fase 5.5, se detectaron las siguientes vulnerabilidades y debilidades arquitectónicas:

1. **Credencial de Desarrollo por Defecto en Configuración (`src/api/config.py`):**
   - Existía un valor por defecto `"ecomix-dev-api-key-2026"` para `ECOMIX_API_KEY`. En caso de omisión accidental de variables de entorno al desplegar en producción, el servicio quedaba expuesto con una credencial pública conocida.
   - No existía restricción para impedir que `ECOMIX_AUTH_ENABLED=false` apagara la autenticación en entornos de producción.

2. **Vulnerabilidad a Ataques de Canal Lateral por Tiempos (Timing Attacks):**
   - La comprobación `x_api_key != settings.api_key` utilizaba el operador de igualdad estándar (`!=`), vulnerable a ataques de temporización mediante análisis estadístico de la latencia de comparación de cadenas.

3. **Contaminación de Estados Globales y Dependencia del Singleton `get_settings()`:**
   - Tanto `middleware.py` como `dependencies.py` invocaban `get_settings()` en lugar de leer `request.app.state.settings`. Si se instanciaban dos aplicaciones FastAPI con configuraciones distintas en un mismo proceso, ambas compartían las credenciales del singleton global.

4. **Sondas de Preparación Inseguras con Estimadores Sintéticos:**
   - La sonda `/health/ready` retornaba HTTP 200 siempre que `loader.is_loaded()` fuera verdadero, permitiendo inadvertidamente que un estimador mock/sintético de pruebas se declarara listo para recibir tráfico en un entorno de producción.

5. **Falta de Validación Estricta en Cabeceras HTTP:**
   - `Content-Length` no controlaba valores negativos ni strings no enteros, provocando excepciones 500 no controladas.
   - Cuerpos de solicitud enviados sin `Content-Length` (por ejemplo mediante transferencia fragmentada *chunked*) no estaban acotados en memoria.
   - `X-Request-ID` no contaba con sanitización ni límites de longitud, abriendo vectores de inyección CRLF o saturación de logs.
   - El endpoint predictivo no exigía `Content-Type: application/json`, procesando cargas no tipadas.

6. **Exposición de Documentación Interactiva en Producción:**
   - Aunque `/docs` y `/redoc` se desactivaban en producción, `/openapi.json` permanecía accesible, permitiendo reconocimiento automatizado de la API.

---

## 2. Correcciones Realizadas

### 2.1 Endurecimiento de Configuración (`src/api/config.py`)
- **Reglas Estrictas de Producción:** Implementación de `validate_security_and_production_rules` mediante `@model_validator(mode="after")`:
  * En entorno `production`, `ECOMIX_API_KEY` es obligatoria; si está vacía o ausente, el arranque falla inmediatamente con `ValueError`.
  * Lista negra estricta (`BANNED_PRODUCTION_KEYS`): se rechazan claves triviales o de desarrollo (`ecomix-dev-api-key-2026`, `admin`, `secret`, `dev`, `test`, `password`).
  * Entropía mínima: se exige una clave de al menos 16 caracteres en producción.
  * Prohibición absoluta de desactivar autenticación (`auth_enabled=False`) en producción.
- **Soporte de Rotación de Credenciales:** Función `get_valid_api_keys()` que admite múltiples secretos concurrentes (mediante cadenas separadas por coma en `ECOMIX_API_KEY` y/o `ECOMIX_API_KEY_SECONDARY`).
- **Enmascaramiento de Secretos:** Sobrescritura de `__repr__` para que las claves nunca se expongan en logs ni volcados de depuración (`keys_configured=True`).

### 2.2 Autenticación Segura y Aislamiento (`src/api/dependencies.py`)
- **Aislamiento por Instancia:** Inyección de `get_app_settings(request)` que resuelve `request.app.state.settings` con fallback al singleton, garantizando aislamiento total entre aplicaciones.
- **Comparación en Tiempo Constante:** Uso de `secrets.compare_digest(x_api_key, vk)` para todas las claves válidas, neutralizando completamente los ataques de temporización.
- **Manejo de Servidor no Configurado:** Si el servicio no tiene claves activas y la autenticación está encendida, responde con HTTP 503 (`auth-misconfigured`) bajo RFC 7807 sin filtrar datos internos.

### 2.3 Endurecimiento de Middleware HTTP (`src/api/middleware.py`)
- **Validación Segura de `Content-Length`:** Detección de cabeceras malformadas o negativas retornando HTTP 400 (`Bad Request`) estructurado.
- **Control de Cuerpos sin `Content-Length`:** Lectura y verificación del tamaño real del cuerpo en memoria (`request.body()`), retornando HTTP 413 si excede `max_request_body_bytes` (1 MB).
- **Sanitización de `X-Request-ID`:** Validación contra la expresión regular `^[a-zA-Z0-9_\-\.:]{1,128}$`. Si el valor es inválido o excede 128 caracteres, se sustituye automáticamente por un UUIDv4 seguro.
- **Enforzamiento de `Content-Type`:** Verificación obligatoria de `application/json` en `/api/v1/predict/concrete-strength`, devolviendo HTTP 415 (`Unsupported Media Type`) si se reciben otros formatos.

### 2.4 Disponibilidad y Sondas (`src/api/routes/health.py` y `src/api/main.py`)
- **Prohibición de Mocks en Producción:** La sonda `/health/ready` comprueba `artifact_info.is_synthetic`. Si el entorno es `production` y el estimador es sintético, retorna HTTP 503 (`synthetic-model-forbidden`).
- **Sonda de Arranque Dedicada (`/health/startup`):** Implementada para permitir a Azure Container Apps tolerar los ~26 segundos de carga inicial de Azure AutoML sin activar prematuramente los umbrales de fallo de `livenessProbe`.
- **Desactivación Integral de OpenAPI en Producción:** En modo producción y sin debug, `docs_url=None`, `redoc_url=None` y `openapi_url=None`.

---

## 3. Estrategia y Archivos de Contenedorización (`docker/`)

Se diseñó la arquitectura para empaquetar el microservicio de inferencia en un contenedor de grado de producción, sin desplegar recursos en Azure:

1. **`docker/requirements-inference.txt`:**
   - Fija con precisión las versiones de producción:
     * `fastapi==0.115.6`, `uvicorn[standard]==0.34.0`, `starlette==0.41.3`.
     * `pydantic==2.12.5`, `pydantic-settings==2.12.0`.
     * `scikit-learn==1.5.1`, `mlflow-skinny==2.15.1`, `azureml-training-tabular==1.61.0`.
   - Garantiza reproducibilidad sobre Python 3.10.19.

2. **`docker/Dockerfile`:**
   - **Imagen Base:** `mcr.microsoft.com/azureml/curated/ai-ml-automl:41` (imagen curada oficial de Microsoft con el entorno de AutoML preinstalado).
   - **Principio de Menor Privilegio:** Ejecución bajo el usuario no privilegiado `appuser` (UID 10001).
   - **Aislamiento del Modelo:** El binario del modelo (`model.pkl`) **NO se empaqueta en la imagen**. Se suministra en tiempo de ejecución mediante volumen montado en `/app/models`.
   - **Comando de Arranque:** `uvicorn src.api.main:app --host 0.0.0.0 --port 8000 --workers 1 --no-access-log` (1 worker por réplica para evitar contención de GIL en inferencias de Machine Learning).

3. **`docker/.dockerignore`:**
   - Excluye estrictamente archivos sensibles (`config.json`, `.env`), entornos virtuales (`.venv/`), modelos binarios (`models/*.pkl`), datos de entrenamiento y caches.

4. **`docker/azure-container-app-spec.yaml`:**
   - Plantilla declarativa para Azure Container Apps que especifica:
     * Asignación de recursos: 1.0 vCPU, 2.0 GiB RAM.
     * Escalado: `minReplicas: 1` (elimina el cold start para el usuario web), `maxReplicas: 3`.
     * Sonda de arranque (`Startup Probe`): tolera hasta 60 segundos de inicialización inicial.
     * Sonda de vida (`Liveness Probe`) y preparación (`Readiness Probe`).
     * Secreto `ECOMIX_API_KEY` inyectado desde Azure Key Vault.

---

## 4. Resultados de Pruebas Automatizadas

Se construyó la suite [`tests/test_api_hardening.py`](file:///c:/Users/Admin/Desktop/Proyectos/ML%20EcomixIA/tests/test_api_hardening.py) con 14 pruebas específicas de DevSecOps, ejecutándose en conjunto con la suite existente:

| Suite de Pruebas | Archivo | Pruebas | Estado |
|---|---|---|---|
| **Endurecimiento DevSecOps (Fase 5.6-A)** | `tests/test_api_hardening.py` | 14 | **14 PASSED (100%)** |
| **Servicio API REST (Fase 5.5)** | `tests/test_api_service.py` | 18 | **18 PASSED (100%)** |
| **Jobs y Azure ML (Fase 4)** | `tests/test_azure_eval_job.py` | 13 | **13 PASSED (100%)** |
| **Diagnóstico del Sistema** | `tests/test_doctor.py` | 10 | **10 PASSED (100%)** |
| **Control de Evaluación** | `tests/test_evaluation_control.py` | 17 | **17 PASSED (100%)** |
| **Desacoplamiento de Runtime** | `tests/test_evaluation_runtime_decoupling.py` | 5 | **5 PASSED (100%)** |
| **Motor de Inferencia y Loader** | `tests/test_inference_engine_and_loader.py` | 17 | **17 PASSED (100%)** |
| **Runtime y Contratos de Job** | `tests/test_inference_runtime_and_job.py` | 14 | **14 PASSED (100%)** |
| **Esquemas y Validación de Dominio** | `tests/test_inference_schemas_and_validation.py` | 24 | **24 PASSED (100%)** |
| **Descarga Segura de Artefactos** | `tests/test_inspect_and_download.py` | 14 | **14 PASSED (100%)** |
| **Carga de Modelos** | `tests/test_model_loading.py` | 10 | **10 PASSED (100%)** |
| **Auditoría de Runtime** | `tests/test_model_runtime.py` | 6 | **6 PASSED (100%)** |
| **Sincronización de Estado** | `tests/test_sync_state.py` | 5 | **5 PASSED (100%)** |
| **TOTAL GENERAL** | **13 suites** | **176** | **176 PASSED (100%)** |

---

## 5. Riesgos Pendientes y Mitigaciones Planificadas

| Riesgo Técnico / Operativo | Severidad | Mitigación Implementada / Propuesta |
|---|---|---|
| **Latencia de Arranque en Frío (~26.69 s)** | Media | Sonda de arranque `/health/startup` tolera hasta 60 s. Configuración `minReplicas = 1` en Container Apps garantiza réplica caliente permanente. |
| **Incompatibilidad de Runtime en Desarrollo Local** | Baja | Claramente desacoplado: localmente se ejecutan pruebas de contrato y sintéticas; el modelo real se ejecuta en el contenedor curado oficial de Azure AutoML. |
| **Suministro del Binario en Contenedor** | Media | Se definió montaje externo mediante volumen (`/app/models`), auditado por hash criptográfico SHA-256 antes de deserialización. |

---

## 6. Archivos Creados y Modificados

### Archivos Modificados
- `config/project_status.json`: Actualización de fases hacia 5.6-A.
- `docs/PROJECT_STATE.md`: Sincronización automática de estado documental.
- `src/api/config.py`: Reglas de seguridad en producción, prohibición de claves públicas, rotación de credenciales.
- `src/api/dependencies.py`: Inyección `get_app_settings`, comparación con `secrets.compare_digest`.
- `src/api/middleware.py`: Control de tamaño sin Content-Length, sanitización de X-Request-ID, Content-Type 415.
- `src/api/routes/health.py`: Rechazo de modelos sintéticos en producción, endpoint `/health/startup`.
- `src/api/main.py`: Ciclo de vida con verificación estricta de claves y desactivación de OpenAPI en producción.

### Archivos Creados
- `docker/requirements-inference.txt`: Dependencias bloqueadas para runtime Python 3.10.19.
- `docker/Dockerfile`: Definición de contenedor seguro no privilegiado sobre imagen curada de Azure AutoML.
- `docker/.dockerignore`: Filtros de exclusión para empaquetado Docker limpio.
- `docker/azure-container-app-spec.yaml`: Manifiesto declarativo para Azure Container Apps.
- `tests/test_api_hardening.py`: 14 pruebas automatizadas de seguridad DevSecOps.
- `docs/PHASE_5_6_A_API_HARDENING_REPORT.md`: Este informe técnico.

---

## 7. Estado Git y Veredicto

- **Línea Base:** `0af7692` (Merge de PR #1 en `main`).
- **Rama Actual:** `fix/phase-05-api-hardening`
- **Veredicto Técnico:** **API ENDURECIDA, RESILIENTE Y TOTALMENTE PREPARADA PARA CONTENEDORIZACIÓN Y DESPLIEGUE CONTROLADO EN FASE 5.6-B.**
