# Multi-stage build optimisé pour Railway
FROM python:3.11-slim as builder

# Variables d'environnement pour build
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# Installation des dépendances système pour audio
RUN apt-get update && apt-get install -y \
    ffmpeg \
    libsndfile1 \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Création user pour dependencies
RUN adduser --disabled-password --gecos '' --uid 1000 appuser

# Switch to appuser pour installation packages
USER appuser
WORKDIR /home/appuser

# Copy et installation des requirements
COPY requirements.txt .
RUN pip install --user -r requirements.txt

# Stage final - Production
FROM python:3.11-slim

# Variables d'environnement runtime
ENV PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app \
    PATH=/home/appuser/.local/bin:$PATH

# Installation runtime dependencies seulement
RUN apt-get update && apt-get install -y \
    ffmpeg \
    libsndfile1 \
    && rm -rf /var/lib/apt/lists/* \
    && adduser --disabled-password --gecos '' --uid 1000 appuser

# Copy des dépendances Python installées depuis builder
COPY --from=builder /home/appuser/.local /home/appuser/.local

# Setup application directory
WORKDIR /app
COPY --chown=appuser:appuser . .

# Switch to non-root user
USER appuser

# Expose port
EXPOSE 8000

# Commande de démarrage
CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000} --workers 1"]

