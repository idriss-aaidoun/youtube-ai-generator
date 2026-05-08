import os
from PIL import Image, ImageDraw, ImageFont, ImageFilter, ImageEnhance
import textwrap

ASSETS_DIR = os.getenv("ASSETS_DIR", "/app/assets")


def generate_thumbnail(title: str, output_path: str, background_image: str = None) -> str:
    width, height = 1280, 720

    if background_image and os.path.exists(background_image):
        img = Image.open(background_image).convert("RGB")
        img = img.resize((width, height), Image.LANCZOS)
        img = ImageEnhance.Brightness(img).enhance(0.4)
        img = img.filter(ImageFilter.GaussianBlur(radius=3))
    else:
        img = Image.new("RGB", (width, height))
        draw_bg = ImageDraw.Draw(img)
        for y in range(height):
            ratio = y / height
            r = int(10 + 30 * ratio)
            g = int(20 + 40 * ratio)
            b = int(60 + 80 * ratio)
            draw_bg.line([(0, y), (width, y)], fill=(r, g, b))

    overlay = Image.new("RGBA", (width, height), (0, 0, 0, 120))
    img = img.convert("RGBA")
    img = Image.alpha_composite(img, overlay)
    img = img.convert("RGB")

    draw = ImageDraw.Draw(img)

    accent_height = 8
    for x in range(width):
        ratio = x / width
        r = int(0 + 100 * ratio)
        g = int(150 - 50 * ratio)
        b = int(255 - 100 * ratio)
        draw.line([(x, 0), (x, accent_height)], fill=(r, g, b))
        draw.line([(x, height - accent_height), (x, height)], fill=(r, g, b))

    try:
        title_font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 80)
        sub_font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 45)
    except Exception:
        title_font = ImageFont.load_default()
        sub_font = title_font

    title_upper = title.upper()
    wrapped = textwrap.wrap(title_upper, width=22)

    total_h = len(wrapped) * 90
    start_y = (height - total_h) // 2 - 20

    for i, line in enumerate(wrapped):
        bbox = draw.textbbox((0, 0), line, font=title_font)
        text_w = bbox[2] - bbox[0]
        x = (width - text_w) // 2
        y = start_y + i * 92

        for dx in [-3, -2, 0, 2, 3]:
            for dy in [-3, -2, 0, 2, 3]:
                if dx != 0 or dy != 0:
                    draw.text((x + dx, y + dy), line, fill=(0, 0, 0), font=title_font)

        draw.text((x, y), line, fill=(255, 255, 255), font=title_font)

    badge_text = "REGARDEZ MAINTENANT"
    bbox = draw.textbbox((0, 0), badge_text, font=sub_font)
    bw = bbox[2] - bbox[0] + 40
    bh = bbox[3] - bbox[1] + 20
    bx = (width - bw) // 2
    by = start_y + total_h + 30

    draw.rectangle([bx, by, bx + bw, by + bh], fill=(220, 50, 50))
    draw.text((bx + 20, by + 10), badge_text, fill=(255, 255, 255), font=sub_font)

    img.save(output_path, "JPEG", quality=92)
    return output_path
