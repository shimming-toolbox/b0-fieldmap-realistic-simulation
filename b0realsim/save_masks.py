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
        label = nib.load(
            dir 
            / subject 
            / (subject + "_T1w_label-all.nii.gz")
        )
        data = label.get_fdata()

        data[data != 4] = 0
        data = np.ndarray.sum(data, 2)
        data = np.ndarray.sum(data, 1)
        centerline = np.argmax(data)
        print(centerline)
        del data

        label = nib.load(
            dir
            / subject 
            / (subject + "_T1w_label-all.nii.gz")
        )
        mask = label.get_fdata()
        mask[mask == 2] = 0
        mask[mask == 3] = 0
        mask[mask == 4] = 0
        mask[mask == 5] = 0
        mask[mask == 6] = 0
        mask[mask == 91] = 0
        mask[mask == 92] = 0
        mask[mask > 0] = 1
        mask = np.ndarray.astype(mask, bool)

        # Save mask to nifti
        mask_img = nib.Nifti1Image(mask, label.affine, label.header)
        nib.save(mask_img, dir / subject / (subject + "_mask.nii.gz"))


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
