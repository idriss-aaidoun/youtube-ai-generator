FROM python:3.11-slim

# ── Dépendances système ─────────────────────────────────────────────────────
RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg \
    wget \
    curl \
    libsndfile1 \
    espeak-ng \
    imagemagick \
    libmagickwand-dev \
    ghostscript \
    fonts-dejavu-core \
    fonts-dejavu-extra \
    && rm -rf /var/lib/apt/lists/*

# Corriger la politique ImageMagick (nécessaire pour MoviePy)
RUN [ -f /etc/ImageMagick-6/policy.xml ] && \
    sed -i 's/rights="none" pattern="PDF"/rights="read|write" pattern="PDF"/' \
    /etc/ImageMagick-6/policy.xml || true

WORKDIR /app

# ── Étape 1 : setuptools + wheel d'abord (OBLIGATOIRE avant openai-whisper) ─
# openai-whisper utilise setup.py qui requiert pkg_resources (fourni par setuptools)
RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir setuptools wheel

# ── Étape 2 : PyTorch CPU uniquement (évite de télécharger ~2 Go de CUDA) ──
# On passe --extra-index-url pour avoir la version +cpu
RUN pip install --no-cache-dir \
    torch \
    torchaudio \
    --index-url https://download.pytorch.org/whl/cpu

# ── Étape 3 : Whisper (dépend de torch et setuptools) ──────────────────────
RUN pip install --no-cache-dir openai-whisper==20231117 --no-build-isolation

# ── Étape 4 : Reste des dépendances Python ─────────────────────────────────
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# ── Structure des dossiers de sortie ───────────────────────────────────────
RUN mkdir -p \
    /app/models/piper \
    /app/outputs/videos \
    /app/outputs/audio \
    /app/outputs/images \
    /app/assets \
    /app/db

# ── Piper TTS binary ────────────────────────────────────────────────────────
# Si le téléchargement échoue, espeak-ng est utilisé comme fallback automatique
RUN wget -q \
    https://github.com/rhasspy/piper/releases/download/2023.11.14-2/piper_linux_x86_64.tar.gz \
    -O /tmp/piper.tar.gz \
    && tar -xzf /tmp/piper.tar.gz -C /app/models/piper \
    && rm /tmp/piper.tar.gz \
    && chmod +x /app/models/piper/piper/piper \
    || echo "[INFO] Piper non disponible — fallback espeak-ng actif"

# ── Code source ─────────────────────────────────────────────────────────────
COPY . .

ENV PYTHONPATH=/app
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

EXPOSE 8000

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
