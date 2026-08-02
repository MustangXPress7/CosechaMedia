#!/bin/bash

# Verificar si Python 3 está instalado
if ! command -v python3 &> /dev/null; then
    echo "Error: Python 3 no está instalado. Por favor, instálalo desde python.org"
    exit 1
fi

echo "======================================================"
echo "    INICIADOR DE SD IMPORT (Mac / Linux)"
echo "======================================================"
echo ""

echo "[1/3] Verificando dependencias..."
python3 -m pip install PySide6 PyInstaller --quiet

echo ""
echo "[2/3] Generando ejecutable..."
# Usamos python3 para asegurar la compatibilidad
python3 -m PyInstaller --noconsole --onefile --path.app=app --clean main.py

echo ""
echo "[3/3] ¡Listo! Abriendo aplicación..."
echo ""
# Esperar un poco para que el usuario vea el mensaje
sleep 3

# Abrir la aplicación
if [[ "$OSTYPE" == "darwin"* ]]; then
    open dist/main
else
    ./dist/main &
fi
