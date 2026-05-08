from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv


BASE_DIR = Path(__file__).resolve().parent.parent
INSTANCE_DIR = BASE_DIR / "instance"

load_dotenv(BASE_DIR / ".env", override=False)


class Config:
    SECRET_KEY = os.getenv("SECRET_KEY", "dev-secret-key")
    SQLALCHEMY_DATABASE_URI = os.getenv(
        "DATABASE_URL",
        f"sqlite:///{(INSTANCE_DIR / 'ytb.db').resolve().as_posix()}",
    )
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    OUTPUT_DIR = Path(os.getenv("OUTPUT_DIR", str((INSTANCE_DIR / "generated").resolve())))
    DEFAULT_LANGUAGE = os.getenv("DEFAULT_LANGUAGE", "fr")
    DEFAULT_TONE = os.getenv("DEFAULT_TONE", "engaging")
    DEFAULT_VOICE = os.getenv("DEFAULT_VOICE", "female")
    HUGGINGFACE_API_TOKEN = os.getenv("HUGGINGFACE_API_TOKEN", os.getenv("HF_TOKEN", ""))
    HUGGINGFACE_MODEL = os.getenv("HUGGINGFACE_MODEL", "TinyLlama/TinyLlama-1.1B-Chat-v1.0")
    HUGGINGFACE_TIMEOUT_SECONDS = os.getenv("HUGGINGFACE_TIMEOUT_SECONDS", "60")
    HUGGINGFACE_MAX_NEW_TOKENS = os.getenv("HUGGINGFACE_MAX_NEW_TOKENS", "700")
    HUGGINGFACE_TEMPERATURE = os.getenv("HUGGINGFACE_TEMPERATURE", "0.7")
    HUGGINGFACE_IMAGE_MODEL = os.getenv("HUGGINGFACE_IMAGE_MODEL", "stabilityai/stable-diffusion-xl-base-1.0")
    HUGGINGFACE_IMAGE_TIMEOUT_SECONDS = os.getenv("HUGGINGFACE_IMAGE_TIMEOUT_SECONDS", "120")
    HUGGINGFACE_IMAGE_GUIDANCE_SCALE = os.getenv("HUGGINGFACE_IMAGE_GUIDANCE_SCALE", "7.5")
    HUGGINGFACE_IMAGE_NEGATIVE_PROMPT = os.getenv(
        "HUGGINGFACE_IMAGE_NEGATIVE_PROMPT",
        "blurry, low quality, distorted, watermark, text, logo, extra fingers, deformed",
    )
    ELEVENLABS_API_KEY = os.getenv("ELEVENLABS_API_KEY", "")
    ELEVENLABS_MODEL_ID = os.getenv("ELEVENLABS_MODEL_ID", "eleven_multilingual_v2")
    ELEVENLABS_VOICE_ID = os.getenv("ELEVENLABS_VOICE_ID", "")
    ELEVENLABS_VOICE_ID_FEMALE = os.getenv("ELEVENLABS_VOICE_ID_FEMALE", "")
    ELEVENLABS_VOICE_ID_MALE = os.getenv("ELEVENLABS_VOICE_ID_MALE", "")
    ELEVENLABS_TIMEOUT_SECONDS = os.getenv("ELEVENLABS_TIMEOUT_SECONDS", "60")
    ELEVENLABS_OUTPUT_FORMAT = os.getenv("ELEVENLABS_OUTPUT_FORMAT", "mp3_44100_128")
    ELEVENLABS_STABILITY = os.getenv("ELEVENLABS_STABILITY", "0.5")
    ELEVENLABS_SIMILARITY_BOOST = os.getenv("ELEVENLABS_SIMILARITY_BOOST", "0.75")
    ELEVENLABS_STYLE = os.getenv("ELEVENLABS_STYLE", "0.0")
    ELEVENLABS_USE_SPEAKER_BOOST = os.getenv("ELEVENLABS_USE_SPEAKER_BOOST", "true")
    VIDEO_RENDER_WIDTH = os.getenv("VIDEO_RENDER_WIDTH", "1280")
    VIDEO_RENDER_HEIGHT = os.getenv("VIDEO_RENDER_HEIGHT", "720")
    VIDEO_RENDER_FPS = os.getenv("VIDEO_RENDER_FPS", "24")
    VIDEO_RENDER_TRANSITION_SECONDS = os.getenv("VIDEO_RENDER_TRANSITION_SECONDS", "0.75")
    VIDEO_RENDER_TEST_WIDTH = os.getenv("VIDEO_RENDER_TEST_WIDTH", "640")
    VIDEO_RENDER_TEST_HEIGHT = os.getenv("VIDEO_RENDER_TEST_HEIGHT", "360")
    VIDEO_RENDER_TEST_FPS = os.getenv("VIDEO_RENDER_TEST_FPS", "8")
    VIDEO_RENDER_TEST_TRANSITION_SECONDS = os.getenv("VIDEO_RENDER_TEST_TRANSITION_SECONDS", "0.25")
