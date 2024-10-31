import slicer
import os
import click
from pathlib import Path
import json
import datetime
import git

@click.command()
@click.option("-m", "--main_volume_path", required=True, help="Path to the main volume")
@click.option(
    "-s", "--segmentation_path", required=True, help="Path to the SAMSEG segmentation"
)
@click.option("-o", "--output_path", required=True, help="Path to the output file")
@click.option("-a", "--anatomy", required=True, help="Anatomy label")
def smoothing_procedure(main_volume_path, segmentation_path, output_path, anatomy):
    """
    Perform a smoothing procedure on a given volume and segmentation in Slicer.

    This function loads a main volume and its corresponding SAMSEG segmentation,
    keeps only the skull and eyes labels, applies smoothing and island removal effects
    on the skull, and then saves the processed segmentation to the specified output path.

    Parameters:
    - main_volume_path (str): Path to the main volume file (subject T1w image).
    - segmentation_path (str): Path to the SAMSEG segmentation file.
    - output_path (str): Path where the output labelmap will be saved.

    Returns:
        None

    Example to run the script in a terminal:
        Slicer.exe --python-script smoothing_procedure.py
                    -m "C:/path/to/main_volume.nii.gz"
                    -s "C:/path/to/segmentation.nii.gz"
                    -o "C:/path/to/output_labelmap.nii.gz"

    """

    if anatomy == "body":
        segment_id = "Segment_1"
    elif anatomy == "skull":
        segment_id = "Segment_1"
    elif anatomy == "sinus":
        segment_id = "Segment_1"
    elif anatomy == "brain":
        segment_id = "Segment_56"
    elif anatomy == "eyes":
        segment_id = "Segment_1"
    elif anatomy == "earcanal":
        segment_id = "Segment_1"
    print(anatomy)
    print(f"Segment ID: {segment_id}")
    print("Starting the smoothing procedure...")

    # Load the main volume and segmentation
    main_filename = str(Path(main_volume_path).stem) + '.gz' # Get the filename from the path

    # Remove the extension to
    main_filename_without_extension = Path(Path(main_filename).stem).stem

    print(f"Loading main volume from: {Path(main_volume_path).resolve()}")
    slicer.util.loadVolume(Path(main_volume_path).resolve())

    print("Main volume loaded")

    masterVolumeNode = slicer.util.getNode(main_filename_without_extension)
    print("Main volume node obtained")

    print(f"Loading segmentation from: {Path(segmentation_path).resolve()}")
    segmentation_node = slicer.util.loadSegmentation(Path(segmentation_path).resolve())
    print("Segmentation loaded")

    # Create segment editor to get access to effects
    segmentEditorWidget = slicer.qMRMLSegmentEditorWidget()
    segmentEditorWidget.setMRMLScene(slicer.mrmlScene)
    segmentEditorNode = slicer.mrmlScene.AddNewNodeByClass("vtkMRMLSegmentEditorNode")
    segmentEditorWidget.setMRMLSegmentEditorNode(segmentEditorNode)
    segmentEditorWidget.setSegmentationNode(segmentation_node)
    segmentEditorWidget.setMasterVolumeNode(masterVolumeNode)

    # Define the segment to select
    segmentEditorNode.SetSelectedSegmentID(segment_id)

    if anatomy == "body":
        # Grow the segment
        grow(segmentEditorWidget, 3)

        processing_steps = {
            "grow": {
                "margin_mm": 3,
            },
        }
    elif anatomy == "skull":
        # Remove small islands
        islands(segmentEditorWidget)
        # Smoothing
        close(segmentEditorWidget, 15)
        # Grow the segment
        grow(segmentEditorWidget, 3)
        # Smoothing
        close(segmentEditorWidget, 15)
        # Shrink the segment
        shrink(segmentEditorWidget, 2)

        processing_steps = {
            "islands": {
                "operation": "REMOVE_SMALL_ISLANDS",
            },
            "smoothing": {
                "method": "MORPHOLOGICAL_CLOSING",
                "kernel_size_mm": 15,
            },
            "grow": {
                "margin_mm": 3,
            },
            "smoothing": {
                "method": "MORPHOLOGICAL_CLOSING",
                "kernel_size_mm": 15,
            },
            "shrink": {
                "margin_mm": 2,
            },
        }
    elif anatomy == "sinus":
        # Remove small islands
        islands(segmentEditorWidget)
        # Smoothing
        gaussian(segmentEditorWidget, 2)
        # Shrink the segment
        shrink(segmentEditorWidget, 2)

        processing_steps = {
            "islands": {
                "operation": "REMOVE_SMALL_ISLANDS",
            },
            "smoothing": {
                "method": "GAUSSIAN",
                "kernel_size_mm": 2,
            },
            "shrink": {
                "margin_mm": 2,
            },
        }
    elif anatomy == "brain":
        # Remove small islands
        islands(segmentEditorWidget)
        # Smoothing
        gaussian(segmentEditorWidget, 2)
        # Grow the segment
        grow(segmentEditorWidget, 1)

        processing_steps = {
            "islands": {
                "operation": "REMOVE_SMALL_ISLANDS",
            },
            "smoothing": {
                "method": "GAUSSIAN",
                "kernel_size_mm": 2,
            },
            "grow": {
                "margin_mm": 1,
            },
        }
    elif anatomy == "eyes":
        # Remove small islands
        islands(segmentEditorWidget)
        # Smoothing
        close(segmentEditorWidget, 15)
        # Grow the segment
        grow(segmentEditorWidget, 3)
        # Smoothing
        close(segmentEditorWidget, 15)
        # Shrink the segment
        shrink(segmentEditorWidget, 3)

        processing_steps = {
            "islands": {
                "operation": "REMOVE_SMALL_ISLANDS",
            },
            "smoothing": {
                "method": "MORPHOLOGICAL_CLOSING",
                "kernel_size_mm": 15,
            },
            "grow": {
                "margin_mm": 3,
            },
            "smoothing": {
                "method": "MORPHOLOGICAL_CLOSING",
                "kernel_size_mm": 15,
            },
            "shrink": {
                "margin_mm": 3,
            },
        }
    elif anatomy == "earcanal":
        # Remove small islands
        islands(segmentEditorWidget)
        # Smoothing
        gaussian(segmentEditorWidget, 2)
        # Shrink the segment
        shrink(segmentEditorWidget, 1)

        processing_steps = {
            "islands": {
                "operation": "REMOVE_SMALL_ISLANDS",
            },
            "smoothing": {
                "method": "GAUSSIAN",
                "kernel_size_mm": 2,
            },
            "shrink": {
                "margin_mm": 1,
            },
        }

    # List of segments to keep
    segmentsToKeep = [segment_id]  # Body

    segmentation = segmentation_node.GetSegmentation()
    # List to store segment IDs that need to be removed
    segmentsToRemove = []

    # Iterate through all segment IDs in the segmentation
    segmentIDs = [
        segmentation.GetNthSegmentID(i)
        for i in range(segmentation.GetNumberOfSegments())
    ]

    for segmentID in segmentIDs:
        # Get the segment name
        segmentName = segmentation.GetSegment(segmentID).GetName()

        # Check if the segment name is not in the list of segments to keep
        if segmentName not in segmentsToKeep:
            # Add the segment ID to the list of segments to remove
            segmentsToRemove.append(segmentID)

    # Remove segments that are not in the list of segments to keep
    for segmentID in segmentsToRemove:
        segmentation.RemoveSegment(segmentID)

    print("Smoothing procedure completed. Saving the output...")
    # Export segmentation to a labelmap
    labelmapVolumeNode = slicer.mrmlScene.AddNewNodeByClass("vtkMRMLLabelMapVolumeNode")
    slicer.modules.segmentations.logic().ExportVisibleSegmentsToLabelmapNode(
        segmentation_node, labelmapVolumeNode, masterVolumeNode
    )
    slicer.util.saveNode(labelmapVolumeNode, str(Path(output_path).resolve()))

    # JSON sidecar

    repo = git.Repo(search_parent_directories=True)


    bids_sidecar = {}
    bids_sidecar['author'] = os.getenv('USER')
    bids_sidecar['date'] = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    bids_sidecar['script'] = str(Path(os.path.abspath(__file__)).resolve())
    bids_sidecar['script source'] = repo.remotes.origin.url
    bids_sidecar['script commit hash'] = repo.head.object.hexsha
    bids_sidecar["input file"] = str(Path(segmentation_path).resolve())
    bids_sidecar["label"] = {}
    bids_sidecar["label"]["anatomy"] = anatomy
    bids_sidecar["label"]["value"] = 1
    bids_sidecar["label"]["input file value"] = int(segment_id.split("_")[1])
    bids_sidecar["label"]["processing steps"] = processing_steps
    bids_sidecar['command'] = "/Applications/Slicer.app/Contents/MacOS/Slicer --python-script " + bids_sidecar['script'] + " -m " + main_volume_path + " -s " + segmentation_path + " -o " + output_path + " -a " + anatomy
    bids_sidecar["slicer version"] = str(slicer.app.majorVersion) + "." + str(slicer.app.minorVersion)
    bids_sidecar["slicer repository revision"] = str(slicer.app.repositoryRevision)

    json_file = str(Path(output_path).resolve()).replace(".nii.gz", ".json")
    if os.path.exists(json_file):
        os.remove(json_file)

    with open(json_file, 'w', encoding='utf-8') as f:
        json.dump(bids_sidecar, f, ensure_ascii=False, indent=4)

def grow(segmentEditorWidget, marginmm):

    assert marginmm > 0, "Margin must be a negative number"

    print("Starting grow margins operation")
    # Margins
    segmentEditorWidget.setActiveEffectByName("Margin")
    effect = segmentEditorWidget.activeEffect()
    effect.setParameter("MarginSizeMm", marginmm)
    effect.self().onApply()
    print("Finished grow margins operation")

    return segmentEditorWidget


def shrink(segmentEditorWidget, marginmm):

    assert marginmm > 0, "Margin must be a negative number"

    print("Starting shrink margins operation")
    # Margins
    segmentEditorWidget.setActiveEffectByName("Margin")
    effect = segmentEditorWidget.activeEffect()
    effect.setParameter("MarginSizeMm", -marginmm)
    effect.self().onApply()
    print("Finished shrink margins operation")

    return segmentEditorWidget


def islands(segmentEditorWidget):

    print("Starting islands operation")
    # Islands

    segmentEditorWidget.setActiveEffectByName("Islands")
    effect = segmentEditorWidget.activeEffect()
    effect.setParameter("Operation", "REMOVE_SMALL_ISLANDS")
    effect.self().onApply()

    print("Finished islands operation")

    return segmentEditorWidget


def close(segmentEditorWidget, kernelmm):

    print("Starting smoothing operation")
    # Smoothing
    segmentEditorWidget.setActiveEffectByName("Smoothing")
    effect = segmentEditorWidget.activeEffect()
    effect.setParameter("SmoothingMethod", "MORPHOLOGICAL_CLOSING")
    effect.setParameter("KernelSizeMm", kernelmm)
    effect.self().onApply()
    print("Finished smoothing operation")

    return segmentEditorWidget


def gaussian(segmentEditorWidget, kernelmm):

    print("Starting smoothing operation")
    # Smoothing
    segmentEditorWidget.setActiveEffectByName("Smoothing")
    effect = segmentEditorWidget.activeEffect()
    effect.setParameter("SmoothingMethod", "GAUSSIAN")
    effect.setParameter("KernelSizeMm", kernelmm)
    effect.self().onApply()
    print("Finished smoothing operation")

    return segmentEditorWidget


if __name__ == "__main__":
    smoothing_procedure()
