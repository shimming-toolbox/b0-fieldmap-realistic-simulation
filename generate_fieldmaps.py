import subprocess
import os
from time import perf_counter
import click

@click.command()
@click.option('-i','--combined_label_path', required=True, help='Path to the combined labels')
def generate_fieldmap(combined_label_path):
    """
    Generates fieldmaps from combined label files.
    This function processes each file in the specified directory, generating susceptibility maps and fieldmaps.
    It creates necessary directories if they do not exist and runs external commands to perform the conversions.
    Args:
        combined_label_path (str): The path to the directory containing the combined label files.
    Raises:
        subprocess.CalledProcessError: If an external command fails.
        Exception: For any other errors that occur during processing.
    Notes:
        - The function assumes the presence of external tools `tissue_to_mr` and `compute_fieldmap`.
        - The function assumes the combined label files are in the format `subjectID_combined_labels.nii.gz`.
        - The generated susceptibility maps and fieldmaps are saved in the current working directory under 
          'susceptibility_maps' and 'fieldmaps' folders respectively.
    """

    # Get the current working directory
    current_directory = os.getcwd()

    # Create the full path for the new folders
    susceptibility_path = os.path.join(current_directory, 'susceptibility_maps')
    fieldmap_path = os.path.join(current_directory, 'fieldmaps')

    if not os.path.exists(susceptibility_path) and not os.path.exists(fieldmap_path):
        os.mkdir(susceptibility_path)
        os.mkdir(fieldmap_path)

    for filename in os.listdir(combined_label_path):

        start = perf_counter()
        subject = filename.split('_')[0]
        print(f"=================Processing {subject}==================")
        # Define the commands
        first_command = f"tissue_to_mr {combined_label_path}\\{filename} -t sus -s charles -v v1 -g 0 {susceptibility_path}\\{subject}_sus_dist.nii.gz"
        second_command = f"compute_fieldmap -i {susceptibility_path}\\{subject}_sus_dist.nii.gz -o {fieldmap_path}\\{subject}_fm.nii.gz"

        # Run the first command
        print("Running the label to susceptibility command")
        try:
            subprocess.run(first_command, check=True, shell=True)
        except subprocess.CalledProcessError as e:
            print(f"Error running the label to susceptibility command for {subject}: {e}")

        # Run the second command
        print("Running the susceptibility to fieldmap command")
        try:
            subprocess.run(second_command, check=True, shell=True)
        except subprocess.CalledProcessError as e:
            print(f"Error running the susceptibility to fieldmap command for {subject}: {e}")
        except Exception as e:
            print(f"An error occurred: {e}")

        end = perf_counter()
        print(f"Time taken: {end - start:.2f} seconds")

if __name__ == '__main__':
    generate_fieldmap()