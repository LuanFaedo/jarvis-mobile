@echo off
echo =========================================
echo      INICIANDO ESPELHAMENTO ANDROID
echo =========================================
echo.
echo Certifique-se que:
echo 1. O modo Desenvolvedor estah ativado no celular.
echo 2. A depuracao USB estah ativada.
echo 3. O cabo USB estah conectado.
echo.
cd /d "%~dp0\tools\scrcpy\scrcpy-win64-v2.4"
start scrcpy.exe --stay-awake --window-title="JARVIS - Espelho Android" --max-size=1024 --always-on-top
echo Espelhamento iniciado em janela separada.
exit
