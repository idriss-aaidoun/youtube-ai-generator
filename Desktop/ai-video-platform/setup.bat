@echo off
setlocal enabledelayedexpansion

REM Se positionner dans le dossier du script (corrige l'erreur "not found")
cd /d "%~dp0"

echo.
echo ============================================================
echo   AI Video Generator v2.0 - Multi-Agent Architecture
echo   Installation automatique Windows
echo ============================================================
echo.
echo [INFO] Dossier : %CD%
echo.

REM ── Verification Docker ──────────────────────────────────────
docker --version >nul 2>&1
if errorlevel 1 (
    echo [ERREUR] Docker n'est pas installe.
    echo    Telecharger : https://www.docker.com/products/docker-desktop/
    pause & exit /b 1
)

docker info >nul 2>&1
if errorlevel 1 (
    echo [ERREUR] Docker n'est pas demarre.
    echo    Ouvrir Docker Desktop et reessayer.
    pause & exit /b 1
)
echo [OK] Docker detecte et demarre.

REM ── Fichier .env ──────────────────────────────────────────────
if not exist .env (
    copy .env.example .env >nul
    echo [INFO] .env cree depuis .env.example
)

REM ── Build + Start ─────────────────────────────────────────────
echo.
echo [INFO] Construction et demarrage des conteneurs...
echo        (5-15 minutes la premiere fois)
echo.
docker compose up -d --build
if errorlevel 1 (
    echo [ERREUR] docker compose a echoue.
    echo    Verifiez que docker-compose.yml est dans ce dossier : %CD%
    pause & exit /b 1
)

REM ── Attente Ollama ────────────────────────────────────────────
echo.
echo [INFO] Attente du demarrage d'Ollama (60 secondes)...
timeout /t 60 /nobreak >nul

REM ── Telechargement Mistral ────────────────────────────────────
echo.
echo [INFO] Telechargement du modele Mistral (~4 Go)...
echo        Cela peut prendre plusieurs minutes selon votre connexion.
echo.
docker exec ai_ollama ollama pull mistral
if errorlevel 1 (
    echo [ATTENTION] Le telechargement de Mistral a echoue.
    echo    Reessayez manuellement : docker exec ai_ollama ollama pull mistral
)

REM ── Resume ────────────────────────────────────────────────────
echo.
echo ============================================================
echo  [OK] Installation terminee !
echo ============================================================
echo.
echo   Interface Streamlit : http://localhost:8501
echo   API FastAPI          : http://localhost:8000/docs
echo   Ollama               : http://localhost:11434
echo.
echo   Verifier les services : docker compose ps
echo   Logs en temps reel   : docker compose logs -f
echo   Arreter              : docker compose down
echo.
pause
