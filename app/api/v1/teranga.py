from fastapi import APIRouter, Depends, Body, UploadFile, File, Form
from fastapi.responses import JSONResponse, StreamingResponse
from groq import Groq
# from sqlalchemy.orm import Session
# from core.database import get_db
from app.core.config import settings
from app.models.user import User
from app.models.api_key import APIKey
from app.api.deps import get_api_key_user
from pydantic import BaseModel
from typing import Optional
import io
from app.api.functions import (
    synthese_vocale,
    transcrire_audio,
    obtenir_reponse_llm,
    build_prompt,
    compress_base64
)

router = APIRouter()


class ChatRequest(BaseModel):
    # messages: List[ChatMessage]
    # model: str = "teranga-1"
    # max_tokens: int = 1000
    # temperature: float = 0.7
    user_id: str
    pre_prompt: str
    message: Optional[str] = None  # Message optionnel
    history: list[str] = []



groq_api_key = settings.GROQ_API_KEY
if not groq_api_key:
    raise RuntimeError("La variable d'environnement GROQ_API_KEY n'est pas définie")
client = Groq(api_key=groq_api_key)


# Endpoints compatibles avec l'API OpenAI
@router.post("/chat_text")
async def chat_text(
    request: ChatRequest,
    user_and_key: tuple[User, APIKey] = Depends(get_api_key_user),
    # db: Session = Depends(get_db)
):
    """
    Endpoint de chat completion compatible OpenAI
    Authentification via clé API
    """
    user, api_key = user_and_key
    prompt = build_prompt(request.pre_prompt, request.history)
    reponse = obtenir_reponse_llm(prompt, request.message, client)
    audio_tts = synthese_vocale(reponse)
    return JSONResponse({
        "texte_utilisateur": request.message,
        "reponse_assistant": reponse,
        "tts_audio_base64": compress_base64(audio_tts),
        "user": user.email
    })

@router.post("/chat_audio")
async def create_completion(
    pre_prompt: str = Form(...),
    history: str = Form(...),
    user_id: str = Form(...),
    file: UploadFile = File(...),
    user_and_key: tuple[User, APIKey] = Depends(get_api_key_user),
    # db: Session = Depends(get_db)
):
    """
    Endpoint de text completion compatible OpenAI
    Authentification via clé API
    """
    user, api_key = user_and_key
    
    audio_bytes = io.BytesIO(await file.read())
    texte_transcrit = transcrire_audio(audio_bytes)
    audio_origine_base64 = compress_base64(audio_bytes.getvalue())

    prompt = build_prompt(texte_transcrit, pre_prompt, history)
    reponse = obtenir_reponse_llm(prompt, client)
    audio_tts = synthese_vocale(reponse)

    return JSONResponse({
        "texte_utilisateur": texte_transcrit,
        "audio_utilisateur_base64": audio_origine_base64,
        "reponse_assistant": reponse,
        "tts_audio_base64": compress_base64(audio_tts),
        "user": user.email
    })

@router.post("/tts/")
async def tts_endpoint(
    message: str = Body(..., embed=True),
    user_and_key: tuple[User, APIKey] = Depends(get_api_key_user),
):
    audio_tts = synthese_vocale(message)
    return StreamingResponse(io.BytesIO(audio_tts), media_type="audio/mpeg")

@router.post("/stt/")
async def stt_endpoint(
    file: UploadFile = File(...),
    user_and_key: tuple[User, APIKey] = Depends(get_api_key_user)
):
    user, api_key = user_and_key
    audio_bytes = io.BytesIO(await file.read())
    texte = transcrire_audio(audio_bytes)
    return {"texte": texte, "user": user.email}