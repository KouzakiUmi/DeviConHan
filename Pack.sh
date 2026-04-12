#!/usr/bin/env bash
# Set script to exit on error
set -e

# Change to script directory
cd "$(dirname "$0")"

ROOT="$(pwd)"
PY_SCRIPT="main.py"
OUT_TOOL="Tyrano_Toolbox"
OUT_PATCH="DevilConnection_Patch"

echo "=========================================="
echo "   Tyrano Builder (Mac/Linux)"
echo "=========================================="

if [ ! -f "$ROOT/$PY_SCRIPT" ]; then
    echo "[Error] Script missing: main.py"
    exit 1
fi

if ! command -v python3 >/dev/null 2>&1; then
    if ! command -v python >/dev/null 2>&1; then
        echo "[Error] Python not found"
        exit 1
    else
        PYTHON_CMD="python"
    fi
else
    PYTHON_CMD="python3"
fi

$PYTHON_CMD --version

if ! $PYTHON_CMD -m PyInstaller --version >/dev/null 2>&1; then
    echo "[Error] PyInstaller not found. Please install it using 'pip install pyinstaller asar'"
    exit 1
fi

echo
echo "[1/2] Building Toolbox..."
echo "------------------------------------------"

rm -rf "dist"

$PYTHON_CMD -m PyInstaller -F -w --clean \
    -i "$ROOT/icon.ico" \
    --distpath "dist" \
    --workpath "build_toolbox" \
    --add-data "$ROOT/icon.ico:." \
    --add-data "$ROOT/config.ini:." \
    --name "$OUT_TOOL" \
    "$ROOT/$PY_SCRIPT"

rm -rf "build_toolbox"

echo
echo "[2/2] Checking for Patch Data..."

BUILD_PATCHER=0
HAS_PATCH_DATA=0

if [ -f "$ROOT/Patch.zip" ]; then
    echo "- Patch.zip found."
    BUILD_PATCHER=1
    HAS_PATCH_DATA=1
fi

if [ -d "$ROOT/Patch" ]; then
    if [ "$(ls -A "$ROOT/Patch")" ]; then
        echo "- Patch folder found. Compressing to Patch.zip to boost startup performance..."
        rm -f "$ROOT/Patch.zip"
        $PYTHON_CMD -c "import shutil; shutil.make_archive('Patch', 'zip', 'Patch')"
        
        if [ -f "$ROOT/Patch.zip" ]; then
            echo "- Cleaning up original Patch directory..."
            rm -rf "$ROOT/Patch"
            BUILD_PATCHER=1
            HAS_PATCH_DATA=1
        else
            echo "[Error] Failed to compress Patch directory."
        fi
    else
        echo "- Warning: Patch folder is empty."
    fi
fi

if [ "$BUILD_PATCHER" -eq 1 ]; then
    echo "- Building Patcher..."
    echo "------------------------------------------"

    $PYTHON_CMD -m PyInstaller -F -w --clean \
        -i "$ROOT/icon.ico" \
        --distpath "dist" \
        --workpath "build_patcher" \
        --add-data "$ROOT/icon.ico:." \
        --add-data "$ROOT/config.ini:." \
        --add-data "$ROOT/Patch.zip:." \
        --name "$OUT_PATCH" \
        "$ROOT/$PY_SCRIPT"
    
    echo "- Patcher build success."
    rm -rf "build_patcher"
else
    echo "- No Patch data found. Skipped."
fi

echo
echo "[Cleanup] Cleaning up..."
rm -rf "build_toolbox" "build_patcher" "__pycache__"
rm -f *.spec

echo
echo "=========================================="
echo "   Build Complete!"
echo "=========================================="
echo
echo "Generated files:"
[ -f "dist/$OUT_TOOL" ] && echo "  - Toolbox: dist/$OUT_TOOL" || ([ -f "dist/$OUT_TOOL.app" ] && echo "  - Toolbox: dist/$OUT_TOOL.app")
[ -f "dist/$OUT_PATCH" ] && echo "  - Patcher: dist/$OUT_PATCH" || ([ -f "dist/$OUT_PATCH.app" ] && echo "  - Patcher: dist/$OUT_PATCH.app")
echo
