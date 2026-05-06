from __future__ import annotations

import json

from app.services.script_service import generate_script_package


class _FakeResponse:
    def __init__(self, payload: str):
        self._payload = payload

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False

    def read(self):
        return self._payload.encode("utf-8")


def test_generate_script_package_uses_huggingface(monkeypatch):
    generated_payload = {
        "title": "Automatiser YouTube sans se compliquer",
        "hook": "Vous voulez produire plus vite sans perdre la qualité ?",
        "development_points": [
            "Définir un angle clair avant de lancer la production.",
            "Structurer chaque scène autour d'une seule idée forte.",
            "Publier avec un titre et des tags cohérents.",
        ],
        "conclusion": "Passez à l'action avec un premier test simple.",
    }

    response_body = json.dumps(
        [
            {
                "generated_text": json.dumps(generated_payload, ensure_ascii=False),
            }
        ],
        ensure_ascii=False,
    )

    captured_request = {}

    def fake_urlopen(request, timeout=0):
        captured_request["url"] = request.full_url
        captured_request["body"] = json.loads(request.data.decode("utf-8"))
        captured_request["timeout"] = timeout
        return _FakeResponse(response_body)

    monkeypatch.setattr("urllib.request.urlopen", fake_urlopen)

    result = generate_script_package(
        subject="Automatiser une chaîne YouTube",
        idea_package={
            "hook": "Vous voulez automatiser votre chaîne ?",
            "primary_angle": "Automatiser une chaîne YouTube simplement",
            "keywords": ["automatisation", "youtube", "script"],
            "secondary_angles": ["gagner du temps", "standardiser le workflow"],
        },
        audience="creators",
        tone="direct",
        language="fr",
        duration_minutes=3,
        settings={
            "HUGGINGFACE_API_TOKEN": "hf_test_token",
            "HUGGINGFACE_MODEL": "TinyLlama/TinyLlama-1.1B-Chat-v1.0",
            "HUGGINGFACE_TIMEOUT_SECONDS": "12",
            "HUGGINGFACE_MAX_NEW_TOKENS": "256",
            "HUGGINGFACE_TEMPERATURE": "0.5",
        },
    )

    assert captured_request["url"].endswith("TinyLlama/TinyLlama-1.1B-Chat-v1.0")
    assert captured_request["timeout"] == 12
    assert result["source"] == "huggingface"
    assert result["model_name"] == "TinyLlama/TinyLlama-1.1B-Chat-v1.0"
    assert "Automatiser YouTube sans se compliquer" in result["title_candidates"][0]
    assert "Définir un angle clair" in result["full_text"]
    assert result["fallback_reason"] is None
