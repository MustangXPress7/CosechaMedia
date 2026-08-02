#!/bin/bash
# SD IMPORT / CosechaMedia - Compilar ejecutable para macOS
set -e

echo "======================================================"
echo "    SD IMPORT - Compilar ejecutable (macOS)"
echo "======================================================"

cd "$(dirname "$0")"

echo "[1/3] Verificando dependencias..."
python3 -m pip install -r requirements.txt --quiet

echo "[2/3] Compilando ejecutable..."
python3 -m PyInstaller --clean main.spec

echo "[3/3] Listo: dist/CosechaMedia.app"
echo ""
echo "Abre la app con: open dist/CosechaMedia.app"
