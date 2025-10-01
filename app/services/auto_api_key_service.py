from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from app.core.security import security
from app.models.user import User
from app.models.api_key import APIKey
import json
from datetime import timezone
from app.core.config import settings
import dotenv
dotenv.load_dotenv()

class AutoApiKeyService:
    @staticmethod
    def create_trial_api_key(user: User, db: Session) -> APIKey:
        """Créer automatiquement une clé API d'essai de 60 jours"""
        
        # Vérifier si l'utilisateur a déjà une clé d'essai
        if user.has_trial_api_key:
            existing_key = db.query(APIKey).filter(
                APIKey.user_id == user.id,
                APIKey.name == "Clé d'essai automatique"
            ).first()
            if existing_key and existing_key.is_active:
                return existing_key
        
        # Générer la clé API
        api_key = security.generate_api_key()
        key_hash = security.hash_api_key(api_key)
        key_prefix = api_key[:12] + "..."
        
        # Date d'expiration : 60 jours
        expires_at = datetime.utcnow() + timedelta(days=settings.TRIAL_API_KEY_DAYS)
        
        # Créer l'enregistrement de clé API
        db_key = APIKey(
            name="Clé d'essai automatique",
            key_hash=key_hash,
            key_prefix=key_prefix,
            user_id=user.id,
            expires_at=expires_at,
            permissions=json.dumps(["chat", "completion", "models"])  # Permissions de base
        )
        
        # Mettre à jour l'utilisateur
        user.has_trial_api_key = True
        user.trial_api_key_created_at = datetime.utcnow()
        user.subscription_expires_at = expires_at
        
        db.add(db_key)
        db.commit()
        db.refresh(db_key)
        
        # Stocker temporairement la clé en clair pour la retourner
        db_key._plain_key = api_key
        
        return db_key
    
    @staticmethod
    def renew_api_key(
        user_id: int, 
        renewal_days: int = 365, 
        subscription_type: str = "premium",
        payment_reference: str = None,
        action: str = "api_key_renewed",
        db: Session = None
    ) -> tuple[str, datetime]:
        """Renouveler la clé API d'un utilisateur"""
        
        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            raise ValueError("Utilisateur non trouvé")
        
        # Trouver la clé API actuelle de l'utilisateur
        current_key = db.query(APIKey).filter(
            APIKey.user_id == user_id,
            APIKey.is_active == True
        ).order_by(APIKey.created_at.desc()).first()
        
        if current_key:
            # Désactiver l'ancienne clé
            current_key.is_active = False
        
        # Créer une nouvelle clé
        new_api_key = security.generate_api_key()
        new_key_hash = security.hash_api_key(new_api_key)
        new_key_prefix = new_api_key[:12] + "..."
        
        # Nouvelle date d'expiration
        new_expires_at = datetime.utcnow() + timedelta(days=renewal_days)
        
        # Créer le nouvel enregistrement
        new_db_key = APIKey(
            name=f"Clé {subscription_type} - {datetime.utcnow().strftime('%Y-%m-%d')}",
            key_hash=new_key_hash,
            key_prefix=new_key_prefix,
            user_id=user_id,
            expires_at=new_expires_at,
            permissions=json.dumps(["chat", "completion", "models", "advanced"] if subscription_type == "premium" else ["chat", "completion", "models"])
        )
        
        # Mettre à jour l'utilisateur
        user.subscription_type = subscription_type
        user.subscription_expires_at = new_expires_at
        
        db.add(new_db_key)
        db.commit()
        
        # Log du renouvellement
        from app.models.audit import AuditLog
        audit_log = AuditLog(
            user_id=user_id,
            api_key_id=new_db_key.id,
            action=action,
            request_data={"payment_reference": payment_reference, "subscription_type": subscription_type}
        )
        db.add(audit_log)
        db.commit()
        
        return new_api_key, new_expires_at
    
    @staticmethod
    def check_api_key_expiry(user_id: int, db: Session) -> dict:
        """Vérifier l'état d'expiration de la clé API"""
        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            return {"error": "Utilisateur non trouvé"}
        
        current_key = db.query(APIKey).filter(
            APIKey.user_id == user_id,
            APIKey.is_active == True
        ).first()
        
        if not current_key:
            return {
                "has_active_key": False,
                "message": "Aucune clé API active"
            }
        
        now = datetime.now(timezone.utc)
        expires_at = current_key.expires_at
        
        if expires_at and expires_at <= now:
            # Clé expirée
            current_key.is_active = False
            db.commit()
            return {
                "has_active_key": False,
                "expired": True,
                "expired_at": expires_at,
                "message": "Clé API expirée"
            }
        
        # Calculer les jours restants
        days_remaining = (expires_at - now).days if expires_at else None
        
        return {
            # "key":
            "has_active_key": True,
            "expires_at": expires_at,
            "days_remaining": days_remaining,
            "subscription_type": user.subscription_type,
            "is_trial": user.subscription_type == "trial",
            "message": f"Clé active, expire dans {days_remaining} jours" if days_remaining else "Clé active"
        }