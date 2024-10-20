#!/bin/bash

# Take the subject directory argument (-s), assign it, and print it to the screen
while getopts s: option
do
case "${option}"
in
s) SUBJECT=${OPTARG};;
esac
done

echo "Subject directory: $SUBJECT"

# Extract the subject ID from the subject directory. eg for "sub-amuAL_T1w.nii.gz", the subject ID is "sub-amuAL"
SUBJECT_ID=$(basename $SUBJECT | cut -d'_' -f1)

# Print the subject ID to the screen
echo "Subject ID: $SUBJECT_ID"

# Create a dictionnary of (called save_inputs) containing the file suffixes, eg for the key "body", return the value "_T1w_label-air_tissue.nii.gz"
declare -A save_inputs
save_inputs["body"]="-air_tissue.nii.gz"
save_inputs["brain"]="-brain_dseg.nii.gz"
save_inputs["earcanal"]="-air_tissue.nii.gz"
save_inputs["eyes"]="-brain_dseg.nii.gz"
save_inputs["sinus"]="-air_tissue.nii.gz"
save_inputs["skin"]="-brain_dseg.nii.gz"
save_inputs["skull"]="-brain_dseg.nii.gz"

# Create a dictionnary of (called save_outputs) containing the file suffixes, eg for the key "body", return the value "_T1w_label-body-raw.nii.gz"
declare -A save_outputs
save_outputs[body]="-body-raw.nii.gz"
save_outputs[brain]="-brain-raw.nii.gz"
save_outputs[earcanal]="-earcanal-raw.nii.gz"
save_outputs[eyes]="-eyes-raw.nii.gz"
save_outputs[sinus]="-sinus-raw.nii.gz"
save_outputs[skin]="-skin.nii.gz"
save_outputs[skull]="-skull-raw.nii.gz"

# Create a dictionary of (called smooth_outputs) containing the file suffixes, eg for the key "body", return the value "_T1w_label-body.nii.gz"
declare -A smooth_outputs
smooth_outputs[body]="-body.nii.gz"
smooth_outputs[brain]="-brain.nii.gz"
smooth_outputs[earcanal]="-earcanal.nii.gz"
smooth_outputs[eyes]="-eyes.nii.gz"
smooth_outputs[sinus]="-sinus.nii.gz"
smooth_outputs[skull]="-skull.nii.gz"

# Take the previous 7 commands and run them in in a loop, using the respective save_input and save_output labels set as variables and the keywords
for keyword in "body" "earcanal" "eyes" "sinus" "skin" "skull"
do
  /Applications/Slicer.app/Contents/MacOS/Slicer --python-script ../b0realsim/slicer_scripts/save_segment.py -m "$SUBJECT/anat/${SUBJECT_ID}_T1w.nii.gz" -s "derivatives/$SUBJECT/anat/${SUBJECT_ID}_T1w_label${save_inputs[$keyword]}" -o "derivatives/$SUBJECT/anat/${SUBJECT_ID}_T1w_label${save_outputs[$keyword]}" -a "$keyword"
done

# Take the previous 7 commands and run them in in a loop, using the respective save_output and smooth_output labels set as variables and the keywords
for keyword in "body" "earcanal" "eyes" "sinus" "skull"
do
  /Applications/Slicer.app/Contents/MacOS/Slicer --python-script ../b0realsim/slicer_scripts/smooth_segment.py -m "$SUBJECT/anat/${SUBJECT_ID}_T1w.nii.gz" -s "derivatives/$SUBJECT/anat/${SUBJECT_ID}_T1w_label${save_outputs[$keyword]}" -o "derivatives/$SUBJECT/anat/${SUBJECT_ID}_T1w_label${smooth_outputs[$keyword]}" -a "$keyword" || true
done

