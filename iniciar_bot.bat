@echo off
title Agente de Vagas - Bot Telegram
cd /d "%~dp0"
echo ========================================================
echo 🤖 INICIANDO BOT DO TELEGRAM DO AGENTE DE VAGAS...
echo ========================================================

:LOOP
echo [%TIME%] Iniciando processo do Bot Telegram...
if exist ".venv\Scripts\python.exe" (
    ".venv\Scripts\python.exe" "modules\telegram_bot.py"
) else if exist "venv\Scripts\python.exe" (
    "venv\Scripts\python.exe" "modules\telegram_bot.py"
) else (
    python "modules\telegram_bot.py"
)

echo.
echo ⚠️ [AVISO] O processo do bot foi interrompido. Reiniciando em 5 segundos...
timeout /t 5 /nobreak >nul
goto LOOP
