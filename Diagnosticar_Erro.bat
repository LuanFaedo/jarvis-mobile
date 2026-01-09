@echo off
title Diagnostico JARVIS V11
echo ===================================================
echo   INICIANDO DIAGNOSTICO DO JARVIS STABLE
echo ===================================================
echo.
echo Tentando abrir o servidor e capturar logs...
echo (Aguarde alguns segundos e feche a janela se o erro aparecer)
echo.

:: Tenta rodar o executável estável e grava o erro
executar_TOTAL.BAT > log_erro_sistema.txt 2>&1

echo.
echo ===================================================
echo   CONCLUIDO. Verifique o arquivo: log_erro_sistema.txt
echo ===================================================
echo.
echo O ERRO ENCONTRADO FOI:
echo ---------------------------------------------------
type log_erro_sistema.txt
echo ---------------------------------------------------
echo.
pause
