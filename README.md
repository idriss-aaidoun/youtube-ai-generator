# YouTube AI Studio

Prototype Flask du cahier des charges: génération d'idées, script, audio, storyboard, montage et préparation de publication YouTube à partir d'un sujet.

Le cahier des charges formel est disponible dans [docs/cahier_des_charges.md](docs/cahier_des_charges.md).

## Démarrage

1. Crée l'environnement et installe les dépendances:

```powershell
& "c:/Users/HP G7/Desktop/ytb/.venv/Scripts/python.exe" -m pip install -r requirements.txt
```

2. Lance l'application:

```powershell
& "c:/Users/HP G7/Desktop/ytb/.venv/Scripts/python.exe" run.py
```

3. Ouvre `http://127.0.0.1:5000`.

## Fonctionnalités déjà en place

- Interface web pour lancer une génération.
- API Flask pour générer un brouillon vidéo complet.
- Persistance SQLite via Flask-SQLAlchemy.
- Génération d'idées avec analyse de tendance plus réaliste et score multi-signal.
- Génération de script via Hugging Face si `HUGGINGFACE_API_TOKEN` ou `HF_TOKEN` est configuré.
- Pipeline local de secours quand les APIs externes ne sont pas configurées ou tombent en erreur.
- Génération audio via ElevenLabs si `ELEVENLABS_API_KEY` est configuré.
- Rendu vidéo réel en MP4 via images générées, transitions et mux audio si disponible.
- Génération automatique de sous-titres SRT à partir du storyboard rendu.
- Génération d'images IA via Hugging Face si `HUGGINGFACE_IMAGE_MODEL` et le token sont configurés.
- Publication YouTube réelle via OAuth refresh token si les identifiants sont configurés.
- Miniature YouTube générée automatiquement à partir des visuels produits et uploadée avec la vidéo.
- Description de publication enrichie automatiquement avec des chapitres et des hashtags.

## Configuration script IA

- `HUGGINGFACE_API_TOKEN` ou `HF_TOKEN` pour activer l'appel réel à Hugging Face.
- `HUGGINGFACE_MODEL` pour choisir le modèle de génération.
- `HUGGINGFACE_TIMEOUT_SECONDS`, `HUGGINGFACE_MAX_NEW_TOKENS` et `HUGGINGFACE_TEMPERATURE` pour ajuster le comportement.

## Configuration images IA

- `HUGGINGFACE_IMAGE_MODEL` active le modèle de génération d'images.
- `HUGGINGFACE_IMAGE_TIMEOUT_SECONDS` règle le délai d'attente.
- `HUGGINGFACE_IMAGE_GUIDANCE_SCALE` ajuste le respect du prompt.
- `HUGGINGFACE_IMAGE_NEGATIVE_PROMPT` limite les artefacts visuels.

## Configuration TTS

- `ELEVENLABS_API_KEY` active la synthèse vocale réelle.
- `ELEVENLABS_VOICE_ID` force une voix précise.
- `ELEVENLABS_VOICE_ID_FEMALE` et `ELEVENLABS_VOICE_ID_MALE` permettent un mapping direct selon le choix du formulaire.
- Si aucun `voice_id` n'est fourni, le service interroge `/v1/voices` et sélectionne automatiquement une voix disponible.
- `ELEVENLABS_MODEL_ID`, `ELEVENLABS_OUTPUT_FORMAT` et les paramètres de voix permettent d'ajuster le rendu.

## Configuration vidéo

- `VIDEO_RENDER_WIDTH`, `VIDEO_RENDER_HEIGHT` et `VIDEO_RENDER_FPS` contrôlent le rendu standard.
- `VIDEO_RENDER_TRANSITION_SECONDS` règle la durée des transitions.
- Les variantes `VIDEO_RENDER_TEST_*` sont utilisées automatiquement pendant les tests.
- Le MP4 final est écrit dans le dossier artefacts de génération.

## Configuration YouTube

- `YOUTUBE_ACCESS_TOKEN` permet de publier directement sans échange de refresh token.
- `YOUTUBE_CLIENT_ID`, `YOUTUBE_CLIENT_SECRET` et `YOUTUBE_REFRESH_TOKEN` activent le flux OAuth.
- `YOUTUBE_PRIVACY_STATUS`, `YOUTUBE_CATEGORY_ID`, `YOUTUBE_MADE_FOR_KIDS` et `YOUTUBE_NOTIFY_SUBSCRIBERS` contrôlent les métadonnées de publication.
- `YOUTUBE_DEFAULT_LANGUAGE` et `YOUTUBE_DEFAULT_AUDIO_LANGUAGE` complètent le snippet publié.
- La miniature est générée automatiquement depuis les visuels du pipeline et uploadée via l'API YouTube si l'upload vidéo réussit.
- La description publiée reprend le résumé SEO, ajoute les chapitres détectés dans le script et termine par une sélection de hashtags.
- `publication_options` dans la requête JSON permet de forcer des chapitres manuels et une liste de hashtags, avec un filtre `hashtag_blacklist` pour retirer les termes à exclure.

## Endpoints

- `GET /health`
- `POST /api/generate`
- `GET /api/videos`
- `GET /api/videos/<id>`

## Étapes suivantes possibles

- Brancher OpenAI ou Hugging Face pour la génération de script.
- Brancher ElevenLabs ou Google TTS pour le rendu audio.
- Brancher MoviePy ou FFmpeg pour le montage réel.
- Ajouter l'upload YouTube via OAuth.
