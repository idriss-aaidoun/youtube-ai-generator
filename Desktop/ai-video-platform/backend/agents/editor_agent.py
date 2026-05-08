"""
Agent 4 — Editor Agent
Rôle : Montage automatique de la vidéo finale
Stack : MoviePy + FFmpeg
Sortie : video.mp4 1080p (audio + images Ken Burns + transitions + sous-titres)
"""
import os
import subprocess
import shutil
import asyncio
import numpy as np
from concurrent.futures import ThreadPoolExecutor
from PIL import Image as PILImage

from moviepy.editor import VideoClip, AudioFileClip, concatenate_videoclips

from settings import settings

_executor = ThreadPoolExecutor(max_workers=1)
TRANSITION = 0.5


def _ken_burns_clip(img_path: str, duration: float, w: int, h: int, index: int):
    """
    Crée un clip avec effet Ken Burns (zoom/panoramique lent) sur une image.
    Rend la vidéo dynamique même avec des images statiques.
    """
    # Charger et redimensionner l'image à 110% pour avoir de la marge de mouvement
    scale = 1.10
    sw, sh = int(w * scale), int(h * scale)
    try:
        pil_img = PILImage.open(img_path).convert("RGB").resize((sw, sh), PILImage.LANCZOS)
    except Exception:
        pil_img = PILImage.new("RGB", (sw, sh), (20, 20, 50))
    img_array = np.array(pil_img)

    dx = sw - w  # marge horizontale
    dy = sh - h  # marge verticale

    # 5 mouvements différents pour varier entre les clips
    movements = [
        (0,       0,       dx,      dy),      # haut-gauche → bas-droite
        (dx,      0,       0,       dy),      # haut-droite → bas-gauche
        (0,       dy,      dx,      0),       # bas-gauche → haut-droite
        (dx // 2, 0,       dx // 2, dy),      # zoom descendant (centre)
        (0,       dy // 2, dx,      dy // 2), # panoramique droite
    ]
    x0, y0, x1, y1 = movements[index % len(movements)]

    def make_frame(t):
        progress = min(t / max(duration, 0.001), 1.0)
        # Interpolation douce (ease in-out)
        progress = progress * progress * (3 - 2 * progress)
        cx = int(x0 + (x1 - x0) * progress)
        cy = int(y0 + (y1 - y0) * progress)
        return img_array[cy:cy + h, cx:cx + w]

    return VideoClip(make_frame, duration=duration).set_fps(settings.VIDEO_FPS)


def _assemble(image_paths: list, audio_path: str, temp_out: str) -> None:
    """Assemble images avec Ken Burns + audio."""
    audio = AudioFileClip(audio_path)
    total = audio.duration
    n = len(image_paths)
    w, h = settings.VIDEO_WIDTH, settings.VIDEO_HEIGHT

    dur_per = total / n
    clips = []
    for i, p in enumerate(image_paths):
        d = min(dur_per, total - i * dur_per)
        if d <= 0:
            break
        clip = _ken_burns_clip(p, d, w, h, i)
        if i > 0:
            try:
                clip = clip.crossfadein(TRANSITION)
            except Exception:
                pass
        clips.append(clip)

    try:
        video = concatenate_videoclips(clips, method="compose", padding=-TRANSITION)
    except Exception:
        video = concatenate_videoclips(clips, method="compose")

    video = video.set_audio(audio)
    video.write_videofile(
        temp_out,
        fps=settings.VIDEO_FPS,
        codec="libx264",
        audio_codec="aac",
        audio_bitrate="192k",
        temp_audiofile=temp_out + ".tmp.m4a",
        remove_temp=True,
        threads=2,
        preset="fast",
        ffmpeg_params=["-crf", "20"],
        logger=None,
    )
    audio.close()
    video.close()


def _burn_subs(temp_video: str, srt_path: str, final_out: str) -> None:
    """Grave les sous-titres .srt dans la vidéo via FFmpeg."""
    style = (
        "FontName=DejaVu Sans,FontSize=28,"
        "PrimaryColour=&H00FFFFFF,OutlineColour=&H00000000,"
        "Outline=3,Shadow=2,Bold=1,Alignment=2,MarginV=60"
    )
    srt_safe = srt_path.replace("\\", "/").replace(":", "\\:")
    cmd = [
        "ffmpeg", "-y",
        "-i", temp_video,
        "-vf", f"subtitles='{srt_safe}':force_style='{style}'",
        "-c:v", "libx264",
        "-preset", "fast",
        "-crf", "20",
        "-c:a", "copy",
        final_out,
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        shutil.copy2(temp_video, final_out)


def _render(image_paths: list, audio_path: str, srt_path: str, output_path: str) -> str:
    temp = output_path.replace(".mp4", "_tmp.mp4")
    try:
        _assemble(image_paths, audio_path, temp)
        if srt_path and os.path.exists(srt_path):
            _burn_subs(temp, srt_path, output_path)
        else:
            shutil.move(temp, output_path)
    finally:
        if os.path.exists(temp):
            try:
                os.remove(temp)
            except Exception:
                pass
    return output_path


async def run(image_paths: list, audio_path: str, srt_path: str, output_path: str) -> str:
    """Lance le montage dans un thread pour ne pas bloquer FastAPI."""
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(
        _executor, _render, image_paths, audio_path, srt_path, output_path
    )