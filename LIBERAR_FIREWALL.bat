@echo off
echo =========================================
echo    LIBERANDO PORTA 5000 NO FIREWALL
echo =========================================
echo.

:: Verifica se esta rodando como admin
net session >nul 2>&1
if %errorlevel% neq 0 (
    echo ERRO: Execute este script como ADMINISTRADOR!
    echo Clique com botao direito e selecione "Executar como administrador"
    pause
    exit /b 1
)

echo Removendo regra antiga (se existir)...
netsh advfirewall firewall delete rule name="Jarvis Server Port 5000" >nul 2>&1

echo Adicionando regra de entrada TCP...
netsh advfirewall firewall add rule name="Jarvis Server Port 5000" dir=in action=allow protocol=TCP localport=5000

echo Adicionando regra de saida TCP...
netsh advfirewall firewall add rule name="Jarvis Server Port 5000 OUT" dir=out action=allow protocol=TCP localport=5000

echo.
echo =========================================
echo    FIREWALL CONFIGURADO COM SUCESSO!
echo =========================================
echo.
echo Seu IP local:
ipconfig | findstr "IPv4"
echo.
echo Use este IP no app Flutter!
echo Exemplo: http://192.168.3.101:5000
echo.
pause
