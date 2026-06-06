@echo off
set PYTHONIOENCODING=utf-8
echo =========================================
echo        Iniciando Automyx Platform
echo =========================================

echo [1/4] Verificando dependencias de Python...
pip install -r requirements.txt >nul 2>&1

echo [2/4] Limpiando procesos huerfanos de Chromium...
taskkill /F /IM chrome.exe /T >nul 2>&1
taskkill /F /IM chromium.exe /T >nul 2>&1

echo [3/4] Iniciando Servidor de WhatsApp Bot (Node.js)...
cd whatsapp_api
start "Automyx WhatsApp Bot" cmd /k "npm install && node server.js"
cd ..

echo [4/4] Iniciando Motor de IA (FastAPI)...
python -m uvicorn api.main:app --host 0.0.0.0 --port 8000 --reload

