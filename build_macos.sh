#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"
if [[ "$(uname -s)" != Darwin ]]; then
  echo 'Build the macOS application on a Mac, using its native Python architecture.' >&2
  exit 1
fi
python -c 'import PySide6, cryptography, openpyxl, reportlab, PyInstaller; import platform; print("Building for", platform.machine())'
python test_store.py
python -m PyInstaller --noconfirm --clean --windowed --onedir \
  --name 'DIDAR Connect' --osx-bundle-identifier 'ca.didarmtl.connect' \
  --icon assets/didar-connect.icns --collect-data reportlab main.py
[[ -d 'dist/DIDAR Connect.app' ]]
echo 'Built: dist/DIDAR Connect.app'
echo 'Test first: open -n "dist/DIDAR Connect.app" --args --data-dir "$HOME/DIDAR-Connect-test-v1"'
