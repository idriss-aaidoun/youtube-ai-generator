import os
import httpx
import asyncio
from PIL import Image, ImageDraw, ImageFont
import random

PEXELS_API_KEY = os.getenv("PEXELS_API_KEY", "")
ASSETS_DIR = os.getenv("ASSETS_DIR", "/app/assets")

BACKGROUND_COLORS = [
    [(20, 30, 48), (36, 59, 85)],
    [(11, 12, 16), (22, 24, 35)],
    [(15, 32, 39), (32, 58, 67)],
    [(24, 24, 24), (44, 62, 80)],
    [(30, 30, 30), (60, 60, 80)],
]


async def fetch_images_for_sections(sections: list, output_dir: str, count: int = None) -> list[str]:
    if count is None:
        count = len(sections)

    paths = []
    for i, section in enumerate(sections[:count]):
        keyword = section.get("title", f"section {i+1}")
        img_path = os.path.join(output_dir, f"image_{i:02d}.jpg")

        if PEXELS_API_KEY:
            try:
                downloaded = await _fetch_from_pexels(keyword, img_path)
                if downloaded:
                    paths.append(img_path)
                    continue
            except Exception:
                pass

        _create_placeholder_image(keyword, img_path, i)
        paths.append(img_path)

    while len(paths) < max(count, 3):
        idx = len(paths)
        img_path = os.path.join(output_dir, f"image_{idx:02d}.jpg")
        _create_placeholder_image(f"Slide {idx+1}", img_path, idx)
        paths.append(img_path)

    return paths


async def _fetch_from_pexels(query: str, output_path: str) -> bool:
    headers = {"Authorization": PEXELS_API_KEY}
    params = {"query": query, "per_page": 3, "orientation": "landscape"}

    async with httpx.AsyncClient(timeout=15.0) as client:
        response = await client.get(
            "https://api.pexels.com/v1/search",
            headers=headers,
            params=params
        )
        if response.status_code != 200:
            return False
        data = response.json()
        photos = data.get("photos", [])
        if not photos:
            return False

        photo = random.choice(photos)
        img_url = photo["src"]["large"]
        img_response = await client.get(img_url)
        if img_response.status_code != 200:
            return False

        with open(output_path, "wb") as f:
            f.write(img_response.content)
        return True


def _create_placeholder_image(text: str, output_path: str, index: int = 0):
    width, height = 1920, 1080
    img = Image.new("RGB", (width, height))
    draw = ImageDraw.Draw(img)

    colors = BACKGROUND_COLORS[index % len(BACKGROUND_COLORS)]
    for y in range(height):
        ratio = y / height
        r = int(colors[0][0] + (colors[1][0] - colors[0][0]) * ratio)
        g = int(colors[0][1] + (colors[1][1] - colors[0][1]) * ratio)
        b = int(colors[0][2] + (colors[1][2] - colors[0][2]) * ratio)
        draw.line([(0, y), (width, y)], fill=(r, g, b))

    for i in range(20):
        x1 = random.randint(0, width)
        y1 = random.randint(0, height)
        x2 = x1 + random.randint(100, 500)
        y2 = y1 + random.randint(2, 6)
        alpha = random.randint(20, 60)
        overlay = Image.new("RGBA", img.size, (0, 0, 0, 0))
        overlay_draw = ImageDraw.Draw(overlay)
        overlay_draw.line([(x1, y1), (x2, y2)], fill=(255, 255, 255, alpha), width=1)

    font_size = 72
    try:
        font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", font_size)
        small_font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 36)
    except Exception:
        font = ImageFont.load_default()
        small_font = font

    display_text = text.upper()[:40]

    bbox = draw.textbbox((0, 0), display_text, font=font)
    text_w = bbox[2] - bbox[0]
    text_h = bbox[3] - bbox[1]
    x = (width - text_w) // 2
    y = (height - text_h) // 2

    for dx in range(-3, 4):
        for dy in range(-3, 4):
            if dx != 0 or dy != 0:
                draw.text((x + dx, y + dy), display_text, fill=(0, 0, 0, 100), font=font)
    draw.text((x, y), display_text, fill=(255, 255, 255), font=font)

    line_y = y + text_h + 20
    line_x1 = width // 2 - 100
    line_x2 = width // 2 + 100
    draw.line([(line_x1, line_y), (line_x2, line_y)], fill=(100, 180, 255), width=3)

    img.save(output_path, "JPEG", quality=90)
