from __future__ import annotations

from app.services.idea_service import generate_idea_package


def test_generate_idea_package_builds_realistic_trend_analysis():
    result = generate_idea_package(
        subject="Automatiser une chaîne YouTube",
        audience="creators",
        tone="direct",
        language="fr",
    )

    assert result["trend_score"] >= 70
    assert result["trend_category"] == "Création YouTube & contenu"
    assert result["trend_stage"] in {"rising", "strong"}
    assert result["trend_analysis"]["recommended_format"] == "optimisation de contenu"
    assert result["trend_analysis"]["summary"]
    assert result["hook"]
    assert len(result["secondary_angles"]) == 3


def test_generate_idea_package_penalizes_generic_topics():
    result = generate_idea_package(
        subject="Cuisine",
        audience="general",
        tone="warm",
        language="fr",
    )

    assert result["trend_score"] < 60
    assert result["trend_category"] == "Sujet général"
    assert result["trend_stage"] in {"stable", "niche"}