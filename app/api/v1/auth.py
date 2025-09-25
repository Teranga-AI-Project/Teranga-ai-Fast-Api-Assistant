from datetime import timedelta
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.security import security, settings
from app.models.user import User
from app.schemas.auth import UserLogin, UserRegister, UserResponse, TokenResponse, TokenRefresh
from app.api.deps import get_current_user
from app.services.auto_api_key_service import AutoApiKeyService

router = APIRouter()

@router.post("/register", response_model=TokenResponse)
def register_user(user_data: UserRegister, db: Session = Depends(get_db)):
    """Inscription d'un nouvel utilisateur avec clé API automatique"""
    # Vérifier si l'utilisateur existe
    if db.query(User).filter(User.email == user_data.email).first():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered"
        )
    
    # if db.query(User).filter(User.username == user_data.username).first():
    #     raise HTTPException(
    #         status_code=status.HTTP_400_BAD_REQUEST,
    #         detail="Username already taken"
    #     )
    
    # Créer l'utilisateur
    hashed_password = security.hash_password(user_data.password)
    db_user = User(
        username=user_data.username,
        email=user_data.email,
        hashed_password=hashed_password,
        has_trial_api_key=True,
        subscription_type="trial"
    )
    
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    
    # Créer automatiquement la clé API d'essai
    trial_api_key = AutoApiKeyService.create_trial_api_key(db_user, db)
    
    # Créer les tokens JWT
    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = security.create_access_token(
        data={"sub": str(db_user.id), "username": db_user.username, "is_admin": db_user.is_admin},
        expires_delta=access_token_expires
    )
    
    refresh_token = security.create_refresh_token(
        data={"sub": str(db_user.id)}
    )
    
    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        api_key=trial_api_key._plain_key,
        api_key_expires_at=trial_api_key.expires_at
    )

@router.post("/login", response_model=TokenResponse)
def login_user(credentials: UserLogin, db: Session = Depends(get_db)):
    """Connexion utilisateur avec information de clé API"""
    user = db.query(User).filter(User.email == credentials.email).first()
    
    if not user or not security.verify_password(credentials.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials"
        )
    
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User account disabled"
        )
    
    # Créer les tokens
    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = security.create_access_token(
        data={"sub": str(user.id), "username": user.username, "is_admin": user.is_admin},
        expires_delta=access_token_expires
    )
    
    refresh_token = security.create_refresh_token(
        data={"sub": str(user.id)}
    )
    
    # Vérifier l'état de la clé API
    api_key_status = AutoApiKeyService.check_api_key_expiry(user.id, db)
    
    
    response = TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60
    )
    
    # Ajouter les infos de clé API si elle existe et est active
    if api_key_status.get("has_active_key"):
        new_api_key, expires_at = AutoApiKeyService.renew_api_key(
            user_id=user.id,
            renewal_days=api_key_status.get("days_remaining", 0),
            subscription_type=api_key_status.get("subscription_type", "trial"),
            action="login",
            db=db
        )
        response.api_key_expires_at = api_key_status.get("expires_at")
        response.api_key = new_api_key
    
    return response

# Nouvel endpoint pour le renouvellement
@router.post("/renew-api-key", response_model=dict)
def renew_api_key(
    renewal_request: dict,  # {"payment_reference": "...", "subscription_type": "premium"}
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Renouveler la clé API après paiement"""
    try:
        payment_reference = renewal_request.get("payment_reference")
        subscription_type = renewal_request.get("subscription_type", "premium")
        renewal_days = renewal_request.get("renewal_days", 365)
        
        # Ici vous pourriez ajouter une vérification de paiement
        # if not verify_payment(payment_reference):
        #     raise HTTPException(status_code=400, detail="Payment verification failed")
        
        new_api_key, expires_at = AutoApiKeyService.renew_api_key(
            user_id=current_user.id,
            renewal_days=renewal_days,
            subscription_type=subscription_type,
            payment_reference=payment_reference,
            db=db
        )
        
        return {
            "success": True,
            "message": "Clé API renouvelée avec succès",
            "new_api_key": new_api_key,
            "expires_at": expires_at,
            "subscription_type": subscription_type
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Erreur lors du renouvellement: {str(e)}"
        )

@router.get("/api-key-status")
def get_api_key_status(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Obtenir le statut de la clé API de l'utilisateur"""
    return AutoApiKeyService.check_api_key_expiry(current_user.id, db)

@router.post("/refresh", response_model=TokenResponse)
def refresh_token(token_data: TokenRefresh, db: Session = Depends(get_db)):
    """Rafraîchir le token d'accès"""
    payload = security.verify_token(token_data.refresh_token, "refresh")
    user_id = payload.get("sub")
    
    user = db.query(User).filter(User.id == user_id).first()
    if not user or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid refresh token"
        )
    
    # Créer un nouveau token d'accès
    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = security.create_access_token(
        data={"sub": str(user.id), "username": user.username, "is_admin": user.is_admin},
        expires_delta=access_token_expires
    )
    
    return TokenResponse(
        access_token=access_token,
        refresh_token=token_data.refresh_token,
        expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60
    )

@router.get("/me", response_model=UserResponse)
def get_current_user_info(current_user: User = Depends(get_current_user)):
    """Obtenir les informations de l'utilisateur connecté"""
    return current_user