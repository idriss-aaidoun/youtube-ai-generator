from __future__ import annotations

from pathlib import Path

from PIL import Image

from app.services.render_service import render_video_package


def _write_scene_image(path: Path, color: tuple[int, int, int]) -> None:
    image = Image.new("RGB", (96, 96), color)
    image.save(path)


def test_render_video_package_generates_mp4(tmp_path: Path):
    scene_one = tmp_path / "scene_01.png"
    scene_two = tmp_path / "scene_02.png"
    scene_three = tmp_path / "scene_03.png"
    _write_scene_image(scene_one, (255, 183, 3))
    _write_scene_image(scene_two, (0, 209, 178))
    _write_scene_image(scene_three, (88, 196, 255))

    result = render_video_package(
        subject="Automatiser une chaîne YouTube",
        script_package={
            "sections": [
                {"heading": "Hook", "summary": "Accroche rapide", "body": "Accroche rapide"},
                {"heading": "Développement", "summary": "Méthode claire", "body": "Méthode claire"},
                {"heading": "Conclusion", "summary": "Action finale", "body": "Action finale"},
            ],
            "full_text": "Script complet de test.",
        },
        audio_package={
            "status": "planned",
            "provider": "placeholder",
            "artifact_path": str(tmp_path / "audio_manifest.json"),
            "audio_file_path": None,
            "estimated_duration_seconds": 3,
        },
        visual_package={
            "status": "planned",
            "scene_count": 3,
            "total_duration_seconds": 3,
            "keywords": ["automatisation", "youtube", "video"],
            "scenes": [
                {
                    "scene_number": 1,
                    "duration_seconds": 1,
                    "title": "Hook",
                    "caption": "Accroche rapide",
                    "visual_prompt": "Visuel d'accroche.",
                    "image_path": str(scene_one),
                },
                {
                    "scene_number": 2,
                    "duration_seconds": 1,
                    "title": "Développement",
                    "caption": "Méthode claire",
                    "visual_prompt": "Visuel méthode.",
                    "image_path": str(scene_two),
                },
                {
                    "scene_number": 3,
                    "duration_seconds": 1,
                    "title": "Conclusion",
                    "caption": "Action finale",
                    "visual_prompt": "Visuel conclusion.",
                    "image_path": str(scene_three),
                },
            ],
        },
        artifact_dir=tmp_path / "generated",
        settings={"TESTING": True},
    )

    assert result["status"] == "generated"
    assert result["provider"] == "imageio_ffmpeg"
    assert result["artifact_path"].endswith("rendered_video.mp4")
    assert Path(result["artifact_path"]).exists()
    assert Path(result["manifest_path"]).exists()
    assert Path(result["frames_dir"]).exists()
    assert result["subtitle_path"].endswith("subtitles.srt")
    assert Path(result["subtitle_path"]).exists()
    assert result["image_source_count"] == 3
    assert result["audio_muxed"] is False
