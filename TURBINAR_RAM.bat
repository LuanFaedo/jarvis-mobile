@echo off
title TURBINAR RAM VIRTUAL - JARVIS
echo ===================================================
echo   CONFIGURANDO 20GB DE MEMORIA ADICIONAL (SSD)
echo ===================================================
echo.
echo Solicitando permissoes de Administrador...
echo.

:: Script PowerShell para ajustar o Pagefile
powershell -Command "Start-Process powershell -ArgumentList '-NoProfile -ExecutionPolicy Bypass -Command \"$sys = Get-CimInstance Win32_ComputerSystem; $sys | Set-CimInstance -Property @{AutomaticManagedPagefile = $false}; $page = Get-CimInstance Win32_PageFileSetting; if ($page) { $page | Remove-CimInstance }; New-CimInstance -ClassName Win32_PageFileSetting -Property @{Name=''C:\pagefile.sys''; InitialSize=20480; MaximumSize=30720}\" -Verb RunAs"

echo.
echo ===================================================
echo   PROCEDIMENTO ENVIADO!
echo ===================================================
echo 1. Se apareceu uma janela azul pedindo "Sim", clique nela.
echo 2. REINICIE O COMPUTADOR agora para aplicar as alteracoes.
echo 3. Apos reiniciar, o Jarvis conseguira carregar o modelo 32B.
echo ===================================================
pause
