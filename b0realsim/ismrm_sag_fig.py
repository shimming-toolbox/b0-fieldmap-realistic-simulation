import numpy as np
import nibabel as nib
from pathlib import Path

subjects = [
    'sub-amuAL',
    'sub-amuALT',
    'sub-amuAM',
    'sub-amuAP',
    'sub-amuCR',
    'sub-amuED',
    'sub-amuFL',
    'sub-amuFR',
    'sub-amuGB',
    'sub-amuHB',
    'sub-amuJD',
    'sub-amuJW',
    'sub-amuLJ',
    'sub-amuMD',
    'sub-amuMLL',
    'sub-amuMT',
    'sub-amuPA',
    'sub-amuTM',
    'sub-amuTR',
    'sub-amuTT',
    'sub-amuVC',
    'sub-amuVG',
    'sub-amuVP',
    'sub-unfErssm002',
    'sub-unfErssm003',
    'sub-unfErssm004',
    'sub-unfErssm005',
    'sub-unfErssm006',
    'sub-unfErssm007',
    'sub-unfErssm008',
    'sub-unfErssm009',
    'sub-unfErssm010',
    'sub-unfErssm011',
    'sub-unfErssm012',
    'sub-unfErssm013',
    'sub-unfErssm014',
    'sub-unfErssm015',
    'sub-unfErssm016',
    'sub-unfErssm017',
    'sub-unfErssm018',
    'sub-unfErssm019',
    'sub-unfErssm020',
    'sub-unfErssm022',
    'sub-unfErssm023',
    'sub-unfErssm024',
    'sub-unfErssm025',
    'sub-unfErssm026',
    'sub-unfErssm027',
    'sub-unfErssm028',
    'sub-unfErssm029',
    'sub-unfErssm030',
    'sub-unfErssm031',
    'sub-unfPain001',
    'sub-unfPain002',
    'sub-unfPain003',
    'sub-unfPain004',
    'sub-unfPain005',
    'sub-unfPain006',
    'sub-unfSCT001',
    'sub-unfSCT002'
]

bids_dir = Path('/Users/mathieuboudreau/neuropoly/projects/shimming-toolbox/data/data.neuro.polymtl.ca/whole-spine/')

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

    mask[mask>0]=1
    mask = np.ndarray.astype(mask, int)

    b0map = nib.load(bids_dir / 'derivatives' / subject / 'fmap' / (subject+'_T1w_fmap_b0-sim.nii.gz'))

    b0map = b0map.get_fdata()

    b0map = b0map*127.74
    mean_b0 = -2.5*127.74

    print(f'{subject}: {b0map.shape}')

    fulldata.append(np.squeeze(b0map[centerline,:,:])-mean_b0)
    fullmask.append(np.squeeze(mask[centerline,:,:]))

    del b0map, mask


# Create a 6x12 concatenation of the images in fulldata. The dimensions sizes are heterogenous, so we need to pad the smaller ones with zeros

# Find the maximum size in the first dimension
max_size1 = max([x.shape[0] for x in fulldata])
max_size2 = 600

# Create a new array with the maximum size in the first dimension
concatenated  = np.ones((max_size1*12, max_size2*5))*(500)
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

fig = plt.figure(frameon=False)
cmap = plt.get_cmap('bwr')
plt.imshow(np.rot90(concatenated), cmap=cmap, vmin=-2.5*127.74, vmax=2.5*127.74)
plt.tick_params(
    axis='x',          # changes apply to the x-axis
    which='both',      # both major and minor ticks are affected
    bottom=False,      # ticks along the bottom edge are off
    top=False,         # ticks along the top edge are off
    labelbottom=False) # labels along the bottom edge are off

plt.tick_params(
    axis='y',          # changes apply to the x-axis
    which='both',      # both major and minor ticks are affected
    bottom=False,      # ticks along the bottom edge are off
    top=False,         # ticks along the top edge are off
    labelbottom=False) # labels along the bottom edge are off

plt.gca().xaxis.set_visible(False)
plt.gca().yaxis.set_visible(False)

breakpoint()

masked = np.ma.masked_where(concatenated_mask == 1, concatenated_mask)

plt.imshow(np.rot90(masked), alpha=1,cmap = 'grey')

fig.set_facecolor('k')

plt.savefig('b0_offsets.png', dpi=1200)

