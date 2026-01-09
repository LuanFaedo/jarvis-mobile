@echo off
title INICIALIZADOR JARVIS V11
echo ===================================================
echo   LIMPANDO AMBIENTE E LIBERANDO ACESSO...
echo ===================================================
taskkill /F /IM JARVIS.exe /T >nul 2>&1
taskkill /F /IM cloudflared.exe /T >nul 2>&1
timeout /t 2 /nobreak >nul

echo.
echo ===================================================
echo   INICIANDO SERVIDOR JARVIS...
echo ===================================================
echo Se o Windows pedir permissao, clique em PERMITIR.
echo.

:: Tenta rodar a versao mais estavel encontrada
if exist JARVIS_STABLE.exe (
    start JARVIS_STABLE.exe
) else (
    start JARVIS.exe
)

echo.
echo JARVIS iniciado com sucesso! 
echo Aguarde o link aparecer na janela do servidor.
echo.
pause
