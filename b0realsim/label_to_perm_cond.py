import nibabel as nib
import numpy as np
import argparse
from pathlib import Path
import os
import json
import datetime
import git
from utils.tissue2MR import run_tissue2MR


def label_to_perm_cond(bids_subject_dir):

    bids_subject_dir = Path(bids_subject_dir)
    subject = str(bids_subject_dir.stem)
    merged_labels_path = bids_subject_dir / ".." / 'derivatives' / 'labels' / subject / 'anat' / (subject + '_T1w_label-all.nii.gz')

    # Check if the directory  bids_subject_dir / ".." / 'derivatives' / subject / exists and if no, create it

    if not os.path.exists(bids_subject_dir / ".." / 'derivatives' / subject ):
        os.makedirs(bids_subject_dir / ".." / 'derivatives' / subject )

    # Check if the directory  bids_subject_dir / ".." / 'derivatives' / subject / 'anat' exists and if no, create it

    if not os.path.exists(bids_subject_dir / ".." / 'derivatives' / subject / 'anat' ):
        os.makedirs(bids_subject_dir / ".." / 'derivatives' / subject / 'anat' )

    elecsim_anat_dir = bids_subject_dir / ".." / 'derivatives' / 'elecsim' / subject / 'anat'
    os.makedirs(elecsim_anat_dir, exist_ok=True)

    perm7t_file = bids_subject_dir / ".." / 'derivatives' / 'elecsim' / subject / 'anat' / (subject + '_T1w-perm7T.nii.gz')
    chi7t_file = bids_subject_dir / ".." / 'derivatives' / 'elecsim' / subject / 'anat' / (subject + '_T1w-cond7T.nii.gz')

    run_tissue2MR(
        in_file = str(merged_labels_path.resolve()),
        seg_tool = "compare_fm",
        version = "ds005616",
        tissue_prop = "perm7T",
        out_file = str(perm7t_file)
    )

    run_tissue2MR(
        in_file = str(merged_labels_path.resolve()),
        seg_tool = "compare_fm",
        version = "ds005616",
        tissue_prop = "cond7T",
        out_file = str(chi7t_file)
    )
    # Save json

    repo = git.Repo(search_parent_directories=True)


    bids_sidecar = {}
    bids_sidecar['author'] = os.getenv('USERNAME')
    bids_sidecar['date'] = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    bids_sidecar['script'] = str(Path(os.path.abspath(__file__)).resolve())
    bids_sidecar['script source'] = repo.remotes.origin.url
    bids_sidecar['script commit hash'] = repo.head.object.hexsha
    bids_sidecar['input file'] = str(merged_labels_path.resolve())
    bids_sidecar['command'] = 'python label_to_perm_cond.py -s ' + str(bids_subject_dir)

    json_perm7t_file = bids_subject_dir / ".." / 'derivatives' / subject / 'anat' / (subject + '_T1w-perm7T.json')
    json_cond7t_file = bids_subject_dir / ".." / 'derivatives' / subject / 'anat' / (subject + '_T1w-cond7T.json')
    if os.path.exists(json_perm7t_file):
        os.remove(json_perm7t_file)

    with open(json_perm7t_file, 'w', encoding='utf-8') as f:
        json.dump(bids_sidecar, f, ensure_ascii=False, indent=4)

    if os.path.exists(json_cond7t_file):
        os.remove(json_cond7t_file)

    with open(json_cond7t_file, 'w', encoding='utf-8') as f:
        json.dump(bids_sidecar, f, ensure_ascii=False, indent=4)


if __name__ == "__main__":
    
    current_directory = os.path.dirname(os.path.abspath(__file__))

    # Create an argument parser
    parser = argparse.ArgumentParser(description="Process subject directory path and other arguments.")
    
    # Add the -s argument to the parser
    parser.add_argument("-s", "--bids_subject_dir", required=True, help="Path to the subject directory in BIDS format")

    # Parse the arguments
    args = parser.parse_args()
    label_to_perm_cond(args.bids_subject_dir)
