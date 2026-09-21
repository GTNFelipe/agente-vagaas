@echo off
title Parar Bot Agente de Vagas
echo ========================================================
echo 🛑 ENCERRANDO BOT DO TELEGRAM (AGENTE DE VAGAS)...
echo ========================================================
echo.

powershell -NoProfile -ExecutionPolicy Bypass -Command "$procs = Get-CimInstance Win32_Process | Where-Object { $_.CommandLine -like '*telegram_bot.py*' -or $_.CommandLine -like '*iniciar_bot.bat*' }; if ($procs) { foreach ($p in $procs) { Stop-Process -Id $p.ProcessId -Force; Write-Host ('[OK] Processo encerrado: PID ' + $p.ProcessId + ' (' + $p.Name + ')') } } else { Write-Host '[INFO] Nenhum processo do bot em execucao foi encontrado.' }"

echo.
echo ========================================================
echo Processo concluido.
pause
