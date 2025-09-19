# Base image
FROM python:3.11-slim

# Set workdir
WORKDIR /app

# Copier le projet et installer les dépendances
COPY . /app
COPY requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Exposer le port FastAPI
EXPOSE 8000

# Définir la variable d'environnement (optionnel)
# ENV GROQ_API_KEY=your_api_key_here

# Commande pour démarrer l’API
CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8000"]
# Utiliser un gestionnaire de processus comme Gunicorn pour la production
# CMD ["gunicorn", "-w", "4", "-k", "uvicorn.workers.UvicornWorker", "app:app", "--bind", "0.0.0.0:8000"]