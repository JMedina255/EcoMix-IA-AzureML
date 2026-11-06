# ==============================================================================
# EcoMix IA — Dockerfile de Inferencia en Producción (Azure Container Apps)
# ==============================================================================
# Base: Imagen oficial curada de Azure AutoML para Tabular/Ensemble
#       (Ubuntu 20.04/22.04, Python 3.10.19, scikit-learn 1.5.1,
#        azureml-training-tabular 1.61.0, mlflow-skinny 2.15.1 preinstalados en amlenv).
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
    PATH="/opt/miniconda/envs/amlenv/bin:$PATH"

WORKDIR /app

# 1. Instalar dependencias adicionales de la API Web sobre el runtime científico
COPY docker/requirements-inference.txt /app/requirements-inference.txt
RUN /opt/miniconda/envs/amlenv/bin/pip install --no-cache-dir -r /app/requirements-inference.txt

# 2. Copiar código fuente y configuración declarativa del proyecto
# Nota: docker/.dockerignore excluye secretos, datasets brutos, caches y modelos .pkl
COPY src/ /app/src/
COPY config/ /app/config/

# 3. Crear directorios para montaje seguro del modelo en tiempo de ejecución
# Se otorga permiso de lectura y ejecución universal para compatibilidad con montajes de volumen
RUN mkdir -p /app/models /app/logs && \
    chmod -R 755 /app

# 4. Configurar usuario no privilegiado (Principle of Least Privilege)
RUN useradd -u 10001 -m -s /bin/bash appuser && \
    chown -R appuser:appuser /app

USER appuser

# Exponer puerto HTTP estándar
EXPOSE 8000

# Sonda de salud nativa en Python (sin depender de binarios externos como curl o wget)
HEALTHCHECK --interval=30s --timeout=5s --start-period=35s --retries=3 \
    CMD /opt/miniconda/envs/amlenv/bin/python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/health/live', timeout=4)" || exit 1

# Comando de arranque: 1 worker ASGI dedicado para evitar contención de GIL en cómputo de inferencia
CMD ["uvicorn", "src.api.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "1", "--no-access-log"]
