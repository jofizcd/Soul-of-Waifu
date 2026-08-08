#!/usr/bin/env bash
DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
cd "$DIR" || exit 1

echo "============================================="
echo " Soul of Waifu v2.4.5 - Starting Application"
echo "============================================="
echo

printf "\n[1/4] Setting working directory...\n"
echo "   Current directory: $(pwd)"
echo "   Successfully switched to script location."
echo

######################
### Check for Pixi ###
######################

printf "[2/4] Activating Pixi environment...\n"
if command -v pixi >/dev/null 2>&1; then
    PIXI_EXE="pixi"
else
    PIXI_EXE="$DIR/.pixi-bin/pixi"
fi
if [ ! -x "$PIXI_EXE" ] && ! command -v "$PIXI_EXE" >/dev/null 2>&1; then
    echo "   ERROR: Pixi not found!"
    echo "   Please run installer.sh first to set up the environment."
    echo
    read -n 1 -s -r -p "   Press any key to exit..."
    echo
    exit 1
fi
echo "   Using Pixi: $PIXI_EXE"
echo "   Running: $PIXI_EXE shell (in $DIR)"
echo

########################
### Check for ffmpeg ###
########################

echo "[3/4] Checking: Is ffmpeg accessible..."
if ! $PIXI_EXE run ffmpeg -version >/dev/null 2>&1; then
    echo "   ERROR: ffmpeg not found!"
    echo "   Please make sure the \"app/ffmpeg/bin\" folder exists"
    echo "   and contains the executable files: ffmpeg, ffprobe and ffplay."
    echo
    echo "   ffmpeg is required for audio/video processing."
    echo "   Download it and place it in the specified folder."
    echo
    read -n 1 -s -r -p "   Press any key to exit..."
    echo
    exit 1
else
    echo "   SUCCESS: ffmpeg found and working correctly."
fi
echo


#####################
### Start main.py ###
######################

printf "[4/4] Starting main application: main.py...\n"
echo

"$PIXI_EXE" run python main.py

status=$?
if [ $status -ne 0 ]; then
    echo
    echo "==================================================="
    echo " CRITICAL ERROR: Application exited with code $status"
    echo "==================================================="
    echo
    echo "   An error occurred while running main.py."
    echo "   Possible causes:"
    echo "     - Missing or corrupted Python dependencies."
    echo "     - Damaged main.py or other modules."
    echo "     - Permission issues or antivirus interference."
    echo
    echo "   Please check the \"logs/\" folder for detailed error logs."
    echo "   Consider restarting the script or reinstalling the app."
    echo
    read -n 1 -s -r -p "   Press any key to exit..."
    echo
    exit $status
else
    echo
    echo "==================================="
    echo " Application terminated gracefully"
    echo "==================================="
fi

echo
echo "================================"
echo " Soul of Waifu - Execution Done"
echo "================================"
echo
echo "   The application was launched and closed successfully."
echo "   Thank you for using Soul of Waifu!"
echo
read -n 1 -s -r -p "Press any key to close this window..."
echo
