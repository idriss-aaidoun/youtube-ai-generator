"""
Module 6 — Montage automatique
Outils : MoviePy + FFmpeg
Fonctions : audio + images + transitions + sous-titres synchronisés
Export : MP4 1080p
"""

import os
import subprocess
import asyncio
from concurrent.futures import ThreadPoolExecutor
from moviepy.editor import (
    ImageClip, AudioFileClip, concatenate_videoclips
)

_executor = ThreadPoolExecutor(max_workers=1)

VIDEO_WIDTH = 1920
VIDEO_HEIGHT = 1080
FPS = 24
TRANSITION_DURATION = 0.5


def _build_video_with_moviepy(
    image_paths: list[str],
    audio_path: str,
    temp_output: str
) -> float:
    """
    Assemble les images + audio avec transitions douces (fade).
    Retourne la durée totale.
    """
    audio = AudioFileClip(audio_path)
    total_duration = audio.duration

    if not image_paths:
        raise ValueError("Au moins une image est requise pour le montage.")

    duration_per_image = total_duration / len(image_paths)

    clips = []
    for i, img_path in enumerate(image_paths):
        clip_duration = min(duration_per_image, total_duration - i * duration_per_image)
        if clip_duration <= 0:
            break

        clip = (
            ImageClip(img_path)
            .set_duration(clip_duration)
            .resize((VIDEO_WIDTH, VIDEO_HEIGHT))
        )

        if i > 0:
            clip = clip.crossfadein(TRANSITION_DURATION)

        clips.append(clip)

    video = concatenate_videoclips(clips, method="compose", padding=-TRANSITION_DURATION)
    video = video.set_audio(audio)

    video.write_videofile(
        temp_output,
        fps=FPS,
        codec="libx264",
        audio_codec="aac",
        temp_audiofile=temp_output + ".temp.m4a",
        remove_temp=True,
        threads=2,
        preset="ultrafast",
        logger=None
    )

    duration = video.duration
    audio.close()
    video.close()
    return duration


def _burn_subtitles_ffmpeg(temp_video: str, srt_path: str, final_output: str):
    """
    Utilise FFmpeg directement pour graver les sous-titres (.srt) dans la vidéo.
    Plus fiable qu'ImageMagick/TextClip.
    Commande : ffmpeg -i video.mp4 -vf subtitles=narration.srt output.mp4
    """
    subtitle_style = (
        "FontName=DejaVu Sans,"
        "FontSize=22,"
        "PrimaryColour=&H00FFFFFF,"
        "OutlineColour=&H00000000,"
        "Outline=2,"
        "Shadow=1,"
        "Bold=1,"
        "Alignment=2,"
        "MarginV=40"
    )

    srt_escaped = srt_path.replace("\\", "/").replace(":", "\\:")

    cmd = [
        "ffmpeg", "-y",
        "-i", temp_video,
        "-vf", f"subtitles='{srt_escaped}':force_style='{subtitle_style}'",
        "-c:v", "libx264",
        "-preset", "ultrafast",
        "-c:a", "copy",
        final_output
    ]

    result = subprocess.run(cmd, capture_output=True, text=True)

    if result.returncode != 0:
        import shutil
        shutil.copy2(temp_video, final_output)


def _render_video(
    image_paths: list[str],
    audio_path: str,
    srt_path: str,
    output_path: str
) -> str:
    temp_video = output_path.replace(".mp4", "_temp.mp4")

    try:
        _build_video_with_moviepy(image_paths, audio_path, temp_video)

        if srt_path and os.path.exists(srt_path):
            _burn_subtitles_ffmpeg(temp_video, srt_path, output_path)
        else:
            import shutil
            shutil.move(temp_video, output_path)

    finally:
        if os.path.exists(temp_video):
            os.remove(temp_video)

    return output_path


async def render_video(
    image_paths: list[str],
    audio_path: str,
    srt_path: str,
    output_path: str
) -> str:
    loop = asyncio.get_event_loop()
    result = await loop.run_in_executor(
        _executor,
        _render_video,
        image_paths,
        audio_path,
        srt_path,
        output_path
    )
    return result
