#!/usr/bin/env python3
"""Add a mannequin body around a torso-to-head cropped label volume, for any subject.

Subject-agnostic successor to build_fullbody_spline.py, which hardcodes every landmark as a
sub-amuPA voxel index (vertex 662, shoulder 368, sole -1088, calibration slice 382, ratio 1.29).
Each of those is really "so many mm below the vertex at a 1750 mm stature", so they are stored that
way here and re-anchored to whatever the input subject measures:

  MEASURED per subject   vertex z, inferior-most acquired slice, per-slice A-P depth and centre,
                         the lateral-truncation range (which also gives the acromion), the tissue
                         profile on the truncated lateral faces, and the subject's own width/depth
                         ratio at the first laterally untruncated slice.
  ASSUMED (population)   stature (default 1750 mm) and the landmark fractions / limb radii below,
                         scaled by stature/1750.

How the acquired data is protected: the mannequin is DRAFTED without restriction, including through
the acquired FOV, so primitives are never clipped and the smoothing sees a complete shape; then
every voxel inside the acquired FOV is restored from the input label volume. Acquired anatomy
therefore comes out bit-identical, while the drafted body outside it is anatomically continuous.

Closing the truncated face: where the body runs off the lateral edge of the FOV, that cut face is a
flat wall of tissue. The trunk primitives (an ellipse fitted to the measured depth) only cover a
sliver of it, which is what leaves an air-tissue interface along the sides of the upper torso. So
every truncated face profile is additionally extruded outward by --lateral-extrusion-mm as a
CHAMFER - each step outward erodes the profile, so thick sections (chest) continue nearly straight
while thin ones (the top of the shoulder) taper away - covering the cut face by construction. The
count of still-exposed face voxels is checked at the end.

Continuity of slope: the smoothing is applied to the UNION of the draft and the acquired anatomy,
not to the draft alone. Smoothing the draft by itself rounds it off against the FOV wall and leaves
a step where it meets the real skin surface; smoothing the union makes the added surface leave the
acquired one tangentially. The acquired FOV is restored afterwards either way.
"""
import argparse, csv, json, os, re, sys
from pathlib import Path
import numpy as np, nibabel as nib
from scipy import ndimage
from scipy.interpolate import PchipInterpolator

# Labels and their susceptibilities come from label_to_chi, which owns CHI_LUT.
# This stage emits labels only (design decision D8) - it never writes chi - but it
# still needs to know which label values are legal and which one marks added
# material, and duplicating that here is how the two stages would drift apart.
try:
    from b0realsim.label_to_chi import CHI_LUT, LABEL_NAMES, ADDED_LABEL
except ImportError:                      # run as a script by path
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
    from b0realsim.label_to_chi import CHI_LUT, LABEL_NAMES, ADDED_LABEL

# Label values the ACQUIRED volume may contain (everything except the value this
# stage adds).
ACQUIRED_LABELS = set(CHI_LUT) - {ADDED_LABEL}
REF_STATURE = 1750.0

# mm BELOW THE VERTEX at REF_STATURE, read off the sub-amuPA model (vertex 662, sole -1088)
D_CHEST, D_SHOULDER, D_ARM_MAX, D_ELBOW = 412, 294, 332, 600
D_WRIST, D_FOREARM, D_TIP = 860, 962, 1000
D_HIP, D_PELVIS_FLOOR, D_KNEE, D_SHIN, D_ANKLE, D_FOOT, D_SOLE = 812, 892, 1270, 1492, 1680, 1722, 1750
RATIO_CHEST = 1.45              # anthropometric chest width/depth, reached at D_CHEST
BIACROMIAL = 0.23               # shoulder breadth as a fraction of stature, caps the trunk width
TRUNK_MID_FRAC = 70.0 / 150.0   # where the a_nav*1.03 control point sat between FOV bottom and hip


def pchip(pts):
    """Monotone-in-x spline through (z, value) control points, clamped outside the range."""
    z = np.array([p[0] for p in pts], float); v = np.array([p[1] for p in pts], float)
    o = np.argsort(z); z, v = z[o], v[o]
    f = PchipInterpolator(z, v, extrapolate=False)
    def g(zz):
        out = f(zz)
        return float(np.where(np.isnan(out), v[0] if zz < z[0] else v[-1], out))
    return g


def main():
    p = argparse.ArgumentParser(description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--labels", required=True, help="subject's *_label-all.nii.gz")
    p.add_argument("--out-prefix", required=True)
    p.add_argument("--stature", default="auto",
                   help="stature in mm, or 'auto' (default): look the subject up in the dataset's "
                        f"participants.tsv and use its recorded height, falling back to "
                        f"{REF_STATURE:.0f} mm when there is none")
    p.add_argument("--participants", help="path to participants.tsv; found automatically by "
                                          "walking up from --labels if not given")
    p.add_argument("--vertex", choices=["tissue", "fovtop"], default="tissue",
                   help="anchor landmarks to the top labelled voxel (default, anatomical) or to "
                        "the top of the FOV (what the sub-amuPA model did)")
    p.add_argument("--shoulder", choices=["measured", "assumed"], default="measured",
                   help="measured: the arms taper out at the acromion, taken as the first slice "
                        "where the body no longer runs off the lateral FOV edge. assumed: use the "
                        "population landmark 294 mm below the vertex.")
    p.add_argument("--lateral-extrusion-mm", type=float, default=20.0,
                   help="how far a cut-off cross-section is carried outward past the FOV face "
                        "before it rounds off, so the added surface continues the real one instead "
                        "of stepping down onto a primitive. 0 disables.")
    p.add_argument("--margin-lat", type=float, default=45.0, help="air margin beyond the body, mm")
    p.add_argument("--margin-ap", type=float, default=40.0)
    p.add_argument("--margin-z", type=float, default=20.0)
    p.add_argument("--smooth-sigma", type=float, default=3.0)
    p.add_argument("--qc", action="store_true", help="also write label-panel and surface QC pngs")
    a = p.parse_args()

    # ---------------- input ----------------
    lab_img = nib.load(a.labels)
    lab = np.asanyarray(lab_img.dataobj)
    vox = np.array(nib.affines.voxel_sizes(lab_img.affine), float)
    axc = nib.aff2axcodes(lab_img.affine)
    if axc[2] not in "SI" or axc[1] not in "AP":
        raise SystemExit(f"expected axes (L/R, A/P, S/I); got {axc}")
    if axc[2] == "I":
        raise SystemExit("z runs inferior-ward; reorient before running")
    if not np.allclose(vox, vox[0], atol=1e-3):
        raise SystemExit(f"anisotropic voxels {vox}: this builder works in voxel=mm units")
    mm = float(vox[0])                       # mm per voxel, all three axes

    # ---- stature: measured for this subject if the dataset records it ----
    subject = re.search(r"(sub-[A-Za-z0-9]+)", os.path.basename(a.labels))
    stature_src = "given on the command line"
    if a.stature == "auto":
        stature, stature_src = REF_STATURE, f"default, no participants.tsv found"
        tsv = a.participants
        if not tsv:
            d = os.path.dirname(os.path.abspath(a.labels))
            for _ in range(6):
                cand = os.path.join(d, "participants.tsv")
                if os.path.exists(cand): tsv = cand; break
                d = os.path.dirname(d)
        if tsv and subject:
            with open(tsv) as fh:
                for row in csv.DictReader(fh, delimiter="\t"):
                    if row.get("participant_id") != subject.group(1): continue
                    col = next((c for c in row if c.lower().startswith("height")), None)
                    val = (row.get(col) or "").strip() if col else ""
                    if val and val.lower() not in ("n/a", "na", "-"):
                        stature = float(val) * (10.0 if "cm" in (col or "").lower() else 1.0)
                        stature_src = f"{os.path.relpath(tsv)} ({col} = {val})"
                    else:
                        stature_src = f"not recorded in {os.path.relpath(tsv)}; default"
                    break
                else:
                    stature_src = f"{subject.group(1)} not in {os.path.relpath(tsv)}; default"
        a.stature = stature
    else:
        a.stature = float(a.stature)
    print(f"stature {a.stature:.0f} mm — {stature_src}")
    if "default" in stature_src:
        print(f"WARNING: stature is assumed. Every limb landmark scales with it, so a subject far "
              f"from {REF_STATURE:.0f} mm will have its legs and arms placed proportionally wrong.")
    k = a.stature / REF_STATURE              # scales the population landmarks
    S = k / mm                               # population mm -> voxels
    unknown = set(np.unique(lab).astype(int).tolist()) - ACQUIRED_LABELS
    if unknown:
        raise SystemExit(f"labels not in the published LUT: {sorted(unknown)}")
    if lab.min() < 0 or lab.max() > 100:
        raise SystemExit("label range does not fit alongside ADDED_LABEL in uint8")

    nxo, nyo, nzo = lab.shape
    body = lab != 0

    # ---------------- measurements ----------------
    zs = np.nonzero(body.any(axis=(0, 1)))[0]
    z_vertex = int(zs.max()) if a.vertex == "tissue" else nzo - 1
    z_bot = int(zs.min())
    lat = [z for z in range(nzo) if body[0, :, z].any() or body[-1, :, z].any()]
    ap = [z for z in range(nzo) if body[:, 0, z].any() or body[:, -1, z].any()]
    if ap:
        print(f"WARNING: {len(ap)} slices are truncated in A-P too; the depth measured there is a "
              f"lower bound and the trunk will come out too thin")
    if not lat:
        raise SystemExit("no laterally truncated slices: nothing to complete, and no slice to "
                         "calibrate the width/depth ratio against")
    z_top = int(max(lat)) + 1                        # first fully visible slice above truncation
    if z_top >= nzo:
        raise SystemExit("the body is laterally truncated all the way to the top of the FOV")
    # A narrow FOV can clip the head laterally as well, and then the top of the truncated range is
    # in the skull rather than at the shoulder. The acromion is never less than ~160 mm below the
    # vertex in an adult, so treat anything higher as contaminated and fall back to the population
    # landmark - and to the population chest ratio, since the calibration slice is then a head slice.
    acromion_ok = (z_vertex - z_top) * mm / k >= 0.55 * D_SHOULDER
    if not acromion_ok:
        print(f"WARNING: lateral truncation reaches z={z_top-1}, only "
              f"{(z_vertex-z_top)*mm/k:.0f} mm below the vertex - the head is being clipped "
              f"laterally too, so the acromion and the width/depth ratio cannot be measured. "
              f"Falling back to the population shoulder landmark and chest ratio.")

    xc_o = (nxo - 1) / 2.0
    depth, ycen, width, xext, trunc, side_trunc = {}, {}, {}, {}, {}, {}
    b_nav = y_nav_o = None
    for z in range(nzo):
        m = body[:, :, z]
        if not m.any(): continue
        ys = np.nonzero(m.any(axis=0))[0]; xs = np.nonzero(m.any(axis=1))[0]
        depth[z] = (ys.max() - ys.min() + 1) / 2.0
        ycen[z] = (ys.min() + ys.max()) / 2.0
        width[z] = (xs.max() - xs.min() + 1) / 2.0
        xext[z] = max(abs(xs.max() - xc_o), abs(xc_o - xs.min()))
        trunc[z] = bool(m[0].any() or m[-1].any())
        side_trunc[z] = (bool(m[0].any()), bool(m[-1].any()))
    # A-P profile of the tissue ON the truncated faces. The outboard extension has to continue THAT,
    # not the whole slice: at the top of the shoulder the slice also contains the neck and chin, so
    # an ellipse centred on the slice's full A-P extent sticks out tens of mm proud of the shoulder.
    yface_c, yface_h = {}, {}
    for z in lat:
        prof = body[0, :, z] | body[-1, :, z]
        ys = np.nonzero(prof)[0]
        yface_c[z] = (ys.min() + ys.max()) / 2.0
        yface_h[z] = (ys.max() - ys.min() + 1) / 2.0
    def lat_y(z):
        """(centre, half-depth) the outboard extension should be built around at slice z."""
        return (yface_c.get(z, ycen.get(z, y_nav_o)), yface_h.get(z, depth.get(z, b_nav)))

    b_nav, y_nav_o = depth[z_bot], ycen[z_bot]
    ratio_top = width[z_top] / depth[z_top] if acromion_ok else RATIO_CHEST
    print(f"vertex z={z_vertex} ({a.vertex})   acquired tissue z {z_bot}..{int(zs.max())}   "
          f"lateral truncation z {min(lat)}..{max(lat)}")
    if acromion_ok:
        print(f"ratio calibration slice z={z_top}: width/depth = {ratio_top:.3f}  "
              f"(next: {', '.join(f'{width[z]/depth[z]:.3f}' for z in range(z_top+1, min(z_top+4, nzo)) if z in width)})")
    else:
        print(f"width/depth ratio: {ratio_top:.3f} (population fallback, not measured)")

    # ---------------- landmarks, in this subject's voxel grid ----------------
    def L(d_mm): return z_vertex - d_mm * k / mm       # mm below vertex -> z index
    Z_CHEST, Z_ARMMAX, Z_ELB = L(D_CHEST), L(D_ARM_MAX), L(D_ELBOW)
    Z_WR, Z_FORE, Z_TIP = L(D_WRIST), L(D_FOREARM), L(D_TIP)
    Z_HIP, Z_PELV, Z_KNEE = L(D_HIP), L(D_PELVIS_FLOOR), L(D_KNEE)
    Z_SHIN, Z_ANKLE, Z_FOOT, Z_SOLE = L(D_SHIN), L(D_ANKLE), L(D_FOOT), L(D_SOLE)
    Z_SH = float(z_top) if (a.shoulder == "measured" and acromion_ok) else L(D_SHOULDER)
    if a.shoulder == "measured" and acromion_ok:
        print(f"acromion taken from the data: z={Z_SH:.0f} "
              f"({(z_vertex - Z_SH)*mm/k:.0f} mm below the vertex; population value {D_SHOULDER})")
    if Z_SH <= Z_ARMMAX:
        raise SystemExit("acromion is at or below the widest-arm level; check the input")
    if Z_HIP > z_bot - 30 / mm:
        print(f"WARNING: assumed hip ({Z_HIP:.0f}) is not clear of the FOV bottom ({z_bot}); "
              f"clamping. Check the stature assumption.")
        shift = Z_HIP - (z_bot - 30 / mm)
        Z_HIP, Z_PELV = Z_HIP - shift, Z_PELV - shift
    Z_SOLE_I, Z_HIP_I = int(np.floor(Z_SOLE)), int(round(Z_HIP))
    print(f"landmarks (z): chest {Z_CHEST:.0f} shoulder {Z_SH:.0f} elbow {Z_ELB:.0f} "
          f"wrist {Z_WR:.0f} tip {Z_TIP:.0f} | hip {Z_HIP:.0f} knee {Z_KNEE:.0f} "
          f"ankle {Z_ANKLE:.0f} sole {Z_SOLE:.0f}")

    z_cal = z_top if acromion_ok else int(Z_SH)      # where ratio_top applies from
    def torso_ratio(z):
        if z >= z_cal: return ratio_top
        if z <= Z_CHEST: return RATIO_CHEST
        t = (z_cal - z) / (z_cal - Z_CHEST)
        return ratio_top + t * (RATIO_CHEST - ratio_top)

    def torso_half(z):
        """Modelled trunk half-width. Never narrower than the body is seen to be: on a laterally
        truncated slice the anatomy demonstrably reaches the FOV edge, so a ratio-derived ellipse
        smaller than that would model the torso thinner than the data already show."""
        a_ratio = torso_ratio(z) * depth[z]
        if not trunc.get(z): return a_ratio
        return min(max(a_ratio, xext[z] + a.lateral_extrusion_mm / mm), 0.5 * BIACROMIAL * a.stature / mm)

    a_nav = torso_ratio(z_bot) * b_nav
    a_hip, b_hip = a_nav * 1.05, b_nav * 0.95
    hip_dx = 0.45 * a_hip
    trunk_mid = z_bot + TRUNK_MID_FRAC * (Z_HIP - z_bot)
    trunk_a = pchip([(Z_PELV, a_hip*0.99), (Z_HIP, a_hip), (trunk_mid, a_nav*1.03), (z_bot, a_nav)])
    trunk_b = pchip([(Z_PELV, b_hip*0.98), (Z_HIP, b_hip), (trunk_mid, b_nav*0.98), (z_bot, b_nav)])
    leg_rx = pchip([(Z_HIP, a_hip - hip_dx), (Z_FORE, 62*S), (Z_KNEE, 50*S), (Z_SHIN, 44*S),
                    (Z_ANKLE, 36*S), (Z_SOLE, 44*S)])
    leg_ry = pchip([(Z_HIP, b_hip), (Z_FORE, 66*S), (Z_KNEE, 55*S), (Z_SHIN, 48*S),
                    (Z_ANKLE, 40*S), (Z_SOLE, 125*S)])
    leg_dy = pchip([(Z_ANKLE, 0.0), (Z_FOOT, 55*S), (Z_SOLE, 95*S)])     # feet project anteriorly
    arm_r = pchip([(Z_TIP, 0.0), (Z_FORE, 22*S), (Z_WR, 30*S), (Z_ELB, 42*S),
                   (Z_ARMMAX, 52*S), (Z_SH, 0.0)])
    # The shoulder girdle is as deep in A-P as the chest but far wider than any ratio*depth ellipse:
    # at the acromion the slice is mostly neck, so its measured depth is small and the ratio model
    # collapses. Ramp the half-width from what is actually seen at the acromion out to the
    # biacromial half-breadth at the widest-arm level, keeping the MEASURED depth of each slice.
    sh_half = pchip([(Z_SH, xext.get(int(Z_SH), xext.get(max(xext), b_nav)) + 2.0),
                     (Z_ARMMAX, 0.5 * BIACROMIAL * a.stature / mm)])
    def shoulder_half(z):
        return sh_half(z) if Z_ARMMAX <= z <= Z_SH else 0.0

    # ---------------- canvas, sized from the geometry it has to hold ----------------
    z_arm = range(int(np.floor(Z_TIP)), int(np.ceil(Z_SH)) + 1)
    def trunk_half_at(z):
        return torso_half(z) if z in depth else (trunk_a(max(z, Z_PELV)) if z < z_bot else b_nav)
    half_x = max([torso_half(z) for z in depth] + [shoulder_half(z) for z in depth] +
                 [trunk_a(z) for z in range(Z_HIP_I, z_bot)] +
                 [abs(hip_dx) + leg_rx(z) for z in range(Z_SOLE_I, Z_HIP_I + 1)] +
                 [trunk_half_at(min(z, nzo-1)) + 2*arm_r(z) - 12*S for z in z_arm])
    y_lo = min([ycen[z] - depth[z] for z in depth] +
               [y_nav_o - trunk_b(z) for z in range(Z_HIP_I, z_bot)] +
               [y_nav_o + leg_dy(z) - leg_ry(z) for z in range(Z_SOLE_I, Z_HIP_I + 1)])
    y_hi = max([ycen[z] + depth[z] for z in depth] +
               [y_nav_o + trunk_b(z) for z in range(Z_HIP_I, z_bot)] +
               [y_nav_o + leg_dy(z) + leg_ry(z) for z in range(Z_SOLE_I, Z_HIP_I + 1)])
    ox = int(np.ceil(max(half_x - xc_o, half_x - (nxo - 1 - xc_o)) + a.margin_lat / mm))
    NX = nxo + 2 * ox
    oy = int(np.ceil(max(0.0, -y_lo) + a.margin_ap / mm))
    NY = int(np.ceil(oy + max(y_hi, nyo - 1) + 1 + a.margin_ap / mm))
    z_lo = Z_SOLE_I - int(round(a.margin_z / mm))
    z_hi_pad = int(round((a.margin_z + a.lateral_extrusion_mm) / mm)) if body[:, :, -1].any() else 0
    NZ = nzo - z_lo + z_hi_pad
    def zi(z): return z - z_lo
    oz = zi(0)
    acq_box = (slice(ox, ox+nxo), slice(oy, oy+nyo), slice(oz, oz+nzo))
    print(f"canvas {nxo}x{nyo}x{nzo} -> {NX}x{NY}x{NZ}   acquired FOV at ({ox}, {oy}, {oz})")

    # ---------------- draft, with no regard for the acquired FOV ----------------
    added = np.zeros((NX, NY, NZ), bool)
    gx, gy = np.ogrid[:NX, :NY]
    xc, y_nav = ox + xc_o, oy + y_nav_o

    def paint(mask, z):
        kk = zi(z)
        if 0 <= kk < NZ:
            added[:, :, kk] |= mask

    def ell(cx, cy, rx, ry):
        if rx <= 0.5 or ry <= 0.5: return np.zeros((NX, NY), bool)
        return (((gx - cx) / rx) ** 2 + ((gy - cy) / ry) ** 2) <= 1.0

    # trunk over the acquired range: complete the laterally truncated slices, plus the shoulder
    # girdle over the acromion-to-deltoid range
    for z in range(nzo):
        if not trunc.get(z): continue
        if z > Z_SH:
            # above the acromion the anatomy is head and neck, not trunk. A narrow FOV can clip the
            # head laterally, and completing THAT with a trunk ellipse lays a plank through the
            # skull; the slope-extrapolated face continuation below handles it properly instead.
            continue
        # ONLY on the side(s) actually cut off. The body is not always centred in the FOV - a head
        # can be clipped on one side and clear of the other - and a symmetric completion then lays
        # material outside an untruncated face, where the acquired data says air. Once the FOV is
        # restored that material is floating, disconnected from the body.
        yc, yh = lat_y(z)
        trL, trR = side_trunc[z]
        half = (gx <= xc) if not trR else ((gx >= xc) if not trL else np.ones((NX, 1), bool))
        paint(ell(xc, oy + yc, torso_half(z), max(yh, depth[z] * 0.5)) & half, z)
        if shoulder_half(z) > 0:
            paint(ell(xc, oy + yc, shoulder_half(z), max(yh, depth[z] * 0.5)) & half, z)
    # trunk below the acquired range
    for z in range(Z_HIP_I, z_bot):
        paint(ell(xc, y_nav, trunk_a(z), trunk_b(z)), z)
    # legs and feet, one continuous splined profile
    for z in range(Z_SOLE_I, Z_HIP_I + 1):
        rx, ry, dy = leg_rx(z), leg_ry(z), leg_dy(z)
        for s in (-1, 1):
            paint(ell(xc + s * hip_dx, y_nav + dy, rx, ry), z)
    # arms, tapering to zero at the acromion and at the fingertips
    for z in z_arm:
        r = arm_r(z)
        zc = int(np.clip(z, 0, nzo - 1))
        aa = trunk_half_at(zc) if z >= z_bot else trunk_a(max(z, Z_PELV))
        yy = oy + lat_y(zc)[0] if z >= z_bot else y_nav
        for s in (-1, 1):
            paint(ell(xc + s * (aa + r - 12*S), yy, r, r * 1.15), z)

    # Continue every cut-off cross-section outward at ITS OWN SLOPE. Where anatomy runs off a face
    # of the FOV, the outline on that face is extrapolated: the signed distance field of the face
    # profile and of a profile SLOPE_MM inside it give the rate at which the outline is opening or
    # closing, and that rate is carried outward. A morphological collar (a distance ball around the
    # face) will not do - it dilates the profile ~R mm in every direction at once, so the body
    # bulges proud of the real skin right at the FOV wall instead of continuing it.
    ext = a.lateral_extrusion_mm
    n_ext = 0
    if ext > 0:
        SLOPE_MM = 5.0
        kk = max(1, int(round(SLOPE_MM / mm)))
        n_out = int(round(ext / mm))
        taper_from = max(1, n_out - int(round(6.0 / mm)))     # round the far end off

        def sdf(m):
            return (ndimage.distance_transform_edt(m, sampling=(mm, mm))
                    - ndimage.distance_transform_edt(~m, sampling=(mm, mm)))

        for axis in (0, 1, 2):
            bm = np.moveaxis(body, axis, 0)
            if bm.shape[0] <= kk: continue
            for side in (0, 1):
                p0 = bm[0] if side == 0 else bm[-1]
                if not p0.any(): continue
                pk = bm[kk] if side == 0 else bm[-1-kk]
                d0 = sdf(p0)
                rate = np.clip(d0 - sdf(pk), -kk*mm, kk*mm) / (kk * mm)   # mm of outline per mm out
                for t in range(1, n_out + 1):
                    lvl = d0 + rate * (t * mm) - max(0, t - taper_from) * mm
                    m2 = lvl > 0
                    if not m2.any(): break
                    if axis == 0:
                        xx = ox - t if side == 0 else ox + nxo - 1 + t
                        if not 0 <= xx < NX: break
                        tgt = added[xx, oy:oy+nyo, oz:oz+nzo]
                    elif axis == 1:
                        yy = oy - t if side == 0 else oy + nyo - 1 + t
                        if not 0 <= yy < NY: break
                        tgt = added[ox:ox+nxo, yy, oz:oz+nzo]
                    else:
                        zz = oz - t if side == 0 else oz + nzo - 1 + t
                        if not 0 <= zz < NZ: break
                        tgt = added[ox:ox+nxo, oy:oy+nyo, zz]
                    n_ext += int((m2 & ~tgt).sum())
                    tgt |= m2
        print(f"cut faces continued outward at their own slope ({ext:.0f} mm): {n_ext:,} voxels")

    n_draft_inside = int(added[acq_box].sum())
    if a.smooth_sigma > 0:
        # smooth the union with the real anatomy so the added surface leaves the skin tangentially
        added[acq_box] |= body
        added = ndimage.gaussian_filter(added.astype(np.float32), a.smooth_sigma / mm) >= 0.5

    # ---------------- restore the acquired FOV, verbatim ----------------
    added[acq_box] = False
    acquired = np.zeros((NX, NY, NZ), bool); acquired[acq_box] = True
    labels_out = np.zeros((NX, NY, NZ), np.uint8)
    labels_out[added] = ADDED_LABEL
    labels_out[acq_box] = lab
    assert np.array_equal(labels_out[acq_box], lab.astype(np.uint8)), "acquired labels were modified"
    print(f"drafted through the acquired FOV then discarded there: {n_draft_inside:,} voxels")

    # did the extension actually cover the truncated cut face?
    exposed_before = exposed_after = 0
    for side, nb in ((0, ox-1), (nxo-1, ox+nxo)):
        prof = body[side, :, :]                        # (nyo, nzo) tissue on the cut face
        if 0 <= nb < NX:
            nbr = added[nb, oy:oy+nyo, oz:oz+nzo] | (labels_out[nb, oy:oy+nyo, oz:oz+nzo] > 0)
            exposed_after += int((prof & ~nbr).sum())
        exposed_before += int(prof.sum())
    print(f"truncated cut-face tissue voxels: {exposed_before:,}, still facing air after "
          f"extension: {exposed_after:,} ({100*exposed_after/max(exposed_before,1):.2f}%)")

    # ---------------- checks and save ----------------
    # `chi < -1` and `label > 0` are equivalent: background is the only label
    # whose susceptibility is positive.
    tis = labels_out > 0
    lbl, n = ndimage.label(tis)
    sizes = ndimage.sum(tis, lbl, range(1, n+1)); del lbl
    touch = dict(x=bool(tis[0].any() or tis[-1].any()), y=bool(tis[:, 0].any() or tis[:, -1].any()),
                 z=bool(tis[:, :, 0].any() or tis[:, :, -1].any()))
    acq_tissue = int(body.sum())
    print(f"tissue {acq_tissue:,} -> {int(tis.sum()):,} (+{100*added.sum()/acq_tissue:.1f}% added)")
    print(f"connected components: {n}  largest {100*sizes.max()/tis.sum():.4f}% of tissue")
    print(f"touches faces {touch}")

    aff = lab_img.affine.copy()
    aff[:3, 3] -= aff[:3, 0]*ox + aff[:3, 1]*oy + aff[:3, 2]*oz
    hdr = lab_img.header.copy(); hdr.set_data_dtype(np.uint8)
    nib.save(nib.Nifti1Image(labels_out, aff, header=hdr), f"{a.out_prefix}_label-all.nii.gz")
    nib.save(nib.Nifti1Image(acquired.astype(np.uint8), aff, header=hdr),
             f"{a.out_prefix}_acquired.nii.gz")
    json.dump({
        "Description": "Full-body mannequin extension of a torso-to-head cropped label volume.",
        "GeneratedBy": "working/body_extension/build_fullbody_generic.py",
        "Sources": {"labels": a.labels},
        "Measured": {"vertex_z": z_vertex, "vertex_mode": a.vertex,
                     "acromion_measurable": bool(acromion_ok),
                     "acquired_tissue_z": [z_bot, int(zs.max())],
                     "lateral_truncation_z": [int(min(lat)), int(max(lat))],
                     "acromion_z": Z_SH, "acromion_source": a.shoulder,
                     "ratio_calibration_slice": z_top,
                     "measured_width_depth_ratio": round(ratio_top, 4),
                     "ap_truncated_slices": len(ap)},
        "Assumed": {"stature_mm": a.stature, "stature_source": stature_src,
                    "chest_width_depth_ratio": RATIO_CHEST,
                    "landmarks_mm_below_vertex_at_1750mm": {
                        "chest": D_CHEST, "shoulder": D_SHOULDER, "elbow": D_ELBOW,
                        "wrist": D_WRIST, "fingertip": D_TIP, "hip": D_HIP,
                        "pelvis_floor": D_PELVIS_FLOOR, "knee": D_KNEE, "ankle": D_ANKLE,
                        "sole": D_SOLE},
                    "posture": "supine, arms at sides, legs straight"},
        "AcquiredFOV": {"policy": "drafted through, smoothed together with the real anatomy so the "
                                  "surfaces join tangentially, then restored verbatim",
                        "draft_voxels_discarded_inside_fov": n_draft_inside,
                        "cut_face_extrusion_mm": a.lateral_extrusion_mm,
                        "cut_face_extrusion_voxels": n_ext,
                        "cut_face_tissue_voxels": exposed_before,
                        "cut_face_voxels_still_facing_air": exposed_after},
        "CanvasShape": [NX, NY, NZ], "AcquiredFOVOffset": [ox, oy, oz],
        "AcquiredFOVShape": [nxo, nyo, nzo],
        "Labels": {str(k2): v for k2, v in {**LABEL_NAMES, ADDED_LABEL:
                   "added-body (model extension, not measured anatomy)"}.items()},
        "AddedLabel": ADDED_LABEL,
        "AddedLabelChi_ppm": CHI_LUT[ADDED_LABEL], "BackgroundChi_ppm": CHI_LUT[0],
        "ConnectedComponents": int(n), "LargestComponentFraction": float(sizes.max()/tis.sum()),
        "TissueTouchesCanvasFace": touch,
        "Caveats": [
            "Added material is a mannequin: uniform water, no lungs/bone/bowel gas, limb geometry "
            "from population proportions, only the trunk width anchored to this subject.",
            "Acquired anatomy is bit-identical to the input: the draft is discarded inside the FOV.",
            "This volume fully determines the chi map: every voxel carries a label in CHI_LUT and "
            "there is no interpolation at the added/acquired interface. An earlier version apodised "
            "the boundary chi into water over 25 mm, which made chi unreproducible from the labels "
            "alone; that blend was dropped so this volume stays the single description of the model.",
        ],
    }, open(f"{a.out_prefix}_label-all.json", "w"), indent=4)
    print(f"saved {a.out_prefix}_label-all.nii.gz / _acquired.nii.gz / _label-all.json")

    if a.qc:
        import matplotlib; matplotlib.use("Agg")
        import matplotlib.pyplot as plt, matplotlib.patches as mp
        from matplotlib.colors import ListedColormap, BoundaryNorm
        vals = [0, 1, 2, 3, 4, 5, 6, 56, 60, 91, 92, 93, 100, ADDED_LABEL]
        names = ["air", "body", "sinus", "earcanal", "trachea", "R lung", "L lung", "brain",
                 "eyes", "skull", "vertebrae", "disks", "canal", "ADDED"]
        cols = ["#0d0d14", "#c98b6b", "#4fc3f7", "#26c6da", "#7e57c2", "#ef5350", "#ec407a",
                "#ffca28", "#66bb6a", "#eeeeee", "#bdbdbd", "#8d6e63", "#42a5f5", "#1f6f8b"]
        idx = np.zeros(256, np.uint8)
        for i, v in enumerate(vals): idx[v] = i
        disp = idx[labels_out]
        cmap = ListedColormap(cols); norm = BoundaryNorm(np.arange(len(vals)+1)-0.5, len(vals))
        per_z = (labels_out[:, :, oz:oz+nzo] == ADDED_LABEL).sum(axis=(0, 1))
        z_ax = int(np.argmax(per_z))
        fig, axx = plt.subplots(1, 3, figsize=(15, 9), facecolor="#0d0d14")
        panels = [(disp[NX//2, :, :].T[::-1], f"sagittal x={NX//2}"),
                  (disp[:, oy + int(y_nav_o), :].T[::-1], f"coronal y={oy + int(y_nav_o)}"),
                  (disp[:, :, oz + z_ax].T[::-1],
                   f"axial z={z_ax} (most completion: {int(per_z[z_ax]):,} vox)")]
        for axi, (im, t) in zip(axx, panels):
            axi.imshow(im, cmap=cmap, norm=norm, interpolation="nearest")
            axi.set_title(t, color="w", fontsize=10); axi.axis("off")
        axx[0].add_patch(mp.Rectangle((oy, NZ-oz-nzo), nyo, nzo, ec="#00e5ff", fc="none", lw=1))
        axx[1].add_patch(mp.Rectangle((ox, NZ-oz-nzo), nxo, nzo, ec="#00e5ff", fc="none", lw=1))
        h = [mp.Patch(color=c, label=n2) for c, n2 in zip(cols, names)]
        fig.legend(handles=h, loc="lower center", ncol=7, framealpha=0, labelcolor="w", fontsize=9)
        fig.suptitle(f"{a.out_prefix.split('/')[-1]} — label volume (cyan = acquired FOV)",
                     color="w", fontsize=12)
        fig.tight_layout(rect=[0, 0.06, 1, 0.97])
        fig.savefig(f"{a.out_prefix}_label_qc.png", dpi=110, facecolor=fig.get_facecolor())
        print(f"saved {a.out_prefix}_label_qc.png")


if __name__ == "__main__":
    main()
