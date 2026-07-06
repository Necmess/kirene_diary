@echo off
setlocal enabledelayedexpansion

cd /d "%~dp0"

if not exist ".env" (
    echo [cyrene] .env 파일이 없습니다. .env.example을 복사해서 설정한 뒤 다시 실행하세요.
    exit /b 1
)

if exist ".venv\Scripts\activate.bat" (
    call ".venv\Scripts\activate.bat"
)

if not exist "logs" mkdir "logs"

rem .env에서 CYRENE_MODEL 값을 읽는다 (없으면 기본값 사용)
set "CYRENE_MODEL=gemma3:4b"
for /f "usebackq tokens=1,* delims==" %%A in (".env") do (
    if /i "%%A"=="CYRENE_MODEL" set "CYRENE_MODEL=%%B"
)

tasklist /fi "imagename eq ollama.exe" | find /i "ollama.exe" > nul
if errorlevel 1 (
    echo [cyrene] Ollama가 실행 중이 아닙니다. 시작합니다...
    start "ollama" /min ollama serve
    timeout /t 5 /nobreak > nul
)

echo [cyrene] 모델 확인/다운로드: %CYRENE_MODEL%
ollama pull %CYRENE_MODEL%

:loop
echo [cyrene] Discord 봇 시작 %date% %time%
python discord_bot.py >> "logs\discord_bot.log" 2>&1
echo [cyrene] 봇 종료됨. 10초 후 재시작. %date% %time% >> "logs\discord_bot.log"
timeout /t 10 /nobreak > nul
goto loop
