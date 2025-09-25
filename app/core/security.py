from datetime import datetime, timedelta
from typing import Optional, Dict, Any
from jose import jwt
import bcrypt
import secrets
import hashlib
from fastapi import HTTPException, status
from app.core.config import settings

class SecurityManager:
    def __init__(self, secret_key: str):
        self.secret_key = secret_key
        self.algorithm = "HS256"
    
    # JWT Management
    def create_access_token(self, data: Dict[Any, Any], expires_delta: Optional[timedelta] = None) -> str:
        """Créer un token JWT d'accès"""
        to_encode = data.copy()
        if expires_delta:
            expire = datetime.utcnow() + expires_delta
        else:
            expire = datetime.utcnow() + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
        
        to_encode.update({"exp": expire, "type": "access"})
        return jwt.encode(to_encode, self.secret_key, algorithm=self.algorithm)
    
    def create_refresh_token(self, data: Dict[Any, Any]) -> str:
        """Créer un token JWT de refresh"""
        to_encode = data.copy()
        expire = datetime.utcnow() + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
        to_encode.update({"exp": expire, "type": "refresh"})
        return jwt.encode(to_encode, self.secret_key, algorithm=self.algorithm)
    
    def verify_token(self, token: str, token_type: str = "access") -> Dict[Any, Any]:
        """Vérifier et décoder un token JWT"""
        try:
            payload = jwt.decode(token, self.secret_key, algorithms=[self.algorithm])
            if payload.get("type") != token_type:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Invalid token type"
                )
            return payload
        except jwt.ExpiredSignatureError:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token expired"
            )
        except jwt.JWTError:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token"
            )
    
    # Password Management
    def hash_password(self, password: str) -> str:
        """Hasher un mot de passe avec bcrypt"""
        salt = bcrypt.gensalt()
        return bcrypt.hashpw(password.encode('utf-8'), salt).decode('utf-8')
    
    def verify_password(self, password: str, hashed: str) -> bool:
        """Vérifier un mot de passe"""
        return bcrypt.checkpw(password.encode('utf-8'), hashed.encode('utf-8'))
    
    # API Key Management
    def generate_api_key(self, prefix: str = "tk") -> str:
        """Générer une clé API sécurisée"""
        # Format: tk-proj_xxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
        random_part = secrets.token_urlsafe(32)
        return f"{prefix}-proj_{random_part}"
    
    def hash_api_key(self, api_key: str) -> str:
        """Hasher une clé API avec SHA-256"""
        return hashlib.sha256(api_key.encode()).hexdigest()
    
    def verify_api_key_format(self, api_key: str) -> bool:
        """Vérifier le format d'une clé API"""
        return api_key.startswith("tk-proj_") and len(api_key) >= 40

security = SecurityManager(settings.SECRET_KEY)