from pathlib import Path

from typing import List
import numpy.typing as npt

import nibabel as nib
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

def merge_labels(list_labels: List[Path], config_file=None) -> None:
    """
    Merges multiple tissue label volumes into a single volume, optionally remapping labels based on a configuration file.

    Parameters
    ----------
    list_labels : List[Path]
        List of Paths to tissue labels.
    config : Path, optional
        Path to a configuration file in TSV format that specifies label remapping.

    Error
    -----
    Raises an error if any of the label files cannot be loaded or if the configuration file is invalid.

    Returns
    -------
    None
    """

    num_files = len(list_labels)

    # Get label suffixes
    label_suffixes = []

    for label_path in list_labels:
        label_suffixes.append(get_label_suffix(label_path))

    label_prefix = get_label_prefix(label_path)

    print(str(num_files) + " files were provided.")
    print("The labels provided are: ")
    print(*label_suffixes, ", ")

    # Load volumes of labels
    volume_set = {}

    for idx, label_path in enumerate(list_labels):
        volume_set[label_suffixes[idx]] = load_volume(label_path)

    print("Loaded the volumes for all the following files:")
    print(*volume_set.keys(), ", ")

    # Create new nifti volume
    template_path = list_labels[0]  # Assuming the first label file can be used as a template
    volume_nifti = create_volume(template_path)
    volume = volume_nifti.get_fdata()

    # Load configuration file if provided
    if config_file is not None:
        config_db = pd.read_csv(config_file, sep="\t", header=0)
    else:
        config_db = None

    #for idx, key in enumerate(volume_set):
    #    labels = volume_set[key]
    #    suffix = label_suffixes[idx]
    #    volume = set_labels(volume, labels, suffix, config=config_db)

    volume = set_labels(volume,  volume_set[label_suffixes[9]], label_suffixes[9], config=config_db)
    volume = set_labels(volume,  volume_set[label_suffixes[3]], label_suffixes[3], config=config_db)
    volume = set_labels(volume,  volume_set[label_suffixes[2]], label_suffixes[2], config=config_db)
    volume = set_labels(volume,  volume_set[label_suffixes[6]], label_suffixes[6], config=config_db)
    volume = set_labels(volume,  volume_set[label_suffixes[1]], label_suffixes[1], config=config_db)
    volume = set_labels(volume,  volume_set[label_suffixes[0]], label_suffixes[0], config=config_db, anatomy=['lung left', 'lung right'] )
    volume = set_labels(volume,  volume_set[label_suffixes[4]], label_suffixes[4], config=config_db, anatomy=['skull'] )
    volume = set_labels(volume,  volume_set[label_suffixes[0]], label_suffixes[0], config=config_db, anatomy=['trachea'])
    volume = set_labels(volume,  volume_set[label_suffixes[7]], label_suffixes[7], config=config_db)
    volume = set_labels(volume,  volume_set[label_suffixes[8]], label_suffixes[8], config=config_db)
    volume = set_labels(volume,  volume_set[label_suffixes[5]], label_suffixes[5], config=config_db, anatomy=['eyes'] )

    save_volume(template_path, volume)

    return None


def load_volume(nifti_path: Path) -> npt.NDArray:
    """
    Loads the volume of a NIfTI image as an ndarray

    Parameters
    ----------
    nifti_path : Path
        Path of Nifti file

    Returns
    -------
    volume : numpy.typing.NDArray
        Image volume
    """

    nifti = nib.load(nifti_path)

    volume = nifti.get_fdata()

    return volume


def create_volume(template_path: Path) -> nib.nifti1.Nifti1Image:
    """
    Creates a new NIfTI volume based on a template, with all voxel values set to zero.

    Parameters
    ----------
    template_path : Path
        Path to the template NIfTI file.

    Returns
    -------
    new_volume : nib.nifti1.Nifti1Image
        New NIfTI image with the same shape and affine as the template, but with all voxel values set to zero.
    """

    nifti = nib.load(template_path)

    volume = nifti.get_fdata()

    volume.fill(0)

    new_volume = nib.Nifti1Image(volume, nifti.affine, nifti.header)

    return new_volume

def save_volume(template_path: Path, volume) -> nib.nifti1.Nifti1Image:
    """
    Creates a new NIfTI volume based on a template, with all voxel values set to zero.

    Parameters
    ----------
    template_path : Path
        Path to the template NIfTI file.

    Returns
    -------
    new_volume : nib.nifti1.Nifti1Image
        New NIfTI image with the same shape and affine as the template, but with all voxel values set to zero.
    """

    nifti = nib.load(template_path)

    new_volume = nib.Nifti1Image(volume.astype(np.int8), nifti.affine, nifti.header,  dtype=np.int8)
    nib.save(new_volume,'sub-amuAL_T1w_label-all.nii.gz')
    return None

def get_label_suffix(nifti_path: Path) -> str:
    """
    Extracts the suffix of the BIDS label filename, i.e., the text that follows "label" in the filename.

    Parameters
    ----------
    nifti_path : Path
        Path of Nifti file.

    Returns
    -------
    file_suffix : str
        The suffix of the BIDS label filename.
    """

    file_str = str(nifti_path)
    file_suffix = file_str.split("label", 1)[1]

    return file_suffix

def get_label_prefix(nifti_path: Path) -> str:
    """
    Extracts the prefix of the BIDS label filename, i.e., the text that precedes "label" in the filename.
    """

    file_str = str(nifti_path)
    file_prefix = file_str.split("label", 1)[0]

    return file_prefix

def set_labels(volume, labels, suffix, config=None, anatomy=None) -> str:
    """
    Sets the labels to a volume, remapping if configured to do so.

    Parameters
    ----------
    volume : numpy.typing.NDArray
        The volume to set labels in.
    labels : numpy.typing.NDArray
        The labels to set in the volume.
    suffix : str
        The suffix of the label file.
    config : pandas.DataFrame, optional
        Configuration DataFrame for remapping labels.

    Returns
    -------
    file_suffix : str
        The suffix of the BIDS label filename.
    """
    breakpoint()
    file_db = config[config['source']==suffix]

    if anatomy is not None:
        for tissue in anatomy:
            new_label_val = int(file_db[file_db['anatomy']==tissue]["label"].values[0])
            old_label_val = int(file_db[file_db['anatomy']==tissue]["original-label"].values[0])
            volume[labels==old_label_val] = new_label_val 
    else:
        for tissue in file_db['anatomy'].tolist():
            new_label_val = int(file_db[file_db['anatomy']==tissue]["label"].values[0])
            old_label_val = file_db[file_db['anatomy']==tissue]["original-label"].values[0]
            volume[labels==old_label_val] = new_label_val 
    return volume


def main() -> None:
    air_tissue = Path("data/sub-amuAL_T1w_label-air_tissue.nii.gz")
    canal_seg = Path("data/sub-amuAL_T1w_label-canal_seg.nii.gz")
    spine_dseg = Path("data/sub-amuAL_T1w_label-spine_dseg.nii.gz")
    #brain_dseg = Path("data/sub-amuAL_T1w_label-brain_dseg.nii.gz")
    brainonly_dseg = Path("data/sub-amuAL_T1w_label-brainonly_merged.nii.gz")
    skin_dseg = Path("data/sub-amuAL_T1w_label-skin.nii.gz")
    skull = Path("data/sub-amuAL_T1w_label-skull.nii.gz")
    eyes = Path("data/sub-amuAL_T1w_label-eyes.nii.gz")
    sinus = Path("data/sub-amuAL_T1w_label-sinus.nii.gz")
    earcanal = Path("data/sub-amuAL_T1w_label-earcanal.nii.gz")
    body = Path("data/sub-amuAL_T1w_label-body.nii.gz")

    list_labels = [air_tissue, canal_seg, spine_dseg, brainonly_dseg, skull, eyes, skin_dseg, sinus, earcanal, body]

    config = Path("config/whole-body-labels.tsv")

    merge_labels(list_labels, config)

    return None


if __name__ == "__main__":
    main()
