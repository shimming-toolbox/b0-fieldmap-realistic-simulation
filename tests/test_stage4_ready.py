"""Guards on the stage-4 (shimming) scripts.

Stage 4 runs unattended over 60 subjects on a remote host. These are the things
that would stop it dead partway through, or silently read the wrong directory.
"""
import re
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
SHIM = REPO / "b0realsim" / "shim"
STEP4 = REPO / "b0realsim" / "step_4_shim.sh"

DEBUG_PATTERN = re.compile(r'^\s*(breakpoint\(\)|import\s+pdb\b|pdb\.set_trace\(\))')


def test_no_debug_breakpoints_anywhere_in_the_pipeline():
    """A live breakpoint() drops an unattended run into pdb and hangs it."""
    offenders = []
    for path in sorted((REPO / "b0realsim").rglob("*.py")):
        for i, line in enumerate(path.read_text(errors="ignore").splitlines(), 1):
            if DEBUG_PATTERN.search(line):
                offenders.append(f"{path.relative_to(REPO)}:{i}: {line.strip()}")
    assert not offenders, "debug breakpoints left in:\n  " + "\n  ".join(offenders)


def test_step4_reads_where_the_prep_scripts_write():
    """step_4_shim.sh looked in $BIDS_DIR/data/b0shim while the prep scripts
    write to $BIDS_DIR/derivatives/b0shim, so it would have found no subjects."""
    step4 = STEP4.read_text()
    assert "data/b0shim" not in step4, \
        "step_4_shim.sh still refers to data/b0shim; the prep scripts write derivatives/b0shim"
    assert "derivatives/b0shim" in step4


def test_prep_scripts_write_under_derivatives():
    for name in ("prep_for_shimming_head.py", "prep_for_shimming_brain.py"):
        text = (SHIM / name).read_text()
        assert '"derivatives" / "b0shim"' in text or "'derivatives' / 'b0shim'" in text, \
            f"{name} does not write under derivatives/b0shim"


def test_run_order_is_documented_in_step4():
    """The two prep scripts write overlapping filenames, so the order decides
    which demeaning survives. That must not be folklore."""
    step4 = STEP4.read_text().lower()
    assert "prep_for_shimming_head" in step4 and "prep_for_shimming_brain" in step4, \
        "step_4_shim.sh does not document the required prep run order"
