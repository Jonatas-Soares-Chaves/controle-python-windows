@echo off
setlocal

cd /d "%~dp0"

set "APP_NAME=ControleBrilho"
set "APP_EXE=%~dp0dist\%APP_NAME%.exe"
set "VENV_DIR=%~dp0..\..\work\controle_brilho_venv"
set "PYTHON_EXE=%VENV_DIR%\Scripts\python.exe"
set "CREATE_VENV_CMD="

echo Preparando Controle de Brilho...

py -3.13 -c "import sys" >nul 2>&1
if not errorlevel 1 set "CREATE_VENV_CMD=py -3.13"

if not defined CREATE_VENV_CMD (
    py -3.12 -c "import sys" >nul 2>&1
    if not errorlevel 1 set "CREATE_VENV_CMD=py -3.12"
)

if not defined CREATE_VENV_CMD (
    py -3.11 -c "import sys" >nul 2>&1
    if not errorlevel 1 set "CREATE_VENV_CMD=py -3.11"
)

if not defined CREATE_VENV_CMD (
    py -3 -c "import sys" >nul 2>&1
    if not errorlevel 1 set "CREATE_VENV_CMD=py -3"
)

if not defined CREATE_VENV_CMD (
    python -c "import sys" >nul 2>&1
    if not errorlevel 1 set "CREATE_VENV_CMD=python"
)

if not defined CREATE_VENV_CMD (
    echo Python nao encontrado.
    exit /b 1
)

if exist "%PYTHON_EXE%" (
    "%PYTHON_EXE%" -c "import sys; raise SystemExit(0 if sys.version_info[:2] in ((3, 11), (3, 12), (3, 13), (3, 14)) else 1)" >nul 2>&1
    if errorlevel 1 (
        rmdir /s /q "%VENV_DIR%" >nul 2>&1
    )
)

if not exist "%PYTHON_EXE%" (
    %CREATE_VENV_CMD% -m venv "%VENV_DIR%"
    if errorlevel 1 exit /b 1
)

echo Fechando versoes abertas...
powershell -NoProfile -ExecutionPolicy Bypass -Command ^
    "$targets = Get-CimInstance Win32_Process | Where-Object { $_.Name -eq 'ControleBrilho.exe' -or ($_.Name -like 'pythonw*' -and $_.CommandLine -like '*controle_brilho.pyw*') }; foreach ($p in $targets) { Stop-Process -Id $p.ProcessId -Force -ErrorAction SilentlyContinue }" >nul 2>&1

echo Instalando dependencias...
"%PYTHON_EXE%" -m pip install --upgrade pip
if errorlevel 1 exit /b 1

"%PYTHON_EXE%" -m pip install --only-binary=:all: -r requirements.txt
if errorlevel 1 (
    "%PYTHON_EXE%" -m pip install -r requirements.txt
)
if errorlevel 1 exit /b 1

echo Gerando executavel...
"%PYTHON_EXE%" -m PyInstaller ^
    --noconfirm ^
    --onefile ^
    --windowed ^
    --name "%APP_NAME%" ^
    --collect-all winrt ^
    --hidden-import winrt._winrt ^
    --hidden-import winrt._winrt_windows_foundation ^
    --hidden-import winrt._winrt_windows_foundation_collections ^
    --hidden-import winrt._winrt_windows_storage_streams ^
    --hidden-import winrt._winrt_windows_media_control ^
    --hidden-import winrt.windows.media.control ^
    --hidden-import winrt.windows.foundation ^
    --hidden-import winrt.windows.foundation.collections ^
    --hidden-import winrt.windows.storage.streams ^
    controle_brilho.pyw
if errorlevel 1 exit /b 1

echo Iniciando app...
start "" "%APP_EXE%"

endlocal
exit /b 0
