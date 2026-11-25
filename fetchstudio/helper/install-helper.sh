#!/bin/sh
# One-time setup of the Fetch Studio "cal" helper. Run as root from the folder that contains this file:
#   sudo sh install-helper.sh              install
#   sudo sh install-helper.sh --uninstall  remove
set -eu
HELPER_DIR=/usr/libexec/fetchstudio
POLICY=/usr/share/polkit-1/actions/io.github.bobbycomet.fetchstudio.policy
[ "$(id -u)" -eq 0 ] || { echo "Run this as root:  sudo sh $0 ${1:-}" >&2; exit 1; }

if [ "${1:-}" = "--uninstall" ]; then
  rm -f "$HELPER_DIR/fetchstudio-cal-helper" "$POLICY"; rmdir "$HELPER_DIR" 2>/dev/null || true
  echo "Fetch Studio helper removed."; exit 0
fi

here=$(cd "$(dirname "$0")" && pwd)
[ -f "$here/fetchstudio-cal-helper" ] && [ -f "$here/io.github.bobbycomet.fetchstudio.policy" ] || { echo "Helper files not found next to this script." >&2; exit 1; }
install -d -m 0755 -o root -g root "$HELPER_DIR"
install -m 0755 -o root -g root "$here/fetchstudio-cal-helper" "$HELPER_DIR/fetchstudio-cal-helper"
install -d -m 0755 -o root -g root "$(dirname "$POLICY")"
install -m 0644 -o root -g root "$here/io.github.bobbycomet.fetchstudio.policy" "$POLICY"
echo "Installed. Fetch Studio can now install 'cal' for you (administrator password required each time)."
