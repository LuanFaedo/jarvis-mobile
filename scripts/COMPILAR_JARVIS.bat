@echo off
title COMPILADOR JARVIS V12 (AUTO)
echo ===================================================
echo   INICIANDO COMPILACAO ROBUSTA...
echo ===================================================

:: Garante instalacao do PyInstaller
echo [0/3] Verificando dependencias...
python -m pip install --upgrade pyinstaller

:: Limpa builds anteriores
if exist build rmdir /s /q build
if exist dist rmdir /s /q dist
if exist JARVIS.spec del JARVIS.spec

echo.
echo [1/3] Compilando com PyInstaller...
python -m PyInstaller --noconfirm --onefile --windowed --clean ^
    --name "JARVIS" ^
    --add-data "templates;templates" ^
    --add-data "static;static" ^
    --add-data "tessdata;tessdata" ^
    --add-data "download_url.toml;." ^
    --hidden-import "engineio.async_drivers.threading" ^
    --hidden-import "flask_socketio" ^
    --hidden-import "socketio" ^
    --hidden-import "simple_websocket" ^
    --hidden-import "wsproto" ^
    --hidden-import "pydub" ^
    --hidden-import "speech_recognition" ^
    --hidden-import "win32timezone" ^
    --hidden-import "pyautogui" ^
    --hidden-import "psutil" ^
    --hidden-import "pyscreeze" ^
    --hidden-import "pygetwindow" ^
    --hidden-import "mouseinfo" ^
    app.py

echo.
echo [2/3] Movendo executavel para a raiz...
if exist "dist\JARVIS.exe" (
    move /Y "dist\JARVIS.exe" "JARVIS.exe"
    echo [SUCESSO] JARVIS.exe atualizado na raiz!
) else (
    echo [ERRO] O arquivo dist\JARVIS.exe nao foi encontrado. Compilacao falhou.
    exit /b 1
)

echo.
echo [3/3] Limpeza final...
rmdir /s /q build
rmdir /s /q dist
del JARVIS.spec

echo ===================================================
echo   PROCESSO FINALIZADO COM SUCESSO.
echo ===================================================
