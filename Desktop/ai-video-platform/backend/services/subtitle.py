"""
Module 5 — Génération de sous-titres
Outil : Whisper (openai-whisper)
Commande équivalente : whisper narration.wav --language French
Sorties : .srt + .txt
"""

import whisper
import os
import asyncio
from concurrent.futures import ThreadPoolExecutor

_executor = ThreadPoolExecutor(max_workers=1)

_whisper_model = None


def _get_model():
    global _whisper_model
    if _whisper_model is None:
        _whisper_model = whisper.load_model("base")
    return _whisper_model


def _run_whisper(audio_path: str, language: str, output_dir: str) -> dict:
    """
    Transcrit l'audio avec Whisper et génère les fichiers .srt et .txt.
    Équivalent à : whisper narration.wav --language French
    """
    lang_code = "fr" if language == "Français" else "en"

    model = _get_model()
    result = model.transcribe(
        audio_path,
        language=lang_code,
        word_timestamps=False,
        verbose=False
    )

    base_name = os.path.splitext(os.path.basename(audio_path))[0]
    srt_path = os.path.join(output_dir, f"{base_name}.srt")
    txt_path = os.path.join(output_dir, f"{base_name}.txt")

    with open(srt_path, "w", encoding="utf-8") as f:
        for i, segment in enumerate(result["segments"], 1):
            start = _seconds_to_srt_time(segment["start"])
            end = _seconds_to_srt_time(segment["end"])
            text = segment["text"].strip()
            f.write(f"{i}\n{start} --> {end}\n{text}\n\n")

    with open(txt_path, "w", encoding="utf-8") as f:
        f.write(result["text"].strip())

    return {
        "srt_path": srt_path,
        "txt_path": txt_path,
        "text": result["text"].strip(),
        "language": lang_code
    }


def _seconds_to_srt_time(seconds: float) -> str:
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    secs = int(seconds % 60)
    millis = int((seconds % 1) * 1000)
    return f"{hours:02d}:{minutes:02d}:{secs:02d},{millis:03d}"


async def generate_subtitles(audio_path: str, language: str, output_dir: str) -> dict:
    loop = asyncio.get_event_loop()
    result = await loop.run_in_executor(
        _executor,
        _run_whisper,
        audio_path,
        language,
        output_dir
    )
    return result
