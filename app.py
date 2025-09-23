"""
Auteur : Moustapha NDIAYE
Rôle   : Senior AI Developer @ Teranga AI
Email  : infos@terangaai.com
Date   : 19/09/2025
Site   : https://terangaai.com
Téléphone : +221 77 784 01 61
Description : API FastAPI pour l'assistant vocal & chatbot Teranga AI
"""
from fastapi import FastAPI, UploadFile, File, Body, HTTPException, Depends, Security, status, Request
from fastapi.responses import JSONResponse, StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.httpsredirect import HTTPSRedirectMiddleware
from fastapi_limiter import FastAPILimiter
from fastapi_limiter.depends import RateLimiter
from pydantic import BaseModel
from groq import Groq
from langdetect import detect, DetectorFactory

import io, re, base64, logging, gzip
from datetime import datetime
from typing import Optional
from collections import defaultdict
import time
import os

# Imports internes
from auth.routes import router as auth_router
from auth.utils import verify_api_key
from users.routes import router as users_router
from auth.dependencies import get_current_user
from users.schemas import UserSchema
from database import SessionLocal
from functions import (
    synthese_vocale,
    transcrire_audio,
    obtenir_reponse_llm,
    build_prompt,
    compress_base64
)

# ==========================
# Limiteur de débit en mémoire
# ==========================
class InMemoryRateLimiter:
    def __init__(self, times: int = 10, seconds: int = 60):
        self.times = times
        self.seconds = seconds
        self.requests = defaultdict(list)
    
    async def __call__(self, request: Request):
        now = time.time()
        client_ip = request.client.host
        
        self.requests[client_ip] = [
            req_time for req_time in self.requests[client_ip]
            if now - req_time < self.seconds
        ]
        
        if len(self.requests[client_ip]) >= self.times:
            raise HTTPException(
                status_code=429,
                detail="Too many requests"
            )
            
        self.requests[client_ip].append(now)
        return True

# Variable globale pour suivre l'état du rate limiter
USE_REDIS_LIMITER = False
memory_limiter = InMemoryRateLimiter()

# ==========================
# Logging
# ==========================
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# ==========================
# FastAPI
# ==========================
app = FastAPI(
    title="API Assistant Vocal & Chat Bot Teranga AI", 
    version="1.0",
    docs_url="/api/docs",
    openapi_url="/api/openapi.json"
)

# Middleware de sécurité
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["GET", "POST"],
    allow_headers=["Authorization", "Content-Type", "X-API-Key"],
    expose_headers=["X-Total-Count"]
)

# Middleware de base de données
@app.middleware("http")
async def db_session_middleware(request, call_next):
    request.state.db = SessionLocal()
    response = await call_next(request)
    request.state.db.close()
    return response

# Montage des routes
app.include_router(
    auth_router,
    prefix="/auth",
    tags=["auth"],
    dependencies=[Depends(verify_api_key)]
)

app.include_router(
    users_router,
    prefix="/users",
    tags=["users"],
    dependencies=[Depends(verify_api_key), Depends(get_current_user)]
)

# ==========================
# Schémas Pydantic
# ==========================
class ChatRequest(BaseModel):
    user_id: str
    pre_prompt: str
    message: Optional[str] = None  # Message optionnel
    history: list[str] = []

# ==========================
# Client LLM
# ==========================
# Utiliser la variable d'environnement GROQ_API_KEY
groq_api_key = os.getenv("GROQ_API_KEY")
if not groq_api_key:
    raise RuntimeError("La variable d'environnement GROQ_API_KEY n'est pas définie")
client = Groq(api_key=groq_api_key)

# ==========================
# Fonction helper pour le rate limiting
# ==========================
def get_rate_limiter(times: int = 10, seconds: int = 60):
    """Retourne le bon rate limiter selon la disponibilité de Redis"""
    if USE_REDIS_LIMITER:
        return RateLimiter(times=times, seconds=seconds)
    else:
        # Pour l'in-memory limiter, on retourne toujours la même instance
        return Depends(memory_limiter)

# ==========================
# Endpoints
# ==========================
@app.get("/")
async def root():
    return {
        "status": "active",
        "timestamp": datetime.now().isoformat(),
        "version": app.version,
        "message": "API Assistant Vocal & Chat Bot Teranga AI"
    }

@app.get("/health")
def health_check():
    """Health check pour Railway"""
    try:
        return {
            "status": "healthy",
            "timestamp": time.time(),
            "service": "Teranga AI FastAPI Assistant",
            "version": "1.0.0",
            "environment": os.getenv("ENVIRONMENT", "development")
        }
        
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"Health check failed: {str(e)}")

# Gestionnaire d'erreurs
@app.exception_handler(HTTPException)
async def http_exception_handler(request, exc):
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "status": "error",
            "message": exc.detail,
            "code": exc.status_code
        }
    )

# Events de démarrage et d'arrêt
@app.on_event("startup")
async def startup_event():
    global USE_REDIS_LIMITER
    logger.info("Starting up application...")
    try:
        import aioredis
        redis = aioredis.from_url(os.getenv("REDIS_URL", "redis://localhost:6379"))
        await FastAPILimiter.init(redis)
        USE_REDIS_LIMITER = True
        logger.info("Redis rate limiter initialized successfully")
    except Exception as e:
        logger.warning(f"Redis connection failed: {str(e)}")
        logger.info("Using in-memory rate limiter as fallback")
        USE_REDIS_LIMITER = False

@app.on_event("shutdown")
async def shutdown_event():
    logger.info("Shutting down application...")
    # Nettoyage des ressources si nécessaire

@app.post("/chat_text/")
async def chat_text(
    req: ChatRequest = Body(...),
    current_user: UserSchema = Depends(get_current_user),
    _: bool = Depends(memory_limiter)  # Rate limiting toujours appliqué
):
    prompt = build_prompt(req.message, req.pre_prompt, req.history)
    reponse = obtenir_reponse_llm(prompt, client)
    audio_tts = synthese_vocale(reponse)
    return JSONResponse({
        "texte_utilisateur": req.message,
        "reponse_assistant": reponse,
        "tts_audio_base64": compress_base64(audio_tts),
        "user": current_user.email
    })

@app.post("/chat_audio/")
async def chat_audio(
    req: ChatRequest = Body(...), 
    file: UploadFile = File(...),
    current_user: UserSchema = Depends(get_current_user),
    _: bool = Depends(memory_limiter)  # Rate limiting toujours appliqué
):
    audio_bytes = io.BytesIO(await file.read())
    texte_transcrit = transcrire_audio(audio_bytes)
    audio_origine_base64 = compress_base64(audio_bytes.getvalue())

    prompt = build_prompt(texte_transcrit, req.pre_prompt, req.history)
    reponse = obtenir_reponse_llm(prompt, client)
    audio_tts = synthese_vocale(reponse)

    return JSONResponse({
        "texte_utilisateur": texte_transcrit,
        "audio_utilisateur_base64": audio_origine_base64,
        "reponse_assistant": reponse,
        "tts_audio_base64": compress_base64(audio_tts),
        "user": current_user.email
    })

@app.post("/tts/")
async def tts_endpoint(
    message: str = Body(..., embed=True),
    current_user: UserSchema = Depends(get_current_user),
    _: bool = Depends(memory_limiter)  # Rate limiting toujours appliqué
):
    audio_tts = synthese_vocale(message)
    return StreamingResponse(io.BytesIO(audio_tts), media_type="audio/mpeg")

@app.post("/stt/")
async def stt_endpoint(
    file: UploadFile = File(...),
    current_user: UserSchema = Depends(get_current_user),
    _: bool = Depends(memory_limiter)  # Rate limiting toujours appliqué
):
    audio_bytes = io.BytesIO(await file.read())
    texte = transcrire_audio(audio_bytes)
    return {"texte": texte, "user": current_user.email}