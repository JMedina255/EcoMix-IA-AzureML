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
| **4.4** | Evaluacion Independiente del Modelo | 🟡 Pendiente | `src/evaluate_model.py --evaluate` | Fase 4.4-A verificada: firma del modelo (8 variables) y prueba controlada de carga. Evaluador MLflow implementado (src/evaluate_model.py). Job declarativo Azure ML preparado (config/azure_eval_job.yml). Carga local no viable en Windows por dependencias de Azure AutoML (azureml-training-tabular). Fase 4.4-B (ejecucion de evaluacion y reporte de metricas reales) pendiente de despacho autorizado en Azure ML. |
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
- **Total de Pruebas:** 61 pruebas automatizadas pasando al 100%.
- **Archivos de Prueba:**
  - `tests/test_azure_eval_job.py`
  - `tests/test_doctor.py`
  - `tests/test_evaluation_control.py`
  - `tests/test_inspect_and_download.py`
  - `tests/test_model_loading.py`
  - `tests/test_model_runtime.py`
  - `tests/test_sync_state.py`

---

## 6. Distinción Entre Hechos Comprobados y Plan de Ejecución

### Hechos Comprobados y Pasos Completados
1. **Partición de Datos:** Congelada deterministicamente en 824 registros para entrenamiento y 206 para prueba (`concrete_test.csv`, SHA-256 canónico: `6484d9f1493ca19ada7c7ec32ebf0a7015bcb1773605b2de428ff1b5a889026b`).
2. **Entrenamiento AutoML:** El job `wheat_cheese_4swj34tkjn` produjo un modelo ganador `VotingEnsemble` con NRMSE de `0.05859`.
3. **Inspección y Descarga del Artefacto (Completadas):** El activo `azureml_wheat_cheese_4swj34tkjn_11_output_mlflow_log_model_873731674:1` se descarga selectivamente mediante `ml_client.models.download` (670,849 bytes).
4. **Verificación de Firma y Metadatos (Completada):** Se validó que el artefacto declare estrictamente las 8 variables predictoras sin requerir deserialización (`scripts/verify_model_load.py --signature-only`).
5. **Carga Local (No Viable en Windows):** La deserialización local en el intérprete Windows/Python 3.13 no es viable debido a dependencias binarias especializadas de Azure AutoML (`azureml.training.tabular.models.voting_ensemble.PreFittedSoftVotingRegressor`).
6. **Evaluador MLflow Independiente (Completado):** `src/evaluate_model.py` preparado para cargar paquetes MLflow, auditar solapamientos objetivamente sin atribuciones normativas ASTM y segmentar métricas a 7d y 28d.
7. **Job Declarativo Azure ML (Completado):** Especificación reproducible `config/azure_eval_job.yml` validada para ejecutar `evaluate_model.py` bajo el runtime oficial `mcr.microsoft.com/azureml/curated/ai-ml-automl:41` en el clúster existente `cpu-cluster-ecomix`.
8. **Suite Automatizada de Pruebas:** 61 pruebas automatizadas pasando al 100% en entornos multiplataforma (Windows y Ubuntu con Python 3.10 y 3.13).

### Plan de Ejecución y Tareas Pendientes
1. **Ejecución de la Evaluación Independiente (Fase 4.4-B):**
   - **Estado:** No ejecutada. Planificada y validada estáticamente.
   - **Comando de Despacho en Azure ML:**
     ```bash
     az ml job create -f config/azure_eval_job.yml
     ```
     *(Importante: Este comando NUNCA debe ejecutarse automáticamente por agentes IDE; requiere confirmación explícita y por escrito del usuario).* 
   - **Costos Estimados de Cómputo:**
     El clúster existente `cpu-cluster-ecomix` escala dinámicamente a 1 nodo CPU (`STANDARD_DS11_V2`, ~$0.14 USD/hora). La evaluación toma ~2 a 4 minutos (costo acotado inferior a $0.02 USD / 0.08 S/.).
2. **Consolidación de Métricas y Trazabilidad (Fase 4.5):** Generación y registro de `reports/evaluation_wheat_cheese_4swj34tkjn.json` y el gráfico de correlación real vs predicho una vez obtenidos los resultados reales de la nube.
3. **Módulo de Inferencia EcoMix (Fase 5):** Implementación de fórmulas de sostenibilidad (reemplazo clínker por puzolana/escoria, huella de carbono y costo) sin alterar el runtime del predictor ML.
