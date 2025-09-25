from sqlalchemy import Column, Integer, String, DateTime, Boolean, ForeignKey, Text
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from app.core.database import Base

class APIKey(Base):
    __tablename__ = "api_keys"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)  # Nom donné à la clé
    key_hash = Column(String, unique=True, index=True, nullable=False)  # Hash de la clé
    key_prefix = Column(String, index=True, nullable=False)  # Préfixe pour identification
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    is_active = Column(Boolean, default=True)
    last_used_at = Column(DateTime(timezone=True))
    expires_at = Column(DateTime(timezone=True))
    permissions = Column(Text)  # JSON des permissions
    usage_count = Column(Integer, default=0)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relations
    owner = relationship("User", back_populates="api_keys")
    audit_logs = relationship("AuditLog", back_populates="api_key")