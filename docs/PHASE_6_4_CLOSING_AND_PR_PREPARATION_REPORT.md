# Informe de Cierre, Evidencias y Preparación de Sustentación — Fase 6.4

**Repositorio ML:** `JMedina255/EcoMix-IA-AzureML` (Rama: `fix/phase-05-api-hardening`)  
**Repositorio Web:** `joeguillenl/EcomixIA` (Rama: `feat/integration-fastapi-service`)  
**Servicio Cloud:** `ca-ecomix-inference-api` en Azure Container Apps (`chilecentral`)  
**Fecha:** Noviembre 2026  
**Veredicto:** **FASE 6.4 COMPLETADA AL 100% — DEMO ACADÉMICA REPRODUCIBLE Y PAQUETES DE PULL REQUEST PREPARADOS**

---

## 1. Resumen Ejecutivo y Auditoría Inicial

En la Fase 6.4 se consolidó el cierre documental integral de la plataforma **EcoMix IA** previa a la sustentación académica del **Reto 2 de Yura S.A.** (Hackathon Innova Sur 2026).

### 1.1 Estado de los Repositorios:
- **`joeguillenl/EcomixIA` (Web ASP.NET MVC 5):**
  - Rama: `feat/integration-fastapi-service` (partiendo de `master` en commit `07a7d73`).
  - HEAD base: `7964a9a` (`feat(validation): refine json serialization and add visual evidence assets for demo`).
  - Estado: Árbol de trabajo listo para commit atómico documental. Compilación exitosa en MSBuild 17.14 (0 errores, 0 advertencias).
- **`JMedina255/EcoMix-IA-AzureML` (ML Core & Azure ML):**
  - Rama: `fix/phase-05-api-hardening` (partiendo de `main`).
  - HEAD base: `c4765db` (`docs(integration): document asp.net mvc 5 integration plan and demo evidence matrix`).
  - Estado: Árbol de trabajo listo para commit atómico documental. Suite completa de 177 pruebas unitarias e integración aprobadas al 100% (`177 passed in 94.38s`).

### 1.2 Integridad de Infraestructura y Modelos:
- Se respetó la prohibición de nuevos entrenamientos y consumos de cómputo en Azure ML.
- El modelo oficial `VotingEnsemble` (670 KB, SHA-256 verificado `294101e4a520...`) y el dataset UCI 165 (1,030 filas) permanecen inmutables.
- El servicio en la nube `ca-ecomix-inference-api` se mantiene en estado `Succeeded` con escalado a cero réplicas activo.

---

## 2. Correcciones Críticas al Guion y Diagrama de Secuencia

En las fases preliminares se detectaron inconsistencias conceptuales que fueron rigurosamente subsanadas en [`docs/GUION_EXPOSICION_ECOMIX_IA.md`](file:///C:/Users/Admin/Desktop/Proyectos/ML%20EcomixIA%20Sistema/docs/GUION_EXPOSICION_ECOMIX_IA.md) y [`docs/PRESENTACION_ECOMIX_IA_AVANCE.md`](file:///C:/Users/Admin/Desktop/Proyectos/ML%20EcomixIA%20Sistema/docs/PRESENTACION_ECOMIX_IA_AVANCE.md):

1. **Separación de Niveles de Validación:**
   - **Validación Local (ASP.NET MVC / C#):** Intercepción sintáctica inmediata mediante DataAnnotations y `ModelState.IsValid` (ej. Cemento = -10 kg/m³). Se procesa en el servidor IIS en **~8 ms sin realizar llamadas a la red ni consumir saldo en Azure**.
   - **Validación Remota (FastAPI / Azure):** Validadores Pydantic que interceptan transgresiones a las leyes de tecnología del concreto (ej. agua excesiva $w/b > 4.0$). Responde con **HTTP 422 Unprocessable Entity** bajo la especificación **RFC 7807 ProblemDetails** en **~163 ms**.
2. **Eliminación de Ambigüedades sobre Certificación Estructural:**
   - Se erradicó cualquier afirmación que sugiera que el modelo "certifica la resistencia de la estructura" o "reemplaza los ensayos de laboratorio".
   - **Declaración Normativa:** Las predicciones del VotingEnsemble ($R^2=0.912$) representan **estimaciones estadísticas orientativas de soporte a la decisión**. De acuerdo con la **NTP 339.034**, **E.060**, **ACI 318** y **ASTM C39**, es legal y técnicamente obligatorio realizar roturas destructivas de probetas cilíndricas normalizadas bajo la supervisión de un ingeniero colegiado.
   - Las advertencias ACI (`WARN_HIGH_SCM_REPLACEMENT`, `WARN_HIGH_WATER_CEMENT_RATIO`) guían el diseño, advirtiendo sobre la necesidad de mayor curado húmedo, pero no suplen la validación experimental.
3. **Transparencia en la Estructura de Costos Cloud:**
   - Se diferenció el **costo de cómputo en reposo ($0.00 USD/h)** debido al escalado a cero réplicas (`minReplicas = 0`) en Azure Container Apps Consumption, del **costo recurrente de almacenamiento** en Azure Container Registry (`crecomixprod`, SKU Basic), el cual asciende a aproximadamente **$0.167 USD/día (~$5.00 USD/mes)** mientras la imagen permanezca alojada.
4. **Diferenciación de Latencias (Cold vs Warm Start):**
   - El guion y la presentación explicitan que el primer arranque desde cero réplicas toma entre **8.4 y 8.8 segundos** (cold start), mientras que las inferencias sucesivas con el contenedor activo responden en **130 a 150 milisegundos** (warm start).

---

## 3. Auditoría de Evidencias Visuales

Se auditó el catálogo de 7 capturas de pantalla ubicadas en [`docs/evidencias-fase-6-3/`](file:///C:/Users/Admin/Desktop/Proyectos/ML%20EcomixIA%20Sistema/docs/evidencias-fase-6-3/):

| Archivo | Dimensión / Peso | Verificación de Autenticidad | Verificación DevSecOps |
|---|---|---|---|
| `01-pagina-principal-navegacion.png` | 135.9 KB | Portal institucional con enlace al Simulador ML | Sin credenciales expuestas |
| `02-formulario-simulador-vacio.png` | 145.2 KB | 7 inputs en kg/m³, preset buttons, descargo ético | Sin credenciales expuestas |
| `03-prediccion-convencional-completada.png` | 182.7 KB | Caso A: 280 kg cto $\rightarrow$ 21.96 / 31.15 MPa, a/c 0.643 | Paridad 100% con VotingEnsemble oficial |
| `04-prediccion-ecologica-advertencias.png` | 198.0 KB | Caso B: 150 cto + 180 SCM $\rightarrow$ 25.98 / 33.61 MPa + 2 ACI | Cumplimiento Reto 2 Yura verificado |
| `05-manejo-dosificacion-invalida.png` | 137.5 KB | Banner rojo con errores detallados | Manejo robusto sin caídas de UI |
| `06-resultado-peticion-http.png` | 66.4 KB | Inspección DevTools con POST 200 y JSON sanitizado | `X-API-Key: [REDACTED]` confirmado |
| `07-azure-container-apps-estado.png` | 55.9 KB | Consola Azure CLI: `ca-ecomix-inference-api` Succeeded | 0 réplicas en reposo ($0.00 cómputo) |

Todos los archivos fueron trazados uno a uno en la [Matriz de Trazabilidad](file:///C:/Users/Admin/Desktop/Proyectos/ML%20EcomixIA%20Sistema/docs/MATRIZ_EVIDENCIAS_PRESENTACION.md).

---

## 4. Paquete de Presentación Entregado

Se estructuraron y versionaron los cuatro documentos clave:
1. [`PRESENTACION_ECOMIX_IA_AVANCE.md`](file:///C:/Users/Admin/Desktop/Proyectos/ML%20EcomixIA%20Sistema/docs/PRESENTACION_ECOMIX_IA_AVANCE.md): Ocho diapositivas proyectables con poco texto, métricas claras, diagramas de arquitectura y capturas reales.
2. [`GUION_EXPOSICION_ECOMIX_IA.md`](file:///C:/Users/Admin/Desktop/Proyectos/ML%20EcomixIA%20Sistema/docs/GUION_EXPOSICION_ECOMIX_IA.md): Guion cronometrado para una intervención técnica y demostración de 3 minutos exactos (180 s), con pautas claras de qué decir y qué evitar.
3. [`MATRIZ_EVIDENCIAS_PRESENTACION.md`](file:///C:/Users/Admin/Desktop/Proyectos/ML%20EcomixIA%20Sistema/docs/MATRIZ_EVIDENCIAS_PRESENTACION.md): Mapeo bidireccional entre diapositivas, capturas, componentes C#/Python, códigos HTTP y justificación técnica.
4. [`CHECKLIST_DEMO_ECOMIX_IA.md`](file:///C:/Users/Admin/Desktop/Proyectos/ML%20EcomixIA%20Sistema/docs/CHECKLIST_DEMO_ECOMIX_IA.md): Guía de preflight (T-15 min), calentamiento opcional de contenedor (T-5 min), ejecución secuencial y plan de contingencia offline.

---

## 5. Análisis de Cambios Git y Preparación de Pull Requests

### 5.1 Repositorio Web (`joeguillenl/EcomixIA`)
- **Rama Origen:** `feat/integration-fastapi-service`
- **Rama Destino:** `master`
- **Commits a Incorporar:** 6 commits (desde `810e0bf` hasta el commit documental de Fase 6.4).
- **Archivos Incluidos:**
  - `Controllers/MezclasController.cs`: Acciones `Simulador` (GET/POST) y `SimularAjax` (POST JSON).
  - `Services/EcoMixMlClientService.cs`, `IEcoMixMlClientService.cs`, `EcoMixMlClientException.cs`: Cliente HTTP estático desacoplado, compresión GZip, timeout 45s, mapeo RFC 7807.
  - `Models/Dtos/*.cs`: DTOs de petición, respuesta y detalles de problemas.
  - `Models/ViewModels/SimuladorDosificacionViewModel.cs`: ViewModel para renderizado Razor.
  - `Views/Mezclas/Simulador.cshtml`: Interfaz interactiva de simulación con validación JavaScript/CSRF.
  - `Views/Shared/_Layout.cshtml`, `Views/Mezclas/Index.cshtml`: Accesos directos al simulador.
  - `Web.Secrets.example.config`: Plantilla pública de configuración sin credenciales.
  - `Web.config`, `EcomixIA.csproj`, `packages.config`, `.gitignore`: Ajustes para Newtonsoft.Json y exclusión de `Web.Secrets.config`.
  - `docs/evidencias-fase-6-3/*.png`: 7 capturas de pantalla de la validación visual.
  - `docs/*.md`: 4 documentos de presentación, guion, matriz y checklist.
- **Auditoría de Seguridad:** Ninguna clave o secreto se incluye en el control de versiones. `Web.Secrets.config` permanece fuera de Git.
- **Propuesta de PR:**
  - **Título:** `feat(ml-integration): simulador interactivo de resistencia y conexión con servicio azure container apps`
  - **Tipo:** `feat` (Nueva funcionalidad de valor de negocio).

### 5.2 Repositorio ML (`JMedina255/EcoMix-IA-AzureML`)
- **Rama Origen:** `fix/phase-05-api-hardening`
- **Rama Destino:** `main`
- **Commits a Incorporar:** 10 commits (desde `174c6dc` hasta el commit documental de Fase 6.4).
- **Archivos Incluidos:**
  - `docker/Dockerfile`, `docker/requirements-inference.txt`, `docker/azure-container-app-spec.yaml`: Especificación de contenedor y despliegue ACA.
  - `.dockerignore`, `docker/.dockerignore`, `docker/Dockerfile.dockerignore`: Aislamiento estricto del contexto de construcción (modelo 670 KB incluido, datasets y secretos excluidos).
  - `src/api/config.py`, `src/api/dependencies.py`, `src/api/main.py`, `src/api/middleware.py`, `src/api/routes/health.py`: Securización de FastAPI, CORS, autenticación por API Key, middleware de límite de cuerpo y ciclo de vida de disponibilidad.
  - `tests/test_api_hardening.py`: 15 pruebas de seguridad y hardening (177 pruebas totales aprobadas).
  - `docs/PHASE_5_6_*.md`, `docs/PHASE_6_*.md`: Trazabilidad completa de auditoría previa al gasto, publicación ACR, despliegue ACA e integración MVC.
- **Auditoría de Seguridad:** Sin binarios `.pkl`, sin `config.json`, sin credenciales de Azure.
- **Propuesta de PR:**
  - **Título:** `feat(api-hardening-aca): securización de api fastapi, empaquetado docker y despliegue serverless en azure container apps chilecentral`
  - **Tipo:** `feat` (Infraestructura, seguridad y despliegue cloud).

---

## 6. Plan de Contingencia para la Demostración

Si ocurre una falla total de conectividad en el aula:
1. **Contingencia 1:** Abrir el portal offline interactivo [`docs-interactive/index.html`](file:///C:/Users/Admin/Desktop/Proyectos/ML%20EcomixIA%20Sistema/docs-interactive/index.html) para explicar la arquitectura general y el flujo del ingeniero.
2. **Contingencia 2:** Abrir la galería verificada en [`docs/evidencias-fase-6-3/`](file:///C:/Users/Admin/Desktop/Proyectos/ML%20EcomixIA%20Sistema/docs/evidencias-fase-6-3/) y proyectar las capturas reales de ejecución.
3. **Compromiso Ético:** No falsificar respuestas con JavaScript mock ni alterar datos en caliente.

---

## 7. Dictamen Final y Recomendación

Se recomienda al equipo:
1. Realizar los commits atómicos documentales en ambas ramas locales.
2. Presentar la demostración siguiendo el [`CHECKLIST_DEMO_ECOMIX_IA.md`](file:///C:/Users/Admin/Desktop/Proyectos/ML%20EcomixIA%20Sistema/docs/CHECKLIST_DEMO_ECOMIX_IA.md).
3. Tras la aprobación del jurado o del líder del proyecto, proceder con la apertura y fusión controlada de los Pull Requests hacia `master` y `main` respectivamente.
