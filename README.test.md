# Fichiers de configuration pour Teranga AI Platform

## requirements.txt
```txt
fastapi==0.104.1
uvicorn[standard]==0.24.0
sqlalchemy==2.0.23
psycopg2-binary==2.9.9
alembic==1.13.1
pydantic==2.5.2
pydantic-settings==2.1.0
python-jose[cryptography]==3.3.0
passlib[bcrypt]==1.7.4
python-multipart==0.0.6
httpx==0.25.2
pytest==7.4.3
pytest-asyncio==0.21.1
```

## .env (exemple)
```env
# Base de données Supabase (projet-b)
DATABASE_URL=postgresql://username:password@db.supabase.co:5432/postgres

# Sécurité
SECRET_KEY=your-super-secret-key-here-change-in-production
ACCESS_TOKEN_EXPIRE_MINUTES=30
REFRESH_TOKEN_EXPIRE_DAYS=7
API_KEY_EXPIRE_DAYS=365

# CORS (à ajuster selon vos besoins)
ALLOWED_ORIGINS=["http://localhost:3000", "https://your-flutter-app.com"]

# Rate Limiting
RATE_LIMIT_REQUESTS=1000
RATE_LIMIT_PERIOD=3600
```

## docker-compose.yml
```yaml
version: '3.8'

services:
  api:
    build: .
    container_name: teranga_api
    ports:
      - "8000:8000"
    environment:
      - DATABASE_URL=${DATABASE_URL}
      - SECRET_KEY=${SECRET_KEY}
    volumes:
      - ./app:/app
    restart: unless-stopped
    depends_on:
      - redis

  redis:
    image: redis:7-alpine
    container_name: teranga_redis
    ports:
      - "6379:6379"
    restart: unless-stopped

  nginx:
    image: nginx:alpine
    container_name: teranga_nginx
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - ./nginx.conf:/etc/nginx/nginx.conf
      - ./ssl:/etc/ssl/certs
    depends_on:
      - api
    restart: unless-stopped
```

## Dockerfile
```dockerfile
FROM python:3.11-slim

WORKDIR /app

# Installation des dépendances système
RUN apt-get update && apt-get install -y \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Installation des dépendances Python
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copie du code
COPY ./app /app

# Variables d'environnement
ENV PYTHONPATH=/app
ENV PYTHONUNBUFFERED=1

# Exposition du port
EXPOSE 8000

# Commande de démarrage
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
```

## alembic.ini (pour les migrations de base de données)
```ini
[alembic]
script_location = alembic
prepend_sys_path = .
version_path_separator = os
sqlalchemy.url = driver://user:pass@localhost/dbname

[post_write_hooks]

[loggers]
keys = root,sqlalchemy,alembic

[handlers]
keys = console

[formatters]
keys = generic

[logger_root]
level = WARN
handlers = console
qualname =

[logger_sqlalchemy]
level = WARN
handlers =
qualname = sqlalchemy.engine

[logger_alembic]
level = INFO
handlers =
qualname = alembic

[handler_console]
class = StreamHandler
args = (sys.stderr,)
level = NOTSET
formatter = generic

[formatter_generic]
format = %(levelname)-5.5s [%(name)s] %(message)s
datefmt = %H:%M:%S
```

## Script de migration initial (alembic/versions/001_initial_migration.py)
```python
"""Initial migration

Revision ID: 001
Revises: 
Create Date: 2024-01-01 10:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers
revision = '001'
down_revision = None
branch_labels = None
depends_on = None

def upgrade() -> None:
    # Table users
    op.create_table('users',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('email', sa.String(), nullable=False),
        sa.Column('username', sa.String(), nullable=False),
        sa.Column('hashed_password', sa.String(), nullable=False),
        sa.Column('is_active', sa.Boolean(), nullable=True),
        sa.Column('is_admin', sa.Boolean(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_users_id'), 'users', ['id'], unique=False)
    op.create_index(op.f('ix_users_email'), 'users', ['email'], unique=True)
    op.create_index(op.f('ix_users_username'), 'users', ['username'], unique=True)

    # Table api_keys
    op.create_table('api_keys',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(), nullable=False),
        sa.Column('key_hash', sa.String(), nullable=False),
        sa.Column('key_prefix', sa.String(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('is_active', sa.Boolean(), nullable=True),
        sa.Column('last_used_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('expires_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('permissions', sa.Text(), nullable=True),
        sa.Column('usage_count', sa.Integer(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_api_keys_key_hash'), 'api_keys', ['key_hash'], unique=True)
    op.create_index(op.f('ix_api_keys_key_prefix'), 'api_keys', ['key_prefix'], unique=False)

    # Table audit_logs
    op.create_table('audit_logs',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=True),
        sa.Column('api_key_id', sa.Integer(), nullable=True),
        sa.Column('action', sa.String(), nullable=False),
        sa.Column('endpoint', sa.String(), nullable=True),
        sa.Column('ip_address', sa.String(), nullable=True),
        sa.Column('user_agent', sa.Text(), nullable=True),
        sa.Column('status_code', sa.Integer(), nullable=True),
        sa.Column('request_data', sa.JSON(), nullable=True),
        sa.Column('response_data', sa.JSON(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.ForeignKeyConstraint(['api_key_id'], ['api_keys.id'], ),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id')
    )

def downgrade() -> None:
    op.drop_table('audit_logs')
    op.drop_table('api_keys')
    op.drop_table('users')
```

## nginx.conf (pour la production)
```nginx
events {
    worker_connections 1024;
}

http {
    upstream teranga_api {
        server api:8000;
    }

    # Rate limiting
    limit_req_zone $binary_remote_addr zone=api_limit:10m rate=10r/s;
    
    server {
        listen 80;
        server_name your-domain.com;
        
        # Redirection HTTPS
        return 301 https://$server_name$request_uri;
    }

    server {
        listen 443 ssl http2;
        server_name your-domain.com;

        # Configuration SSL
        ssl_certificate /etc/ssl/certs/cert.pem;
        ssl_certificate_key /etc/ssl/certs/key.pem;
        ssl_protocols TLSv1.2 TLSv1.3;
        ssl_ciphers HIGH:!aNULL:!MD5;

        # Headers de sécurité
        add_header X-Frame-Options DENY;
        add_header X-Content-Type-Options nosniff;
        add_header X-XSS-Protection "1; mode=block";
        add_header Strict-Transport-Security "max-age=31536000; includeSubDomains" always;

        location / {
            # Rate limiting
            limit_req zone=api_limit burst=20 nodelay;
            
            proxy_pass http://teranga_api;
            proxy_set_header Host $host;
            proxy_set_header X-Real-IP $remote_addr;
            proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
            proxy_set_header X-Forwarded-Proto $scheme;
            
            # Timeouts
            proxy_connect_timeout 60s;
            proxy_send_timeout 60s;
            proxy_read_timeout 60s;
        }

        # Gestion des fichiers statiques (si nécessaire)
        location /static/ {
            alias /app/static/;
            expires 1y;
            add_header Cache-Control "public, immutable";
        }
    }
}
```

## Makefile (pour faciliter le développement)
```makefile
.PHONY: install dev test migrate upgrade downgrade docker-build docker-up docker-down

# Installation des dépendances
install:
	pip install -r requirements.txt

# Mode développement
dev:
	uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# Tests
test:
	pytest tests/ -v

# Migrations de base de données
migrate:
	alembic revision --autogenerate -m "$(message)"

upgrade:
	alembic upgrade head

downgrade:
	alembic downgrade -1

# Docker
docker-build:
	docker-compose build

docker-up:
	docker-compose up -d

docker-down:
	docker-compose down

docker-logs:
	docker-compose logs -f api

# Production
deploy:
	docker-compose -f docker-compose.prod.yml up -d

# Nettoyage
clean:
	find . -type f -name "*.pyc" -delete
	find . -type d -name "__pycache__" -delete
	find . -type d -name ".pytest_cache" -exec rm -rf {} +
```

## Tests d'exemple (tests/test_api.py)
```python
import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.core.database import get_db
from app.core.security import security

client = TestClient(app)

def test_root_endpoint():
    response = client.get("/")
    assert response.status_code == 200
    assert response.json()["message"] == "Teranga AI API Platform"

def test_health_check():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "healthy"

def test_user_registration():
    user_data = {
        "username": "testuser",
        "email": "test@example.com",
        "password": "testpassword123"
    }
    response = client.post("/api/v1/auth/register", json=user_data)
    assert response.status_code == 200
    assert response.json()["email"] == user_data["email"]

def test_user_login():
    login_data = {
        "email": "test@example.com",
        "password": "testpassword123"
    }
    response = client.post("/api/v1/auth/login", json=login_data)
    assert response.status_code == 200
    assert "access_token" in response.json()
    assert "refresh_token" in response.json()

def test_api_key_creation():
    # D'abord se connecter pour obtenir un token
    login_data = {"email": "test@example.com", "password": "testpassword123"}
    login_response = client.post("/api/v1/auth/login", json=login_data)
    token = login_response.json()["access_token"]
    
    # Créer une clé API
    key_data = {"name": "Test API Key"}
    headers = {"Authorization": f"Bearer {token}"}
    response = client.post("/api/v1/api-keys/create", json=key_data, headers=headers)
    
    assert response.status_code == 200
    assert response.json()["api_key"].startswith("tk-proj_")

def test_chat_completion_with_api_key():
    # Utiliser une clé API générée pour tester l'endpoint
    api_key = "tk-proj_example_key_for_testing"
    headers = {"Authorization": f"Bearer {api_key}"}
    
    chat_data = {
        "messages": [{"role": "user", "content": "Hello, Teranga AI!"}],
        "model": "teranga-1"
    }
    
    response = client.post("/api/v1/chat/completions", json=chat_data, headers=headers)
    # Note: Ce test échouera sans une vraie clé API en base
    # Il faudrait mocker la base de données pour les tests
```

## Guide de déploiement (DEPLOYMENT.md)
```markdown
# Guide de déploiement Teranga AI Platform

## Prérequis
- Python 3.11+
- PostgreSQL (Supabase projet-b)
- Redis (pour le cache et rate limiting)
- Nginx (pour la production)
- Docker & Docker Compose (optionnel)

## Configuration de la base de données Supabase

1. **Créer les tables dans Supabase (projet-b)**
```sql
-- Exécuter ces requêtes dans l'éditeur SQL de Supabase

-- Table users
CREATE TABLE users (
    id SERIAL PRIMARY KEY,
    email VARCHAR UNIQUE NOT NULL,
    username VARCHAR UNIQUE NOT NULL,
    hashed_password VARCHAR NOT NULL,
    is_active BOOLEAN DEFAULT TRUE,
    is_admin BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE
);

-- Index pour les performances
CREATE INDEX idx_users_email ON users(email);
CREATE INDEX idx_users_username ON users(username);

-- Table api_keys
CREATE TABLE api_keys (
    id SERIAL PRIMARY KEY,
    name VARCHAR NOT NULL,
    key_hash VARCHAR UNIQUE NOT NULL,
    key_prefix VARCHAR NOT NULL,
    user_id INTEGER REFERENCES users(id),
    is_active BOOLEAN DEFAULT TRUE,
    last_used_at TIMESTAMP WITH TIME ZONE,
    expires_at TIMESTAMP WITH TIME ZONE,
    permissions TEXT,
    usage_count INTEGER DEFAULT 0,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX idx_api_keys_hash ON api_keys(key_hash);
CREATE INDEX idx_api_keys_user ON api_keys(user_id);

-- Table audit_logs
CREATE TABLE audit_logs (
    id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES users(id),
    api_key_id INTEGER REFERENCES api_keys(id),
    action VARCHAR NOT NULL,
    endpoint VARCHAR,
    ip_address INET,
    user_agent TEXT,
    status_code INTEGER,
    request_data JSONB,
    response_data JSONB,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX idx_audit_logs_user ON audit_logs(user_id);
CREATE INDEX idx_audit_logs_created ON audit_logs(created_at);
```

## Installation locale

1. **Cloner le projet**
```bash
git clone <your-repo>
cd teranga-api-platform
```

2. **Créer l'environnement virtuel**
```bash
python -m venv venv
source venv/bin/activate  # Sur Windows: venv\Scripts\activate
```

3. **Installer les dépendances**
```bash
pip install -r requirements.txt
```

4. **Configurer les variables d'environnement**
```bash
cp .env.example .env
# Éditer .env avec vos configurations
```

5. **Lancer l'application**
```bash
# Mode développement
make dev

# Ou directement
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

## Déploiement Docker

1. **Construction et lancement**
```bash
# Construction
docker-compose build

# Lancement
docker-compose up -d

# Vérifier les logs
docker-compose logs -f api
```

## Déploiement en production

1. **Configuration Nginx**
- Copier le fichier `nginx.conf` fourni
- Obtenir des certificats SSL (Let's Encrypt recommandé)
- Ajuster les domaines dans la configuration

2. **Variables d'environnement de production**
```env
DATABASE_URL=postgresql://user:pass@your-supabase-url/postgres
SECRET_KEY=your-super-secret-production-key-256-bits
ALLOWED_ORIGINS=["https://your-flutter-app.com", "https://your-dashboard.com"]
```

3. **Lancement en production**
```bash
docker-compose -f docker-compose.prod.yml up -d
```

## Tests de l'API

### 1. Test d'authentification
```bash
# Inscription
curl -X POST "http://localhost:8000/api/v1/auth/register" \
     -H "Content-Type: application/json" \
     -d '{
       "username": "testuser",
       "email": "test@example.com", 
       "password": "securepassword123"
     }'

# Connexion
curl -X POST "http://localhost:8000/api/v1/auth/login" \
     -H "Content-Type: application/json" \
     -d '{
       "email": "test@example.com",
       "password": "securepassword123"
     }'
```

### 2. Création de clé API
```bash
# Récupérer le token JWT de la réponse de connexion
TOKEN="eyJ0eXAiOiJKV1QiLCJhbGc..."

# Créer une clé API
curl -X POST "http://localhost:8000/api/v1/api-keys/create" \
     -H "Authorization: Bearer $TOKEN" \
     -H "Content-Type: application/json" \
     -d '{
       "name": "Flutter App Key",
       "expires_in_days": 365
     }'
```

### 3. Test des endpoints IA
```bash
# Utiliser la clé API créée
API_KEY="tk-proj_your_generated_key_here"

# Chat completion (compatible OpenAI)
curl -X POST "http://localhost:8000/api/v1/chat/completions" \
     -H "Authorization: Bearer $API_KEY" \
     -H "Content-Type: application/json" \
     -d '{
       "messages": [
         {"role": "user", "content": "Bonjour, comment allez-vous?"}
       ],
       "model": "teranga-1",
       "max_tokens": 150
     }'

# Text completion
curl -X POST "http://localhost:8000/api/v1/completions" \
     -H "Authorization: Bearer $API_KEY" \
     -H "Content-Type: application/json" \
     -d '{
       "prompt": "La capitale du Sénégal est",
       "model": "teranga-1",
       "max_tokens": 50
     }'

# Liste des modèles
curl -X GET "http://localhost:8000/api/v1/models" \
     -H "Authorization: Bearer $API_KEY"
```

## Monitoring et maintenance

### Logs
```bash
# Voir les logs en temps réel
docker-compose logs -f api

# Logs d'une période spécifique
docker-compose logs --since="2024-01-01T00:00:00" api
```

### Base de données
```sql
-- Statistiques d'usage
SELECT 
    u.username,
    COUNT(ak.id) as api_keys_count,
    SUM(ak.usage_count) as total_api_calls
FROM users u 
LEFT JOIN api_keys ak ON u.id = ak.user_id 
GROUP BY u.id, u.username;

-- Clés API les plus utilisées
SELECT 
    ak.name,
    ak.usage_count,
    ak.last_used_at,
    u.username
FROM api_keys ak
JOIN users u ON ak.user_id = u.id
WHERE ak.is_active = true
ORDER BY ak.usage_count DESC
LIMIT 10;

-- Activité récente
SELECT 
    action,
    COUNT(*) as count,
    DATE(created_at) as date
FROM audit_logs 
WHERE created_at >= NOW() - INTERVAL '7 days'
GROUP BY action, DATE(created_at)
ORDER BY date DESC, count DESC;
```

## Sécurité

### Recommandations de production
1. **Changer les clés secrètes** : Générer de nouvelles clés pour la production
2. **HTTPS obligatoire** : Configurer SSL/TLS avec des certificats valides
3. **Rate limiting** : Configurer des limites adaptées à votre usage
4. **CORS restrictif** : Limiter les origines autorisées
5. **Monitoring** : Mettre en place des alertes pour les activités suspectes
6. **Backups** : Sauvegarder régulièrement la base de données
7. **Updates** : Maintenir les dépendances à jour

### Rotation des clés API
```python
# Script de rotation automatique (à exécuter périodiquement)
from app.core.database import SessionLocal
from app.models.api_key import APIKey
from datetime import datetime, timedelta

db = SessionLocal()
expired_keys = db.query(APIKey).filter(
    APIKey.expires_at < datetime.utcnow(),
    APIKey.is_active == True
).all()

for key in expired_keys:
    key.is_active = False
    print(f"Clé expirée désactivée: {key.name}")

db.commit()
db.close()
```
```

## Structure finale des endpoints

### Authentification (JWT Admin)
- `POST /api/v1/auth/register` - Inscription
- `POST /api/v1/auth/login` - Connexion  
- `POST /api/v1/auth/refresh` - Rafraîchir token
- `GET /api/v1/auth/me` - Profil utilisateur

### Gestion des clés API
- `POST /api/v1/api-keys/create` - Créer une clé
- `GET /api/v1/api-keys/list` - Lister les clés
- `DELETE /api/v1/api-keys/{id}` - Révoquer une clé
- `PUT /api/v1/api-keys/{id}/regenerate` - Régénérer une clé

### API Teranga AI (Authentification par clé API)
- `POST /api/v1/chat/completions` - Chat completion
- `POST /api/v1/completions` - Text completion  
- `GET /api/v1/models` - Liste des modèles

### Administration (JWT Admin uniquement)
- `GET /api/v1/admin/stats` - Statistiques globales
- `GET /api/v1/admin/users` - Liste des utilisateurs
- `PUT /api/v1/admin/users/{id}/toggle-status` - Activer/désactiver
- `DELETE /api/v1/admin/users/{id}/api-keys` - Révoquer toutes les clés

Cette plateforme offre :
- ✅ **Multi-clients** avec authentification flexible
- ✅ **Sécurité robuste** (JWT HS256, bcrypt, SHA-256)
- ✅ **Auto-gestion** des clés API
- ✅ **Compatibilité OpenAI** pour faciliter l'intégration
- ✅ **Monitoring complet** avec audit logs
- ✅ **Scalabilité** avec Docker et Nginx
- ✅ **Intégration Supabase** pour la base de données