from __future__ import annotations

import json
import os
import urllib.error
import urllib.request
from collections.abc import Mapping, Sequence
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

from app.utils import clamp_int, coerce_text, ensure_directory, write_json


DEFAULT_HUGGINGFACE_IMAGE_MODEL = "stabilityai/stable-diffusion-xl-base-1.0"
DEFAULT_IMAGE_TIMEOUT_SECONDS = 120
DEFAULT_GUIDANCE_SCALE = 7.5
DEFAULT_NEGATIVE_PROMPT = "blurry, low quality, distorted, watermark, text, logo, extra fingers, deformed"


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


def _font_candidates(bold: bool) -> list[Path]:
    windir = Path(os.environ.get("WINDIR", r"C:\Windows"))
    candidates = [
        windir / "Fonts" / ("arialbd.ttf" if bold else "arial.ttf"),
        windir / "Fonts" / ("segoeuib.ttf" if bold else "segoeui.ttf"),
        windir / "Fonts" / ("calibrib.ttf" if bold else "calibri.ttf"),
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
        test_line = f"{current_line} {word}"
        test_width, _ = _measure_text(draw, test_line, font)
        if test_width <= max_width:
            current_line = test_line
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
    spacing = line_spacing if line_spacing is not None else max(6, int(getattr(font, "size", 16) * 0.35))
    cursor_y = y

    for line in lines:
        draw.text((x, cursor_y), line, font=font, fill=fill)
        _, height = _measure_text(draw, line, font)
        cursor_y += height + spacing

    return cursor_y - y


def _build_prompt(subject: str, scene: dict, idea_package: dict, script_package: dict) -> str:
    section_summary = coerce_text(scene.get("caption") or scene.get("summary"), "")
    section_body = coerce_text(scene.get("visual_prompt"), "")
    keywords = ", ".join(coerce_text(keyword, "") for keyword in idea_package.get("keywords", [])[:5] if coerce_text(keyword, ""))
    section_title = coerce_text(scene.get("title"), "Scene")
    scene_index = int(scene.get("scene_number") or 1) - 1
    sections = script_package.get("sections") or []
    script_focus = ""
    if 0 <= scene_index < len(sections):
        script_focus = coerce_text(sections[scene_index].get("body"), "")
        script_focus = script_focus.split("\n", 1)[0]

    return "\n".join(
        [
            "Professional YouTube thumbnail-style cinematic illustration, no text, no watermark.",
            f"Topic: {subject}",
            f"Scene: {section_title}",
            f"Summary: {section_summary}",
            f"Visual direction: {section_body}",
            f"Keywords: {keywords}",
            f"Script focus: {script_focus}",
            "Wide composition, clean subject hierarchy, modern lighting, high detail, crisp colors.",
        ]
    )


def _build_negative_prompt(settings: Mapping[str, object] | None) -> str:
    return _settings_value(settings, "HUGGINGFACE_IMAGE_NEGATIVE_PROMPT") or DEFAULT_NEGATIVE_PROMPT


def _call_huggingface_image(
    prompt: str,
    model_name: str,
    token: str,
    timeout_seconds: int,
    guidance_scale: float,
    negative_prompt: str,
) -> bytes:
    payload = {
        "inputs": prompt,
        "parameters": {
            "guidance_scale": guidance_scale,
            "negative_prompt": negative_prompt,
            "num_inference_steps": 30,
            "width": 1024,
            "height": 1024,
        },
        "options": {"wait_for_model": True},
    }
    request = urllib.request.Request(
        f"https://api-inference.huggingface.co/models/{model_name}",
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
            "Accept": "image/png",
        },
        method="POST",
    )

    try:
        with urllib.request.urlopen(request, timeout=timeout_seconds) as response:
            content_type = response.headers.get("Content-Type", "")
            body = response.read()
    except urllib.error.HTTPError as exc:
        error_body = exc.read().decode("utf-8", errors="replace") if exc.fp else ""
        raise RuntimeError(f"Hugging Face image API error ({exc.code}): {error_body or exc.reason}") from exc
    except urllib.error.URLError as exc:
        raise RuntimeError(f"Hugging Face image API request failed: {exc.reason}") from exc

    if content_type.startswith("image/"):
        return body

    if content_type.startswith("application/json"):
        try:
            parsed = json.loads(body.decode("utf-8"))
        except json.JSONDecodeError as exc:
            raise RuntimeError("Hugging Face image response was JSON but could not be parsed") from exc

        if isinstance(parsed, dict) and parsed.get("error"):
            raise RuntimeError(str(parsed["error"]))
        if isinstance(parsed, list) and parsed:
            first_item = parsed[0]
            if isinstance(first_item, dict) and first_item.get("error"):
                raise RuntimeError(str(first_item["error"]))

        raise RuntimeError("Hugging Face image model returned JSON instead of image bytes")

    raise RuntimeError(f"Unexpected Hugging Face image response type: {content_type or 'unknown'}")


def _gradient_background(width: int, height: int, top_color: tuple[int, int, int], bottom_color: tuple[int, int, int]) -> Image.Image:
    image = Image.new("RGB", (width, height), top_color)
    draw = ImageDraw.Draw(image)
    for row in range(height):
        blend = row / max(1, height - 1)
        color = tuple(
            int(top_color[index] * (1 - blend) + bottom_color[index] * blend)
            for index in range(3)
        )
        draw.line((0, row, width, row), fill=color)
    return image


def _create_placeholder_image(scene: dict, subject: str, output_path: Path) -> Path:
    width, height = 1280, 720
    background = _gradient_background(width, height, (16, 24, 46), (9, 12, 22)).convert("RGBA")
    draw = ImageDraw.Draw(background, "RGBA")

    accent = (255, 183, 3)
    secondary = (0, 209, 178)
    draw.ellipse((-140, -120, 380, 400), fill=(accent[0], accent[1], accent[2], 70))
    draw.ellipse((900, 80, 1480, 660), fill=(secondary[0], secondary[1], secondary[2], 60))
    draw.rounded_rectangle((90, 150, width - 90, height - 140), radius=36, fill=(8, 14, 26), outline=(255, 255, 255))

    title_font = _resolve_font(42, bold=True)
    body_font = _resolve_font(24, bold=False)
    small_font = _resolve_font(18, bold=True)

    scene_title = coerce_text(scene.get("title"), "Scene")
    caption = coerce_text(scene.get("caption") or scene.get("summary"), "")
    prompt = coerce_text(scene.get("visual_prompt"), "")
    subject_label = coerce_text(subject, "YouTube AI Studio")

    draw.rounded_rectangle((130, 190, 320, 242), radius=18, fill=accent)
    draw.text((150, 206), f"SCÈNE {int(scene.get('scene_number') or 1):02d}", font=small_font, fill=(16, 24, 46))

    draw.text((130, 285), scene_title, font=title_font, fill=(248, 250, 252))
    cursor_y = 350
    cursor_y += _draw_wrapped_text(draw, caption, body_font, 130, cursor_y, width - 260, (220, 229, 241))
    cursor_y += 14
    cursor_y += _draw_wrapped_text(draw, prompt, body_font, 130, cursor_y, width - 260, (173, 185, 204))

    footer_text = f"{subject_label} | image fallback local"
    draw.text((130, height - 92), footer_text, font=body_font, fill=(197, 207, 219))

    ensure_directory(output_path.parent)
    background.convert("RGB").save(output_path)
    return output_path


def _save_image_bytes(image_bytes: bytes, output_path: Path) -> Path:
    ensure_directory(output_path.parent)
    output_path.write_bytes(image_bytes)
    return output_path


def generate_visual_package(
    subject: str,
    idea_package: dict,
    script_package: dict,
    artifact_dir: Path,
    settings: Mapping[str, object] | None = None,
) -> dict:
    artifact_dir = ensure_directory(Path(artifact_dir))
    scenes = []
    for index, section in enumerate(script_package["sections"], start=1):
        duration_seconds = 12 if index == 1 else 18
        scenes.append(
            {
                "scene_number": index,
                "duration_seconds": duration_seconds,
                "title": section["heading"],
                "caption": section["summary"],
                "summary": section["summary"],
                "visual_prompt": (
                    f"Visuel propre et pédagogique montrant {section['summary'].lower()} "
                    f"autour du sujet {subject}."
                ),
            }
        )

    if not scenes:
        scenes = [
            {
                "scene_number": 1,
                "duration_seconds": 15,
                "title": "Intro",
                "caption": f"Introduction à {subject}",
                "summary": f"Introduction à {subject}",
                "visual_prompt": f"Visuel d'introduction pour {subject}.",
            }
        ]

    storyboard = {
        "scene_count": len(scenes),
        "total_duration_seconds": sum(scene["duration_seconds"] for scene in scenes),
        "keywords": idea_package.get("keywords", []),
        "scenes": scenes,
    }
    storyboard_path = write_json(artifact_dir / "storyboard.json", storyboard)

    hf_token = _settings_value(settings, "HUGGINGFACE_API_TOKEN", "HF_TOKEN")
    hf_model = _settings_value(settings, "HUGGINGFACE_IMAGE_MODEL") or DEFAULT_HUGGINGFACE_IMAGE_MODEL
    timeout_seconds = _settings_int(settings, "HUGGINGFACE_IMAGE_TIMEOUT_SECONDS", DEFAULT_IMAGE_TIMEOUT_SECONDS, 10, 600)
    guidance_scale = _settings_float(settings, "HUGGINGFACE_IMAGE_GUIDANCE_SCALE", DEFAULT_GUIDANCE_SCALE, 1.0, 20.0)
    negative_prompt = _build_negative_prompt(settings)
    image_assets_dir = ensure_directory(artifact_dir / "visual_assets")

    image_assets = []
    fallback_reason = None
    generated_by_hf = bool(hf_token)

    for scene in scenes:
        scene_number = int(scene.get("scene_number", len(image_assets) + 1))
        image_filename = f"scene_{scene_number:02d}.png"
        image_path = image_assets_dir / image_filename
        image_prompt = _build_prompt(subject, scene, idea_package, script_package)
        scene_source = "local_placeholder"

        if hf_token and fallback_reason is None:
            try:
                image_bytes = _call_huggingface_image(
                    prompt=f"{image_prompt}\nNegative prompt: {negative_prompt}",
                    model_name=hf_model,
                    token=hf_token,
                    timeout_seconds=timeout_seconds,
                    guidance_scale=guidance_scale,
                    negative_prompt=negative_prompt,
                )
                _save_image_bytes(image_bytes, image_path)
                scene_source = "huggingface_image_api"
            except Exception as exc:
                fallback_reason = str(exc)
                generated_by_hf = False
                _create_placeholder_image(scene, subject, image_path)
        else:
            _create_placeholder_image(scene, subject, image_path)

        image_assets.append(
            {
                "scene_number": scene_number,
                "image_path": str(image_path),
                "source": scene_source,
                "prompt": image_prompt,
                "title": scene.get("title"),
                "caption": scene.get("caption"),
            }
        )

    provider = "huggingface_image_api" if hf_token and fallback_reason is None and generated_by_hf else "local_placeholder"
    status = "generated" if provider == "huggingface_image_api" else "planned"

    return {
        "status": status,
        "provider": provider,
        "artifact_path": str(storyboard_path),
        "storyboard_path": str(storyboard_path),
        "scene_count": len(scenes),
        "total_duration_seconds": storyboard["total_duration_seconds"],
        "keywords": storyboard["keywords"],
        "scenes": [
            {
                **scene,
                "image_path": image_assets[index]["image_path"],
                "image_source": image_assets[index]["source"],
            }
            for index, scene in enumerate(scenes)
        ],
        "image_assets_dir": str(image_assets_dir),
        "image_assets": image_assets,
        "image_model": hf_model if hf_token else None,
        "negative_prompt": negative_prompt,
        "fallback_reason": fallback_reason,
    }
