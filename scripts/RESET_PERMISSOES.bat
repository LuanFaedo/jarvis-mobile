@echo off
title RESET DE ACESSO JARVIS
echo ===================================================
echo   LIBERANDO ACESSO AOS ARQUIVOS DA PASTA...
echo ===================================================
icacls . /grant %username%:(OI)(CI)F /T
attrib -r -s memoria\*.* /S /D
attrib -r -s historico\*.* /S /D
echo.
echo Acesso liberado com sucesso!
echo Agora rode o INICIAR_JARVIS.bat
pause
