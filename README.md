Fast API Voice Assistant:

# Teranga AI - FastAPI Voice & Chat Assistant

**Teranga AI FastAPI Assistant** est une API conversationnelle multilingue qui combine :

- Reconnaissance vocale (STT – Speech-to-Text)
- Synthèse vocale (TTS – Text-to-Speech)
- Modèle LLM pour la génération de réponses (Groq Llama 3.1)
- Gestion complète des conversations pour applications mobiles et web

Cette API est optimisée pour un usage mobile avec des temps de réponse rapides, la détection automatique de la langue et le support audio/textuel bidirectionnel.

---

## 🔹 Fonctionnalités

1. **Chat Textuel**
   - Recevoir un texte d’utilisateur
   - Détecter automatiquement la langue
   - Générer une réponse avec LLM
   - Retourner la réponse sous forme texte et audio (Base64)

2. **Chat Vocal**
   - Recevoir un fichier audio utilisateur
   - Transcrire l’audio en texte (STT)
   - Détecter la langue automatiquement
   - Générer réponse LLM et audio
   - Retourner la transcription, l’audio original et la réponse audio (Base64)

3. **Endpoints dédiés**
   - `/chat_text/` – Chat textuel avec TTS
   - `/chat_audio/` – Chat vocal avec STT + TTS
   - `/tts/` – Générer audio à partir d’un texte
   - `/stt/` – Transcrire un audio en texte

4. **Optimisations Mobile**
   - Limitation des tokens pour réduire la latence LLM
   - Audio traité en mono 16kHz pour accélérer STT
   - Fichiers temporaires en mémoire (BytesIO) au lieu du disque
   - Compression Base64 possible pour envoi mobile
   - HTTPS obligatoire pour les communications sécurisées

---

## 🔹 Installation

1. Cloner le dépôt :

```bash
git clone https://github.com/<votre-utilisateur>/Teranga-ai-Fast-Api-Assistant.git
cd Teranga-ai-Fast-Api-Assistant
Créer un environnement Python et installer les dépendances :

python3 -m venv venv
source venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
Lancer le serveur FastAPI en local :

uvicorn app:app --host 0.0.0.0 --port 8000 --reload
Accéder à la documentation Swagger :

http://localhost:8000/docs

🔹 Docker
Construire l’image Docker :

docker build -t teranga-ai-api .
Lancer le conteneur :

docker run -d -p 8000:8000 teranga-ai-api

🔹 Déploiement sur VPS (exemple expert)
Installer Docker et Docker Compose sur le VPS

Cloner le repo et construire l’image

Lancer le conteneur Docker

Configurer un reverse proxy Nginx + HTTPS (Certbot)

Tester l’API via HTTPS

🔹 Exemple d’utilisation avec curl
Chat textuel
curl -X POST "https://api.terangaai.com/chat_text/" \
-H "Content-Type: application/json" \
-d '{"message":"Bonjour"}'
Chat vocal
curl -X POST "https://api.terangaai.com/chat_audio/" \
-H "Content-Type: multipart/form-data" \
-F "file=@mon_audio.wav"

🔹 Structure du projet
Teranga-ai-Fast-Api-Assistant/
│
├─ app.py               # Script principal FastAPI
├─ requirements.txt     # Dépendances Python
├─ Dockerfile           # Dockerisation
├─ .gitignore
├─ logo.png             # Logo de l'assistant
└─ README.md

🔹 Sécurité & Bonnes pratiques
Toujours utiliser HTTPS pour les applications mobiles

Stocker la clé API Groq dans un fichier .env ou un secret manager

Limiter les tokens LLM pour réduire la latence et les coûts

Traiter les fichiers audio en mémoire pour accélérer STT/TTS

Compresser les données Base64 pour réduire la bande passante mobile

🔹 Contact
👨‍💻 Moustapha NDIAYE – Senior AI Developer @ Teranga AI
🌐 Site web : terangaai.com
📧 Email : infos@terangaai.com
📞 Téléphone : +221 77 784 01 61


