"""
FastAPI Backend — Point d'entrée
Architecture : Streamlit → FastAPI → Pipeline → 5 Agents IA
"""
import httpx
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from database import create_tables
from api.routes import router
from settings import settings
import PIL.Image
if not hasattr(PIL.Image, 'ANTIALIAS'):
    PIL.Image.ANTIALIAS = PIL.Image.LANCZOS
app = FastAPI(
    title="AI Video Generator API",
    description=(
        "Plateforme multi-agents de génération de vidéos YouTube.\n\n"
        "**Pipeline** : Script (LangChain+Mistral) → Piper TTS → "
        "Images → Whisper → MoviePy+FFmpeg → SEO → Pillow Thumbnail"
    ),
    version="2.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router, prefix="/api")

create_tables()


@app.get("/health", tags=["System"])
async def health():
    ollama_ok = False
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            r = await client.get(f"{settings.OLLAMA_URL}/api/tags")
            ollama_ok = r.status_code == 200
    except Exception:
        pass

    sd_ok = False
    if settings.SD_WEBUI_URL:
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                r = await client.get(f"{settings.SD_WEBUI_URL}/sdapi/v1/sd-models")
                sd_ok = r.status_code == 200
        except Exception:
            pass

    return {
        "status": "ok",
        "version": "2.0.0",
        "services": {
            "ollama_mistral": "connected" if ollama_ok else "disconnected",
            "stable_diffusion": "connected" if sd_ok else "not configured",
            "pexels": "configured" if settings.PEXELS_API_KEY else "not configured",
        },
        "agents": [
            "Agent 1 — Script Agent (LangChain + Mistral)",
            "Agent 2 — Voice Agent (Piper TTS)",
            "Agent 3 — Visual Agent (SD / Pexels / Pillow)",
            "Agent 4 — Editor Agent (MoviePy + FFmpeg)",
            "Agent 5 — SEO Agent (LangChain + Mistral)",
        ],
        "pipeline": [
            "1. Script JSON structuré",
            "2. narration.wav (TTS)",
            "3. images scènes",
            "4. sous-titres .srt (Whisper)",
            "5. video.mp4 1080p (FFmpeg)",
            "6. SEO métadonnées",
            "7. thumbnail.jpg (Pillow)",
        ],
    }
