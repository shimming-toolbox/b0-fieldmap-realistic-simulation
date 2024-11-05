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
echo $subjects > subjects.txt

# Define the variables
SHORT_BIDS_DIR=whole-spine
SCRIPT_NAME="compute_fieldmap"
SCRIPT_SOURCE="https://github.com/shimming-toolbox/susceptibility-to-fieldmap-fft"
SCRIPT_COMMIT_HASH="d9f785b082fb145d547ff03ae53f23f1564ccc38"
PADDING=50
PADDING_OPTION="b0SimISMRM"

# For each subject, write to a file running the command (compute_fieldmap -i /Users/mathieuboudreau/neuropoly/projects/shimming-toolbox/data/data.neuro.polymtl.ca/whole-spine/derivatives/sub-amuAL/anat/sub-amuAL_T1w-chi.nii.gz -o /Users/mathieuboudreau/neuropoly/projects/shimming-toolbox/data/data.neuro.polymtl.ca/whole-spine/derivatives/sub-amuALT/fmap/sub-amuALT_T1w_fmap_b0-sim.nii.gz -p 50 -m constant) for each subject, one subject per line
for subject in $SUBJECTS
do
    INPUT_FILE="${BIDS_DIR}/derivatives/${subject}/anat/${subject}_T1w-chi.nii.gz"
    OUTPUT_FILE="${BIDS_DIR}/derivatives/${subject}/fmap/${subject}_T1w_fmap_b0-sim.nii.gz"
    OUTPUT_SIDECAR="${BIDS_DIR}/derivatives/${subject}/fmap/${subject}_T1w_fmap_b0-sim.json"
    COMMAND="compute_fieldmap -i $INPUT_FILE -o ${OUTPUT_FILE} -b $PADDING -m $PADDING_OPTION"

    echo "$COMMAND" >> run_3_compute_b0maps.sh

    # Define the JSON format string
    JSON_FMT='{\n\t\\\"author\\\":\\\"%s\\\",\n\t\\\"creation date\\\":\\"%s",\n\t\\\"script\\\":\\\"%s\\\",\n\t\\\"script source\\\":\\\"%s\\\",\n\t\\\"script commit hash\\\":\\\"%s\\\",\n\t\\\"input file\\\":\\\"%s\\\",\n\t\\\"padding\\\":%s,\n\t\\\"command\\\":\\\"%s\\\"\n}\n'

    # Create the JSON string with variables replaced by their values, except for the date
    JSON_STR=$(printf "$JSON_FMT" "$USER" "\$(date  +\"%Y-%m-%d %H:%M:%S\")\\" "$SCRIPT_NAME" "$SCRIPT_SOURCE" "$SCRIPT_COMMIT_HASH" "$INPUT_FILE" "$PADDING" "$COMMAND")

    # Write the command to the script file
    echo "echo \"$JSON_STR\" >| $OUTPUT_SIDECAR" >> run_3_compute_b0maps.sh
done

