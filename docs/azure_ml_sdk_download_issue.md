# Documentación Técnica: Incidencia en Descarga de Outputs en Azure ML SDK v2

**Proyecto:** EcoMix IA  
**Fase:** 4.3 — Descarga selectiva de modelo ganador  
**Componente afectado:** `azure-ai-ml` / `azure-cli (ml extension)`  

---

## 1. Descripción de la Incidencia

Al invocar la descarga selectiva del modelo ganador mediante el SDK de Azure ML:

```python
ml_client.jobs.download(name=job_name, output_name="best_model", download_path=dest_dir, all=False)
```

O mediante la herramienta de línea de comandos oficial de Azure CLI:

```bash
az ml job download --name wheat_cheese_4swj34tkjn --output-name best_model --resource-group EcomixIA --workspace-name ecomix-ia-ml --download-path models/wheat_cheese_4swj34tkjn
```

El proceso se interrumpe antes de iniciar la transferencia de archivos con la siguiente traza de error:

```text
TypeError: BatchGetResolvedUrisDto.__init__() got an unexpected keyword argument 'values'
```

---

## 2. Entorno y Versiones Registradas

- **Sistema Operativo:** Windows 10/11
- **Python:** `3.13.5`
- **azure-ai-ml (SDK v2):** `1.35.2` (última versión estable publicada en PyPI a la fecha)
- **azure-cli:** `2.91.0`
- **azure-cli ml extension (azext_mlv2):** `2.45.2`

---

## 3. Causa Raíz Comprobada

Tras la inspección del código fuente del paquete instalado en `site-packages/azure/ai/ml`:

1. En el módulo generado por TypeSpec / Autorest v3:
   `azure/ai/ml/_restclient/model_dataplane/models/_models_py3.py` (y `_models.py`), el DTO para resolución por lotes de URIs se define como:
   ```python
   class BatchGetResolvedUrisDto(_Model):
       values_property: Optional[list[str]] = rest_field(
           name="values", visibility=["read", "create", "update", "delete", "query"], original_tsp_name="values"
       )

       @overload
       def __init__(
           self,
           *,
           values_property: Optional[list[str]] = None,
       ) -> None: ...
   ```
   El generador renombró el parámetro del constructor a `values_property` para evitar colisiones con palabras reservadas / métodos de diccionario.

2. Sin embargo, en la capa de operaciones del SDK:
   `azure/ai/ml/operations/_model_dataplane_operations.py` (línea 26):
   ```python
   def get_batch_model_uris(self, model_ids: List[str]) -> BatchModelPathResponseDto:
       batch_uri_request = BatchGetResolvedUrisDto(values=model_ids)
   ```
   El SDK continúa enviando el argumento `values=model_ids`.
   Al ser invocado, el inicializador de `_Model` valida los argumentos recibidos y, al no existir un atributo denominado `values`, lanza:
   `TypeError: BatchGetResolvedUrisDto.__init__() got an unexpected keyword argument 'values'`.

3. La extensión `ml` de Azure CLI (`azext_mlv2` versión `2.45.2`) comparte la misma base de código Python interna, por lo que experimenta idéntica excepción.

---

## 4. Verificación en Entorno Aislado

Se comprobó en un entorno virtual aislado con `azure-ai-ml==1.35.1` y la versión estable actual `1.35.2`. Ambas versiones presentan la misma incompatibilidad interna al resolver URIs de modelos para jobs AutoML.

---

## 5. Medidas de Mitigación Implementadas en EcoMix IA

Para salvaguardar la robustez del pipeline sin violar restricciones de seguridad ni alterar paquetes del sistema:

1. **Manejo de Excepciones Específico:**
   En `src/evaluate_model.py`, la llamada a `ml_client.jobs.download()` se encuentra encapsulada para detectar de manera precisa `TypeError` asociado a `BatchGetResolvedUrisDto` y discrepancias de parámetros.

2. **Diagnóstico Claro y Preservación del Error:**
   La aplicación no enmascara la falla; emite un diagnóstico en consola con las causas del SDK y relanza `RuntimeError` encadenado (`raise ... from e`) para trazabilidad técnica.

3. **Garantía de Descarga Selectiva:**
   Bajo ninguna circunstancia se recurre a `all=True`, evitando descargas masivas e innecesarias de gigabytes en disco.

4. **Verificación Estricta de Existencia en Disco:**
   La descarga solo se declara exitosa si se valida fehacientemente la existencia y tamaño no nulo de los artefactos (`model.pkl` o carpeta `MLmodel`) en el directorio de destino.

---

## 6. Alternativas Comprobadas para Obtención del Modelo

Cuando el comando `ml_client.jobs.download(output_name="best_model")` sea bloqueado por este bug del SDK:

### Alternativa A: Descarga vía Azure ML Studio (Recomendada)
1. Ingrese al portal [ml.azure.com](https://ml.azure.com).
2. Navegue a **Trabajos (Jobs)** -> seleccione el experimento `wheat_cheese_4swj34tkjn`.
3. Vaya a la pestaña **Resultados y registros (Outputs + logs)**.
4. Ubique el directorio `best_model` o `outputs`, haga clic en los tres puntos (`...`) y elija **Descargar**.
5. Deposite los archivos en la carpeta del proyecto:
   `models/wheat_cheese_4swj34tkjn/best_model/`

### Alternativa B: Descarga directa del Model Asset (Python SDK)
Dado que Azure ML AutoML registra automáticamente un activo de modelo para la iteración ganadora (`wheat_cheese_4swj34tkjn_11`):
```python
from azure.ai.ml import MLClient
from src.evaluate_model import get_ml_client

client = get_ml_client()
client.models.download(
    name="azureml_wheat_cheese_4swj34tkjn_11_output_mlflow_log_model_873731674",
    version="1",
    download_path="models/wheat_cheese_4swj34tkjn"
)
```
*Comprobado con éxito: descarga completa de `model.pkl` (670,849 bytes), `MLmodel`, `conda.yaml` y dependencias.*

### Ejecución de Evaluación con Modelo Descargado
Una vez obtenido el modelo por cualquiera de las alternativas:
```bash
python src/evaluate_model.py --evaluate --model-path "models/wheat_cheese_4swj34tkjn/best_model/model.pkl"
```
