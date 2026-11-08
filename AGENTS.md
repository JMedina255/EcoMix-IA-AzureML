# Instrucciones Permanentes para Agentes de Desarrollo — EcoMix IA (Azure ML)

Este documento define el protocolo de actuación, directrices de arquitectura, convenciones de desarrollo y restricciones ineludibles para cualquier agente de inteligencia artificial (o desarrollador) que opere en este repositorio.

---

## 1. Contexto del Sistema EcoMix IA y Alcance del Repositorio

### 1.1 EcoMix IA como Sistema Integral
**EcoMix IA** es una plataforma tecnológica orientada a la sostenibilidad en la industria de la construcción, desarrollada en el marco del **Reto 2 de Yura S.A.** (Hackathon Innova Sur 2026, Universidad Privada de Tacna). Su propósito es predecir la resistencia a la compresión ($f'_c$ en MPa) a **7 y 28 días** en dosificaciones de concreto ecológico y convencional mediante sustitución de clínker por puzolana y escoria de alto horno, conforme a las normas técnicas peruanas (NTP) y el código **ACI PRC-211.1-22**.

### 1.2 Límites de Responsabilidad del Repositorio (`JMedina255/EcoMix-IA-AzureML`)
Este repositorio contiene **exclusivamente el núcleo de Machine Learning y su integración con Microsoft Azure**:
1. Adquisición y validación del dataset estándar ([UCI Machine Learning Repository ID: 165](https://archive.ics.uci.edu/dataset/165/concrete+compressive+strength)).
2. Preprocesamiento, partición determinística 80/20 (`seed=42`) y registro de Data Assets en Azure ML.
3. Orquestación y gobernanza del entrenamiento AutoML en Azure ML (`cpu-cluster-ecomix`).
4. Inspección segura, descarga selectiva y evaluación independiente de modelos.
5. Microservicio REST de inferencia dual (7 y 28 días) con FastAPI, contenedorizado en Docker y desplegado en Azure Container Apps (ACA en `chilecentral`).

> [!IMPORTANT]
> **Aislamiento de Responsabilidades:** La plataforma web cliente (ASP.NET MVC 5), persistencia relacional SQL Server, gestión de usuarios, generación de dossiers PDF y el **cálculo analítico de optimización de costos ($\text{S/./m}^3$) y reducción de $\text{CO}_2$ ($\text{kg CO}_2\text{e/m}^3$)** son responsabilidades de la plataforma frontend/backend descritas en los documentos de ingeniería, no de este repositorio de Machine Learning.

### 1.3 Relación con los Documentos de Ingeniería (FD02 y FD03)
- 📑 [**FD02-EPIS — Informe de Visión (v1.0)**](docs/FD02-EPIS-Informe_Vision_EcoMixIA.md): Define el alcance, necesidades de interesados, aislamiento físico del predictor ML (UCI 165), fórmulas analíticas de sostenibilidad y precedencia de desarrollo (P1 MVP $\rightarrow$ P2 Demostración $\rightarrow$ P3 Azure).
- 📋 [**FD03-EPIS — Especificación de Requerimientos de Software - SRS (v0.1)**](docs/FD03-EPIS-Informe_SRS_EcoMixIA_v0.1.md): Formaliza el levantamiento de procesos, los 10 requerimientos no funcionales bajo **ISO/IEC 25010** (latencia $< 2\text{ s}$, optimización $< 10\text{ s}$, integridad de datos N09) y las reglas de negocio **RN-01 a RN-12**.
- 🌐 [**Portal Archify 3.2**](docs/archify/index.html): Diagramas arquitectónicos (D02 Arquitectura General, D03 Flujo del Ingeniero).
- 🧭 [**Índice General de Documentación**](docs/INDEX.md): Catálogo completo de reportes técnicos, bitácoras y especificaciones del repositorio.

---

## 2. Procedimiento Obligatorio al Iniciar una Sesión Nueva

Todo agente IDE que inicie una sesión de trabajo debe ejecutar rigurosamente el siguiente protocolo antes de proponer cambios o modificar código:

```bash
# 1. Verificar el estado del árbol de trabajo local
git status

# 2. Sincronizar referencias remotas de forma segura
git fetch origin

# 3. Si se encuentra en la rama principal main:
# git pull --ff-only origin main
# Si se encuentra en una rama de trabajo (feature/fix/docs):
# git pull --ff-only origin <nombre-de-rama> (si tiene seguimiento remoto)

# 4. Diagnosticar la integridad del entorno local y componentes del sistema
python scripts/doctor.py

# 5. Comprobar la sincronización del estado declarativo
python scripts/sync_state.py --check
```

Adicionalmente, el agente debe:
- Consultar el archivo de estado vivo: [`docs/PROJECT_STATE.md`](docs/PROJECT_STATE.md) (y la configuración declarativa [`config/project_status.json`](config/project_status.json)) para conocer la fase actual y el próximo hito autorizado.
- Comprobar las incidencias técnicas abiertas antes de reintentar operaciones conocidas que fallen.

---

## 3. Restricciones y Reglas Ineludibles para Agentes

### 3.1 Prohibición de Nuevos Entrenamientos y Cómputo Azure
- **NUNCA ejecutar `src/train_automl.py` ni lanzar nuevos trabajos de entrenamiento en Azure ML** a menos que el usuario lo solicite explícitamente por escrito. El job ganador `wheat_cheese_4swj34tkjn` ya concluyó exitosamente.
- **PROHIBIDO crear recursos de cómputo, clústeres adicionales o consumir cuota de suscripción de Azure** sin autorización explícita y previa del usuario.
- **PROHIBIDO construir, etiquetar o publicar imágenes de contenedor hacia Azure Container Registry (ACR)** o modificar la configuración de Azure Container Apps sin autorización explícita. El despliegue de Fase 5.6-C ya se encuentra completado y validado en `chilecentral`.

### 3.2 Seguridad y Secretos
- **PROHIBIDO subir credenciales, tokens o suscripciones al repositorio:**
  - El archivo `config.json` está en `.gitignore` y no debe versionarse bajo ninguna circunstancia.
  - Usar siempre `config.example.json` como plantilla pública con identificadores dummy.
  - Nunca imprimir secrets, claves de API (`X-API-Key`), claves de almacenamiento o tokens en logs, commits o salidas versionadas.
  - No recuperar ni exponer API Keys en el diálogo ni en la documentación.

### 3.3 Artefactos Binarios y Entornos Virtuales
- **PROHIBIDO commitear modelos binarios o entornos:**
  - Archivos `.pkl`, `.joblib`, `.onnx` o carpetas de entornos (`.venv/`, `venv/`, `env/`) no deben agregarse a Git (controlados por `.gitignore`).
  - La procedencia del modelo ganador se audita por sus metadatos en Azure ML (`azureml_wheat_cheese_4swj34tkjn_11_output_mlflow_log_model_873731674:1`) y su digest SHA-256 (`7eaa501c5eeb...`), no por su binario en el árbol de Git.

### 3.4 Compatibilidad de Entorno y Runtime
- El entorno local y de integración continua (CI) soporta **Python 3.10 a 3.13.x** para tareas de desarrollo, análisis y testing de la plataforma.
- El modelo AutoML de Azure ML (`VotingEnsemble`) fue serializado específicamente en **Python 3.10.19** con Scikit-learn 1.5.1 y MLflow 2.15.1.
- El contenedor oficial de producción ejecuta la imagen curada `mcr.microsoft.com/azureml/curated/ai-ml-automl:41` (Python 3.10.19), garantizando compatibilidad binaria absoluta.
- Mantener estrictamente desacopladas las herramientas de desarrollo general del runtime de inferencia especializado; nunca intentar conversiones no auditadas del binario.
- No alterar instalaciones globales del sistema operativo ni intentar desinstalar/reinstalar versiones de Python a nivel de máquina.

---

## 4. Convenciones de Desarrollo, Ramas y Commits Atómicos

1. **Gobernanza de Ramas:**
   - `main`: Rama protegida y estable. Solo recibe cambios mediante Pull Requests aprobados con CI verde.
   - `feat/<nombre>`: Nuevas funcionalidades o endpoints.
   - `fix/<nombre>`: Correcciones de bugs o dependencias.
   - `docs/<nombre>`: Documentación, sincronización de estado y guías técnicas.
   - **NUNCA hacer force push (`git push -f`), reset destructivo (`git reset --hard`) ni merges directos sin revisión a `main`.**

2. **Commits Atómicos y Claros:**
   - Cada commit debe resolver una unidad lógica de trabajo siguiendo la convención Conventional Commits:
     - `feat:` nueva funcionalidad o script.
     - `fix:` corrección de errores o compatibilidad.
     - `docs:` documentación y guías.
     - `test:` adición o refuerzo de suites de pruebas.
     - `refactor:` reestructuración sin cambio de comportamiento.
     - `ci:` flujos de integración continua.

3. **Ejecución de Pruebas Previa al Commit:**
   - Todo cambio en `src/`, `scripts/` o dependencias debe validarse con la suite completa de pruebas:
     ```bash
     python -m pytest tests/ -v
     ```
   - No realizar commits si alguna prueba falla o si existen advertencias no controladas.

4. **Mantenimiento de Documentación Viva:**
   - Si un cambio en el código altera parámetros, dependencias o el estado de una fase, debe actualizarse la configuración declarativa [`config/project_status.json`](config/project_status.json) y regenerar el documento vivo:
     ```bash
     python scripts/sync_state.py
     python scripts/sync_state.py --check
     ```

---

## 5. Carga Manual de este Documento en Diferentes IDEs / Agentes

Si opera en un agente que no carga automáticamente este contexto:
- **Antigravity / Gemini CLI:** Carga este archivo automáticamente por las reglas de proyecto. En subsesiones, invoque: *«Lee AGENTS.md y adopta el rol y las restricciones descritas antes de continuar.»*
- **Cursor / VS Code:** Añada `Follow all instructions and constraints established in @AGENTS.md` en los System Instructions o adjunte `@AGENTS.md` en el primer prompt.
- **Claude Dev / Aider / Windsurf:** Inicie la sesión con `/add AGENTS.md` o referéncielo en `.windsurfrules`.

---

## 6. Estado Actual y Próximo Hito Autorizado

* **Fase Actual:** **Fase 6.4 — Cierre Documental Definitivo y Congelamiento del Repositorio ML** (completada y auditada).
* **Hitos Completados:**
  - Fases 1 a 4.5: Pipeline AutoML en Azure ML, evaluación independiente en nube ($R^2 = 0.9121$, $\text{RMSE} = 4.7592\text{ MPa}$) y consolidación de reportes.
  - Fase 5: Servicio de inferencia dual 7d/28d y API REST FastAPI con paridad determinística ($|\Delta| = 0.0\text{ MPa}$).
  - Fase 5.6-A/B/C: Endurecimiento DevSecOps, contenedorización y despliegue en Azure Container Apps (`ca-ecomix-inference-api` en `chilecentral`) con Managed Identity (`id-ecomix-aca`) y latencia en caliente de ~248 ms.
  - Fase 6.4: Estabilización de CI en GitHub Actions (4 jobs en verde, Run 42527034654 posterior al merge `5d12792`), saneamiento de contratos JSON, runbook operativo y cierre documental integral.
* **Próximo Hito Técnico Autorizado:**
  - **Repositorio ML Congelado y en Producción:** Este repositorio actúa como referencia técnica, pipeline reproducible y microservicio en Azure Container Apps. La **Fase 6.1 (Integración con Plataforma Web ASP.NET MVC 5)** y la optimización analítica de costos y $\text{CO}_2$ se implementan exclusivamente en el repositorio cliente externo (`joeguillenl/EcomixIA`).
