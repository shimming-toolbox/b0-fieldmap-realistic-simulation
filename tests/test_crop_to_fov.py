"""Stage 3b: crop the canvas fieldmap back to the acquired FOV grid.

compute_fieldmap returns a volume the same shape as its input, which after the
body-extension stage is the whole canvas (~13x the acquired FOV, 1.2 GB per
subject). Everything downstream - the shimming prep scripts, the published
derivatives, any comparison with r0 - expects the acquired 1 mm grid.
"""
import json
import subprocess
import sys
from pathlib import Path

import nibabel as nib
import numpy as np
import pytest

REPO = Path(__file__).resolve().parent.parent
CROP = REPO / "b0realsim" / "crop_to_fov.py"


@pytest.fixture
def canvas_case(tmp_path):
    """A canvas volume with a known FOV block placed at a known offset."""
    fov_shape, offset = (7, 9, 11), (5, 3, 13)
    canvas_shape = tuple(o + n + 4 for o, n in zip(offset, fov_shape))

    rng = np.random.default_rng(0)
    canvas = rng.standard_normal(canvas_shape).astype(np.float32)

    # Canvas affine as the builder writes it: origin shifted back by the offset.
    fov_affine = np.diag([1.0, 1.0, 1.0, 1.0])
    fov_affine[:3, 3] = [10.0, -20.0, 30.0]
    canvas_affine = fov_affine.copy()
    for axis, o in enumerate(offset):
        canvas_affine[:3, 3] -= fov_affine[:3, axis] * o

    nib.save(nib.Nifti1Image(canvas, canvas_affine), tmp_path / "canvas.nii.gz")
    (tmp_path / "meta.json").write_text(json.dumps({
        "AcquiredFOVOffset": list(offset), "AcquiredFOVShape": list(fov_shape)}))

    return dict(tmp_path=tmp_path, canvas=canvas, offset=offset,
                fov_shape=fov_shape, fov_affine=fov_affine)


def run_crop(case, extra=()):
    out = case["tmp_path"] / "cropped.nii.gz"
    r = subprocess.run([sys.executable, str(CROP),
                        "--fieldmap", str(case["tmp_path"] / "canvas.nii.gz"),
                        "--meta", str(case["tmp_path"] / "meta.json"),
                        "--out", str(out), *extra],
                       capture_output=True, text=True)
    assert r.returncode == 0, f"crop failed:\n{r.stdout}\n{r.stderr}"
    return out


def test_crops_to_the_acquired_shape(canvas_case):
    out = run_crop(canvas_case)
    assert nib.load(out).shape == canvas_case["fov_shape"]


def test_voxels_match_the_canvas_block_exactly(canvas_case):
    out = run_crop(canvas_case)
    ox, oy, oz = canvas_case["offset"]
    nx, ny, nz = canvas_case["fov_shape"]
    expected = canvas_case["canvas"][ox:ox + nx, oy:oy + ny, oz:oz + nz]
    assert np.array_equal(np.asanyarray(nib.load(out).dataobj), expected)


def test_restores_the_original_acquired_affine(canvas_case):
    """The crop must undo the builder's origin shift, or every downstream tool
    places the fieldmap in the wrong physical location."""
    out = run_crop(canvas_case)
    assert np.allclose(nib.load(out).affine, canvas_case["fov_affine"]), \
        "cropped affine does not match the acquired FOV affine"


def test_refuses_when_the_fov_does_not_fit(canvas_case):
    """A mismatched meta file must fail loudly, not silently clip."""
    (canvas_case["tmp_path"] / "meta.json").write_text(json.dumps({
        "AcquiredFOVOffset": [5, 3, 13], "AcquiredFOVShape": [999, 9, 11]}))
    out = canvas_case["tmp_path"] / "cropped.nii.gz"
    r = subprocess.run([sys.executable, str(CROP),
                        "--fieldmap", str(canvas_case["tmp_path"] / "canvas.nii.gz"),
                        "--meta", str(canvas_case["tmp_path"] / "meta.json"),
                        "--out", str(out)], capture_output=True, text=True)
    assert r.returncode != 0
    assert "does not fit" in (r.stdout + r.stderr).lower()
