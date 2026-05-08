from __future__ import annotations

import json
import os
import urllib.error
import urllib.request
from collections.abc import Mapping, Sequence
from pathlib import Path

from app.utils import clamp_int, coerce_text, ensure_directory, write_json


DEFAULT_ELEVENLABS_MODEL = "eleven_multilingual_v2"
DEFAULT_OUTPUT_FORMAT = "mp3_44100_128"
DEFAULT_TIMEOUT_SECONDS = 60


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


def _settings_bool(settings: Mapping[str, object] | None, name: str, default: bool) -> bool:
    raw_value = _settings_value(settings, name)
    if not raw_value:
        return default

    return raw_value.lower() in {"1", "true", "yes", "on"}


def _content_type(headers: object) -> str:
    if headers is None:
        return ""
    if hasattr(headers, "get_content_type"):
        try:
            return str(headers.get_content_type())
        except Exception:
            return ""
    if hasattr(headers, "get"):
        try:
            return str(headers.get("Content-Type", ""))
        except Exception:
            return ""
    return ""


def _request_json(request: urllib.request.Request, timeout_seconds: int) -> dict:
    try:
        with urllib.request.urlopen(request, timeout=timeout_seconds) as response:
            payload = response.read().decode("utf-8")
    except urllib.error.HTTPError as exc:
        error_body = exc.read().decode("utf-8", errors="replace") if exc.fp else ""
        raise RuntimeError(f"ElevenLabs API error ({exc.code}): {error_body or exc.reason}") from exc
    except urllib.error.URLError as exc:
        raise RuntimeError(f"ElevenLabs API request failed: {exc.reason}") from exc

    try:
        parsed = json.loads(payload)
    except json.JSONDecodeError as exc:
        raise RuntimeError("ElevenLabs voices response was not valid JSON") from exc

    if not isinstance(parsed, dict):
        raise RuntimeError("ElevenLabs voices response had an unexpected structure")

    if parsed.get("error"):
        raise RuntimeError(str(parsed["error"]))

    return parsed


def _request_binary(request: urllib.request.Request, timeout_seconds: int) -> tuple[bytes, str]:
    try:
        with urllib.request.urlopen(request, timeout=timeout_seconds) as response:
            headers = getattr(response, "headers", None)
            content_type = _content_type(headers)
            body = response.read()
    except urllib.error.HTTPError as exc:
        error_body = exc.read().decode("utf-8", errors="replace") if exc.fp else ""
        raise RuntimeError(f"ElevenLabs API error ({exc.code}): {error_body or exc.reason}") from exc
    except urllib.error.URLError as exc:
        raise RuntimeError(f"ElevenLabs API request failed: {exc.reason}") from exc

    if content_type.startswith("application/json"):
        try:
            parsed = json.loads(body.decode("utf-8"))
        except json.JSONDecodeError as exc:
            raise RuntimeError("ElevenLabs response was JSON but could not be parsed") from exc
        if isinstance(parsed, dict) and parsed.get("error"):
            raise RuntimeError(str(parsed["error"]))
        raise RuntimeError("ElevenLabs returned JSON instead of audio content")

    return body, content_type


def _fetch_voices(api_key: str, timeout_seconds: int) -> list[dict]:
    request = urllib.request.Request(
        "https://api.elevenlabs.io/v1/voices",
        headers={"xi-api-key": api_key, "Accept": "application/json"},
        method="GET",
    )
    payload = _request_json(request, timeout_seconds)
    voices = payload.get("voices", [])
    if not isinstance(voices, list):
        raise RuntimeError("ElevenLabs voices response did not include a voices list")
    return [voice for voice in voices if isinstance(voice, dict)]


def _select_voice_id(requested_voice: str, voices: Sequence[dict], settings: Mapping[str, object] | None) -> tuple[str, str]:
    explicit_voice_id = _settings_value(settings, "ELEVENLABS_VOICE_ID")
    if explicit_voice_id:
        return explicit_voice_id, "explicit"

    normalized_voice = coerce_text(requested_voice, "female").lower()
    if normalized_voice in {"female", "woman", "f"}:
        configured_voice_id = _settings_value(settings, "ELEVENLABS_VOICE_ID_FEMALE")
        if configured_voice_id:
            return configured_voice_id, "configured_female"
    elif normalized_voice in {"male", "man", "m"}:
        configured_voice_id = _settings_value(settings, "ELEVENLABS_VOICE_ID_MALE")
        if configured_voice_id:
            return configured_voice_id, "configured_male"

    if not voices:
        return "", "unresolved"

    gender_candidates = []
    fallback_candidates = []

    for voice in voices:
        voice_id = coerce_text(voice.get("voice_id"), "")
        if not voice_id:
            continue

        voice_name = coerce_text(voice.get("name"), "")
        labels = voice.get("labels") if isinstance(voice.get("labels"), Mapping) else {}
        gender = coerce_text(labels.get("gender") if isinstance(labels, Mapping) else "", "").lower()

        if normalized_voice in {"female", "woman", "f"} and gender == "female":
            gender_candidates.append((voice_name, voice_id))
            continue
        if normalized_voice in {"male", "man", "m"} and gender == "male":
            gender_candidates.append((voice_name, voice_id))
            continue

        fallback_candidates.append((voice_name, voice_id))

    if gender_candidates:
        gender_candidates.sort(key=lambda item: item[0].lower())
        return gender_candidates[0][1], "voices_api_gender"

    if fallback_candidates:
        fallback_candidates.sort(key=lambda item: item[0].lower())
        return fallback_candidates[0][1], "voices_api_default"

    return "", "unresolved"


def _build_manifest(
    *,
    subject: str,
    voice: str,
    voice_id: str | None,
    language: str,
    provider: str,
    status: str,
    estimated_duration_seconds: int,
    narration_excerpt: str,
    model_id: str | None,
    audio_file_path: str | None,
    fallback_reason: str | None,
    voice_source: str | None,
) -> dict:
    return {
        "status": status,
        "provider": provider,
        "subject": subject,
        "voice": voice,
        "voice_id": voice_id,
        "voice_source": voice_source,
        "language": language,
        "model_id": model_id,
        "estimated_duration_seconds": estimated_duration_seconds,
        "narration_excerpt": narration_excerpt[:800],
        "audio_file_path": audio_file_path,
        "fallback_reason": fallback_reason,
    }


def _synthesize_with_elevenlabs(
    *,
    api_key: str,
    voice_id: str,
    text: str,
    model_id: str,
    output_format: str,
    stability: float,
    similarity_boost: float,
    style: float,
    use_speaker_boost: bool,
    timeout_seconds: int,
) -> tuple[bytes, str]:
    payload = {
        "text": text,
        "model_id": model_id,
        "voice_settings": {
            "stability": stability,
            "similarity_boost": similarity_boost,
            "style": style,
            "use_speaker_boost": use_speaker_boost,
        },
    }
    request = urllib.request.Request(
        f"https://api.elevenlabs.io/v1/text-to-speech/{voice_id}?output_format={output_format}",
        data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
        headers={
            "xi-api-key": api_key,
            "Content-Type": "application/json",
            "Accept": "audio/mpeg",
        },
        method="POST",
    )
    return _request_binary(request, timeout_seconds)


def generate_audio_package(
    subject: str,
    script_package: dict,
    voice: str,
    language: str,
    artifact_dir: Path,
    settings: Mapping[str, object] | None = None,
) -> dict:
    voice = coerce_text(voice, "female")
    language = coerce_text(language, "fr")
    artifact_dir = ensure_directory(Path(artifact_dir))
    script_text = coerce_text(script_package.get("narration_text") or script_package.get("full_text"), "")
    estimated_duration_seconds = max(30, int((len(script_text.split()) / 150) * 60))
    api_key = _settings_value(settings, "ELEVENLABS_API_KEY")

    manifest_path = artifact_dir / "audio_manifest.json"
    audio_file_path = artifact_dir / "voiceover.mp3"

    if not api_key:
        manifest = _build_manifest(
            subject=subject,
            voice=voice,
            voice_id=None,
            language=language,
            provider="placeholder",
            status="planned",
            estimated_duration_seconds=estimated_duration_seconds,
            narration_excerpt=script_text,
            model_id=None,
            audio_file_path=None,
            fallback_reason="ELEVENLABS_API_KEY is not configured.",
            voice_source=None,
        )
        manifest["notes"] = "Configure ELEVENLABS_API_KEY to generate a real voiceover with ElevenLabs."
        path = write_json(manifest_path, manifest)
        return {**manifest, "artifact_path": str(path), "manifest_path": str(path), "audio_file_path": None}

    timeout_seconds = _settings_int(settings, "ELEVENLABS_TIMEOUT_SECONDS", DEFAULT_TIMEOUT_SECONDS, 5, 300)
    model_id = _settings_value(settings, "ELEVENLABS_MODEL_ID") or DEFAULT_ELEVENLABS_MODEL
    output_format = _settings_value(settings, "ELEVENLABS_OUTPUT_FORMAT") or DEFAULT_OUTPUT_FORMAT
    stability = _settings_float(settings, "ELEVENLABS_STABILITY", 0.5, 0.0, 1.0)
    similarity_boost = _settings_float(settings, "ELEVENLABS_SIMILARITY_BOOST", 0.75, 0.0, 1.0)
    style = _settings_float(settings, "ELEVENLABS_STYLE", 0.0, 0.0, 1.0)
    use_speaker_boost = _settings_bool(settings, "ELEVENLABS_USE_SPEAKER_BOOST", True)

    try:
        voices = _fetch_voices(api_key, timeout_seconds)
        selected_voice_id, voice_source = _select_voice_id(voice, voices, settings)
        if not selected_voice_id:
            raise RuntimeError("No ElevenLabs voice could be selected")

        audio_bytes, content_type = _synthesize_with_elevenlabs(
            api_key=api_key,
            voice_id=selected_voice_id,
            text=script_text,
            model_id=model_id,
            output_format=output_format,
            stability=stability,
            similarity_boost=similarity_boost,
            style=style,
            use_speaker_boost=use_speaker_boost,
            timeout_seconds=timeout_seconds,
        )

        if not audio_bytes:
            raise RuntimeError("ElevenLabs returned an empty audio payload")

        audio_file_path.write_bytes(audio_bytes)
        manifest = _build_manifest(
            subject=subject,
            voice=voice,
            voice_id=selected_voice_id,
            language=language,
            provider="elevenlabs",
            status="generated",
            estimated_duration_seconds=estimated_duration_seconds,
            narration_excerpt=script_text,
            model_id=model_id,
            audio_file_path=str(audio_file_path),
            fallback_reason=None,
            voice_source=voice_source,
        )
        manifest["content_type"] = content_type or "audio/mpeg"
        manifest["output_format"] = output_format
        manifest["notes"] = "Real voiceover generated with ElevenLabs."
        path = write_json(manifest_path, manifest)
        return {
            **manifest,
            "artifact_path": str(audio_file_path),
            "manifest_path": str(path),
            "audio_file_path": str(audio_file_path),
        }
    except Exception as exc:
        manifest = _build_manifest(
            subject=subject,
            voice=voice,
            voice_id=None,
            language=language,
            provider="placeholder",
            status="planned",
            estimated_duration_seconds=estimated_duration_seconds,
            narration_excerpt=script_text,
            model_id=model_id,
            audio_file_path=None,
            fallback_reason=str(exc),
            voice_source=None,
        )
        manifest["notes"] = "ElevenLabs integration failed, so the pipeline fell back to a manifest only."
        path = write_json(manifest_path, manifest)
        return {**manifest, "artifact_path": str(path), "manifest_path": str(path), "audio_file_path": None}
