from __future__ import annotations

from datetime import datetime, timezone
from collections.abc import Mapping
from pathlib import Path
from uuid import uuid4

from app.services.audio_service import generate_audio_package
from app.services.idea_service import generate_idea_package
from app.services.montage_service import assemble_video_package
from app.services.script_service import generate_script_package
from app.services.seo_service import generate_seo_package
from app.services.thumbnail_service import generate_thumbnail_package
from app.services.visual_service import generate_visual_package
from app.services.youtube_service import prepare_publication_package
from app.utils import clamp_int, coerce_text, ensure_directory, slugify, timestamp_token, write_json


def normalize_request(payload: dict | None) -> dict:
    payload = payload or {}
    publication_options = payload.get("publication_options")
    if not isinstance(publication_options, dict):
        publication_options = {}

    subject = coerce_text(payload.get("subject") or payload.get("topic") or payload.get("title"), "")
    topic = coerce_text(payload.get("topic") or subject, subject)
    title = coerce_text(payload.get("title"), "")
    description = coerce_text(payload.get("description"), "")

    return {
        "subject": subject,
        "topic": topic,
        "title": title,
        "description": description,
        "creative_brief": description,
        "audience": coerce_text(payload.get("audience"), "general"),
        "tone": coerce_text(payload.get("tone"), "engaging"),
        "language": coerce_text(payload.get("language"), "fr"),
        "voice": coerce_text(payload.get("voice"), "female"),
        "duration_minutes": clamp_int(payload.get("duration_minutes"), 3, minimum=1, maximum=30),
        "user_id": payload.get("user_id"),
        "publication_options": publication_options,
    }


class VideoPipeline:
    def __init__(self, output_root: Path | str):
        self.output_root = ensure_directory(Path(output_root))

    def generate(self, payload: dict | None, settings: Mapping[str, object] | None = None) -> dict:
        request = normalize_request(payload)
        subject = request["subject"]

        if not subject:
            raise ValueError("subject is required")

        generation_id = uuid4().hex
        folder_name = f"{slugify(subject)}-{timestamp_token()}-{generation_id[:8]}"
        artifact_dir = ensure_directory(self.output_root / folder_name)

        idea = generate_idea_package(
            subject=subject,
            audience=request["audience"],
            tone=request["tone"],
            language=request["language"],
        )
        script = generate_script_package(
            subject=subject,
            idea_package=idea,
            audience=request["audience"],
            tone=request["tone"],
            language=request["language"],
            duration_minutes=request["duration_minutes"],
            requested_title=request["title"],
            creative_brief=request["creative_brief"],
            settings=settings,
        )
        audio = generate_audio_package(
            subject=subject,
            script_package=script,
            voice=request["voice"],
            language=request["language"],
            artifact_dir=artifact_dir,
            settings=settings,
        )
        visuals = generate_visual_package(
            subject=subject,
            idea_package=idea,
            script_package=script,
            artifact_dir=artifact_dir,
            settings=settings,
        )
        montage = assemble_video_package(
            subject=subject,
            script_package=script,
            audio_package=audio,
            visual_package=visuals,
            artifact_dir=artifact_dir,
            settings=settings,
        )
        seo = generate_seo_package(subject=subject, idea_package=idea, script_package=script)
        thumbnail = generate_thumbnail_package(
            subject=subject,
            seo_package=seo,
            visual_package=visuals,
            artifact_dir=artifact_dir,
        )
        trend_analysis = idea["trend_analysis"]
        publication = prepare_publication_package(
            subject=subject,
            seo_package=seo,
            artifact_dir=artifact_dir,
            video_path=montage["artifact_path"],
            script_package=script,
            publication_options=request["publication_options"],
            thumbnail_package=thumbnail,
            settings=settings,
        )

        result = {
            "generation_id": generation_id,
            "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z"),
            "request": request,
            "summary": {
                "title": seo["title"],
                "trend_score": idea["trend_score"],
                "trend_category": idea["trend_category"],
                "trend_stage": idea["trend_stage"],
                "trend_format": idea["trend_analysis"].get("recommended_format"),
                "trend_summary": idea["trend_analysis"].get("summary"),
                "trend_signals": trend_analysis.get("signals") or [],
                "trend_opportunities": trend_analysis.get("opportunities") or [],
                "trend_risks": trend_analysis.get("risks") or [],
                "trend_keywords": trend_analysis.get("matched_keywords") or [],
                "trend_phrases": trend_analysis.get("matched_phrases") or [],
                "trend_breakdown": trend_analysis.get("score_breakdown") or {},
                "seo_score": seo["score"],
                "scene_count": visuals["scene_count"],
                "audio_status": audio["status"],
                "audio_provider": audio["provider"],
                "audio_voice_id": audio.get("voice_id"),
                "visual_provider": visuals["provider"],
                "visual_model": visuals.get("image_model"),
                "visual_image_count": len(visuals.get("image_assets", [])),
                "video_status": montage["status"],
                "video_provider": montage["provider"],
                "subtitle_path": montage.get("subtitle_path"),
                "thumbnail_status": thumbnail["status"],
                "thumbnail_provider": thumbnail["provider"],
                "thumbnail_path": thumbnail["artifact_path"],
                "thumbnail_source_image_provider": thumbnail.get("source_image_provider"),
                "thumbnail_upload_status": publication.get("thumbnail_upload_status"),
                "publication_chapter_count": len(publication.get("chapters", [])),
                "publication_hashtag_count": len(publication.get("hashtags", [])),
                "publication_chapter_source": publication.get("chapter_source"),
                "publication_hashtag_source": publication.get("hashtag_source"),
                "publication_status": publication["status"],
                "publication_provider": publication["provider"],
                "publication_url": publication.get("youtube_url"),
                "script_source": script["source"],
                "script_model": script.get("model_name"),
                "video_path": montage["artifact_path"],
                "artifact_dir": str(artifact_dir),
                "primary_angle": idea["primary_angle"],
            },
            "idea": idea,
            "script": script,
            "audio": audio,
            "visuals": visuals,
            "montage": montage,
            "seo": seo,
            "thumbnail": thumbnail,
            "publication": publication,
            "artifact_dir": str(artifact_dir),
            "pipeline_stages": [
                {"name": "idea", "status": "generated"},
                {"name": "script", "status": "generated"},
                {"name": "audio", "status": audio["status"]},
                {"name": "visuals", "status": visuals["status"]},
                {"name": "montage", "status": montage["status"]},
                {"name": "thumbnail", "status": thumbnail["status"]},
                {"name": "seo", "status": "generated"},
                {"name": "publication", "status": publication["status"]},
            ],
        }
        write_json(artifact_dir / "generation_result.json", result)
        return result


def create_pipeline(output_root: Path | str) -> VideoPipeline:
    return VideoPipeline(output_root=output_root)
