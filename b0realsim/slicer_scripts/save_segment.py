import slicer
import os
import click
from pathlib import Path

@click.command()
@click.option("-m", "--main_volume_path", required=True, help="Path to the main volume")
@click.option(
    "-s", "--segmentation_path", required=True, help="Path to the SAMSEG segmentation"
)
@click.option("-o", "--output_path", required=True, help="Path to the output file")
@click.option("-a", "--anatomy", required=True, help="Anatomy label")
def save_segment(main_volume_path, segmentation_path, output_path, anatomy):
    """
    Save a specific segment from a segmentation file

    Args:
        main_volume_path: str, path to the main volume
        segmentation_path: str, path to the segmentation file
        output_path: str, path to the output file
        anatomy: str, anatomy label

    Returns:
        None

    """

    if anatomy == "body":
        segment_id = "Segment_1"
    elif anatomy == "skull":
        segment_id = "Segment_165"
    elif anatomy == "sinus":
        segment_id = "Segment_2"
    elif anatomy == "brain":
        segment_id = "Segment_56"
    elif anatomy == "eyes":
        segment_id = "Segment_259"
    elif anatomy == "earcanal":
        segment_id = "Segment_3"
    elif anatomy == "skin":
        segment_id = "Segment_258"

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


    # List of segments to keep
    segmentsToKeep = [segment_id]  # Sinus

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


if __name__ == "__main__":
    save_segment()
