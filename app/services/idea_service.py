from __future__ import annotations

from app.utils import coerce_text
from app.services.trend_service import analyze_trend_profile


def _extract_keywords(subject: str) -> list[str]:
    words = [word.strip(" ,.!?:;()[]{}") for word in subject.lower().split()]
    keywords: list[str] = []

    for word in words:
        if len(word) < 4:
            continue
        normalized = word.replace("'", "")
        if normalized not in keywords:
            keywords.append(normalized)

    if not keywords:
        keywords.append(subject.lower())

    return keywords[:6]


def _build_primary_angle(subject: str, audience: str, trend_analysis: dict) -> str:
    category = trend_analysis.get("category", "")
    trend_stage = trend_analysis.get("trend_stage", "")

    if category == "Comparatif & décision":
        return f"{subject} : le comparatif clair pour {audience}"
    if category == "Résolution de problème":
        return f"{subject} : la méthode simple pour {audience}"
    if category == "IA & automatisation":
        return f"{subject} expliqué pas à pas pour {audience}"
    if category == "Création YouTube & contenu":
        return f"{subject} : optimiser ses résultats sur YouTube pour {audience}"
    if trend_stage in {"rising", "strong"}:
        return f"{subject} : l'angle le plus porteur pour {audience}"
    return f"{subject} expliqué simplement pour {audience}"


def _build_hook(subject: str, trend_analysis: dict) -> str:
    hook_style = trend_analysis.get("hook_style", "curiosity_gap")

    if hook_style == "comparison":
        return f"Quel est le meilleur choix pour {subject} ?"
    if hook_style == "problem_solution":
        return f"Vous cherchez une façon simple de {subject.lower()} ?"
    if hook_style == "demonstration":
        return f"Voici comment {subject} sans perdre de temps."
    return f"Il existe un levier simple pour {subject}, et il change tout."


def _build_secondary_angles(subject: str, audience: str, trend_analysis: dict) -> list[str]:
    category = trend_analysis.get("category", "")
    recommended_format = trend_analysis.get("recommended_format", "")

    if category == "Comparatif & décision":
        candidates = [
            f"Quel choix retenir pour {subject} ?",
            f"Les critères qui comptent vraiment pour {subject}",
            f"L'approche la plus simple pour comparer {subject}",
        ]
    elif category == "IA & automatisation":
        candidates = [
            f"Mettre en place {subject} en 3 étapes",
            f"Les erreurs à éviter sur {subject}",
            f"Un workflow simple pour {subject} avec un résultat visible",
        ]
    elif category == "Création YouTube & contenu":
        candidates = [
            f"Optimiser {subject} pour gagner plus de vues",
            f"Les réglages qui améliorent {subject}",
            f"Transformer {subject} en workflow efficace pour {audience}",
        ]
    elif category == "Résolution de problème":
        candidates = [
            f"Les erreurs à éviter avec {subject}",
            f"La solution la plus simple pour {subject}",
            f"Comment corriger {subject} rapidement",
        ]
    else:
        candidates = [
            f"{subject} en mode pratique",
            f"Les erreurs à éviter avec {subject}",
            f"Comment obtenir des résultats rapides avec {subject}",
        ]

    if recommended_format:
        candidates.append(f"Adapter {subject} au format {recommended_format}")

    if audience and audience != "general":
        candidates.append(f"Version orientée {audience} de {subject}")

    unique_candidates = []
    seen: set[str] = set()
    for candidate in candidates:
        normalized = candidate.strip().lower()
        if not normalized or normalized in seen:
            continue
        seen.add(normalized)
        unique_candidates.append(candidate)

    return unique_candidates[:3]


def generate_idea_package(subject: str, audience: str, tone: str, language: str) -> dict:
    subject = coerce_text(subject, "Sujet sans titre")
    audience = coerce_text(audience, "general")
    tone = coerce_text(tone, "engaging")
    language = coerce_text(language, "fr")
    keywords = _extract_keywords(subject)
    trend_analysis = analyze_trend_profile(subject, audience, tone, language, keywords)

    return {
        "subject": subject,
        "audience": audience,
        "tone": tone,
        "language": language,
        "trend_score": trend_analysis["trend_score"],
        "trend_category": trend_analysis["category"],
        "trend_stage": trend_analysis["trend_stage"],
        "trend_analysis": trend_analysis,
        "primary_angle": _build_primary_angle(subject, audience, trend_analysis),
        "secondary_angles": _build_secondary_angles(subject, audience, trend_analysis),
        "keywords": keywords,
        "hook": _build_hook(subject, trend_analysis),
        "content_brief": f"Angle {tone} conçu pour {audience}. {trend_analysis['summary']}",
    }
