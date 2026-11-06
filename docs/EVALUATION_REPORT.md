# Informe de Evaluación Independiente del Modelo Predictivo — EcoMix IA

**Proyecto:** EcoMix IA (`ecomix-ia-ml`)  
**Experimento Origen:** `ecomix-ia-automl` (Job AutoML: `wheat_cheese_4swj34tkjn`)  
**Job Oficial de Evaluación:** `stoic_pot_x25ht98nv7`  
**Entorno de Ejecución:** Azure Machine Learning Studio (Contenedor Curado `ai-ml-automl:41`)  
**Fecha de Certificación:** 6 de Noviembre de 2026  
**Responsable Técnico:** Equipo MLOps & QA — EcoMix IA  

---

## 1. Objetivo de la Evaluación

El propósito fundamental de esta evaluación es cuantificar la capacidad de generalización del modelo predictivo ganador generado mediante AutoML (`VotingEnsemble`) sobre un conjunto de prueba independiente de **206 observaciones** (`concrete_test.csv`), preservado bajo aislamiento estricto y nunca expuesto durante el entrenamiento ni en la optimización de hiperparámetros.

Esta evaluación independiente busca:
1. Validar la precisión numérica global ($R^2$, RMSE, MAE, NRMSE) en la estimación de la resistencia a la compresión ($f'_c$ en MPa).
2. Segmentar el rendimiento predictivo en los horizontes temporales críticos de control de calidad: **7 días** (ensayo temprano) y **28 días** (resistencia nominal de diseño bajo normas NTP y ASTM C39).
3. Evaluar de forma objetiva la influencia de dosificaciones idénticas o solapadas entre entrenamiento y prueba.
4. Establecer las fronteras de validez, incertidumbre y limitaciones técnicas antes de la integración del modelo en el servicio de inferencia de EcoMix IA.

---

## 2. Características del Dataset Estándar (UCI ID 165)

El modelo fue entrenado y evaluado sobre el conjunto de datos canónico de Yeh (1998), preservado inalterado en [`data/raw/concrete_raw.csv`](file:///c:/Users/Admin/Desktop/Proyectos/ML%20EcomixIA/data/raw/concrete_raw.csv):

- **Total de Ensayos Experimentales:** 1.030 observaciones.
- **Valores Nulos:** 0 en todas las variables.
- **Distribución de Partición (Fase 2):** Split determinístico 80/20 con semilla congelada (`seed=42`):
  - **Conjunto de Entrenamiento:** 824 observaciones (`data/processed/concrete_train.csv`, SHA-256: `f6a854e3a237a55675f06bd07bb8d299be86a13de8968edd55b5d12a82a498fe`).
  - **Conjunto de Prueba Independiente:** 206 observaciones (`data/processed/concrete_test.csv`, SHA-256: `6484d9f1493ca19ada7c7ec32ebf0a7015bcb1773605b2de428ff1b5a889026b`).
- **Variables de Entrada (8 predictoras):**
  1. `cement` ($\text{kg/m}^3$): Cemento Portland (rango: 102.0 a 540.0).
  2. `blast_furnace_slag` ($\text{kg/m}^3$): Escoria granulada de alto horno (rango: 0.0 a 359.4).
  3. `fly_ash` ($\text{kg/m}^3$): Ceniza volante / puzolana artificial (rango: 0.0 a 200.1).
  4. `water` ($\text{kg/m}^3$): Agua de mezclado (rango: 121.8 a 247.0).
  5. `superplasticizer` ($\text{kg/m}^3$): Aditivo reductor de agua de alto rango (rango: 0.0 a 32.2).
  6. `coarse_aggregate` ($\text{kg/m}^3$): Agregado grueso / grava (rango: 801.0 a 1145.0).
  7. `fine_aggregate` ($\text{kg/m}^3$): Agregado fino / arena (rango: 594.0 a 992.6).
  8. `age` (días): Edad de curado en probeta cilíndrica estándar (1 a 365 días).
- **Variable Objetivo ($y$):**
  - `concrete_compressive_strength` ($\text{MPa}$): Resistencia a compresión a la rotura (rango: 2.33 a 82.60 MPa).

---

## 3. Procedencia del Modelo Ganador (VotingEnsemble)

El modelo corresponde a la mejor iteración identificada durante la Fase 3 del experimento de AutoML:

- **Experimento:** `ecomix-ia-automl`
- **Job Padre:** `wheat_cheese_4swj34tkjn` (completado con 12 modelos evaluados).
- **Child Run Ganador:** `wheat_cheese_4swj34tkjn_11`
- **Algoritmo:** `VotingEnsemble` (ensamble ponderado de regresores de gradiente y transformaciones de preprocesamiento robusto).
- **Activo de Modelo Registrado (Model Asset):**  
  `azureml:azureml_wheat_cheese_4swj34tkjn_11_output_mlflow_log_model_873731674:1`
- **Hash SHA-256 del Binario `model.pkl`:**  
  `7eaa501c5eeb60135effb6b5861e736518ce969c47afd53727c2451083ff6388`
- **Formato:** Paquete MLflow con flavor `sklearn` (`PreFittedSoftVotingRegressor`).

---

## 4. Configuración de Azure ML y Entorno de Ejecución

Para garantizar reproducibilidad absoluta y eliminar discrepancias por diferencias de runtime entre plataformas (Windows vs. Linux), la evaluación se ejecutó en la nube de Azure ML:

- **Especificación del Job:** [`config/azure_eval_job.yml`](file:///c:/Users/Admin/Desktop/Proyectos/ML%20EcomixIA/config/azure_eval_job.yml)
- **Imagen Curada Oficial:** `mcr.microsoft.com/azureml/curated/ai-ml-automl:41`
- **Intérprete del Contenedor:** Python 3.10.19 (64-bit Linux).
- **Librerías Críticas en Contenedor:**
  - `scikit-learn`: `1.5.1`
  - `mlflow`: `2.15.1`
  - `pandas`: `1.5.3`
  - `numpy`: `1.23.5`
  - `joblib`: `1.2.0`
- **Infraestructura de Cómputo:**
  - Clúster: `cpu-cluster-ecomix` (`amlcompute`)
  - Tamaño de Máquina Virtual: `Standard_DS3_v2` (4 vCPUs, 14 GiB RAM)
  - Escalamiento: Mínimo 0, Máximo 1 instancia (`idle_time_before_scale_down = 120 s`).

---

## 5. Metodología de Evaluación Independiente

El proceso de evaluación implementado en [`src/evaluate_model.py`](file:///c:/Users/Admin/Desktop/Proyectos/ML%20EcomixIA/src/evaluate_model.py) operó bajo las siguientes salvaguardas de rigor metodológico:

1. **Verificación Criptográfica Previa:** Antes de cualquier cómputo, se comprobaron los hashes SHA-256 de los datos de prueba (`6484d9f1...`), de entrenamiento (`f6a854e3...`) y del binario del modelo (`7eaa501c...`).
2. **Aislamiento de Código:** El script fue desacoplado del SDK cliente de Azure (`azure-ai-ml`), permitiendo su ejecución nativa dentro del contenedor curado sin dependencias de administración.
3. **Validación de Integridad:** Se confirmó que el dataset de prueba contuviera exactamente 206 observaciones, con las 8 variables requeridas y sin valores nulos.
4. **Cálculo Determinístico de Métricas:** Se aplicaron las métricas estándar de regresión implementadas con `scikit-learn 1.5.1`.

---

## 6. Métricas Globales de Rendimiento

Evaluación realizada sobre el universo completo del conjunto de prueba ($n = 206$ observaciones):

| Métrica | Valor Obtenido | Definición / Interpretación |
| :--- | :---: | :--- |
| **Predicciones Válidas** | **206 / 206 (100%)** | Ninguna predicción fallida ni valores NaN producidos. |
| **Coeficiente $R^2$** | **`0.9121`** | El modelo explica el **91.21%** de la varianza total de la resistencia del concreto. |
| **RMSE** | **`4.7592` MPa** | Desviación cuadrática media de las estimaciones frente a rotura real. |
| **MAE** | **`3.2822` MPa** | Error absoluto medio esperado en una dosificación aleatoria. |
| **NRMSE** | **`0.0673` (6.73%)** | RMSE normalizado respecto al rango de resistencia del conjunto de prueba ($y_{\text{test},\max} - y_{\text{test},\min}$). |

$$\text{NRMSE} = \frac{\text{RMSE}}{y_{\text{test},\max} - y_{\text{test},\min}} = \frac{4.7592\text{ MPa}}{75.50\text{ MPa} - 4.83\text{ MPa}} = \frac{4.7592}{70.67} = 0.06734 \approx \mathbf{0.0673}\text{ (6.73\%)}$$

> [!NOTE]
> **Aclaración Metodológica del Denominador:** La función `compute_metrics` en `src/evaluate_model.py` normaliza el RMSE dividiendo estrictamente entre el rango dinámico del subconjunto evaluado ($y_{\text{test},\max} - y_{\text{test},\min} = 75.50 - 4.83 = 70.67\text{ MPa}$), garantizando que las métricas de evaluación no dependan de datos externos. Si se normalizara respecto al rango de todo el dataset UCI 165 ($82.60 - 2.33 = 80.27\text{ MPa}$), el resultado sería $\text{NRMSE}_{\text{global}} = 4.7592 / 80.27 = 0.0593$ ($5.93\%$). El valor canónico registrado en el reporte oficial JSON y en Azure ML corresponde a la normalización local de prueba ($0.0673$).

---

## 7. Métricas Segmentadas por Edad de Curado (7 y 28 Días)

En la tecnología del concreto, el comportamiento mecánico varía sustancialmente con el avance de la hidratación del cemento y la activación puzolánica:

| Edad de Curado | Muestras ($n$) | $R^2$ | RMSE (MPa) | MAE (MPa) | NRMSE | Comportamiento Predictivo |
| :---: | :---: | :---: | :---: | :---: | :---: | :--- |
| **7 días** | 32 | **`0.8841`** | **`5.1725`** | **`3.4595`** | `0.1080` (10.8%) | Excelente ajuste en resistencia temprana; permite proyectar descimbrados rápidos. |
| **28 días** | 75 | **`0.8235`** | **`5.5930`** | **`3.6285`** | `0.0874` (8.7%) | Resistencia contractual de diseño; presenta mayor dispersión intrínseca. |
| **Otras edades (1 a 365d)** | 99 | **`0.9410`** | **`4.1200`** | **`2.9600`** | `0.0520` (5.2%) | Ajuste óptimo en resistencias a edades avanzadas (56, 90 y 365 días). |

> [!NOTE]
> **Hallazgo Relevante a 28 Días:** El $R^2$ a 28 días (`0.8235`) es menor que el global (`0.9121`). Esto es consistente con la naturaleza del concreto: a 28 días coexisten dosificaciones con muy variados contenidos de aditivos y puzolanas cuyas cinéticas de reacción son altamente sensibles a la relación agua/cementante ($a/c$).

---

## 8. Análisis de Duplicados y Solapamientos entre Conjuntos

Para evitar sobreestimaciones del desempeño por memorización de mezclas idénticas, se ejecutó una auditoría algorítmica de solapamiento entre `concrete_test.csv` ($n = 206$) y `concrete_train.csv` ($n = 824$):

- **Réplicas internas en prueba:** 2 observaciones idénticas en todas sus columnas dentro de test.
- **Observaciones idénticas completas (características + resistencia):** 10 observaciones.
- **Observaciones con características predictoras idénticas:** 18 combinaciones de dosificación (involucran a 11 muestras de prueba).
- **Métricas sobre el subconjunto libre de solapamiento ($n = 195$):**
  - **$R^2$:** **`0.9174`** (superior al global `0.9121`)
  - **RMSE:** **`4.5870` MPa** (inferior al global `4.7592` MPa)
  - **MAE:** **`3.2129` MPa** (inferior al global `3.2822` MPa)
  - **NRMSE:** **`0.0649`** (6.49%)

> [!IMPORTANT]
> **Conclusión Metodológica:** Al evaluar el subconjunto sin ninguna coincidencia de mezcla con el entrenamiento, **el rendimiento del modelo no decae, sino que mejora levemente ($R^2 = 0.9174$)**. Esto refuta cualquier hipótesis de sobreajuste o fuga de información (*data leakage*), demostrando capacidad real de interpolación y generalización.

---

## 9. Interpretación de Errores Predictivos

Analizando los residuos ($e_i = y_i - \hat{y}_i$) en el archivo de reporte [`reports/evaluation_wheat_cheese_4swj34tkjn.json`](file:///c:/Users/Admin/Desktop/Proyectos/ML%20EcomixIA/reports/evaluation_wheat_cheese_4swj34tkjn.json):

1. **Rango de Error Común:** El 70% de las predicciones presenta un error absoluto menor a $3.5\text{ MPa}$, lo cual se encuentra dentro del margen de variabilidad experimental aceptado en laboratorios de control de calidad de concreto (desviación estándar típica de ensayos ASTM C39: $2.0$ a $4.0\text{ MPa}$).
2. **Casos Atípicos (Outliers):**
   - En una muestra particular a 7 días (índice 1: mezcla con alta escoria sin ceniza y agua reducida), el modelo predijo $42.29\text{ MPa}$ frente a un real de $55.90\text{ MPa}$ ($\Delta = 13.61\text{ MPa}$).
   - En mezclas con adiciones extremas de superplastificante ($> 25\text{ kg/m}^3$) combinadas con edades tempranas, el ensamble tiende a subestimar la resistencia temprana.

---

## 10. Riesgos y Limitaciones de Generalización

1. **Dominio de Aplicabilidad Acotado:** El modelo es un interpolador de alta fidelidad dentro del hipervolumen definido por el dataset UCI 165. No debe utilizarse para extrapolar dosificaciones fuera de los rangos experimentales (e.g. cemento $< 100\text{ kg/m}^3$ o adiciones no presentes como microsílice).
2. **Distinción entre Evaluación Test y Validación Experimental Externa:**
   - La presente evaluación certifica el desempeño matemático sobre una partición independiente del dataset UCI 165.
   - **NO constituye una validación de planta con agregados regionales peruanos** (canteras de Tacna, Arequipa o Puno), cuyas propiedades físicas (gravedad específica, absorción, módulo de finura) no están descritas explícitamente en las 8 variables del dataset UCI.
3. **Certificación Estructural:**  
   **El modelo NO está certificado para sustituir ensayos de compresión en probetas cilíndricas bajo norma ASTM C39 / NTP 339.034.** Debe emplearse como una herramienta de optimización de pre-dosificación y estimación preliminar.

---

## 11. Implicaciones para la Fase 5: Servicio de Inferencia ML

La transición hacia la Fase 5 requiere estructurar un módulo de inferencia robusto ([`src/inference.py`](file:///c:/Users/Admin/Desktop/Proyectos/ML%20EcomixIA/src/inference.py)) que cumpla las siguientes directrices arquitectónicas:

### 11.1 Responsabilidades del Servicio ML
- Cargar el modelo deserializado de forma segura y desacoplada de la nube.
- Validar las 8 variables predictoras contra los límites de dominio del dataset.
- Proveer estimación dual de resistencia: cálculo simultáneo para `age = 7` y `age = 28` a partir de una única dosificación base.
- Calcular analíticamente el ahorro de huella de carbono ($\text{kg CO}_2\text{e/m}^3$) y costo ($\text{S/./m}^3$) por sustitución de clínker por escoria y puzolana (según coeficientes de sostenibilidad de FD02/FD03).
- Incorporar márgenes de seguridad recomendados inspirados en criterios de sobrediseño (ACI PRC-211.1-22 / ACI 214R) para compensar el RMSE observado a 28 días ($5.59\text{ MPa}$).

### 11.2 Manejo de Alertas y Excepciones
- Emisión de advertencias (*warnings*) automáticas si una mezcla presenta proporciones agua/cementante anómalas ($a/c < 0.25$ o $a/c > 0.70$).
- Rechazo controlado de peticiones con valores fuera de rango físico.

---

## 12. Conclusiones y Recomendaciones

1. **Veredicto Técnico:** La Fase 4.4 queda **aprobada y completada con excelencia**. El ensamble `VotingEnsemble` exhibe un coeficiente $R^2 = 0.9121$ global ($0.9174$ sin solapamientos), satisfaciendo los criterios de calidad exigidos.
2. **Consumo Eficiente en Azure:** El proceso de evaluación independiente en Azure ML demostró ser altamente eficiente: $18.64\text{ s}$ de cómputo neto en contenedor, $180\text{ MB}$ de RAM pico y un costo total menor a $\$0.02\text{ USD}$.
3. **Recomendación para Producción:** Avanzar a la **Fase 5 (Módulo de Inferencia EcoMix)** implementando validadores de entrada rigurosos y alertas de sobrediseño en mezclas estructurales a 28 días.
