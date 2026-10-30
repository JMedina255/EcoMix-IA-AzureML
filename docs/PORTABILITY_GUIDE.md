# Guía de Portabilidad, Migración y Recuperación Limpia — EcoMix IA

**Repositorio:** `JMedina255/EcoMix-IA-AzureML`  
**Rama:** `main`  
**Objetivo:** Permitir clonar, diagnosticar, configurar y continuar el desarrollo de EcoMix IA en cualquier computadora o laboratorio universitario sin dependencias de rutas personales (`C:\Users\Admin\...`), sin exigir privilegios de administrador y sin comprometer modelos binarios ni credenciales en el repositorio Git.

---

## 1. Principios de Portabilidad

1. **Sin Rutas Absolutas en Código:** Todo script resuelve rutas de forma relativa a la raíz del repositorio (`BASE_DIR = Path(__file__).resolve().parent.parent`).
2. **Sin Binarios en Git:** Los modelos entrenados (`.pkl`, `.joblib`) se recuperan bajo demanda mediante el SDK de Azure ML o MLflow (`python src/evaluate_model.py --download`).
3. **Sin Secretos Versionados:** `config.json` se encuentra en `.gitignore`. Se provee `config.example.json` como plantilla estructurada.
4. **Independencia de Permisos de Administrador:** El entorno virtual se crea dentro del espacio de usuario (`.venv/`), compatible con terminales restringidas de laboratorios de cómputo.
5. **No Dependencia Obligatoria de Miniforge/Conda:** Funciona con el intérprete estándar de Python (`venv` + `pip`), aunque es compatible con entornos Conda si ya están presentes.

---

## 2. Flujo Completo de Onboarding en una Máquina Nueva

Al llegar a una computadora limpia (por ejemplo, en un laboratorio de la universidad o máquina personal), siga esta secuencia ordenada:

### Paso 1: Clonar el Repositorio
```bash
git clone https://github.com/JMedina255/EcoMix-IA-AzureML.git
cd EcoMix-IA-AzureML
```

### Paso 2: Abrir el Proyecto en su Entorno o IDE
Abra la carpeta raíz en VS Code, Cursor, Windsurf, PyCharm o terminal preferida.

### Paso 3: Consultar las Instrucciones de Agentes
Revise [`AGENTS.md`](../AGENTS.md) para conocer las reglas de desarrollo, límites de responsabilidad y restricciones de commits atómicos.

### Paso 4: Ejecutar Inicialización y Diagnóstico

En Windows PowerShell:
```powershell
# Inspección no destructiva por defecto
pwsh -File .\scripts\bootstrap.ps1

# O para crear .venv e instalar dependencias automáticamente:
pwsh -File .\scripts\bootstrap.ps1 -Install
```

En cualquier sistema operativo (Linux, macOS, Windows):
```bash
python scripts/doctor.py
```
El diagnóstico evalúa automáticamente los 4 sub-entornos:
- **Desarrollo:** Versión de Python, Git, Pytest, Pandas, Scikit-learn.
- **Azure ML:** Estado de `config.json`, SDK e Identity.
- **Evaluación:** Presencia del dataset de prueba (`concrete_test.csv`) y modelos binarios.
- **Inferencia:** Scripts y runtime disponible (Python local, Docker, API).

### Paso 5: Restaurar Configuración de Azure ML
Si necesita interactuar con Azure (inspección de jobs o descarga de modelos):
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
Lea [`docs/PROJECT_STATE.md`](PROJECT_STATE.md) para conocer la fase actual y el próximo hito autorizado, o ejecute:
```bash
python scripts/sync_state.py
```

### Paso 7: Recuperar Artefactos Faltantes
- **Particiones de datos:** Si no existen en `data/processed/`, se regeneran deterministicamente con:
  ```bash
  python src/prepare_data.py
  ```
- **Modelo ganador de Azure:** Si no existe en `models/`, se descarga selectivamente con:
  ```bash
  python src/evaluate_model.py --download
  ```

### Paso 8: Continuar con el Próximo Hito Autorizado
Verifique que los tests unitarios pasen antes de realizar cualquier cambio:
```bash
pytest tests/ -v
```
El próximo hito autorizado es la **Fase 4.4: Evaluación independiente y controlada del modelo ganador**.

---

## 3. Escenarios de Ejecución

### Escenario A — Computadora Personal (Windows / macOS / Linux)

Ideal para desarrollo activo y depuración con control total de dependencias.

1. **Python Recomendado:** Python 3.10 o 3.11 (permite compatibilidad directa con deserialización Scikit-learn de AutoML). Si utiliza Python 3.13, las herramientas de desarrollo y tests funcionan al 100%, pero la carga del binario `.pkl` de AutoML podría requerir un entorno aislado de Python 3.10.
2. **Creación del Entorno Virtual:**
   ```bash
   python -m venv .venv
   # Windows PowerShell:
   .venv\Scripts\Activate.ps1
   # Linux / macOS:
   source .venv/bin/activate
   ```
3. **Instalación:**
   ```bash
   pip install --upgrade pip
   pip install -r requirements.txt
   ```
4. **Verificación:**
   ```bash
   python scripts/doctor.py
   pytest tests/ -v
   ```

---

### Escenario B — Laboratorio Universitario (Sin Privilegios de Administrador)

Diseñado para máquinas de aula o laboratorios compartidos donde no se puede instalar software globalmente ni usar instaladores `.exe`.

1. **Uso de Python del Sistema:** Verifique qué versión está instalada:
   ```bash
   python --version
   ```
2. **Entorno Virtual en Carpeta de Usuario o Almacenamiento Portátil:**
   Dado que no se requieren permisos de administrador para crear un entorno virtual en la carpeta del proyecto:
   ```powershell
   pwsh -File .\scripts\bootstrap.ps1 -Install
   ```
   Si la política de ejecución de scripts de PowerShell está restringida (`Restricted`), ejecute:
   ```powershell
   powershell -ExecutionPolicy Bypass -File .\scripts\bootstrap.ps1 -Install
   ```
3. **Modo Offline:** Si la terminal del laboratorio no cuenta con salida a Internet para descargar desde Azure:
   - Los datos preprocesados ya se encuentran versionados en `data/processed/`.
   - Las pruebas automatizadas corren 100% desconectadas con `pytest tests/ -v`.
   - `scripts/sync_state.py` y `scripts/doctor.py` funcionan de forma autónoma.
4. **Limpieza:** Al finalizar la sesión, basta con borrar la carpeta del clon o `.venv/` sin dejar rastro en el registro del sistema.

---

### Escenario C — Evaluación Remota o Contenedorizada en Azure ML

Recomendado cuando el sistema operativo anfitrión no puede deserializar el modelo de Azure AutoML debido a incompatibilidades de versión de Python o Scikit-learn (ej. Python 3.13 local vs 3.10 de entrenamiento).

1. **Imagen Curada Oficial de Azure ML:**
   El modelo ganador (`wheat_cheese_4swj34tkjn_11` / `VotingEnsemble`) fue entrenado bajo el entorno administrado:
   ```text
   mcr.microsoft.com/azureml/curated/ai-ml-automl:41
   ```
2. **Uso con Docker Local (Opcional):**
   Si Docker está instalado y operativo en el host, puede ejecutarse un contenedor interactivo con el runtime exacto:
   ```bash
   docker run -it --rm -v ${PWD}:/workspace -w /workspace mcr.microsoft.com/azureml/curated/ai-ml-automl:41 python src/evaluate_model.py --evaluate
   ```
3. **Ejecución en Compute Instance de Azure:**
   Alternativamente, el script `src/evaluate_model.py` puede ejecutarse directamente en una instancia de cómputo de Azure ML Workspace (`cpu-cluster-ecomix` o instancia de desarrollo) donde las librerías del SDK y Scikit-learn coinciden bit a bit con el entorno de entrenamiento.

---

## 4. Matriz de Componentes y Diagnóstico Rápido

| Componente | Archivo / Comando | Función | Dependencia de Red |
| :--- | :--- | :--- | :---: |
| **Inicialización** | `scripts/bootstrap.ps1` | Detecta entorno, crea `.venv`, instala `requirements.txt` | No (salvo `-Install`) |
| **Diagnóstico** | `scripts/doctor.py` | Audita 4 sub-entornos (Dev, Azure, Eval, Infer) | No |
| **Sincronización** | `scripts/sync_state.py` | Valida consistencia y renderiza `PROJECT_STATE.md` | No |
| **Pruebas** | `pytest tests/ -v` | Suite automatizada de regresión e integridad | No |
| **Descarga Modelo** | `src/evaluate_model.py --download` | Descarga selectiva del Model Asset ganador | Sí (Azure ML) |
| **Inspección** | `src/evaluate_model.py --inspect` | Consulta telemetría del experimento sin descargar | Sí (Azure ML) |

---

## 5. Verificación de Integridad Antes de Commits

Para garantizar que el repositorio permanezca limpio, portable y compatible en CI:

1. Ejecutar las pruebas:
   ```bash
   pytest tests/ -v
   ```
2. Auditar la sincronización de estado documental:
   ```bash
   python scripts/sync_state.py --check
   ```
3. Comprobar que no se agreguen binarios ni credenciales:
   ```bash
   git status
   ```
   Asegurarse de que `.venv/`, `config.json` y archivos `*.pkl` permanezcan ignorados por Git.
