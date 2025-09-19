from fastapi import FastAPI, UploadFile, File, Body, HTTPException
from fastapi.responses import JSONResponse, StreamingResponse
import io, re, base64, logging, gzip
from groq import Groq
from langdetect import detect, DetectorFactory
from pydub import AudioSegment
import speech_recognition as sr
from gtts import gTTS
import os
from dotenv import load_dotenv

# ---------------- Logging ---------------- #
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Fix langdetect seed pour éviter des résultats aléatoires
DetectorFactory.seed = 0

# ---------------- FastAPI ---------------- #
app = FastAPI(title="API Assistant Vocal & Chat Bot Teranga AI", version="1.0")

# ---------------- Client LLM ---------------- #
# Utiliser la variable d'environnement GROQ_API_KEY
groq_api_key = os.environ.get("GROQ_API_KEY")
if not groq_api_key:
    raise RuntimeError("La variable d'environnement GROQ_API_KEY n'est pas définie")
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

# ---------------- Endpoints ---------------- #

@app.get("/")
def home():
    return {"message": "API Assistant Vocal & Chat Bot Teranga AI", "status": "active"}

@app.post("/chat_text/")
async def chat_text(message: str = Body(..., embed=True)):
    reponse = obtenir_reponse_llm(message)
    audio_tts = synthese_vocale(reponse)
    return JSONResponse({
        "texte_utilisateur": message,
        "reponse_assistant": reponse,
        "tts_audio_base64": compress_base64(audio_tts)
    })

@app.post("/chat_audio/")
async def chat_audio(file: UploadFile = File(...)):
    audio_bytes = io.BytesIO(await file.read())
    texte_transcrit = transcrire_audio(audio_bytes)
    audio_origine_base64 = compress_base64(audio_bytes.getvalue())

    reponse = obtenir_reponse_llm(texte_transcrit)
    audio_tts = synthese_vocale(reponse)

    return JSONResponse({
        "texte_utilisateur": texte_transcrit,
        "audio_utilisateur_base64": audio_origine_base64,
        "reponse_assistant": reponse,
        "tts_audio_base64": compress_base64(audio_tts)
    })

@app.post("/tts/")
async def tts_endpoint(message: str = Body(..., embed=True)):
    audio_tts = synthese_vocale(message)
    return StreamingResponse(io.BytesIO(audio_tts), media_type="audio/mpeg")

@app.post("/stt/")
async def stt_endpoint(file: UploadFile = File(...)):
    audio_bytes = io.BytesIO(await file.read())
    texte = transcrire_audio(audio_bytes)
    return {"texte": texte}
