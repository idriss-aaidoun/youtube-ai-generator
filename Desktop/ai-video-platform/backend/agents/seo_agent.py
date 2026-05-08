"""
Agent 5 — SEO Agent
Rôle : Génère les métadonnées YouTube optimisées (titre, description, hashtags, tags)
Stack : LangChain + Ollama (Mistral)
"""
import json
import re
import asyncio
from concurrent.futures import ThreadPoolExecutor

from langchain_community.llms import Ollama
from langchain_core.prompts import PromptTemplate

from settings import settings

_executor = ThreadPoolExecutor(max_workers=2)

SEO_PROMPT = PromptTemplate.from_template("""{lang_instruction}

Génère les métadonnées YouTube SEO pour cette vidéo :

Titre du script : {title}
Hook            : {hook}
Sections        : {sections}

Retourne UNIQUEMENT ce JSON valide, sans aucun texte avant ou après :
{{
  "seo_title": "Titre YouTube viral et optimisé SEO (max 60 caractères)",
  "description": "Description YouTube SEO optimisée (150-250 mots), avec mots-clés intégrés naturellement",
  "hashtags": ["#hashtag1", "#hashtag2", "#hashtag3", "#hashtag4", "#hashtag5"],
  "tags": ["tag1", "tag2", "tag3", "tag4", "tag5", "tag6", "tag7"],
  "category": "Catégorie YouTube recommandée",
  "thumbnail_text": "Texte court pour la miniature (max 5 mots majuscules)"
}}""")


def _parse_seo(raw: str, script: dict, subject: str) -> dict:
    match = re.search(r"\{[\s\S]*\}", raw)
    if match:
        try:
            return json.loads(match.group())
        except json.JSONDecodeError:
            pass
    title = script.get("title", subject)
    return {
        "seo_title": title,
        "description": f"Dans cette vidéo, nous explorons : {subject}. Une présentation complète et informative.",
        "hashtags": [f"#{subject.replace(' ', '')}", "#YouTube", "#IA", "#Contenu", "#Education"],
        "tags": [subject, "youtube", "ia", "video", "contenu", "education", "gratuit"],
        "category": "Education",
        "thumbnail_text": title[:30].upper(),
    }


def _call_llm(script: dict, subject: str, language: str) -> dict:
    lang_instruction = (
        "Réponds UNIQUEMENT en français."
        if language == "Français"
        else "Reply ONLY in English."
    )
    sections_str = ", ".join(s.get("title", "") for s in script.get("sections", []))
    llm = Ollama(
        model=settings.LLM_MODEL,
        base_url=settings.OLLAMA_URL,
        temperature=0.8,
    )
    chain = SEO_PROMPT | llm
    raw = chain.invoke({
        "lang_instruction": lang_instruction,
        "title": script.get("title", subject),
        "hook": script.get("hook", ""),
        "sections": sections_str,
    })
    return _parse_seo(raw, script, subject)


async def run(script: dict, subject: str, language: str) -> dict:
    """Lance la génération SEO dans un thread."""
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(
        _executor, _call_llm, script, subject, language
    )
