@echo off
title PAREAR JARVIS COM TV SAMSUNG
echo ========================================================
echo   INICIANDO PROTOCOLO DE PAREAMENTO TV SAMSUNG
echo ========================================================
echo.
echo 1. Pegue o controle remoto da TV.
echo 2. Fique de olho na tela para aceitar a conexao.
echo.
echo Iniciando script...
echo.

python iot/parear_tv.py

echo.
echo ========================================================
if %errorlevel% neq 0 (
    echo [FALHA] Ocorreu um erro. Verifique as mensagens acima.
) else (
    echo [SUCESSO] Processo finalizado.
)
echo ========================================================
pause
