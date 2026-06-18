import subprocess
from pathlib import Path

def run_tissue2MR(
    in_file: str,
    seg_tool: str,
    version: str,
    tissue_prop: str,
    out_file: str,
):
    """
    Run tissue_to_MR from command line inside Python.

    Parameters
    ----------
    in_file : str
        Path to input NIfTI file (.nii.gz).
    seg_tool : str
        The tool used to segmented the input file (argument to -s).
    version : str
        Version of the tool used to select approriate dictionary (argument to -v).
    tissue_prop : str
        Tissue type desired (argument to -t).
    out_file : str
        Path to output NIfTI file (.nii.gz).
    """

    # Ensure paths are safe
    in_file = Path(in_file).resolve()
    out_file = Path(out_file).resolve()

    cmd = [
        "tissue_to_MR",
        "-i", str(in_file),
        "-s", seg_tool,
        "-v", version,
        "-t", tissue_prop,
        "-o", str(out_file)
    ]

    try:
        subprocess.run(cmd, check=True)
        print(f"[INFO] tissue_to_MR finished successfully. Output: {out_file}")
    except subprocess.CalledProcessError as e:
        print("[ERROR] tissue_to_MR failed!")
        print(e)
