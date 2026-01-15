@echo off
echo Deletando arquivo "nul" da pasta C:\WORD...
echo.

REM Metodo 1: Caminho longo
del "\\?\C:\WORD\nul" 2>NUL

REM Metodo 2: Renomear primeiro
ren "\\?\C:\WORD\nul" "temp_delete.tmp" 2>NUL
del "C:\WORD\temp_delete.tmp" 2>NUL

REM Metodo 3: Forcar com attrib
attrib -r -s -h "\\?\C:\WORD\nul" 2>NUL
del "\\?\C:\WORD\nul" 2>NUL

echo.
if exist "C:\WORD\nul" (
    echo [FALHOU] O arquivo ainda existe. Execute como Administrador.
) else (
    echo [SUCESSO] Arquivo deletado!
)
echo.
pause
