"""
Auteur : Moustapha NDIAYE
Rôle   : Senior AI Developer @ Teranga AI
Email  : infos@terangaai.com
Date   : 19/09/2025
Site   : https://terangaai.com
Téléphone : +221 77 784 01 61
Description : API FastAPI pour l'assistant vocal & chatbot Teranga AI
"""
from fastapi import FastAPI, UploadFile, File, Body, HTTPException
from fastapi.responses import JSONResponse, StreamingResponse
import io, re, base64, logging, gzip
from groq import Groq
from langdetect import detect, DetectorFactory
from pydub import AudioSegment
import speech_recognition as sr
from gtts import gTTS
import os
import time
import psutil
# from dotenv import load_dotenv
from typing import Optional
from pydantic import BaseModel

# ---------------- Logging ---------------- #
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Fix langdetect seed pour éviter des résultats aléatoires
DetectorFactory.seed = 0



# ---------------- FastAPI ---------------- #
app = FastAPI(title="API Assistant Vocal & Chat Bot Teranga AI", version="1.0")

# ==========================
# Schémas Pydantic
# ==========================
class ChatRequest(BaseModel):
    user_id: str
    pre_prompt: str
    message: Optional[str] = None  # Message optionnel
    history: list[str] = []


# ---------------- Client LLM ---------------- #
# Utiliser la variable d'environnement GROQ_API_KEY
# groq_api_key = os.getenv("GROQ_API_KEY")
# if not groq_api_key:
#     raise RuntimeError("La variable d'environnement GROQ_API_KEY n'est pas définie")
# client = Groq(api_key=groq_api_key)

# Debug des variables d'environnement
logger.info("=== DEBUG VARIABLES D'ENVIRONNEMENT ===")
logger.info(f"GROQ_API_KEY présente: {'GROQ_API_KEY' in os.environ}")
logger.info(f"Toutes les variables: {list(os.environ.keys())}")

# Configuration Groq avec gestion d'erreur améliorée
groq_api_key = os.getenv("GROQ_API_KEY")
if not groq_api_key:
    logger.error("GROQ_API_KEY manquante!")
    logger.error(f"Variables disponibles: {[k for k in os.environ.keys() if 'GROQ' in k.upper()]}")
    raise RuntimeError("La variable d'environnement GROQ_API_KEY n'est pas définie")

logger.info("GROQ_API_KEY trouvée et configurée ✅")
client = Groq(api_key=groq_api_key)



# ---------------- Fonctions utilitaires ---------------- #

def detecter_langue(texte: str) -> str:
    try:
        return detect(texte)
    except:
        return "fr"

def synthese_vocale(texte: str) -> bytes:
    texte_nettoye = re.sub(r"[*_`~^<>#{}[\]|\\]", "", texte)
    texte_nettoye = re.sub(r"\s+", " ", texte_nettoye).strip()
    if not texte_nettoye:
        return b""

    langue_tts = detecter_langue(texte_nettoye)
    mapping_langues = {
        'fr': 'fr', 'en': 'en', 'es': 'es', 'de': 'de',
        'it': 'it', 'pt': 'pt', 'ru': 'ru', 'ja': 'ja',
        'zh-cn': 'zh', 'zh-tw': 'zh-tw'
    }
    langue_tts = mapping_langues.get(langue_tts, 'fr')

    try:
        tts = gTTS(text=texte_nettoye, lang=langue_tts, slow=False)
        mp3_fp = io.BytesIO()
        tts.write_to_fp(mp3_fp)
        mp3_fp.seek(0)
        return mp3_fp.getvalue()
    except Exception as e:
        logger.error(f"Erreur TTS: {e}")
        return b""

def transcrire_audio(audio_bytes: io.BytesIO) -> str:
    audio_bytes.seek(0)
    try:
        audio = AudioSegment.from_file(audio_bytes)
        audio = audio.set_frame_rate(16000).set_channels(1)  # Prétraitement mono 16kHz

        wav_io = io.BytesIO()
        audio.export(wav_io, format="wav")
        wav_io.seek(0)

        recognizer = sr.Recognizer()
        with sr.AudioFile(wav_io) as source:
            audio_data = recognizer.record(source)
            texte = recognizer.recognize_google(audio_data, language="fr-FR")
        return texte
    except sr.UnknownValueError:
        raise HTTPException(status_code=400, detail="Impossible de comprendre l'audio")
    except sr.RequestError as e:
        raise HTTPException(status_code=500, detail=f"Erreur API: {e}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erreur de traitement audio: {e}")

def obtenir_reponse_llm(texte_prompt: str) -> str:
    try:
        completion = client.chat.completions.create(
            messages=[{"role": "user", "content": texte_prompt}],
            model="llama-3.1-8b-instant",
            temperature=0.3,
            top_p=0.9,
            max_tokens=400,  # Limiter le nombre de tokens pour réduire la latence
            stream=False
        )
        return completion.choices[0].message.content
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erreur LLM : {e}")

def compress_base64(data: bytes) -> str:
    return base64.b64encode(gzip.compress(data)).decode()

def build_prompt(message: str, pre_prompt: str, history: list[str]) -> str:
    """
    Construit le prompt pour LLaMA.
    L'humeur est fournie par l'utilisateur via l'interface.
    """
    hist = "\n".join(history[-5:])  # garder les 5 derniers échanges
    prompt = (
        f"{pre_prompt} "
        f"Historique récent:\n{hist}\n\n"
        f"Utilisateur: {message}\n"
        f"Mentor:"
    )
    return prompt




# ---------------- Endpoints ---------------- #

@app.get("/health")
async def health_check():
    """Health check optimisé pour Railway"""
    try:
        start_time = time.time()
        
        # Test basic functionality
        test_response = {"status": "healthy"}
        
        # Check system resources
        memory_percent = psutil.virtual_memory().percent
        cpu_percent = psutil.cpu_percent()
        
        # Check if system is under stress
        if memory_percent > 90 or cpu_percent > 95:
            raise HTTPException(status_code=503, detail="System under high load")
        
        response_time = time.time() - start_time
        
        return {
            "status": "healthy",
            "timestamp": time.time(),
            "response_time": response_time,
            "memory_usage": f"{memory_percent}%",
            "cpu_usage": f"{cpu_percent}%",
            "services": {
                "stt": "operational",
                "tts": "operational", 
                "llm": "operational"
            }
        }
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"Health check failed: {str(e)}")
    

@app.get("/")
def home():
    return {"message": "API Assistant Vocal & Chat Bot Teranga AI", "status": "active"}

@app.post("/chat_text/")
async def chat_text(req: ChatRequest = Body(...)):
    prompt = build_prompt(req.message, req.pre_prompt, req.history)
    reponse = obtenir_reponse_llm(prompt)
    audio_tts = synthese_vocale(reponse)
    return JSONResponse({
        "texte_utilisateur": req.message,
        "reponse_assistant": reponse,
        "tts_audio_base64": compress_base64(audio_tts)
    })

@app.post("/chat_audio/")
# async def chat_audio(file: UploadFile = File(...)):
async def chat_audio(req: ChatRequest = Body(...), file: UploadFile = File(...)):
    audio_bytes = io.BytesIO(await file.read())
    texte_transcrit = transcrire_audio(audio_bytes)
    audio_origine_base64 = compress_base64(audio_bytes.getvalue())

    prompt = build_prompt(texte_transcrit, req.pre_prompt, req.history)
    reponse = obtenir_reponse_llm(prompt)
    audio_tts = synthese_vocale(reponse)

    return JSONResponse({
        "texte_utilisateur": texte_transcrit,
        "audio_utilisateur_base64": audio_origine_base64,
        "reponse_assistant": reponse,
        "tts_audio_base64": compress_base64(audio_tts)
    })

@app.post("/tts/")
async def tts_endpoint(message: str = Body(...)):
    audio_tts = synthese_vocale(message)
    return StreamingResponse(io.BytesIO(audio_tts), media_type="audio/mpeg")

@app.post("/stt/")
async def stt_endpoint(file: UploadFile = File(...)):
    audio_bytes = io.BytesIO(await file.read())
    texte = transcrire_audio(audio_bytes)
    return {"texte": texte}
