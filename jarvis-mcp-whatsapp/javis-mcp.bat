@echo off
title Jarvis WhatsApp Interface
cd /d "%~dp0"

echo ---------------------------------------------------
echo        INICIANDO INTERFACE DO JARVIS (WHATSAPP)
echo ---------------------------------------------------
echo.
echo Certifique-se que o "app.py" (Cerebro) esta rodando na pasta anterior.
echo.

call npm start

if %ERRORLEVEL% NEQ 0 (
    echo.
    echo [ERRO] O sistema parou inesperadamente.
    echo Verifique as mensagens de erro acima.
    pause
) else (
    echo.
    echo Sistema encerrado.
    pause
)
