import httpx
import json
import os
import re

OLLAMA_URL = os.getenv("OLLAMA_URL", "http://localhost:11434")
MODEL = "mistral"


async def generate_script(subject: str, style: str, duration: str, language: str) -> dict:
    duration_map = {
        "1 min": "1 minute (environ 150 mots)",
        "3 min": "3 minutes (environ 450 mots)",
        "5 min": "5 minutes (environ 750 mots)",
        "10 min": "10 minutes (environ 1500 mots)",
    }
    word_count = duration_map.get(duration, "3 minutes (environ 450 mots)")

    lang_instruction = "Réponds UNIQUEMENT en français." if language == "Français" else "Reply ONLY in English."

    prompt = f"""{lang_instruction}

Tu es un expert en création de contenu YouTube. Crée un script vidéo structuré sur :

SUJET : {subject}

FORMAT OBLIGATOIRE (JSON uniquement, sans texte avant ou après) :
{{
  "title": "Titre accrocheur YouTube (max 60 caractères)",
  "hook": "Phrase d'accroche puissante pour les 5 premières secondes",
  "introduction": "Introduction de 2-3 phrases qui présente le sujet",
  "sections": [
    {{"title": "Section 1", "content": "Contenu détaillé de la section 1"}},
    {{"title": "Section 2", "content": "Contenu détaillé de la section 2"}},
    {{"title": "Section 3", "content": "Contenu détaillé de la section 3"}}
  ],
  "conclusion": "Conclusion de 2-3 phrases qui résume les points clés",
  "cta": "Appel à l'action pour s'abonner et liker",
  "description": "Description YouTube SEO optimisée (max 200 mots)",
  "hashtags": ["#hashtag1", "#hashtag2", "#hashtag3", "#hashtag4", "#hashtag5"],
  "tags": ["tag1", "tag2", "tag3", "tag4", "tag5"]
}}

TON : {style}
DURÉE CIBLE : {word_count}

IMPORTANT : Retourne UNIQUEMENT le JSON valide, rien d'autre.
"""

    async with httpx.AsyncClient(timeout=120.0) as client:
        response = await client.post(
            f"{OLLAMA_URL}/api/generate",
            json={
                "model": MODEL,
                "prompt": prompt,
                "stream": False,
                "options": {
                    "temperature": 0.7,
                    "top_p": 0.9,
                }
            }
        )
        response.raise_for_status()
        result = response.json()
        raw_text = result.get("response", "")

    json_match = re.search(r'\{[\s\S]*\}', raw_text)
    if json_match:
        try:
            return json.loads(json_match.group())
        except json.JSONDecodeError:
            pass

    return {
        "title": f"Vidéo sur : {subject}",
        "hook": f"Saviez-vous que {subject} peut changer votre vie ?",
        "introduction": f"Aujourd'hui, nous allons explorer en profondeur le sujet de {subject}.",
        "sections": [
            {"title": "Contexte", "content": f"Le sujet {subject} est crucial dans notre monde actuel."},
            {"title": "Points clés", "content": f"Voici les éléments essentiels à comprendre sur {subject}."},
            {"title": "Impact", "content": f"L'impact de {subject} se fait sentir dans de nombreux domaines."}
        ],
        "conclusion": f"En conclusion, {subject} est un sujet qui mérite toute notre attention.",
        "cta": "N'oubliez pas de vous abonner et d'activer la cloche pour ne rien manquer !",
        "description": f"Dans cette vidéo, nous explorons {subject} en détail. {style.capitalize()} et informatif.",
        "hashtags": [f"#{subject.replace(' ', '')}", "#YouTube", "#Contenu", "#Education", "#Viral"],
        "tags": [subject, style, "youtube", "video", "contenu"]
    }


async def check_ollama_status() -> bool:
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            response = await client.get(f"{OLLAMA_URL}/api/tags")
            return response.status_code == 200
    except Exception:
        return False


async def pull_model_if_needed() -> bool:
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            response = await client.get(f"{OLLAMA_URL}/api/tags")
            data = response.json()
            models = [m["name"] for m in data.get("models", [])]
            if any(MODEL in m for m in models):
                return True

        async with httpx.AsyncClient(timeout=300.0) as client:
            await client.post(
                f"{OLLAMA_URL}/api/pull",
                json={"name": MODEL, "stream": False}
            )
        return True
    except Exception:
        return False
