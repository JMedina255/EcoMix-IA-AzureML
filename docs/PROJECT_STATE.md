# Estado Vivo del Proyecto — EcoMix IA (Azure ML)

> **Documento vivo de trazabilidad técnica.**  
> Fuente declarativa: [`config/project_status.json`](../config/project_status.json).  
> Actualizado y verificado mediante: `python scripts/sync_state.py`.

---

## 1. Identificación y Parámetros Generales

- **Identificador del Proyecto:** `ecomix-ia-ml`
- **Repositorio:** `JMedina255/EcoMix-IA-AzureML`
- **Rama Principal:** `main`
- **Fase Actual:** `4.3 — Descarga selectiva de modelo ganador`
- **Próximo Hito Autorizado:** `4.4 - Evaluacion controlada e independiente del modelo ganador`
- **Última Validación Registrada:** `2026-10-30` (Origen: *Azure ML Studio & Workspace Telemetry*)

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
| **4.4** | Evaluacion Independiente del Modelo | 🟡 Pendiente | `src/evaluate_model.py --evaluate` | Pendiente de ejecucion bajo entorno compatible |
| **4.5** | Generacion de Reportes y Trazabilidad | 🟡 Pendiente | `src/evaluate_model.py (reporting)` | Pendiente de consolidacion de metricas en reports/ |
| **5** | Modulo de Inferencia EcoMix (7d y 28d + Ahorro CO2) | 🟡 Pendiente | `src/inference.py` | No iniciado |
| **6** | API de Inferencia (FastAPI) | 🟡 Pendiente | `src/api.py` | No iniciado |
| **7** | Simulador Interactivo (Streamlit UI) | 🟡 Pendiente | `app.py` | No iniciado |

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

---

## 4. Incidencias Técnicas y Mitigaciones

### Incidencia ISSUE-SDK-01 (Mitigated)
- **Descripción:** TypeError en BatchGetResolvedUrisDto.__init__() al descargar por output_name='best_model'.
- **Mitigación comprobada:** Descarga directa selectiva via Model Asset (ml_client.models.download) implementada en evaluate_model.py.

### Incidencia ISSUE-ENV-01 (Monitored)
- **Descripción:** El modelo AutoML VotingEnsemble fue generado en Python 3.10.19 con scikit-learn 1.5.1 y mlflow 2.15.1. El entorno de desarrollo general soporta Python 3.10-3.13, pero la deserializacion fiel del modelo binario requiere concordancia de runtime.
- **Recomendación:** Separar el entorno de desarrollo general del runtime de inferencia; utilizar Python 3.10.19 en venv dedicado o ejecucion remota documentada.

---

## 5. Pruebas y Cobertura Verificada

- **Suite de Pruebas:** `pytest tests/ -v`
- **Total de Pruebas:** 37 pruebas automatizadas pasando al 100%.
- **Archivos de Prueba:**
  - `tests/test_evaluation_control.py` (6 pruebas: validación de dataset, nulos, tipado, solapamiento, métricas robustas, ejecución end-to-end con dummy model).
  - `tests/test_inspect_and_download.py` (16 pruebas: normalizadores de estado y outputs, Casos A-D de AutoML, seguridad `all=False`, manejo de errores del SDK, verificación de archivos en disco, preferencia de Model Asset y validación de procedencia).

---

## 6. Distinción Entre Hechos Comprobados y Decisiones Pendientes

### Hechos Comprobados
1. El split de datos está congelado en 824 registros para entrenamiento y 206 para prueba (`concrete_test.csv`).
2. El job `wheat_cheese_4swj34tkjn` produjo un modelo `VotingEnsemble` con NRMSE de `0.05859`.
3. El activo de modelo `azureml_wheat_cheese_4swj34tkjn_11_output_mlflow_log_model_873731674:1` se descarga selectiva e íntegramente mediante `ml_client.models.download`.
4. El pipeline local cuenta con 37 pruebas automatizadas unitarias y de integración simulada sin dependencia de credenciales en CI.

### Decisiones Técnicas Pendientes
1. **Entorno de Ejecución de la Evaluación (Fase 4.4):** Determinar si se ejecuta localmente sobre Python 3.13 con validación estricta de compatibilidad o si se monta un contenedor Docker basado en `ai-ml-automl:41`.
2. **Estructura del Dossier de Métricas (Fase 4.5):** Consolidación de curvas de paridad y residuales en formato PNG/JSON para la sustentación del Reto Yura.
3. **Fórmulas de Sostenibilidad en Inferencia (Fase 5):** Parametrización de factores de emisión de $\text{CO}_2$ y costos de insumos según especificación de FD02/FD03.
