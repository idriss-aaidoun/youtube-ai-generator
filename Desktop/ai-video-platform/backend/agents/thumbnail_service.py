"""
Thumbnail Service — Pillow
Rôle : Génère la miniature YouTube (1280x720)
Fonction : image de fond + texte accrocheur + contraste élevé + badge
"""
import os
import textwrap
from PIL import Image, ImageDraw, ImageFont, ImageFilter, ImageEnhance


def run(title: str, thumbnail_text: str, output_path: str, background_image: str = None) -> str:
    """
    Génère une miniature YouTube professionnelle.
    - Image de fond (floutée + assombrie si disponible)
    - Texte principal en blanc gras
    - Badge rouge "REGARDEZ"
    - Contraste élevé pour le CTR
    """
    w, h = 1280, 720

    if background_image and os.path.exists(background_image):
        img = Image.open(background_image).convert("RGB").resize((w, h), Image.LANCZOS)
        img = ImageEnhance.Brightness(img).enhance(0.35)
        img = img.filter(ImageFilter.GaussianBlur(radius=5))
    else:
        img = Image.new("RGB", (w, h))
        draw_bg = ImageDraw.Draw(img)
        for y in range(h):
            r = int(10 + 20 * y / h)
            g = int(15 + 30 * y / h)
            b = int(60 + 80 * y / h)
            draw_bg.line([(0, y), (w, y)], fill=(r, g, b))

    overlay = Image.new("RGBA", (w, h), (0, 0, 0, 100))
    img = Image.alpha_composite(img.convert("RGBA"), overlay).convert("RGB")
    draw = ImageDraw.Draw(img)

    for x in range(w):
        ratio = x / w
        r = int(220 * ratio)
        g = int(50 + 100 * (1 - ratio))
        b = int(255 * (1 - ratio))
        draw.line([(x, 0), (x, 7)], fill=(r, g, b))
        draw.line([(x, h - 7), (x, h)], fill=(r, g, b))

    try:
        big_font = ImageFont.truetype(
            "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 82)
        sub_font = ImageFont.truetype(
            "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 42)
    except Exception:
        big_font = ImageFont.load_default()
        sub_font = big_font

    display = (thumbnail_text or title or "VIDÉO IA").upper()
    wrapped = textwrap.wrap(display, width=20)
    line_h = 94
    total_h = len(wrapped) * line_h
    start_y = (h - total_h) // 2 - 30

    for i, line in enumerate(wrapped):
        bbox = draw.textbbox((0, 0), line, font=big_font)
        x = (w - (bbox[2] - bbox[0])) // 2
        y = start_y + i * line_h
        for dx in range(-3, 4):
            for dy in range(-3, 4):
                if dx or dy:
                    draw.text((x + dx, y + dy), line, fill=(0, 0, 0), font=big_font)
        draw.text((x, y), line, fill=(255, 255, 255), font=big_font)

    badge = "▶ REGARDEZ"
    bbox = draw.textbbox((0, 0), badge, font=sub_font)
    bw = bbox[2] - bbox[0] + 40
    bh = bbox[3] - bbox[1] + 18
    bx = (w - bw) // 2
    by = start_y + total_h + 20
    draw.rounded_rectangle([bx, by, bx + bw, by + bh], radius=8, fill=(210, 40, 40))
    draw.text((bx + 20, by + 9), badge, fill=(255, 255, 255), font=sub_font)

    os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)
    img.save(output_path, "JPEG", quality=93)
    return output_path
