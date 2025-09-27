#!/bin/bash

# Find all the subjects in the bids directory and create a list of them
# This is useful for the batch processing of subjects

# Parse the command line arguments -b --bids_dir
while getopts ":b:" opt; do
  case ${opt} in
    b )
      BIDS_DIR=$OPTARG
      ;;
    \? )
      echo "Usage: cmd [-b] bids_dir"
      exit 1
      ;;
  esac
done

# Handle Windows-style paths like E:/... or C:/...
if [[ "$BIDS_DIR" =~ ^[A-Z]:/ ]]; then
    drive=$(echo $BIDS_DIR | cut -c1 | tr 'A-Z' 'a-z')
    path=$(echo $BIDS_DIR | cut -c3-)
    BIDS_DIR="/cygdrive/$drive/$path"
fi

# Print the bids directory to the screen
echo "BIDS directory: $BIDS_DIR"

# Check if BIDS_DIR exists
if [ ! -d "$BIDS_DIR" ]; then
    echo "[ERROR] BIDS directory not found: $BIDS_DIR"
    exit 1
fi

# If subjects.txt exists, remove it and create a new one
if [ -f subjects.txt ]; then
    rm subjects.txt
    touch subjects.txt
fi

# Find all the subjects in the bids directory
SUBJECTS=$(ls $BIDS_DIR | grep sub-)

# Remove sub-unfErssm001 and sub-unfErssm021 from the list of subjects
SUBJECTS=$(echo $SUBJECTS | sed 's/sub-unfErssm001//g' | sed 's/sub-unfErssm021//g')

echo "Subjects found:"
echo $SUBJECTS

# Create a list of the subjects
echo $SUBJECTS > subjects.txt

# Get script directory
DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" >/dev/null 2>&1 && pwd )"

# Convert DIR to Windows path for Windows Python
WIN_DIR=$(echo "$DIR" | sed 's|/cygdrive/\([a-z]\)/|\U\1:/|')

for subject in $SUBJECTS
do
    # Skip empty entries from excluded subjects
    if [ -z "$subject" ]; then
        continue
    fi

    echo "[INFO] Processing $subject"

    # Convert BIDS_DIR to Windows path
    WIN_BIDS_DIR=$(echo "$BIDS_DIR" | sed 's|/cygdrive/\([a-z]\)/|\U\1:/|')

    # Check if subject folder exists
    if [ ! -d "$WIN_BIDS_DIR/$subject" ]; then
        echo "[WARNING] Subject folder not found: $WIN_BIDS_DIR/$subject, skipping..."
        continue
    fi

    # Check if Python script exists
    if [ ! -f "$WIN_DIR/label_to_perm_cond.py" ]; then
        echo "[ERROR] Python script not found: $WIN_DIR/label_to_perm_cond.py"
        exit 1
    fi

    # Run Python to generate perm/cond maps
    "C:/Users/Admin/Miniconda3/python.exe" "$WIN_DIR/label_to_perm_cond.py" -s "$WIN_BIDS_DIR/$subject"
done

echo "[INFO] All subjects processed."


