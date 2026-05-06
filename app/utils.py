from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from pathlib import Path


def coerce_text(value, default: str) -> str:
    if value is None:
        return default
    text = str(value).strip()
    return text or default


def clamp_int(value, default: int, minimum: int = 1, maximum: int | None = None) -> int:
    try:
        number = int(value)
    except (TypeError, ValueError):
        return default

    if number < minimum:
        number = minimum
    if maximum is not None and number > maximum:
        number = maximum
    return number


def slugify(value: str) -> str:
    normalized = re.sub(r"[^a-zA-Z0-9]+", "-", value.lower().strip())
    slug = normalized.strip("-")
    if not slug:
        return "video"

    return slug[:80].rstrip("-") or "video"


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def timestamp_token() -> str:
    return utc_now().strftime("%Y%m%d%H%M%S")


def ensure_directory(path: Path | str) -> Path:
    directory = Path(path)
    directory.mkdir(parents=True, exist_ok=True)
    return directory


def write_json(path: Path | str, payload: dict) -> Path:
    destination = Path(path)
    ensure_directory(destination.parent)
    destination.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
    return destination


def isoformat_z(value: datetime | None) -> str | None:
    if value is None:
        return None
    if value.tzinfo is None:
        return value.isoformat(timespec="seconds") + "Z"
    return value.astimezone(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")
