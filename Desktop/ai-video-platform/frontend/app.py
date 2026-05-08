"""
Frontend Streamlit — Interface utilisateur
AI Autonomous Video Generation Platform v2.0
"""
import os
import time
import httpx
import streamlit as st

BACKEND_URL = os.getenv("BACKEND_URL", "http://localhost:8000")

st.set_page_config(
    page_title="AI Video Generator",
    page_icon="🎬",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown("""
<style>
[data-testid="stAppViewContainer"] { background: #0a0a0f; }
[data-testid="stSidebar"] { background: #0f0f1a; border-right: 1px solid #1e1e3a; }
.hero {
    background: linear-gradient(135deg,#0f0f1a 0%,#1a1a2e 50%,#0f3460 100%);
    padding:2.5rem 2rem; border-radius:16px; margin-bottom:2rem;
    border:1px solid #1e3a5f; text-align:center;
}
.hero h1 { color:#e94560; font-size:2.8rem; margin:0; letter-spacing:-1px; }
.hero p  { color:#7eceff; font-size:1.05rem; margin-top:0.6rem; }
.agent-card {
    background:#0f0f1a; border:1px solid #1e3a5f;
    border-radius:10px; padding:0.7rem 1rem; margin:0.35rem 0;
}
.agent-card .num   { color:#7eceff; font-size:0.75rem; font-weight:700; }
.agent-card .name  { color:#e2e8f0; font-size:0.9rem; font-weight:600; }
.agent-card .tools { color:#64748b; font-size:0.78rem; }
.stProgress > div > div { background:linear-gradient(90deg,#e94560,#0f3460) !important; }
div[data-testid="stButton"] button {
    background:linear-gradient(135deg,#e94560,#0f3460) !important;
    color:white !important; border:none !important; border-radius:8px !important;
    font-weight:700 !important; font-size:1.05rem !important;
}
</style>
""", unsafe_allow_html=True)


# ── helpers ──────────────────────────────────────────────────────────────────
def api_get(path: str, timeout: float = 10.0):
    try:
        r = httpx.get(f"{BACKEND_URL}{path}", timeout=timeout)
        return r.json() if r.status_code == 200 else None
    except Exception:
        return None


def api_post(path: str, payload: dict, timeout: float = 30.0):
    try:
        r = httpx.post(f"{BACKEND_URL}{path}", json=payload, timeout=timeout)
        return r.json() if r.status_code == 200 else None
    except Exception:
        return None


def download_bytes(path: str):
    try:
        r = httpx.get(f"{BACKEND_URL}{path}", timeout=120.0)
        return r.content if r.status_code == 200 else None
    except Exception:
        return None


# ── Sidebar ───────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("## ⚙️ Statut système")
    health = api_get("/health", timeout=6.0)
    if health:
        svcs = health.get("services", {})
        if svcs.get("ollama_mistral") == "connected":
            st.success("✅ Ollama + Mistral")
        else:
            st.error("❌ Ollama non connecté")
            st.caption("Attendez le démarrage ou exécutez :")
            st.code("docker exec ai_ollama ollama pull mistral", language="bash")

        sd = svcs.get("stable_diffusion", "not configured")
        if sd == "connected":
            st.success("✅ Stable Diffusion")
        elif sd == "not configured":
            st.info("💡 Stable Diffusion : optionnel (GPU)")
        else:
            st.warning("⚠️ SD configuré mais injoignable")

        if svcs.get("pexels") == "configured":
            st.success("✅ Pexels API")
        else:
            st.info("💡 Pexels : non configuré (optionnel)")
    else:
        st.error("❌ Backend non disponible")
        st.caption("Vérifiez que le conteneur backend est démarré.")

    st.markdown("---")
    st.markdown("## 🤖 Agents IA")

    for num, name, tools in [
        ("1", "Script Agent",  "LangChain + Mistral"),
        ("2", "Voice Agent",   "Piper TTS"),
        ("3", "Visual Agent",  "SD / Pexels / Pillow"),
        ("4", "Editor Agent",  "MoviePy + FFmpeg"),
        ("5", "SEO Agent",     "LangChain + Mistral"),
    ]:
        st.markdown(f"""
        <div class="agent-card">
            <div class="num">Agent {num}</div>
            <div class="name">{name}</div>
            <div class="tools">{tools}</div>
        </div>""", unsafe_allow_html=True)

    st.markdown("---")
    st.markdown("## 🔄 Pipeline")
    for s in ["① Script JSON", "② narration.wav", "③ Images scènes",
              "④ Sous-titres .srt", "⑤ video.mp4 1080p", "⑥ SEO YouTube", "⑦ thumbnail.jpg"]:
        st.markdown(f"<small style='color:#64748b'>{s}</small>", unsafe_allow_html=True)


# ── Hero ──────────────────────────────────────────────────────────────────────
st.markdown("""
<div class="hero">
    <h1>🎬 AI Video Generator</h1>
    <p>Plateforme multi-agents • LangChain + Mistral • Piper TTS • Whisper • MoviePy • 100% Local • 100% Gratuit</p>
</div>
""", unsafe_allow_html=True)

# ── Tabs ──────────────────────────────────────────────────────────────────────
tab_gen, tab_hist, tab_guide = st.tabs(["🚀 Générer", "📊 Historique", "📖 Guide"])

# ══ Tab : Générer ═════════════════════════════════════════════════════════════
with tab_gen:
    col_form, col_prog = st.columns([1, 1], gap="large")

    with col_form:
        st.markdown("### 📝 Paramètres de la vidéo")

        subject = st.text_area(
            "Sujet",
            placeholder="Ex: Les dangers de l'intelligence artificielle pour l'humanité",
            height=110,
        )
        c1, c2 = st.columns(2)
        with c1:
            style = st.selectbox("Style", [
                "éducatif", "storytelling", "documentaire",
                "viral", "motivationnel", "news"])
        with c2:
            duration = st.selectbox("Durée", ["1 min", "3 min", "5 min", "10 min"], index=1)

        c3, c4 = st.columns(2)
        with c3:
            voice = st.selectbox("Voix", ["homme", "femme"])
        with c4:
            language = st.selectbox("Langue", ["Français", "Anglais"])

        st.markdown("")
        btn_generate = st.button("🚀 Lancer la génération", use_container_width=True, type="primary")

    with col_prog:
        st.markdown("### 📈 Progression")

        if "job_id" not in st.session_state:
            st.session_state.job_id = None
        if "done" not in st.session_state:
            st.session_state.done = False

        # ── Lancement d'un nouveau job ────────────────────────────────────────
        if btn_generate:
            if not subject.strip():
                st.error("❌ Saisissez un sujet pour la vidéo.")
            else:
                st.session_state.done = False
                with st.spinner("Démarrage du pipeline..."):
                    res = api_post("/api/generate", {
                        "subject": subject, "style": style,
                        "duration": duration, "voice": voice, "language": language,
                    })
                if res and "job_id" in res:
                    st.session_state.job_id = res["job_id"]
                    st.rerun()
                else:
                    st.error("❌ Impossible de démarrer le job. Le backend est-il lancé ?")

        # ── Suivi progression ─────────────────────────────────────────────────
        if st.session_state.job_id and not st.session_state.done:
            job = api_get(f"/api/jobs/{st.session_state.job_id}")
            if job:
                status   = job.get("status", "pending")
                progress = job.get("progress", 0)
                step     = job.get("current_step", "")

                st.progress(progress / 100)
                st.markdown(f"**{step}**")

                if status in ("running", "pending"):
                    st.info(f"⏳ En cours… {progress}%")
                    time.sleep(4)
                    st.rerun()

                elif status == "completed":
                    st.session_state.done = True
                    st.success("🎉 Vidéo générée avec succès !")
                    if job.get("script_title"):
                        st.markdown(f"#### 🎬 {job['script_title']}")

                    d1, d2, d3 = st.columns(3)
                    with d1:
                        if job.get("video_url"):
                            vid = download_bytes(job["video_url"])
                            if vid:
                                st.download_button(
                                    "🎬 MP4", vid,
                                    f"video_{st.session_state.job_id[:8]}.mp4",
                                    "video/mp4", use_container_width=True)
                    with d2:
                        if job.get("thumbnail_url"):
                            thumb = download_bytes(job["thumbnail_url"])
                            if thumb:
                                st.download_button(
                                    "🖼️ Miniature", thumb,
                                    f"thumbnail_{st.session_state.job_id[:8]}.jpg",
                                    "image/jpeg", use_container_width=True)
                                st.image(thumb, use_column_width=True)
                    with d3:
                        if job.get("subtitle_url"):
                            srt = download_bytes(job["subtitle_url"])
                            if srt:
                                st.download_button(
                                    "📝 .srt", srt,
                                    f"subtitles_{st.session_state.job_id[:8]}.srt",
                                    "text/plain", use_container_width=True)

                    script = api_get(f"/api/jobs/{st.session_state.job_id}/script")
                    if script:
                        with st.expander("📄 Script + SEO complet"):
                            st.markdown(f"**Titre SEO :** {script.get('seo_title') or script.get('title','')}")
                            st.markdown(f"**Hook :** {script.get('hook','')}")
                            for s in script.get("sections", []):
                                st.markdown(f"- **{s.get('title','')}**")
                            st.markdown("**Description YouTube :**")
                            st.text_area("", script.get("description", ""), height=120,
                                         label_visibility="collapsed")
                            if script.get("hashtags"):
                                st.markdown("**Hashtags :** " + " ".join(script["hashtags"]))
                            if script.get("tags"):
                                st.markdown("**Tags :** " + ", ".join(script["tags"]))

                    if st.button("🔄 Nouvelle vidéo"):
                        st.session_state.job_id = None
                        st.session_state.done = False
                        st.rerun()

                elif status == "failed":
                    st.session_state.done = True
                    st.error(f"❌ Erreur : {job.get('error_message','Erreur inconnue')}")
                    if st.button("🔄 Réessayer"):
                        st.session_state.job_id = None
                        st.session_state.done = False
                        st.rerun()

            else:
                st.warning("Impossible de récupérer le statut du job.")

        elif not st.session_state.job_id:
            st.markdown("""
            <div style='text-align:center;padding:3rem 1rem;color:#334155;
                        border:2px dashed #1e293b;border-radius:12px;margin-top:1rem'>
                <div style='font-size:3.5rem'>🎬</div>
                <p style='color:#475569;margin-top:1rem'>
                    Remplissez le formulaire et cliquez sur<br>
                    <strong style='color:#7eceff'>Lancer la génération</strong>
                </p>
                <p style='font-size:0.85rem;color:#334155;margin-top:0.8rem'>
                    Temps estimé : 5-20 min selon la durée et le matériel
                </p>
            </div>""", unsafe_allow_html=True)

# ══ Tab : Historique ══════════════════════════════════════════════════════════
with tab_hist:
    st.markdown("### 📊 Historique des vidéos")
    if st.button("🔄 Actualiser"):
        st.rerun()

    history = api_get("/api/history") or []
    if not history:
        st.info("Aucune vidéo générée pour l'instant.")
    else:
        for job in history:
            emoji = {"completed": "✅", "running": "⏳", "failed": "❌", "pending": "🕐"}.get(
                job["status"], "❓")
            title = job.get("script_title") or job["subject"][:60]
            date = (job.get("created_at") or "")[:10]
            with st.expander(f"{emoji} {title}  —  {date}"):
                c1, c2, c3 = st.columns(3)
                with c1:
                    st.markdown(f"**Sujet :** {job['subject'][:80]}")
                    st.markdown(f"**Style :** {job['style']}  |  **Durée :** {job['duration']}")
                with c2:
                    st.markdown(f"**Langue :** {job['language']}  |  **Statut :** `{job['status']}`")
                    st.progress(job["progress"] / 100)
                with c3:
                    if job["status"] == "completed":
                        vid = download_bytes(f"/api/jobs/{job['job_id']}/video")
                        if vid:
                            st.download_button(
                            "🎬 Télécharger la vidéo",
                             vid,
                            f"video_{job['job_id'][:8]}.mp4",
                            "video/mp4",
                            use_container_width=True,
                            key=f"dl_{job['job_id']}"
                     )
                        else:
                            st.warning("Vidéo introuvable")

# ══ Tab : Guide ═══════════════════════════════════════════════════════════════
with tab_guide:
    st.markdown("""
### 🏗️ Architecture
```
Streamlit (UI)
    ↓ HTTP
FastAPI (Orchestrateur)
    ↓
Pipeline — 7 étapes séquentielles
    ├─ Agent 1 : Script Agent    — LangChain + Mistral
    ├─ Agent 2 : Voice Agent     — Piper TTS
    ├─ Agent 3 : Visual Agent    — Pexels / Pillow (SD optionnel)
    ├─ Étape 4 : Whisper STT     — Sous-titres .srt
    ├─ Agent 4 : Editor Agent    — MoviePy + FFmpeg → MP4 1080p
    ├─ Agent 5 : SEO Agent       — LangChain + Mistral
    └─ Étape 7 : Thumbnail       — Pillow
```

### ✅ Technologies (100% gratuites, 100% locales)
| Technologie | Rôle | Licence |
|---|---|---|
| Streamlit | Interface | Apache 2.0 |
| FastAPI | API REST | MIT |
| Ollama + Mistral | LLM | MIT / Apache 2.0 |
| LangChain | Orchestration LLM | MIT |
| Piper TTS | Synthèse vocale | MIT |
| Whisper | Sous-titres (STT) | MIT |
| MoviePy + FFmpeg | Montage vidéo | MIT / LGPL |
| Pillow | Images & miniature | HPND |
| SQLite | Base de données | Domaine public |
| Docker | Déploiement local | Apache 2.0 |

### 🚀 Démarrage rapide
```bash
# Windows
setup.bat

# Linux / Mac
bash setup.sh
```

### ⚙️ Activer Pexels (images réelles, gratuit)
```
1. Créer un compte : https://www.pexels.com/api/
2. Ajouter dans .env : PEXELS_API_KEY=votre_cle
3. docker-compose up -d
```

### 🎮 Activer Stable Diffusion (GPU NVIDIA requis)
```
1. Décommenter le service dans docker-compose.yml
2. Ajouter dans .env : SD_WEBUI_URL=http://stable-diffusion:7860
3. docker-compose up -d
```
""")
