@echo off
title SUPER INICIADOR JARVIS
echo ===================================================
echo   LIMPANDO PROCESSOS TRAVADOS...
echo ===================================================
taskkill /F /IM JARVIS.exe /T >nul 2>&1
taskkill /F /IM cloudflared.exe /T >nul 2>&1
timeout /t 2 >nul

echo.
echo ===================================================
echo   INICIANDO JARVIS COM PERMISSAO TOTAL
echo ===================================================
echo.
echo Se o Windows perguntar, clique em "SIM" ou "PERMITIR".
echo.
start JARVIS.exe
echo.
echo JARVIS iniciado. Verifique o link na janela que abriu.
timeout /t 5
exit
