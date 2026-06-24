import os
from dotenv import load_dotenv

load_dotenv()

class Settings:
    HOST = os.getenv("HOST", "127.0.0.1")
    PORT = int(os.getenv("PORT", "8088"))
    LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")

    TTS_PROVIDER = os.getenv("TTS_PROVIDER", "mock").lower()
    OUTPUT_AUDIO_PATH = os.getenv("OUTPUT_AUDIO_PATH", "output.wav")

    AZURE_SPEECH_KEY = os.getenv("AZURE_SPEECH_KEY", "")
    AZURE_SPEECH_REGION = os.getenv("AZURE_SPEECH_REGION", "southeastasia")
    AZURE_VOICE_NAME = os.getenv("AZURE_VOICE_NAME", "vi-VN-HoaiMyNeural")

    ELEVENLABS_API_KEY = os.getenv("ELEVENLABS_API_KEY", "")
    ELEVENLABS_VOICE_ID = os.getenv("ELEVENLABS_VOICE_ID", "")

    AVATAR_PROVIDER = os.getenv("AVATAR_PROVIDER", "mock").lower()
    VTUBE_STUDIO_WS = os.getenv("VTUBE_STUDIO_WS", "ws://127.0.0.1:8001")

settings = Settings()
