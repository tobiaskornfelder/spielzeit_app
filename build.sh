#!/usr/bin/env bash
set -e

# immer vom Skript-Ordner aus arbeiten
cd "$(dirname "$0")"

# alte Builds aufräumen
rm -rf build dist *.spec

# App bauen (achtet auf ZWEI Minusstriche "--")
pyinstaller --noconfirm --windowed \
  --name "Spielzeitberechnung" \
  --icon resources/spielzeit_icon.icns \
  --add-data "resources:resources" \
  main.py

echo "✅ Build fertig: dist/Spielzeitberechnung.app"
echo "Tipp: Öffne die App manuell aus dem Finder oder per:"
echo "open \"dist/Spielzeitberechnung.app\""