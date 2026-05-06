from __future__ import annotations

import os
import subprocess
from collections.abc import Mapping, Sequence
from pathlib import Path

import imageio.v2 as imageio
import imageio_ffmpeg
import numpy as np
from PIL import Image, ImageDraw, ImageFont

from app.utils import clamp_int, coerce_text, ensure_directory, write_json


DEFAULT_WIDTH = 1280
DEFAULT_HEIGHT = 720
DEFAULT_FPS = 24
DEFAULT_TRANSITION_SECONDS = 0.75
TEST_WIDTH = 640
TEST_HEIGHT = 360
TEST_FPS = 8
TEST_TRANSITION_SECONDS = 0.25

PALETTES = [
    {"top": (18, 28, 62), "bottom": (10, 16, 30), "accent": (255, 183, 3), "secondary": (0, 209, 178)},
    {"top": (14, 44, 72), "bottom": (8, 16, 26), "accent": (88, 196, 255), "secondary": (255, 126, 103)},
    {"top": (26, 18, 54), "bottom": (11, 10, 24), "accent": (161, 255, 94), "secondary": (255, 196, 61)},
    {"top": (41, 24, 66), "bottom": (17, 12, 31), "accent": (255, 111, 145), "secondary": (115, 210, 255)},
]


def _setting_text(settings: Mapping[str, object] | None, *names: str) -> str:
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


def _setting_int(
    settings: Mapping[str, object] | None,
    name: str,
    default: int,
    minimum: int,
    maximum: int,
) -> int:
    return clamp_int(_setting_text(settings, name), default, minimum=minimum, maximum=maximum)


def _setting_float(
    settings: Mapping[str, object] | None,
    name: str,
    default: float,
    minimum: float,
    maximum: float,
) -> float:
    raw_value = _setting_text(settings, name)
    if not raw_value:
        return default

    try:
        number = float(raw_value)
    except ValueError:
        return default

    return max(minimum, min(maximum, number))


def _setting_bool(settings: Mapping[str, object] | None, name: str, default: bool) -> bool:
    raw_value = _setting_text(settings, name)
    if not raw_value:
        return default

    return raw_value.lower() in {"1", "true", "yes", "on"}


def _render_profile(settings: Mapping[str, object] | None) -> dict:
    testing_mode = _setting_bool(settings, "TESTING", False)
    width = _setting_int(
        settings,
        "VIDEO_RENDER_WIDTH" if not testing_mode else "VIDEO_RENDER_TEST_WIDTH",
        TEST_WIDTH if testing_mode else DEFAULT_WIDTH,
        minimum=320,
        maximum=3840,
    )
    height = _setting_int(
        settings,
        "VIDEO_RENDER_HEIGHT" if not testing_mode else "VIDEO_RENDER_TEST_HEIGHT",
        TEST_HEIGHT if testing_mode else DEFAULT_HEIGHT,
        minimum=240,
        maximum=2160,
    )
    fps = _setting_int(
        settings,
        "VIDEO_RENDER_FPS" if not testing_mode else "VIDEO_RENDER_TEST_FPS",
        TEST_FPS if testing_mode else DEFAULT_FPS,
        minimum=2,
        maximum=60,
    )
    transition_seconds = _setting_float(
        settings,
        "VIDEO_RENDER_TRANSITION_SECONDS"
        if not testing_mode
        else "VIDEO_RENDER_TEST_TRANSITION_SECONDS",
        TEST_TRANSITION_SECONDS if testing_mode else DEFAULT_TRANSITION_SECONDS,
        minimum=0.0,
        maximum=3.0,
    )
    return {
        "testing_mode": testing_mode,
        "width": width,
        "height": height,
        "fps": fps,
        "transition_seconds": transition_seconds,
    }


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
    bbox = draw.textbbox((0, 0), text, font=font)
    return bbox[2] - bbox[0], bbox[3] - bbox[1]


def _wrap_text(draw: ImageDraw.ImageDraw, text: str, font: ImageFont.ImageFont, max_width: int) -> list[str]:
    words = text.split()
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
    fill: tuple[int, int, int] | tuple[int, int, int, int],
    line_spacing: int | None = None,
) -> int:
    lines = _wrap_text(draw, coerce_text(text, ""), font, max_width)
    spacing = line_spacing if line_spacing is not None else max(6, int(getattr(font, "size", 16) * 0.35))
    cursor_y = y

    for line in lines:
        draw.text((x, cursor_y), line, font=font, fill=fill)
        _, height = _measure_text(draw, line, font)
        cursor_y += height + spacing

    return cursor_y - y


def _palette(index: int) -> dict:
    return PALETTES[index % len(PALETTES)]


def _vertical_gradient(width: int, height: int, top_color: tuple[int, int, int], bottom_color: tuple[int, int, int]) -> Image.Image:
    top = Image.new("RGBA", (width, height), top_color + (255,))
    bottom = Image.new("RGBA", (width, height), bottom_color + (255,))
    mask_array = np.linspace(0, 255, height, dtype=np.uint8)
    mask = Image.fromarray(np.repeat(mask_array[:, None], width, axis=1)).convert("L")
    return Image.composite(bottom, top, mask)


def _add_ambient_shapes(image: Image.Image, accent: tuple[int, int, int], secondary: tuple[int, int, int], scene_index: int) -> Image.Image:
    overlay = Image.new("RGBA", image.size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay)
    width, height = image.size

    circles = [
        (int(width * 0.8), int(height * 0.18), int(min(width, height) * 0.18), accent, 30),
        (int(width * 0.1), int(height * 0.25), int(min(width, height) * 0.14), secondary, 24),
        (int(width * 0.88), int(height * 0.74), int(min(width, height) * 0.12), accent, 20),
    ]
    for x, y, radius, color, alpha in circles:
        fill = color + (alpha - scene_index % 8,)
        draw.ellipse((x - radius, y - radius, x + radius, y + radius), fill=fill)

    return Image.alpha_composite(image, overlay)


def _allocate_durations(weights: Sequence[int], total_seconds: float) -> list[float]:
    if not weights:
        return [max(1.0, total_seconds)]

    safe_weights = [max(1, int(weight)) for weight in weights]
    total_weight = sum(safe_weights) or len(safe_weights)
    raw = [total_seconds * weight / total_weight for weight in safe_weights]

    if len(raw) == 1:
        return [max(1.0, total_seconds)]

    allocated = raw[:-1]
    last_value = max(1.0, total_seconds - sum(allocated))
    allocated.append(last_value)

    # Keep the total stable after rounding artifacts.
    difference = total_seconds - sum(allocated)
    allocated[-1] = max(1.0, allocated[-1] + difference)
    return allocated


def _format_srt_timestamp(total_seconds: float) -> str:
    total_milliseconds = max(0, int(round(total_seconds * 1000)))
    hours, remainder = divmod(total_milliseconds, 3_600_000)
    minutes, remainder = divmod(remainder, 60_000)
    seconds, milliseconds = divmod(remainder, 1000)
    return f"{hours:02d}:{minutes:02d}:{seconds:02d},{milliseconds:03d}"


def _subtitle_text(scene: Mapping[str, object]) -> str:
    caption = coerce_text(scene.get("caption") or scene.get("summary"), "")
    title = coerce_text(scene.get("title"), "")
    if caption and title and caption != title:
        return f"{title}\n{caption}"
    return caption or title


def _write_subtitles_file(subtitle_path: Path, scenes: Sequence[Mapping[str, object]], durations: Sequence[float], transition_seconds: float) -> Path:
    blocks: list[str] = []
    elapsed_seconds = 0.0

    for index, scene in enumerate(scenes, start=1):
        scene_duration = max(0.5, float(durations[index - 1] if index - 1 < len(durations) else 1.0))
        text = _subtitle_text(scene)
        if not text:
            continue

        start_timestamp = _format_srt_timestamp(elapsed_seconds)
        end_timestamp = _format_srt_timestamp(elapsed_seconds + scene_duration)
        blocks.append(f"{index}\n{start_timestamp} --> {end_timestamp}\n{text}")

        elapsed_seconds += scene_duration
        if index < len(scenes):
            elapsed_seconds += max(0.0, float(transition_seconds))

    subtitle_path.write_text("\n\n".join(blocks), encoding="utf-8")
    return subtitle_path


def _build_scene_image(
    *,
    subject: str,
    scene: dict,
    scene_index: int,
    total_scenes: int,
    width: int,
    height: int,
    script_package: dict,
    keywords: Sequence[str],
) -> Image.Image:
    palette = _palette(scene_index)
    background = _vertical_gradient(width, height, palette["top"], palette["bottom"])
    background = _add_ambient_shapes(background, palette["accent"], palette["secondary"], scene_index)
    image = background.convert("RGBA")
    draw = ImageDraw.Draw(image)

    title_font = _resolve_font(max(28, width // 24), bold=True)
    body_font = _resolve_font(max(18, width // 48), bold=False)
    chip_font = _resolve_font(max(16, width // 62), bold=True)
    small_font = _resolve_font(max(14, width // 72), bold=False)

    panel_left = int(width * 0.08)
    panel_top = int(height * 0.26)
    panel_right = int(width * 0.92)
    panel_bottom = int(height * 0.84)
    draw.rounded_rectangle(
        (panel_left, panel_top, panel_right, panel_bottom),
        radius=32,
        fill=(7, 12, 22, 200),
        outline=palette["accent"] + (90,),
        width=3,
    )

    chip_box = (panel_left + 28, panel_top + 22, panel_left + 225, panel_top + 70)
    draw.rounded_rectangle(chip_box, radius=16, fill=palette["accent"] + (255,))
    scene_label = f"SCÈNE {scene_index:02d} / {total_scenes:02d}"
    draw.text((chip_box[0] + 18, chip_box[1] + 11), scene_label, font=chip_font, fill=(12, 16, 28))

    subject_label = coerce_text(subject, "YouTube AI Studio")
    subject_width, subject_height = _measure_text(draw, subject_label, small_font)
    draw.text(
        (panel_right - subject_width - 28, panel_top + 34 - subject_height // 2),
        subject_label,
        font=small_font,
        fill=(220, 229, 241),
    )

    title = coerce_text(scene.get("title"), scene.get("heading", "Section"))
    caption = coerce_text(scene.get("caption"), "")
    prompt = coerce_text(scene.get("visual_prompt"), "")
    section_text = coerce_text(script_package.get("sections", [{}])[min(scene_index - 1, len(script_package.get("sections", [])) - 1)] .get("body") if script_package.get("sections") else "", "")

    content_x = panel_left + 34
    content_y = panel_top + 105
    max_text_width = panel_right - content_x - 40

    draw.text((content_x, content_y), title, font=title_font, fill=(248, 250, 252))
    title_height = _measure_text(draw, title, title_font)[1]
    content_y += title_height + 20

    content_y += _draw_wrapped_text(draw, caption, body_font, content_x, content_y, max_text_width, (225, 232, 240))
    content_y += 16
    content_y += _draw_wrapped_text(draw, prompt, body_font, content_x, content_y, max_text_width, (197, 214, 227))
    content_y += 16
    if section_text:
        excerpt = section_text.split("\n", 1)[0]
        content_y += _draw_wrapped_text(draw, excerpt, small_font, content_x, content_y, max_text_width, (161, 174, 193))

    keyword_row_y = panel_bottom - 108
    if keywords:
        current_x = content_x
        for keyword in list(keywords)[:4]:
            keyword_text = coerce_text(keyword, "")
            if not keyword_text:
                continue
            keyword_width, keyword_height = _measure_text(draw, keyword_text, small_font)
            pill_width = keyword_width + 30
            pill_height = keyword_height + 18
            draw.rounded_rectangle(
                (current_x, keyword_row_y, current_x + pill_width, keyword_row_y + pill_height),
                radius=12,
                fill=palette["secondary"] + (80,),
                outline=palette["secondary"] + (130,),
            )
            draw.text((current_x + 15, keyword_row_y + 9), keyword_text, font=small_font, fill=(248, 250, 252))
            current_x += pill_width + 12

    progress_left = content_x
    progress_top = panel_bottom - 38
    progress_right = panel_right - 34
    draw.rounded_rectangle(
        (progress_left, progress_top, progress_right, progress_top + 12),
        radius=6,
        fill=(255, 255, 255, 28),
    )
    progress_width = int((scene_index / max(total_scenes, 1)) * (progress_right - progress_left))
    draw.rounded_rectangle(
        (progress_left, progress_top, progress_left + progress_width, progress_top + 12),
        radius=6,
        fill=palette["accent"] + (240,),
    )

    footer_text = f"Storyboard automatique | {coerce_text(scene.get('summary'), scene.get('caption'),)}"
    footer_font = _resolve_font(max(14, width // 78), bold=False)
    draw.text((panel_left + 28, panel_bottom + 14), footer_text, font=footer_font, fill=(197, 207, 219))

    return image.convert("RGB")


def _frame_sequence(scene_images: Sequence[Image.Image], durations: Sequence[float], fps: int, transition_seconds: float):
    transition_frames = max(0, int(round(transition_seconds * fps))) if len(scene_images) > 1 else 0
    for index, image in enumerate(scene_images):
        hold_frames = max(1, int(round(durations[index] * fps)))
        frame_array = np.asarray(image)
        for _ in range(hold_frames):
            yield frame_array

        if index < len(scene_images) - 1 and transition_frames > 0:
            next_image = scene_images[index + 1]
            for step in range(1, transition_frames + 1):
                alpha = step / (transition_frames + 1)
                blended = Image.blend(image, next_image, alpha)
                yield np.asarray(blended)


def _write_video(video_path: Path, frames, fps: int) -> int:
    frame_count = 0
    with imageio.get_writer(
        str(video_path),
        fps=fps,
        codec="libx264",
        quality=8,
        macro_block_size=None,
        ffmpeg_log_level="error",
    ) as writer:
        for frame in frames:
            writer.append_data(frame)
            frame_count += 1
    return frame_count


def _mux_audio(video_path: Path, audio_path: Path, final_path: Path) -> None:
    ffmpeg_exe = imageio_ffmpeg.get_ffmpeg_exe()
    command = [
        ffmpeg_exe,
        "-y",
        "-i",
        str(video_path),
        "-i",
        str(audio_path),
        "-c:v",
        "copy",
        "-c:a",
        "aac",
        "-b:a",
        "192k",
        "-shortest",
        str(final_path),
    ]
    subprocess.run(command, check=True, capture_output=True, text=True)


def render_video_package(
    subject: str,
    script_package: dict,
    audio_package: dict,
    visual_package: dict,
    artifact_dir: Path,
    settings: Mapping[str, object] | None = None,
) -> dict:
    subject = coerce_text(subject, "Sujet sans titre")
    artifact_dir = ensure_directory(Path(artifact_dir))
    profile = _render_profile(settings)

    scenes = visual_package.get("scenes", []) if isinstance(visual_package, Mapping) else []
    if not scenes:
        scenes = [
            {
                "scene_number": 1,
                "duration_seconds": 6,
                "title": "Intro",
                "caption": f"Introduction à {subject}",
                "visual_prompt": f"Visuel d'introduction pour {subject}.",
            }
        ]

    keywords = visual_package.get("keywords", []) if isinstance(visual_package, Mapping) else []
    if not isinstance(keywords, Sequence):
        keywords = []

    audio_target_seconds = int(audio_package.get("estimated_duration_seconds") or visual_package.get("total_duration_seconds") or 0)
    if profile["testing_mode"]:
        audio_target_seconds = min(max(audio_target_seconds, 3), 5)
    else:
        audio_target_seconds = max(audio_target_seconds, len(scenes) * 4)

    transition_seconds = profile["transition_seconds"]
    max_transition_total = max(0.0, audio_target_seconds - len(scenes))
    if len(scenes) > 1 and transition_seconds * (len(scenes) - 1) > max_transition_total:
        transition_seconds = max(0.0, max_transition_total / (len(scenes) - 1))

    hold_total_seconds = max(float(len(scenes)), float(audio_target_seconds) - transition_seconds * max(len(scenes) - 1, 0))
    scene_weights = [int(scene.get("duration_seconds") or 1) for scene in scenes]
    scene_durations = _allocate_durations(scene_weights, hold_total_seconds)

    frames_dir = ensure_directory(artifact_dir / "rendered_frames")
    scene_images: list[Image.Image] = []
    scene_assets: list[dict] = []
    for index, scene in enumerate(scenes, start=1):
        source_label = coerce_text(
            scene.get("image_source"),
            "generated_image",
        )
        image = _build_scene_image(
            subject=subject,
            scene=scene,
            scene_index=index,
            total_scenes=len(scenes),
            width=profile["width"],
            height=profile["height"],
            script_package=script_package,
            keywords=keywords,
        )
        image_path = frames_dir / f"scene_{index:02d}.png"
        image.save(image_path)
        scene_images.append(image)
        scene_assets.append(
            {
                "scene_number": index,
                "image_path": str(image_path),
                "duration_seconds": scene_durations[index - 1],
                "title": coerce_text(scene.get("title"), f"Scene {index}"),
                "caption": coerce_text(scene.get("caption"), ""),
                "source": source_label,
            }
        )

    subtitle_dir = ensure_directory(artifact_dir / "subtitle_assets")
    subtitle_path = _write_subtitles_file(subtitle_dir / "subtitles.srt", scenes, scene_durations, transition_seconds)

    temp_video_path = artifact_dir / "rendered_video_silent.mp4"
    final_video_path = artifact_dir / "rendered_video.mp4"
    frame_count = _write_video(temp_video_path, _frame_sequence(scene_images, scene_durations, profile["fps"], transition_seconds), profile["fps"])

    source_audio_path = Path(coerce_text(audio_package.get("audio_file_path") or audio_package.get("artifact_path"), ""))
    audio_available = source_audio_path.exists() and source_audio_path.suffix.lower() in {".mp3", ".wav", ".m4a", ".aac", ".flac", ".ogg"}
    audio_muxed = False
    fallback_reason = None

    if audio_available:
        try:
            _mux_audio(temp_video_path, source_audio_path, final_video_path)
            audio_muxed = True
        except Exception as exc:
            fallback_reason = str(exc)
            temp_video_path.replace(final_video_path)
    else:
        temp_video_path.replace(final_video_path)

    if not final_video_path.exists() and temp_video_path.exists():
        temp_video_path.replace(final_video_path)

    manifest = {
        "status": "generated",
        "provider": "imageio_ffmpeg",
        "subject": subject,
        "scene_count": len(scenes),
        "frame_count": frame_count,
        "width": profile["width"],
        "height": profile["height"],
        "fps": profile["fps"],
        "transition_seconds": transition_seconds,
        "estimated_duration_seconds": round(sum(scene_durations) + transition_seconds * max(len(scenes) - 1, 0), 2),
        "video_file_path": str(final_video_path),
        "audio_file_path": str(source_audio_path) if audio_available else None,
        "audio_muxed": audio_muxed,
        "subtitle_path": str(subtitle_path),
        "scene_assets": scene_assets,
        "frame_dir": str(frames_dir),
        "fallback_reason": fallback_reason,
        "image_source_count": sum(1 for asset in scene_assets if asset.get("source") != "stylized_slide"),
    }
    manifest_path = write_json(artifact_dir / "render_manifest.json", manifest)
    return {
        **manifest,
        "artifact_path": str(final_video_path),
        "manifest_path": str(manifest_path),
        "video_path": str(final_video_path),
        "frames_dir": str(frames_dir),
        "subtitle_path": str(subtitle_path),
    }