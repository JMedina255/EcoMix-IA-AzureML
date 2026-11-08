# Reporte Técnico de Validación Real y Paridad del VotingEnsemble en Azure ML (Fase 5.4-B)

**EcoMix IA — Plataforma Tecnológica para Dosificación Sostenible de Concreto Ecológico**  
**Proyecto:** Reto 2 de Yura S.A. | Hackathon Innova Sur 2026 | Universidad Privada de Tacna  
**Repositorio:** `JMedina255/EcoMix-IA-AzureML`  
**Rama:** `feat/phase-05-inference-service`  
**Línea Base Git:** `2d3d75c48a7635dbb88b92987cbba4455a41f8c2`  
**Fecha de Validación:** 06 de Noviembre de 2026  
**Responsable:** Ingeniero MLOps, Arquitecto de Inferencia Python y Aseguramiento de Calidad (QA)

---

## 1. Veredicto Oficial de la Fase 5.4-B

```text
================================================================================
CLASIFICACIÓN OFICIAL:
VALIDADO CON MODELO REAL
================================================================================
```

### Síntesis del Veredicto
El nuevo motor de inferencia de **EcoMix IA** ([`src/inference/`](../src/inference/)) ha sido **validado experimentalmente de forma exitosa en el runtime certificado de Microsoft Azure Machine Learning**, utilizando el artefacto binario original del modelo `VotingEnsemble` (Child Run `wheat_cheese_4swj34tkjn_11`).

Se demostró una **paridad numérica absoluta** ($\Delta = 0.000000\text{ MPa}$, estrictamente menor al umbral contractual de $10^{-5}\text{ MPa}$) entre la fachada desacoplada de inferencia y la invocación directa del estimador, con latencias de inferencia dual en caliente de **57 a 65 ms** y un consumo máximo de memoria RAM de **251.85 MB**.

---

## 2. Metadatos de la Ejecución en Azure ML

| Parámetro | Valor Verificado en Azure ML | Observaciones / Estado |
| :--- | :--- | :--- |
| **Identificador del Job** | `serene_spinach_sn7khxvkq7` | Ejecución única autorizada |
| **Estado Terminal** | `Completed` | Finalizado con código de salida `0` |
| **Workspace / Grupo** | `ecomix-ia-ml` / `EcomixIA` | Suscripción `72d4dc56-4d14-4a13-a9ca-9773ed0ba6eb` |
| **Experimento** | `ecomix-ia-inference-validation` | Trazabilidad en Azure ML Studio |
| **Enlace de Seguimiento** | [Azure ML Studio Run](https://ml.azure.com/runs/serene_spinach_sn7khxvkq7?wsid=/subscriptions/72d4dc56-4d14-4a13-a9ca-9773ed0ba6eb/resourcegroups/EcomixIA/workspaces/ecomix-ia-ml&tid=b6b466ee-468d-4011-b9fc-fbdcf82ac90a) | Telemetría oficial |
| **Objetivo de Cómputo** | `azureml:cpu-cluster-ecomix` | 1 nodo dedicado `Standard_DS3_v2` |
| **Escalado del Clúster** | Min: `0`, Max: `1`, Idle time: `120 s` | Regresa automáticamente a 0 nodos sin costos ociosos |
| **Duración del Job** | $\approx 2.6\text{ minutos}$ ($158\text{ s}$ en estado `Running`) | Cómputo efectivo acotado |
| **Costo Estimado** | $\approx \$0.0105\text{ USD}$ ($\text{S/. } 0.04\text{ PEN}$) | Tarifa `Standard_DS3_v2` $\approx \$0.24/\text{h}$ |

---

## 3. Auditoría del Runtime Efectivo

Se realizó una auditoría rigurosa para contrastar el entorno declarado en el job con el utilizado exitosamente en la evaluación independiente previa (`stoic_pot_x25ht98nv7`):

### 3.1 Clarificación Técnica de Entornos
> [!IMPORTANT]
> Se corroboró que el entorno registrado `azureml:AzureML-AutoML:41` (versión histórica de 2020 con Python 3.6.2 y scikit-learn 0.22.1) **no es equivalente** a la imagen curada de contenedor `mcr.microsoft.com/azureml/curated/ai-ml-automl:41`. El Command Job especificó directamente la imagen MCR, la cual fue resuelta por Azure ML en el mismo entorno anónimo verificado (`azureml:CliV2AnonymousEnvironment:2f1ab110e59775a653ca32731cb86b644fa858a9862018b3694034a18604e0dc`).

### 3.2 Versiones de Dependencias Auditadas en el Contenedor
- **Sistema Operativo:** `Linux-6.8.0-1068-azure-x86_64-with-glibc2.39`
- **Intérprete Python:** `3.10.19 | packaged by conda-forge | (main, Jan 26 2026, 23:45:08) [GCC 14.3.0]`
- **scikit-learn:** `1.5.1` (idéntico al del entrenamiento y evaluación 4.4-B.3)
- **mlflow:** `2.15.1` (MLflow Skinny 2.15.1)
- **azureml.training.tabular:** Presente (`1.61.0`), permitiendo deserializar `PreFittedSoftVotingRegressor` sin errores de importación
- **pydantic:** `2.12.5` (`pydantic-core==2.41.5`, `pydantic-settings==2.12.0` presentes de forma nativa en la imagen curada)
- **pandas:** `1.5.3`
- **numpy:** `1.23.5`

**Conclusión de Compatibilidad:** Las dependencias del nuevo motor de inferencia desacoplado (`pydantic` v2, esquemas tipados, transformadores pandas/numpy) son **100% compatibles de forma nativa** con el runtime curado oficial de Azure ML sin requerir inyección de paquetes adicionales ni alteraciones de versiones.

---

## 4. Auditoría de Integridad del Modelo Binario

Antes de deserializar el artefacto en memoria RAM, el script ejecutó la auditoría criptográfica SHA-256 sobre el punto de montaje del Model Asset:

```text
Binario resuelto:     model.pkl
Ruta de Montaje:      /mnt/azureml/.../INPUT_model_dir/model.pkl
Hash SHA-256:         7eaa501c5eeb60135effb6b5861e736518ce969c47afd53727c2451083ff6388
Hash Certificado:     7eaa501c5eeb60135effb6b5861e736518ce969c47afd53727c2451083ff6388
Verificación:         [OK - COINCIDE EXACTAMENTE AL 100%]
```

- **Tiempo de Carga en Frío (*Cold-Start*):** $26,690.09\text{ ms}$ ($26.69\text{ s}$).  
  Incluye la lectura desde almacenamiento montado Blobstore (`ro_mount`), auditoría de checksum y deserialización de los 11 submodelos que conforman el ensamble `VotingEnsemble`.
- **Estado del Estimador en RAM:** `LOADED_SUCCESSFULLY` (modelo real, cero sustitución sintética).

---

## 5. Resultados de Paridad Numérica en Casos de Benchmark

Se evaluaron tres mezclas representativas del espectro de diseño de mezclas de concreto:

### Caso 1: Dosificación Canónica EcoMix (`canonical_ecomix`)
- **Composición ($\text{kg/m}^3$):** Cemento: $280.0$, Escoria: $105.0$, Ceniza volante / Puzolana (`fly_ash`): $60.0$, Agua: $175.0$, SP: $8.5$, Ag. Grueso: $1020.0$, Ag. Fino: $750.0$.
- **Ratios Calculados:** $a/c = 0.6250$, $a/mc = 0.3933$, Sustitución SCM: $37.08\%$, Masa Total: $2398.5\text{ kg/m}^3$.
- **Predicción a 7 días:**
  - Fachada `DualPredictionEngine`: **$35.16\text{ MPa}$**
  - Estimador Directo: **$35.16\text{ MPa}$**
  - Diferencia Absoluta: **$0.000000\text{ MPa}$**
- **Predicción a 28 días:**
  - Fachada `DualPredictionEngine`: **$49.58\text{ MPa}$**
  - Estimador Directo: **$49.58\text{ MPa}$**
  - Diferencia Absoluta: **$0.000000\text{ MPa}$**
- **Latencia de Inferencia en Caliente:** **$64.79\text{ ms}$**
- **Advertencias:** Ninguna (dentro de todos los límites físicos y experimentales).
- **Paridad Numérica:** **Cumplida ($\Delta < 10^{-5}\text{ MPa}$)**.

---

### Caso 2: Alta Sustitución Ecológica SCM (`high_scm_substitution`)
- **Composición ($\text{kg/m}^3$):** Cemento: $160.0$, Escoria: $220.0$, Ceniza volante / Puzolana (`fly_ash`): $70.0$, Agua: $165.0$, SP: $9.0$, Ag. Grueso: $1000.0$, Ag. Fino: $740.0$.
- **Ratios Calculados:** $a/c = 1.0312$, $a/mc = 0.3667$, Sustitución SCM: $64.44\%$, Masa Total: $2364.0\text{ kg/m}^3$.
- **Predicción a 7 días:**
  - Fachada `DualPredictionEngine`: **$27.00\text{ MPa}$**
  - Estimador Directo: **$27.00\text{ MPa}$**
  - Diferencia Absoluta: **$0.000000\text{ MPa}$**
- **Predicción a 28 días:**
  - Fachada `DualPredictionEngine`: **$43.39\text{ MPa}$**
  - Estimador Directo: **$43.39\text{ MPa}$**
  - Diferencia Absoluta: **$0.000000\text{ MPa}$**
- **Latencia de Inferencia en Caliente:** **$58.62\text{ ms}$**
- **Advertencias Emitidas por el Validador de Dominio:**
  1. `WARN_HIGH_SCM_REPLACEMENT` (Info): Sustitución de $64.44\%$ supera la cota de referencia usual ($40\%$). Se recomienda extender período de curado húmedo debido a la cinética puzolánica más lenta.
  2. `WARN_HIGH_WATER_CEMENT_RATIO` (Info): Relación $a/c = 1.0312$ elevada frente al cemento puro; sin embargo, $a/mc = 0.3667$ es óptima considerando los cementantes suplementarios.
- **Paridad Numérica:** **Cumplida ($\Delta < 10^{-5}\text{ MPa}$)**.

---

### Caso 3: Patrón de Referencia Portland Puro (`reference_portland_pure`)
- **Composición ($\text{kg/m}^3$):** Cemento: $380.0$, Escoria: $0.0$, Ceniza volante / Puzolana (`fly_ash`): $0.0$, Agua: $180.0$, SP: $4.0$, Ag. Grueso: $1020.0$, Ag. Fino: $760.0$.
- **Ratios Calculados:** $a/c = 0.4737$, $a/mc = 0.4737$, Sustitución SCM: $0.0\%$, Masa Total: $2344.0\text{ kg/m}^3$.
- **Predicción a 7 días:**
  - Fachada `DualPredictionEngine`: **$35.64\text{ MPa}$**
  - Estimador Directo: **$35.64\text{ MPa}$**
  - Diferencia Absoluta: **$0.000000\text{ MPa}$**
- **Predicción a 28 días:**
  - Fachada `DualPredictionEngine`: **$53.26\text{ MPa}$**
  - Estimador Directo: **$53.26\text{ MPa}$**
  - Diferencia Absoluta: **$0.000000\text{ MPa}$**
- **Latencia de Inferencia en Caliente:** **$57.22\text{ ms}$**
- **Advertencias:** Ninguna.
- **Paridad Numérica:** **Cumplida ($\Delta < 10^{-5}\text{ MPa}$)**.

---

## 6. Cuadro Comparativo Consolidado de Paridad

| Caso de Prueba | Edad | Predicción Motor (MPa) | Inferencia Directa (MPa) | Diferencia Absoluta ($\Delta$) | Criterio $\Delta < 10^{-5}$ | Latencia (ms) | Estado |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **Canonical EcoMix** | 7d | **35.16** | 35.16 | $0.000000$ | Superado | $64.79$ | PASSED |
| **Canonical EcoMix** | 28d | **49.58** | 49.58 | $0.000000$ | Superado | — | PASSED |
| **High SCM Sub.** | 7d | **27.00** | 27.00 | $0.000000$ | Superado | $58.62$ | PASSED |
| **High SCM Sub.** | 28d | **43.39** | 43.39 | $0.000000$ | Superado | — | PASSED |
| **Reference Portland** | 7d | **35.64** | 35.64 | $0.000000$ | Superado | $57.22$ | PASSED |
| **Reference Portland** | 28d | **53.26** | 53.26 | $0.000000$ | Superado | — | PASSED |

---

## 7. Desempeño y Consumo de Recursos

La medición de memoria y tiempos mediante `tracemalloc` y `time.perf_counter()` en el contenedor arrojó:

- **Memoria RAM Pico Consumida:** **$251.85\text{ MB}$**  
  (Muy por debajo del límite seguro de $2000\text{ MB}$ asignado a la memoria compartida del contenedor y de los $14\text{ GiB}$ disponibles en el nodo).
- **Memoria RAM al Finalizar:** **$250.93\text{ MB}$**  
  (Evidencia estabilidad del consumo de memoria en la ejecución del script acotado; la confirmación definitiva de ausencia de fugas de memoria a largo plazo requerirá pruebas de estrés continuas en la API de servicio).
- **Latencia Promedio en Caliente:** **$60.21\text{ ms}$** por inferencia dual (7 y 28 días simultáneos).  
  Corresponde estrictamente al tiempo de cómputo en memoria del motor de inferencia (`InferenceEngine.predict`). Deja una holgura de aproximadamente $1940\text{ ms}$ para absorber la sobrecarga de red HTTP, serialización y middleware web frente al límite máximo del SLA contractual (**RNF-01**: $< 2000\text{ ms}$).

---

## 8. Interpretación Rigurosa de Resultados y Distinciones Técnicas

De acuerdo con los principios de ingeniería de software y MLOps, se establecen las siguientes distinciones conceptuales y metodológicas:

1. **Paridad Numérica del Motor de Inferencia:**  
   Demuestra que las capas de abstracción (validación de esquemas Pydantic v2, normalización de arrays NumPy, construcción del DataFrame y ensamblado de edades) **no introducen ruido numérico, sesgos ni alteraciones algorítmicas**. La diferencia frente al estimador directo es estrictamente $\Delta = 0.000000\text{ MPa}$ ($< 10^{-5}\text{ MPa}$).
2. **Precisión Predictiva vs. Paridad de Invocación:**  
   La capacidad predictiva del modelo frente a roturas reales fue certificada de manera independiente en la **Fase 4.4-B** (job `stoic_pot_x25ht98nv7`) sobre las 206 observaciones congeladas de prueba:
   $$\mathbf{R^2 = 0.9121}, \quad \mathbf{\text{RMSE} = 4.7592\text{ MPa}}, \quad \mathbf{\text{MAE} = 3.2822\text{ MPa}}, \quad \mathbf{\text{NRMSE} = 0.0673}$$
   La prueba actual de paridad no evalúa precisión frente al terreno ni reemplaza dicha evaluación previa, sino que audita la fidelidad de ejecución del artefacto en el nuevo motor.
3. **Ámbito de Generalización Empírica:**  
   El modelo VotingEnsemble generaliza de forma confiable dentro del dominio experimental del dataset UCI 165 (concreto de peso normal, agregados estándar, curado húmedo convencional). No debe extrapolarse sin calibración previa a concretos especiales (ligeros, pesados, autocompactantes o geopolímeros puros).
4. **Criterios Normativos de Diseño Estructural (ACI / NTP):**  
   El valor estimado por el modelo ($f'_{c,\text{est}}$) representa una predicción empírica de resistencia a compresión en probetas cilíndricas. **No sustituye el cálculo de resistencia promedio requerida ($f'_{cr}$) ni las tolerancias de sobrediseño estadístico estipuladas en ACI 214R / ACI 318 ni en la NTP 339.034**. Asimismo, las advertencias por alta sustitución SCM o elevada relación $a/c$ son criterios de soporte al criterio del ingeniero proyectista, quien debe verificar la durabilidad según ACI 318-19 Tabla 19.3.2.1.
5. **Compatibilidad del Runtime:**  
   Confirma que el binario `VotingEnsemble` deserializa de manera reproducible en Linux Python 3.10 con `azureml-training-tabular` 1.61.0 y scikit-learn 1.5.1, validando la estrategia para el futuro contenedor de producción.
6. **Rendimiento Operativo:**  
   Garantiza que una vez que el modelo está en memoria RAM, el servicio puede computar inferencias duales en $\approx 60\text{ ms}$, facilitando la integración con ASP.NET MVC 5.

---

## 9. Artefactos Generados y Preservados

1. **Reporte JSON Oficial:**  
   [`reports/real_inference_validation.json`](../reports/real_inference_validation.json) (recuperado íntegramente del output `reports_dir` del job `serene_spinach_sn7khxvkq7`).
2. **Especificación del Job de Azure ML:**  
   [`config/azure_inference_job.yml`](../config/azure_inference_job.yml).
3. **Script Reproducible de Validación:**  
   [`scripts/validate_real_inference.py`](../scripts/validate_real_inference.py).
4. **Suite de Pruebas Automatizadas:**  
   [`tests/test_inference_runtime_and_job.py`](../tests/test_inference_runtime_and_job.py).
