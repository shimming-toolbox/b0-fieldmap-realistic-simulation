import numpy as np
import nibabel as nib
from pathlib import Path
import argparse
import os


def main(bids_dir):
    bids_dir = Path(bids_dir)

    # If b0shim directory does not exist in bids_dir / "derivatives", create it
    dir = bids_dir / "derivatives" / "b0shim"
    if not dir.exists():
        dir.mkdir(parents=True, exist_ok=True)
    else:
        print(f"Directory {dir} already exists. Skipping creation.")

    # Find the names of the folders in the BIDS directory starting with "sub-" and store them in a list (not full path)

    subjects = [
        x.parts[-1]
        for x in bids_dir.iterdir()
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
            bids_dir
            / "derivatives"
            / "labels"
            / subject
            / "anat"
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
            bids_dir
            / "derivatives"
            / "labels"
            / subject
            / "anat"
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
        mask_tissue = mask.copy()
        mask_tissue = mask_tissue[:, :, -301:]

        b0map = nib.load(
            bids_dir
            / "derivatives"
            / subject
            / "fmap"
            / (subject + "_T1w_fmap_b0-sim.nii.gz")
        )

        b0map = b0map.get_fdata()
        
        # Crop head
        mask = mask[:, :, -301:]
        b0map = b0map[:, :, -301:]


        # Scale the b0map from ppm Hz (3T)
        b0map = b0map *  123.2

        mean_b0 = np.ma.masked_array(b0map, np.logical_not(mask)).mean()
        b0map = b0map - mean_b0
        print(f"{subject}: {b0map.shape}")

        # reset
        label = nib.load(
            bids_dir
            / "derivatives"
            / "labels"
            / subject
            / "anat"
            / (subject + "_T1w_label-all.nii.gz")
        )

        mask = label.get_fdata()
        mask = mask[:, :, -301:]

        mask[mask > 0] = 1
        mask = np.ndarray.astype(mask, int)

        fulldata.append(np.squeeze(b0map[centerline, :, :]) - mean_b0)
        fullmask.append(np.squeeze(mask[centerline, :, :]))

        # Make subject directory if it does not exist\
        subject_dir = bids_dir / "derivatives" / "b0shim"  / subject 
        if not subject_dir.exists():
            subject_dir.mkdir(parents=True, exist_ok=True)
        else:
            print(f"Directory {subject_dir} already exists. Skipping creation.")

        # Save head to nifti

        t1w_nii = nib.load(
            bids_dir
            / subject
            / "anat"
            / (subject + "_T1w.nii.gz")
        )

        b0map_img = nib.Nifti1Image(b0map, t1w_nii.affine, t1w_nii.header)
        nib.save(b0map_img,  bids_dir / "derivatives" / "b0shim"  / subject / (subject + "_T1w_fmap_b0-sim_head.nii.gz"))

        mask_img = nib.Nifti1Image(mask_tissue, label.affine, label.header)
        nib.save(mask_img, bids_dir / "derivatives" / "b0shim" / subject / (subject + "_mask_head.nii.gz"))

        t1w = t1w_nii.get_fdata()
        t1w = t1w[:, :, -301:]
        
        t1w_img = nib.Nifti1Image(t1w, t1w_nii.affine, t1w_nii.header)
        nib.save(t1w_img, bids_dir / "derivatives" / "b0shim" / subject /  (subject + "_T1w_head.nii.gz"))
        
        # Copy B0 map and T1w json file to new directory
        b0map_json = bids_dir / "derivatives" / subject / "fmap" / (subject + "_T1w_fmap_b0-sim.json")
        t1w_json = bids_dir / subject / "anat" / (subject + "_T1w.json")
        if b0map_json.exists():
            import shutil
            shutil.copy(b0map_json, bids_dir / "derivatives" / "b0shim" / subject / (subject + "_T1w_fmap_b0-sim_head.json"))
        else:
            print(f"JSON file {b0map_json} does not exist. Skipping copy.")
        if t1w_json.exists():
            shutil.copy(t1w_json, bids_dir / "derivatives" / "b0shim" / subject / (subject + "_T1w_head.json"))
        else:
            print(f"JSON file {t1w_json} does not exist. Skipping copy.")
        
        # Load T1w json file and update it
        import json
        t1w_json_path = bids_dir / "derivatives" / "b0shim" / subject / (subject + "_T1w_head.json")
        with open(t1w_json_path, 'r') as f:
            t1w_json = json.load(f)
        t1w_json["Manufacturer"] = "Siemens"
        t1w_json["ManufacturersModelName"] = "Prisma_fit"
        t1w_json["PatientPosition"]= "HFS"
        t1w_json["TablePosition"] = [0,0,0]
        t1w_json["ShimSetting"] = [0,0,0,0,0,0,0,0	]
        t1w_json["ImagingFrequency"] = 123.249
        
        # Save updated T1w json file
        with open(t1w_json_path, 'w') as f:
            json.dump(t1w_json, f, indent=4)

        # Load B0 json file and update it
        b0map_json_path = bids_dir / "derivatives" / "b0shim" / subject / (subject + "_T1w_fmap_b0-sim_head.json")
        with open(b0map_json_path, 'r') as f:
            b0map_json = json.load(f)
        b0map_json["Manufacturer"] = "Siemens"
        b0map_json["ManufacturersModelName"] = "Prisma_fit"
        b0map_json["PatientPosition"] = "HFS"
        b0map_json["TablePosition"] = [0, 0, 0]
        b0map_json["ShimSetting"] = [0, 0, 0, 0, 0, 0, 0, 0]
        b0map_json["ImagingFrequency"] = 123.249

        # Save updated B0 json file
        with open(b0map_json_path, 'w') as f:
            json.dump(b0map_json, f, indent=4)


        del b0map, mask



if __name__ == "__main__":
    current_directory = os.path.dirname(os.path.abspath(__file__))

    # Create an argument parser
    parser = argparse.ArgumentParser(
        description="Process subject directory path and other arguments."
    )

    # Add the -s argument to the parser
    parser.add_argument(
        "-b", "--bids_dir", required=True, help="Path to the BIDS dataset directory."
    )

    # Parse the arguments
    args = parser.parse_args()
    main(args.bids_dir)
