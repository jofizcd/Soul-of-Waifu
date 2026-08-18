#!/usr/bin/env bash

DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)

cd "$DIR" || exit 1

echo "=============================================================="
echo "Welcome to the Soul of Waifu installer!"
echo "=============================================================="
echo ""

######################
### Check for Pixi ###
######################

echo "[1/3] Checking for Pixi..."
echo ""

if command -v pixi >/dev/null 2>&1; then
    printf "Found Pixi in PATH.\n"
    PIXI_EXE="pixi"
else
    printf "Pixi not found in PATH. Checking local directory.\n"
    PIXI_EXE="$DIR/.pixi-bin/pixi"
    if [ ! -f "$PIXI_EXE" ]; then
        printf "Pixi not found in local directory. Downloading...\n"
        mkdir -p "$DIR/.pixi-bin"
        PIXI_ARCH=$(uname -m)
        PIXI_URL="https://github.com/prefix-dev/pixi/releases/latest/download/pixi-${PIXI_ARCH}-unknown-linux-musl"
        curl -L "$PIXI_URL" -o "$PIXI_EXE"
        chmod +x "$PIXI_EXE"
    fi
fi

echo "Pixi is ready to use"
echo ""

############################
### Install Dependencies ###
############################

echo "[2/3] Installing dependencies..."
echo "=============================================================="
echo "Please select PyTorch installation:"
echo "[1] CUDA (cu128) - Recommended for GPU"
echo "[2] CPU only"
echo "=============================================================="
read -p "Enter your choice (1 or 2): " choice

case $choice in
    1)
        echo "Installing dependencies, PyTorch with CUDA support..."
        $PIXI_EXE install -e gpu
        ;;
    2)
        echo "Installing dependencies, CPU-only PyTorch..."
        $PIXI_EXE install -e cpu
        ;;
    *)
        printf "Invalid choice. Exiting.\n"
        exit 1
        ;;
esac

if [ $? -ne 0 ]; then
    echo "INSTALLATION ERROR: Pixi failed to resolve/install dependencies."
    exit 1
fi

###################################
### Final checks and completion ###
###################################

echo ""
echo "[3/3] Final checks..."
"$PIXI_EXE" run sh -c '
    python -m pip check
    python -c "import torch, numpy, transformers, PyQt6; print(\"Core imports OK\")"
    python -c "from TTS.api import TTS; print(\"Coqui TTS import OK\")" || echo "WARNING: Coqui TTS import failed - possible version conflict!"
'

# if user chose CUDA, check if torch can access GPU
if [ "$choice" == "1" ]; then
    $PIXI_EXE run python -c "import torch; print('CUDA available:', torch.cuda.is_available())"
fi

echo "=============================================================="
echo "Installation completed successfully!"
echo NOTE: If there are warnings from pip check,
echo       RVC and Coqui may have minor conflicts.
echo "=============================================================="
echo "[1] Start the program"
echo "[2] Exit"
read -p "Enter your choice: " post_install_choice

case $post_install_choice in
    1)
        echo "Starting the program..."
        "$DIR"/start.sh
        ;;
    2)
        echo "Exiting."
        exit 0
        ;;
    *)
        echo "Invalid choice. Exiting."
        exit 1
        ;;
esac
