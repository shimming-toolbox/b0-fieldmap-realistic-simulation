#!/bin/bash

# Find all the subjects in the bids directory and create a list of them
# This is useful for the batch processing of subjects

# Parse the command line arguments -b --bids_dir & shimming toolbox options
SHIM_ARGS=""
while [[ $# -gt 0 ]]; do
  case $1 in
    -b|--bids-dir)
      BIDS_DIR="$2"
      shift 2
      ;;
    -h|--help)
      echo "Usage: $0 -b <bids_dir> [shimming_toolbox_options...]"
      echo "Example: $0 -b /path/to/bids --scanner-coil-order 0,1,2 --slices volume"
      exit 0
      ;;
    *)
      # Collect all other arguments as shimming options
      SHIM_ARGS="$SHIM_ARGS $1"
      shift
      ;;
  esac
done

# Still keep the validation for missing required argument
if [ -z "$BIDS_DIR" ]; then
    echo "Error: BIDS directory is required"
    echo "Usage: $0 -b <bids_dir> [shimming_toolbox_options...]"
    exit 1
fi

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

# If run_2_compute_chimaps.sh exists, remove it and create a new one
if [ -f run_4_shim.sh ]; then
    rm run_4_shim.sh
    touch run_4_shim.sh
fi

# For each subject, write to a file running the command (bash /Users/mathieuboudreau/neuropoly/projects/shimming-toolbox/b0-fieldmap-realistic-simulation/b0realsim/slicer_scripts/merge_pipeline.sh -s $bids_dir/$subject) for each subject, one subject per line
for subject in $SUBJECTS
do
    echo "st_b0shim dynamic --fmap ${BIDS_DIR}/derivatives/b0shim_brain/$subject/${subject}_T1w_fmap_b0-sim_head.nii.gz --anat ${BIDS_DIR}/derivatives/b0shim_brain/$subject/${subject}_T1w_head.nii.gz --mask ${BIDS_DIR}/derivatives/b0shim_brain/$subject/${subject}_mask_brain.nii.gz -o ${BIDS_DIR}/derivatives/b0shim_brain/$subject/output-2ndorder/ $SHIM_ARGS" >> run_4_shim.sh
done

