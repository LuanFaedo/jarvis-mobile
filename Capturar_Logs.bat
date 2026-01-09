@echo off
title JARVIS LOG COLLECTOR
echo Iniciando JARVIS e capturando atividade...
echo Pressione CTRL+C para parar e salvar o log.
echo.
JARVIS.exe > jarvis_activity.log 2>&1
pause
