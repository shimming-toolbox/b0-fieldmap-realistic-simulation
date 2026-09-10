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

# If run_3_compute_b0maps.sh exists, remove it and create a new one.
# Without this the generator APPENDS to the previous run: re-generating would
# simulate every subject twice, and after a parameter change it would run both
# the old and the new settings with the last write winning.
if [ -f run_3_compute_b0maps.sh ]; then
    rm run_3_compute_b0maps.sh
    touch run_3_compute_b0maps.sh
fi

# Get the path for the directory of this script (crop_to_fov.py lives beside it)
DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" >/dev/null 2>&1 && pwd )"

# Define the variables
SHORT_BIDS_DIR=whole-spine
SCRIPT_NAME="compute_fieldmap"
SCRIPT_SOURCE="https://github.com/shimming-toolbox/susceptibility-to-fieldmap-fft"

# Resolve the commit hash of the susceptibility-to-fieldmap-fft checkout that actually provides
# compute_fieldmap. This used to be a hardcoded constant, which silently stamped a stale hash into
# every sidecar regardless of which version was installed.
PYTHON_BIN=$(command -v python3 || command -v python)
SCRIPT_REPO_DIR=$("$PYTHON_BIN" -c "import functions, pathlib; print(pathlib.Path(functions.__file__).resolve().parent.parent)" 2>/dev/null)

if [ -z "$SCRIPT_REPO_DIR" ] || ! git -C "$SCRIPT_REPO_DIR" rev-parse --git-dir >/dev/null 2>&1; then
    echo "ERROR: could not locate the susceptibility-to-fieldmap-fft git checkout providing compute_fieldmap." >&2
    echo "       Install it from a git clone in editable mode (pip install -e .) so provenance can be recorded." >&2
    exit 1
fi

SCRIPT_COMMIT_HASH=$(git -C "$SCRIPT_REPO_DIR" rev-parse HEAD)

# Flag uncommitted changes so a sidecar never claims a clean commit that was not
# what ran. Untracked files are deliberately EXCLUDED: they do not change what
# the code does, and they produce false positives - e.g. macOS AppleDouble "._*"
# files travel inside a tarball and would otherwise mark a clean checkout dirty.
# This must stay consistent with label_to_chi.py, which uses
# repo.is_dirty(untracked_files=False).
if ! git -C "$SCRIPT_REPO_DIR" diff --quiet HEAD 2>/dev/null; then
    SCRIPT_COMMIT_HASH="${SCRIPT_COMMIT_HASH}-dirty"
fi

echo "compute_fieldmap provenance: $SCRIPT_REPO_DIR @ $SCRIPT_COMMIT_HASH"

# r1 revision: the object is now finite and enclosed in air (stage 1b), so pad
# with AIR to R=2 on every face instead of replicating tissue off the edges.
# The old setting was PADDING=50 / PADDING_OPTION="b0SimISMRM", which extended
# tissue below and air above, making the DFT see an infinite lattice of bodies.
# Overridable from the environment so the run driver can set them without
# editing this file: e.g. WORKERS=4 ./step_3_generate_b0.sh -b $BIDS_DIR
ZEROFILL="${ZEROFILL:-2}"
PAD_VALUE="${PAD_VALUE:-0.35}"
DTYPE="${DTYPE:-float32}"
# FFT threads per subject. -1 grabs every core, which is right for one job at a
# time and wrong when the driver runs several concurrently; the driver overrides
# this via the generated script or by editing here.
WORKERS="${WORKERS:--1}"
# Canvas fieldmaps are ~1.2 GB each: 72 GB across 60 subjects, against 6.6 GB
# cropped. Discarded by default; set KEEP_CANVAS=1 for the QC subset.
if [ "${KEEP_CANVAS:-0}" = "1" ]; then KEEP_CANVAS_FLAG=""; else KEEP_CANVAS_FLAG=" --discard-canvas"; fi

# For each subject, write to a file running the command (compute_fieldmap -i /Users/mathieuboudreau/neuropoly/projects/shimming-toolbox/data/data.neuro.polymtl.ca/whole-spine/derivatives/sub-amuAL/anat/sub-amuAL_T1w-chi.nii.gz -o /Users/mathieuboudreau/neuropoly/projects/shimming-toolbox/data/data.neuro.polymtl.ca/whole-spine/derivatives/sub-amuALT/fmap/sub-amuALT_T1w_fmap_b0-sim.nii.gz -p 50 -m constant) for each subject, one subject per line
for subject in $SUBJECTS
do
    INPUT_FILE="${BIDS_DIR}/derivatives/${subject}/anat/${subject}_T1w-chi.nii.gz"
    OUTPUT_FILE="${BIDS_DIR}/derivatives/${subject}/fmap/${subject}_T1w_fmap_b0-sim.nii.gz"
    OUTPUT_SIDECAR="${BIDS_DIR}/derivatives/${subject}/fmap/${subject}_T1w_fmap_b0-sim.json"
    # compute_fieldmap returns the shape it was given, which after stage 1b is the
    # whole canvas (~13x the acquired FOV, ~1.2 GB). Simulate on the canvas, then
    # crop back to the acquired grid that everything downstream expects.
    CANVAS_FILE="${BIDS_DIR}/derivatives/${subject}/fmap/${subject}_T1w_fmap_b0-sim_canvas.nii.gz"
    FULLBODY_META="${BIDS_DIR}/derivatives/fullbody/${subject}/anat/${subject}_T1w_fullbody_label-all.json"
    COMMAND="compute_fieldmap -i $INPUT_FILE -o ${CANVAS_FILE} -r $ZEROFILL --pad-value $PAD_VALUE --dtype $DTYPE --workers $WORKERS"
    CROP_COMMAND="python $DIR/crop_to_fov.py --fieldmap ${CANVAS_FILE} --meta ${FULLBODY_META} --out ${OUTPUT_FILE}${KEEP_CANVAS_FLAG}"

    echo "$COMMAND" >> run_3_compute_b0maps.sh
    echo "$CROP_COMMAND" >> run_3_compute_b0maps.sh

    # Define the JSON format string
    JSON_FMT='{\n\t\\\"author\\\":\\\"%s\\\",\n\t\\\"creation date\\\":\\\"%s\\\",\n\t\\\"script\\\":\\\"%s\\\",\n\t\\\"script source\\\":\\\"%s\\\",\n\t\\\"script commit hash\\\":\\\"%s\\\",\n\t\\\"input file\\\":\\\"%s\\\",\n\t\\\"zerofill\\\":%s,\n\t\\\"pad value ppm\\\":%s,\n\t\\\"dtype\\\":\\\"%s\\\",\n\t\\\"cropped to acquired FOV\\\":true,\n\t\\\"command\\\":\\\"%s\\\"\n}\n'

    # Create the JSON string with variables replaced by their values, except for the date
    JSON_STR=$(printf "$JSON_FMT" "$USER" "$(date  +"%Y-%m-%d %H:%M:%S")" "$SCRIPT_NAME" "$SCRIPT_SOURCE" "$SCRIPT_COMMIT_HASH" "$INPUT_FILE" "$ZEROFILL" "$PAD_VALUE" "$DTYPE" "$COMMAND")

    # Write the command to the script file
    echo "echo \"$JSON_STR\" >| $OUTPUT_SIDECAR" >> run_3_compute_b0maps.sh
done

