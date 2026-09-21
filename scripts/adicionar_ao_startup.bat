@echo off
title Configurar Inicializacao Automatica com o Windows
echo ========================================================
echo 🚀 ADICIONANDO BOT PARA INICIAR AUTOMATICAMENTE COM O WINDOWS
echo ========================================================
echo.

set SCRIPT_VBS=%~dp0iniciar_bot_silencioso.vbs
set STARTUP_FOLDER=%APPDATA%\Microsoft\Windows\Start Menu\Programs\Startup
set SHORTCUT_PATH=%STARTUP_FOLDER%\AgenteVagasBot.lnk

powershell -NoProfile -ExecutionPolicy Bypass -Command "$ws = New-Object -ComObject WScript.Shell; $s = $ws.CreateShortcut('%SHORTCUT_PATH%'); $s.TargetPath = '%SCRIPT_VBS%'; $s.WorkingDirectory = '%~dp0'; $s.Save()"

if exist "%SHORTCUT_PATH%" (
    echo ✅ Atalho criado com sucesso na pasta de Inicializacao do Windows!
    echo    Caminho: %SHORTCUT_PATH%
    echo.
    echo O bot agora iniciara em segundo plano sempre que voce ligar o PC.
) else (
    echo ❌ Ocorreu um erro ao criar o atalho.
)

echo.
pause
