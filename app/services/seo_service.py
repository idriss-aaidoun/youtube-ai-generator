from __future__ import annotations

from app.utils import coerce_text


def _dedupe(items: list[str]) -> list[str]:
    seen: set[str] = set()
    ordered: list[str] = []
    for item in items:
        normalized = item.strip().lower()
        if not normalized or normalized in seen:
            continue
        seen.add(normalized)
        ordered.append(item.strip())
    return ordered


def _truncate(text: str, limit: int) -> str:
    if len(text) <= limit:
        return text
    return text[: limit - 3].rstrip() + "..."


def generate_seo_package(subject: str, idea_package: dict, script_package: dict) -> dict:
    subject = coerce_text(subject, "Sujet sans titre")
    keywords = idea_package.get("keywords", [])
    primary_keyword = keywords[0] if keywords else subject.lower()

    title = _truncate(script_package["title_candidates"][0], 95)
    tags = _dedupe(
        [
            primary_keyword,
            subject,
            idea_package.get("audience", "general"),
            "automatisation youtube",
            "ia",
            "video marketing",
            *keywords[:4],
        ]
    )

    description = "\n".join(
        [
            f"Découvrez {subject} avec une approche claire et actionnable.",
            f"Angle principal : {idea_package['primary_angle']}.",
            "Structure : hook, développement, conclusion.",
            "Avant publication, adaptez le ton et vérifiez les droits des ressources utilisées.",
        ]
    )

    return {
        "title": title,
        "description": description,
        "tags": tags,
        "score": min(100, 70 + len(tags) * 2),
        "estimated_ctr": round(4.5 + min(3.0, len(tags) * 0.18), 1),
        "primary_keyword": primary_keyword,
    }
