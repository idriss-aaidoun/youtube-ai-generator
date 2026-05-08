"""
Configuration centralisée — variables d'environnement Docker.
"""
import os


class Settings:
    # LLM
    OLLAMA_URL: str      = os.getenv("OLLAMA_URL", "http://ai_ollama:11434")
    LLM_MODEL: str       = os.getenv("LLM_MODEL", "mistral")
    LLM_TEMPERATURE: float = float(os.getenv("LLM_TEMPERATURE", "0.7"))

    # Base de données
    DATABASE_URL: str    = os.getenv("DATABASE_URL", "sqlite:///db/videos.db")

    # Chemins de sortie
    OUTPUTS_DIR: str     = os.getenv("OUTPUTS_DIR", "/app/outputs")
    VIDEOS_DIR: str      = os.getenv("VIDEOS_DIR", "/app/outputs/videos")
    AUDIO_DIR: str       = os.getenv("AUDIO_DIR", "/app/outputs/audio")
    IMAGES_DIR: str      = os.getenv("IMAGES_DIR", "/app/outputs/images")

    # Assets & Modèles
    ASSETS_DIR: str      = os.getenv("ASSETS_DIR", "/app/assets")
    MODELS_DIR: str      = os.getenv("MODELS_DIR", "/app/models")
    PIPER_BIN: str       = os.getenv("PIPER_BIN", "/app/models/piper/piper/piper")

    # Images
    SD_WEBUI_URL: str    = os.getenv("SD_WEBUI_URL", "")
    PEXELS_API_KEY: str  = os.getenv("PEXELS_API_KEY", "")

    # Vidéo
    VIDEO_WIDTH: int     = int(os.getenv("VIDEO_WIDTH", "1920"))
    VIDEO_HEIGHT: int    = int(os.getenv("VIDEO_HEIGHT", "1080"))
    VIDEO_FPS: int       = int(os.getenv("VIDEO_FPS", "24"))

    # Audio
    ADD_BACKGROUND_MUSIC: bool = os.getenv("ADD_BACKGROUND_MUSIC", "true").lower() == "true"


settings = Settings()

for _d in [settings.OUTPUTS_DIR, settings.VIDEOS_DIR, settings.AUDIO_DIR, settings.IMAGES_DIR]:
    os.makedirs(_d, exist_ok=True)