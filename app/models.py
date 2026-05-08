from __future__ import annotations

from datetime import datetime, timezone

from app.extensions import db
from app.utils import isoformat_z


def _split_text(value: str | None) -> list[str]:
    if not value:
        return []
    return [item.strip() for item in value.split(",") if item.strip()]


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


class User(db.Model):
    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    email = db.Column(db.String(255), unique=True, nullable=False)
    created_at = db.Column(db.DateTime(timezone=True), default=_utc_now, nullable=False)

    videos = db.relationship("Video", back_populates="user", lazy="selectin")

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "name": self.name,
            "email": self.email,
            "video_count": len(self.videos or []),
            "created_at": isoformat_z(self.created_at),
        }


class Video(db.Model):
    __tablename__ = "videos"

    id = db.Column(db.Integer, primary_key=True)
    generation_id = db.Column(db.String(64), unique=True, nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True)
    topic = db.Column(db.String(255), nullable=False)
    audience = db.Column(db.String(120), nullable=False, default="general")
    tone = db.Column(db.String(120), nullable=False, default="engaging")
    language = db.Column(db.String(32), nullable=False, default="fr")
    voice = db.Column(db.String(64), nullable=False, default="female")
    idea_primary_angle = db.Column(db.String(255), nullable=False, default="")
    idea_keywords = db.Column(db.Text, nullable=False, default="")
    title = db.Column(db.String(255), nullable=False)
    description = db.Column(db.Text, nullable=False)
    seo_tags = db.Column(db.Text, nullable=False, default="")
    script = db.Column(db.Text, nullable=False)
    audio_path = db.Column(db.String(512), nullable=False)
    storyboard_path = db.Column(db.String(512), nullable=False)
    subtitle_path = db.Column(db.String(512), nullable=False)
    montage_path = db.Column(db.String(512), nullable=False)
    artifact_dir = db.Column(db.String(512), nullable=False)
    seo_score = db.Column(db.Integer, nullable=False, default=0)
    publication_status = db.Column(db.String(64), nullable=False, default="draft")
    youtube_url = db.Column(db.String(512))
    created_at = db.Column(db.DateTime(timezone=True), default=_utc_now, nullable=False)
    updated_at = db.Column(db.DateTime(timezone=True), default=_utc_now, onupdate=_utc_now, nullable=False)

    user = db.relationship("User", back_populates="videos")
    analytics = db.relationship(
        "Analytics",
        back_populates="video",
        cascade="all, delete-orphan",
        lazy="selectin",
    )

    def to_summary_dict(self) -> dict:
        return {
            "id": self.id,
            "generation_id": self.generation_id,
            "topic": self.topic,
            "title": self.title,
            "seo_score": self.seo_score,
            "publication_status": self.publication_status,
            "language": self.language,
            "voice": self.voice,
            "created_at": isoformat_z(self.created_at),
        }

    def to_dict(self, include_script: bool = False, include_analytics: bool = False) -> dict:
        payload = {
            "id": self.id,
            "generation_id": self.generation_id,
            "topic": self.topic,
            "audience": self.audience,
            "tone": self.tone,
            "language": self.language,
            "voice": self.voice,
            "idea_primary_angle": self.idea_primary_angle,
            "idea_keywords": _split_text(self.idea_keywords),
            "title": self.title,
            "description": self.description,
            "seo_tags": _split_text(self.seo_tags),
            "audio_path": self.audio_path,
            "storyboard_path": self.storyboard_path,
            "subtitle_path": self.subtitle_path,
            "montage_path": self.montage_path,
            "artifact_dir": self.artifact_dir,
            "seo_score": self.seo_score,
            "publication_status": self.publication_status,
            "youtube_url": self.youtube_url,
            "created_at": isoformat_z(self.created_at),
            "updated_at": isoformat_z(self.updated_at),
        }
        if include_script:
            payload["script"] = self.script
        if include_analytics:
            payload["analytics"] = [item.to_dict() for item in self.analytics]
        return payload


class Analytics(db.Model):
    __tablename__ = "analytics"

    id = db.Column(db.Integer, primary_key=True)
    video_id = db.Column(db.Integer, db.ForeignKey("videos.id"), nullable=False)
    views = db.Column(db.Integer, nullable=False, default=0)
    likes = db.Column(db.Integer, nullable=False, default=0)
    ctr = db.Column(db.Float, nullable=False, default=0.0)
    watch_time_minutes = db.Column(db.Float, nullable=False, default=0.0)
    created_at = db.Column(db.DateTime(timezone=True), default=_utc_now, nullable=False)

    video = db.relationship("Video", back_populates="analytics")

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "video_id": self.video_id,
            "views": self.views,
            "likes": self.likes,
            "ctr": self.ctr,
            "watch_time_minutes": self.watch_time_minutes,
            "created_at": isoformat_z(self.created_at),
        }
