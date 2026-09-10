"""Tests for the body-extension stage (step 1b).

The builder completes an approximate whole body around each subject's acquired
labels so the simulated object is finite and enclosed in air, instead of a
truncated torso that the DFT fuses into an infinite lattice.

Per design decision D8 it emits LABELS ONLY - no chi map, no blend band - so the
published label volume fully determines the chi map through CHI_LUT, with no
hidden interpolation.
"""
import json
import subprocess
import sys
from pathlib import Path

import nibabel as nib
import numpy as np
import pytest

from b0realsim.label_to_chi import CHI_LUT, ADDED_LABEL

REPO = Path(__file__).resolve().parent.parent
BUILDER = REPO / "b0realsim" / "build_fullbody.py"
DATA = Path("/Users/mathieuboudreau/neuropoly/projects/b0sim_r1/data/whole-spine")
LABELS = DATA / "derivatives/labels/sub-amuPA/anat/sub-amuPA_T1w_label-all.nii.gz"
# Built on 2026-09-08 by the pre-vendoring script; the geometry must not move.
REFERENCE = Path("/Users/mathieuboudreau/neuropoly/projects/b0sim_r1/working/body_extension/"
                 "tested_subjects_labels/sub-amuPA_fullbody_label-all.nii.gz")

needs_data = pytest.mark.skipif(not LABELS.exists(), reason="dataset not present")


@pytest.fixture(scope="module")
def built(tmp_path_factory):
    """Run the builder once for the whole module - it takes ~35 s."""
    if not LABELS.exists():
        pytest.skip("dataset not present")
    out = tmp_path_factory.mktemp("fullbody") / "sub-amuPA_T1w_fullbody"
    result = subprocess.run(
        [sys.executable, str(BUILDER), "--labels", str(LABELS), "--out-prefix", str(out)],
        capture_output=True, text=True)
    assert result.returncode == 0, f"builder failed:\n{result.stdout}\n{result.stderr}"
    return out


@needs_data
def test_emits_labels_and_no_chi_map(built):
    """D8: the builder no longer writes chi. label_to_chi owns that mapping."""
    assert (built.parent / f"{built.name}_label-all.nii.gz").exists()
    assert (built.parent / f"{built.name}_acquired.nii.gz").exists()
    assert (built.parent / f"{built.name}_label-all.json").exists()
    assert not (built.parent / f"{built.name}_chi.nii.gz").exists(), \
        "builder must not write a chi map any more (D8)"


@needs_data
def test_acquired_labels_are_bit_identical(built):
    """The acquired anatomy is the published data; the builder may draft through
    it but must restore every voxel verbatim."""
    meta = json.loads((built.parent / f"{built.name}_label-all.json").read_text())
    ox, oy, oz = meta["AcquiredFOVOffset"]
    nx, ny, nz = meta["AcquiredFOVShape"]

    canvas = np.asanyarray(nib.load(built.parent / f"{built.name}_label-all.nii.gz").dataobj)
    original = np.asanyarray(nib.load(LABELS).dataobj).astype(np.uint8)

    assert np.array_equal(canvas[ox:ox + nx, oy:oy + ny, oz:oz + nz], original), \
        "acquired labels were modified"


@needs_data
def test_added_material_uses_the_shared_added_label(built):
    """The label value must be the one label_to_chi maps to water, or the two
    stages disagree about what the mannequin is made of."""
    canvas = np.asanyarray(nib.load(built.parent / f"{built.name}_label-all.nii.gz").dataobj)
    assert (canvas == ADDED_LABEL).sum() > 0
    assert ADDED_LABEL in CHI_LUT


@needs_data
def test_every_label_written_is_in_chi_lut(built):
    """If the builder emits a label CHI_LUT does not know, stage 2 dies."""
    canvas = np.asanyarray(nib.load(built.parent / f"{built.name}_label-all.nii.gz").dataobj)
    written = set(np.unique(canvas).astype(int).tolist())
    assert written <= set(CHI_LUT), f"labels not in CHI_LUT: {sorted(written - set(CHI_LUT))}"


@needs_data
def test_body_is_enclosed_in_air_on_every_canvas_face(built):
    """The whole point of the stage: air padding is only legitimate if no tissue
    reaches a canvas face."""
    canvas = np.asanyarray(nib.load(built.parent / f"{built.name}_label-all.nii.gz").dataobj)
    faces = {"x-": canvas[0], "x+": canvas[-1], "y-": canvas[:, 0],
             "y+": canvas[:, -1], "z-": canvas[:, :, 0], "z+": canvas[:, :, -1]}
    touching = {name: int((f > 0).sum()) for name, f in faces.items() if (f > 0).any()}
    assert not touching, f"tissue touches canvas faces: {touching}"


@needs_data
def test_geometry_matches_the_pre_vendoring_reference(built):
    """Dropping chi and the blend band must not move a single voxel of geometry.
    The blend only ever touched chi values, never labels, so this is exact."""
    if not REFERENCE.exists():
        pytest.skip("2026-09-08 reference volume not present")
    new = np.asanyarray(nib.load(built.parent / f"{built.name}_label-all.nii.gz").dataobj)
    ref = np.asanyarray(nib.load(REFERENCE).dataobj)
    assert new.shape == ref.shape, f"canvas shape moved: {ref.shape} -> {new.shape}"
    differing = int((new != ref).sum())
    assert differing == 0, f"{differing} voxels differ from the 2026-09-08 reference"
