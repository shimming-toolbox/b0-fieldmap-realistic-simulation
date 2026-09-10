"""Tests for the susceptibility lookup table.

CHI_LUT is the single source of truth for the values that define the simulation.
Before this refactor the values appeared twice in label_to_chi.py - once in the
mapping and once in the BIDS sidecar block - so a change could land in one and
not the other. R2.3 asks us to revisit the lung/trachea values, which is exactly
the edit that duplication would have made dangerous.
"""
import json
from pathlib import Path

import numpy as np
import pytest

from b0realsim.label_to_chi import CHI_LUT, LABEL_NAMES, ADDED_LABEL


def test_lut_matches_the_published_r0_values():
    """These are the values behind the published dataset. Changing one is a
    scientific decision (R2.3), so it must break this test deliberately rather
    than slip through."""
    assert CHI_LUT == {
        0: 0.35, 1: -9.05, 2: -2.0, 3: -2.0, 4: -4.2, 5: -4.2, 6: -4.2,
        56: -9.04, 60: -9.05, 91: -11.0, 92: -11.0, 93: -9.055, 100: -9.055,
        200: -9.05,
    }


def test_added_mannequin_material_is_water():
    assert CHI_LUT[ADDED_LABEL] == CHI_LUT[1], \
        "added body-extension material must carry the same chi as body/water"


def test_added_label_does_not_collide_with_a_published_label():
    published = {0, 1, 2, 3, 4, 5, 6, 56, 60, 91, 92, 93, 100}
    assert ADDED_LABEL not in published


def test_every_lut_key_has_a_sidecar_name():
    assert set(CHI_LUT) == set(LABEL_NAMES), \
        "CHI_LUT and LABEL_NAMES disagree - the sidecar would be incomplete"


def test_lut_covers_every_published_label():
    published = {0, 1, 2, 3, 4, 5, 6, 56, 60, 91, 92, 93, 100}
    assert published <= set(CHI_LUT)


def test_air_is_the_only_positive_chi():
    """The body-extension builder relies on this: it distinguishes tissue from
    air with `label > 0`, which is only equivalent to `chi < 0` if background is
    the sole positive value."""
    positive = {k for k, v in CHI_LUT.items() if v > 0}
    assert positive == {0}, f"unexpected positive chi values: {positive}"


def test_provenance_resolves_from_the_script_not_the_cwd(tmp_path, monkeypatch):
    """git.Repo(search_parent_directories=True) used to search the CALLER's cwd,
    so running the stage from anywhere outside the checkout - which is exactly
    what the run driver does on the compute host - raised
    InvalidGitRepositoryError. Provenance must come from where the script lives.
    """
    import git
    from pathlib import Path as _Path
    import b0realsim.label_to_chi as mod

    monkeypatch.chdir(tmp_path)          # a directory that is not in any repo
    repo = git.Repo(_Path(mod.__file__).resolve().parent, search_parent_directories=True)
    assert repo.head.object.hexsha, "could not resolve provenance from the script location"


PUBLISHED_SIDECAR = Path(
    "/Users/mathieuboudreau/neuropoly/projects/b0sim_r1/data/whole-spine/"
    "derivatives/sub-amuPA/anat/sub-amuPA_T1w-chi.json")


@pytest.mark.skipif(not PUBLISHED_SIDECAR.exists(), reason="dataset not present")
def test_lut_reproduces_every_published_sidecar_value():
    """The r0 sidecars are on OpenNeuro. This asserts the refactored LUT still
    produces exactly those chi values for every label the published dataset
    carries, so the R2.3 edit - when it comes - is visible as a deliberate
    change here rather than an accident of the refactor.
    """
    published = json.loads(PUBLISHED_SIDECAR.read_text())["anatomy"]

    for name, entry in published.items():
        assert name in LABEL_NAMES.values(), f"published key {name!r} missing from LABEL_NAMES"
        label = int(entry["label"])          # r0 stored body's label as the string "1"
        assert CHI_LUT[label] == entry["chi"], (
            f"{name} (label {label}): LUT has {CHI_LUT[label]}, "
            f"published dataset has {entry['chi']}")
        assert LABEL_NAMES[label] == name


@pytest.mark.skipif(not PUBLISHED_SIDECAR.exists(), reason="dataset not present")
def test_only_the_body_extension_label_is_new_relative_to_r0():
    published = json.loads(PUBLISHED_SIDECAR.read_text())["anatomy"]
    published_labels = {int(e["label"]) for e in published.values()}
    assert set(CHI_LUT) - published_labels == {ADDED_LABEL}
