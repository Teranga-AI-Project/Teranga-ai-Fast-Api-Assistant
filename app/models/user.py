from sqlalchemy import Column, Integer, String, DateTime, Boolean, Text
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from app.core.database import Base
from app.core.config import settings
from datetime import datetime, timedelta

class User(Base):
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True, nullable=False)
    username = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    is_active = Column(Boolean, default=True)
    is_admin = Column(Boolean, default=False)
    
    # Nouveaux champs pour le système de clés API automatiques
    has_trial_api_key = Column(Boolean, default=True)
    trial_api_key_created_at = Column(DateTime(timezone=True), default=func.now())
    subscription_type = Column(String, default="trial")  # trial, premium, basic
    subscription_expires_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.utcnow() + timedelta(days=settings.TRIAL_API_KEY_DAYS)
    )
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relations
    api_keys = relationship("APIKey", back_populates="owner")
    audit_logs = relationship("AuditLog", back_populates="user")