@echo off
REM ===========================================================
REM  LinkedIn Bot - SCHEDULED RUN
REM  Para Windows Task Scheduler. Sleep inicial aleatorio para
REM  nao executar sempre no mesmo horario. Loga tudo em logs/.
REM ===========================================================

setlocal EnableDelayedExpansion

REM --- Diretorio do bot (absoluto, robusto a "Start in" vazio) ---
set "BOT_DIR=C:\Users\pedro\.vscode\bot"
cd /d "%BOT_DIR%" || (
    echo [ERROR] Nao foi possivel acessar %BOT_DIR%
    exit /b 1
)

REM --- Logging ---
if not exist "logs" mkdir "logs"
for /f "tokens=2 delims==" %%I in ('"wmic os get localdatetime /value"') do set "DT=%%I"
set "STAMP=%DT:~0,4%-%DT:~4,2%-%DT:~6,2%_%DT:~8,2%-%DT:~10,2%-%DT:~12,2%"
set "LOG=logs\scheduled_%STAMP%.log"

echo =========================================================== >> "%LOG%"
echo  LinkedIn Bot scheduled run  -  %STAMP% >> "%LOG%"
echo =========================================================== >> "%LOG%"

REM --- Sleep inicial aleatorio (0 a 5400 segundos = 0 a 90 min) ---
REM Usa PowerShell para gerar o numero aleatorio (mais uniforme que %RANDOM%).
for /f "usebackq tokens=*" %%R in (`powershell -NoProfile -Command "Get-Random -Minimum 0 -Maximum 5401"`) do set "SLEEP_SEC=%%R"
if "%SLEEP_SEC%"=="" set "SLEEP_SEC=600"

echo [%TIME%] Sleep inicial aleatorio: %SLEEP_SEC% segundos >> "%LOG%"
echo [%TIME%] Sleep inicial aleatorio: %SLEEP_SEC% segundos

REM 'timeout' espera o tempo definido. /nobreak para nao ser interrompido por tecla.
timeout /t %SLEEP_SEC% /nobreak > nul

echo [%TIME%] Sleep concluido, iniciando execucao do bot... >> "%LOG%"

REM --- Ativacao do venv ---
if exist "venv\Scripts\activate.bat" (
    call "venv\Scripts\activate.bat"
) else (
    echo [WARN] venv nao encontrado em venv\Scripts\activate.bat — usando Python global >> "%LOG%"
)

REM --- Execucao do bot (com unbuffered output) ---
set "PYTHONUNBUFFERED=1"
set "PYTHONIOENCODING=utf-8"

python -u "src\bot_v2.py" >> "%LOG%" 2>&1
set "EXIT_CODE=%ERRORLEVEL%"

echo [%TIME%] Bot finalizado com exit code %EXIT_CODE% >> "%LOG%"

REM --- Desativacao do venv ---
if defined VIRTUAL_ENV (
    call "venv\Scripts\deactivate.bat" 2>nul
)

endlocal & exit /b %EXIT_CODE%
