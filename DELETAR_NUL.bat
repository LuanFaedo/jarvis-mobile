@echo off
echo Deletando arquivo "nul" da pasta D:\compartilhado\Projetos\jarvis01\jarvis-mobile01...
echo.

REM Metodo 1: Caminho longo
del "\\?\D:\compartilhado\Projetos\jarvis01\jarvis-mobile01\nul" 2>NUL

REM Metodo 2: Renomear primeiro
ren "\\?\D:\compartilhado\Projetos\jarvis01\jarvis-mobile01\nul" "temp_delete.tmp" 2>NUL
del "C:\WORD\temp_delete.tmp" 2>NUL

REM Metodo 3: Forcar com attrib
attrib -r -s -h "\\?\D:\compartilhado\Projetos\jarvis01\jarvis-mobile01\nul" 2>NUL
del "\\?\D:\compartilhado\Projetos\jarvis01\jarvis-mobile01\nul" 2>NUL

echo.
if exist "D:\compartilhado\Projetos\jarvis01\jarvis-mobile01\nul" (
    echo [FALHOU] O arquivo ainda existe. Execute como Administrador.
) else (
    echo [SUCESSO] Arquivo deletado!
)
echo.
pause
