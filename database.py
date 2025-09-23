import os
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from sqlalchemy.orm import declarative_base
from dotenv import load_dotenv
import logging
# from urllib.parse import quote_plus

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")
if not DATABASE_URL:
    logger.error("La variable d'environnement DATABASE_URL n'est pas définie.")
    raise ValueError("La variable d'environnement DATABASE_URL n'est pas définie.")

# Create engine with proper configuration
try:
    engine = create_engine(
        DATABASE_URL,
        connect_args={
            "sslmode": "require",
            "application_name": "teranga_ai_assistant",
        },
        pool_pre_ping=True,
        pool_size=5,
        max_overflow=10
    )
    
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    Base = declarative_base()
    logger.info("Creation database engine successful")
    
except Exception as e:
    logger.error(f"Failed to create database engine: {str(e)}")
    raise

# def test_connection():
#     """Test database connection"""
#     try:
#         with SessionLocal() as session:
#             result = session.execute(text("SELECT 1 FROM user_profiles")).scalar()
#             logger.info(f"Result of test query: {result}")
#             logger.info("Database connection test successful")
#             return True
#     except Exception as e:
#         logger.error(f"Database connection failed: {str(e)}")
#         return False