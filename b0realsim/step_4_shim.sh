#!/bin/bash
#
# Stage 4: dynamic shimming with Shimming Toolbox.
#
# RUN THE PREP SCRIPTS FIRST, IN THIS ORDER:
#     python b0realsim/shim/prep_for_shimming_head.py  -b $BIDS_DIR
#     python b0realsim/shim/prep_for_shimming_brain.py -b $BIDS_DIR
#
# The order matters and is not cosmetic. Both scripts write
# <sub>_T1w_fmap_b0-sim_head.nii.gz and <sub>_T1w_head.nii.gz, but they demean
# the fieldmap differently - head over soft tissue excluding airways and bone,
# brain over label 56 only - so whichever runs LAST decides the DC offset of the
# map that run_4_shim.sh actually shims.
#
# Why head-then-brain: the head script crops the acquired volume down to the
# shimming FOV (the superior 301 slices); the brain script then re-demeans that
# over the brain and writes <sub>_mask_brain.nii.gz, which is the mask
# run_4_shim.sh passes to st_b0shim. Shimming a brain mask against a
# brain-demeaned map is the coherent pairing, and it is what the corresponding
# author recalls doing for r0.
#
# NOTE for anyone tempted to verify this from the published shim coefficients:
# you cannot. The 0th-order coefficient in coefs_coil0_Prisma_fit.txt is NOT the
# negative of the masked mean - the shim basis is not orthogonal over a real
# brain mask, so a field demeaned to exactly zero still fits a large constant
# term (measured: -393 Hz on a synthetic case whose masked mean was 0.000).

# The offset is absorbed by the 0th-order shim term, so post-shim SD is
# unaffected either way - but the reported f0 coefficient is not.

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
SUBJECTS=$(ls "$BIDS_DIR/derivatives/b0shim" | grep sub-)

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

# If run_2_compute_chimaps.sh exists, remove it and create a new one
if [ -f run_4_shim.sh ]; then
    rm run_4_shim.sh
    touch run_4_shim.sh
fi

# For each subject, write to a file running the command (bash /Users/mathieuboudreau/neuropoly/projects/shimming-toolbox/b0-fieldmap-realistic-simulation/b0realsim/slicer_scripts/merge_pipeline.sh -s $bids_dir/$subject) for each subject, one subject per line
for subject in $SUBJECTS
do
    echo "st_b0shim dynamic --fmap ${BIDS_DIR}/derivatives/b0shim/$subject/${subject}_T1w_fmap_b0-sim_head.nii.gz --anat ${BIDS_DIR}/derivatives/b0shim/$subject/${subject}_T1w_head.nii.gz --mask ${BIDS_DIR}/derivatives/b0shim/$subject/${subject}_mask_brain.nii.gz --scanner-coil-order "0,1,2" -o ${BIDS_DIR}/derivatives/b0shim/$subject/output-paper-step1/ --slices volume" >> run_4_shim.sh
    echo "st_b0shim dynamic --fmap ${BIDS_DIR}/derivatives/b0shim/$subject/output-paper-step1/fieldmap_calculated_shim.nii.gz --anat ${BIDS_DIR}/derivatives/b0shim/$subject/${subject}_T1w_head.nii.gz --mask ${BIDS_DIR}/derivatives/b0shim/$subject/${subject}_mask_brain.nii.gz --scanner-coil-order "0,1" -o ${BIDS_DIR}/derivatives/b0shim/$subject/output-paper-step2/ --slices descending --slice-factor 1" >> run_4_shim.sh
done

