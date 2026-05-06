from __future__ import annotations

import json
import os
import re
import urllib.error
import urllib.request
from collections.abc import Mapping, Sequence

from app.utils import clamp_int, coerce_text


DEFAULT_HUGGINGFACE_MODEL = "TinyLlama/TinyLlama-1.1B-Chat-v1.0"
DEFAULT_TIMEOUT_SECONDS = 60
DEFAULT_MAX_NEW_TOKENS = 700
DEFAULT_TEMPERATURE = 0.7


def _settings_value(settings: Mapping[str, object] | None, *names: str) -> str:
    if settings is not None:
        for name in names:
            value = settings.get(name)
            if value is None:
                continue
            text = str(value).strip()
            if text:
                return text

    for name in names:
        value = os.getenv(name)
        if value is None:
            continue
        text = value.strip()
        if text:
            return text

    return ""


def _settings_int(
    settings: Mapping[str, object] | None,
    name: str,
    default: int,
    minimum: int,
    maximum: int,
) -> int:
    return clamp_int(_settings_value(settings, name), default, minimum=minimum, maximum=maximum)


def _settings_float(
    settings: Mapping[str, object] | None,
    name: str,
    default: float,
    minimum: float,
    maximum: float,
) -> float:
    raw_value = _settings_value(settings, name)
    if not raw_value:
        return default

    try:
        number = float(raw_value)
    except ValueError:
        return default

    return max(minimum, min(maximum, number))


def _language_label(language: str) -> str:
    mapping = {
        "fr": "français",
        "en": "anglais",
        "es": "espagnol",
        "de": "allemand",
        "it": "italien",
    }
    return mapping.get(language.lower(), language)


def _unique(items: Sequence[str]) -> list[str]:
    seen: set[str] = set()
    ordered: list[str] = []

    for item in items:
        text = coerce_text(item, "")
        if not text:
            continue
        lowered = text.lower()
        if lowered in seen:
            continue
        seen.add(lowered)
        ordered.append(text)

    return ordered


def _default_development_points(subject: str, audience: str, keywords: Sequence[str]) -> list[str]:
    points = [
        f"Comprendre les bases de {subject}.",
        f"Appliquer une méthode claire adaptée à {audience}.",
        "Éviter les erreurs fréquentes et garder une exécution simple.",
    ]

    if keywords:
        points.insert(1, f"Relier {keywords[0]} à un cas concret.")

    return points


def _compose_full_text(hook: str, development_points: Sequence[str], conclusion: str) -> str:
    development_block = "\n".join(f"{index}. {point}" for index, point in enumerate(development_points, start=1))
    return "\n\n".join(
        [
            f"INTRODUCTION\n{hook}",
            f"DÉVELOPPEMENT\n{development_block}",
            f"CONCLUSION\n{conclusion}",
        ]
    )


def _build_script_package(
    *,
    subject: str,
    audience: str,
    tone: str,
    language: str,
    duration_minutes: int,
    target_word_count: int,
    title: str,
    hook: str,
    development_points: Sequence[str] | str | None,
    conclusion: str,
    source: str,
    provider: str,
    model_name: str | None,
    fallback_reason: str | None = None,
) -> dict:
    if isinstance(development_points, str):
        normalized_points = [item.strip() for item in re.split(r"[\n;•-]+", development_points) if item.strip()]
    elif development_points is None:
        normalized_points = []
    else:
        normalized_points = [coerce_text(item, "") for item in development_points if coerce_text(item, "")]

    fallback_points = _default_development_points(subject, audience, [])
    while len(normalized_points) < 3 and fallback_points:
        normalized_points.append(fallback_points[len(normalized_points) % len(fallback_points)])

    normalized_points = normalized_points[:5]
    normalized_title = coerce_text(title, f"{subject} : le guide simple en {duration_minutes} minutes")
    normalized_hook = coerce_text(hook, f"Vous voulez comprendre {subject} sans perdre de temps ?")
    normalized_conclusion = coerce_text(
        conclusion,
        (
            f"En résumé, {subject} devient beaucoup plus simple quand on suit un plan clair. "
            "Testez la méthode, ajustez-la à votre audience, puis publiez une version courte et directe."
        ),
    )
    full_text = _compose_full_text(normalized_hook, normalized_points, normalized_conclusion)
    sections = [
        {
            "heading": "Hook",
            "summary": normalized_hook,
            "body": f"{normalized_hook} Vous allez voir une méthode lisible, réutilisable et rapide à produire.",
        },
        {
            "heading": "Développement",
            "summary": f"{len(normalized_points)} étapes pour maîtriser {subject}.",
            "body": "\n".join(f"{index}. {point}" for index, point in enumerate(normalized_points, start=1)),
        },
        {
            "heading": "Conclusion",
            "summary": f"Récapitulatif et prochaine action autour de {subject}.",
            "body": normalized_conclusion,
        },
    ]

    return {
        "subject": subject,
        "audience": audience,
        "tone": tone,
        "language": language,
        "duration_minutes": duration_minutes,
        "target_word_count": target_word_count,
        "sections": sections,
        "full_text": full_text,
        "narration_text": full_text,
        "title_candidates": _unique(
            [
                normalized_title,
                f"{subject} : le guide simple en {duration_minutes} minutes",
                f"Comment réussir {subject} sans complexité",
                f"{subject} expliqué pas à pas",
            ]
        ),
        "source": source,
        "provider": provider,
        "model_name": model_name,
        "fallback_reason": fallback_reason,
    }


def _build_local_script_package(
    subject: str,
    idea_package: dict,
    audience: str,
    tone: str,
    language: str,
    duration_minutes: int,
    requested_title: str = "",
) -> dict:
    keywords = idea_package.get("keywords", [])
    hook = f"{idea_package['hook']} Dans cette vidéo, on passe de la théorie à l'action."
    development_points = [
        f"Comprendre les bases de {subject}.",
        f"Appliquer une méthode claire adaptée à {audience}.",
        "Éviter les erreurs fréquentes et garder une exécution simple.",
    ]

    if keywords:
        development_points.insert(1, f"Relier {keywords[0]} à un cas concret.")

    conclusion = (
        f"En résumé, {subject} devient beaucoup plus simple quand on suit un plan clair. "
        "Testez la méthode, ajustez-la à votre audience, puis publiez une version courte et directe."
    )

    return _build_script_package(
        subject=subject,
        audience=audience,
        tone=tone,
        language=language,
        duration_minutes=duration_minutes,
        target_word_count=duration_minutes * 150,
        title=requested_title or f"{subject} : le guide simple en {duration_minutes} minutes",
        hook=hook,
        development_points=development_points,
        conclusion=conclusion,
        source="local_template",
        provider="local_template",
        model_name=None,
    )


def _build_prompt(
    subject: str,
    idea_package: dict,
    audience: str,
    tone: str,
    language: str,
    duration_minutes: int,
    requested_title: str = "",
    creative_brief: str = "",
) -> str:
    keywords = ", ".join(idea_package.get("keywords", [])[:6]) or subject
    secondary_angles = " | ".join(idea_package.get("secondary_angles", [])[:3]) or idea_package.get(
        "primary_angle",
        subject,
    )
    trend_analysis = idea_package.get("trend_analysis") if isinstance(idea_package.get("trend_analysis"), dict) else {}
    trend_score = idea_package.get("trend_score", 0)
    trend_category = idea_package.get("trend_category") or trend_analysis.get("category", "n/a")
    trend_stage = idea_package.get("trend_stage") or trend_analysis.get("trend_stage", "stable")
    trend_format = trend_analysis.get("recommended_format", "")
    trend_summary = trend_analysis.get("summary", "")

    return "\n".join(
        [
            "Tu es un scénariste YouTube senior.",
            f"Rédige un script en {_language_label(language)} pour la vidéo suivante :",
            f"- Sujet : {subject}",
            f"- Titre souhaité : {requested_title}" if requested_title else "",
            f"- Brief utilisateur : {creative_brief}" if creative_brief else "",
            f"- Audience : {audience}",
            f"- Ton : {tone}",
            f"- Durée cible : {duration_minutes} minutes",
            f"- Analyse de tendance : {trend_score}/100 ({trend_stage})",
            f"- Catégorie tendance : {trend_category}",
            f"- Format recommandé : {trend_format or 'n/a'}",
            f"- Lecture rapide : {trend_summary}" if trend_summary else "",
            f"- Angle principal : {idea_package.get('primary_angle', subject)}",
            f"- Idée d'accroche : {idea_package.get('hook', '')}",
            f"- Mots-clés : {keywords}",
            f"- Angles secondaires : {secondary_angles}",
            "",
            "Retourne uniquement un objet JSON valide, sans texte avant ni après.",
            'Schéma attendu : {"title":"...","hook":"...","development_points":["..."],"conclusion":"..."}',
            "Contraintes :",
            "- Le hook doit capter l'attention en 1 à 2 phrases.",
            "- Les points de développement doivent être concrets, orientés action et faciles à lire à voix haute.",
            "- La conclusion doit proposer une prochaine action claire.",
            "- Le script doit rester naturel, fluide et utile.",
        ]
    )


def _call_huggingface(prompt: str, model_name: str, token: str, timeout_seconds: int, max_new_tokens: int, temperature: float) -> str:
    payload = {
        "inputs": prompt,
        "parameters": {
            "max_new_tokens": max_new_tokens,
            "temperature": temperature,
            "return_full_text": False,
            "do_sample": temperature > 0,
            "top_p": 0.9,
            "repetition_penalty": 1.05,
        },
        "options": {"wait_for_model": True},
    }
    request = urllib.request.Request(
        f"https://api-inference.huggingface.co/models/{model_name}",
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
            "Accept": "application/json",
        },
        method="POST",
    )

    try:
        with urllib.request.urlopen(request, timeout=timeout_seconds) as response:
            response_body = response.read().decode("utf-8")
    except urllib.error.HTTPError as exc:
        error_body = exc.read().decode("utf-8", errors="replace") if exc.fp else ""
        raise RuntimeError(f"Hugging Face API error ({exc.code}): {error_body or exc.reason}") from exc
    except urllib.error.URLError as exc:
        raise RuntimeError(f"Hugging Face API request failed: {exc.reason}") from exc

    return response_body


def _extract_generated_text(response_payload: object) -> str:
    if isinstance(response_payload, list):
        for item in response_payload:
            if isinstance(item, dict):
                generated_text = item.get("generated_text") or item.get("summary_text")
                if generated_text:
                    return str(generated_text)

    if isinstance(response_payload, dict):
        error_message = response_payload.get("error")
        if error_message:
            raise RuntimeError(str(error_message))

        generated_text = response_payload.get("generated_text") or response_payload.get("summary_text")
        if generated_text:
            return str(generated_text)

    raise ValueError("Hugging Face response did not contain generated text")


def _extract_json_object(text: str) -> dict:
    cleaned = text.strip()
    if cleaned.startswith("```"):
        cleaned = re.sub(r"^```(?:json)?\s*", "", cleaned)
        if cleaned.endswith("```"):
            cleaned = cleaned[:-3]
    start_index = cleaned.find("{")
    end_index = cleaned.rfind("}")
    if start_index == -1 or end_index == -1 or end_index <= start_index:
        raise ValueError("Hugging Face response did not contain a JSON object")

    return json.loads(cleaned[start_index : end_index + 1])


def _build_remote_script_package(
    subject: str,
    audience: str,
    tone: str,
    language: str,
    duration_minutes: int,
    target_word_count: int,
    parsed_payload: dict,
    model_name: str,
    requested_title: str = "",
) -> dict:
    return _build_script_package(
        subject=subject,
        audience=audience,
        tone=tone,
        language=language,
        duration_minutes=duration_minutes,
        target_word_count=target_word_count,
        title=requested_title or parsed_payload.get("title", ""),
        hook=parsed_payload.get("hook", ""),
        development_points=parsed_payload.get("development_points", []),
        conclusion=parsed_payload.get("conclusion", ""),
        source="huggingface",
        provider="huggingface_inference_api",
        model_name=model_name,
    )


def generate_script_package(
    subject: str,
    idea_package: dict,
    audience: str,
    tone: str,
    language: str,
    duration_minutes: int,
    requested_title: str = "",
    creative_brief: str = "",
    settings: Mapping[str, object] | None = None,
) -> dict:
    subject = coerce_text(subject, "Sujet sans titre")
    audience = coerce_text(audience, "general")
    tone = coerce_text(tone, "engaging")
    language = coerce_text(language, "fr")
    duration_minutes = clamp_int(duration_minutes, 3, minimum=1, maximum=30)
    target_word_count = duration_minutes * 150

    local_package = _build_local_script_package(
        subject=subject,
        idea_package=idea_package,
        audience=audience,
        tone=tone,
        language=language,
        duration_minutes=duration_minutes,
        requested_title=requested_title,
    )

    hf_token = _settings_value(settings, "HUGGINGFACE_API_TOKEN", "HF_TOKEN")
    if not hf_token:
        return {
            **local_package,
            "fallback_reason": "HUGGINGFACE_API_TOKEN is not configured.",
        }

    hf_model = _settings_value(settings, "HUGGINGFACE_MODEL") or DEFAULT_HUGGINGFACE_MODEL
    timeout_seconds = _settings_int(settings, "HUGGINGFACE_TIMEOUT_SECONDS", DEFAULT_TIMEOUT_SECONDS, 5, 300)
    max_new_tokens = _settings_int(settings, "HUGGINGFACE_MAX_NEW_TOKENS", DEFAULT_MAX_NEW_TOKENS, 64, 2048)
    temperature = _settings_float(settings, "HUGGINGFACE_TEMPERATURE", DEFAULT_TEMPERATURE, 0.1, 1.5)
    prompt = _build_prompt(
        subject,
        idea_package,
        audience,
        tone,
        language,
        duration_minutes,
        requested_title=requested_title,
        creative_brief=creative_brief,
    )

    try:
        response_body = _call_huggingface(
            prompt=prompt,
            model_name=hf_model,
            token=hf_token,
            timeout_seconds=timeout_seconds,
            max_new_tokens=max_new_tokens,
            temperature=temperature,
        )
        parsed_payload = _extract_json_object(_extract_generated_text(json.loads(response_body)))
        return _build_remote_script_package(
            subject=subject,
            audience=audience,
            tone=tone,
            language=language,
            duration_minutes=duration_minutes,
            target_word_count=target_word_count,
            parsed_payload=parsed_payload,
            model_name=hf_model,
            requested_title=requested_title,
        )
    except Exception as exc:
        return {
            **local_package,
            "model_name": hf_model,
            "fallback_reason": str(exc),
        }
