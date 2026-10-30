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

1. **Descarga Directa mediante Model Asset (Ruta Principal):**
   En `src/evaluate_model.py`, la función `download_winner_model` resuelve dinámicamente el Model Asset registrado automáticamente por AutoML para el child run ganador (`resolve_model_asset`). Al estar verificado y validar la procedencia, ejecuta prioritariamente `ml_client.models.download(name, version, download_path)`, eludiendo de forma completa el defecto interno de resolución de outputs del dataplane.

2. **Manejo de Excepciones Específico en `jobs.download`:**
   Si se especifica un `--output-name` manual o si no existe Model Asset y se recurre a `ml_client.jobs.download()`, la llamada está protegida para capturar de manera precisa `TypeError` asociado a `BatchGetResolvedUrisDto`.

3. **Diagnóstico Claro y Exclusión de Azure CLI:**
   La aplicación no enmascara la falla; emite un diagnóstico en consola explicando el defecto interno del SDK. Se advierte explícitamente que Azure CLI (extensión `ml` 2.45.2) presenta la misma falla interna por compartir la base de código, por lo que no se recomienda como alternativa. En su lugar, se indican la descarga directa por Model Asset y la descarga manual desde Azure ML Studio.

4. **Garantía de Descarga Selectiva:**
   Bajo ninguna circunstancia se recurre a `all=True`, evitando descargas masivas e innecesarias de gigabytes en disco.

5. **Verificación Estricta de Existencia en Disco:**
   La descarga solo se declara exitosa (`verify_downloaded_model_files`) si se valida fehacientemente la existencia y tamaño no nulo de los artefactos (`model.pkl` o carpeta `MLmodel`) en el directorio de destino.

---

## 6. Procedimiento Comprobado para Obtención y Evaluación del Modelo

### Procedimiento Principal: Descarga Automatizada Integrada
Con la incorporación de la descarga por Model Asset, el comando estándar de descarga opera de manera directa y selectiva:
```bash
python src/evaluate_model.py --download --job-name wheat_cheese_4swj34tkjn
```
El script extrae dinámicamente el activo de modelo ganador (`azureml_wheat_cheese_4swj34tkjn_11_output_mlflow_log_model_873731674:1`), descarga los artefactos mediante `ml_client.models.download` y verifica la integridad de `model.pkl`.

### Procedimiento Alternativo: Descarga vía Azure ML Studio
1. Ingrese al portal [ml.azure.com](https://ml.azure.com).
2. Navegue a **Trabajos (Jobs)** -> seleccione el experimento `wheat_cheese_4swj34tkjn`.
3. Vaya a la pestaña **Resultados y registros (Outputs + logs)**.
4. Ubique el directorio `best_model` o `outputs`, haga clic en los tres puntos (`...`) y elija **Descargar**.
5. Deposite los archivos en la carpeta del proyecto:
   `models/wheat_cheese_4swj34tkjn/best_model/`

### Ejecución de Evaluación Local
Una vez obtenido el modelo:
```bash
python src/evaluate_model.py --evaluate --model-path "models/wheat_cheese_4swj34tkjn"
```
