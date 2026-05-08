"""
Audio Post-Processor — Qualité broadcast
Pipeline FFmpeg :
  1. Suppression silences longs
  2. Filtre passe-haut (coupe bruit < 80 Hz)
  3. Compression voix (acompressor)
  4. Normalisation EBU R128 (standard YouTube/broadcast)
  5. Normalisation dynamique fine
"""
import os
import subprocess
import asyncio
from concurrent.futures import ThreadPoolExecutor

_executor = ThreadPoolExecutor(max_workers=2)


def _remove_long_silences(input_path: str, output_path: str) -> str:
    """Supprime les silences supérieurs à 1.2 secondes."""
    cmd = [
        "ffmpeg", "-y", "-i", input_path,
        "-af", "silenceremove=stop_periods=-1:stop_duration=1.2:stop_threshold=-38dB",
        output_path,
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode == 0 and os.path.exists(output_path) and os.path.getsize(output_path) > 1000:
        return output_path
    return input_path


def _enhance_audio(input_path: str, output_path: str) -> str:
    """
    Chaîne de filtres FFmpeg pour qualité broadcast :
    - highpass     : supprime les bruits basse fréquence (< 80 Hz)
    - acompressor  : compresse légèrement pour voix claire et constante
    - loudnorm     : normalisation EBU R128 (standard YouTube)
    - dynaudnorm   : lissage final des variations de volume
    """
    filters = ",".join([
        "highpass=f=80",
        "acompressor=threshold=-18dB:ratio=3.5:attack=5:release=60:makeup=2dB",
        "loudnorm=I=-16:LRA=9:TP=-1.5",
        "dynaudnorm=p=0.9:s=5:r=0.9",
    ])
    cmd = [
        "ffmpeg", "-y", "-i", input_path,
        "-af", filters,
        "-ar", "44100", "-ac", "1",
        "-c:a", "pcm_s16le",
        output_path,
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode == 0 and os.path.exists(output_path):
        return output_path

    # Fallback : normalisation seule
    cmd_simple = [
        "ffmpeg", "-y", "-i", input_path,
        "-af", "loudnorm=I=-16:LRA=11:TP=-1.5",
        "-ar", "44100",
        output_path,
    ]
    subprocess.run(cmd_simple, capture_output=True)
    return output_path if os.path.exists(output_path) else input_path


def _get_audio_duration(path: str) -> float:
    """Retourne la durée audio en secondes via ffprobe."""
    cmd = [
        "ffprobe", "-v", "quiet", "-show_entries", "format=duration",
        "-of", "default=noprint_wrappers=1:nokey=1", path,
    ]
    try:
        out = subprocess.check_output(cmd, stderr=subprocess.DEVNULL).decode().strip()
        return float(out)
    except Exception:
        return 0.0


async def process(input_path: str, output_dir: str) -> str:
    """
    Post-traite l'audio TTS pour une qualité broadcast YouTube.
    Retourne le chemin du fichier audio amélioré.
    """
    loop = asyncio.get_event_loop()

    # Étape 1 : suppression silences
    no_silence = os.path.join(output_dir, "narration_ns.wav")
    cleaned = await loop.run_in_executor(_executor, _remove_long_silences, input_path, no_silence)

    # Étape 2 : enhancement complet
    enhanced = os.path.join(output_dir, "narration_enhanced.wav")
    result = await loop.run_in_executor(_executor, _enhance_audio, cleaned, enhanced)

    # Nettoyage fichier intermédiaire
    if cleaned != input_path and os.path.exists(cleaned):
        try:
            os.remove(cleaned)
        except Exception:
            pass

    return result