"""
Agent 3 — Visual Agent
Rôle : Génère/récupère une image par scène du script
Stack : Stable Diffusion (optionnel) → Pexels API → Pillow (fallback amélioré)
"""
import os
import asyncio
import random
import textwrap
import httpx
from PIL import Image, ImageDraw, ImageFont, ImageFilter

from settings import settings

PALETTES = [
    [(8, 8, 35),   (20, 60, 150)],
    [(15, 5, 45),  (80, 20, 170)],
    [(5, 28, 45),  (5, 85, 65)],
    [(35, 8, 8),   (140, 20, 20)],
    [(10, 18, 38), (25, 35, 55)],
    [(8, 22, 8),   (18, 110, 50)],
    [(45, 25, 8),  (160, 75, 8)],
]

ACCENT_COLORS = [
    (100, 200, 255), (180, 120, 255), (80, 220, 180),
    (255, 100, 120), (255, 200, 80),  (80, 255, 150),
    (255, 150, 80),
]


async def _fetch_pexels(query: str, output_path: str) -> bool:
    if not settings.PEXELS_API_KEY:
        return False
    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            r = await client.get(
                "https://api.pexels.com/v1/search",
                headers={"Authorization": settings.PEXELS_API_KEY},
                params={"query": query, "per_page": 8, "orientation": "landscape"},
            )
            if r.status_code != 200:
                return False
            photos = r.json().get("photos", [])
            if not photos:
                return False
            photo = random.choice(photos)
            img_r = await client.get(photo["src"]["large2x"])
            if img_r.status_code != 200:
                return False
            with open(output_path, "wb") as f:
                f.write(img_r.content)
            return True
    except Exception:
        return False


async def _generate_sd(prompt: str, output_path: str) -> bool:
    if not settings.SD_WEBUI_URL:
        return False
    try:
        import base64
        payload = {
            "prompt": f"{prompt}, cinematic, 4k, professional, high quality",
            "negative_prompt": "blurry, low quality, watermark, text, ugly",
            "steps": 25, "width": 1920, "height": 1080, "cfg_scale": 7.5,
        }
        async with httpx.AsyncClient(timeout=120.0) as client:
            r = await client.post(f"{settings.SD_WEBUI_URL}/sdapi/v1/txt2img", json=payload)
            if r.status_code != 200:
                return False
            images = r.json().get("images", [])
            if not images:
                return False
            with open(output_path, "wb") as f:
                f.write(base64.b64decode(images[0]))
            return True
    except Exception:
        return False


def _load_font(size: int, bold: bool = True):
    paths = [
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf" if bold else "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf" if bold else "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf",
        "/usr/share/fonts/truetype/freefont/FreeSansBold.ttf" if bold else "/usr/share/fonts/truetype/freefont/FreeSans.ttf",
    ]
    for p in paths:
        try:
            return ImageFont.truetype(p, size)
        except Exception:
            continue
    return ImageFont.load_default()


def _pillow_image(title: str, content: str, output_path: str, index: int = 0, section_num: int = 0, total_sections: int = 3):
    """Génère une image de scène professionnelle avec titre + contenu."""
    w, h = settings.VIDEO_WIDTH, settings.VIDEO_HEIGHT
    accent = ACCENT_COLORS[index % len(ACCENT_COLORS)]

    # --- Fond avec dégradé diagonal ---
    img = Image.new("RGB", (w, h))
    draw = ImageDraw.Draw(img)
    c1, c2 = PALETTES[index % len(PALETTES)]
    for y in range(h):
        ratio = y / h
        r = int(c1[0] + (c2[0] - c1[0]) * ratio)
        g = int(c1[1] + (c2[1] - c1[1]) * ratio)
        b = int(c1[2] + (c2[2] - c1[2]) * ratio)
        draw.line([(0, y), (w, y)], fill=(r, g, b))

    # --- Cercles décoratifs flous en arrière-plan ---
    overlay = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    od = ImageDraw.Draw(overlay)
    circles = [
        (w * 0.85, h * 0.15, 320, (*accent, 18)),
        (w * 0.05, h * 0.85, 250, (*accent, 12)),
        (w * 0.5,  h * 0.5,  180, (255, 255, 255, 8)),
        (w * 0.2,  h * 0.3,  120, (*accent, 10)),
    ]
    for cx, cy, r, color in circles:
        od.ellipse([cx - r, cy - r, cx + r, cy + r], fill=color)
    blurred = overlay.filter(ImageFilter.GaussianBlur(radius=40))
    img = Image.alpha_composite(img.convert("RGBA"), blurred).convert("RGB")
    draw = ImageDraw.Draw(img)

    # --- Barre colorée en haut ---
    bar_h = 8
    for x in range(w):
        ratio = x / w
        r_c = int(accent[0] * (1 - ratio * 0.4))
        g_c = int(accent[1] * (1 - ratio * 0.4))
        b_c = int(accent[2] * (1 - ratio * 0.4))
        draw.line([(x, 0), (x, bar_h)], fill=(r_c, g_c, b_c))

    # --- Badge numéro de section ---
    badge_font = _load_font(28, bold=True)
    badge_text = f"PARTIE {section_num + 1}/{total_sections}"
    badge_bbox = draw.textbbox((0, 0), badge_text, font=badge_font)
    bw = badge_bbox[2] - badge_bbox[0] + 32
    bh = badge_bbox[3] - badge_bbox[1] + 14
    bx, by = 60, 40
    draw.rounded_rectangle([bx, by, bx + bw, by + bh], radius=6,
                           fill=(*accent, 220) if len(accent) == 3 else accent)
    draw.text((bx + 16, by + 7), badge_text, fill=(0, 0, 0), font=badge_font)

    # --- Ligne séparatrice décorative ---
    sep_y = 110
    draw.line([(60, sep_y), (w - 60, sep_y)], fill=(*accent, 80) if len(accent) == 3 else (100, 100, 100), width=1)

    # --- Titre principal ---
    title_font = _load_font(72, bold=True)
    title_clean = title.upper()[:50]
    title_wrapped = textwrap.wrap(title_clean, width=28)

    title_start_y = 135
    line_spacing = 85
    for i, line in enumerate(title_wrapped[:2]):
        bbox = draw.textbbox((0, 0), line, font=title_font)
        tw = bbox[2] - bbox[0]
        tx = (w - tw) // 2
        ty = title_start_y + i * line_spacing
        # Ombre portée
        for dx, dy in [(-2, -2), (2, -2), (-2, 2), (2, 2), (0, 3)]:
            draw.text((tx + dx, ty + dy), line, fill=(0, 0, 0), font=title_font)
        draw.text((tx, ty), line, fill=(255, 255, 255), font=title_font)

    # --- Soulignement accent ---
    last_title_y = title_start_y + min(len(title_wrapped), 2) * line_spacing
    draw.line([(w // 2 - 160, last_title_y), (w // 2 + 160, last_title_y)],
              fill=accent, width=4)

    # --- Contenu textuel ---
    if content:
        content_font = _load_font(36, bold=False)
        content_clean = content.replace('\n', ' ').strip()
        content_wrapped = textwrap.wrap(content_clean, width=70)[:4]

        content_y = last_title_y + 30
        for line in content_wrapped:
            bbox = draw.textbbox((0, 0), line, font=content_font)
            tw = bbox[2] - bbox[0]
            tx = (w - tw) // 2
            draw.text((tx + 1, content_y + 1), line, fill=(0, 0, 0), font=content_font)
            draw.text((tx, content_y), line, fill=(200, 220, 240), font=content_font)
            content_y += 50

    # --- Barre de progression en bas ---
    prog_y = h - 25
    draw.line([(0, prog_y), (w, prog_y)], fill=(30, 30, 60), width=20)
    if total_sections > 0:
        prog_w = int(w * (section_num + 1) / total_sections)
        for x in range(prog_w):
            ratio = x / max(prog_w, 1)
            r_p = int(accent[0] * 0.7 + accent[0] * 0.3 * ratio)
            g_p = int(accent[1] * 0.7 + accent[1] * 0.3 * ratio)
            b_p = int(accent[2] * 0.7 + accent[2] * 0.3 * ratio)
            draw.line([(x, prog_y - 10), (x, prog_y + 10)], fill=(r_p, g_p, b_p))

    img.save(output_path, "JPEG", quality=95)


async def run(sections: list, output_dir: str, subject: str = "") -> list:
    """
    Génère une image par section.
    Ordre : Stable Diffusion → Pexels → Pillow amélioré
    """
    os.makedirs(output_dir, exist_ok=True)
    paths = []
    total = max(len(sections), 3)

    for i, section in enumerate(sections):
        img_path = os.path.join(output_dir, f"scene_{i:02d}.jpg")
        keyword = section.get("title", f"scene {i + 1}")
        content = section.get("content", "")

        if await _generate_sd(keyword, img_path):
            paths.append(img_path)
            continue

        if await _fetch_pexels(keyword, img_path):
            paths.append(img_path)
            continue

        _pillow_image(keyword, content, img_path, i, section_num=i, total_sections=total)
        paths.append(img_path)

    while len(paths) < 3:
        idx = len(paths)
        img_path = os.path.join(output_dir, f"scene_{idx:02d}.jpg")
        _pillow_image(subject or f"Slide {idx + 1}", "", img_path, idx,
                      section_num=idx, total_sections=total)
        paths.append(img_path)

    return paths