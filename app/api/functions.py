from fastapi import HTTPException
from langdetect import detect, DetectorFactory
from pydub import AudioSegment
import speech_recognition as sr
from gtts import gTTS
from groq import Groq

import io, re, base64, logging, gzip


logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Fix langdetect seed pour éviter des résultats aléatoires
DetectorFactory.seed = 0

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

def obtenir_reponse_llm(texte_prompt: str, client: Groq) -> str:
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

