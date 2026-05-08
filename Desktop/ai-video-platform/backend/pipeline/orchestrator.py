"""
Pipeline Orchestrator v3.0 — YouTube Quality
7 étapes + post-processing audio + musique de fond optionnelle
"""
import os
import json
from datetime import datetime
from sqlalchemy.orm import Session

from agents import script_agent, voice_agent, visual_agent, editor_agent, seo_agent
from agents import stt_service, thumbnail_service
from services import audio_processor, music_mixer
from database import VideoJob
from settings import settings


def _update(db: Session, job_id: str, **kwargs):
    job = db.query(VideoJob).filter(VideoJob.job_id == job_id).first()
    if job:
        for k, v in kwargs.items():
            setattr(job, k, v)
        db.commit()


async def run_pipeline(
    job_id: str,
    subject: str,
    style: str,
    duration: str,
    voice: str,
    language: str,
    db: Session,
    add_music: bool = True,
):
    audio_dir  = os.path.join(settings.AUDIO_DIR,  job_id)
    images_dir = os.path.join(settings.IMAGES_DIR, job_id)
    video_dir  = os.path.join(settings.VIDEOS_DIR, job_id)
    for d in [audio_dir, images_dir, video_dir]:
        os.makedirs(d, exist_ok=True)

    try:
        # ── Étape 1 : Script ─────────────────────────────────────────────────
        _update(db, job_id, status="running", progress=8,
                current_step="[1/8] Génération du script IA...")

        script = await script_agent.run(subject, style, duration, language)
        _update(db, job_id, progress=16,
                current_step="[2/8] Synthèse vocale (TTS)...",
                script_title=script.get("title", ""),
                script_json=json.dumps(script, ensure_ascii=False))

        # ── Étape 2 : Voix ───────────────────────────────────────────────────
        audio_path = os.path.join(audio_dir, "narration.wav")
        await voice_agent.run(script, audio_path, language, voice)

        # ── Étape 3 : Post-traitement audio ──────────────────────────────────
        _update(db, job_id, progress=26,
                current_step="[3/8] Post-traitement audio (normalisation, compression)...")

        enhanced_audio = await audio_processor.process(audio_path, audio_dir)

        # ── Étape 3b : Musique de fond (optionnelle) ──────────────────────────
        if add_music and settings.ADD_BACKGROUND_MUSIC:
            _update(db, job_id, progress=30,
                    current_step="[3b/8] Ajout musique de fond...")
            final_audio = await music_mixer.add_background_music(
                enhanced_audio, audio_dir, style
            )
        else:
            final_audio = enhanced_audio

        # ── Étape 4 : Images ─────────────────────────────────────────────────
        _update(db, job_id, progress=38,
                current_step="[4/8] Génération des images de scènes...")

        image_paths = await visual_agent.run(
            sections=script.get("sections", []),
            output_dir=images_dir,
            subject=subject,
        )

        # ── Étape 5 : Whisper STT → sous-titres .srt ─────────────────────────
        _update(db, job_id, progress=54,
                current_step="[5/8] Transcription Whisper → sous-titres .srt...")

        srt_path = None
        try:
            stt_result = await stt_service.run(final_audio, language, audio_dir)
            srt_path = stt_result.get("srt_path")
        except Exception:
            pass

        # ── Étape 6 : Montage vidéo ───────────────────────────────────────────
        _update(db, job_id, progress=66,
                current_step="[6/8] Montage vidéo (Ken Burns + transitions + sous-titres)...")

        video_path = os.path.join(video_dir, "video.mp4")
        await editor_agent.run(image_paths, final_audio, srt_path, video_path)

        # ── Étape 7 : SEO ─────────────────────────────────────────────────────
        _update(db, job_id, progress=82,
                current_step="[7/8] Génération SEO (titre, description, hashtags)...")

        seo = await seo_agent.run(script, subject, language)

        # ── Étape 8 : Miniature ───────────────────────────────────────────────
        _update(db, job_id, progress=93,
                current_step="[8/8] Génération de la miniature YouTube...")

        thumbnail_path = os.path.join(video_dir, "thumbnail.jpg")
        thumbnail_service.run(
            title=script.get("title", subject),
            thumbnail_text=seo.get("thumbnail_text", ""),
            output_path=thumbnail_path,
            background_image=image_paths[0] if image_paths else None,
        )

        # ── Résultat ──────────────────────────────────────────────────────────
        full_data = {**script, **seo}
        _update(
            db, job_id,
            status="completed", progress=100,
            current_step="Terminé — vidéo YouTube-ready !",
            script_title=seo.get("seo_title") or script.get("title", ""),
            script_description=seo.get("description", ""),
            script_json=json.dumps(full_data, ensure_ascii=False),
            video_path=video_path,
            thumbnail_path=thumbnail_path,
            subtitle_path=srt_path,
            completed_at=datetime.utcnow(),
        )

    except Exception as e:
        _update(db, job_id, status="failed", progress=0,
                current_step="Erreur", error_message=str(e))
        raise