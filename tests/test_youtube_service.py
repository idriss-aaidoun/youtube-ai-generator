from __future__ import annotations

import json
from pathlib import Path

from app.services.youtube_service import prepare_publication_package


class _FakeHeaders:
    def __init__(self, values: dict[str, str]):
        self._values = values

    def get(self, key, default=None):
        return self._values.get(key, default)


class _FakeResponse:
    def __init__(self, payload: bytes, headers: dict[str, str] | None = None):
        self._payload = payload
        self.headers = _FakeHeaders(headers or {})

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False

    def read(self):
        return self._payload


def test_prepare_publication_package_uploads_to_youtube(monkeypatch, tmp_path: Path):
    video_path = tmp_path / "rendered_video.mp4"
    video_path.write_bytes(b"FAKE-MP4-BYTES")
    thumbnail_path = tmp_path / "thumbnail.png"
    thumbnail_path.write_bytes(b"FAKE-THUMBNAIL-BYTES")

    captured_requests = []

    def fake_urlopen(request, timeout=0):
        body = request.data.decode("utf-8") if request.data else None
        captured_requests.append((request.full_url, body, dict(request.headers), timeout, request.get_method()))

        if request.full_url == "https://oauth2.googleapis.com/token":
            return _FakeResponse(json.dumps({"access_token": "access-token"}).encode("utf-8"), {"Content-Type": "application/json"})

        if request.full_url.startswith("https://www.googleapis.com/upload/youtube/v3/videos") and request.get_method() == "POST":
            return _FakeResponse(b"", {"Location": "https://upload.youtube.test/resumable-session"})

        if request.full_url == "https://upload.youtube.test/resumable-session" and request.get_method() == "PUT":
            return _FakeResponse(json.dumps({"id": "video123"}).encode("utf-8"), {"Content-Type": "application/json"})

        if request.full_url == "https://www.googleapis.com/upload/youtube/v3/thumbnails/set?videoId=video123&uploadType=media" and request.get_method() == "POST":
            return _FakeResponse(json.dumps({"kind": "youtube#thumbnailSetResponse"}).encode("utf-8"), {"Content-Type": "application/json"})

        raise AssertionError(f"Unexpected request: {request.full_url}")

    monkeypatch.setattr("urllib.request.urlopen", fake_urlopen)

    result = prepare_publication_package(
        subject="Automatiser une chaîne YouTube",
        seo_package={
            "title": "Automatiser une chaîne YouTube : le guide simple en 3 minutes",
            "description": "Description SEO",
            "tags": ["youtube", "automation"],
        },
        artifact_dir=tmp_path / "generated",
        video_path=video_path,
        script_package={
            "duration_minutes": 3,
            "sections": [
                {"heading": "Hook", "summary": "Accroche"},
                {"heading": "Développement", "summary": "Étapes concrètes"},
                {"heading": "Conclusion", "summary": "Prochaine action"},
            ],
        },
        thumbnail_package={
            "artifact_path": str(thumbnail_path),
            "provider": "thumbnail_composite",
            "status": "generated",
            "source_image_provider": "local_placeholder",
        },
        settings={
            "YOUTUBE_CLIENT_ID": "client-id",
            "YOUTUBE_CLIENT_SECRET": "client-secret",
            "YOUTUBE_REFRESH_TOKEN": "refresh-token",
            "YOUTUBE_PRIVACY_STATUS": "unlisted",
            "YOUTUBE_CATEGORY_ID": "22",
            "YOUTUBE_MADE_FOR_KIDS": "false",
            "YOUTUBE_NOTIFY_SUBSCRIBERS": "false",
            "YOUTUBE_DEFAULT_LANGUAGE": "fr",
            "YOUTUBE_DEFAULT_AUDIO_LANGUAGE": "fr",
            "YOUTUBE_TIMEOUT_SECONDS": "15",
        },
    )

    assert result["status"] == "uploaded"
    assert result["provider"] == "youtube_data_api"
    assert result["upload_enabled"] is True
    assert result["description"].startswith("Description SEO")
    assert result["chapters"][0]["timestamp"] == "0:00"
    assert result["chapters"][1]["timestamp"] == "1:00"
    assert result["chapters"][2]["timestamp"] == "2:00"
    assert result["hashtags"]
    assert result["upload_metadata"]["snippet"]["description"] == result["description"]
    assert result["upload_metadata"]["snippet"]["title"] == "Automatiser une chaîne YouTube : le guide simple en 3 minutes"
    assert result["upload_metadata"]["status"]["privacyStatus"] == "unlisted"
    assert result["thumbnail_provider"] == "thumbnail_composite"
    assert result["thumbnail_status"] == "generated"
    assert result["youtube_video_id"] == "video123"
    assert result["youtube_url"] == "https://www.youtube.com/watch?v=video123"
    assert result["thumbnail_upload_status"] == "uploaded"
    assert result["thumbnail_url"] == "https://img.youtube.com/vi/video123/maxresdefault.jpg"
    assert result["artifact_path"].endswith("youtube_publication.json")
    assert Path(result["artifact_path"]).exists()
    assert len(captured_requests) == 4
    assert captured_requests[0][0] == "https://oauth2.googleapis.com/token"
    assert captured_requests[1][0].startswith("https://www.googleapis.com/upload/youtube/v3/videos")
    assert captured_requests[1][4] == "POST"
    assert captured_requests[2][0] == "https://upload.youtube.test/resumable-session"
    assert captured_requests[2][4] == "PUT"
    assert captured_requests[3][0] == "https://www.googleapis.com/upload/youtube/v3/thumbnails/set?videoId=video123&uploadType=media"
    assert captured_requests[3][4] == "POST"


def test_prepare_publication_package_honors_manual_chapters_and_hashtags(monkeypatch, tmp_path: Path):
    video_path = tmp_path / "rendered_video.mp4"
    video_path.write_bytes(b"FAKE-MP4-BYTES")
    thumbnail_path = tmp_path / "thumbnail.png"
    thumbnail_path.write_bytes(b"FAKE-THUMBNAIL-BYTES")

    captured_requests = []

    def fake_urlopen(request, timeout=0):
        body = request.data.decode("utf-8") if request.data else None
        captured_requests.append((request.full_url, body, dict(request.headers), timeout, request.get_method()))

        if request.full_url == "https://oauth2.googleapis.com/token":
            return _FakeResponse(json.dumps({"access_token": "access-token"}).encode("utf-8"), {"Content-Type": "application/json"})

        if request.full_url.startswith("https://www.googleapis.com/upload/youtube/v3/videos") and request.get_method() == "POST":
            return _FakeResponse(b"", {"Location": "https://upload.youtube.test/resumable-session"})

        if request.full_url == "https://upload.youtube.test/resumable-session" and request.get_method() == "PUT":
            return _FakeResponse(json.dumps({"id": "video456"}).encode("utf-8"), {"Content-Type": "application/json"})

        if request.full_url == "https://www.googleapis.com/upload/youtube/v3/thumbnails/set?videoId=video456&uploadType=media" and request.get_method() == "POST":
            return _FakeResponse(json.dumps({"kind": "youtube#thumbnailSetResponse"}).encode("utf-8"), {"Content-Type": "application/json"})

        raise AssertionError(f"Unexpected request: {request.full_url}")

    monkeypatch.setattr("urllib.request.urlopen", fake_urlopen)

    result = prepare_publication_package(
        subject="Automatiser une chaîne YouTube",
        seo_package={
            "title": "Automatiser une chaîne YouTube : le guide simple en 3 minutes",
            "description": "Description SEO",
            "tags": ["youtube", "automation"],
            "primary_keyword": "youtube",
        },
        artifact_dir=tmp_path / "generated",
        video_path=video_path,
        script_package={
            "duration_minutes": 3,
            "sections": [
                {"heading": "Hook", "summary": "Accroche"},
                {"heading": "Développement", "summary": "Étapes concrètes"},
                {"heading": "Conclusion", "summary": "Prochaine action"},
            ],
        },
        publication_options={
            "chapters": [
                {"timestamp": "0:15", "title": "Intro"},
                {"timestamp": "1:20", "title": "Bloc principal", "summary": "Ce qui compte"},
            ],
            "hashtags": ["Automation", "#YouTube", "Creators"],
            "hashtag_blacklist": ["creators"],
        },
        thumbnail_package={
            "artifact_path": str(thumbnail_path),
            "provider": "thumbnail_composite",
            "status": "generated",
            "source_image_provider": "local_placeholder",
        },
        settings={
            "YOUTUBE_CLIENT_ID": "client-id",
            "YOUTUBE_CLIENT_SECRET": "client-secret",
            "YOUTUBE_REFRESH_TOKEN": "refresh-token",
            "YOUTUBE_PRIVACY_STATUS": "unlisted",
            "YOUTUBE_CATEGORY_ID": "22",
            "YOUTUBE_MADE_FOR_KIDS": "false",
            "YOUTUBE_NOTIFY_SUBSCRIBERS": "false",
            "YOUTUBE_DEFAULT_LANGUAGE": "fr",
            "YOUTUBE_DEFAULT_AUDIO_LANGUAGE": "fr",
            "YOUTUBE_TIMEOUT_SECONDS": "15",
        },
    )

    assert result["status"] == "uploaded"
    assert result["chapter_source"] == "manual"
    assert result["hashtag_source"] == "manual"
    assert result["chapters"][0]["timestamp"] == "0:15"
    assert result["chapters"][0]["title"] == "Intro"
    assert result["chapters"][1]["timestamp"] == "1:20"
    assert result["chapters"][1]["summary"] == "Ce qui compte"
    assert result["hashtags"] == ["#automation", "#youtube"]
    assert "0:15 Intro" in result["description"]
    assert "1:20 Bloc principal" in result["description"]
    assert result["upload_metadata"]["snippet"]["description"] == result["description"]
    assert result["thumbnail_upload_status"] == "uploaded"
    assert len(captured_requests) == 4
