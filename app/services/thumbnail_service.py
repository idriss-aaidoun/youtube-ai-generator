from __future__ import annotations

from pathlib import Path
from collections.abc import Mapping, Sequence
from textwrap import wrap

from PIL import Image, ImageDraw, ImageFont, ImageOps

from app.utils import coerce_text, ensure_directory, write_json

THUMBNAIL_WIDTH = 1280
THUMBNAIL_HEIGHT = 720


def _font_candidates(bold: bool) -> list[Path]:
    windows_root = Path(r"C:\Windows")
    candidates = [
        windows_root / "Fonts" / ("arialbd.ttf" if bold else "arial.ttf"),
        windows_root / "Fonts" / ("segoeuib.ttf" if bold else "segoeui.ttf"),
        windows_root / "Fonts" / ("calibrib.ttf" if bold else "calibri.ttf"),
        Path("/usr/share/fonts/truetype/dejavu") / ("DejaVuSans-Bold.ttf" if bold else "DejaVuSans.ttf"),
    ]
    return candidates


def _resolve_font(size: int, bold: bool = False) -> ImageFont.ImageFont:
    for candidate in _font_candidates(bold):
        if candidate.exists():
            try:
                return ImageFont.truetype(str(candidate), size=size)
            except OSError:
                continue
    return ImageFont.load_default()


def _measure_text(draw: ImageDraw.ImageDraw, text: str, font: ImageFont.ImageFont) -> tuple[int, int]:
    bbox = draw.textbbox((0, 0), text or " ", font=font)
    return bbox[2] - bbox[0], bbox[3] - bbox[1]


def _wrap_text(draw: ImageDraw.ImageDraw, text: str, font: ImageFont.ImageFont, max_width: int) -> list[str]:
    words = coerce_text(text, "").split()
    if not words:
        return [""]

    lines: list[str] = []
    current_line = words[0]
    for word in words[1:]:
        candidate_line = f"{current_line} {word}"
        candidate_width, _ = _measure_text(draw, candidate_line, font)
        if candidate_width <= max_width:
            current_line = candidate_line
        else:
            lines.append(current_line)
            current_line = word
    lines.append(current_line)
    return lines


def _draw_wrapped_text(
    draw: ImageDraw.ImageDraw,
    text: str,
    font: ImageFont.ImageFont,
    x: int,
    y: int,
    max_width: int,
    fill: tuple[int, int, int],
    line_spacing: int | None = None,
) -> int:
    lines = _wrap_text(draw, text, font, max_width)
    spacing = line_spacing if line_spacing is not None else max(4, int(getattr(font, "size", 18) * 0.25))
    cursor_y = y

    for line in lines:
        draw.text((x, cursor_y), line, font=font, fill=fill)
        _, height = _measure_text(draw, line, font)
        cursor_y += height + spacing

    return cursor_y - y


def _select_source_asset(visual_package: dict) -> tuple[Path | None, str | None]:
    assets = visual_package.get("image_assets") or []
    if not isinstance(assets, Sequence):
        return None, None

    for asset in assets:
        if not isinstance(asset, Mapping):
            continue
        image_path = coerce_text(asset.get("image_path"), "")
        if not image_path:
            continue
        path = Path(image_path)
        if path.exists():
            return path, coerce_text(asset.get("source"), "") or None
    return None, None


def _create_background() -> Image.Image:
    image = Image.new("RGBA", (THUMBNAIL_WIDTH, THUMBNAIL_HEIGHT), (11, 18, 33, 255))
    draw = ImageDraw.Draw(image, "RGBA")
    draw.rectangle((0, 0, THUMBNAIL_WIDTH, THUMBNAIL_HEIGHT), fill=(10, 18, 36, 255))
    draw.ellipse((-180, -120, 420, 420), fill=(255, 183, 3, 80))
    draw.ellipse((880, 40, 1480, 640), fill=(0, 209, 178, 75))
    draw.ellipse((920, 500, 1420, 1000), fill=(88, 196, 255, 50))
    draw.rounded_rectangle((70, 64, THUMBNAIL_WIDTH - 70, THUMBNAIL_HEIGHT - 64), radius=42, outline=(255, 255, 255, 26), width=3)
    return image


def _overlay_source_image(image: Image.Image, source_image: Image.Image) -> Image.Image:
    fitted = ImageOps.fit(source_image.convert("RGB"), (THUMBNAIL_WIDTH, THUMBNAIL_HEIGHT), Image.Resampling.LANCZOS, centering=(0.5, 0.42))
    overlay = Image.new("RGBA", (THUMBNAIL_WIDTH, THUMBNAIL_HEIGHT), (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay, "RGBA")
    draw.rectangle((0, 0, int(THUMBNAIL_WIDTH * 0.58), THUMBNAIL_HEIGHT), fill=(8, 12, 22, 190))
    draw.rectangle((0, THUMBNAIL_HEIGHT - 120, THUMBNAIL_WIDTH, THUMBNAIL_HEIGHT), fill=(4, 8, 16, 120))
    draw.rounded_rectangle((96, 78, 396, 136), radius=18, fill=(255, 183, 3, 255))
    draw.rounded_rectangle((96, 78, 396, 136), radius=18, outline=(255, 255, 255, 120), width=2)
    return Image.alpha_composite(fitted.convert("RGBA"), overlay)


def _draw_title_block(image: Image.Image, subject: str, seo_package: dict) -> None:
    draw = ImageDraw.Draw(image, "RGBA")
    brand_font = _resolve_font(22, bold=True)
    title_font = _resolve_font(64, bold=True)
    subtitle_font = _resolve_font(28, bold=False)
    footer_font = _resolve_font(20, bold=False)

    draw.text((122, 96), "MINIATURE AUTOMATIQUE", font=brand_font, fill=(16, 24, 36))

    title = coerce_text(seo_package.get("title"), subject)
    title_lines = _wrap_text(draw, title, title_font, 760)
    title_y = 180
    for line in title_lines[:4]:
        draw.text((122, title_y), line, font=title_font, fill=(248, 250, 252))
        _, height = _measure_text(draw, line, title_font)
        title_y += height + 8

    subtitle = coerce_text(seo_package.get("primary_keyword") or subject, subject)
    subtitle_y = title_y + 18
    _draw_wrapped_text(draw, subtitle, subtitle_font, 122, subtitle_y, 760, (225, 232, 240))

    footer = "YouTube AI Studio"
    footer_width, footer_height = _measure_text(draw, footer, footer_font)
    draw.rounded_rectangle(
        (THUMBNAIL_WIDTH - footer_width - 150, THUMBNAIL_HEIGHT - 102, THUMBNAIL_WIDTH - 86, THUMBNAIL_HEIGHT - 52),
        radius=18,
        fill=(255, 183, 3, 255),
    )
    draw.text((THUMBNAIL_WIDTH - footer_width - 126, THUMBNAIL_HEIGHT - 92), footer, font=footer_font, fill=(16, 24, 36))


def _create_fallback_thumbnail(subject: str, seo_package: dict) -> Image.Image:
    return _create_background().convert("RGB")


def generate_thumbnail_package(
    subject: str,
    seo_package: dict,
    visual_package: dict,
    artifact_dir: Path,
) -> dict:
    artifact_dir = ensure_directory(Path(artifact_dir))
    thumbnail_dir = ensure_directory(artifact_dir / "thumbnail_assets")
    thumbnail_path = thumbnail_dir / "thumbnail.png"

    source_image_path, source_image_provider = _select_source_asset(visual_package)
    if source_image_path is not None:
        with Image.open(source_image_path) as source_image:
            base_image = _overlay_source_image(_create_background(), source_image)
        provider = "thumbnail_composite"
    else:
        base_image = _create_fallback_thumbnail(subject, seo_package)
        provider = "thumbnail_placeholder"

    _draw_title_block(base_image, subject, seo_package)
    base_image.convert("RGB").save(thumbnail_path)

    manifest = {
        "status": "generated",
        "provider": provider,
        "subject": subject,
        "title": coerce_text(seo_package.get("title"), subject),
        "subtitle": coerce_text(seo_package.get("primary_keyword") or subject, subject),
        "thumbnail_text": coerce_text(seo_package.get("title"), subject),
        "thumbnail_path": str(thumbnail_path),
        "source_image_path": str(source_image_path) if source_image_path else None,
        "source_image_provider": source_image_provider,
        "output_size": {"width": THUMBNAIL_WIDTH, "height": THUMBNAIL_HEIGHT},
        "notes": "Thumbnail composed automatically from the first available visual asset.",
    }
    manifest_path = write_json(thumbnail_dir / "thumbnail_manifest.json", manifest)
    return {
        **manifest,
        "artifact_path": str(thumbnail_path),
        "manifest_path": str(manifest_path),
    }
