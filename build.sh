#!/usr/bin/env bash
# Build Pigmy Backup for the current platform (Linux or macOS).
# Usage: ./build.sh --version X.X.X
set -euo pipefail

# ── Argument parsing ──────────────────────────────────────────────────────────
VERSION=""
while [[ $# -gt 0 ]]; do
  case "$1" in
    --version) VERSION="$2"; shift 2 ;;
    *) echo "Unknown argument: $1" >&2; exit 1 ;;
  esac
done

if [[ -z "$VERSION" ]]; then
  echo "Usage: $0 --version X.X.X" >&2
  exit 1
fi

if ! [[ "$VERSION" =~ ^[0-9]+\.[0-9]+\.[0-9]+$ ]]; then
  echo "Version must be X.X.X format (e.g. 2.1.3)" >&2
  exit 1
fi

# Always run from the project root regardless of where the script is called from
cd "$(dirname "$0")"

OS="$(uname -s)"
case "$OS" in
  Darwin) PLATFORM="macos" ;;
  *)      PLATFORM="linux" ;;
esac

PLATFORM_DIR="releases/$VERSION/$PLATFORM"

echo "=============================="
echo " Pigmy Backup — Build $VERSION"
echo " Platform : $PLATFORM"
echo " Output   : $PLATFORM_DIR"
echo "=============================="
echo ""

# ── 1. Virtual environment & dependencies ─────────────────────────────────────
if [[ ! -d ".venv" ]]; then
  echo "[1/4] Creating virtual environment..."
  python3 -m venv .venv
fi
# shellcheck source=/dev/null
source .venv/bin/activate
echo "[1/4] Installing dependencies..."
pip install -q -r requirements.txt
pip install -q pyinstaller

# ── 2. Tests ──────────────────────────────────────────────────────────────────
echo ""
echo "[2/4] Running tests..."
python3 -m unittest discover -s tests -v
echo ""
echo "All tests passed."

# ── 3. PyInstaller build ──────────────────────────────────────────────────────
echo ""
echo "[3/4] Building executable..."
rm -rf "$PLATFORM_DIR"
mkdir -p "$PLATFORM_DIR"

python3 -m PyInstaller \
  --onefile \
  --windowed \
  --name "PigmyBackup" \
  --distpath "$PLATFORM_DIR" \
  --workpath "build/_pyinstaller" \
  --specpath "build" \
  backup_gui.py

# ── 4. Stamp version ─────────────────────────────────────────────────────────
echo "$VERSION" > "releases/$VERSION/VERSION"

echo ""
echo "[4/4] Done."
echo ""
ls -lh "$PLATFORM_DIR/"

if [[ "$OS" == "Darwin" ]]; then
  echo ""
  echo "macOS note: Gatekeeper may block unsigned apps on first launch."
  echo "To allow, run once:  xattr -cr \"$PLATFORM_DIR/PigmyBackup\""
fi
