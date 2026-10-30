# Instrucciones Permanentes para Agentes de Desarrollo — EcoMix IA (Azure ML)

Este documento define el protocolo de actuación, directrices de arquitectura, convenciones de desarrollo y restricciones ineludibles para cualquier agente de inteligencia artificial (o desarrollador) que opere en este repositorio.

---

## 1. Contexto del Sistema EcoMix IA y Alcance del Repositorio

### 1.1 EcoMix IA como Sistema Integral
**EcoMix IA** es una plataforma tecnológica orientada a la sostenibilidad en la industria de la construcción, desarrollada en el marco del **Reto 2 de Yura S.A.** (Hackathon Innova Sur 2026, Universidad Privada de Tacna). Su propósito es optimizar dosificaciones de concreto ecológico minimizando el costo ($\text{S/./m}^3$) y la huella de carbono ($\text{kg CO}_2\text{e/m}^3$) mediante sustitución de clínker por puzolana y escoria, garantizando la resistencia a compresión (MPa) conforme a las normas técnicas peruanas (NTP) y el código **ACI PRC-211.1-22**.

### 1.2 Límites de Responsabilidad del Repositorio (`JMedina255/EcoMix-IA-AzureML`)
Este repositorio contiene **exclusivamente el núcleo de Machine Learning y su integración con Microsoft Azure ML**. Sus responsabilidades abarcan:
1. Adquisición y validación del dataset estándar (UCI Machine Learning Repository, ID 165).
2. Preprocesamiento, partición determinística 80/20 y registro de Data Assets en Azure ML.
3. Orquestación y gobernanza del entrenamiento AutoML en Azure ML (`cpu-cluster-ecomix`).
4. Inspección segura, descarga selectiva y evaluación independiente de modelos.
5. Exportación del pipeline de inferencia para consumo de la plataforma web.

> [!IMPORTANT]
> La interfaz gráfica web (MVC / Streamlit), persistencia relacional SQL, gestión de usuarios y generación de dossiers PDF son responsabilidades de las plataformas frontend/backend descritas en los documentos de ingeniería, no de este repositorio de experimentación ML.

### 1.3 Relación con los Documentos de Ingeniería (FD02 y FD03)
- 📑 [**FD02-EPIS — Informe de Visión (v1.0)**](docs/FD02-EPIS-Informe_Vision_EcoMixIA.md): Define el alcance, necesidades de interesados, aislamiento físico del predictor ML (UCI 165), fórmulas analíticas de sostenibilidad y precedencia de desarrollo (P1 MVP $\rightarrow$ P2 Demostración $\rightarrow$ P3 Azure).
- 📋 [**FD03-EPIS — Especificación de Requerimientos de Software - SRS (v0.1)**](docs/FD03-EPIS-Informe_SRS_EcoMixIA_v0.1.md): Formaliza el levantamiento de procesos, los 10 requerimientos no funcionales bajo **ISO/IEC 25010** (latencia $< 2\text{ s}$, optimización $< 10\text{ s}$, integridad de datos N09) y las reglas de negocio **RN-01 a RN-12**.
- 🌐 [**Portal Archify 3.2**](docs/archify/index.html): Diagramas arquitectónicos (D02 Arquitectura General, D03 Flujo del Ingeniero).

---

## 2. Procedimiento Obligatorio al Iniciar una Sesión Nueva

Todo agente IDE que inicie una sesión de trabajo debe ejecutar rigurosamente el siguiente protocolo antes de proponer cambios o modificar código:

```bash
# 1. Verificar el estado del árbol de trabajo local
git status

# 2. Sincronizar cambios remotos sin reescritura de historia
git pull --ff-only origin main

# 3. Diagnosticar la integridad del entorno local y componentes del sistema
python scripts/doctor.py
```

Adicionalmente, el agente debe:
- Consultar el archivo de estado vivo: [`docs/PROJECT_STATE.md`](docs/PROJECT_STATE.md) (y la configuración declarativa [`config/project_status.json`](config/project_status.json)) para conocer la fase actual y el próximo hito autorizado.
- Comprobar las incidencias técnicas abiertas antes de reintentar operaciones conocidas que fallen.

---

## 3. Restricciones y Reglas Ineludibles para Agentes

### 3.1 Prohibición de Nuevos Entrenamientos y Cómputo Azure
- **NUNCA ejecutar `src/train_automl.py` ni lanzar nuevos trabajos de entrenamiento en Azure ML** a menos que el usuario lo solicite explícitamente por escrito. El job ganador `wheat_cheese_4swj34tkjn` ya concluyó exitosamente.
- No crear recursos de cómputo, clústeres adicionales ni consumir cuota de suscripción de Azure sin autorización explícita.

### 3.2 Seguridad y Secretos
- **PROHIBIDO subir credenciales, tokens o suscripciones al repositorio.**
  - El archivo `config.json` está en `.gitignore` y no debe versionarse.
  - Usar siempre `config.example.json` como plantilla pública con identificadores dummy.
  - Nunca imprimir secrets, claves de almacenamiento o tokens en logs o salidas que se versionen.

### 3.3 Artefactos Binarios y Entornos Virtuales
- **PROHIBIDO commitear modelos binarios o entornos:**
  - Archivos `.pkl`, `.joblib`, `.onnx` o carpetas de entornos (`.venv/`, `venv/`, `env/`) no deben agregarse a Git (controlados por `.gitignore`).
  - La procedencia del modelo ganador se audita por sus metadatos en Azure ML (`azureml_wheat_cheese_4swj34tkjn_11_output_mlflow_log_model_873731674:1`), no por su binario en el árbol de Git.

### 3.4 Compatibilidad de Entorno
- El entorno local puede ejecutar Python 3.13.x, pero el modelo de Azure ML AutoML fue serializado en entornos basados en Python 3.9/3.10.
- No alterar instalaciones globales del sistema operativo ni intentar desinstalar/reinstalar versiones de Python a nivel de máquina.
- Recomendar siempre entornos virtuales aislados.

---

## 4. Convenciones de Desarrollo y Commits Atómicos

1. **Commits Atómicos y Claros:**
   - Cada commit debe resolver una unidad lógica de trabajo.
   - Seguir la convención Conventional Commits:
     - `feat:` nueva funcionalidad o script.
     - `fix:` corrección de errores o compatibilidad.
     - `docs:` documentación y guías.
     - `test:` adición o refuerzo de suites de pruebas.
     - `refactor:` reestructuración sin cambio de comportamiento.
     - `ci:` flujos de integración continua.

2. **Ejecución de Pruebas Previa al Commit:**
   - Todo cambio en `src/` o `scripts/` debe validarse con la suite completa de pruebas:
     ```bash
     python -m pytest tests/ -v
     ```
   - No realizar commits si alguna prueba falla o si existen advertencias no controladas.

3. **Mantenimiento de Documentación Viva:**
   - Si un cambio en el código altera parámetros, comandos CLI o el estado de una fase, debe actualizarse la documentación correspondiente (`README.md`, `docs/PROJECT_STATE.md`, etc.).
   - Utilizar el script automatizado para sincronizar la documentación:
     ```bash
     python scripts/sync_state.py
     ```
   - Verificar la sincronización documental sin modificarla con:
     ```bash
     python scripts/sync_state.py --check
     ```

---

## 5. Carga Manual de este Documento en Diferentes IDEs / Agentes

No todos los entornos de desarrollo leen `AGENTS.md` de forma nativa. Si utiliza un agente que no carga automáticamente este contexto:

- **Antigravity / Gemini CLI:** Carga este archivo automáticamente si está configurado en las reglas de proyecto. Si se abre una subsesión, invoque:  
  *«Lee AGENTS.md y adopta el rol y las restricciones descritas antes de continuar.»*
- **Cursor / VS Code (Copilot / Cline / Roo Code):**
  - Añada una referencia explícita en `.cursorrules` o en los System Instructions del agente:  
    `Follow all instructions and constraints established in @AGENTS.md`.
  - O adjunte `@AGENTS.md` como contexto en el primer prompt de la conversación.
- **Claude Dev / Aider / Windsurf:**
  - Inicie la sesión con: `/add AGENTS.md` o referéncielo en `.windsurfrules`.

---

## 6. Próximo Hito Autorizado

El estado del proyecto se encuentra en la **Fase 4.3 completada** (inspección y descarga de modelo asegurada vía Model Asset).  
El próximo hito técnico autorizado es:
- **Fase 4.4 — Evaluación Controlada del Modelo:** Ejecución de la evaluación independiente contra el conjunto de 206 observaciones de prueba (`concrete_test.csv`) bajo consumo acotado de memoria y generación del reporte de métricas ($R^2$, RMSE, MAE, NRMSE global y segmentado a 7d y 28d).
