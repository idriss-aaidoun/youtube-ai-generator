from __future__ import annotations

import json
from io import BytesIO
from pathlib import Path

from PIL import Image

from app.services.visual_service import generate_visual_package


class _FakeResponse:
    def __init__(self, payload: bytes, content_type: str):
        self._payload = payload
        self.headers = {"Content-Type": content_type}

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False

    def read(self):
        return self._payload


def _make_png_bytes(color: tuple[int, int, int]) -> bytes:
    buffer = BytesIO()
    Image.new("RGB", (64, 64), color).save(buffer, format="PNG")
    return buffer.getvalue()


def test_generate_visual_package_uses_huggingface_images(monkeypatch, tmp_path: Path):
    captured_requests = []
    png_bytes = _make_png_bytes((255, 183, 3))

    def fake_urlopen(request, timeout=0):
        captured_requests.append((request.full_url, json.loads(request.data.decode("utf-8")), timeout))
        return _FakeResponse(png_bytes, "image/png")

    monkeypatch.setattr("urllib.request.urlopen", fake_urlopen)

    result = generate_visual_package(
        subject="Automatiser une chaîne YouTube",
        idea_package={"keywords": ["automatisation", "youtube"], "primary_angle": "Angle"},
        script_package={
            "sections": [
                {"heading": "Hook", "summary": "Accroche rapide", "body": "Accroche rapide"},
                {"heading": "Développement", "summary": "Méthode claire", "body": "Méthode claire"},
            ]
        },
        artifact_dir=tmp_path / "generated",
        settings={
            "HUGGINGFACE_API_TOKEN": "hf_test_token",
            "HUGGINGFACE_IMAGE_MODEL": "stabilityai/stable-diffusion-xl-base-1.0",
            "HUGGINGFACE_IMAGE_TIMEOUT_SECONDS": "10",
        },
    )

    assert result["status"] == "generated"
    assert result["provider"] == "huggingface_image_api"
    assert result["image_model"] == "stabilityai/stable-diffusion-xl-base-1.0"
    assert len(result["image_assets"]) == 2
    assert Path(result["image_assets"][0]["image_path"]).exists()
    assert Path(result["storyboard_path"]).exists()
    assert len(captured_requests) == 2
    assert "Professional YouTube thumbnail-style cinematic illustration" in captured_requests[0][1]["inputs"]
    assert "Negative prompt" in captured_requests[0][1]["inputs"]
