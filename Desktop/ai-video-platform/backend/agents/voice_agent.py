"""
Agent 2 — Voice Agent
Rôle : Convertit le script en narration audio (narration.wav)
Stack : Piper TTS (local) + fallback espeak-ng
"""
import os
import asyncio
import httpx

from settings import settings

PIPER_VOICES = {
    "Français": {
        "homme": {
            "model": "fr_FR-upmc-medium",
            "url": "https://huggingface.co/rhasspy/piper-voices/resolve/v1.0.0/fr/fr_FR/upmc/medium/fr_FR-upmc-medium.onnx",
            "config_url": "https://huggingface.co/rhasspy/piper-voices/resolve/v1.0.0/fr/fr_FR/upmc/medium/fr_FR-upmc-medium.onnx.json",
        },
        "femme": {
            "model": "fr_FR-siwis-medium",
            "url": "https://huggingface.co/rhasspy/piper-voices/resolve/v1.0.0/fr/fr_FR/siwis/medium/fr_FR-siwis-medium.onnx",
            "config_url": "https://huggingface.co/rhasspy/piper-voices/resolve/v1.0.0/fr/fr_FR/siwis/medium/fr_FR-siwis-medium.onnx.json",
        },
    },
    "Anglais": {
        "homme": {
            "model": "en_US-ryan-medium",
            "url": "https://huggingface.co/rhasspy/piper-voices/resolve/v1.0.0/en/en_US/ryan/medium/en_US-ryan-medium.onnx",
            "config_url": "https://huggingface.co/rhasspy/piper-voices/resolve/v1.0.0/en/en_US/ryan/medium/en_US-ryan-medium.onnx.json",
        },
        "femme": {
            "model": "en_US-amy-medium",
            "url": "https://huggingface.co/rhasspy/piper-voices/resolve/v1.0.0/en/en_US/amy/medium/en_US-amy-medium.onnx",
            "config_url": "https://huggingface.co/rhasspy/piper-voices/resolve/v1.0.0/en/en_US/amy/medium/en_US-amy-medium.onnx.json",
        },
    },
}


def build_narration_text(script: dict) -> str:
    parts = []
    for key in ["hook", "introduction"]:
        if script.get(key):
            parts.append(script[key])
    for section in script.get("sections", []):
        if section.get("content"):
            parts.append(section["content"])
    for key in ["conclusion", "cta"]:
        if script.get(key):
            parts.append(script[key])
    return " ".join(parts)


async def _download_file(url: str, dest: str):
    async with httpx.AsyncClient(timeout=180.0, follow_redirects=True) as client:
        r = await client.get(url)
        r.raise_for_status()
        with open(dest, "wb") as f:
            f.write(r.content)


async def _ensure_piper_model(language: str, voice: str) -> tuple:
    voices = PIPER_VOICES.get(language, PIPER_VOICES["Français"])
    info = voices.get(voice, list(voices.values())[0])
    piper_dir = os.path.join(settings.MODELS_DIR, "piper")
    os.makedirs(piper_dir, exist_ok=True)
    model_path = os.path.join(piper_dir, f"{info['model']}.onnx")
    config_path = os.path.join(piper_dir, f"{info['model']}.onnx.json")
    if not os.path.exists(model_path):
        await _download_file(info["url"], model_path)
    if not os.path.exists(config_path):
        await _download_file(info["config_url"], config_path)
    return model_path, config_path


async def _run_piper(text: str, output_path: str, language: str, voice: str) -> str:
    model_path, config_path = await _ensure_piper_model(language, voice)
    proc = await asyncio.create_subprocess_exec(
        settings.PIPER_BIN,
        "--model", model_path,
        "--config", config_path,
        "--output_file", output_path,
        stdin=asyncio.subprocess.PIPE,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    _, stderr = await proc.communicate(input=text.encode("utf-8"))
    if proc.returncode != 0:
        raise RuntimeError(f"Piper: {stderr.decode()}")
    return output_path


async def _run_espeak(text: str, output_path: str, language: str) -> str:
    lang_code = "fr" if language == "Français" else "en"
    raw = output_path + ".raw.wav"
    proc = await asyncio.create_subprocess_exec(
        "espeak-ng", "-v", lang_code, "-s", "145", "-w", raw, text[:4000],
        stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE,
    )
    await proc.communicate()
    proc2 = await asyncio.create_subprocess_exec(
        "ffmpeg", "-y", "-i", raw, "-ar", "44100", "-ac", "1", output_path,
        stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE,
    )
    await proc2.communicate()
    if os.path.exists(raw) and raw != output_path:
        os.remove(raw)
    return output_path


async def run(script: dict, output_path: str, language: str = "Français", voice: str = "homme") -> str:
    """
    Convertit le script en fichier narration.wav.
    Priorité : Piper TTS → espeak-ng (fallback)
    """
    text = build_narration_text(script)
    os.makedirs(os.path.dirname(output_path), exist_ok=True)

    if os.path.exists(settings.PIPER_BIN):
        try:
            return await _run_piper(text, output_path, language, voice)
        except Exception:
            pass

    return await _run_espeak(text, output_path, language)
