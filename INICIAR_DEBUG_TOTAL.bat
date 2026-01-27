@echo off
title JARVIS - PAINEL DE CONTROLE (DEBUG)
color 0A

echo ===================================================
echo   INICIANDO MODO DE DIAGNOSTICO TOTAL (MATRIX)
echo ===================================================
echo.
echo [1/2] Iniciando CEREBRO (Python/Flask) em nova janela...
start "JARVIS BRAIN (PYTHON)" cmd /k "python app.py --no-bot --debug"

echo.
echo [2/2] Iniciando CORPO (WhatsApp/Node) em nova janela...
cd jarvis-mcp-whatsapp
start "JARVIS BODY (WHATSAPP)" cmd /k "node index.js"

echo.
echo [OK] Sistemas iniciados separadamente.
echo Verifique as duas janelas abertas para logs detalhados.
echo.
pause
