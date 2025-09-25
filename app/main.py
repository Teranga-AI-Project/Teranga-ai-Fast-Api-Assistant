from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
import time
# import uvicorn
from app.core.config import settings
from app.core.database import engine, Base
from app.api.v1 import auth, api_keys, teranga, admin

# Créer les tables
Base.metadata.create_all(bind=engine)

# Initialiser FastAPI
app = FastAPI(
    title=settings.APP_NAME,
    version=settings.VERSION,
    description="Plateforme API sécurisée pour Teranga AI - Compatible OpenAI",
    docs_url="/docs",
    redoc_url="/redoc"
)

# Middleware de sécurité
app.add_middleware(TrustedHostMiddleware, allowed_hosts=["*"])  # À configurer en production
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Middleware de logging et rate limiting (basique)
@app.middleware("http")
async def logging_middleware(request: Request, call_next):
    start_time = time.time()
    
    # TODO: Implémenter rate limiting avancé ici
    
    response = await call_next(request)
    
    process_time = time.time() - start_time
    response.headers["X-Process-Time"] = str(process_time)
    
    return response

# Gestionnaire d'erreurs global
@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={
            "error": {
                "message": "Invalid request format",
                "type": "invalid_request_error",
                "details": exc.errors()
            }
        }
    )

@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "error": {
                "message": "Internal server error",
                "type": "api_error"
            }
        }
    )

# Routes principales
@app.get("/")
def root():
    """Point d'entrée de l'API"""
    return {
        "message": "Teranga AI API Platform",
        "version": settings.VERSION,
        "status": "operational"
    }

@app.get("/health")
def health_check():
    """Vérification de santé de l'API"""
    return {
        "status": "healthy",
        "timestamp": time.time()
    }

# Inclusion des routers
app.include_router(
    auth.router,
    prefix=f"{settings.API_V1_STR}/auth",
    tags=["Authentication"]
)

# Désactivation temporaire de la gestion des clés API pour se concentrer sur Teranga AI
# app.include_router(
#     api_keys.router,
#     prefix=f"{settings.API_V1_STR}/api-keys",
#     tags=["API Keys Management"]
# )

app.include_router(
    teranga.router,
    prefix=f"{settings.API_V1_STR}",
    tags=["Teranga AI"]
)

# Désactivation temporaire de l'admin pour se concentrer sur Teranga AI
# app.include_router(
#     admin.router,
#     prefix=f"{settings.API_V1_STR}/admin",
#     tags=["Administration"]
# )

# if __name__ == "__main__":
#     uvicorn.run(
#         "app.main:app",
#         host="0.0.0.0",
#         port=8000,
#         reload=True,
#         log_level="info"
#     )