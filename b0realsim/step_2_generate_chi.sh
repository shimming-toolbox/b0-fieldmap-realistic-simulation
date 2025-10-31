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

# If run_2_compute_chimaps.sh exists, remove it and create a new one
if [ -f run_2_compute_chimaps.sh ]; then
    rm run_2_compute_chimaps.sh
    touch run_2_compute_chimaps.sh
fi

# For each subject, write to a file running the command (bash /Users/mathieuboudreau/neuropoly/projects/shimming-toolbox/b0-fieldmap-realistic-simulation/b0realsim/slicer_scripts/merge_pipeline.sh -s $bids_dir/$subject) for each subject, one subject per line
for subject in $SUBJECTS
do
    echo "python $DIR/label_to_chi.py -s $BIDS_DIR/$subject" >> run_2_compute_chimaps.sh
done

