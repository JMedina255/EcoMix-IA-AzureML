# ==============================================================================
# EcoMix IA — Dockerfile de Inferencia en Producción (Azure Container Apps)
# ==============================================================================
# Base: Imagen oficial curada de Azure AutoML para Tabular/Ensemble
#       (Ubuntu 20.04/22.04, Python 3.10.19, scikit-learn 1.5.1,
#        azureml-training-tabular 1.61.0, mlflow-skinny 2.15.1 preinstalados en /azureml-envs/azureml-automl).
# ==============================================================================

FROM mcr.microsoft.com/azureml/curated/ai-ml-automl:41

LABEL maintainer="EcoMix IA DevSecOps <soporte@ecomix.ia>"
LABEL description="Microservicio FastAPI de inferencia predictiva para EcoMix IA (VotingEnsemble)"
LABEL version="1.0.0"
LABEL project="EcoMix-IA-AzureML"

# Variables de entorno del sistema
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    ECOMIX_ENV=production \
    ECOMIX_HOST=0.0.0.0 \
    ECOMIX_PORT=8000 \
    ECOMIX_MODEL_PATH=/app/models \
    PYTHONPATH=/app \
    PATH="/azureml-envs/azureml-automl/bin:$PATH"

WORKDIR /app

# 1. Instalar dependencias adicionales de la API Web sobre el runtime científico
COPY docker/requirements-inference.txt /app/requirements-inference.txt
RUN /azureml-envs/azureml-automl/bin/pip install --no-cache-dir -r /app/requirements-inference.txt

# 2. Copiar código fuente y configuración declarativa del proyecto
# Nota: .dockerignore (y docker/Dockerfile.dockerignore) excluyen secretos, datasets brutos, caches y entornos virtuales
COPY src/ /app/src/
COPY config/ /app/config/

# 3. Incorporar el artefacto predictivo MLflow oficial certificado (670 KB, SHA-256 verificado)
# Esto convierte la imagen en un artefacto inmutable y autocontenido (Opción C),
# eliminando costos y complejidad de almacenamiento externo (Azure Files / Blob Storage).
COPY models/wheat_cheese_4swj34tkjn/model_asset_v1/azureml_wheat_cheese_4swj34tkjn_11_output_mlflow_log_model_873731674/mlflow-model/ /app/models/

# 4. Configurar permisos para directorios de trabajo y logs
RUN mkdir -p /app/logs && \
    chmod -R 755 /app

# 5. Configurar usuario no privilegiado (Principle of Least Privilege)
RUN useradd -u 10001 -m -s /bin/bash appuser && \
    chown -R appuser:appuser /app

USER appuser

# Exponer puerto HTTP estándar
EXPOSE 8000

# Sonda de salud nativa en Python (sin depender de binarios externos como curl o wget)
HEALTHCHECK --interval=30s --timeout=5s --start-period=35s --retries=3 \
    CMD /azureml-envs/azureml-automl/bin/python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/health/live', timeout=4)" || exit 1

# Comando de arranque: 1 worker ASGI dedicado para evitar contención de GIL en cómputo de inferencia
CMD ["uvicorn", "src.api.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "1", "--no-access-log"]
