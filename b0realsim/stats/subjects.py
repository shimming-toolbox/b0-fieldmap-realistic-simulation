import pandas as pd
import numpy as np
from pathlib import Path
import os
import argparse


def main(BIDS_DIR):
    """
    Main function to run the age/weight/height stats for the subjects in the BIDS dataset

    :param BIDS_DIR: Path to the BIDS dataset

    :return: None
    """

    participants = "participants.tsv"

    omit = ["sub-unfErssm001", "sub-unfErssm021"]

    df = pd.read_csv(BIDS_DIR / participants, sep="\t")

    for o in omit:
        df = df[df["participant_id"] != o]

    print(df)

    print("Mean age")
    print(np.nanmean(df["age"].values))
    print("STD age")
    print(np.nanstd(df["age"].values))

    print("Max age")
    print(np.nanmax(df["age"].values))
    print("Min age")
    print(np.nanmin(df["age"].values))

    print("Mean weight")
    print(np.nanmean(df["weight (kg)"].values))
    print("STD weight")
    print(np.nanstd(df["weight (kg)"].values))

    print("Max weight")
    print(np.nanmax(df["weight (kg)"].values))
    print("Min weight")
    print(np.nanmin(df["weight (kg)"].values))

    print("Mean height")
    print(np.nanmean(df["height (cm)"].values))
    print("STD height")
    print(np.nanstd(df["height (cm)"].values))

    print("Max height")
    print(np.nanmax(df["height (cm)"].values))
    print("Min height")
    print(np.nanmin(df["height (cm)"].values))


if __name__ == "__main__":
    current_directory = os.path.dirname(os.path.abspath(__file__))

    # Create an argument parser
    parser = argparse.ArgumentParser(
        description="Run th age/weight/height stats for the subjects in the BIDS dataset"
    )

    # Add arguments to the parser (-b or --bids_dir)
    parser.add_argument("-b", "--bids_dir", type=str, help="Path to the BIDS dataset")

    # Parse the arguments
    args = parser.parse_args()

    # Pass the bids directory to the main function
    BIDS_DIR = Path(args.bids_dir)

    main(BIDS_DIR)
