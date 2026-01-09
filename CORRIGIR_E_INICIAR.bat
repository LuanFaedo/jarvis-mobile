@echo off
title JARVIS - MODO CORRIGIDO
echo ===================================================
echo   PARANDO SISTEMA ANTERIOR...
echo ===================================================
taskkill /F /IM python.exe /T >nul 2>&1
taskkill /F /IM node.exe /T >nul 2>&1
taskkill /F /IM cloudflared.exe /T >nul 2>&1
timeout /t 2 >nul

echo ===================================================
echo   INICIANDO JARVIS (RESTAURADO)
echo ===================================================
echo.
echo DICA: Se voce fechar esta janela, o Jarvis desliga.
echo Para cancelar apenas uma acao, tente dizer "Pare" ou "Cancelar" no chat.
echo.
python interface_desktop.py
pause
