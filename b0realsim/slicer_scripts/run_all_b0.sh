#!/bin/bash

# Find all the subjects in the bids directory and create a list of them
# This is useful for the batch processing of subjects

# Set the bids directory to the directory
bids_dir=/Users/mathieuboudreau/neuropoly/projects/shimming-toolbox/data/data.neuro.polymtl.ca/whole-spine

# Print the bids directory to the screen
echo "BIDS directory: $bids_dir"

# Find all the subjects in the bids directory
subjects=$(ls $bids_dir | grep sub-)

echo "Subjects found:"
echo $subjects

# Create a list of the subjects
echo $subjects > subjects.txt

# Define the variables
SHORT_BIDS_DIR=whole-spine
SCRIPT_NAME="compute_fieldmap"
SCRIPT_SOURCE="https://github.com/shimming-toolbox/susceptibility-to-fieldmap-fft"
SCRIPT_COMMIT_HASH="665a8d4ce2b4bfa5336199e650423104fe64baa5"
PADDING=50
PADDING_OPTION="b0SimISMRM"

# For each subject, write to a file running the command (compute_fieldmap -i /Users/mathieuboudreau/neuropoly/projects/shimming-toolbox/data/data.neuro.polymtl.ca/whole-spine/derivatives/sub-amuAL/anat/sub-amuAL_T1w-chi.nii.gz -o /Users/mathieuboudreau/neuropoly/projects/shimming-toolbox/data/data.neuro.polymtl.ca/whole-spine/derivatives/sub-amuALT/fmap/sub-amuALT_T1w_fmap_b0-sim.nii.gz -p 50 -m constant) for each subject, one subject per line
for subject in $subjects
do
    INPUT_FILE="${bids_dir}/derivatives/${subject}/anat/${subject}_T1w-chi.nii.gz"
    OUTPUT_FILE="${bids_dir}/derivatives/${subject}/fmap/${subject}_T1w_fmap_b0-sim.nii.gz"
    OUTPUT_SIDECAR="${bids_dir}/derivatives/${subject}/fmap/${subject}_T1w_fmap_b0-sim.json"
    COMMAND="compute_fieldmap -i $INPUT_FILE -o ${OUTPUT_FILE} -b $PADDING -m $PADDING_OPTION"

    echo "$COMMAND" >> compute_fieldmaps.sh

    # Define the JSON format string
    JSON_FMT='{\n\t\\\"author\\\":\\\"%s\\\",\n\t\\\"creation date\\\":\\"%s",\n\t\\\"script\\\":\\\"%s\\\",\n\t\\\"script source\\\":\\\"%s\\\",\n\t\\\"script commit hash\\\":\\\"%s\\\",\n\t\\\"input file\\\":\\\"%s\\\",\n\t\\\"padding\\\":%s,\n\t\\\"command\\\":\\\"%s\\\"\n}\n'

    # Create the JSON string with variables replaced by their values, except for the date
    JSON_STR=$(printf "$JSON_FMT" "$USER" "\$(date  +\"%Y-%m-%d %H:%M:%S\")\\" "$SCRIPT_NAME" "$SCRIPT_SOURCE" "$SCRIPT_COMMIT_HASH" "$INPUT_FILE" "$PADDING" "$COMMAND")

    # Write the command to the script file
    echo "echo \"$JSON_STR\" > $OUTPUT_SIDECAR" >> compute_fieldmaps.sh
done

