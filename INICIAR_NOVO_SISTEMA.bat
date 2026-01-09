@echo off
title JARVIS V12 - PYTHON CORE
echo ===================================================
echo   INICIANDO O CERÉBRO ATUALIZADO (PYTHON)
echo ===================================================
echo.
echo Certifique-se de fechar qualquer janela antiga do Jarvis.
echo.

:: Mata processos antigos
taskkill /F /IM JARVIS.exe /T >nul 2>&1
taskkill /F /IM python.exe /T >nul 2>&1

:: Inicia o App
python app.py
pause