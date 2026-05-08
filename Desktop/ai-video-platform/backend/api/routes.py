"""
Routes FastAPI — API REST
"""
import json
import os
import uuid
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, HTTPException, Depends, BackgroundTasks
from fastapi.responses import FileResponse
from pydantic import BaseModel
from sqlalchemy.orm import Session

from database import get_db, VideoJob, SessionLocal

router = APIRouter()


class VideoRequest(BaseModel):
    subject: str
    style: str = "éducatif"
    duration: str = "3 min"
    voice: str = "homme"
    language: str = "Français"


class JobResponse(BaseModel):
    job_id: str
    status: str
    progress: int
    current_step: str
    script_title: Optional[str] = None
    script_description: Optional[str] = None
    video_url: Optional[str] = None
    thumbnail_url: Optional[str] = None
    subtitle_url: Optional[str] = None
    script_url: Optional[str] = None
    error_message: Optional[str] = None
    created_at: Optional[str] = None
    completed_at: Optional[str] = None


async def _run_pipeline_bg(job_id: str, req: VideoRequest):
    from pipeline.orchestrator import run_pipeline
    db = SessionLocal()
    try:
        await run_pipeline(
            job_id=job_id,
            subject=req.subject,
            style=req.style,
            duration=req.duration,
            voice=req.voice,
            language=req.language,
            db=db,
        )
    finally:
        db.close()


@router.post("/generate")
async def generate(req: VideoRequest, bg: BackgroundTasks, db: Session = Depends(get_db)):
    job_id = str(uuid.uuid4())
    job = VideoJob(
        job_id=job_id,
        subject=req.subject,
        style=req.style,
        duration=req.duration,
        voice=req.voice,
        language=req.language,
        status="pending",
        progress=0,
        current_step="En attente de démarrage...",
    )
    db.add(job)
    db.commit()
    bg.add_task(_run_pipeline_bg, job_id, req)
    return {"job_id": job_id, "status": "pending"}


@router.get("/jobs/{job_id}", response_model=JobResponse)
async def get_job(job_id: str, db: Session = Depends(get_db)):
    job = db.query(VideoJob).filter(VideoJob.job_id == job_id).first()
    if not job:
        raise HTTPException(404, "Job non trouvé")
    base = f"/api/jobs/{job_id}"
    return JobResponse(
        job_id=job.job_id,
        status=job.status,
        progress=job.progress,
        current_step=job.current_step,
        script_title=job.script_title,
        script_description=job.script_description,
        video_url=f"{base}/video" if job.video_path and os.path.exists(job.video_path) else None,
        thumbnail_url=f"{base}/thumbnail" if job.thumbnail_path and os.path.exists(job.thumbnail_path) else None,
        subtitle_url=f"{base}/subtitles" if job.subtitle_path and os.path.exists(job.subtitle_path) else None,
        script_url=f"{base}/script" if job.script_json else None,
        error_message=job.error_message,
        created_at=job.created_at.isoformat() if job.created_at else None,
        completed_at=job.completed_at.isoformat() if job.completed_at else None,
    )


@router.get("/jobs/{job_id}/video")
async def download_video(job_id: str, db: Session = Depends(get_db)):
    job = db.query(VideoJob).filter(VideoJob.job_id == job_id).first()
    if not job or not job.video_path or not os.path.exists(job.video_path):
        raise HTTPException(404, "Vidéo non disponible")
    return FileResponse(job.video_path, media_type="video/mp4",
                        filename=f"video_{job_id[:8]}.mp4")


@router.get("/jobs/{job_id}/thumbnail")
async def download_thumbnail(job_id: str, db: Session = Depends(get_db)):
    job = db.query(VideoJob).filter(VideoJob.job_id == job_id).first()
    if not job or not job.thumbnail_path or not os.path.exists(job.thumbnail_path):
        raise HTTPException(404, "Miniature non disponible")
    return FileResponse(job.thumbnail_path, media_type="image/jpeg",
                        filename=f"thumbnail_{job_id[:8]}.jpg")


@router.get("/jobs/{job_id}/subtitles")
async def download_subtitles(job_id: str, db: Session = Depends(get_db)):
    job = db.query(VideoJob).filter(VideoJob.job_id == job_id).first()
    if not job or not job.subtitle_path or not os.path.exists(job.subtitle_path):
        raise HTTPException(404, "Sous-titres non disponibles")
    return FileResponse(job.subtitle_path, media_type="text/plain",
                        filename=f"subtitles_{job_id[:8]}.srt")


@router.get("/jobs/{job_id}/script")
async def get_script(job_id: str, db: Session = Depends(get_db)):
    job = db.query(VideoJob).filter(VideoJob.job_id == job_id).first()
    if not job or not job.script_json:
        raise HTTPException(404, "Script non disponible")
    return json.loads(job.script_json)


@router.get("/history")
async def history(db: Session = Depends(get_db)):
    jobs = db.query(VideoJob).order_by(VideoJob.created_at.desc()).limit(30).all()
    return [
        {
            "job_id": j.job_id,
            "subject": j.subject,
            "style": j.style,
            "duration": j.duration,
            "language": j.language,
            "status": j.status,
            "progress": j.progress,
            "script_title": j.script_title,
            "created_at": j.created_at.isoformat() if j.created_at else None,
        }
        for j in jobs
    ]
