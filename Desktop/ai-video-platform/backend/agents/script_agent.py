"""
Agent 1 — Script Agent
Rôle : Génère le script YouTube structuré (Hook → Corps → CTA)
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

SCRIPT_PROMPT = PromptTemplate.from_template("""{lang_instruction}

Tu es un expert YouTube. Crée un script vidéo complet sur : "{subject}"

Style : {style}
Durée : {duration} ({words})

Retourne UNIQUEMENT ce JSON valide, sans aucun texte avant ou après :
{{
  "title": "Titre accrocheur YouTube (max 60 caractères)",
  "hook": "Accroche percutante pour les 5 premières secondes",
  "introduction": "Introduction en 2-3 phrases",
  "sections": [
    {{"title": "Titre section 1", "content": "Contenu détaillé de la section 1"}},
    {{"title": "Titre section 2", "content": "Contenu détaillé de la section 2"}},
    {{"title": "Titre section 3", "content": "Contenu détaillé de la section 3"}}
  ],
  "conclusion": "Conclusion en 2-3 phrases",
  "cta": "Appel à l'action (abonnement, like, commentaire)"
}}""")

_DURATION_WORDS = {
    "1 min": "150 mots",
    "3 min": "450 mots",
    "5 min": "750 mots",
    "10 min": "1500 mots",
}

_DEFAULT_SCRIPT = {
    "title": "Vidéo générée par IA",
    "hook": "Bienvenue dans cette vidéo exclusive.",
    "introduction": "Aujourd'hui nous explorons un sujet fascinant.",
    "sections": [
        {"title": "Contexte", "content": "Voici le contexte du sujet abordé."},
        {"title": "Points clés", "content": "Les éléments essentiels à retenir."},
        {"title": "Impact", "content": "Ce que cela change pour vous."},
    ],
    "conclusion": "Voilà les points clés à retenir de cette vidéo.",
    "cta": "Abonnez-vous pour ne rien manquer !",
}


def _parse_json(raw: str) -> dict:
    match = re.search(r"\{[\s\S]*\}", raw)
    if match:
        try:
            return json.loads(match.group())
        except json.JSONDecodeError:
            pass
    return _DEFAULT_SCRIPT.copy()


def _call_llm(subject: str, style: str, duration: str, language: str) -> dict:
    lang_instruction = (
        "Réponds UNIQUEMENT en français."
        if language == "Français"
        else "Reply ONLY in English."
    )
    llm = Ollama(
        model=settings.LLM_MODEL,
        base_url=settings.OLLAMA_URL,
        temperature=settings.LLM_TEMPERATURE,
    )
    chain = SCRIPT_PROMPT | llm
    raw = chain.invoke({
        "lang_instruction": lang_instruction,
        "subject": subject,
        "style": style,
        "duration": duration,
        "words": _DURATION_WORDS.get(duration, "450 mots"),
    })
    return _parse_json(raw)


async def run(subject: str, style: str, duration: str, language: str) -> dict:
    """Lance la génération du script dans un thread (LLM est synchrone)."""
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(
        _executor, _call_llm, subject, style, duration, language
    )
