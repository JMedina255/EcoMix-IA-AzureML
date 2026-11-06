# Matriz de Trazabilidad de Evidencias y Presentación — EcoMix IA (Fase 6.4)

Este documento certifica la autenticidad, correspondencia técnica y trazabilidad de cada elemento visual y resultado numérico presentado ante el jurado evaluador, vinculándolo directamente con el código fuente y los registros de ejecución en Microsoft Azure.

---

## 1. Matriz Integral de Trazabilidad

| N° Diapo | Archivo de Evidencia Visual | Componente / Archivo Fuente | Código HTTP / Protocolo | Entradas Clave ($\text{kg/m}^3$) | Resultados / Salida Observada | Latencia Observada | Justificación y Propósito Técnico |
|:---:|---|---|---|---|---|:---:|---|
| **D01** | [`01-pagina-principal-navegacion.png`](evidencias-fase-6-3/01-pagina-principal-navegacion.png) | `Views/Shared/_Layout.cshtml`<br/>`Views/Mezclas/Index.cshtml` | `HTTP 200 OK` (HTML) | N/A (Navegación general) | Portal institucional con acceso destacado al nuevo *"Simulador ML"* | < 20 ms (Local) | Demuestra la integración natural del módulo de inferencia en la interfaz de usuario existente sin alterar flujos previos. |
| **D02** | [`02-formulario-simulador-vacio.png`](evidencias-fase-6-3/02-formulario-simulador-vacio.png) | `Views/Mezclas/Simulador.cshtml`<br/>`Models/ViewModels/SimuladorDosificacionViewModel.cs` | `HTTP 200 OK` (HTML) | Formulario listo (7 inputs numéricos en $\text{kg/m}^3$) | Formulario limpio con valores por defecto canónicos, botones de preset y descargo legal visible | < 15 ms (Local) | Evidencia diseño ergonómico, validación HTML5, selector de casos rápidos y aviso explícito sobre el carácter estadístico del modelo. |
| **D05** | [`03-prediccion-convencional-completada.png`](evidencias-fase-6-3/03-prediccion-convencional-completada.png) | `Controllers/MezclasController.cs`<br/>`Services/EcoMixMlClientService.cs`<br/>`ca-ecomix-inference-api` (Azure) | `HTTP 200 OK` (JSON / AJAX) | - Cemento: 280<br/>- Agua: 180<br/>- Grava: 1050<br/>- Arena: 750<br/>- SCM: 0% | - $f'_c\text{ 7d} = \mathbf{21.96\text{ MPa}}$<br/>- $f'_c\text{ 28d} = \mathbf{31.15\text{ MPa}}$<br/>- $w/c = \mathbf{0.643}$<br/>- Advertencias ACI: **0** | **1,002 ms** (Roundtrip total)<br/>(923 ms inferencia Azure) | Valida el Caso Canónico base. Paridad matemática exacta al 100% con la evaluación del modelo serializado VotingEnsemble. |
| **D06** | [`04-prediccion-ecologica-advertencias.png`](evidencias-fase-6-3/04-prediccion-ecologica-advertencias.png) | `Controllers/MezclasController.cs`<br/>`ca-ecomix-inference-api` (FastAPI)<br/>`src/api/routes/prediction.py` | `HTTP 200 OK` (JSON / AJAX) | - Cemento: 150<br/>- Escoria: 100<br/>- Ceniza: 80<br/>- Agua: 165<br/>- SP: 5.0 | - $f'_c\text{ 7d} = \mathbf{25.98\text{ MPa}}$<br/>- $f'_c\text{ 28d} = \mathbf{33.61\text{ MPa}}$<br/>- Sustitución SCM: $\mathbf{54.55\%}$<br/>- **2 Advertencias ACI** activas | **139 ms** (Roundtrip total)<br/>(131 ms inferencia Azure en caliente) | Demuestra cumplimiento de los objetivos de sostenibilidad del Reto 2 de Yura S.A. (> 25 MPa con -46.4% clínker) e interpretación del código ACI PRC-211.1-22. |
| **D07** | [`05-manejo-dosificacion-invalida.png`](evidencias-fase-6-3/05-manejo-dosificacion-invalida.png) | `Controllers/MezclasController.cs`<br/>`Models/ViewModels/SimuladorDosificacionViewModel.cs` | `HTTP 200 OK` (ModelState Inval.) / `HTTP 422` (Remoto) | - Cemento: -10<br/>o Agua: 450 ($w/b = 4.5$) | Banner rojo de alerta con desglose de violaciones físicas/sintácticas | **8 ms** (Local)<br/>**163 ms** (Remoto) | Acredita la doble barrera de contención: la UI no expone trazas de excepción no controladas y orienta al usuario para corregir su diseño. |
| **D04** / **D07** | [`06-resultado-peticion-http.png`](evidencias-fase-6-3/06-resultado-peticion-http.png) | `EcoMixMlClientService.cs`<br/>`Web.Secrets.config`<br/>F12 DevTools Network | `HTTP 200 OK` (REST HTTPS) | Cabeceras y payload JSON de inferencia | `X-API-Key: [REDACTED]`<br/>`Content-Type: application/json`<br/>`X-Request-ID` presente | Variable según estado de réplica | Comprobación DevSecOps: la clave criptográfica se mantiene oculta al usuario y las respuestas siguen la especificación OpenAPI/Swagger. |
| **D04** | [`07-azure-container-apps-estado.png`](evidencias-fase-6-3/07-azure-container-apps-estado.png) | Azure CLI / Portal<br/>`docker/azure-container-app-spec.yaml` | Cloud Telemetry (Azure ARM) | Recurso: `ca-ecomix-inference-api`<br/>Región: `chilecentral` | Estado: `Succeeded`<br/>Réplicas en reposo: **`0`**<br/>Costo de cómputo: **$0.00/h** | N/A (Estado de infraestructura) | Valida el cumplimiento presupuestario: escalado a cero automático para no agotar el crédito de estudiante y despliegue geográfico óptimo. |

---

## 2. Protocolo de Auditoría y Verificación de Autenticidad

1. **Inexistencia de Datos Sintéticos o Respuestas Mock:**
   - La totalidad de las métricas obtenidas ($21.96\text{ MPa}$, $31.15\text{ MPa}$, $25.98\text{ MPa}$, $33.61\text{ MPa}$) provienen del contenedor real `crecomixprod.azurecr.io/ecomix-ml-inference:1.0.0` ejecutando el artefacto VotingEnsemble oficial en Azure Container Apps.
   - No se utilizó ningún simulador falso ni valores cableados (*hardcoded*) en el controlador `MezclasController.cs`.

2. **Auditoría DevSecOps de Secretos:**
   - En ninguna de las 7 capturas ni en los archivos de configuración versionados en Git figura la clave privada de Container Apps.
   - La cadena de conexión y las credenciales se cargan mediante el mecanismo seguro `file="Web.Secrets.config"`, el cual está estrictamente excluido por `.gitignore`.

3. **Gobernanza Normativa:**
   - Las advertencias técnicas del código ACI (`WARN_HIGH_SCM_REPLACEMENT`, `WARN_HIGH_WATER_CEMENT_RATIO`) son generadas analíticamente por el microservicio en Python y deserializadas en C# mediante el DTO `PredictionResponseDto.cs`.
   - El disclaimer legal visible en pantalla asegura la observancia de la NTP 339.034 y ASTM C39.
