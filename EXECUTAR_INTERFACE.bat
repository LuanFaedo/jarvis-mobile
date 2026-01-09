@echo off
title LAUNCHER JARVIS V12 - SYSTEM INTEGRATION
color 0B

echo ===================================================
echo   INICIALIZANDO ECOSSISTEMA JARVIS
echo ===================================================

:: 1. Limpeza de Processos Anteriores
echo [1/4] Parando processos antigos...
taskkill /F /IM python.exe /T >nul 2>&1
taskkill /F /IM JARVIS.exe /T >nul 2>&1

:: 2. Inicia o Supervisor (Cérebro Híbrido)
echo [2/4] Ativando Supervisor (Gemini + Ollama)...
start "JARVIS SUPERVISOR (NAO FECHE)" /min cmd /k "color 0E && python supervisor_auto.py"

:: 3. Aguarda um pouco para o Supervisor subir
timeout /t 2 >nul

:: 4. Inicia a Interface Principal
echo [3/4] Carregando Interface Grafica...
echo.
echo ===================================================
echo   TUDO PRONTO!
echo   - Janela Amarela: Supervisor (Logs de IA)
echo   - Janela App: Jarvis Chat
echo ===================================================
echo.

python interface_desktop.py
pause