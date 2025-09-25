from datetime import datetime, timedelta
from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.security import security, settings
from app.models.user import User
from app.models.api_key import APIKey
from app.schemas.api_key import APIKeyCreate, APIKeyResponse, APIKeyCreateResponse, APIKeyList
from app.api.deps import get_current_user
import json

router = APIRouter()

@router.post("/create", response_model=APIKeyCreateResponse)
def create_api_key(
    key_data: APIKeyCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Créer une nouvelle clé API"""
    # Générer la clé API
    api_key = security.generate_api_key()
    key_hash = security.hash_api_key(api_key)
    key_prefix = api_key[:12] + "..."  # Préfixe pour l'affichage
    
    # Date d'expiration
    expires_at = None
    if key_data.expires_in_days:
        expires_at = datetime.utcnow() + timedelta(days=key_data.expires_in_days)
    
    # Créer l'enregistrement en base
    db_key = APIKey(
        name=key_data.name,
        key_hash=key_hash,
        key_prefix=key_prefix,
        user_id=current_user.id,
        expires_at=expires_at,
        permissions=json.dumps(key_data.permissions or [])
    )
    
    db.add(db_key)
    db.commit()
    db.refresh(db_key)
    
    return APIKeyCreateResponse(
        api_key=api_key,
        key_info=APIKeyResponse(
            id=db_key.id,
            name=db_key.name,
            key_prefix=db_key.key_prefix,
            is_active=db_key.is_active,
            last_used_at=db_key.last_used_at,
            expires_at=db_key.expires_at,
            usage_count=db_key.usage_count,
            created_at=db_key.created_at
        )
    )

@router.get("/list", response_model=APIKeyList)
def list_api_keys(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Lister toutes les clés API de l'utilisateur"""
    keys = db.query(APIKey).filter(APIKey.user_id == current_user.id).all()
    
    return APIKeyList(
        keys=[APIKeyResponse(
            id=key.id,
            name=key.name,
            key_prefix=key.key_prefix,
            is_active=key.is_active,
            last_used_at=key.last_used_at,
            expires_at=key.expires_at,
            usage_count=key.usage_count,
            created_at=key.created_at
        ) for key in keys],
        total=len(keys)
    )

@router.delete("/{key_id}")
def revoke_api_key(
    key_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Révoquer une clé API"""
    db_key = db.query(APIKey).filter(
        APIKey.id == key_id,
        APIKey.user_id == current_user.id
    ).first()
    
    if not db_key:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="API key not found"
        )
    
    db_key.is_active = False
    db.commit()
    
    return {"message": "API key revoked successfully"}

@router.put("/{key_id}/regenerate", response_model=APIKeyCreateResponse)
def regenerate_api_key(
    key_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Régénérer une clé API"""
    db_key = db.query(APIKey).filter(
        APIKey.id == key_id,
        APIKey.user_id == current_user.id
    ).first()
    
    if not db_key:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="API key not found"
        )
    
    # Générer une nouvelle clé
    new_api_key = security.generate_api_key()
    new_key_hash = security.hash_api_key(new_api_key)
    new_key_prefix = new_api_key[:12] + "..."
    
    # Mettre à jour la clé
    db_key.key_hash = new_key_hash
    db_key.key_prefix = new_key_prefix
    db_key.usage_count = 0
    db_key.last_used_at = None
    db.commit()
    db.refresh(db_key)
    
    return APIKeyCreateResponse(
        api_key=new_api_key,
        key_info=APIKeyResponse(
            id=db_key.id,
            name=db_key.name,
            key_prefix=db_key.key_prefix,
            is_active=db_key.is_active,
            last_used_at=db_key.last_used_at,
            expires_at=db_key.expires_at,
            usage_count=db_key.usage_count,
            created_at=db_key.created_at
        )
    )