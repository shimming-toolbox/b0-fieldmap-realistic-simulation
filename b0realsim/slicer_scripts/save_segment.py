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
        # Add all segments to Segment 1 to fill in cavities
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

    if anatomy == "body":
        # Keep largest island

        # Smooth gaussian 5 or 10 mm, might need to adjust the grow step
        
        
        # Grow the segment
        union(segmentEditorWidget, ["Segment_2", "Segment_3", "Segment_4", "Segment_5", "Segment_6"])
    
        processing_steps = {
            0: {
                "union": {
                    "merged_segments": ["Segment_2", "Segment_3", "Segment_4", "Segment_5", "Segment_6"],
                },
            }
        }
    else:
        processing_steps = None

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

def union(segmentEditorWidget, id_list):

    print("Starting segment union operation")
    # Union
    segmentEditorWidget.setActiveEffectByName("Logical operators")
    effect = segmentEditorWidget.activeEffect()
    effect.setParameter("Operation", "UNION")

    for segment_id in id_list:
        effect.setParameter("ModifierSegmentID", segment_id)
        effect.self().onApply()
    print("Finished segment union operation")

    return segmentEditorWidget


if __name__ == "__main__":
    save_segment()
