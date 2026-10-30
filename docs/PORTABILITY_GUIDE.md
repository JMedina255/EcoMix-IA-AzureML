# Guía de Portabilidad, Migración y Recuperación Limpia — EcoMix IA

**Repositorio:** `JMedina255/EcoMix-IA-AzureML`  
**Rama:** `main`  
**Objetivo:** Permitir clonar, diagnosticar, configurar y continuar el desarrollo de EcoMix IA en cualquier computadora o laboratorio universitario sin dependencias de rutas personales (`C:\Users\Admin\...`), sin exigir privilegios de administrador y sin comprometer modelos binarios ni credenciales en el repositorio Git.

---

## 1. Principios de Portabilidad

1. **Sin Rutas Absolutas en Código:** Todo script resuelve rutas de forma relativa a la raíz del repositorio (`BASE_DIR = Path(__file__).resolve().parent.parent`).
2. **Sin Binarios en Git:** Los modelos entrenados (`.pkl`, `.joblib`) se recuperan bajo demanda mediante el SDK de Azure ML (`python src/evaluate_model.py --download`).
3. **Sin Secretos Versionados:** `config.json` se encuentra en `.gitignore`. Se provee `config.example.json` como plantilla estructurada sin credenciales reales.
4. **Independencia de Permisos de Administrador:** El entorno virtual se crea dentro del espacio de usuario (`.venv/`), compatible con terminales restringidas de laboratorios universitarios.
5. **No Dependencia Obligatoria de Miniforge ni Docker:** Funciona con el intérprete estándar de Python (`venv` + `pip`), compatible con Windows PowerShell 5.1 nativo.

---

## 2. Diferenciación de Entornos: Desarrollo vs. Runtime de Inferencia

Es fundamental distinguir las dos capas operativas del proyecto:

### A. Entorno de Desarrollo y Calidad (General)
* **Intérprete soportado:** Python 3.10 a 3.13.x.
* **Manifiestos:** `requirements.txt` (manipulación de datos, Azure ML SDK, utilidades) y `requirements-dev.txt` (pytest, pytest-cov, faker, anyio).
* **Propósito:** Preprocesamiento de datasets, ejecución de suites de pruebas (`tests/`), auditoría documental con `scripts/sync_state.py`, diagnósticos con `scripts/doctor.py` e integración continua en GitHub Actions.
* **Aislamiento:** Este entorno no requiere versiones congeladas de Scikit-learn ni librerías de AutoML.

### B. Entorno de Inferencia y Evaluación AutoML (Especializado)
* **Intérprete verificado:** **Python 3.10.19** (confirmado oficialmente por `python_env.yaml` y `MLmodel` del artefacto ganador `wheat_cheese_4swj34tkjn_11`).
* **Librerías clave congeladas:** `scikit-learn==1.5.1`, `mlflow==2.15.1`, `joblib==1.4.2`.
* **Imagen base Azure ML:** `mcr.microsoft.com/azureml/curated/ai-ml-automl:41`.
* **Propósito:** Deserialización sin advertencias ni discrepancias numéricas del ensamble `VotingEnsemble` (`model.pkl`).
* **Regla:** Mantener este runtime especializado aislado para evitar conflictos con el entorno de desarrollo general.

---

## 3. Flujo Completo de Onboarding en una Máquina Nueva

Al llegar a una computadora limpia (en aula universitaria o equipo personal), siga esta secuencia ordenada:

### Paso 1: Clonar el Repositorio
```bash
git clone https://github.com/JMedina255/EcoMix-IA-AzureML.git
cd EcoMix-IA-AzureML
```

### Paso 2: Abrir el Proyecto en su Editor o Terminal
Abra la raíz del proyecto en VS Code, Cursor, Windsurf o la consola de su preferencia.

### Paso 3: Consultar las Instrucciones para Agentes
Revise [`AGENTS.md`](../AGENTS.md) para conocer las directrices de sesión, arquitectura ML y restricciones de commits.

### Paso 4: Ejecutar Inicialización y Diagnóstico

#### En Windows (PowerShell 5.1 nativo o PowerShell 7):
En laboratorios de cómputo donde no está instalado PowerShell 7 (`pwsh`), utilice el PowerShell estándar de Windows con bypass de directiva de ejecución:
```powershell
# Inspección no destructiva:
powershell -ExecutionPolicy Bypass -File .\scripts\bootstrap.ps1

# O para crear .venv e instalar dependencias automáticamente (modo usuario, sin admin):
powershell -ExecutionPolicy Bypass -File .\scripts\bootstrap.ps1 -Install
```
*(Si dispone de PowerShell 7+, puede usar equivalentemente: `pwsh -File .\scripts\bootstrap.ps1`)*.

#### En Linux o macOS:
```bash
python3 scripts/doctor.py
```
El script [`scripts/doctor.py`](file:///c:/Users/Admin/Desktop/Proyectos/ML%20EcomixIA/scripts/doctor.py) evalúa los 4 sub-entornos:
- **Desarrollo:** Versión de Python, Git, Pytest, Pandas, Scikit-learn.
- **Azure ML:** Estado de `config.json`, SDK e Identity.
- **Evaluación:** Dataset de prueba (`data/processed/concrete_test.csv`) y modelos descargados.
- **Inferencia:** Scripts y runtime disponible.

### Paso 5: Restaurar Configuración de Azure ML
Si necesita interactuar con Azure (inspección de jobs o descarga del modelo):
```bash
cp config.example.json config.json
```
Edite `config.json` con los identificadores reales de su suscripción:
```json
{
  "subscription_id": "TU_SUBSCRIPTION_ID_REAL",
  "resource_group": "rg-ecomix",
  "workspace_name": "ecomix-ia-ml"
}
```

### Paso 6: Consultar el Estado del Proyecto
Revise [`docs/PROJECT_STATE.md`](PROJECT_STATE.md) para conocer el estado vivo del sistema y el próximo hito autorizado, o ejecute:
```bash
python scripts/sync_state.py
```

### Paso 7: Recuperar Artefactos Faltantes
- **Particiones de datos:** Si no estuvieran en `data/processed/`, se regeneran deterministicamente con:
  ```bash
  python src/prepare_data.py
  ```
- **Modelo ganador de Azure:** Si no existe en `models/`, se descarga selectivamente con:
  ```bash
  python src/evaluate_model.py --download
  ```

### Paso 8: Continuar con el Próximo Hito Autorizado
Verifique que la suite de pruebas pase íntegramente:
```bash
python -m pytest tests/ -v
```
El próximo hito técnico autorizado es la **Fase 4.4: Evaluación independiente y controlada del modelo ganador** (pendiente de ejecución).

---

## 4. Escenarios de Ejecución

### Escenario A — Computadora Personal (Windows / macOS / Linux)

Ideal para desarrollo continuo con permisos locales para gestionar múltiples versiones de Python.

1. **Python para Desarrollo:** Python 3.10 a 3.13.
2. **Creación del Entorno Virtual:**
   ```bash
   python -m venv .venv
   # Windows PowerShell 5.1 / 7:
   .venv\Scripts\Activate.ps1
   # Linux / macOS:
   source .venv/bin/activate
   ```
3. **Instalación:**
   ```bash
   python -m pip install --upgrade pip
   pip install -r requirements.txt
   pip install -r requirements-dev.txt
   ```
4. **Verificación:**
   ```bash
   python scripts/doctor.py
   python -m pytest tests/ -v
   ```

---

### Escenario B — Laboratorio Universitario (Restricciones y Sin Privilegios de Administrador)

Diseñado para equipos compartidos de universidad donde:
- **No se cuenta con permisos de administrador.**
- **No está instalado Docker ni se tiene acceso a daemons de contenedores.**
- **Solo se dispone de Windows PowerShell 5.1** (`powershell.exe`) con política de ejecución estándar.
- **La versión de Python instalada a nivel de máquina no se puede modificar.**

#### Procedimiento de Trabajo:
1. **Comprobar la versión de Python del sistema:**
   ```powershell
   python --version
   ```
2. **Crear y activar el entorno virtual local en espacio de usuario:**
   El entorno se crea dentro de la carpeta del proyecto sin tocar el sistema:
   ```powershell
   powershell -ExecutionPolicy Bypass -File .\scripts\bootstrap.ps1 -Install
   ```
   Para activar la consola:
   ```powershell
   powershell -ExecutionPolicy Bypass -NoExit -Command "& '.\.venv\Scripts\Activate.ps1'"
   ```
3. **Operación Offline:**
   Las particiones de datos (`concrete_train.csv` y `concrete_test.csv`) están versionadas en el repositorio. La suite de pruebas y scripts de estado funcionan al 100% sin conexión a Internet:
   ```powershell
   python -m pytest tests/ -v
   python scripts/sync_state.py --check
   ```
4. **Limpieza al terminar:**
   Basta con eliminar la carpeta del repositorio clonado o `.venv/` para dejar la máquina limpia.

---

### Escenario C — Evaluación Remota o Runtime Especializado en Azure ML

Recomendado cuando el equipo local (por ejemplo, con Python 3.13) no cuenta con el intérprete exacto para deserializar el modelo `VotingEnsemble` de AutoML.

1. **Especificación Exacta del Modelo Ganador:**
   * **Python:** 3.10.19
   * **Scikit-learn:** 1.5.1
   * **MLflow:** 2.15.1
   * **Imagen Curada de Referencia:** `mcr.microsoft.com/azureml/curated/ai-ml-automl:41`
2. **Ejecución en Compute Instance de Azure ML (Recomendada en laboratorios):**
   Dado que en un laboratorio universitario típicamente no hay Docker disponible, la alternativa directa y oficial es ejecutar la evaluación en una Compute Instance o Job de Azure ML Workspace (`cpu-cluster-ecomix`), donde el entorno ya cuenta con las versiones binarias exactas.
3. **Uso de Docker Local (Opcional, solo si el anfitrión cuenta con Docker):**
   Si la máquina personal dispone de Docker y privilegios suficientes:
   ```bash
   docker run -it --rm -v ${PWD}:/workspace -w /workspace mcr.microsoft.com/azureml/curated/ai-ml-automl:41 python src/evaluate_model.py --evaluate
   ```

---

## 5. Matriz de Componentes del Proyecto

| Componente | Archivo / Comando | Función Principal | Dependencia de Red |
| :--- | :--- | :--- | :---: |
| **Inicialización** | `scripts/bootstrap.ps1` | Detecta entorno, crea `.venv`, instala dependencias | Solo con `-Install` |
| **Diagnóstico** | `scripts/doctor.py` | Audita 4 sub-entornos (Dev, Azure, Eval, Infer) | No |
| **Sincronización** | `scripts/sync_state.py` | Valida consistencia y renderiza `PROJECT_STATE.md` | No |
| **Pruebas** | `python -m pytest tests/ -v` | Suite automatizada de pruebas y calidad | No |
| **Descarga Modelo** | `src/evaluate_model.py --download` | Descarga selectiva del Model Asset ganador | Sí (Azure ML) |
| **Inspección** | `src/evaluate_model.py --inspect` | Consulta telemetría del experimento sin descargar | Sí (Azure ML) |

---

## 6. Verificación de Integridad Antes de Commits

Para asegurar la reproducibilidad y mantener el árbol limpio:

1. **Ejecutar la suite completa de pruebas:**
   ```bash
   python -m pytest tests/ -v
   ```
2. **Verificar sincronización documental:**
   ```bash
   python scripts/sync_state.py --check
   ```
3. **Auditar que no existan archivos binarios ni secretos pendientes:**
   ```bash
   git status
   ```
   Comprobar que `.venv/`, `config.json` y `models/**/*.pkl` se mantengan ignorados.
