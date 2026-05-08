from __future__ import annotations

from pathlib import Path

from collections.abc import Mapping

from app.services.render_service import render_video_package


def assemble_video_package(
    subject: str,
    script_package: dict,
    audio_package: dict,
    visual_package: dict,
    artifact_dir: Path,
    settings: Mapping[str, object] | None = None,
) -> dict:
    return render_video_package(
        subject=subject,
        script_package=script_package,
        audio_package=audio_package,
        visual_package=visual_package,
        artifact_dir=artifact_dir,
        settings=settings,
    )
