#!/bin/bash
set -e
cd "$(dirname "$0")"

GREEN='\033[0;32m'; YELLOW='\033[1;33m'; RED='\033[0;31m'; BLUE='\033[0;34m'; NC='\033[0m'

echo ""
echo -e "${BLUE}============================================================${NC}"
echo -e "${BLUE}  AI Video Generator v2.0 — Multi-Agent Architecture${NC}"
echo -e "${BLUE}  Installation automatique Linux / macOS${NC}"
echo -e "${BLUE}============================================================${NC}"
echo ""
echo "Dossier de travail : $(pwd)"
echo ""

# ── Docker ──────────────────────────────────────────────────
if ! command -v docker &>/dev/null; then
    echo -e "${RED}❌ Docker non installé.${NC}"
    echo "   → https://www.docker.com/products/docker-desktop/"
    exit 1
fi

if ! docker info &>/dev/null; then
    echo -e "${RED}❌ Docker non démarré.${NC}"
    echo "   → Lancez Docker Desktop puis réessayez."
    exit 1
fi
echo -e "${GREEN}✅ Docker prêt${NC}"

# ── .env ────────────────────────────────────────────────────
if [ ! -f .env ]; then
    cp .env.example .env
    echo -e "${YELLOW}📄 .env créé depuis .env.example${NC}"
fi

# ── Build + Start ────────────────────────────────────────────
echo ""
echo "📦 Construction et démarrage des conteneurs..."
echo "   (5-15 minutes la première fois)"
echo ""
docker-compose up -d --build

# ── Attente Ollama ───────────────────────────────────────────
echo ""
echo "⏳ Attente du démarrage d'Ollama..."
MAX=150; WAITED=0
until docker exec ai_ollama curl -sf http://localhost:11434/api/tags >/dev/null 2>&1; do
    sleep 5; WAITED=$((WAITED+5))
    echo "   → ${WAITED}s..."
    if [ $WAITED -ge $MAX ]; then
        echo -e "${YELLOW}⚠️ Timeout Ollama. Continuez manuellement :${NC}"
        echo "   docker exec ai_ollama ollama pull mistral"
        break
    fi
done

# ── Mistral ──────────────────────────────────────────────────
echo ""
echo "🤖 Téléchargement du modèle Mistral (~4 Go)..."
docker exec ai_ollama ollama pull mistral

# ── Résumé ──────────────────────────────────────────────────
echo ""
echo -e "${GREEN}============================================================${NC}"
echo -e "${GREEN}✅ Installation terminée !${NC}"
echo -e "${GREEN}============================================================${NC}"
echo ""
echo "  🌐 Interface Streamlit : http://localhost:8501"
echo "  📡 API FastAPI (docs)  : http://localhost:8000/docs"
echo "  🤖 Ollama              : http://localhost:11434"
echo ""
echo "  Vérifier : docker-compose ps"
echo "  Logs     : docker-compose logs -f"
echo "  Arrêter  : docker-compose down"
echo ""
