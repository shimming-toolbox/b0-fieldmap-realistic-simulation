# B0 fieldmap realistic simulation

Generation of B0 fieldmap based on anatomical MRIs of 60 adult subjects. The fieldmaps are generated from the segmented tissues and assignment of susceptibility values. 

**Pipeline**

<img width="1148" alt="Pipeline" src="https://github.com/user-attachments/assets/8bf04642-0ab2-460c-8893-5d2d94490a13">

<br/><br/>

**3D Render of segmentations**

<img width="600" alt="3D Render of segmentations" src="https://github.com/user-attachments/assets/5062eb6c-e2a3-42ad-936e-26f402caa1b8">

<br/><br/>

**Sagittal mosaic of simulated B0 maps**

<img width="800" alt="3D Render of segmentations" src="https://github.com/user-attachments/assets/6bd82576-3a10-40bf-b965-64a10b8f53d3">
<br/><br/>

# Dataset

Link to OpenNeuro BIDS dataset to be provided soon.

# Installation

## Python depedencies
In a new virtual environment (recommended), install this repository:

```shell
git clone https://github.com/shimming-toolbox/b0-fieldmap-realistic-simulation.git
cd b0-fieldmap-realistic-simulation
pip install -e requirements.txt
```

Install the susceptibility-to-fieldmap project,

```shell
git clone https://github.com/shimming-toolbox/susceptibility-to-fieldmap-fft
cd susceptibility-to-fieldmap-fft
git checkout d9f785b082fb145d547ff03ae53f23f1564ccc38
pip install -e .
```
## Slicer3D

> **_NOTE:_** This pipeline has only been tested using Slicer3D version 5.6.2, and may need to be updated for compatibility with more recent versions. Please open an issue if you encounter a problem.

Install via their website, https://www.slicer.org

Open the application, then navigate to the Python terminal (see Python "snake" logo in the top toolbar) and run:

```python
import slicer
slicer.util.pip_install('click')
```

Update [this script](https://github.com/shimming-toolbox/b0-fieldmap-realistic-simulation/blob/main/b0realsim/slicer_scripts/merge_pipeline.sh) with your Slicer path if you are not running on a Mac, or if you installed Slicer in a different location

# Usage

## Main pipeline

Note: for all *.sh script files, you'll need to provide execution permissions,

`chmod +xxx $SCRIPT`

where $SCRIPT is the *.sh filename for that script.

For convenience, we recommend you set the variable `BIDS_DIR` in your shell to the datasets BIDS directory,

`BIDS_DIR = /path/to/bids/dir`

This way, you can copy-paste the commands below directly.

### Create shell scripts customized for your BIDS directory

**Step 1**: Smooth & merge
From within this directory, first generate the script for smoothing using 3D Slicer & merging of the labels:

`./b0realsim/step_1_generate_smoothing.sh -b $BIDS_DIR`

Output: **run_1_smooth.sh**

**Step 2**: Labels to chi
Then, generate the script that will, for each subject, map the labels to their chi values.

`./b0realsim/step_2_generate_chi.sh -b $BIDS_DIR`]

Output: **run_2_compute_chimaps.sh**

**Step 3**: Chi to B0 field map
Lastly, generate the script that will, for each subject, simulate the B0 field map using the chi map generated in the previous step.

`./b0realsim/step_3_generate_b0.sh -b $BIDS_DIR`

Output: **run_3_compute_b0maps.sh**

### Run pipeline scripts

Now, provide execute permission (`chmod +xxx $SCRIPT`) each pipeline scripts you just generated and then run them in order

`./run_1_smooth.sh` - runtime: ~2 hours

`./run_2_compute_chimaps.sh` - runtime: ~1 minute

`./run_3_compute_b0maps.sh` - runtime: ~30 minutes

## Outputs

**Smoothed & merged labels**
$BIDS_DIR/derivatives/labels/$SUBJECT/anat/

**Chi maps**
$BIDS_DIR/derivatives/$SUBJECT/anat/

**B0 maps**
$BIDS_DIR/derivatives/$SUBJECT/fmap/

## Plot saggital mosaic of B0 maps

`python b0realsim/visualization/plot_mosaic.py -b $BIDS_DIR` - runtime ~3 minutes

Output: **subject-mosaic.png**

## Fetch additional information
To compute the age/weight/height statistics for the subjects,

`python b0realsim/stats/subjects.py -b $BIDS_DIR`

