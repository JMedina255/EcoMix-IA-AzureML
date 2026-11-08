# 🧭 Índice Maestro de Documentación Técnica — EcoMix IA

Este documento constituye el índice canónico de navegación para toda la arquitectura, especificaciones de ingeniería, reportes de experimentación, bitácoras de despliegue y guías operativas del proyecto **EcoMix IA (Azure ML)**.

---

## 📑 1. Documentos Fundacionales de Ingeniería de Software

Documentación formal elaborada bajo metodología RUP / estándares EPIS para el Reto 2 de Yura S.A. (Hackathon Innova Sur 2026):

* [**FD02-EPIS — Informe de Visión del Proyecto (v1.0)**](FD02-EPIS-Informe_Vision_EcoMixIA.md)  
  *Alcance general, modelo de negocio, necesidades de interesados, aislamiento físico del predictor ML (UCI 165), fórmulas analíticas de sostenibilidad y precedencia de desarrollo (P1 MVP $\rightarrow$ P2 Demostración $\rightarrow$ P3 Azure).*
* [**FD03-EPIS — Especificación de Requerimientos de Software - SRS (v0.1)**](FD03-EPIS-Informe_SRS_EcoMixIA_v0.1.md)  
  *Formalización de requerimientos funcionales (RF-01 a RF-12), 10 requerimientos no funcionales bajo norma **ISO/IEC 25010** (latencia $< 2\text{ s}$, optimización $< 10\text{ s}$, integridad N09), reglas de negocio **RN-01 a RN-12** y casos de uso.*
* [**Portal Interactivo de Arquitectura (Archify 3.2)**](archify/index.html)  
  *Diagramas navegables D02 (Arquitectura General del Sistema) y D03 (Flujo del Ingeniero de Mezclas).*

---

## 📊 2. Trazabilidad Viva y Gobernanza del Proyecto

* [**Estado Vivo del Proyecto (`docs/PROJECT_STATE.md`)**](PROJECT_STATE.md)  
  *Documento vivo de trazabilidad técnica derivado declarativamente de [`config/project_status.json`](../config/project_status.json). Mantiene el registro de fases, métricas oficiales de Azure ML, estado de pruebas y tareas pendientes.*
* [**Guía de Gobernanza y Reglas para Agentes (`AGENTS.md`)**](../AGENTS.md)  
  *Protocolos ineludibles de inicio de sesión, prohibiciones estrictas de reentrenamiento y cómputo no autorizado, política de secretos y convenciones de ramas Git.*
* [**Guía de Portabilidad y Diagnóstico**](PORTABILITY_GUIDE.md)  
  *Instrucciones de reproducibilidad sin dependencias globales y uso del script `scripts/doctor.py`.*

---

## 🔬 3. Experimentación AutoML y Evaluación de Modelos (Fases 1 a 4)

* [**Reporte Oficial de Evaluación Técnica del Modelo**](EVALUATION_REPORT.md)  
  *Evaluación ciega sobre el conjunto de prueba independiente de 206 observaciones en Azure ML (Job `stoic_pot_x25ht98nv7`). Análisis detallado de $R^2 = 0.9121$, $\text{RMSE} = 4.7592\text{ MPa}$, $\text{MAE} = 3.2822\text{ MPa}$, $\text{NRMSE} = 0.0673$, subconjunto sin solapamiento (195 muestras) y desglose a 7 y 28 días.*
* [**Reporte JSON de Evaluación Oficial**](../reports/evaluation_wheat_cheese_4swj34tkjn.json)  
  *Métricas brutas, metadatos del job y predicciones completas exportadas por el CommandJob en Azure ML.*

---

## ⚡ 4. Servicio de Inferencia y Endurecimiento DevSecOps (Fases 5 a 5.6-B)

* [**Fase 5.3 — Informe del Motor de Inferencia Multi-Edad**](PHASE_5_3_INFERENCE_ENGINE_REPORT.md)  
  *Diseño del motor `InferenceEngine`, desacoplamiento del SDK de Azure ML y soporte simultáneo para inferencia dual a 7 y 28 días.*
* [**Fase 5.4-B — Validación de Inferencia Real en Azure ML**](PHASE_5_4_B_REAL_INFERENCE_VALIDATION_REPORT.md)  
  *Ejecución remota en Azure ML (Job `serene_spinach_sn7khxvkq7`) que certifica paridad determinística absoluta ($|\Delta| = 0.0\text{ MPa}$) con el modelo ganador `VotingEnsemble`.*
* [**Fase 5.5 — Microservicio REST con FastAPI**](PHASE_5_5_FASTAPI_SERVICE_REPORT.md)  
  *Arquitectura del microservicio, endpoints `/health/live`, `/health/ready` y `/api/v1/predict/concrete-strength`, autenticación `X-API-Key` y contratos RFC 7807.*
* [**Fase 5.6-A — Endurecimiento DevSecOps de la API**](PHASE_5_6_A_API_HARDENING_REPORT.md)  
  *Mitigación de timing attacks con `secrets.compare_digest`, prohibición de claves públicas en producción, aislamiento por instancia y control de flujo en middleware.*
* [**Fase 5.6-B — Verificación del Contenedor Docker**](PHASE_5_6_B_CONTAINER_VALIDATION_REPORT.md)  
  *Construcción sobre la imagen curada oficial `mcr.microsoft.com/azureml/curated/ai-ml-automl:41` (Python 3.10.19) y manifest de Azure Container Apps.*

---

## ☁️ 5. Despliegue en la Nube y Operación Cloud (Fase 5.6-C)

* [**Fase 5.6-C.0 — Auditoría Previa de Costos y Recursos**](PHASE_5_6_C_0_PRE_EXPENSE_AUDIT_REPORT.md)  
  *Análisis financiero preventivo, dimensionamiento de cuotas y estimación de gasto cero bajo cuota gratuita de Azure Container Apps.*
* [**Fase 5.6-C.0R — Preparación y Corrección de Contexto ACR**](PHASE_5_6_C_0R_ACR_PREP_REPORT.md)  
  *Blindaje de `.dockerignore` raíz, eliminación de credenciales de administración en ACR y diseño de Managed Identity.*
* [**Fase 5.6-C.1R — Construcción Local y Prueba del Contenedor**](PHASE_5_6_C_1R_LOCAL_BUILD_REPORT.md)  
  *Construcción de imagen local y verificación del empaquetado de dependencias web sin alterar el runtime de AutoML.*
* [**Fase 5.6-C.2 — Publicación de Imagen en Azure Container Registry**](PHASE_5_6_C_2_ACR_PUBLICATION_REPORT.md)  
  *Certificación de la imagen `crecomixprod.azurecr.io/ecomix-ml-inference:1.0.0` y registro de digest OCI.*
* [**Fase 5.6-C.3 — Despliegue Operativo en Azure Container Apps**](PHASE_5_6_C_3_ACA_DEPLOYMENT_REPORT.md)  
  *Despliegue de `ca-ecomix-inference-api` en `chilecentral`, asignación de Managed Identity `id-ecomix-aca`, configuración de política Scale-to-Zero (`minReplicas=0`) y verificación en caliente (~248 ms).*
* [**Runbook Operativo de Inferencia**](INFERENCE_OPERATIONAL_RUNBOOK.md)  
  *Manual de operaciones cloud: monitoreo de logs, mitigación de cold start (~8.4 s), rotación de claves, solución de errores HTTP y contingencia offline.*

---

## 🤝 6. Integración Externa y Presentación (Fases 6.1 a 6.4)

* [**Plan de Integración con la Plataforma Web ASP.NET MVC 5 (Fase 6.1)**](PHASE_6_1_MVC_INTEGRATION_PLAN.md)  
  *Arquitectura de integración desacoplada, especificación de contratos C# / DTOs, clase `EcoMixInferenceClient`, inyección de dependencias y políticas de reintento Polly.*
* [**Guion Técnico de Exposición Oral (3 Minutos)**](GUION_EXPOSICION_ECOMIX_IA.md)  
  *Estructura cronometrada (180 s) para defensa ante jurado técnico, enfatizando el Reto 2 de Yura S.A. y el rol de Azure ML.*
* [**Estructura Proyectable de Diapositivas**](PRESENTACION_ECOMIX_IA_AVANCE.md)  
  *Contenido textual para 8 diapositivas de avance, métricas oficiales y esquemas de arquitectura.*
* [**Matriz de Evidencias de Presentación**](MATRIZ_EVIDENCIAS_PRESENTACION.md)  
  *Trazabilidad cruzada entre afirmaciones de diapositivas, capturas de pantalla, códigos HTTP y métricas comprobadas.*
* [**Checklist Pre-Demo**](CHECKLIST_DEMO_ECOMIX_IA.md)  
  *Protocolo de verificación técnica (T-15 min y T-5 min pre-calentamiento cloud) para asegurar latencia $< 2\text{ s}$ ante el jurado.*
* [**Informe de Cierre Documental y Recuperación de CI (Fase 6.4-D)**](PHASE_6_4_D_DOCUMENTATION_CLOSURE.md)  
  *Auditoría de dependencias, solución a errores de colección de TestClient en CI, refactorización declarativa y balance antes/después.*
