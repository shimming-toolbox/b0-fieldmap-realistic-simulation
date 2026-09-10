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

# Print the bids directory to the screen
echo "BIDS directory: $BIDS_DIR"

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

# Get the path for the directory of this script
DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" >/dev/null 2>&1 && pwd )"

# Echo the directory to the screen
echo "Directory: $DIR"

# If run_1b_bodyext.sh exists, remove it and create a new one
if [ -f run_1b_bodyext.sh ]; then
    rm run_1b_bodyext.sh
    touch run_1b_bodyext.sh
fi


# Stage 1b: build a mannequin body around each subject's acquired labels, so the
# simulated object is finite and enclosed in air rather than a truncated torso
# that the DFT fuses into an infinite lattice.
#
# Emits LABELS ONLY - stage 2 maps them to chi through CHI_LUT.
for subject in $SUBJECTS
do
    OUT_DIR="${BIDS_DIR}/derivatives/fullbody/${subject}/anat"
    echo "mkdir -p ${OUT_DIR}" >> run_1b_bodyext.sh
    echo "python $DIR/build_fullbody.py --labels ${BIDS_DIR}/derivatives/labels/${subject}/anat/${subject}_T1w_label-all.nii.gz --out-prefix ${OUT_DIR}/${subject}_T1w_fullbody --qc" >> run_1b_bodyext.sh
done

