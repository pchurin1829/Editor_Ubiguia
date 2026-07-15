@echo off
echo ==========================================
echo   Editor UBIGUIA - Generar EXE
echo ==========================================
echo.

python --version >nul 2>&1
if errorlevel 1 (
    echo ERROR: Python no esta instalado o no esta en PATH.
    pause
    exit /b 1
)

python -m pip show pyinstaller >nul 2>&1
if errorlevel 1 (
    echo Instalando PyInstaller...
    python -m pip install pyinstaller
)

echo.
echo Generando EXE...
python -m PyInstaller --onefile --windowed --name Editor_UBIGUIA src\main.py

echo.
echo Listo. El EXE queda en:
echo dist\Editor_UBIGUIA.exe
echo.
pause
