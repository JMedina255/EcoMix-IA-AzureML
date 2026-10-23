# 🌱 EcoMix IA — Optimización y Predicción de Resistencia en Concretos Ecológicos

Sistema de Machine Learning basado en **Azure Machine Learning AutoML** para la predicción de resistencia a la compresión ($f'_c$ en MPa) en mezclas de concreto convencionales y ecológicas (incorporando escoria de alto horno y cenizas volantes).

---

## 📌 1. Visión General del Proyecto

El concreto es el segundo material más consumido en el planeta y la producción de cemento Portland representa aproximadamente el 7-8% de las emisiones globales de $\text{CO}_2$. **EcoMix IA** permite dosificar mezclas sustentables, prediciendo con precisión la ganancia de resistencia mecánica a **7 y 28 días**, optimizando el uso de aditivos y materiales cementantes suplementarios (SCMs).

- **Fuente de Datos:** [UCI Machine Learning Repository - Concrete Compressive Strength (ID: 165)](https://archive.ics.uci.edu/dataset/165/concrete+compressive+strength)
- **Observaciones:** 1.030 ensayos experimentales
- **Entorno en la Nube:** Azure Machine Learning Studio & SDK v2
- **Estrategia de Modelado:** AutoML Regression con Ensamble Ponderado y Validación Cruzada ($k=5$)

---

## 🏗️ 2. Variables del Modelo y Unidades

| Variable Técnica | Nombre en Código | Rol | Unidad | Descripción |
| :--- | :--- | :--- | :--- | :--- |
| **Cement** | `cement` | Entrada | $\text{kg/m}^3$ | Cemento Portland |
| **Blast Furnace Slag** | `blast_furnace_slag` | Entrada | $\text{kg/m}^3$ | Escoria de alto horno (material reciclado/suplementario) |
| **Fly Ash** | `fly_ash` | Entrada | $\text{kg/m}^3$ | Ceniza volante (subproducto termoeléctrico) |
| **Water** | `water` | Entrada | $\text{kg/m}^3$ | Agua de mezclado |
| **Superplasticizer** | `superplasticizer` | Entrada | $\text{kg/m}^3$ | Aditivo reductor de agua de alto rango |
| **Coarse Aggregate** | `coarse_aggregate` | Entrada | $\text{kg/m}^3$ | Agregado grueso (grava) |
| **Fine Aggregate** | `fine_aggregate` | Entrada | $\text{kg/m}^3$ | Agregado fino (arena) |
| **Age** | `age` | Entrada | Días | Tiempo de curado en probeta cilíndrica (1-365 días) |
| **Compressive Strength** | `concrete_compressive_strength` | **Objetivo** | $\text{MPa}$ | Resistencia mecánica a la rotura (ASTM C39) |

> [!NOTE]
> **Decisión Funcional:** La edad (`age`) es una variable predictora de entrada. Para estimar la resistencia esperada de una misma mezcla a los 7 y 28 días de curado, el sistema evalúa la misma dosificación configurando `age = 7` y `age = 28` respectivamente.

---

## 📂 3. Estructura del Repositorio

```text
ML EcomixIA/
├── config.json                     # Configuración de Workspace, Grupo de Recursos y Clúster en Azure ML
├── data/
│   ├── raw/
│   │   └── concrete_raw.csv        # Copia intacta de los datos originales de UCI (1.030 filas)
│   └── processed/
│       ├── concrete_clean.csv      # Dataset normalizado con nombres estandarizados
│       ├── concrete_train.csv      # Conjunto de Entrenamiento (80% = 824 filas)
│       ├── concrete_test.csv       # Conjunto de Prueba Independiente (20% = 206 filas)
│       ├── metadata.json           # Registro de semilla (42), particiones y estadísticas
│       ├── train/                  # Definición MLTable para entrenamiento en Azure ML
│       └── test/                   # Definición MLTable para prueba independiente
├── src/
│   ├── prepare_data.py             # Pipeline de limpieza, normalización y partición 80/20
│   ├── register_data.py            # Registro de activos de datos (Data Assets) en Azure ML
│   ├── train_automl.py             # Lanzamiento del job de AutoML con reglas de presupuesto
│   └── evaluate_model.py           # Descarga y evaluación contra el Test Set independiente
├── models/                         # Modelos y artefactos entrenados descargados de Azure
├── reports/                        # Reportes de métricas (JSON) y gráficos de desempeño (PNG)
└── README.md                       # Documentación principal del proyecto
```

---

## 📊 4. Matriz de Fases del Proyecto

| Fase | Nombre | Estado | Script / Archivo Principal | Descripción y Entregables |
| :---: | :--- | :---: | :--- | :--- |
| **1** | **Descarga de Datos** | ✅ Completado | `dataset.py` / `data/raw/` | Adquisición automática del repositorio UCI (ID 165) y preservación inalterada. |
| **2** | **Preparación y Validación** | ✅ Completado | [`src/prepare_data.py`](file:///c:/Users/Admin/Desktop/Proyectos/ML%20EcomixIA/src/prepare_data.py) | Verificación de 0 nulos, 25 réplicas ASTM, tipado, normalización y split 80/20 (`seed=42`). |
| **3** | **Entrenamiento AutoML en Azure** | ✅ Completado | [`src/train_automl.py`](file:///c:/Users/Admin/Desktop/Proyectos/ML%20EcomixIA/src/train_automl.py) | Clúster `cpu-cluster-ecomix`. Límites estrictos (30 min, 5 min/trial, 12 modelos). Job `wheat_cheese_4swj34tkjn`. |
| **4** | **Evaluación Independiente** | 🟡 Listo para ejecutar | [`src/evaluate_model.py`](file:///c:/Users/Admin/Desktop/Proyectos/ML%20EcomixIA/src/evaluate_model.py) | Descarga del mejor modelo, cálculo de $R^2$, RMSE y MAE con las 206 muestras aisladas de prueba. |
| **5** | **Módulo de Inferencia EcoMix** | ⏳ Próximo | `src/inference.py` | Lógica dual de predicción a 7 y 28 días + cálculo de ahorro de huella de carbono ($\text{CO}_2$). |
| **6** | **API de Inferencia (Backend)** | ⏳ Próximo | `src/api.py` | Microservicio REST con FastAPI para integración con sistemas de dosificación en planta. |
| **7** | **Simulador Interactivo (UI)** | ⏳ Próximo | `app.py` | Interfaz web interactiva en Streamlit para cálculo de dosificaciones y curvas de curado. |

---

## 🚀 5. Instrucciones de Ejecución

### Prerrequisitos
- Python 3.10 o superior (compatible con Python 3.13)
- Suscripción de Azure y Azure Machine Learning Workspace configurado
- Dependencias:
  ```bash
  pip install pandas scikit-learn azure-ai-ml azure-identity joblib matplotlib mlflow lightgbm xgboost
  ```

### Flujo de Reproducción
1. **Preparar datos:**
   ```bash
   python src/prepare_data.py
   ```
2. **Registrar activos en Azure ML:**
   ```bash
   python src/register_data.py
   ```
3. **Lanzar entrenamiento AutoML:**
   ```bash
   python src/train_automl.py
   ```
4. **Evaluar y descargar el modelo ganador:**
   ```bash
   python src/evaluate_model.py
   ```
