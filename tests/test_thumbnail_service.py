from __future__ import annotations

from io import BytesIO
from pathlib import Path

from PIL import Image

from app.services.thumbnail_service import generate_thumbnail_package


def _write_png(path: Path, color: tuple[int, int, int]) -> None:
    Image.new("RGB", (128, 128), color).save(path)


def test_generate_thumbnail_package_uses_visual_asset(tmp_path: Path):
    source_image = tmp_path / "scene_01.png"
    _write_png(source_image, (255, 183, 3))

    result = generate_thumbnail_package(
        subject="Automatiser une chaîne YouTube",
        seo_package={
            "title": "Automatiser une chaîne YouTube : le guide simple en 3 minutes",
            "primary_keyword": "automatisation youtube",
        },
        visual_package={
            "image_assets": [
                {
                    "image_path": str(source_image),
                    "source": "huggingface_image_api",
                }
            ]
        },
        artifact_dir=tmp_path / "generated",
    )

    assert result["status"] == "generated"
    assert result["provider"] == "thumbnail_composite"
    assert result["source_image_path"].endswith("scene_01.png")
    assert result["source_image_provider"] == "huggingface_image_api"
    assert Path(result["artifact_path"]).exists()
    assert Path(result["manifest_path"]).exists()
    assert result["output_size"] == {"width": 1280, "height": 720}
