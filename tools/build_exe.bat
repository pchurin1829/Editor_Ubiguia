@echo off
setlocal
cd /d "%~dp0"

python --version >nul 2>&1
if errorlevel 1 (
    echo ERROR: Python no esta instalado.
    pause
    exit /b 1
)

python -m pip install --upgrade pyinstaller openai
if errorlevel 1 (
    echo ERROR: no se pudieron instalar dependencias.
    pause
    exit /b 1
)

if exist build rmdir /s /q build
if exist dist rmdir /s /q dist
if exist Editor_UBIGUIA.spec del /q Editor_UBIGUIA.spec

python -m PyInstaller ^
  --noconfirm ^
  --clean ^
  --onefile ^
  --windowed ^
  --name Editor_UBIGUIA ^
  --collect-all openai ^
  --add-data "templates;templates" ^
  src\main.py

if errorlevel 1 (
    echo ERROR: fallo la generacion del EXE.
    pause
    exit /b 1
)

echo.
echo EXE generado en:
echo %CD%\dist\Editor_UBIGUIA.exe
pause
