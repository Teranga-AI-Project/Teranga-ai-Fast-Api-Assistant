from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime

class APIKeyCreate(BaseModel):
    name: str
    permissions: Optional[List[str]] = None
    expires_in_days: Optional[int] = 365

class APIKeyResponse(BaseModel):
    id: int
    name: str
    key_prefix: str
    is_active: bool
    last_used_at: Optional[datetime]
    expires_at: Optional[datetime]
    usage_count: int
    created_at: datetime
    
    class Config:
        from_attributes = True

class APIKeyCreateResponse(BaseModel):
    api_key: str  # La clé complète (à afficher une seule fois)
    key_info: APIKeyResponse

class APIKeyList(BaseModel):
    keys: List[APIKeyResponse]
    total: int