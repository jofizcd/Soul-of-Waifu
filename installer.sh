#!/usr/bin/env bash

DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)

cd "$DIR" || exit 1

printf "\nWelcome to the Soul of Waifu installer!\n"

######################
### Check for Pixi ###
######################

printf "\n[1/4] Checking for Pixi..."

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

############################
### Install Dependencies ###
############################

printf "\n[2/4] Installing dependencies..."

if ! "$PIXI_EXE" install; then
    echo "INSTALLATION ERROR: Failed to install dependencies."
    exit 1
fi

##########################################
### Install extras not managed by Pixi ###
##########################################

printf "\n[3/4] Installing extras...\n"

echo "=============================================================="
echo "Please select PyTorch installation:"
echo "[1] CUDA (cu128) - Recommended for GPU"
echo "[2] CPU only"
echo "=============================================================="
read -p "Enter your choice (1 or 2): " choice

case $choice in
    1)
        echo "Installing PyTorch with CUDA support..."
        $PIXI_EXE run pip uninstall -y torch torchvision torchaudio >/dev/null 2>&1
        $PIXI_EXE run pip install --no-cache-dir --upgrade --force-reinstall torch==2.10.0 torchvision==0.25.0 torchaudio==2.10.0 --index-url https://download.pytorch.org/whl/cu128
        ;;
    2)
        echo "PyTorch CPU already installed via Pixi, continuing..."
        ;;
    *)
        printf "Invalid choice. Exiting.\n"
        exit 1
        ;;
esac


###################################
### Final checks and completion ###
###################################

printf "\n[4/4] Final checks..."
$PIXI_EXE run python -m pip check
$PIXI_EXE run python -c "import torch, numpy, transformers, PyQt6; print('Core imports OK')"
$PIXI_EXE run python -c "from TTS.api import TTS; print('Coqui TTS import OK')" || echo WARNING: Coqui TTS import failed - possible version conflict!

# if user chose CUDA, check if torch can access GPU
if [ "$choice" == "1" ]; then
    $PIXI_EXE run python -c "import torch; print('CUDA available:', torch.cuda.is_available())"
fi

echo "=============================================================="
echo Installation completed successfully!
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
