from __future__ import annotations

import re
import unicodedata
from collections.abc import Mapping, Sequence
from datetime import datetime

from app.utils import coerce_text


CURRENT_YEAR = datetime.now().year
GENERAL_CATEGORY = "Sujet général"

STOPWORDS = {
    "a",
    "an",
    "and",
    "au",
    "aux",
    "avec",
    "dans",
    "de",
    "des",
    "du",
    "en",
    "et",
    "for",
    "from",
    "in",
    "is",
    "la",
    "le",
    "les",
    "of",
    "on",
    "or",
    "pour",
    "sans",
    "sur",
    "the",
    "to",
    "un",
    "une",
    "vers",
}

TREND_PROFILES = [
    {
        "name": "Création YouTube & contenu",
        "keywords": {
            "youtube": 8,
            "chaine": 6,
            "video": 4,
            "contenu": 4,
            "miniature": 9,
            "thumbnail": 9,
            "seo": 7,
            "tags": 5,
            "shorts": 6,
            "montage": 5,
            "publication": 5,
            "vues": 5,
            "engagement": 5,
            "abonnes": 5,
            "audience": 4,
        },
        "phrases": {
            "plus de vues": 7,
            "plus d abonnes": 6,
            "optimiser sa chaine": 7,
            "meilleure miniature": 8,
            "gagner des vues": 7,
        },
        "recommended_format": "optimisation de contenu",
        "hook_style": "demonstration",
        "summary": "La demande reste forte sur tout ce qui améliore la performance d'une chaîne YouTube.",
        "secondary_angles": [
            "Optimiser {subject} pour gagner plus de vues",
            "Les réglages qui améliorent {subject}",
            "Transformer {subject} en workflow efficace pour {audience}",
        ],
        "signals": ["creator economy", "croissance YouTube", "optimisation"],
        "topic_bonus": 6,
        "timeliness_bonus": 10,
        "evergreen_bonus": 8,
        "virality_bonus": 4,
    },
    {
        "name": "IA & automatisation",
        "keywords": {
            "ia": 8,
            "chatgpt": 8,
            "automatisation": 10,
            "automatiser": 10,
            "workflow": 7,
            "agent": 7,
            "agents": 7,
            "prompt": 6,
            "nocode": 6,
            "n8n": 6,
            "make": 6,
            "zapier": 6,
            "assistant": 5,
            "copilot": 5,
        },
        "phrases": {
            "gain de temps": 7,
            "sans code": 6,
            "sans complexite": 6,
            "faire plus vite": 6,
        },
        "recommended_format": "tutoriel démonstratif",
        "hook_style": "curiosity_gap",
        "summary": "L'IA et l'automatisation restent très porteurs quand la promesse est concrète et directement utile.",
        "secondary_angles": [
            "Mettre en place {subject} en 3 étapes",
            "Les erreurs à éviter sur {subject}",
            "Un workflow simple pour {subject} avec un résultat visible",
        ],
        "signals": ["productivité", "gain de temps", "workflow"],
        "topic_bonus": 7,
        "timeliness_bonus": 12,
        "evergreen_bonus": 9,
        "virality_bonus": 5,
    },
    {
        "name": "Productivité & outils",
        "keywords": {
            "notion": 8,
            "excel": 8,
            "calendar": 5,
            "calendrier": 5,
            "organisation": 6,
            "organisation": 6,
            "productivite": 7,
            "productivity": 7,
            "workflow": 6,
            "template": 5,
            "systeme": 6,
            "outils": 5,
            "dashboard": 5,
        },
        "phrases": {
            "gain de temps": 6,
            "plus efficace": 6,
            "sans perdre de temps": 6,
        },
        "recommended_format": "méthode pratique",
        "hook_style": "problem_solution",
        "summary": "Les méthodes d'organisation et les outils concrets gardent un excellent potentiel evergreen.",
        "secondary_angles": [
            "Simplifier {subject} avec une méthode réutilisable",
            "Les étapes qui font vraiment gagner du temps avec {subject}",
            "Un setup minimal pour {subject} et un résultat rapide",
        ],
        "signals": ["efficacité", "organisation", "outils"],
        "topic_bonus": 6,
        "timeliness_bonus": 8,
        "evergreen_bonus": 10,
        "virality_bonus": 3,
    },
    {
        "name": "Business & marketing",
        "keywords": {
            "marketing": 8,
            "business": 8,
            "vente": 7,
            "conversion": 7,
            "monetisation": 8,
            "monetization": 8,
            "revenu": 7,
            "revenus": 7,
            "entrepreneur": 6,
            "entreprise": 6,
            "freelance": 6,
            "client": 5,
            "strategie": 6,
            "stratégie": 6,
        },
        "phrases": {
            "gagner de l argent": 7,
            "plus de clients": 7,
            "booster ses revenus": 7,
        },
        "recommended_format": "cas pratique",
        "hook_style": "curiosity_gap",
        "summary": "Les contenus orientés résultats et acquisition attirent une audience qualifiée.",
        "secondary_angles": [
            "Comment {subject} peut améliorer le retour sur effort",
            "Les leviers clés pour {subject}",
            "Un plan simple pour appliquer {subject} sans complexité",
        ],
        "signals": ["acquisition", "revenus", "conversion"],
        "topic_bonus": 6,
        "timeliness_bonus": 8,
        "evergreen_bonus": 8,
        "virality_bonus": 4,
    },
    {
        "name": "Tutoriel éducatif",
        "keywords": {
            "guide": 7,
            "tuto": 7,
            "tutoriel": 7,
            "apprendre": 7,
            "expliquer": 6,
            "explication": 6,
            "debutant": 7,
            "debutants": 7,
            "simple": 5,
            "methode": 6,
            "methode": 6,
            "etape": 5,
            "etapes": 5,
        },
        "phrases": {
            "pas a pas": 8,
            "pas à pas": 8,
            "comment faire": 8,
            "debuter": 6,
        },
        "recommended_format": "tutoriel pas à pas",
        "hook_style": "problem_solution",
        "summary": "Les formats pédagogiques génèrent souvent une bonne recherche organique.",
        "secondary_angles": [
            "La méthode étape par étape pour {subject}",
            "Les erreurs à éviter pendant {subject}",
            "Une version simple et claire de {subject} pour {audience}",
        ],
        "signals": ["apprentissage", "résolution", "simplicité"],
        "topic_bonus": 5,
        "timeliness_bonus": 7,
        "evergreen_bonus": 11,
        "virality_bonus": 3,
    },
    {
        "name": "Comparatif & décision",
        "keywords": {
            "vs": 8,
            "meilleur": 8,
            "meilleurs": 8,
            "top": 7,
            "comparatif": 8,
            "alternatives": 7,
            "avis": 5,
            "test": 5,
            "choisir": 7,
            "choix": 7,
            "outil": 4,
            "outils": 4,
        },
        "phrases": {
            "quel est le meilleur": 8,
            "quelle option": 6,
            "comment choisir": 7,
        },
        "recommended_format": "comparatif décisionnel",
        "hook_style": "comparison",
        "summary": "Les comparatifs captent une intention de décision forte et génèrent souvent un bon taux de clic.",
        "secondary_angles": [
            "Quel choix retenir pour {subject} ?",
            "Les critères qui comptent vraiment pour {subject}",
            "L'approche la plus simple pour comparer {subject}",
        ],
        "signals": ["décision", "comparaison", "choix"],
        "topic_bonus": 5,
        "timeliness_bonus": 7,
        "evergreen_bonus": 7,
        "virality_bonus": 6,
    },
    {
        "name": "Résolution de problème",
        "keywords": {
            "erreur": 8,
            "erreurs": 8,
            "eviter": 7,
            "éviter": 7,
            "corriger": 7,
            "solution": 7,
            "probleme": 6,
            "problème": 6,
            "bug": 6,
            "optimiser": 7,
            "ameliorer": 7,
            "améliorer": 7,
            "bloque": 5,
            "bloquer": 5,
        },
        "phrases": {
            "sans bug": 6,
            "sans erreur": 6,
            "corriger rapidement": 7,
        },
        "recommended_format": "résolution de problème",
        "hook_style": "problem_solution",
        "summary": "Les vidéos qui résolvent un problème précis performent bien en recherche.",
        "secondary_angles": [
            "Les erreurs à éviter avec {subject}",
            "La solution la plus simple pour {subject}",
            "Comment corriger {subject} rapidement",
        ],
        "signals": ["diagnostic", "correction", "amélioration"],
        "topic_bonus": 6,
        "timeliness_bonus": 7,
        "evergreen_bonus": 10,
        "virality_bonus": 4,
    },
]

INTENT_CUES = [
    {
        "name": "tutorial",
        "keywords": {
            "comment": 8,
            "guide": 7,
            "tuto": 7,
            "tutoriel": 7,
            "apprendre": 7,
            "debutant": 6,
            "debutants": 6,
            "pas": 4,
            "etape": 4,
            "etapes": 4,
        },
        "phrases": {
            "pas a pas": 8,
            "pas à pas": 8,
            "comment faire": 8,
            "debuter": 6,
        },
        "recommended_format": "tutoriel pas à pas",
        "hook_style": "problem_solution",
        "summary": "Forte intention de recherche avec une promesse claire et actionnable.",
        "signals": ["intention de recherche", "format pédagogique"],
        "evergreen_bonus": 6,
        "virality_bonus": 2,
    },
    {
        "name": "comparison",
        "keywords": {
            "vs": 8,
            "meilleur": 8,
            "meilleurs": 8,
            "top": 7,
            "comparatif": 8,
            "alternatives": 7,
            "avis": 5,
            "test": 5,
            "choisir": 7,
            "choix": 7,
        },
        "phrases": {
            "quel est le meilleur": 8,
            "quelle option": 6,
            "comment choisir": 7,
        },
        "recommended_format": "comparatif décisionnel",
        "hook_style": "comparison",
        "summary": "Angle de décision efficace pour capter des clics et aider au choix.",
        "signals": ["comparaison", "décision"],
        "evergreen_bonus": 4,
        "virality_bonus": 6,
    },
    {
        "name": "problem_solution",
        "keywords": {
            "erreur": 8,
            "erreurs": 8,
            "eviter": 7,
            "éviter": 7,
            "corriger": 7,
            "solution": 7,
            "probleme": 6,
            "problème": 6,
            "bug": 6,
            "optimiser": 7,
            "ameliorer": 7,
            "améliorer": 7,
        },
        "phrases": {
            "sans bug": 6,
            "sans erreur": 6,
            "corriger rapidement": 7,
        },
        "recommended_format": "résolution de problème",
        "hook_style": "problem_solution",
        "summary": "Le sujet répond à un besoin concret et peut générer une bonne recherche organique.",
        "signals": ["solution", "amélioration"],
        "evergreen_bonus": 5,
        "virality_bonus": 3,
    },
    {
        "name": "curiosity",
        "keywords": {
            "secret": 6,
            "hack": 6,
            "astuce": 6,
            "astuces": 6,
            "rapide": 4,
            "facile": 4,
            "nouveau": 5,
            "nouvelle": 5,
            "viral": 6,
            "vital": 0,
        },
        "phrases": {
            "gain de temps": 6,
            "sans effort": 5,
            "le vrai": 4,
        },
        "recommended_format": "angle accrocheur",
        "hook_style": "curiosity_gap",
        "summary": "Le titre peut jouer sur la curiosité et la promesse d'un résultat rapide.",
        "signals": ["curiosité", "accroche"],
        "evergreen_bonus": 2,
        "virality_bonus": 6,
    },
]


def _normalize_text(value: object) -> str:
    text = coerce_text(value, "")
    if not text:
        return ""
    normalized = unicodedata.normalize("NFKD", text)
    ascii_text = normalized.encode("ascii", "ignore").decode("ascii")
    return re.sub(r"\s+", " ", ascii_text.lower()).strip()


def _tokenize(value: object) -> list[str]:
    normalized = _normalize_text(value)
    if not normalized:
        return []

    tokens: list[str] = []
    for raw_token in re.split(r"[^a-z0-9]+", normalized):
        if len(raw_token) < 3 or raw_token in STOPWORDS:
            continue
        if raw_token not in tokens:
            tokens.append(raw_token)
    return tokens


def _unique(items: Sequence[str]) -> list[str]:
    seen: set[str] = set()
    ordered: list[str] = []
    for item in items:
        normalized = coerce_text(item, "")
        if not normalized:
            continue
        lowered = normalized.lower()
        if lowered in seen:
            continue
        seen.add(lowered)
        ordered.append(normalized)
    return ordered


def _score_mapping(
    normalized_subject: str,
    tokens: Sequence[str],
    mapping: Mapping[str, int],
    phrases: Mapping[str, int],
    base_bonus: int,
    ceiling: int,
) -> dict:
    keyword_hits = [token for token in tokens if token in mapping]
    phrase_hits = [phrase for phrase in phrases if phrase in normalized_subject]

    if not keyword_hits and not phrase_hits:
        return {
            "score": 0,
            "keyword_hits": [],
            "phrase_hits": [],
        }

    total = base_bonus
    total += sum(mapping[token] for token in keyword_hits)
    total += sum(phrases[phrase] for phrase in phrase_hits)
    total += len(keyword_hits) * 2
    total += len(phrase_hits) * 2

    return {
        "score": min(ceiling, total),
        "keyword_hits": keyword_hits,
        "phrase_hits": phrase_hits,
    }


def _score_profiles(normalized_subject: str, tokens: Sequence[str]) -> list[dict]:
    profiles: list[dict] = []
    for profile in TREND_PROFILES:
        scored = _score_mapping(
            normalized_subject,
            tokens,
            profile["keywords"],
            profile["phrases"],
            profile["topic_bonus"],
            20,
        )
        if scored["score"] == 0:
            continue

        profiles.append(
            {
                "name": profile["name"],
                "score": scored["score"],
                "keyword_hits": scored["keyword_hits"],
                "phrase_hits": scored["phrase_hits"],
                "recommended_format": profile["recommended_format"],
                "hook_style": profile["hook_style"],
                "summary": profile["summary"],
                "secondary_angles": profile["secondary_angles"],
                "signals": profile["signals"],
                "timeliness_bonus": profile["timeliness_bonus"],
                "evergreen_bonus": profile["evergreen_bonus"],
                "virality_bonus": profile["virality_bonus"],
            }
        )

    profiles.sort(key=lambda item: item["score"], reverse=True)
    return profiles


def _score_intents(normalized_subject: str, tokens: Sequence[str]) -> list[dict]:
    intents: list[dict] = []
    for intent in INTENT_CUES:
        scored = _score_mapping(
            normalized_subject,
            tokens,
            intent["keywords"],
            intent["phrases"],
            4,
            20,
        )
        if scored["score"] == 0:
            continue

        intents.append(
            {
                "name": intent["name"],
                "score": scored["score"],
                "keyword_hits": scored["keyword_hits"],
                "phrase_hits": scored["phrase_hits"],
                "recommended_format": intent["recommended_format"],
                "hook_style": intent["hook_style"],
                "summary": intent["summary"],
                "signals": intent["signals"],
                "evergreen_bonus": intent["evergreen_bonus"],
                "virality_bonus": intent["virality_bonus"],
            }
        )

    intents.sort(key=lambda item: item["score"], reverse=True)
    return intents


def _score_timeliness(normalized_subject: str, tokens: Sequence[str], profile: dict | None) -> int:
    hot_signals = {
        "ia": 4,
        "chatgpt": 4,
        "automatisation": 4,
        "automatiser": 4,
        "youtube": 4,
        "shorts": 3,
        "prompt": 3,
        "agents": 4,
        "agent": 4,
        "seo": 3,
        "miniature": 3,
        "thumbnail": 3,
        "n8n": 4,
        "make": 4,
        "zapier": 4,
    }
    year_boost = 0
    for year in {str(CURRENT_YEAR), str(CURRENT_YEAR + 1)}:
        if year in normalized_subject:
            year_boost = 4
            break

    token_boost = sum(hot_signals[token] for token in tokens if token in hot_signals)
    profile_bonus = profile["timeliness_bonus"] if profile is not None else 4
    return min(20, profile_bonus + token_boost + year_boost)


def _score_evergreen(tokens: Sequence[str], profile: dict | None, intent: dict | None) -> int:
    score = 4
    if profile is not None:
        score += profile["evergreen_bonus"]
    if intent is not None:
        score += intent["evergreen_bonus"]
    if any(token in {"guide", "tuto", "tutoriel", "methode", "methode", "comment"} for token in tokens):
        score += 2
    if len(tokens) >= 3:
        score += 2
    return min(20, score)


def _score_virality(tokens: Sequence[str], profile: dict | None, intent: dict | None) -> int:
    score = 0
    if profile is not None:
        score += profile["virality_bonus"]
    if intent is not None:
        score += intent["virality_bonus"]
    if any(token in {"erreur", "erreurs", "eviter", "éviter", "secret", "hack", "astuce", "astuces", "top", "meilleur", "meilleurs", "vs", "comparatif"} for token in tokens):
        score += 3
    return min(10, score)


def _score_audience(audience: str, tokens: Sequence[str]) -> int:
    normalized_audience = _normalize_text(audience)
    score = 0
    if normalized_audience and normalized_audience not in {"general", "général"}:
        score += 4

    if any(marker in normalized_audience for marker in {"creator", "createur", "creators"}):
        score += 3
    if any(marker in normalized_audience for marker in {"market", "marketing", "marketer"}):
        score += 3
    if any(marker in normalized_audience for marker in {"entrepreneur", "business", "freelance"}):
        score += 3
    if any(token in tokens for token in {"youtube", "video", "contenu", "miniature", "shorts", "seo"}):
        score += 2

    return min(10, score)


def _score_competition_risk(tokens: Sequence[str], profile: dict | None, intent: dict | None) -> int:
    risk = 0
    if len(tokens) <= 1:
        risk += 8
    elif len(tokens) == 2:
        risk += 5
    else:
        risk += 2

    if profile is None:
        risk += 4
    elif profile["name"] in {"Création YouTube & contenu", "Business & marketing"}:
        risk += 2

    if intent is None:
        risk += 2
    if profile is not None and profile["score"] < 12:
        risk += 2

    return min(14, risk)


def _score_stage(trend_score: int) -> str:
    if trend_score >= 82:
        return "rising"
    if trend_score >= 68:
        return "strong"
    if trend_score >= 52:
        return "stable"
    return "niche"


def _build_summary(category: str, recommended_format: str, intent_summary: str, profile_summary: str, stage: str) -> str:
    fragments = [
        f"Sujet {stage} sur {category}.",
        f"Format conseillé : {recommended_format}.",
    ]
    if intent_summary:
        fragments.append(intent_summary)
    if profile_summary:
        fragments.append(profile_summary)
    return " ".join(fragments)


def _build_opportunities(audience: str, profile: dict | None, intent: dict | None, stage: str) -> list[str]:
    opportunities = []
    if profile is not None:
        opportunities.append(f"Capitaliser sur {profile['name'].lower()}.")
    if intent is not None:
        opportunities.append(f"Adopter un format {intent['recommended_format']}.")
    if audience and _normalize_text(audience) not in {"general", "général"}:
        opportunities.append(f"Cibler l'audience {audience} avec un bénéfice concret.")
    if stage in {"rising", "strong"}:
        opportunities.append("Miser sur une promesse claire et un résultat visible rapidement.")
    return opportunities[:4]


def _build_risks(profile: dict | None, intent: dict | None, competition_risk: int, tokens: Sequence[str]) -> list[str]:
    risks = []
    if competition_risk >= 8:
        risks.append("Sujet assez large: préciser l'outil, le cas d'usage ou la promesse.")
    if profile is None:
        risks.append("Les signaux de tendance sont faibles, il faut cadrer l'angle.")
    if intent is None:
        risks.append("Le format n'est pas encore orienté vers une intention de recherche forte.")
    if not tokens:
        risks.append("Le sujet manque de mots-clés exploitables.")
    return risks[:3]


def analyze_trend_profile(
    subject: str,
    audience: str,
    tone: str,
    language: str,
    keywords: Sequence[str] | None = None,
) -> dict:
    subject = coerce_text(subject, "Sujet sans titre")
    audience = coerce_text(audience, "general")
    tone = coerce_text(tone, "engaging")
    language = coerce_text(language, "fr")

    normalized_subject = _normalize_text(subject)
    base_tokens = _tokenize(subject)
    keyword_tokens = [token for token in (_normalize_text(keyword) for keyword in (keywords or [])) if token]
    tokens = _unique(base_tokens + keyword_tokens)

    profiles = _score_profiles(normalized_subject, tokens)
    intents = _score_intents(normalized_subject, tokens)

    top_profile = profiles[0] if profiles else None
    top_intent = intents[0] if intents else None

    category = top_profile["name"] if top_profile is not None else GENERAL_CATEGORY
    recommended_format = (
        top_intent["recommended_format"]
        if top_intent is not None
        else (top_profile["recommended_format"] if top_profile is not None else "format court et concret")
    )
    hook_style = top_intent["hook_style"] if top_intent is not None else (top_profile["hook_style"] if top_profile is not None else "curiosity_gap")

    topic_profile_score = top_profile["score"] if top_profile is not None else 0
    search_intent_score = top_intent["score"] if top_intent is not None else 4
    timeliness_score = _score_timeliness(normalized_subject, tokens, top_profile)
    evergreen_score = _score_evergreen(tokens, top_profile, top_intent)
    virality_score = _score_virality(tokens, top_profile, top_intent)
    audience_fit_score = _score_audience(audience, tokens)
    competition_risk = _score_competition_risk(tokens, top_profile, top_intent)
    specificity_bonus = min(6, max(0, len(tokens) - 1) * 2)

    trend_score = max(
        0,
        min(
            100,
            24
            + topic_profile_score
            + search_intent_score
            + timeliness_score
            + evergreen_score
            + virality_score
            + audience_fit_score
            + specificity_bonus
            - competition_risk,
        ),
    )
    trend_stage = _score_stage(trend_score)

    related_topics = [profile["name"] for profile in profiles[1:3] if profile["name"] != category]
    if not related_topics and top_profile is not None:
        related_topics = [signal for signal in top_profile["signals"][:2] if signal != category]

    matched_keywords = _unique(
        (top_profile["keyword_hits"] if top_profile is not None else [])
        + (top_intent["keyword_hits"] if top_intent is not None else [])
    )
    matched_phrases = _unique(
        (top_profile["phrase_hits"] if top_profile is not None else [])
        + (top_intent["phrase_hits"] if top_intent is not None else [])
    )

    signals: list[str] = []
    if top_profile is not None:
        signals.extend(top_profile["signals"])
    if top_intent is not None:
        signals.extend(top_intent["signals"])
    if audience_fit_score > 0:
        signals.append(f"audience: {audience}")
    if matched_keywords:
        signals.append(f"mots-clés: {', '.join(matched_keywords[:4])}")

    summary = _build_summary(
        category=category,
        recommended_format=recommended_format,
        intent_summary=top_intent["summary"] if top_intent is not None else "",
        profile_summary=top_profile["summary"] if top_profile is not None else "",
        stage=trend_stage,
    )

    opportunities = _build_opportunities(audience, top_profile, top_intent, trend_stage)
    risks = _build_risks(top_profile, top_intent, competition_risk, tokens)

    return {
        "category": category,
        "related_topics": related_topics,
        "trend_stage": trend_stage,
        "trend_score": trend_score,
        "recommended_format": recommended_format,
        "hook_style": hook_style,
        "summary": summary,
        "signals": _unique(signals),
        "matched_keywords": matched_keywords,
        "matched_phrases": matched_phrases,
        "opportunities": opportunities,
        "risks": risks,
        "score_breakdown": {
            "topic_profile": topic_profile_score,
            "search_intent": search_intent_score,
            "timeliness": timeliness_score,
            "evergreen": evergreen_score,
            "virality": virality_score,
            "audience_fit": audience_fit_score,
            "competition_risk": competition_risk,
            "specificity_bonus": specificity_bonus,
        },
        "tone": tone,
        "language": language,
    }
