# ==============================================================================
# EcoMix IA — Dockerfile de Inferencia en Producción (Azure Container Apps)
# ==============================================================================
# Base: Imagen oficial curada de Azure AutoML (Python 3.10.19, scikit-learn 1.5.1,
#       azureml-training-tabular 1.61.0, mlflow 2.15.1 preinstalados en /opt/miniconda).
# ==============================================================================

FROM mcr.microsoft.com/azureml/curated/ai-ml-automl:41

LABEL maintainer="EcoMix IA DevSecOps <soporte@ecomix.ia>"
LABEL description="Microservicio FastAPI de inferencia predictiva para EcoMix IA (VotingEnsemble)"
LABEL version="1.0.0"

# Variables de entorno del sistema
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    ECOMIX_ENV=production \
    ECOMIX_HOST=0.0.0.0 \
    ECOMIX_PORT=8000 \
    PATH="/opt/miniconda/envs/amlenv/bin:$PATH"

WORKDIR /app

# 1. Instalar dependencias adicionales de la API Web sobre el runtime de inferencia
COPY docker/requirements-inference.txt /app/requirements-inference.txt
RUN /opt/miniconda/envs/amlenv/bin/pip install --no-cache-dir \
    fastapi==0.115.6 \
    uvicorn[standard]==0.34.0 \
    starlette==0.41.3 \
    pydantic-settings==2.12.0 \
    httpx==0.28.1

# 2. Copiar código fuente y configuración declarativa del proyecto
COPY src/ /app/src/
COPY config/ /app/config/

# 3. Crear directorios para montaje seguro del modelo en tiempo de ejecución
RUN mkdir -p /app/models /app/logs && \
    chmod -R 755 /app

# 4. Configurar usuario no privilegiado (Principle of Least Privilege)
RUN useradd -u 10001 -m -s /bin/bash appuser && \
    chown -R appuser:appuser /app

USER appuser

# Exponer puerto HTTP estándar
EXPOSE 8000

# Sonda de salud a nivel de Docker (complementaria a las sondas de Kubernetes / Azure Container Apps)
HEALTHCHECK --interval=30s --timeout=5s --start-period=35s --retries=3 \
    CMD curl -f http://localhost:8000/health/live || exit 1

# Comando de arranque: 1 worker ASGI dedicado por contenedor para evitar contención de GIL
CMD ["uvicorn", "src.api.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "1", "--no-access-log"]
