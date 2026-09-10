import nibabel as nib
import numpy as np
import argparse
from pathlib import Path
import os
import json
import datetime
import git


# Label value for material added by the body-extension stage (step 1b). Chosen
# to sit clear of every published label so the two never collide.
ADDED_LABEL = 200

# Susceptibility in ppm, keyed by label value.
#
# SINGLE SOURCE OF TRUTH. Both the chi mapping and the BIDS sidecar are built
# from this dict, so a value cannot be changed in one place and missed in the
# other. Revisiting the lung/trachea/sinus values is reviewer point R2.3; this
# is the only place that edit needs to happen.
CHI_LUT = {
    0: 0.35,      # background (air)
    1: -9.05,     # body
    2: -2.0,      # sinus
    3: -2.0,      # earcanal
    4: -4.2,      # trachea
    5: -4.2,      # right lung
    6: -4.2,      # left lung
    56: -9.04,    # brain
    60: -9.05,    # eyes
    91: -11.0,    # skull
    92: -11.0,    # vertebrae
    93: -9.055,   # disks
    100: -9.055,  # canal
    ADDED_LABEL: -9.05,   # added mannequin material (body extension, step 1b)
}

# Sidecar key per label. Spellings match the published r0 sidecars exactly,
# including "verterbae" - changing them would break comparability with the
# published dataset.
LABEL_NAMES = {
    0: "background",
    1: "body",
    2: "sinus",
    3: "earcanal",
    4: "trachea",
    5: "rightlung",
    6: "leftlung",
    56: "brain",
    60: "eyes",
    91: "skull",
    92: "verterbae",
    93: "disks",
    100: "canal",
    ADDED_LABEL: "bodyextension",
}


def label_to_chi(bids_subject_dir, fullbody=False):

    bids_subject_dir = Path(bids_subject_dir)
    subject = str(bids_subject_dir.stem)

    if fullbody:
        merged_labels_path = (bids_subject_dir / ".." / 'derivatives' / 'fullbody' /
                              subject / 'anat' / (subject + '_T1w_fullbody_label-all.nii.gz'))
    else:
        merged_labels_path = (bids_subject_dir / ".." / 'derivatives' / 'labels' /
                              subject / 'anat' / (subject + '_T1w_label-all.nii.gz'))

    vol = nib.load(merged_labels_path.resolve())
    vol_data = vol.get_fdata()

    # Map into a SEPARATE array. The previous version overwrote vol_data in
    # place with chained comparisons, which only worked because no chi value
    # collided with a label value - a trap for anyone adding a value later.
    labels_present = set(np.unique(vol_data).astype(int).tolist())
    unknown = labels_present - set(CHI_LUT)
    if unknown:
        raise SystemExit(f"labels not in CHI_LUT: {sorted(unknown)}")

    chi_data = np.zeros(vol_data.shape, np.float32)
    for value, chi in CHI_LUT.items():
        chi_data[vol_data == value] = chi

    new_volume = nib.Nifti1Image(chi_data, vol.affine, vol.header, dtype=np.float32)

    # Check if the directory  bids_subject_dir / ".." / 'derivatives' / subject / exists and if no, create it

    if not os.path.exists(bids_subject_dir / ".." / 'derivatives' / subject ):
        os.makedirs(bids_subject_dir / ".." / 'derivatives' / subject )

    # Check if the directory  bids_subject_dir / ".." / 'derivatives' / subject / 'anat' exists and if no, create it

    if not os.path.exists(bids_subject_dir / ".." / 'derivatives' / subject / 'anat' ):
        os.makedirs(bids_subject_dir / ".." / 'derivatives' / subject / 'anat' )
    
    chi_file = bids_subject_dir / ".." / 'derivatives' / subject / 'anat' / (subject + '_T1w-chi.nii.gz')

    nib.save(new_volume, chi_file)

    # Save json

    # Search from THIS SCRIPT's location, not the caller's cwd. The provenance
    # we want is the version of this repo that produced the map, and the run
    # driver's cwd is the bundle root, not the checkout - the previous
    # cwd-relative form raised InvalidGitRepositoryError there.
    repo = git.Repo(Path(__file__).resolve().parent, search_parent_directories=True)


    bids_sidecar = {}
    bids_sidecar['author'] = os.getenv('USER')
    bids_sidecar['date'] = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    bids_sidecar['script'] = str(Path(os.path.abspath(__file__)).resolve())
    bids_sidecar['script source'] = repo.remotes.origin.url
    bids_sidecar['script commit hash'] = repo.head.object.hexsha
    bids_sidecar['input file'] = str(merged_labels_path.resolve())
    bids_sidecar['command'] = ('python label_to_chi.py -s ' + str(bids_subject_dir)
                               + (' --fullbody' if fullbody else ''))

    bids_sidecar['anatomy'] = {
        LABEL_NAMES[label]: {'label': label, 'chi': chi}
        for label, chi in CHI_LUT.items()
    }

    json_file = bids_subject_dir / ".." / 'derivatives' / subject / 'anat' / (subject + '_T1w-chi.json')
    if os.path.exists(json_file):
        os.remove(json_file)

    with open(json_file, 'w', encoding='utf-8') as f:
        json.dump(bids_sidecar, f, ensure_ascii=False, indent=4)


if __name__ == "__main__":
    
    current_directory = os.path.dirname(os.path.abspath(__file__))

    # Create an argument parser
    parser = argparse.ArgumentParser(description="Process subject directory path and other arguments.")
    
    # Add the -s argument to the parser
    parser.add_argument("-s", "--bids_subject_dir", required=True, help="Path to the subject directory in BIDS format")
    parser.add_argument("--fullbody", action="store_true",
                        help="Read the body-extended label volume written by step 1b "
                             "(derivatives/fullbody/<sub>/anat/<sub>_T1w_fullbody_label-all.nii.gz) "
                             "instead of the acquired-FOV labels.")

    # Parse the arguments
    args = parser.parse_args()
    label_to_chi(args.bids_subject_dir, fullbody=args.fullbody)
