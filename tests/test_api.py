from __future__ import annotations

from pathlib import Path

import pytest

from app import create_app
from app.config import Config
from app.extensions import db


def build_test_config(tmp_path: Path):
    class TestConfig(Config):
        TESTING = True
        SQLALCHEMY_DATABASE_URI = f"sqlite:///{(tmp_path / 'test.db').as_posix()}"
        OUTPUT_DIR = tmp_path / "generated"
        YOUTUBE_ACCESS_TOKEN = ""
        YOUTUBE_CLIENT_ID = ""
        YOUTUBE_CLIENT_SECRET = ""
        YOUTUBE_REFRESH_TOKEN = ""

    return TestConfig


@pytest.fixture()
def app(tmp_path: Path):
    application = create_app(build_test_config(tmp_path))
    yield application
    with application.app_context():
        db.session.remove()
        db.drop_all()


@pytest.fixture()
def client(app):
    return app.test_client()


def test_health_endpoint(client):
    response = client.get("/health")
    assert response.status_code == 200
    assert response.get_json()["status"] == "ok"


def test_homepage_renders(client):
    response = client.get("/")
    assert response.status_code == 200
    assert b"YouTube AI Studio" in response.data


def test_generate_endpoint_persists_video(client):
    response = client.post(
        "/api/generate",
        json={
            "subject": "Automatiser une chaîne YouTube",
            "audience": "creators",
            "tone": "direct",
            "language": "fr",
            "voice": "female",
            "duration_minutes": 3,
        },
    )

    assert response.status_code == 201
    payload = response.get_json()
    assert payload["video"]["title"]
    assert payload["pipeline"]["summary"]["trend_score"] >= 65
    assert payload["pipeline"]["summary"]["trend_category"] == "Création YouTube & contenu"
    assert payload["pipeline"]["summary"]["trend_stage"] in {"rising", "strong"}
    assert payload["pipeline"]["summary"]["trend_format"]
    assert payload["pipeline"]["summary"]["trend_summary"]
    assert isinstance(payload["pipeline"]["summary"]["trend_signals"], list)
    assert isinstance(payload["pipeline"]["summary"]["trend_opportunities"], list)
    assert isinstance(payload["pipeline"]["summary"]["trend_risks"], list)
    assert isinstance(payload["pipeline"]["summary"]["trend_breakdown"], dict)
    assert payload["pipeline"]["summary"]["seo_score"] >= 70
    assert payload["pipeline"]["audio"]["status"] == "planned"
    assert payload["pipeline"]["summary"]["audio_provider"] == "placeholder"
    assert payload["pipeline"]["summary"]["visual_provider"] == "local_placeholder"
    assert payload["pipeline"]["summary"]["visual_image_count"] == 3
    assert payload["pipeline"]["summary"]["video_status"] == "generated"
    assert payload["pipeline"]["summary"]["video_provider"] == "imageio_ffmpeg"
    assert payload["pipeline"]["summary"]["subtitle_path"].endswith("subtitles.srt")
    assert payload["pipeline"]["summary"]["thumbnail_status"] == "generated"
    assert payload["pipeline"]["summary"]["thumbnail_provider"] == "thumbnail_composite"
    assert payload["pipeline"]["summary"]["thumbnail_source_image_provider"] == "local_placeholder"
    assert payload["pipeline"]["summary"]["thumbnail_upload_status"] == "pending_credentials"
    assert payload["pipeline"]["summary"]["thumbnail_path"].endswith("thumbnail.png")
    assert payload["pipeline"]["summary"]["publication_chapter_count"] == 3
    assert payload["pipeline"]["summary"]["publication_hashtag_count"] >= 3
    assert payload["pipeline"]["summary"]["publication_provider"] == "local_plan"
    assert payload["video"]["montage_path"].endswith(".mp4")
    assert payload["video"]["subtitle_path"].endswith(".srt")
    assert "Chapitres" in payload["video"]["description"]
    assert "0:00" in payload["video"]["description"]
    assert "#" in payload["video"]["description"]
    assert payload["pipeline"]["summary"]["script_source"] == "local_template"


def test_generate_endpoint_honors_publication_overrides(client):
    response = client.post(
        "/api/generate",
        json={
            "subject": "Automatiser une chaîne YouTube",
            "audience": "creators",
            "tone": "direct",
            "language": "fr",
            "voice": "female",
            "duration_minutes": 3,
            "publication_options": {
                "chapters": [
                    {"timestamp": "0:20", "title": "Départ"},
                    {"timestamp": "1:10", "title": "Cœur"},
                ],
                "hashtags": ["Automation", "#YouTube", "Creators"],
                "hashtag_blacklist": ["creators"],
            },
        },
    )

    assert response.status_code == 201
    payload = response.get_json()
    assert payload["pipeline"]["summary"]["publication_chapter_source"] == "manual"
    assert payload["pipeline"]["summary"]["publication_hashtag_source"] == "manual"
    assert payload["pipeline"]["summary"]["publication_chapter_count"] == 2
    assert payload["pipeline"]["summary"]["publication_hashtag_count"] == 2
    assert "0:20 Départ" in payload["video"]["description"]
    assert "1:10 Cœur" in payload["video"]["description"]
    assert "#automation" in payload["video"]["description"]
    assert "#youtube" in payload["video"]["description"]


def test_generate_endpoint_accepts_topic_title_and_description(client):
    response = client.post(
        "/api/generate",
        json={
            "topic": "Créer un SaaS plus crédible",
            "title": "Créer un SaaS plus crédible en 3 étapes",
            "description": "Mettre en avant le brief produit et la promesse business.",
            "audience": "founders",
            "tone": "direct",
            "language": "fr",
            "voice": "female",
            "duration_minutes": 3,
        },
    )

    assert response.status_code == 201
    payload = response.get_json()
    assert payload["pipeline"]["request"]["subject"] == "Créer un SaaS plus crédible"
    assert payload["pipeline"]["request"]["topic"] == "Créer un SaaS plus crédible"
    assert payload["pipeline"]["request"]["title"] == "Créer un SaaS plus crédible en 3 étapes"
    assert payload["pipeline"]["request"]["creative_brief"] == "Mettre en avant le brief produit et la promesse business."
    assert payload["pipeline"]["script"]["title_candidates"][0] == "Créer un SaaS plus crédible en 3 étapes"

