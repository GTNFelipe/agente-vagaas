@echo off
title Remover Inicializacao Automatica
echo ========================================================
echo 🗑️ REMOVENDO BOT DA INICIALIZACAO DO WINDOWS
echo ========================================================
echo.

set STARTUP_FOLDER=%APPDATA%\Microsoft\Windows\Start Menu\Programs\Startup
set SHORTCUT_PATH=%STARTUP_FOLDER%\AgenteVagasBot.lnk

if exist "%SHORTCUT_PATH%" (
    del /f /q "%SHORTCUT_PATH%"
    echo ✅ Atalho removido com sucesso da pasta de Inicializacao do Windows!
) else (
    echo ℹ️ Nenhum atalho do bot foi encontrado na pasta Startup.
)

echo.
pause
