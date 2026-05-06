from __future__ import annotations

from flask import Blueprint, current_app, jsonify, render_template, request

from app.extensions import db
from app.models import Analytics, Video
from app.services.pipeline import create_pipeline
from app.utils import coerce_text


bp = Blueprint("main", __name__)


def _pipeline():
    return create_pipeline(current_app.config["OUTPUT_DIR"])


@bp.route("/")
def index():
    return render_template("index.html", app_name="YouTube AI Studio")


@bp.route("/health")
def health():
    return jsonify({"status": "ok", "service": "ytb-automation", "version": "0.1.0"})


@bp.route("/api/generate", methods=["POST"])
def generate():
    payload = request.get_json(silent=True) or {}
    subject = coerce_text(payload.get("subject") or payload.get("topic") or payload.get("title"), "")

    if not subject:
        return jsonify({"error": "subject is required"}), 400

    try:
        result = _pipeline().generate(payload, settings=current_app.config)
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400

    video = Video(
        generation_id=result["generation_id"],
        topic=result["request"]["subject"],
        audience=result["request"]["audience"],
        tone=result["request"]["tone"],
        language=result["request"]["language"],
        voice=result["request"]["voice"],
        idea_primary_angle=result["idea"]["primary_angle"],
        idea_keywords=", ".join(result["idea"]["keywords"]),
        title=result["seo"]["title"],
        description=result["publication"]["description"],
        seo_tags=", ".join(result["seo"]["tags"]),
        script=result["script"]["full_text"],
        audio_path=result["audio"].get("audio_file_path") or result["audio"]["artifact_path"],
        storyboard_path=result["visuals"]["artifact_path"],
        subtitle_path=result["montage"]["subtitle_path"],
        montage_path=result["montage"]["artifact_path"],
        artifact_dir=result["artifact_dir"],
        seo_score=result["seo"]["score"],
        publication_status=result["publication"]["status"],
        youtube_url=result["publication"]["youtube_url"],
    )
    analytics = Analytics(video=video, views=0, likes=0, ctr=result["seo"]["estimated_ctr"], watch_time_minutes=0.0)

    db.session.add(video)
    db.session.add(analytics)
    db.session.commit()

    return jsonify(
        {
            "message": "generation completed",
            "pipeline": result,
            "video": video.to_dict(include_script=True, include_analytics=True),
        }
    ), 201


@bp.route("/api/videos")
def list_videos():
    videos = Video.query.order_by(Video.created_at.desc()).all()
    return jsonify({"items": [video.to_summary_dict() for video in videos], "count": len(videos)})


@bp.route("/api/videos/<int:video_id>")
def get_video(video_id: int):
    video = db.session.get(Video, video_id)
    if video is None:
        return jsonify({"error": "video not found"}), 404

    return jsonify(video.to_dict(include_script=True, include_analytics=True))
