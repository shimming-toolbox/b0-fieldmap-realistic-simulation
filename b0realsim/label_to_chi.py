import nibabel as nib
import numpy as np
import argparse
from pathlib import Path
import os
import json
import datetime
import git


def label_to_chi(bids_subject_dir):

    bids_subject_dir = Path(bids_subject_dir)
    subject = str(bids_subject_dir.stem)
    merged_labels_path = bids_subject_dir / ".." / 'derivatives' / 'labels' / subject / 'anat' / (subject + '_T1w_label-all.nii.gz')
    

    vol = nib.load(merged_labels_path.resolve())

    vol_data = vol.get_fdata()

    vol_data.astype(np.float64)

    vol_data[vol_data==0] = 0.35
    vol_data[vol_data==1] = -9.05
    vol_data[vol_data==2] = -2
    vol_data[vol_data==3] = -2
    vol_data[vol_data==4] = -4.2
    vol_data[vol_data==5] = -4.2
    vol_data[vol_data==6] = -4.2
    vol_data[vol_data==56] = -9.04
    vol_data[vol_data==60] = -9.05
    vol_data[vol_data==91] = -11
    vol_data[vol_data==92] = -11
    vol_data[vol_data==93] = -9.055
    vol_data[vol_data==100] = -9.055

    new_volume = nib.Nifti1Image(vol_data, vol.affine, vol.header,  dtype=np.float64)

    # Check if the directory  bids_subject_dir / ".." / 'derivatives' / subject / exists and if no, create it

    if not os.path.exists(bids_subject_dir / ".." / 'derivatives' / subject ):
        os.makedirs(bids_subject_dir / ".." / 'derivatives' / subject )

    # Check if the directory  bids_subject_dir / ".." / 'derivatives' / subject / 'anat' exists and if no, create it

    if not os.path.exists(bids_subject_dir / ".." / 'derivatives' / subject / 'anat' ):
        os.makedirs(bids_subject_dir / ".." / 'derivatives' / subject / 'anat' )
    
    chi_file = bids_subject_dir / ".." / 'derivatives' / subject / 'anat' / (subject + '_T1w-chi.nii.gz')

    nib.save(new_volume, chi_file)

    # Save json

    repo = git.Repo(search_parent_directories=True)


    bids_sidecar = {}
    bids_sidecar['author'] = os.getenv('USER')
    bids_sidecar['date'] = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    bids_sidecar['script'] = str(Path(os.path.abspath(__file__)).resolve())
    bids_sidecar['script source'] = repo.remotes.origin.url
    bids_sidecar['script commit hash'] = repo.head.object.hexsha
    bids_sidecar['input file'] = str(merged_labels_path.resolve())
    bids_sidecar['command'] = 'python label_to_chi.py -s ' + str(bids_subject_dir)

    bids_sidecar['anatomy'] = {}
    bids_sidecar['anatomy']['background'] = {}
    bids_sidecar['anatomy']['background']['label'] = 0
    bids_sidecar['anatomy']['background']['chi'] = 0.35
    bids_sidecar['anatomy']['body'] = {}
    bids_sidecar['anatomy']['body']['label'] = '1'
    bids_sidecar['anatomy']['body']['chi'] = -9.05
    bids_sidecar['anatomy']['sinus'] = {}
    bids_sidecar['anatomy']['sinus'] ['label'] = 2
    bids_sidecar['anatomy']['sinus'] ['chi'] = -2
    bids_sidecar['anatomy']['earcanal'] = {}
    bids_sidecar['anatomy']['earcanal'] ['label'] = 3
    bids_sidecar['anatomy']['earcanal']['chi'] = -2
    bids_sidecar['anatomy']['trachea'] = {}
    bids_sidecar['anatomy']['trachea']['label'] = 4
    bids_sidecar['anatomy']['trachea']['chi'] = -4.2
    bids_sidecar['anatomy']['rightlung'] = {}
    bids_sidecar['anatomy']['rightlung']['label'] = 5
    bids_sidecar['anatomy']['rightlung']['chi'] = -4.2
    bids_sidecar['anatomy']['leftlung'] = {}
    bids_sidecar['anatomy']['leftlung']['label'] = 6
    bids_sidecar['anatomy']['leftlung']['chi'] = -4.2
    bids_sidecar['anatomy']['brain'] = {}
    bids_sidecar['anatomy']['brain']['label'] = 56
    bids_sidecar['anatomy']['brain']['chi'] = -9.04
    bids_sidecar['anatomy']['eyes'] = {}
    bids_sidecar['anatomy']['eyes']['label'] = 60
    bids_sidecar['anatomy']['eyes']['chi'] = -9.05
    bids_sidecar['anatomy']['skull'] = {}
    bids_sidecar['anatomy']['skull']['label'] = 91
    bids_sidecar['anatomy']['skull']['chi'] = -11
    bids_sidecar['anatomy']['verterbae'] = {}
    bids_sidecar['anatomy']['verterbae']['label'] = 92
    bids_sidecar['anatomy']['verterbae']['chi'] = -11
    bids_sidecar['anatomy']['disks'] = {}
    bids_sidecar['anatomy']['disks']['label'] = 93
    bids_sidecar['anatomy']['disks']['chi'] = -9.055
    bids_sidecar['anatomy']['canal'] = {}
    bids_sidecar['anatomy']['canal']['label'] = 100
    bids_sidecar['anatomy']['canal']['chi'] = -9.055

    json_file = bids_subject_dir / ".." / 'derivatives' / subject / 'anat' / (subject + '_T1w-chi.json')
    if os.path.exists(json_file):
        os.remove(json_file)
    
    # Create the json file

    with open(json_file, 'w', encoding='utf-8') as f:
        json.dump(bids_sidecar, f, ensure_ascii=False, indent=4)


if __name__ == "__main__":
    
    current_directory = os.path.dirname(os.path.abspath(__file__))

    # Create an argument parser
    parser = argparse.ArgumentParser(description="Process subject directory path and other arguments.")
    
    # Add the -s argument to the parser
    parser.add_argument("-s", "--bids_subject_dir", required=True, help="Path to the subject directory in BIDS format")

    # Parse the arguments
    args = parser.parse_args()
    label_to_chi(args.bids_subject_dir)
