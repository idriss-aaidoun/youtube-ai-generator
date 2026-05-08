# 🎬 AI Autonomous Video Generation Platform v2.0

> Plateforme IA locale qui transforme une idée en vidéo YouTube complète.
> **100% open-source — 100% local — 0€ d'API payante**

---

## 🎯 Vue d'ensemble

```
Entrée : "Les dangers de l'intelligence artificielle"
   ↓
Sortie :  ✅ video.mp4 (1080p, narration + images + sous-titres)
          ✅ thumbnail.jpg (miniature YouTube)
          ✅ subtitles.srt (sous-titres synchronisés)
          ✅ Titre SEO + Description + Hashtags + Tags
```

---

## 🏗️ Architecture Multi-Agents

```
User Input (Streamlit)
       ↓
FastAPI Backend — Orchestrateur Pipeline
       ↓
AI Pipeline Engine
       ↓
┌──────────────────────────────────────────────────────────┐
│                Multi-Agent System (CrewAI)                │
│                                                          │
│  ① Script Agent     → Script JSON structuré              │
│    (LangChain + Mistral)  {hook, sections, cta...}       │
│         ↓                                                │
│  ② Voice Agent      → narration.wav                     │
│    (Piper TTS)                                           │
│         ↓                                                │
│  ③ Visual Agent     → images des scènes                 │
│    (SD / Pexels / Pillow)                                │
│         ↓                                                │
│  ④ Whisper STT      → sous-titres .srt + .txt           │
│         ↓                                                │
│  ⑤ Editor Agent     → video.mp4 1080p                   │
│    (MoviePy + FFmpeg)  audio + images + transitions      │
│         ↓                                                │
│  ⑥ SEO Agent        → titre viral + description +       │
│    (LangChain + Mistral)  hashtags + tags                │
│         ↓                                                │
│  ⑦ Thumbnail        → miniature.jpg                     │
│    (Pillow)           texte + contraste + design         │
└──────────────────────────────────────────────────────────┘
       ↓
SQLite — Historique des jobs
```

---

## 📦 Stack technique (100% gratuit)

| Composant | Technologie | Rôle |
|-----------|-------------|------|
| **Frontend** | Streamlit | Interface utilisateur |
| **Backend** | FastAPI | API REST + orchestration |
| **LLM** | Ollama + Mistral | Script + SEO (Agents 1 & 6) |
| **Orchestration IA** | LangChain + CrewAI | Coordination des agents LLM |
| **TTS** | Piper TTS | Voix IA (Agent 2) |
| **STT** | Whisper | Sous-titres (étape 4) |
| **Images** | SD / Pexels / Pillow | Visuels scènes (Agent 3) |
| **Montage** | MoviePy + FFmpeg | Assemblage 1080p (Agent 4) |
| **Miniature** | Pillow | Thumbnail YouTube (étape 7) |
| **Base de données** | SQLite | Historique jobs |
| **Déploiement** | Docker Compose | Orchestration locale |

---

## 📁 Structure du projet

```
ai-video-platform/
│
├── docker-compose.yml              ← Orchestration des services
├── .env.example                    ← Configuration à copier
├── setup.bat                       ← Installation automatique Windows
├── setup.sh                        ← Installation automatique Linux/Mac
│
├── config/
│   └── settings.py                 ← Configuration centralisée (pydantic-settings)
│
├── frontend/
│   ├── Dockerfile
│   ├── requirements.txt
│   └── app.py                      ← Interface Streamlit
│
├── backend/
│   ├── Dockerfile                  ← Python + FFmpeg + ImageMagick + Piper
│   ├── requirements.txt            ← FastAPI + LangChain + CrewAI + Whisper + ...
│   ├── main.py                     ← Point d'entrée FastAPI
│   ├── database.py                 ← Modèles SQLite (SQLAlchemy)
│   │
│   ├── api/
│   │   └── routes.py               ← Routes REST (/generate, /jobs, /history)
│   │
│   ├── agents/
│   │   ├── script_agent.py         ← Agent 1 : Script (CrewAI + LangChain + Mistral)
│   │   ├── voice_agent.py          ← Agent 2 : TTS (Piper → narration.wav)
│   │   ├── visual_agent.py         ← Agent 3 : Images (SD / Pexels / Pillow)
│   │   ├── editor_agent.py         ← Agent 4 : Montage (MoviePy + FFmpeg)
│   │   ├── seo_agent.py            ← Agent 5 : SEO (CrewAI + LangChain + Mistral)
│   │   ├── stt_service.py          ← Whisper STT (sous-titres .srt)
│   │   └── thumbnail_service.py    ← Pillow (miniature YouTube)
│   │
│   └── pipeline/
│       └── orchestrator.py         ← Coordonne les 7 étapes
│
├── outputs/
│   ├── videos/                     ← Fichiers video.mp4 générés
│   ├── audio/                      ← Fichiers narration.wav
│   └── images/                     ← Images des scènes
│
├── models/
│   └── piper/                      ← Binaire Piper TTS + modèles voix
│
└── assets/                         ← Ressources statiques
```

---

## 🚀 Guide d'installation complet

### Prérequis

| Outil | Version | Lien |
|-------|---------|------|
| Docker Desktop | 4.x+ | https://www.docker.com/products/docker-desktop/ |
| RAM disponible | 8 Go min (16 Go recommandé) | — |
| Espace disque | 15 Go (Docker + Mistral) | — |

---

### ▶️ Windows — Installation en 1 clic

1. **Installer Docker Desktop** → https://www.docker.com/products/docker-desktop/
   - Lancer Docker Desktop et attendre l'icône verte ✅
   - Sur Windows 10/11 Home : activer WSL2 si demandé

2. **Extraire l'archive** dans un dossier (ex: `C:\Projets\ai-video-platform`)

3. **Double-cliquer sur `setup.bat`**

   Le script fait automatiquement :
   - ✅ Vérifie Docker
   - ✅ Crée le fichier `.env`
   - ✅ Build + démarre les 3 conteneurs
   - ✅ Télécharge le modèle Mistral (~4 Go)

4. **Ouvrir dans le navigateur** → http://localhost:8501

---

### ▶️ Linux / macOS — Installation automatique

```bash
cd ai-video-platform
chmod +x setup.sh
bash setup.sh
```

Puis ouvrir → http://localhost:8501

---

### ▶️ Installation manuelle (toutes plateformes)

```bash
# 1. Se placer dans le dossier du projet
cd ai-video-platform

# 2. (Optionnel) Configurer les variables
cp .env.example .env
# Éditer .env si vous avez une clé Pexels

# 3. Démarrer tous les services
docker-compose up -d --build

# 4. Télécharger Mistral (une seule fois, ~4 Go)
docker exec ai_ollama ollama pull mistral

# 5. Ouvrir l'interface
# http://localhost:8501
```

---

## 🖥️ Utilisation

### Formulaire de génération

| Champ | Options |
|-------|---------|
| **Sujet** | Texte libre |
| **Style** | éducatif / storytelling / documentaire / viral / motivationnel / news |
| **Durée** | 1 min / 3 min / 5 min / 10 min |
| **Voix** | homme / femme |
| **Langue** | Français / Anglais |

### Fichiers générés

- 🎬 `video.mp4` — Vidéo 1080p (narration + images + transitions + sous-titres)
- 🖼️ `thumbnail.jpg` — Miniature YouTube (1280x720)
- 📝 `subtitles.srt` — Sous-titres synchronisés (prêts pour YouTube)
- 📄 Script JSON — Hook + sections + CTA + description SEO + hashtags + tags

---

## ⚙️ Commandes utiles

```bash
# Démarrer
docker-compose up -d

# Arrêter
docker-compose down

# Logs en temps réel
docker-compose logs -f

# Logs d'un seul service
docker-compose logs -f backend

# Reconstruire après modification
docker-compose up -d --build

# Voir les modèles Ollama disponibles
docker exec ai_ollama ollama list

# Installer un autre modèle LLM
docker exec ai_ollama ollama pull llama3
docker exec ai_ollama ollama pull gemma3

# Status des conteneurs
docker-compose ps
```

---

## 🔧 Configuration avancée

### Changer le modèle LLM

Dans `.env` :
```
LLM_MODEL=llama3    # Plus puissant (nécessite plus de RAM)
LLM_MODEL=gemma3    # Plus léger
LLM_MODEL=mistral   # Recommandé (défaut)
```

### Activer les images Pexels (gratuit)

1. Créer un compte sur https://www.pexels.com/api/
2. Dans `.env` :
   ```
   PEXELS_API_KEY=votre_cle_ici
   ```
3. Redémarrer : `docker-compose up -d`

### Activer Stable Diffusion (GPU NVIDIA requis)

1. Dans `docker-compose.yml`, décommenter le service `stable-diffusion`
2. Dans `.env` :
   ```
   SD_WEBUI_URL=http://stable-diffusion:7860
   ```
3. Redémarrer : `docker-compose up -d`

---

## 🔧 Résolution des problèmes

### ❌ "no configuration file provided: not found"
→ Vous n'êtes pas dans le bon dossier.
```bash
# Aller dans le dossier contenant docker-compose.yml
cd ai-video-platform
docker-compose up -d --build
```

### ❌ Docker non démarré
→ Ouvrir Docker Desktop et attendre l'icône verte.

### ❌ Port déjà utilisé
```yaml
# Dans docker-compose.yml, changer le port exposé
ports:
  - "8502:8501"   # Utiliser 8502 au lieu de 8501
```

### ❌ Ollama non connecté dans l'interface
```bash
docker exec ai_ollama ollama pull mistral
docker-compose logs ollama
```

### ❌ Le modèle Mistral est lent
→ Normal pour la première génération (chargement en RAM).
Les suivantes sont plus rapides. Avec GPU NVIDIA, utiliser :
```bash
docker exec ai_ollama ollama pull mistral:latest
```

### ❌ CrewAI / LangChain erreur
```bash
# Voir les logs détaillés du backend
docker-compose logs -f backend
```

---

## 🖥️ Configuration matérielle

| Config | RAM | GPU | LLM | Vitesse |
|--------|-----|-----|-----|---------|
| Minimum | 8 Go | Non | Mistral 7B Q4 | 8-20 min/vidéo |
| Recommandée | 16 Go | Non | Mistral ou Llama3 | 4-10 min/vidéo |
| Optimale | 32 Go | RTX 3060+ | Llama3 70B | 2-5 min/vidéo |

---

## 🛣️ Roadmap

- [x] **Phase 1** — Pipeline MVP (script → TTS → vidéo)
- [x] **Phase 2** — Sous-titres + miniature + SEO
- [x] **Phase 3** — Architecture multi-agents (CrewAI + LangChain)
- [ ] **Phase 4** — Stable Diffusion pour images IA
- [ ] **Phase 5** — Templates YouTube (formats prédéfinis)
- [ ] **Phase 6** — Publication automatique YouTube via API

---

## 📝 Licence

MIT — Utilisation libre, modification libre, commercialisation libre.
