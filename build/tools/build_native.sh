#!/usr/bin/env bash
# build/tools/build_native.sh <product> <variant>
# Called by `make tunefetch` (via envsetup's lunch) - not meant to be
# run directly. Does the actual compile: sets up an isolated build
# sandbox, syncs dependencies, and packages the artifact with PyInstaller.
set -e
ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
cd "$ROOT"

PRODUCT="$1"
VARIANT="${2:-userdebug}"

case "$(uname -s)" in
    Darwin*) HOST_OS="macos" ;;
    Linux*)  HOST_OS="linux" ;;
    *)       HOST_OS="linux" ;;
esac

PY=python3
command -v python3 >/dev/null 2>&1 || PY=python

echo "============================================"
echo "PLATFORM_VERSION_CODENAME=REL"
echo "PLATFORM_VERSION=1.1"
echo "TARGET_PRODUCT=tunefetch_${PRODUCT}"
echo "TARGET_BUILD_VARIANT=${VARIANT}"
echo "HOST_OS=${HOST_OS}"
echo "OUT_DIR=out/target/product/${PRODUCT}"
echo "============================================"
echo

if [ "$PRODUCT" != "$HOST_OS" ]; then
    echo "PyInstaller can't cross-compile: this host ($HOST_OS) can't produce"
    echo "a $PRODUCT artifact. Your options:"
    echo "  - Run this on an actual $PRODUCT machine (or VM): source build/envsetup.sh,"
    echo "    lunch tunefetch-${PRODUCT}-${VARIANT}, make tunefetch."
    echo "  - lunch tunefetch-allproducts-eng here instead, to set up the GitHub"
    echo "    Actions build, which produces Linux + Windows + macOS artifacts"
    echo "    in the cloud on every push - no other machine needed."
    exit 1
fi

BOARD_CONFIG="device/tunefetch/$PRODUCT/BoardConfig.mk"
if [ ! -f "$BOARD_CONFIG" ]; then
    echo "Missing $BOARD_CONFIG - is your device tree intact?"
    exit 1
fi
PYI_BIN_NAME="$(sed -n 's/^PYI_BIN_NAME *:= *//p' "$BOARD_CONFIG")"
PYI_BIN_NAME="${PYI_BIN_NAME:-TuneFetch}"
PYI_WINDOWED_ARGS="$(sed -n 's/^PYI_WINDOWED_ARGS *:= *//p' "$BOARD_CONFIG")"
PYI_ICON_FILE="$(sed -n 's/^PYI_ICON_FILE *:= *//p' "$BOARD_CONFIG")"

WINDOWED_ARGS=()
[ -n "$PYI_WINDOWED_ARGS" ] && WINDOWED_ARGS=($PYI_WINDOWED_ARGS)
ICON_ARGS=()
[ -n "$PYI_ICON_FILE" ] && [ -f "$PYI_ICON_FILE" ] && ICON_ARGS=(--icon="$PYI_ICON_FILE")

echo "[ 05% ] Verifying host toolchain (tkinter)..."
if ! $PY -c "import tkinter" >/dev/null 2>&1; then
    echo "Tkinter isn't installed for $PY - the toolchain needs it to build the GUI."
    if [ "$HOST_OS" = "macos" ]; then
        echo "Fix: brew install python-tk"
    else
        echo "Fix (Debian/Ubuntu): sudo apt install python3-tk"
        echo "Fix (Fedora):        sudo dnf install python3-tkinter"
        echo "Fix (Arch):          sudo pacman -S tk"
    fi
    exit 1
fi

echo "[ 15% ] Setting up the build sandbox (venv)..."
VENV_DIR="$ROOT/.tunefetch-build-venv"
if [ ! -d "$VENV_DIR" ]; then
    if ! $PY -m venv "$VENV_DIR" 2>/tmp/tunefetch_venv_err; then
        cat /tmp/tunefetch_venv_err
        echo
        echo "Could not create the build sandbox."
        if [ "$HOST_OS" = "linux" ]; then
            echo "Fix (Debian/Ubuntu): sudo apt install python3-venv"
        fi
        exit 1
    fi
fi
PY="$VENV_DIR/bin/python"   # every step below runs inside the sandbox, never the system Python

echo "[ 30% ] Syncing build dependencies (pip)..."
"$PY" -m pip install --upgrade pip >/dev/null
"$PY" -m pip install --upgrade pyinstaller customtkinter yt-dlp pillow mutagen imageio-ffmpeg certifi truststore

echo "[ 60% ] Compiling $PYI_BIN_NAME ..."
OUT="out/target/product/$PRODUCT"
"$PY" -m PyInstaller --noconfirm --onefile --name "$PYI_BIN_NAME" \
    "${WINDOWED_ARGS[@]}" "${ICON_ARGS[@]}" \
    --collect-data customtkinter \
    --collect-data imageio_ffmpeg \
    --hidden-import=yt_dlp \
    --distpath "$OUT" \
    --workpath "$OUT/obj" \
    --specpath "$OUT" \
    vendor/tunefetch/tunefetch.py

echo "[100% ] Installing artifact..."
echo
if [ "$HOST_OS" = "macos" ] && [ -d "$OUT/$PYI_BIN_NAME.app" ]; then
    echo "#### make completed successfully ####"
    echo "Artifact: $OUT/$PYI_BIN_NAME.app"
    echo "(Unsigned apps may need: right-click -> Open, the first time,"
    echo " to get past Gatekeeper.)"
elif [ -f "$OUT/$PYI_BIN_NAME" ]; then
    chmod +x "$OUT/$PYI_BIN_NAME"
    echo "#### make completed successfully ####"
    echo "Artifact: $OUT/$PYI_BIN_NAME"
else
    echo "#### make failed ####"
    echo "Scroll up for the PyInstaller error."
    exit 1
fi
