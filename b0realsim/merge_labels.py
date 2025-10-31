from pathlib import Path
import argparse
import os

from typing import List
import numpy.typing as npt

import nibabel as nib
import numpy as np
import pandas as pd
import matplotlib as mpl
import json
import datetime
import git


def merge_labels(
    list_labels: List[Path], config_file=None, flag=None, bids_subject_dir=None
) -> None:
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

    print(str(num_files) + " files were provided.")
    print("The labels provided are: ")
    print(*label_suffixes, ", ")

    # Load volumes of labels
    volume_set = {}

    for idx, label_path in enumerate(list_labels):

        volume_set[label_suffixes[idx]] = load_volume(label_path)

    print("Loaded the volumes for all the following files:")
    print(*volume_set.keys(), ", ")

    # Create new nifti volume, assuming the first label file can be used as a template
    template_path = list_labels[0]

    volume_nifti = create_volume(template_path)
    volume = volume_nifti.get_fdata()

    # Load configuration file if provided
    if config_file is not None:
        config_db = pd.read_csv(config_file, sep="\t", header=0)
    else:
        config_db = None

    if flag == "mergebrain":
        print("Merging brain labels")
        volume = set_labels(
            volume, volume_set[label_suffixes[3]], label_suffixes[3], config=config_db
        )
    else:
        # Set labels using predefined order
        # Order is set to: body, brain, spine, canal, lungs, skull, trachea, sinus,
        # earcanal, and then eyes.
        volume = set_labels(
            volume, volume_set[label_suffixes[9]], label_suffixes[9], config=config_db
        )

        volume = set_labels(
            volume,
            volume_set[label_suffixes[3]],
            label_suffixes[3],
            config=config_db,
            anatomy=["brain-merged"],
        )

        volume = set_labels(
            volume, volume_set[label_suffixes[2]], label_suffixes[2], config=config_db
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

    save_volume(template_path, volume, flag, list_labels, bids_subject_dir)

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

    nifti = nib.load(nifti_path.resolve())

    volume = nifti.get_fdata()

    # Flip volume if nifti orientation is inconsistent with other volumes
    if "R" in nib.orientations.aff2axcodes(nifti.affine):
        volume = volume[::-1, :, :]

    print("Volume loaded :" + str(nifti_path))

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

    try:
        nifti = nib.load(template_path)
    except FileNotFoundError:
        raise FileNotFoundError(f"Template file not found: {template_path}")
    except nib.filebasedimages.ImageFileError:
        raise nib.filebasedimages.ImageFileError(
            f"Error loading NIfTI file: {template_path}"
        )

    volume = nifti.get_fdata()

    volume.fill(0)

    new_volume = nib.Nifti1Image(volume, nifti.affine, nifti.header)

    return new_volume


def save_volume(
    template_path: Path, volume, flag, list_labels, bids_subject_dir
) -> nib.nifti1.Nifti1Image:
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

    if flag == "mergebrain":
        template_path = Path(
            str(template_path.resolve()).replace(
                "-air_tissue.nii.gz", "-brain_dseg.nii.gz"
            )
        )

    nifti = nib.load(template_path)

    new_volume = nib.Nifti1Image(volume.astype(np.int8), nifti.affine, nifti.header, dtype=np.int8)

    if flag == "mergebrain":
        save_path = Path(
            str(template_path.resolve()).replace(
                "-brain_dseg.nii.gz", "-brainonly_merged.nii.gz"
            )
        )
    else:
        save_path = Path(
            str(template_path.resolve()).replace("-air_tissue.nii.gz", "-all.nii.gz")
        )

    nib.save(new_volume, save_path)

    # JSON sidecar

    repo = git.Repo(search_parent_directories=True)

    bids_sidecar = {}
    bids_sidecar["author"] = os.getenv("USER")
    bids_sidecar["date"] = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    bids_sidecar["script"] = str(Path(os.path.abspath(__file__)).resolve())
    bids_sidecar["script source"] = repo.remotes.origin.url
    bids_sidecar["script commit hash"] = repo.head.object.hexsha
    if flag == "mergebrain":
        bids_sidecar["input file"] = str(Path(list_labels[3]).resolve())
    else:
        # For each file in list_labels, convert from Path to string and resolve the path
        list_labels = [str(Path(label).resolve()) for label in list_labels]

        bids_sidecar["input files"] = list_labels

    if flag == "mergebrain":
        bids_sidecar["label"] = {}
        bids_sidecar["label"]["anatomy"] = "brain"
        bids_sidecar["label"]["value"] = 56
    else:
        bids_sidecar["anatomy"] = {}
        bids_sidecar["anatomy"]["background"] = {}
        bids_sidecar["anatomy"]["background"]["label"] = 0
        bids_sidecar["anatomy"]["body"] = {}
        bids_sidecar["anatomy"]["body"]["label"] = "1"
        bids_sidecar["anatomy"]["sinus"] = {}
        bids_sidecar["anatomy"]["sinus"]["label"] = 2
        bids_sidecar["anatomy"]["earcanal"] = {}
        bids_sidecar["anatomy"]["earcanal"]["label"] = 3
        bids_sidecar["anatomy"]["trachea"] = {}
        bids_sidecar["anatomy"]["trachea"]["label"] = 4
        bids_sidecar["anatomy"]["rightlung"] = {}
        bids_sidecar["anatomy"]["rightlung"]["label"] = 5
        bids_sidecar["anatomy"]["leftlung"] = {}
        bids_sidecar["anatomy"]["leftlung"]["label"] = 6
        bids_sidecar["anatomy"]["brain"] = {}
        bids_sidecar["anatomy"]["brain"]["label"] = 56
        bids_sidecar["anatomy"]["eyes"] = {}
        bids_sidecar["anatomy"]["eyes"]["label"] = 60
        bids_sidecar["anatomy"]["skull"] = {}
        bids_sidecar["anatomy"]["skull"]["label"] = 91
        bids_sidecar["anatomy"]["verterbae"] = {}
        bids_sidecar["anatomy"]["verterbae"]["label"] = 92
        bids_sidecar["anatomy"]["disks"] = {}
        bids_sidecar["anatomy"]["disks"]["label"] = 93
        bids_sidecar["anatomy"]["canal"] = {}
        bids_sidecar["anatomy"]["canal"]["label"] = 100

    if flag == "mergebrain":
        bids_sidecar["command"] = (
            "python merge_labels.py -s " + str(bids_subject_dir) + " -f mergebrain "
        )
    else:
        bids_sidecar["command"] = "python merge_labels.py -s " + str(bids_subject_dir)

    json_file = str(Path(save_path).resolve()).replace(".nii.gz", ".json")
    if os.path.exists(json_file):
        os.remove(json_file)

    with open(json_file, "w", encoding="utf-8") as f:
        json.dump(bids_sidecar, f, ensure_ascii=False, indent=4)

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

    file_str = str(nifti_path.name)
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


def main(
    bids_subject_dir, flag=None, config=Path("config/whole-body-labels.tsv")
) -> None:
    """
    Main function to merge labels for a subject.

    Parameters
    ----------
    bids_subject_dir : str
        Path to the subject directory in BIDS format.
    flag : str, optional
        Optional flag argument. If set to 'mergebrain', the brain labels will be merged. Otherwise, the merged-brain labels will be used.
    config : Path, optional
        Path to the configuration file.

    Returns
    -------
    None
    """

    bids_subject_dir = Path(bids_subject_dir)
    subject = str(bids_subject_dir.stem)
    t1w_path = bids_subject_dir / "anat" / (subject + "_T1w.nii.gz")
    t1w = Path(t1w_path)

    t1w_stem = Path(t1w.stem).stem
    bids_dir = bids_subject_dir.parent
    derivatives_dir = bids_dir / "derivatives" / "labels" / subject / "anat"

    air_tissue = derivatives_dir / (t1w_stem + "_label-air_tissue.nii.gz")
    canal = derivatives_dir / (t1w_stem + "_label-canal_seg.nii.gz")
    spine = derivatives_dir / (t1w_stem + "_label-spine_dseg.nii.gz")

    if flag == "mergebrain":
        brain = derivatives_dir / (t1w_stem + "_label-brain_dseg.nii.gz")
    else:
        brain = derivatives_dir / (t1w_stem + "_label-brain.nii.gz")
    skin = derivatives_dir / (t1w_stem + "_label-skin.nii.gz")
    skull = derivatives_dir / (t1w_stem + "_label-skull.nii.gz")
    eyes = derivatives_dir / (t1w_stem + "_label-eyes.nii.gz")
    sinus = derivatives_dir / (t1w_stem + "_label-sinus.nii.gz")
    earcanal = derivatives_dir / (t1w_stem + "_label-earcanal.nii.gz")
    body = derivatives_dir / (t1w_stem + "_label-body.nii.gz")

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

    merge_labels(list_labels, config, flag, bids_subject_dir)

    return None


if __name__ == "__main__":
    current_directory = os.path.dirname(os.path.abspath(__file__))

    # Create an argument parser
    parser = argparse.ArgumentParser(
        description="Process subject directory path and other arguments."
    )

    # Add the -s argument to the parser
    parser.add_argument(
        "-s",
        "--subject_dir",
        required=True,
        help="Path to the subject directory in BIDS format",
    )

    # Add the -f argument to the parser
    parser.add_argument(
        "-f",
        "--flag",
        required=False,
        help="Optional flag argument. If set to 'mergebrain', the brain labels will be merged. Otherwise, the merged-brain labels will be used.",
    )

    # Add the -c argument to the parser
    parser.add_argument(
        "-c",
        "--config",
        required=False,
        default=Path(current_directory) / "../config/whole-body-labels.tsv",
        help="Path to the configuration file",
    )

    # Parse the arguments
    args = parser.parse_args()

    # Call the main function with parsed arguments
    main(bids_subject_dir=args.subject_dir, flag=args.flag, config=Path(args.config))
