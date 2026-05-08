from __future__ import annotations

import json
from pathlib import Path

from app.services.audio_service import generate_audio_package


class _FakeHeaders:
    def __init__(self, content_type: str):
        self._content_type = content_type

    def get(self, key, default=None):
        if str(key).lower() == "content-type":
            return self._content_type
        return default

    def get_content_type(self):
        return self._content_type


class _FakeResponse:
    def __init__(self, payload: bytes, content_type: str):
        self._payload = payload
        self.headers = _FakeHeaders(content_type)

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False

    def read(self):
        return self._payload


def test_generate_audio_package_uses_elevenlabs(monkeypatch, tmp_path: Path):
    voices_payload = {
        "voices": [
            {"voice_id": "voice-f", "name": "Alice", "labels": {"gender": "female"}},
            {"voice_id": "voice-m", "name": "Bob", "labels": {"gender": "male"}},
        ]
    }
    captured_requests = []

    def fake_urlopen(request, timeout=0):
        captured_requests.append(
            (
                request.full_url,
                json.loads(request.data.decode("utf-8")) if request.data else None,
                timeout,
            )
        )
        if request.full_url.endswith("/v1/voices"):
            return _FakeResponse(json.dumps(voices_payload).encode("utf-8"), "application/json")
        if "/v1/text-to-speech/voice-f" in request.full_url:
            return _FakeResponse(b"FAKE-MP3-BYTES", "audio/mpeg")
        raise AssertionError(f"Unexpected request: {request.full_url}")

    monkeypatch.setattr("urllib.request.urlopen", fake_urlopen)

    result = generate_audio_package(
        subject="Automatiser une chaîne YouTube",
        script_package={"full_text": "Bonjour, voici le script de test."},
        voice="female",
        language="fr",
        artifact_dir=tmp_path / "generated",
        settings={
            "ELEVENLABS_API_KEY": "test-key",
            "ELEVENLABS_MODEL_ID": "eleven_multilingual_v2",
            "ELEVENLABS_TIMEOUT_SECONDS": "10",
        },
    )

    assert result["status"] == "generated"
    assert result["provider"] == "elevenlabs"
    assert result["voice_id"] == "voice-f"
    assert result["artifact_path"].endswith("voiceover.mp3")
    assert Path(result["artifact_path"]).read_bytes() == b"FAKE-MP3-BYTES"
    assert Path(result["manifest_path"]).exists()
    assert len(captured_requests) == 2
    assert captured_requests[0][0].endswith("/v1/voices")
    assert captured_requests[1][0].startswith("https://api.elevenlabs.io/v1/text-to-speech/voice-f")
