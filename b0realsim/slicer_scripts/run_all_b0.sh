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

# For each subject, write to a file running the command (compute_fieldmap -i /Users/mathieuboudreau/neuropoly/projects/shimming-toolbox/data/data.neuro.polymtl.ca/whole-spine/derivatives/sub-amuAL/anat/sub-amuAL_T1w-chi.nii.gz -o /Users/mathieuboudreau/neuropoly/projects/shimming-toolbox/data/data.neuro.polymtl.ca/whole-spine/derivatives/sub-amuALT/fmap/sub-amuALT_T1w_fmap_b0-sim.nii.gz -p 50 -m constant) for each subject, one subject per line
for subject in $subjects
do
    echo "compute_fieldmap -i ${bids_dir}/derivatives/${subject}/anat/${subject}_T1w-chi.nii.gz -o ${bids_dir}/derivatives/${subject}/fmap/${subject}_T1w_fmap_b0-sim.nii.gz -b 50 -m edge" >> compute_fieldmaps.txt
done

