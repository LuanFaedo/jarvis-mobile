@echo off
title COMPILADOR JARVIS V12
echo ===================================================
echo   PREPARANDO AMBIENTE PARA COMPILACAO...
echo ===================================================
echo.
echo Instalando dependencias necessarias...
pip install pyinstaller flask flask-socketio pycloudflared openai ollama edge-tts python-dotenv speechrecognition pydub pillow pytesseract requests

echo.
echo ===================================================
echo   COMPILANDO JARVIS.EXE (MODO TURBO)
echo ===================================================
echo.
pyinstaller --onefile --noconsole ^
    --name "JARVIS" ^
    --add-data "templates;templates" ^
    --add-data "static;static" ^
    --add-data "tessdata;tessdata" ^
    --add-data "download_url.toml;." ^
    --hidden-import "simple_websocket" ^
    --hidden-import "wsproto" ^
    --hidden-import "engineio.async_drivers.threading" ^
    --icon "static/favicon.ico" ^
    app.py

echo.
echo ===================================================
echo   COMPILACAO CONCLUIDA!
echo   O novo arquivo esta na pasta 'dist'.
echo ===================================================
pause
