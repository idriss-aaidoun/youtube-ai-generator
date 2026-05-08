"""
STT Service — Whisper
Rôle : Transcrit l'audio en sous-titres synchronisés
Stack : openai-whisper
Équivalent CLI : whisper narration.wav --language French
Sorties : narration.srt + narration.txt
"""
import os
import asyncio
from concurrent.futures import ThreadPoolExecutor

import whisper

_executor = ThreadPoolExecutor(max_workers=1)
_model = None


def _get_model():
    global _model
    if _model is None:
        _model = whisper.load_model("base")
    return _model


def _transcribe(audio_path: str, language: str, output_dir: str) -> dict:
    lang_code = "fr" if language == "Français" else "en"

    model = _get_model()
    result = model.transcribe(audio_path, language=lang_code, verbose=False)

    base = os.path.splitext(os.path.basename(audio_path))[0]
    srt_path = os.path.join(output_dir, f"{base}.srt")
    txt_path = os.path.join(output_dir, f"{base}.txt")

    with open(srt_path, "w", encoding="utf-8") as f:
        for i, seg in enumerate(result["segments"], 1):
            f.write(f"{i}\n{_ts(seg['start'])} --> {_ts(seg['end'])}\n{seg['text'].strip()}\n\n")

    with open(txt_path, "w", encoding="utf-8") as f:
        f.write(result["text"].strip())

    return {
        "srt_path": srt_path,
        "txt_path": txt_path,
        "text": result["text"].strip(),
    }


def _ts(s: float) -> str:
    h = int(s // 3600)
    m = int((s % 3600) // 60)
    sec = int(s % 60)
    ms = int((s % 1) * 1000)
    return f"{h:02d}:{m:02d}:{sec:02d},{ms:03d}"


async def run(audio_path: str, language: str, output_dir: str) -> dict:
    os.makedirs(output_dir, exist_ok=True)
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(_executor, _transcribe, audio_path, language, output_dir)
