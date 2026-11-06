# Estado Vivo del Proyecto — EcoMix IA (Azure ML)

> **Documento vivo de trazabilidad técnica.**  
> Fuente declarativa: [`config/project_status.json`](../config/project_status.json).  
> Actualizado y verificado mediante: `python scripts/sync_state.py`.

---

## 1. Identificación y Parámetros Generales

- **Identificador del Proyecto:** `ecomix-ia-ml`
- **Repositorio:** `JMedina255/EcoMix-IA-AzureML`
- **Rama Principal:** `main`
- **Fase Actual:** `5.6-A — Consolidación documental y cierre de evaluación`
- **Próximo Hito Autorizado:** `Fase 5.6-A — Endurecimiento de API y preparación para contenedorización`
- **Última Validación Registrada:** `2026-11-06` (Origen: *Azure ML Studio & Workspace Telemetry (Job stoic_pot_x25ht98nv7)*)

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
| **4.4** | Evaluacion Independiente del Modelo | ✅ Completado | `src/evaluate_model.py --evaluate` | Job stoic_pot_x25ht98nv7 completado exitosamente en Azure ML (2m 35s). 206 observaciones evaluadas (100% validas): R2 0.9121, RMSE 4.7592 MPa, MAE 3.2822 MPa, NRMSE 0.0673. En subconjunto sin solapamiento (195 muestras): R2 0.9174, RMSE 4.587 MPa. Desglose: 7d (R2 0.8841, RMSE 5.1725 MPa), 28d (R2 0.8235, RMSE 5.5930 MPa). |
| **4.5** | Generacion de Reportes y Trazabilidad | ✅ Completado | `src/evaluate_model.py (reporting)` | Reporte JSON oficial 'reports/evaluation_wheat_cheese_4swj34tkjn.json' (9,928 bytes) y grafico de correlacion auditados y consolidados. Documento de evaluacion tecnica generado en 'docs/EVALUATION_REPORT.md', especificacion de inferencia para Fase 5 preparada y estado del repositorio sincronizado. |
| **5** | Servicio de Inferencia ML y API REST (7d y 28d) | ✅ Completado | `src/api/main.py` | Motor de inferencia real VotingEnsemble validado en Azure ML (serene_spinach_sn7khxvkq7) con paridad determinística (|Δ|=0.0 MPa). Microservicio REST FastAPI modular implementado, validado con 18 pruebas y fusionado a main (PR #1, commit 0af7692). |
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

### Incidencia ISSUE-SDK-02 (Resolved)
- **Descripción:** ModuleNotFoundError: No module named 'azure.ai' al ejecutar CommandJob en el contenedor curado oficial de Azure AutoML debido a importaciones top-level del SDK de gestion.
- **Mitigación comprobada:** Desacoplamiento arquitectonico mediante 'from __future__ import annotations', TYPE_CHECKING y lazy import de azure.ai.ml y azure.identity exclusivamente en funciones cliente (commit 1491940). Verificado exitosamente con job stoic_pot_x25ht98nv7.

---

## 5. Pruebas y Cobertura Verificada

- **Suite de Pruebas:** `pytest tests/ -v`
- **Total de Pruebas:** 88 pruebas automatizadas recopiladas.
- **Resultado en CI (GitHub Actions) y Clones Limpios:** 85 pasando y 3 omitidas (`pytest.skip`).
- **Justificación de las 3 Omisiones en CI:** Los modelos binarios entrenados (`models/model.pkl`) no se versionan en Git por gobernanza, seguridad y límite de peso del repositorio. Por ende, las 3 pruebas que requieren deserializar el artefacto real descargado se omiten limpiamente, mientras que las 85 pruebas de firma, contratos de interfaz, desacoplamiento y modelos sintéticos pasan al 100%. En el equipo de desarrollo local con el modelo descargado, pasan las 88 pruebas al 100%.
- **Archivos de Prueba:**
  - `tests/test_azure_eval_job.py`
  - `tests/test_doctor.py`
  - `tests/test_evaluation_control.py`
  - `tests/test_evaluation_runtime_decoupling.py`
  - `tests/test_inspect_and_download.py`
  - `tests/test_model_loading.py`
  - `tests/test_model_runtime.py`
  - `tests/test_sync_state.py`

---

## 6. Distinción Entre Hechos Comprobados y Plan de Ejecución

### Hechos Comprobados y Pasos Completados
1. **Partición de Datos:** Congelada deterministicamente en 824 registros para entrenamiento y 206 para prueba (`data/processed/concrete_test.csv`, SHA-256 canónico: `6484d9f1493ca19ada7c7ec32ebf0a7015bcb1773605b2de428ff1b5a889026b`).
2. **Entrenamiento AutoML:** El job `wheat_cheese_4swj34tkjn` produjo un modelo ganador `VotingEnsemble` con NRMSE de `0.05859`.
3. **Inspección y Descarga del Artefacto (Completadas):** El activo `azureml_wheat_cheese_4swj34tkjn_11_output_mlflow_log_model_873731674:1` se descarga selectivamente mediante `ml_client.models.download` (670,849 bytes).
4. **Verificación de Firma y Metadatos (Completada):** Se validó que el artefacto declare estrictamente las 8 variables predictoras sin requerir deserialización (`scripts/verify_model_load.py --signature-only`).
5. **Desacoplamiento de Runtime (Completado):** Eliminación de dependencias del SDK Azure ML (`azure-ai-ml`) en la ruta crítica de inferencia mediante importaciones diferidas (`from __future__ import annotations` y `TYPE_CHECKING`), permitiendo ejecución transparente en contenedores curados limpios.
6. **Evaluación Independiente en la Nube (Fase 4.4 - Completada):** Job `stoic_pot_x25ht98nv7` ejecutado exitosamente en Azure ML sobre clúster `cpu-cluster-ecomix` (`Standard_DS3_v2`) en 2m 35s. 206 observaciones evaluadas (100% exitosas) obteniendo: $R^2 = 0.9121$, RMSE = 4.7592 MPa, MAE = 3.2822 MPa, NRMSE = 0.0673. En subconjunto sin solapamiento (195 muestras): $R^2 = 0.9174$, RMSE = 4.587 MPa. A 7d: $R^2 = 0.8841$, RMSE = 5.1725 MPa. A 28d: $R^2 = 0.8235$, RMSE = 5.5930 MPa.
7. **Consolidación de Reportes y Trazabilidad (Fase 4.5 - Completada):** Métricas oficiales almacenadas en `reports/evaluation_wheat_cheese_4swj34tkjn.json`, gráfico de correlación en `reports/evaluation_wheat_cheese_4swj34tkjn_plot.png` e informe técnico integral en `docs/EVALUATION_REPORT.md`.
8. **Suite Automatizada de Pruebas:** 88 pruebas automatizadas recopiladas (85 pasando y 3 omitidas en CI por exclusión de binarios en Git; 100% pasando localmente con modelo descargado).

### Plan de Ejecución y Tareas Pendientes
1. **Fase 5 — Módulo de Inferencia EcoMix (7d y 28d + Ahorro CO2):**
   - Implementación de `src/inference.py` para consumo desde la plataforma web ASP.NET MVC 5.
   - Validación de dominios de entrada para las 8 variables predictoras según límites del dataset UCI 165.
   - Estimación dual a 7 y 28 días con cálculo analítico de reducción de huella de carbono (kg CO2e/m³) y costo (S/./m³).
   - Incorporación de márgenes de seguridad de sobrediseño inspirados en ACI PRC-211.1-22 y ACI 214R debido a la dispersión observada a 28 días.
2. **Fase 6 — API de Inferencia (FastAPI):** Exposición de microservicio REST autenticado y desacoplado.
3. **Fase 7 — Simulador Interactivo (Streamlit UI):** Interfaz para ingeniería de mezclas ecológicas.
