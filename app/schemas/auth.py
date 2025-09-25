from pydantic import BaseModel, EmailStr
from typing import Optional
from datetime import datetime

class UserLogin(BaseModel):
    email: EmailStr
    password: str

class UserRegister(BaseModel):
    username: str
    email: EmailStr
    password: str

class UserResponse(BaseModel):
    id: int
    username: str
    email: str
    is_active: bool
    is_admin: bool
    created_at: datetime
    
    class Config:
        from_attributes = True

class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int
    # Ajout de la clé API dans la réponse
    api_key: Optional[str] = None
    api_key_expires_at: Optional[datetime] = None

class TokenRefresh(BaseModel):
    refresh_token: str

# Nouveau modèle pour le renouvellement de clé API
class ApiKeyRenewalRequest(BaseModel):
    user_id: int
    payment_reference: Optional[str] = None  # Référence de paiement
    subscription_type: str = "premium"  # ou "basic", etc.
    renewal_days: int = 365  # Durée du renouvellement

class ApiKeyRenewalResponse(BaseModel):
    success: bool
    new_api_key: str
    expires_at: datetime
    message: str