#!/usr/bin/env bash
set -euo pipefail

ROOT="$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)"
DIST="$ROOT/dist"
PACKAGE_NAME="moon-clock-demo"
VERSION="0.1.0~demo1"
OUTPUT="$DIST/${PACKAGE_NAME}_${VERSION}_all.deb"

if [[ -e "$OUTPUT" ]]; then
    printf 'Refusing to overwrite existing build output: %s\n' "$OUTPUT" >&2
    exit 1
fi

mkdir -p "$DIST"
STAGE="$(mktemp -d "$DIST/.moon-clock-demo-deb.XXXXXX")"
trap 'rm -rf -- "$STAGE"' EXIT
ROOTFS="$STAGE/root"
mkdir -p "$ROOTFS/DEBIAN" "$ROOTFS/opt/moon-clock-demo" "$ROOTFS/usr/share/applications"

cp "$ROOT/app_linux.py" "$ROOTFS/opt/moon-clock-demo/app.py"
cp "$ROOT/moon_phase.py" "$ROOT/README.md" "$ROOT/DEMO-LICENSE.txt" "$ROOT/THIRD-PARTY-NOTICES.txt" "$ROOTFS/opt/moon-clock-demo/"
cp -R "$ROOT/assets" "$ROOTFS/opt/moon-clock-demo/assets"
chmod -R a+rX "$ROOTFS/opt/moon-clock-demo"

cat > "$ROOTFS/opt/moon-clock-demo/run_moon_clock_demo.sh" <<'EOF'
#!/usr/bin/env bash
set -euo pipefail
exec python3 /opt/moon-clock-demo/app.py
EOF
chmod 0755 "$ROOTFS/opt/moon-clock-demo/run_moon_clock_demo.sh"

cat > "$ROOTFS/DEBIAN/control" <<EOF
Package: $PACKAGE_NAME
Version: $VERSION
Section: utils
Priority: optional
Architecture: all
Depends: python3, python3-gi, gir1.2-gtk-3.0, gir1.2-gdkpixbuf-2.0
Maintainer: TarotByAndrew.com
Description: Moon Clock offline demonstration
 Moon Clock Demo displays local time, the current Moon phase, next major phase,
 and calendar previews. Lunar age and illumination are reserved for the paid edition.
EOF

cat > "$ROOTFS/usr/share/applications/moon-clock-demo.desktop" <<'EOF'
[Desktop Entry]
Name=Moon Clock Demo
Comment=Moon phase clock and calendar demonstration
Exec=/opt/moon-clock-demo/run_moon_clock_demo.sh
Icon=weather-clear-night
Terminal=false
Type=Application
Categories=Utility;Education;
StartupNotify=true
EOF

dpkg-deb --build --root-owner-group "$ROOTFS" "$OUTPUT" >/dev/null
printf 'Created %s\n' "$OUTPUT"
