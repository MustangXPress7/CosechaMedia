@echo off
cd /d "%~dp0"
echo ======================================================
echo    SD IMPORT - Modo Testing
echo ======================================================
echo.

python -c "import PySide6" 2>nul
if errorlevel 1 (
    echo Instalando PySide6...
    python -m pip install PySide6 --quiet
)

echo Iniciando aplicacion...
echo.
python main.py
echo.
echo --- Aplicacion cerrada ---
pause
