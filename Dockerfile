FROM python:3.9-slim

# Définir le répertoire de travail
WORKDIR /app

# Copier les fichiers nécessaires
COPY requirements.txt ./
COPY app.py ./
COPY . .

# Installer les dépendances
RUN pip install --no-cache-dir -r requirements.txt

# Exposer le port FastAPI
EXPOSE 8000

# Définir la variable d'environnement (sera passée depuis .env)
ARG GROQ_API_KEY
ENV GROQ_API_KEY=${GROQ_API_KEY}

# Commande pour lancer l'app (via uvicorn)
CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8000"]
