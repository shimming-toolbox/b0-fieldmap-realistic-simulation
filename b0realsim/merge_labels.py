from pathlib import Path

from typing import List
import numpy.typing as npt

import nibabel as nib
from nibabel.affines import apply_affine
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
    template_path = list_labels[
        0
    ]  # Assuming the first label file can be used as a template
    volume_nifti = create_volume(template_path)
    volume = volume_nifti.get_fdata()

    # Load configuration file if provided
    if config_file is not None:
        config_db = pd.read_csv(config_file, sep="\t", header=0)
    else:
        config_db = None

    # for idx, key in enumerate(volume_set):
    #    labels = volume_set[key]
    #    suffix = label_suffixes[idx]
    #    volume = set_labels(volume, labels, suffix, config=config_db)

    volume = set_labels(
        volume, volume_set[label_suffixes[9]], label_suffixes[9], config=config_db
    )
    volume = set_labels(
        volume, volume_set[label_suffixes[3]], label_suffixes[3], config=config_db
    )
    volume = set_labels(
        volume, volume_set[label_suffixes[2]], label_suffixes[2], config=config_db
    )
    volume = set_labels(
        volume, volume_set[label_suffixes[6]], label_suffixes[6], config=config_db
    )
    volume = set_labels(
        volume, volume_set[label_suffixes[1]], label_suffixes[1], config=config_db
    )
    volume = set_labels(
        volume,
        volume_set[label_suffixes[0]],
        label_suffixes[0],
        config=config_db,
        anatomy=["lung left", "lung right"],
    )
    volume = set_labels(
        volume,
        volume_set[label_suffixes[4]],
        label_suffixes[4],
        config=config_db,
        anatomy=["skull"],
    )
    volume = set_labels(
        volume,
        volume_set[label_suffixes[0]],
        label_suffixes[0],
        config=config_db,
        anatomy=["trachea"],
    )
    volume = set_labels(
        volume, volume_set[label_suffixes[7]], label_suffixes[7], config=config_db
    )
    volume = set_labels(
        volume, volume_set[label_suffixes[8]], label_suffixes[8], config=config_db
    )
    volume = set_labels(
        volume,
        volume_set[label_suffixes[5]],
        label_suffixes[5],
        config=config_db,
        anatomy=["eyes"],
    )

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
    print(nib.orientations.aff2axcodes(nifti.affine))
    if nifti_path == Path("data/sub-unfErssm010_T1w_label-canal_seg.nii.gz"):
        # original_affine = nifti.affine
        # target_affine = np.array([
        # [-9.99812543e-01,  1.00949360e-16,  1.93620156e-02,  7.96067123e+01],
        # [ 9.99812545e-17,  1.00000000e+00, -5.09681033e-17, -1.41025833e+02],
        # [ 1.93620156e-02,  4.90227068e-17,  9.99812543e-01, -5.71042419e+02],
        # [ 0.00000000e+00,  0.00000000e+00,  0.00000000e+00,  1.00000000e+00]
        # ])
        # Compute the inverse of the original affine
        # inverse_affine = np.linalg.inv(original_affine)

        # Transform the volume to voxel space using the inverse affine
        # voxel_space_volume = nib.affines.apply_affine(inverse_affine, volume)

        # Transform the volume to the target affine space
        # volume = nib.affines.apply_affine(target_affine, voxel_space_volume)
        # volume = nib.affines.apply_affine(target_affine, voxel_space_volume)

        volume = volume[::-1, :, :]

    print("Volume loaded :" + str(nifti_path))
    print("Affine is:")
    print(nifti.affine)
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

    new_volume = nib.Nifti1Image(
        volume.astype(np.int8), nifti.affine, nifti.header, dtype=np.int8
    )
    nib.save(new_volume, "sub-unfErssm010_T1w_label-all.nii.gz")
    # nib.save(new_volume,'sub-unfErssm010_T1w_label-brain_dseg-merged.nii.gz')
    # nib.save(new_volume, 'sub-unfErssm010_T1w_label-brain_dseg.nii.gz')

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

    file_db = config[config["source"] == suffix]

    if anatomy is not None:
        for tissue in anatomy:
            new_label_val = int(
                file_db[file_db["anatomy"] == tissue]["label"].values[0]
            )
            old_label_val = int(
                file_db[file_db["anatomy"] == tissue]["original-label"].values[0]
            )
            volume[labels == old_label_val] = new_label_val
    else:
        for tissue in file_db["anatomy"].tolist():
            new_label_val = int(
                file_db[file_db["anatomy"] == tissue]["label"].values[0]
            )
            old_label_val = file_db[file_db["anatomy"] == tissue][
                "original-label"
            ].values[0]
            volume[labels == old_label_val] = new_label_val
    return volume


def main(t1w, flag=None, config=Path("config/whole-body-labels.tsv")) -> None:

    t1w = Path("data/sub-unfErssm010_T1w.nii.gz")
    t1w_stem = Path(t1w.stem).stem

    air_tissue = Path("data/" + t1w_stem + "_label-air_tissue.nii.gz")
    canal = Path("data/" + t1w_stem + "_label-canal_seg.nii.gz")
    spine = Path("data/" + t1w_stem + "_T1w_label-spine_dseg.nii.gz")
    if flag == "mergebrain":
        brain = Path("data/" + t1w_stem + "_label-brain_dseg.nii.gz")
    else:
        brain = Path("data/" + t1w_stem + "_label-brainonly_merged.nii.gz")
    skin = Path("data/" + t1w_stem + "_label-skin.nii.gz")
    skull = Path("data/" + t1w_stem + "_label-skull.nii.gz")
    eyes = Path("data/" + t1w_stem + "_label-eyes.nii.gz")
    sinus = Path("data/" + t1w_stem + "_label-sinus.nii.gz")
    earcanal = Path("data/" + t1w_stem + "_label-earcanal.nii.gz")
    body = Path("data/" + t1w_stem + "_label-body.nii.gz")

    list_labels = [
        air_tissue,
        canal,
        spine,
        brain,
        skull,
        eyes,
        skin,
        sinus,
        earcanal,
        body,
    ]

    merge_labels(list_labels, config)

    return None


if __name__ == "__main__":
    main()
