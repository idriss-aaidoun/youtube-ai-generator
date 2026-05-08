from __future__ import annotations

import json
import mimetypes
import os
import re
import unicodedata
import urllib.error
import urllib.parse
import urllib.request
from collections.abc import Mapping, Sequence
from pathlib import Path

from app.utils import clamp_int, coerce_text, ensure_directory, write_json


DEFAULT_PRIVACY_STATUS = "private"
DEFAULT_CATEGORY_ID = "22"
DEFAULT_TIMEOUT_SECONDS = 60
YOUTUBE_UPLOAD_SCOPE = "https://www.googleapis.com/auth/youtube.upload"


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
        text = str(value).strip()
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


def _settings_bool(settings: Mapping[str, object] | None, name: str, default: bool) -> bool:
    raw_value = _settings_value(settings, name)
    if not raw_value:
        return default
    return raw_value.lower() in {"1", "true", "yes", "on"}


def _response_header(response: object, header_name: str) -> str:
    headers = getattr(response, "headers", None)
    if headers is not None and hasattr(headers, "get"):
        value = headers.get(header_name)
        if value:
            return str(value)
    if hasattr(response, "getheader"):
        value = response.getheader(header_name)
        if value:
            return str(value)
    return ""


def _read_json_response(response: object) -> dict:
    payload = response.read().decode("utf-8")
    try:
        parsed = json.loads(payload)
    except json.JSONDecodeError as exc:
        raise RuntimeError("YouTube API response was not valid JSON") from exc

    if not isinstance(parsed, dict):
        raise RuntimeError("YouTube API response had an unexpected structure")

    if parsed.get("error"):
        error = parsed["error"]
        if isinstance(error, dict):
            message = error.get("message") or json.dumps(error)
        else:
            message = str(error)
        raise RuntimeError(message)

    return parsed


def _format_timestamp(total_seconds: int) -> str:
    total_seconds = max(0, int(total_seconds))
    hours, remainder = divmod(total_seconds, 3600)
    minutes, seconds = divmod(remainder, 60)
    if hours:
        return f"{hours}:{minutes:02d}:{seconds:02d}"
    return f"{minutes}:{seconds:02d}"


def _normalize_hashtag(value: object) -> str:
    text = coerce_text(value, "")
    if not text:
        return ""

    normalized = unicodedata.normalize("NFKD", text)
    ascii_text = normalized.encode("ascii", "ignore").decode("ascii")
    cleaned = re.sub(r"[^0-9A-Za-z]+", "", ascii_text)
    if not cleaned:
        return ""
    return f"#{cleaned.lower()}"


def _parse_timestamp_seconds(value: object) -> int | None:
    if isinstance(value, bool):
        return None
    if isinstance(value, int):
        return max(0, value)
    if isinstance(value, float):
        return max(0, int(value))

    raw_value = coerce_text(value, "")
    if not raw_value:
        return None

    if raw_value.isdigit():
        return max(0, int(raw_value))

    parts = raw_value.split(":")
    if len(parts) not in {2, 3}:
        return None
    if not all(part.isdigit() for part in parts):
        return None

    numbers = [int(part) for part in parts]
    if len(numbers) == 2:
        minutes, seconds = numbers
        return minutes * 60 + seconds

    hours, minutes, seconds = numbers
    return hours * 3600 + minutes * 60 + seconds


def _normalize_chapter_entry(entry: object, index: int, fallback_seconds: int) -> dict | None:
    if not isinstance(entry, Mapping):
        return None

    title = coerce_text(entry.get("title") or entry.get("heading"), f"Section {index + 1}")
    summary = coerce_text(entry.get("summary"), title)
    timestamp_value = entry.get("timestamp")
    if timestamp_value is None:
        timestamp_value = entry.get("start_seconds")
    if timestamp_value is None:
        timestamp_value = entry.get("time")
    if timestamp_value is None:
        timestamp_value = entry.get("offset")

    parsed_seconds = _parse_timestamp_seconds(timestamp_value)
    if parsed_seconds is None:
        parsed_seconds = fallback_seconds

    return {
        "timestamp": _format_timestamp(parsed_seconds),
        "title": title,
        "summary": summary,
    }


def _build_chapters(
    script_package: Mapping[str, object] | None,
    chapter_overrides: Sequence[Mapping[str, object]] | None = None,
) -> list[dict]:
    if chapter_overrides is not None:
        duration_minutes = clamp_int(script_package.get("duration_minutes") if script_package else None, 3, minimum=1, maximum=30)
        total_seconds = max(60, duration_minutes * 60)
        segment_seconds = max(10, total_seconds // max(1, len(chapter_overrides)))
        normalized_chapters: list[dict] = []
        for index, entry in enumerate(chapter_overrides):
            normalized_entry = _normalize_chapter_entry(entry, index, index * segment_seconds)
            if normalized_entry is not None:
                normalized_chapters.append(normalized_entry)
        return normalized_chapters

    if not script_package:
        return []

    sections = script_package.get("sections")
    if not isinstance(sections, list) or not sections:
        return []

    duration_minutes = clamp_int(script_package.get("duration_minutes"), 3, minimum=1, maximum=30)
    total_seconds = max(60, duration_minutes * 60)
    segment_seconds = max(10, total_seconds // len(sections))

    chapters: list[dict] = []
    for index, section in enumerate(sections):
        if not isinstance(section, Mapping):
            continue

        heading = coerce_text(section.get("heading"), f"Section {index + 1}")
        summary = coerce_text(section.get("summary"), heading)
        start_seconds = min(index * segment_seconds, max(0, total_seconds - 1))
        chapters.append(
            {
                "timestamp": _format_timestamp(start_seconds),
                "title": heading,
                "summary": summary,
            }
        )

    return chapters


def _publication_sequence_option(publication_options: Mapping[str, object] | None, name: str) -> list[object] | None:
    if not publication_options or name not in publication_options:
        return None

    value = publication_options.get(name)
    if value is None:
        return []

    if isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray)):
        return list(value)

    return None


def _build_hashtags(
    seo_package: Mapping[str, object],
    hashtag_overrides: Sequence[object] | None = None,
    hashtag_blacklist: Sequence[object] | None = None,
    limit: int = 5,
) -> list[str]:
    blacklist = {
        normalized
        for normalized in (_normalize_hashtag(item) for item in (hashtag_blacklist or []))
        if normalized
    }

    if hashtag_overrides is not None:
        candidates: Sequence[object] = hashtag_overrides
    else:
        candidates = []
        primary_keyword = seo_package.get("primary_keyword")
        if primary_keyword:
            candidates.append(primary_keyword)

        tags = seo_package.get("tags")
        if isinstance(tags, list):
            candidates.extend(tags)

    hashtags: list[str] = []
    seen: set[str] = set()
    for candidate in candidates:
        hashtag = _normalize_hashtag(candidate)
        if not hashtag or hashtag in seen or hashtag in blacklist:
            continue
        seen.add(hashtag)
        hashtags.append(hashtag)
        if len(hashtags) >= limit:
            break

    return hashtags


def _build_publication_description(seo_package: Mapping[str, object], chapters: list[dict], hashtags: list[str]) -> str:
    base_description = coerce_text(seo_package.get("description"), "")
    blocks: list[str] = []

    if base_description:
        blocks.append(base_description)

    if chapters:
        chapter_lines = ["Chapitres"]
        chapter_lines.extend(f"{chapter['timestamp']} {chapter['title']}" for chapter in chapters)
        blocks.append("\n".join(chapter_lines))

    if hashtags:
        blocks.append(" ".join(hashtags))

    return "\n\n".join(blocks)


def _request_json(request: urllib.request.Request, timeout_seconds: int) -> dict:
    try:
        with urllib.request.urlopen(request, timeout=timeout_seconds) as response:
            return _read_json_response(response)
    except urllib.error.HTTPError as exc:
        error_body = exc.read().decode("utf-8", errors="replace") if exc.fp else ""
        raise RuntimeError(f"YouTube API error ({exc.code}): {error_body or exc.reason}") from exc
    except urllib.error.URLError as exc:
        raise RuntimeError(f"YouTube API request failed: {exc.reason}") from exc


def _resolve_access_token(settings: Mapping[str, object] | None, timeout_seconds: int) -> str:
    direct_token = _settings_value(settings, "YOUTUBE_ACCESS_TOKEN")
    if direct_token:
        return direct_token

    client_id = _settings_value(settings, "YOUTUBE_CLIENT_ID")
    client_secret = _settings_value(settings, "YOUTUBE_CLIENT_SECRET")
    refresh_token = _settings_value(settings, "YOUTUBE_REFRESH_TOKEN")

    if not (client_id and client_secret and refresh_token):
        raise RuntimeError("Missing YouTube OAuth credentials")

    token_payload = urllib.parse.urlencode(
        {
            "client_id": client_id,
            "client_secret": client_secret,
            "refresh_token": refresh_token,
            "grant_type": "refresh_token",
        }
    ).encode("utf-8")
    request = urllib.request.Request(
        "https://oauth2.googleapis.com/token",
        data=token_payload,
        headers={"Content-Type": "application/x-www-form-urlencoded", "Accept": "application/json"},
        method="POST",
    )
    response = _request_json(request, timeout_seconds)
    access_token = coerce_text(response.get("access_token"), "")
    if not access_token:
        raise RuntimeError("YouTube OAuth token exchange did not return an access token")
    return access_token


def _build_upload_metadata(
    *,
    seo_package: dict,
    description: str,
    privacy_status: str,
    category_id: str,
    made_for_kids: bool,
    default_language: str | None,
    default_audio_language: str | None,
) -> dict:
    snippet = {
        "title": seo_package["title"],
        "description": description,
        "tags": seo_package["tags"],
        "categoryId": category_id,
    }
    if default_language:
        snippet["defaultLanguage"] = default_language
    if default_audio_language:
        snippet["defaultAudioLanguage"] = default_audio_language

    return {
        "snippet": snippet,
        "status": {
            "privacyStatus": privacy_status,
            "selfDeclaredMadeForKids": made_for_kids,
        },
    }


def _build_publication_plan(
    *,
    subject: str,
    seo_package: dict,
    publication_description: str,
    chapters: list[dict],
    hashtags: list[str],
    chapter_source: str,
    hashtag_source: str,
    video_path: Path | None,
    thumbnail_package: Mapping[str, object] | None,
    privacy_status: str,
    category_id: str,
    made_for_kids: bool,
    notify_subscribers: bool,
    default_language: str | None,
    default_audio_language: str | None,
) -> dict:
    thumbnail_path = None
    thumbnail_provider = None
    thumbnail_status = None
    thumbnail_source_image_provider = None
    if thumbnail_package is not None:
        thumbnail_path = coerce_text(thumbnail_package.get("artifact_path"), "") or None
        thumbnail_provider = coerce_text(thumbnail_package.get("provider"), "") or None
        thumbnail_status = coerce_text(thumbnail_package.get("status"), "") or None
        thumbnail_source_image_provider = coerce_text(thumbnail_package.get("source_image_provider"), "") or None

    upload_metadata = _build_upload_metadata(
        seo_package=seo_package,
        description=publication_description,
        privacy_status=privacy_status,
        category_id=category_id,
        made_for_kids=made_for_kids,
        default_language=default_language,
        default_audio_language=default_audio_language,
    )

    return {
        "platform": "youtube",
        "provider": "local_plan",
        "subject": subject,
        "status": "pending_credentials",
        "upload_enabled": False,
        "youtube_url": None,
        "youtube_video_id": None,
        "video_path": str(video_path) if video_path else None,
        "thumbnail_path": thumbnail_path,
        "thumbnail_provider": thumbnail_provider,
        "thumbnail_status": thumbnail_status,
        "thumbnail_source_image_provider": thumbnail_source_image_provider,
        "description": publication_description,
        "chapters": chapters,
        "chapter_source": chapter_source,
        "hashtags": hashtags,
        "hashtag_source": hashtag_source,
        "upload_metadata": upload_metadata,
        "title": seo_package["title"],
        "seo_description": seo_package["description"],
        "tags": seo_package["tags"],
        "privacy_status": privacy_status,
        "category_id": category_id,
        "made_for_kids": made_for_kids,
        "notify_subscribers": notify_subscribers,
        "notes": "Configure OAuth credentials to enable automatic upload.",
    }


def _initiate_resumable_upload(
    *,
    access_token: str,
    video_path: Path,
    metadata: dict,
    timeout_seconds: int,
) -> str:
    upload_url = "https://www.googleapis.com/upload/youtube/v3/videos?part=snippet,status&uploadType=resumable"
    request = urllib.request.Request(
        upload_url,
        data=json.dumps(metadata, ensure_ascii=False).encode("utf-8"),
        headers={
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json; charset=UTF-8",
            "X-Upload-Content-Length": str(video_path.stat().st_size),
            "X-Upload-Content-Type": "video/mp4",
            "Accept": "application/json",
        },
        method="POST",
    )

    try:
        with urllib.request.urlopen(request, timeout=timeout_seconds) as response:
            location = _response_header(response, "Location")
            if not location:
                raise RuntimeError("YouTube resumable upload did not return a Location header")
            return location
    except urllib.error.HTTPError as exc:
        error_body = exc.read().decode("utf-8", errors="replace") if exc.fp else ""
        raise RuntimeError(f"YouTube upload initialization failed ({exc.code}): {error_body or exc.reason}") from exc
    except urllib.error.URLError as exc:
        raise RuntimeError(f"YouTube upload initialization failed: {exc.reason}") from exc


def _finalize_resumable_upload(upload_location: str, video_path: Path, timeout_seconds: int) -> dict:
    video_bytes = video_path.read_bytes()
    request = urllib.request.Request(
        upload_location,
        data=video_bytes,
        headers={
            "Content-Type": "video/mp4",
            "Content-Length": str(len(video_bytes)),
            "Accept": "application/json",
        },
        method="PUT",
    )
    try:
        with urllib.request.urlopen(request, timeout=timeout_seconds) as response:
            return _read_json_response(response)
    except urllib.error.HTTPError as exc:
        error_body = exc.read().decode("utf-8", errors="replace") if exc.fp else ""
        raise RuntimeError(f"YouTube video upload failed ({exc.code}): {error_body or exc.reason}") from exc
    except urllib.error.URLError as exc:
        raise RuntimeError(f"YouTube video upload failed: {exc.reason}") from exc


def _upload_thumbnail(access_token: str, video_id: str, thumbnail_path: Path, timeout_seconds: int) -> dict:
    content_type = mimetypes.guess_type(str(thumbnail_path))[0] or "image/png"
    request = urllib.request.Request(
        f"https://www.googleapis.com/upload/youtube/v3/thumbnails/set?videoId={video_id}&uploadType=media",
        data=thumbnail_path.read_bytes(),
        headers={
            "Authorization": f"Bearer {access_token}",
            "Content-Type": content_type,
            "Accept": "application/json",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=timeout_seconds) as response:
            return _read_json_response(response)
    except urllib.error.HTTPError as exc:
        error_body = exc.read().decode("utf-8", errors="replace") if exc.fp else ""
        raise RuntimeError(f"YouTube thumbnail upload failed ({exc.code}): {error_body or exc.reason}") from exc
    except urllib.error.URLError as exc:
        raise RuntimeError(f"YouTube thumbnail upload failed: {exc.reason}") from exc


def prepare_publication_package(
    subject: str,
    seo_package: dict,
    artifact_dir: Path,
    video_path: Path | str | None,
    script_package: Mapping[str, object] | None = None,
    publication_options: Mapping[str, object] | None = None,
    thumbnail_package: Mapping[str, object] | None = None,
    settings: Mapping[str, object] | None = None,
) -> dict:
    artifact_dir = ensure_directory(Path(artifact_dir))
    video_file = Path(video_path) if video_path else None
    if video_file is not None and not video_file.exists():
        video_file = None

    privacy_status = _settings_value(settings, "YOUTUBE_PRIVACY_STATUS") or DEFAULT_PRIVACY_STATUS
    category_id = _settings_value(settings, "YOUTUBE_CATEGORY_ID") or DEFAULT_CATEGORY_ID
    made_for_kids = _settings_bool(settings, "YOUTUBE_MADE_FOR_KIDS", False)
    notify_subscribers = _settings_bool(settings, "YOUTUBE_NOTIFY_SUBSCRIBERS", False)
    timeout_seconds = _settings_int(settings, "YOUTUBE_TIMEOUT_SECONDS", DEFAULT_TIMEOUT_SECONDS, 10, 300)
    default_language = _settings_value(settings, "YOUTUBE_DEFAULT_LANGUAGE") or None
    default_audio_language = _settings_value(settings, "YOUTUBE_DEFAULT_AUDIO_LANGUAGE") or None
    chapter_overrides = _publication_sequence_option(publication_options, "chapters")
    hashtag_overrides = _publication_sequence_option(publication_options, "hashtags")
    hashtag_blacklist = _publication_sequence_option(publication_options, "hashtag_blacklist")
    chapters = _build_chapters(script_package, chapter_overrides)
    hashtags = _build_hashtags(seo_package, hashtag_overrides, hashtag_blacklist)
    publication_description = _build_publication_description(seo_package, chapters, hashtags)
    chapter_source = "manual" if chapter_overrides is not None else "auto"
    hashtag_source = "manual" if hashtag_overrides is not None else "seo"

    thumbnail_path = None
    thumbnail_provider = None
    thumbnail_status = None
    thumbnail_source_image_provider = None
    if thumbnail_package is not None:
        thumbnail_path = coerce_text(thumbnail_package.get("artifact_path"), "") or None
        thumbnail_provider = coerce_text(thumbnail_package.get("provider"), "") or None
        thumbnail_status = coerce_text(thumbnail_package.get("status"), "") or None
        thumbnail_source_image_provider = coerce_text(thumbnail_package.get("source_image_provider"), "") or None

    upload_metadata = _build_upload_metadata(
        seo_package=seo_package,
        description=publication_description,
        privacy_status=privacy_status,
        category_id=category_id,
        made_for_kids=made_for_kids,
        default_language=default_language,
        default_audio_language=default_audio_language,
    )

    base_plan = _build_publication_plan(
        subject=subject,
        seo_package=seo_package,
        publication_description=publication_description,
        chapters=chapters,
        hashtags=hashtags,
        chapter_source=chapter_source,
        hashtag_source=hashtag_source,
        video_path=video_file,
        thumbnail_package=thumbnail_package,
        privacy_status=privacy_status,
        category_id=category_id,
        made_for_kids=made_for_kids,
        notify_subscribers=notify_subscribers,
        default_language=default_language,
        default_audio_language=default_audio_language,
    )

    if video_file is None:
        result = {
            **base_plan,
            "status": "missing_video_file",
            "notes": "The MP4 file was not found, so publication could not start.",
        }
        path = write_json(artifact_dir / "youtube_publication.json", result)
        return {**result, "artifact_path": str(path)}

    has_credentials = bool(
        _settings_value(settings, "YOUTUBE_ACCESS_TOKEN")
        or (
            _settings_value(settings, "YOUTUBE_CLIENT_ID")
            and _settings_value(settings, "YOUTUBE_CLIENT_SECRET")
            and _settings_value(settings, "YOUTUBE_REFRESH_TOKEN")
        )
    )

    if not has_credentials:
        result = {
            **base_plan,
            "status": "pending_credentials",
            "thumbnail_upload_status": "pending_credentials" if thumbnail_path else "missing_thumbnail",
            "thumbnail_url": None,
            "upload_metadata": upload_metadata,
            "notes": "OAuth credentials are required for automatic upload.",
        }
        path = write_json(artifact_dir / "youtube_publication.json", result)
        return {**result, "artifact_path": str(path)}

    try:
        access_token = _resolve_access_token(settings, timeout_seconds)
        upload_location = _initiate_resumable_upload(
            access_token=access_token,
            video_path=video_file,
            metadata=upload_metadata,
            timeout_seconds=timeout_seconds,
        )
        upload_response = _finalize_resumable_upload(upload_location, video_file, timeout_seconds)
        youtube_video_id = coerce_text(upload_response.get("id"), "")
        youtube_url = f"https://www.youtube.com/watch?v={youtube_video_id}" if youtube_video_id else None

        thumbnail_upload_response = None
        thumbnail_upload_status = "missing_thumbnail"
        thumbnail_upload_error = None
        if thumbnail_path:
            thumbnail_file = Path(thumbnail_path)
            if thumbnail_file.exists():
                try:
                    thumbnail_upload_response = _upload_thumbnail(access_token, youtube_video_id, thumbnail_file, timeout_seconds)
                    thumbnail_upload_status = "uploaded"
                except Exception as exc:
                    thumbnail_upload_status = "upload_failed"
                    thumbnail_upload_error = str(exc)
            else:
                thumbnail_upload_status = "missing_thumbnail"
        else:
            thumbnail_upload_status = "missing_thumbnail"

        result = {
            **base_plan,
            "provider": "youtube_data_api",
            "status": "uploaded",
            "upload_enabled": True,
            "youtube_url": youtube_url,
            "youtube_video_id": youtube_video_id or None,
            "upload_metadata": upload_metadata,
            "upload_response": upload_response,
            "thumbnail_upload_status": thumbnail_upload_status,
            "thumbnail_upload_response": thumbnail_upload_response,
            "thumbnail_upload_error": thumbnail_upload_error,
            "thumbnail_url": f"https://img.youtube.com/vi/{youtube_video_id}/maxresdefault.jpg" if youtube_video_id else None,
            "notes": (
                "Video and thumbnail uploaded successfully to YouTube."
                if thumbnail_upload_status == "uploaded"
                else "Video uploaded successfully to YouTube."
            ),
        }
        if thumbnail_path:
            result["thumbnail_path"] = thumbnail_path
        path = write_json(artifact_dir / "youtube_publication.json", result)
        return {**result, "artifact_path": str(path)}
    except Exception as exc:
        result = {
            **base_plan,
            "provider": "youtube_data_api",
            "status": "upload_failed",
            "upload_enabled": False,
            "upload_metadata": upload_metadata,
            "thumbnail_upload_status": "not_started" if thumbnail_path else "missing_thumbnail",
            "thumbnail_url": None,
            "fallback_reason": str(exc),
            "notes": "The upload failed, but the pipeline preserved a publication plan for retry.",
        }
        path = write_json(artifact_dir / "youtube_publication.json", result)
        return {**result, "artifact_path": str(path)}
