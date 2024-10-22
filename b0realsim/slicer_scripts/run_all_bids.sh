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

# For each subject, write to a file running the command (bash /Users/mathieuboudreau/neuropoly/projects/shimming-toolbox/b0-fieldmap-realistic-simulation/b0realsim/slicer_scripts/merge_pipeline.sh -s $bids_dir/$subject) for each subject, one subject per line
for subject in $subjects
do
    echo "bash /Users/mathieuboudreau/neuropoly/projects/shimming-toolbox/b0-fieldmap-realistic-simulation/b0realsim/slicer_scripts/merge_pipeline.sh -s $bids_dir/$subject" >> run_all.sh
done

