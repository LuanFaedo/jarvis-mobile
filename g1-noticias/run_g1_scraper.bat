@echo off
REM ==========================================================
REM   run_g1_scraper.bat – Executa g1_scraper.py
REM ==========================================================
echo.
echo ==============================
echo  INICIANDO SCRAPER G1
echo ==============================
echo.

REM ----- Verificar e instalar dependências (requests, beautifulsoup4) -----
python -c "import sys, subprocess, pkgutil; 
missing = []; 
for pkg in ['requests','beautifulsoup4']: 
    if not pkgutil.find_loader(pkg): missing.append(pkg); 
if missing: subprocess.check_call([sys.executable, '-m', 'pip', 'install'] + missing)" 

REM ----- Executar o script -----
python "%~dp0g1_scraper.py"

echo.
echo ========== FINALIZADO ==========
pause