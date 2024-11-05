import numpy as np
import nibabel as nib
from pathlib import Path
import argparse
import os

def main(bids_dir):
    bids_dir = Path(bids_dir)

    # Find the names of the folders in the BIDS directory starting with "sub-" and store them in a list (not full path)

    subjects = [x.parts[-1] for x in bids_dir.iterdir() if x.is_dir() and x.name.startswith("sub-")]

    # Remove sub-unfErssm001 and sub-unfErssm021 from the list of subjects 
    subjects = [x for x in subjects if x != "sub-unfErssm001" and x != "sub-unfErssm021"]

    # initiate a list of numpy arrays to store the data without knowing prior shape
    fulldata = []
    fullmask = []

    for subject in subjects:
        print(subject)
        label = nib.load(bids_dir / 'derivatives' / 'labels' / subject / 'anat' / (subject+'_T1w_label-all.nii.gz'))
        data = label.get_fdata()
        data[data!=4]=0
        data = np.ndarray.sum(data,2)
        data = np.ndarray.sum(data, 1)
        centerline = np.argmax(data)
        print(centerline)
        del data

        label = nib.load(bids_dir / 'derivatives' / 'labels' / subject / 'anat' / (subject+'_T1w_label-all.nii.gz'))
        mask = label.get_fdata()
        mask[mask==2]=0
        mask[mask==3]=0
        mask[mask==4]=0
        mask[mask==5]=0
        mask[mask==6]=0
        mask[mask==91]=0
        mask[mask==92]=0
        mask[mask>0]=1
        mask = np.ndarray.astype(mask, bool)

        b0map = nib.load(bids_dir / 'derivatives' / subject / 'fmap' / (subject+'_T1w_fmap_b0-sim.nii.gz'))

        b0map = b0map.get_fdata()

        # Siemens operating MRI frequency is ~123.2 MHz
        b0map = b0map*123.2

        mean_b0 = np.ma.masked_array(b0map,np.logical_not(mask)).mean()    

        print(f'{subject}: {b0map.shape}')

        #reset
        label = nib.load(bids_dir / 'derivatives' / 'labels' / subject / 'anat' / (subject+'_T1w_label-all.nii.gz'))

        mask = label.get_fdata()

        mask[mask>0]=1
        mask = np.ndarray.astype(mask, int)

        fulldata.append(np.squeeze(b0map[centerline,:,:])-mean_b0)
        fullmask.append(np.squeeze(mask[centerline,:,:]))

        del b0map, mask


    # Create a 6x12 concatenation of the images in fulldata. The dimensions sizes are heterogenous, so we need to pad the smaller ones with zeros

    # Find the maximum size in the first dimension
    max_size1 = max([x.shape[0] for x in fulldata])
    max_size2 = 600

    # Create a new array with the maximum size in the first dimension
    concatenated  = np.ones((max_size1*12, max_size2*5))*(-500)
    concatenated_mask  = np.zeros((max_size1*12, max_size2*5))*(500)

    print(concatenated.shape)
    # Fill the new array with the data
    for i, data in enumerate(fulldata):
        print(i)
        print(data[:,0:max_size2])
        print('xrange')
        print(max_size1*(i%12))
        print(data.shape[0]+max_size1*(i%12))
        print('yrange')
        print(max_size2*(int(i/12)))
        print(data.shape[1]+max_size2*(int(i/12)))

        concatenated[max_size1*(i%12):(data.shape[0]+max_size1*(i%12)), max_size2*(int(i/12)):max_size2*(int(i/12)+1)] = data[:,(data.shape[1]-max_size2-1):-1]
        mask = data[:,(data.shape[1]-max_size2-1):-1]
        mask[mask!=0]=1
        concatenated_mask[max_size1*(i%12):(data.shape[0]+max_size1*(i%12)), max_size2*(int(i/12)):max_size2*(int(i/12)+1)] = fullmask[i][:,(data.shape[1]-max_size2-1):-1]

    # Save the concatenated data as a png and blue-white-red colormap, centered at zero
    import matplotlib.pyplot as plt
    from matplotlib.colors import Normalize
    from matplotlib.cm import ScalarMappable

    # Create a figure and axes
    fig, ax = plt.subplots()
    cmap = plt.get_cmap('bwr')

    # Display the image
    im = ax.imshow(np.rot90(concatenated), cmap=cmap, vmin=-3*123.2, vmax=3*123.2)

    # Disable ticks and labels on both axes
    ax.tick_params(
        axis='both',       # changes apply to both axes
        which='both',      # both major and minor ticks are affected
        bottom=False,      # ticks along the bottom edge are off
        top=False,         # ticks along the top edge are off
        left=False,        # ticks along the left edge are off
        right=False,       # ticks along the right edge are off
        labelbottom=False, # labels along the bottom edge are off
        labelleft=False)   # labels along the left edge are off

    # Hide the axes
    ax.xaxis.set_visible(False)
    ax.yaxis.set_visible(False)

    masked = np.ma.masked_where(concatenated_mask == 1, concatenated_mask)
    plt.imshow(np.rot90(masked), alpha=1,cmap = 'Greys')

    # Add colorbar
    norm = Normalize(vmin=-3*123.2, vmax=3*123.2)
    sm = ScalarMappable(norm=norm, cmap=cmap)
    sm.set_array([])
    #fig.colorbar(sm, ax=ax)

    plt.gca().axis('off')
    clb = plt.colorbar(sm, ax=ax)
    clb.ax.set_title('B0 (Hz)')

    plt.savefig('subject-mosaic.png', dpi=1200)

if __name__ == "__main__":
    current_directory = os.path.dirname(os.path.abspath(__file__))

    # Create an argument parser
    parser = argparse.ArgumentParser(description="Process subject directory path and other arguments.")
    
    # Add the -s argument to the parser
    parser.add_argument("-b", "--bids_dir", required=True, help="Path to the BIDS dataset directory.")

    # Parse the arguments
    args = parser.parse_args()
    main(args.bids_dir)
