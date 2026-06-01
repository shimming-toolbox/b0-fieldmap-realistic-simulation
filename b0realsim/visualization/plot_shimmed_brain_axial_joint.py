import numpy as np
import nibabel as nib
from pathlib import Path
import argparse
import os
import yaml
import gc

def main(bids_dir):
    bids_dir = Path(bids_dir)

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

    # Load slices yaml
    with open('axial_slice.yaml') as f:
        slices = yaml.safe_load(f)
    
    # initiate a list of numpy arrays to store the data without knowing prior shape
    fulldata = []
    fulldata_shimmed = []
    fullmask = []
    mean_b0_array = np.array([])
    mean_b0_array_shimmed =  np.array([])
    mask_array = np.array([])

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
        data[data != 60] = 0
        z_len = data.shape[2]
        data = data[:, :, -301:]
        #data = np.ndarray.sum(data, 1)
        #data = np.ndarray.sum(data, 0)
        centerline = data.shape[2] - (z_len-slices[subject])
        print(centerline)

        label = nib.load(
            bids_dir
            / "derivatives"
            / "labels"
            / subject
            / "anat"
            / (subject + "_T1w_label-all.nii.gz")
        )
        mask = label.get_fdata()
        mask[mask != 56] = 0
        mask[mask == 56] = 1
        mask = np.ndarray.astype(mask, bool)

        b0map = nib.load(
            bids_dir
            / "derivatives"
            / "b0shim"
            / subject
            / (subject + "_T1w_fmap_b0-sim_head.nii.gz")
        )

        b0map = b0map.get_fdata()
        
        # Check if fieldmap_calculated_shim.nii.gz exists, if not, all zeros
        if not (bids_dir / "derivatives" / "b0shim" / subject / "output-paper-step1" / "fieldmap_calculated_shim.nii.gz").exists():
            print(subject)
            #assert False
            b0map_shimmed = np.zeros_like(b0map)

        else:
            # Load the shimmed b0map
            b0map_shimmed = nib.load(
                bids_dir
                / "derivatives"
                / "b0shim"
                / subject
                / "output-paper-step2"
                / "fieldmap_calculated_shim.nii.gz"
            )

            b0map_shimmed = b0map_shimmed.get_fdata()


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

        mask[mask != 56] = 0
        mask[mask == 56] = 1
        mask = np.ndarray.astype(mask, int)
        

        mean_b0 = np.ma.masked_array(b0map, np.logical_not(mask)).mean()
        mean_b0_shimmed = np.ma.masked_array(b0map_shimmed, np.logical_not(mask)).mean()

        mean_b0_array = np.append(mean_b0_array,(b0map - mean_b0)[:])
        mean_b0_array_shimmed = np.append(mean_b0_array_shimmed,(b0map_shimmed - mean_b0_shimmed)[:])
        mask_array = np.append(mask_array,mask[:])

        print("Mean abs(B0) in the original in the mask is: ",  np.ma.masked_array(abs(b0map-mean_b0), np.logical_not(mask)).mean())
        print("Mean abs(B0) in the shimmed in the mask is: ", np.ma.masked_array(abs(b0map_shimmed-mean_b0_shimmed), np.logical_not(mask)).mean())

        fulldata.append(np.squeeze(b0map[:, :, centerline]-mean_b0))
        fulldata_shimmed.append(np.squeeze(b0map_shimmed[:, :, centerline]-mean_b0_shimmed))
        fullmask.append(np.squeeze(mask[:, :, centerline]))

        del data, mask, b0map, b0map_shimmed
        gc.collect() 
    print(mean_b0_array)
    print(np.ma.masked_array(mean_b0_array, np.logical_not(mask_array)).mean())
    print(np.std(mean_b0_array))
    print(np.mean(mean_b0_array_shimmed))
    print(np.std(mean_b0_array_shimmed))    


    # Create a 6x12 concatenation of the images in fulldata. The dimensions sizes are heterogenous, so we need to pad the smaller ones with zeros
    
    # Find the maximum size in the first dimension
    max_size1 = max([x.shape[0] for x in fulldata])
    max_size2 = max([x.shape[1] for x in fulldata])
    
    # Create a new array with the maximum size in the first dimension
    concatenated = np.ones((max_size1 * 12, max_size2 * 5)) * (-500)
    concatenated_shimmed = np.ones((max_size1 * 12, max_size2 * 5)) * (-500)
    concatenated_mask = np.zeros((max_size1 * 12, max_size2 * 5)) * (500)

    print(concatenated.shape)

    # Fill the new array with the data
    for i, data in enumerate(fulldata):
        print(i)
        print(data[:, 0:max_size2])
        print("xrange")
        print(max_size1 * (i % 12))
        print(data.shape[0] + max_size1 * (i % 12))
        print("yrange")
        print(max_size2 * (int(i / 12)))
        print(data.shape[1] + max_size2 * (int(i / 12)))

        temp_data = data
        temp_shimmed_data = fulldata_shimmed[i]
        temp_mask = fullmask[i]

        if temp_data.shape[0] < max_size1:
            # Pad the data with zeros to the right
            pad_left = (max_size1 - temp_data.shape[0])//2
            pad_right = max_size1 - temp_data.shape[0] - pad_left
            temp_data = np.pad(temp_data, ((pad_left, pad_right), (0, 0)), mode='constant', constant_values=0)
            temp_shimmed_data = np.pad(temp_shimmed_data, ((pad_left, pad_right), (0, 0)), mode='constant', constant_values=0)
            temp_mask = np.pad(temp_mask, ((pad_left, pad_right), (0, 0)), mode='constant', constant_values=0)


        if temp_data.shape[1] < max_size2:
            # Pad the data with zeros to the right
            pad_left = (max_size2 - temp_data.shape[1])//2
            pad_right = max_size2 - temp_data.shape[1] - pad_left
            temp_data = np.pad(temp_data, ((0, 0), (pad_left, pad_right)), mode='constant', constant_values=0)
            temp_shimmed_data = np.pad(temp_shimmed_data, ((0, 0), (pad_left, pad_right)), mode='constant', constant_values=0)
            temp_mask = np.pad(temp_mask, ((0, 0), (pad_left, pad_right)), mode='constant', constant_values=0)

        concatenated[
            max_size1 * (i % 12) : (max_size1 + max_size1 * (i % 12)),
            max_size2 * (int(i / 12)) : max_size2 * (int(i / 12) + 1),
        ] = temp_data

        concatenated_shimmed[
            max_size1 * (i % 12) : (max_size1 + max_size1 * (i % 12)),
            max_size2 * (int(i / 12)) : max_size2 * (int(i / 12) + 1),
        ] = temp_shimmed_data

        mask = data[:, -data.shape[1]:]
        mask[mask != 0] = 1
        concatenated_mask[
            max_size1 * (i % 12) : (max_size1 + max_size1 * (i % 12)),
            max_size2 * (int(i / 12)) : max_size2 * (int(i / 12) + 1),
        ] = temp_mask

    # Save the concatenated data as a png and blue-white-red colormap, centered at zero
    import matplotlib.pyplot as plt
    from matplotlib.colors import Normalize
    from matplotlib.cm import ScalarMappable

    # Create a figure and axes
    fig, ax = plt.subplots()
    cmap = plt.get_cmap("bwr")

    # Display the image
    im = ax.imshow(np.rot90(concatenated), cmap=cmap, vmin=-100, vmax=100)

    # Disable ticks and labels on both axes
    ax.tick_params(
        axis="both",  # changes apply to both axes
        which="both",  # both major and minor ticks are affected
        bottom=False,  # ticks along the bottom edge are off
        top=False,  # ticks along the top edge are off
        left=False,  # ticks along the left edge are off
        right=False,  # ticks along the right edge are off
        labelbottom=False,  # labels along the bottom edge are off
        labelleft=False,
    )  # labels along the left edge are off

    # Hide the axes
    ax.xaxis.set_visible(False)
    ax.yaxis.set_visible(False)

    masked = np.ma.masked_where(concatenated_mask == 1, concatenated_mask)
    plt.imshow(np.rot90(masked), alpha=1, cmap="Greys")

    # Add colorbar
    norm = Normalize(vmin=-100, vmax=100)
    sm = ScalarMappable(norm=norm, cmap=cmap)
    sm.set_array([])
    # fig.colorbar(sm, ax=ax)

    plt.gca().axis("off")
    clb = plt.colorbar(sm, ax=ax)
    clb.ax.set_title("B0 (Hz)")

    plt.savefig("subject-mosaic-brain_unshimmed_axial_fixedslice-brainmasked_slicewise.png", dpi=1200)

    # Repeat for shimmed
    import matplotlib.pyplot as plt
    from matplotlib.colors import Normalize
    from matplotlib.cm import ScalarMappable

    # Create a figure and axes
    fig, ax = plt.subplots()
    cmap = plt.get_cmap("bwr")

    # Display the image
    im = ax.imshow(np.rot90(concatenated_shimmed), cmap=cmap, vmin=-100, vmax=100)

    # Disable ticks and labels on both axes
    ax.tick_params(
        axis="both",  # changes apply to both axes
        which="both",  # both major and minor ticks are affected
        bottom=False,  # ticks along the bottom edge are off
        top=False,  # ticks along the top edge are off
        left=False,  # ticks along the left edge are off
        right=False,  # ticks along the right edge are off
        labelbottom=False,  # labels along the bottom edge are off
        labelleft=False,
    )  # labels along the left edge are off

    # Hide the axes
    ax.xaxis.set_visible(False)
    ax.yaxis.set_visible(False)

    masked = np.ma.masked_where(concatenated_mask == 1, concatenated_mask)
    plt.imshow(np.rot90(masked), alpha=1, cmap="Greys")

    # Add colorbar
    norm = Normalize(vmin=-100, vmax=100)
    sm = ScalarMappable(norm=norm, cmap=cmap)
    sm.set_array([])
    # fig.colorbar(sm, ax=ax)

    plt.gca().axis("off")
    clb = plt.colorbar(sm, ax=ax)
    clb.ax.set_title("B0 (Hz)")

    plt.savefig("subject-mosaic-brain_shimmed_axial_fixedslice-brainmasked_slicewise.png", dpi=1200)


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
