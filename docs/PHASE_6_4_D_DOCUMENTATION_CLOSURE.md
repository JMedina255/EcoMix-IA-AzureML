# Informe Técnico de Cierre Documental y Aseguramiento de Calidad — Fase 6.4-D

**Proyecto:** EcoMix IA (Azure Machine Learning)  
**Convocatoria:** Reto 2 — Yura S.A. (Hackathon Innova Sur 2026, Universidad Privada de Tacna)  
**Rama de Entrega:** `docs/phase-06-4-documentation-closure`  
**Fecha:** 8 de noviembre de 2026  
**Responsable:** Arquitecto MLOps, Ingeniero de Software y Responsable de Documentación Técnica  
**Veredicto:** **REPOSITORIO COMPLETAMENTE AUDITADO, ESTABILIZADO Y LISTO PARA INTEGRACIÓN ASP.NET MVC 5 (PENDIENTE VERIFICACIÓN CI)**

---

## 1. Resumen Ejecutivo

En cumplimiento de las directrices de aseguramiento de calidad, gobernanza y cierre técnico, se ha completado la auditoría integral del repositorio `JMedina255/EcoMix-IA-AzureML`.

Los objetivos alcanzados en esta intervención son:
1. **Recuperación de Integración Continua (CI):** Identificación y resolución de la causa raíz que provocó el fallo de colección en los 4 jobs de GitHub Actions (Run `42295337947`) en `tests/test_api_hardening.py` y `tests/test_api_service.py` debido a la ausencia de `httpx` en el entorno limpio de CI.
2. **Refactorización Declarativa del Estado Vivo:** Eliminación de textos fijos obsoletos en `scripts/sync_state.py` (referencias antiguas a 88 pruebas y fases 5-7 pendientes), registrando con rigor las fases completadas 5.6-A, 5.6-B, 5.6-C (ACR y Azure Container Apps en `chilecentral`), con validación de idempotencia al 100%.
3. **Reescritura Estructural de `README.md`:** Clarificación del alcance real (aislamiento estricto del núcleo ML frente a la plataforma ASP.NET MVC 5), diagrama de arquitectura en Mermaid, distinción transparente entre el NRMSE interno de AutoML (`0.05859`) y el NRMSE sobre datos ciegos independientes (`0.0673`), certificación del caso canónico `280/0/0/180/0/1050/750` ($21.96\text{ MPa}$ a 7d y $31.15\text{ MPa}$ a 28d), y advertencia explícita de que la optimización de costos y $\text{CO}_2$ se implementa en la capa de negocio analítica.
4. **Saneamiento Integral de Enlaces y Gobernanza:** Erradicación de todos los enlaces `file:///` locales en los 12 reportes de `docs/`, creación de `docs/INDEX.md` y `docs/INFERENCE_OPERATIONAL_RUNBOOK.md`, y actualización exhaustiva de `AGENTS.md`.
5. **Alineación con la Realidad Operativa:** Registro del tiempo de cold start observado (~8.4 s) derivado de la política Scale-to-Zero (`minReplicas = 0`) bajo la cuota gratuita de ACA, y su régimen de respuesta en caliente (~248 ms).

---

## 2. Diagnóstico de Causa Raíz de CI y Resolución de Compatibilidad

### 2.1 Análisis del Fallo en GitHub Actions (Run `42295337947`)
* **Síntoma:** Los 4 jobs de la matriz (`Python 3.10` y `Python 3.13` sobre `ubuntu-latest` y `windows-latest`) fallaban durante la fase de recolección de pruebas con error:
  ```text
  RuntimeError: The starlette.testclient module requires the httpx package to be installed.
  ```
* **Causa Raíz:** `tests/test_api_hardening.py` y `tests/test_api_service.py` importan `from fastapi.testclient import TestClient`. En las versiones modernas de Starlette y FastAPI, `TestClient` encapsula `httpx.Client`. Mientras que en el contenedor de producción `docker/requirements-inference.txt` incluía `httpx==0.28.1`, en el flujo de CI se instalaban exclusivamente:
  ```bash
  pip install -r requirements.txt
  pip install -r requirements-dev.txt
  ```
  Ninguno de estos dos archivos declaraba `httpx`. En la máquina local del desarrollador las pruebas pasaban porque `httpx` se encontraba preinstalado en el intérprete del host, enmascarando la omisión en clones limpios.

### 2.2 Corrección Implementada
1. En `requirements-dev.txt`:
   ```txt
   # Cliente HTTP para pruebas con TestClient (FastAPI / Starlette)
   httpx==0.28.1
   ```
2. En `requirements.txt`:
   Alineación de versiones mínimas de servicios web con el stack del contenedor:
   ```txt
   fastapi>=0.115.6
   starlette>=0.41.3
   ```
3. En `.github/workflows/validate.yml`:
   Se extendió el paso `py_compile` para comprobar la sintaxis de todos los módulos en `src/api/` y `src/inference/`.
4. En `config/project_status.json`:
   Se registró formalmente la incidencia `ISSUE-CI-01` en estado mitigado/resuelto.

---

## 3. Refactorización Declarativa del Estado del Proyecto

### 3.1 Problemas Detectados en `scripts/sync_state.py`
* El generador Markdown contenía bloques de texto rígidos que declaraban "88 pruebas recopiladas (85 pasando y 3 omitidas)", desactualizados respecto a la suite actual de 177 pruebas.
* Las fases 5.6-A, 5.6-B y 5.6-C no figuraban en el orden de fases de la tabla resumen.
* La sección de tareas pendientes listaba las Fases 5, 6 y 7 como no iniciadas, a pesar de que la inferencia, la API y el despliegue cloud ya habían sido completados y certificados.

### 3.2 Refactorización Realizada
* Se rediseñó `render_markdown_state()` para derivar dinámicamente las secciones a partir de la estructura del JSON (`phases`, `cloud_deployment`, `verified_tests`, `completed_milestones`, `pending_tasks`).
* Se incorporó la sección `3.1 Despliegue Operativo en la Nube (Azure Container Apps)` que expone el FQDN, la imagen ACR con digest SHA-256, la Managed Identity y las latencias medidas.
* Se validó la idempotencia matemática con `python scripts/sync_state.py --check` y se aseguraron las 5 pruebas de `tests/test_sync_state.py`.

---

## 4. Auditoría de Documentos y Eliminación de Enlaces Absolutos

Se auditó la totalidad del directorio `docs/` para erradicar referencias `file:///` que provocaban enlaces rotos al ser visualizados en GitHub o clonados en otros sistemas operativos:

| Archivo Modificado | Enlaces Corregidos | Naturaleza del Ajuste |
| :--- | :---: | :--- |
| `docs/CHECKLIST_DEMO_ECOMIX_IA.md` | 2 | Sustitución de rutas absolutas de Windows por relativas |
| `docs/EVALUATION_REPORT.md` | 5 | Enlaces directos a scripts y datasets relativos a la raíz |
| `docs/PHASE_5_3_INFERENCE_ENGINE_REPORT.md` | 1 | Enlace relativo a suite de pruebas |
| `docs/PHASE_5_4_B_REAL_INFERENCE_VALIDATION_REPORT.md` | 5 | Enlaces a reportes JSON y especificaciones de jobs |
| `docs/PHASE_5_5_FASTAPI_SERVICE_REPORT.md` | 1 | Enlace a `tests/test_api_service.py` |
| `docs/PHASE_5_6_A_API_HARDENING_REPORT.md` | 1 | Enlace a `tests/test_api_hardening.py` |
| `docs/PHASE_5_6_B_CONTAINER_VALIDATION_REPORT.md` | 4 | Enlaces a Dockerfile, spec de ACA y middleware |
| `docs/PHASE_5_6_C_0R_ACR_PREP_REPORT.md` | 9 | Enlaces relativos a `.dockerignore` y Dockerfiles |
| `docs/PHASE_5_6_C_0_PRE_EXPENSE_AUDIT_REPORT.md` | 3 | Enlaces a especificaciones y Dockerfile |
| `docs/PHASE_5_6_C_1R_LOCAL_BUILD_REPORT.md` | 2 | Enlaces a requirements y Dockerfile |
| `docs/PHASE_6_4_CLOSING_AND_PR_PREPARATION_REPORT.md` | 7 | Enlaces a guiones, matrices y presentaciones |
| `docs/PORTABILITY_GUIDE.md` | 1 | Enlace a `scripts/doctor.py` |

**Resultado:** 0 ocurrencias de `file:///` restantes en el repositorio.

---

## 5. Nuevos Artefactos Incorporados

### 5.1 `docs/INDEX.md`
Directorio maestro de navegación que indexa y clasifica la totalidad de informes de ingeniería, reportes de evaluación en Azure ML, especificaciones de la API, reportes de despliegue cloud y materiales de presentación.

### 5.2 `docs/INFERENCE_OPERATIONAL_RUNBOOK.md`
Manual técnico de operaciones para Azure Container Apps que detalla:
* Topología serverless en `chilecentral` con Managed Identity `id-ecomix-aca`.
* Análisis y mitigación del cold start (~8.4 s) mediante protocolo de precalentamiento (warm-up).
* Procedimiento de rotación segura de credenciales `X-API-Key` sin indisponibilidad de servicio.
* Matriz de solución de incidencias HTTP (503, 401, 403, 413, 415, 422, 504).
* Guía de contingencia offline con Docker local.

---

## 6. Matriz de Evidencias y Trazabilidad de Capturas

Respecto a las evidencias visuales citadas en [`docs/MATRIZ_EVIDENCIAS_PRESENTACION.md`](MATRIZ_EVIDENCIAS_PRESENTACION.md):
* Las métricas numéricas ($21.96\text{ MPa}$, $31.15\text{ MPa}$, $25.98\text{ MPa}$, $33.61\text{ MPa}$), códigos HTTP (`200 OK`, `422 ProblemDetails`) y latencias en caliente (~248 ms) corresponden a respuestas reales emitidas por el contenedor en Azure Container Apps.
* Los archivos visuales (`01-pagina-principal-navegacion.png` a `07-azure-container-apps-estado.png`) pertenecen a la interfaz gráfica de la plataforma externa **ASP.NET MVC 5** y al Portal de Azure. En estricto apego al principio de veracidad técnica, no se han inventado ni simulado imágenes sintéticas en este repositorio. Dichas capturas deben ser provistas por el operador al compilar el dossier final de presentación.

---

## 7. Resultados de Verificación y Testing

| Comprobación | Comando | Resultado Obtenido |
| :--- | :--- | :--- |
| **Diagnóstico del Sistema** | `python scripts/doctor.py` | ✅ 4 sub-entornos en estado **[PREPARADO]** |
| **Idempotencia de Estado** | `python scripts/sync_state.py --check` | ✅ **[CHECK OK]** Estado perfectamente sincronizado |
| **Suite de Pruebas** | `python -m pytest tests/ -v` | ✅ **177 / 177 pruebas aprobadas (100%)** en 94.7 s |
| **Verificación de Enlaces** | `git grep "file:///" docs/` | ✅ **0 ocurrencias detectadas** |
| **Verificación Git Diff** | `git diff --check` | ✅ Sin espacios en blanco erróneos ni conflictos |

---

## 8. Conclusión y Veredicto

El repositorio `JMedina255/EcoMix-IA-AzureML` ha alcanzado plena coherencia arquitectónica, documental y metodológica.

* **Integración Continua:** La causa raíz del fallo en GitHub Actions ha sido eliminada mediante la especificación rigurosa de dependencias de testing.
* **Gobierno de Datos y Modelos:** Se preserva intacta la inmutabilidad de los datasets procesados (`concrete_test.csv`, SHA-256 `6484d9f1...`) y del modelo ganador (`VotingEnsemble`, SHA-256 `7eaa501c5eeb...`).
* **Veredicto:** **El repositorio queda oficialmente preparado y certificado para la Fase 6.1 (Integración con la plataforma web ASP.NET MVC 5) una vez validada la luz verde en GitHub Actions.**
