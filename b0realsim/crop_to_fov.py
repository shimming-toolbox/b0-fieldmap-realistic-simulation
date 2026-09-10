#!/usr/bin/env python3
"""Crop a canvas-sized fieldmap back to the acquired FOV grid.

compute_fieldmap returns a volume the same shape as its input. After the
body-extension stage (step 1b) that input is the whole canvas - roughly 13x the
acquired FOV, about 1.2 GB per subject once written - while everything
downstream expects the acquired 1 mm grid: the shimming prep scripts crop the
fieldmap against a mask built from the acquired labels, the published
derivatives sit on that grid, and any comparison against r0 has to.

The offset and shape come from the JSON the builder writes beside its label
volume, so the crop cannot drift from the geometry that was actually simulated.

    python crop_to_fov.py \\
        --fieldmap sub-X_T1w_fmap_b0-sim_canvas.nii.gz \\
        --meta     sub-X_T1w_fullbody_label-all.json \\
        --out      sub-X_T1w_fmap_b0-sim.nii.gz
"""
import argparse
import json
import sys
from pathlib import Path

import nibabel as nib
import numpy as np


def crop_to_fov(fieldmap_path, meta_path, out_path, keep_canvas=True):
    meta = json.loads(Path(meta_path).read_text())
    try:
        offset = [int(v) for v in meta["AcquiredFOVOffset"]]
        shape = [int(v) for v in meta["AcquiredFOVShape"]]
    except KeyError as exc:
        raise SystemExit(f"{meta_path} has no {exc.args[0]}; is it the builder's JSON?")

    img = nib.load(fieldmap_path)
    canvas_shape = img.shape

    for axis, (o, n, c) in enumerate(zip(offset, shape, canvas_shape)):
        if o < 0 or o + n > c:
            raise SystemExit(
                f"acquired FOV does not fit in the canvas on axis {axis}: "
                f"offset {o} + shape {n} = {o + n} > canvas {c}. "
                f"The fieldmap and the metadata describe different volumes.")

    data = np.asanyarray(img.dataobj)[
        offset[0]:offset[0] + shape[0],
        offset[1]:offset[1] + shape[1],
        offset[2]:offset[2] + shape[2]]

    # Undo the origin shift the builder applied when it placed the FOV in the
    # canvas, so the result lands back on the acquired volume's affine exactly.
    affine = img.affine.copy()
    for axis, o in enumerate(offset):
        affine[:3, 3] += img.affine[:3, axis] * o

    out_path = Path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    nib.save(nib.Nifti1Image(np.ascontiguousarray(data), affine), out_path)

    print(f"cropped {canvas_shape} -> {tuple(data.shape)} at offset {tuple(offset)}")
    print(f"saved {out_path}")

    if not keep_canvas:
        Path(fieldmap_path).unlink()
        print(f"removed canvas fieldmap {fieldmap_path}")


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--fieldmap", required=True, help="canvas-sized fieldmap to crop")
    p.add_argument("--meta", required=True,
                   help="the builder's *_label-all.json, for AcquiredFOVOffset/Shape")
    p.add_argument("--out", required=True, help="output path, on the acquired grid")
    p.add_argument("--discard-canvas", action="store_true",
                   help="delete the canvas fieldmap after cropping. 60 subjects of "
                        "canvas fieldmaps is ~72 GB against ~6.6 GB cropped, so the "
                        "run driver sets this for all but the QC subset.")
    a = p.parse_args()
    crop_to_fov(a.fieldmap, a.meta, a.out, keep_canvas=not a.discard_canvas)
