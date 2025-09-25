from typing import List
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from sqlalchemy import func
from pydantic import BaseModel
from app.core.database import get_db
from app.models.user import User
from app.models.api_key import APIKey
from app.models.audit import AuditLog
from app.api.deps import get_current_admin_user
from datetime import datetime, timedelta

router = APIRouter()

class AdminStats(BaseModel):
    total_users: int
    active_users: int
    total_api_keys: int
    active_api_keys: int
    api_calls_today: int
    api_calls_week: int

class UserAdmin(BaseModel):
    id: int
    username: str
    email: str
    is_active: bool
    is_admin: bool
    api_keys_count: int
    created_at: datetime

@router.get("/stats", response_model=AdminStats)
def get_admin_stats(
    admin_user: User = Depends(get_current_admin_user),
    db: Session = Depends(get_db)
):
    """Statistiques d'administration"""
    today = datetime.utcnow().date()
    week_ago = datetime.utcnow() - timedelta(days=7)
    
    return AdminStats(
        total_users=db.query(User).count(),
        active_users=db.query(User).filter(User.is_active == True).count(),
        total_api_keys=db.query(APIKey).count(),
        active_api_keys=db.query(APIKey).filter(APIKey.is_active == True).count(),
        api_calls_today=db.query(AuditLog).filter(
            func.date(AuditLog.created_at) == today,
            AuditLog.action == "api_call"
        ).count(),
        api_calls_week=db.query(AuditLog).filter(
            AuditLog.created_at >= week_ago,
            AuditLog.action == "api_call"
        ).count()
    )

@router.get("/users", response_model=List[UserAdmin])
def list_all_users(
    admin_user: User = Depends(get_current_admin_user),
    db: Session = Depends(get_db),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000)
):
    """Lister tous les utilisateurs"""
    users = db.query(User).offset(skip).limit(limit).all()
    
    result = []
    for user in users:
        api_keys_count = db.query(APIKey).filter(APIKey.user_id == user.id).count()
        result.append(UserAdmin(
            id=user.id,
            username=user.username,
            email=user.email,
            is_active=user.is_active,
            is_admin=user.is_admin,
            api_keys_count=api_keys_count,
            created_at=user.created_at
        ))
    
    return result

@router.put("/users/{user_id}/toggle-status")
def toggle_user_status(
    user_id: int,
    admin_user: User = Depends(get_current_admin_user),
    db: Session = Depends(get_db)
):
    """Activer/désactiver un utilisateur"""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    user.is_active = not user.is_active
    db.commit()
    
    return {"message": f"User {'activated' if user.is_active else 'deactivated'} successfully"}

@router.delete("/users/{user_id}/api-keys")
def revoke_all_user_api_keys(
    user_id: int,
    admin_user: User = Depends(get_current_admin_user),
    db: Session = Depends(get_db)
):
    """Révoquer toutes les clés API d'un utilisateur"""
    keys_updated = db.query(APIKey).filter(APIKey.user_id == user_id).update({"is_active": False})
    db.commit()
    
    return {"message": f"Revoked {keys_updated} API keys"}