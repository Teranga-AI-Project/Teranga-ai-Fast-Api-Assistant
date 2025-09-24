from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from auth.dependencies import get_db, get_user
from auth.utils import (
    verify_password, 
    get_password_hash, 
    create_access_token, 
    create_refresh_token,
    invalidate_user_tokens,
    verify_refresh_token
)
from users.models import User
from users.schemas import UserCreate, UserSchema
from auth.models import LoginRequest
from pydantic import BaseModel
from datetime import datetime

class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str
    expires_at: datetime
    user: UserSchema

router = APIRouter(prefix="/auth", tags=["auth"])

@router.post("/login", response_model=TokenResponse)
async def login(login_data: LoginRequest, db: Session = Depends(get_db)):
    user = get_user(db, email=login_data.email)
    if not user or not verify_password(login_data.password, user.encrypted_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Nom d'utilisateur ou mot de passe incorrect"
        )
    
    # Supprimer les anciens refresh tokens de ce user
    from users.models import RefreshToken
    db.query(RefreshToken).filter(RefreshToken.user_id == user.id).delete()
    db.commit()
    
    # Invalider les anciens access tokens en incrémentant token_version
    invalidate_user_tokens(db, user)
    access_token, expires_at = create_access_token(data={"sub": user.email}, user=user)
    refresh_token = create_refresh_token(db, user.id)
    
    user_schema = UserSchema.from_orm(user)
    
    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        expires_at=expires_at,
        token_type="bearer",
        user=user_schema
    )


class RefreshRequest(BaseModel):
    refresh_token: str

@router.post("/refresh", response_model=TokenResponse)
async def refresh_token(
    refresh_request: RefreshRequest,
    db: Session = Depends(get_db)
):
    refresh_token = verify_refresh_token(db, refresh_request.refresh_token)
    if not refresh_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired refresh token"
        )
        
    user = refresh_token.user
    # Invalider les anciens access tokens en incrémentant token_version
    invalidate_user_tokens(db, user)
    # Créer un nouveau access token
    access_token, expires_at = create_access_token(data={"sub": user.email}, user=user)
    # Créer un nouveau refresh token
    new_refresh_token = create_refresh_token(db, user.id)
    
    # Supprimer l'ancien refresh token
    db.delete(refresh_token)
    db.commit()
    
    user_schema = UserSchema.from_orm(user)
    
    return TokenResponse(
        access_token=access_token,
        refresh_token=new_refresh_token,
        expires_at=expires_at,
        token_type="bearer",
        user=user_schema
    )


@router.post("/signup", response_model=TokenResponse)
def signup(user: UserCreate, db: Session = Depends(get_db)):
    """Endpoint pour créer un nouvel utilisateur (inscription)"""
    # try:
    db_user = get_user(db, email=user.email)
    if db_user:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Email already registered")
    
    encrypted_password = get_password_hash(user.password)
    new_user = User(email=user.email, encrypted_password=encrypted_password)
    
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    
    # Invalider les anciens access tokens en incrémentant token_version
    invalidate_user_tokens(db, user)
    access_token, expires_at = create_access_token(data={"sub": new_user.email}, user=new_user)
    refresh_token = create_refresh_token(db, new_user.id)
    
    user_schema = UserSchema.from_orm(new_user)
    
    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        expires_at=expires_at,
        token_type="bearer",
        user=user_schema
    )
        
    # except Exception as e:
    #     logging.error(f"Error creating user: {str(e)}")
    #     raise HTTPException(
    #         status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
    #         detail="An error occurred while creating the user"
    #     )
