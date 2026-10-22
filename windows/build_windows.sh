#!/usr/bin/env bash
set -euo pipefail

ROOT="$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)"
WINDOWS_DIR="$ROOT/windows"
BUILD_DIR="$WINDOWS_DIR/build"
OUTPUT_DIR="$ROOT/dist/windows"
APP_OUTPUT="$OUTPUT_DIR/Moon Clock Demo.exe"
SETUP_OUTPUT="$OUTPUT_DIR/MoonClock-Demo-Setup-0.1.0-demo1.exe"
WINE_PYTHON='C:\Python313\python.exe'
NSIS_COMPILER='C:\Program Files (x86)\NSIS\makensis.exe'

if [[ -e "$BUILD_DIR" || -e "$APP_OUTPUT" || -e "$SETUP_OUTPUT" ]]; then
    printf 'Refusing to overwrite existing Windows demo build output.\n' >&2
    exit 1
fi

mkdir -p "$BUILD_DIR/app" "$OUTPUT_DIR"
APP_SCRIPT="$(winepath -w "$WINDOWS_DIR/app_windows.py")"
ROOT_WINDOWS="$(winepath -w "$ROOT")"
APP_WORK="$(winepath -w "$BUILD_DIR/app")"
OUTPUT_WINDOWS="$(winepath -w "$OUTPUT_DIR")"
NSIS_SCRIPT="$(winepath -w "$WINDOWS_DIR/moon_clock_demo.nsi")"

WINEDEBUG=-all wine "$WINE_PYTHON" -m PyInstaller \
    --noconfirm \
    --clean \
    --onefile \
    --windowed \
    --name "Moon Clock Demo" \
    --paths "$ROOT_WINDOWS" \
    --add-data "$ROOT_WINDOWS\\assets;assets" \
    --add-data "$ROOT_WINDOWS\\DEMO-LICENSE.txt;." \
    --add-data "$ROOT_WINDOWS\\THIRD-PARTY-NOTICES.txt;." \
    --add-data "$ROOT_WINDOWS\\third-party-licenses;third-party-licenses" \
    --icon "$ROOT_WINDOWS\\assets\\purple-celestial-background.png" \
    --workpath "$APP_WORK" \
    --specpath "$APP_WORK" \
    --distpath "$OUTPUT_WINDOWS" \
    "$APP_SCRIPT"

WINEDEBUG=-all wine "$NSIS_COMPILER" "/DPROJECT_ROOT=$ROOT_WINDOWS" "$NSIS_SCRIPT"
printf 'Created %s\n' "$SETUP_OUTPUT"
