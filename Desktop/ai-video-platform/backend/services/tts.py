import os
import subprocess
import asyncio
import json
import httpx
from pathlib import Path

MODELS_DIR = os.getenv("MODELS_DIR", "/app/models")
PIPER_BIN = os.path.join(MODELS_DIR, "piper", "piper", "piper")

PIPER_VOICES = {
    "Français": {
        "homme": {
            "model": "fr_FR-upmc-medium",
            "url": "https://huggingface.co/rhasspy/piper-voices/resolve/v1.0.0/fr/fr_FR/upmc/medium/fr_FR-upmc-medium.onnx",
            "config_url": "https://huggingface.co/rhasspy/piper-voices/resolve/v1.0.0/fr/fr_FR/upmc/medium/fr_FR-upmc-medium.onnx.json"
        },
        "femme": {
            "model": "fr_FR-siwis-medium",
            "url": "https://huggingface.co/rhasspy/piper-voices/resolve/v1.0.0/fr/fr_FR/siwis/medium/fr_FR-siwis-medium.onnx",
            "config_url": "https://huggingface.co/rhasspy/piper-voices/resolve/v1.0.0/fr/fr_FR/siwis/medium/fr_FR-siwis-medium.onnx.json"
        }
    },
    "Anglais": {
        "homme": {
            "model": "en_US-ryan-medium",
            "url": "https://huggingface.co/rhasspy/piper-voices/resolve/v1.0.0/en/en_US/ryan/medium/en_US-ryan-medium.onnx",
            "config_url": "https://huggingface.co/rhasspy/piper-voices/resolve/v1.0.0/en/en_US/ryan/medium/en_US-ryan-medium.onnx.json"
        },
        "femme": {
            "model": "en_US-amy-medium",
            "url": "https://huggingface.co/rhasspy/piper-voices/resolve/v1.0.0/en/en_US/amy/medium/en_US-amy-medium.onnx",
            "config_url": "https://huggingface.co/rhasspy/piper-voices/resolve/v1.0.0/en/en_US/amy/medium/en_US-amy-medium.onnx.json"
        }
    }
}


def _build_narration_text(script: dict) -> str:
    parts = []
    if script.get("hook"):
        parts.append(script["hook"])
    if script.get("introduction"):
        parts.append(script["introduction"])
    for section in script.get("sections", []):
        if section.get("content"):
            parts.append(section["content"])
    if script.get("conclusion"):
        parts.append(script["conclusion"])
    if script.get("cta"):
        parts.append(script["cta"])
    return " ".join(parts)


async def _download_file(url: str, dest: str):
    async with httpx.AsyncClient(timeout=120.0, follow_redirects=True) as client:
        response = await client.get(url)
        response.raise_for_status()
        with open(dest, "wb") as f:
            f.write(response.content)


async def _ensure_voice_model(language: str, voice: str) -> tuple[str, str]:
    voice_info = PIPER_VOICES.get(language, PIPER_VOICES["Français"]).get(voice, PIPER_VOICES["Français"]["homme"])
    model_name = voice_info["model"]
    model_path = os.path.join(MODELS_DIR, "piper", f"{model_name}.onnx")
    config_path = os.path.join(MODELS_DIR, "piper", f"{model_name}.onnx.json")

    if not os.path.exists(model_path):
        await _download_file(voice_info["url"], model_path)
    if not os.path.exists(config_path):
        await _download_file(voice_info["config_url"], config_path)

    return model_path, config_path


async def generate_tts(script: dict, output_path: str, language: str = "Français", voice: str = "homme") -> str:
    text = _build_narration_text(script)

    if os.path.exists(PIPER_BIN):
        return await _generate_with_piper(text, output_path, language, voice)
    else:
        return await _generate_with_espeak(text, output_path, language)


async def _generate_with_piper(text: str, output_path: str, language: str, voice: str) -> str:
    model_path, config_path = await _ensure_voice_model(language, voice)

    process = await asyncio.create_subprocess_exec(
        PIPER_BIN,
        "--model", model_path,
        "--config", config_path,
        "--output_file", output_path,
        stdin=asyncio.subprocess.PIPE,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE
    )
    stdout, stderr = await process.communicate(input=text.encode("utf-8"))
    if process.returncode != 0:
        raise RuntimeError(f"Piper TTS failed: {stderr.decode()}")
    return output_path


async def _generate_with_espeak(text: str, output_path: str, language: str) -> str:
    lang_code = "fr" if language == "Français" else "en"
    wav_path = output_path.replace(".wav", "_raw.wav") if not output_path.endswith(".wav") else output_path

    process = await asyncio.create_subprocess_exec(
        "espeak-ng",
        "-v", lang_code,
        "-s", "150",
        "-w", wav_path,
        text[:5000],
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE
    )
    await process.communicate()

    if not os.path.exists(output_path) or output_path != wav_path:
        process2 = await asyncio.create_subprocess_exec(
            "ffmpeg", "-y",
            "-i", wav_path,
            "-ar", "44100",
            "-ac", "1",
            output_path,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        await process2.communicate()
        if wav_path != output_path and os.path.exists(wav_path):
            os.remove(wav_path)

    return output_path
