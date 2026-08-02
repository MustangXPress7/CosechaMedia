@echo off
cd /d "%~dp0"
echo ======================================================
echo    SD IMPORT - Compilar ejecutable
echo ======================================================
echo.

echo [1/2] Verificando dependencias...
python -m pip install -r requirements.txt --quiet

echo [2/2] Compilando ejecutable...
pyinstaller --clean main.spec

echo.
echo Listo: dist\CosechaMedia.exe
pause
