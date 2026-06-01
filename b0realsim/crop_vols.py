import numpy as np
import nibabel as nib
from pathlib import Path
import argparse
import os


def main(dir):
    dir = Path(dir)

    # Find the names of the folders in the BIDS directory starting with "sub-" and store them in a list (not full path)

    subjects = [
        x.parts[-1]
        for x in dir.iterdir()
        if x.is_dir() and x.name.startswith("sub-")
    ]

    # Remove sub-unfErssm001 and sub-unfErssm021 from the list of subjects
    subjects = [
        x for x in subjects if x != "sub-unfErssm001" and x != "sub-unfErssm021"
    ]

    # initiate a list of numpy arrays to store the data without knowing prior shape
    fulldata = []
    fullmask = []
    mean_b0s = []

    for subject in subjects:
        print(subject)
        b0map = nib.load(
            dir 
            / subject 
            / (subject + "_T1w_fmap_b0-sim.nii.gz")
        )
        b0map_data = b0map.get_fdata()
        b0map_data = b0map_data[:, :, -301:]

        mask = nib.load(
            dir
            / subject 
            / (subject + "_mask.nii.gz")
        )

        mask_data = mask.get_fdata()
        mask_data = mask_data[:, :, -301:]

        t1w = nib.load(
            dir
            / subject 
            / (subject + "_T1w.nii.gz")
        )

        t1w_data = t1w.get_fdata()
        t1w_data = t1w_data[:, :, -301:]



        # Save head to nifti
        b0map_data = b0map_data * 10 #  Just arbitrary scaling to make it within the +- 100 hz range
        b0map_img = nib.Nifti1Image(b0map_data, b0map.affine, b0map.header)
        nib.save(b0map_img, dir / subject / (subject + "_T1w_fmap_b0-sim_head.nii.gz"))

        mask_img = nib.Nifti1Image(mask_data, mask.affine, mask.header)
        nib.save(mask_img, dir / subject / (subject + "_mask_head.nii.gz"))

        t1w_img = nib.Nifti1Image(t1w_data, t1w.affine, t1w.header)
        nib.save(t1w_img, dir / subject / (subject + "_T1w_head.nii.gz"))

if __name__ == "__main__":
    current_directory = os.path.dirname(os.path.abspath(__file__))

    # Create an argument parser
    parser = argparse.ArgumentParser(
        description="Process subject directory path and other arguments."
    )

    # Add the -s argument to the parser
    parser.add_argument(
        "-d", "--dir", required=True, help="Path to the dataset directory."
    )

    # Parse the arguments
    args = parser.parse_args()
    main(args.dir)
