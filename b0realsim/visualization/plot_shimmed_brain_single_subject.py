import numpy as np
import nibabel as nib
from pathlib import Path
import argparse
import os
import yaml
import matplotlib.pyplot as plt
from matplotlib.colors import Normalize
from matplotlib.cm import ScalarMappable


def find_centerlines(label_data):
    """Find centerline slice indices for all three orientations."""
    centerlines = {}

    # Sagittal: label 4 (spine), sum over z and y, find x-index
    data = label_data.copy()
    data[data != 4] = 0
    data = np.ndarray.sum(data, 2)
    data = np.ndarray.sum(data, 1)
    centerlines["sagittal"] = np.argmax(data)

    # Coronal: label 3 (ear canal), sum over z and x, find y-index
    data = label_data.copy()
    data[data != 3] = 0
    data = np.ndarray.sum(data, 2)
    data = np.ndarray.sum(data, 0)
    centerlines["coronal"] = np.argmax(data)

    return centerlines


def extract_slice(volume, orientation, centerline):
    """Extract a 2D slice from a 3D volume given orientation and index."""
    if orientation == "axial":
        return np.squeeze(volume[:, :, centerline])
    elif orientation == "sagittal":
        return np.squeeze(volume[centerline, :, :])
    elif orientation == "coronal":
        return np.squeeze(volume[:, centerline, :])


def save_plot(slice_data, mask_slice, output_path):
    """Save a single brain-masked B0 slice as a PNG."""
    fig, ax = plt.subplots()
    cmap = plt.get_cmap("bwr")

    im = ax.imshow(np.rot90(slice_data), cmap=cmap, vmin=-100, vmax=100)

    ax.tick_params(
        axis="both",
        which="both",
        bottom=False,
        top=False,
        left=False,
        right=False,
        labelbottom=False,
        labelleft=False,
    )
    ax.xaxis.set_visible(False)
    ax.yaxis.set_visible(False)

    masked = np.ma.masked_where(mask_slice == 1, mask_slice)
    plt.imshow(np.rot90(masked), alpha=1, cmap="Greys")

    norm = Normalize(vmin=-100, vmax=100)
    sm = ScalarMappable(norm=norm, cmap=cmap)
    sm.set_array([])

    plt.gca().axis("off")
    clb = plt.colorbar(sm, ax=ax)
    clb.ax.set_title("B0 (Hz)")

    plt.savefig(output_path, dpi=1200)
    plt.close(fig)


def main(subject_dir, axial_slice_yaml=None):
    subject_dir = Path(subject_dir)
    subject = subject_dir.name
    bids_dir = subject_dir.parent

    print(f"Processing {subject}")

    # Load label volume
    label_path = (
        bids_dir
        / "derivatives"
        / "labels"
        / subject
        / "anat"
        / (subject + "_T1w_label-all.nii.gz")
    )
    label_data = nib.load(label_path).get_fdata()

    # Find centerlines for sagittal and coronal
    centerlines = find_centerlines(label_data)
    print(f"  Sagittal centerline (spine, label 4): {centerlines['sagittal']}")
    print(f"  Coronal centerline (ear canal, label 3): {centerlines['coronal']}")

    # Axial centerline from yaml
    if axial_slice_yaml is not None:
        with open(axial_slice_yaml) as f:
            slices = yaml.safe_load(f)
        z_len = label_data.shape[2]
        centerlines["axial"] = 301 - (z_len - slices[subject])
        print(f"  Axial centerline (from yaml): {centerlines['axial']}")
    else:
        # Fallback: use eyes (label 60) center of mass along z, in cropped space
        data = label_data.copy()
        data[data != 60] = 0
        data = data[:, :, -301:]
        data = np.ndarray.sum(data, 0)
        data = np.ndarray.sum(data, 0)
        centerlines["axial"] = np.argmax(data)
        print(f"  Axial centerline (eyes, label 60): {centerlines['axial']}")

    # Build brain mask (label 56), cropped to last 301 slices to match head fieldmaps
    mask_data = nib.load(label_path).get_fdata()
    mask_data = mask_data[:, :, -301:]
    mask_data[mask_data != 56] = 0
    mask_data[mask_data == 56] = 1
    mask_int = np.ndarray.astype(mask_data, int)

    # Load unshimmed b0map
    b0map_unshimmed = nib.load(
        bids_dir
        / "derivatives"
        / "b0shim"
        / subject
        / (subject + "_T1w_fmap_b0-sim_head.nii.gz")
    ).get_fdata()

    mean_b0_unshimmed = np.ma.masked_array(
        b0map_unshimmed, np.logical_not(mask_int)
    ).mean()

    # Load step1 shimmed b0map
    step1_path = (
        bids_dir
        / "derivatives"
        / "b0shim"
        / subject
        / "output-paper-step1"
        / "fieldmap_calculated_shim.nii.gz"
    )
    if step1_path.exists():
        b0map_step1 = nib.load(step1_path).get_fdata()
    else:
        print(f"  WARNING: step1 shim not found, using zeros")
        b0map_step1 = np.zeros_like(b0map_unshimmed)

    mean_b0_step1 = np.ma.masked_array(
        b0map_step1, np.logical_not(mask_int)
    ).mean()

    # Load step2 shimmed b0map
    step2_path = (
        bids_dir
        / "derivatives"
        / "b0shim"
        / subject
        / "output-paper-step2"
        / "fieldmap_calculated_shim.nii.gz"
    )
    if step2_path.exists():
        b0map_step2 = nib.load(step2_path).get_fdata()
    else:
        print(f"  WARNING: step2 shim not found, using zeros")
        b0map_step2 = np.zeros_like(b0map_unshimmed)

    mean_b0_step2 = np.ma.masked_array(
        b0map_step2, np.logical_not(mask_int)
    ).mean()

    # Print stats
    print(f"  Mean abs(B0) unshimmed: {np.ma.masked_array(abs(b0map_unshimmed - mean_b0_unshimmed), np.logical_not(mask_int)).mean():.2f}")
    print(f"  Mean abs(B0) step1:     {np.ma.masked_array(abs(b0map_step1 - mean_b0_step1), np.logical_not(mask_int)).mean():.2f}")
    print(f"  Mean abs(B0) step2:     {np.ma.masked_array(abs(b0map_step2 - mean_b0_step2), np.logical_not(mask_int)).mean():.2f}")

    # Define conditions
    conditions = {
        "unshimmed": (b0map_unshimmed, mean_b0_unshimmed),
        "shimmed_step1": (b0map_step1, mean_b0_step1),
        "shimmed_step2": (b0map_step2, mean_b0_step2),
    }

    orientations = ["axial", "sagittal", "coronal"]

    # Generate all 9 PNGs
    for orientation in orientations:
        cl = centerlines[orientation]
        mask_slice = extract_slice(mask_int, orientation, cl)

        for condition_name, (b0map, mean_b0) in conditions.items():
            b0_slice = extract_slice(b0map, orientation, cl) - mean_b0

            output_name = f"{subject}_{orientation}_{condition_name}_brainmasked.png"
            print(f"  Saving {output_name}")
            save_plot(b0_slice, mask_slice, output_name)

    print("Done.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Generate individual brain-masked B0 slice PNGs for a single subject."
    )

    parser.add_argument(
        "-s", "--subject_dir", required=True,
        help="Path to the BIDS subject directory (e.g., /path/to/bids/sub-xxx)."
    )
    parser.add_argument(
        "-a", "--axial_slice_yaml", required=False, default=None,
        help="Path to axial_slice.yaml for axial slice index. If not provided, uses eyes (label 60) center."
    )

    args = parser.parse_args()
    main(args.subject_dir, args.axial_slice_yaml)
