import slicer
import click

@click.command()
@click.option('-m','--main_volume_path', required=True, help='Path to the main volume')
@click.option('-s','--segmentation_path', required=True, help='Path to the segmentation')
@click.option('-o','--output_path', required=True, help='Path to the output file')
def combine_spine_and_brain(main_volume_path, segmentation_path, output_path):
    """
    Perform a smoothing procedure on a given volume and segmentation in Slicer and
    create a single mask.

    This function loads a main volume and its corresponding brain/spine segmentation, 
    applies smoothing, and then saves the processed mask to the specified output path.

    Parameters:
    - main_volume_path (str): Path to the main volume file (subject T1w image).
    - segmentation_path (str): Path to the file containing brain and spine segmentation with this form:
            - Segment 1 : Brain
            - Segment 2 : Spine
    - output_path (str): Path where the output mask will be saved.

    Returns:
        None

    Example to run the script in a terminal:
        Slicer.exe --python-script combine_spine_and_brain.py 
                    -m "C:/path/to/main_volume.nii.gz" 
                    -s "C:/path/to/spine_and_brain_segmentation.nii.gz" 
                    -o "C:/path/to/output_mask.nii.gz"
    
    """

    print("Starting the smoothing procedure...")

    # Load the main volume and segmentation
    main_filename = main_volume_path.split('\\')[-1] # Get the filename from the path

    # Remove the extension
    main_filename_without_extension = main_filename.split('.')[0]

    print(f"Loading main volume from: {main_volume_path}")
    slicer.util.loadVolume(main_volume_path)
    print("Main volume loaded")
    masterVolumeNode = slicer.util.getNode(main_filename_without_extension)
    print("Main volume node obtained")
    
    print(f"Loading segmentation from: {segmentation_path}")
    segmentation_node = slicer.util.loadSegmentation(segmentation_path)
    print("Segmentation loaded")
    
    # Create segment editor to get access to effects
    segmentEditorWidget = slicer.qMRMLSegmentEditorWidget()
    segmentEditorWidget.setMRMLScene(slicer.mrmlScene)
    segmentEditorNode = slicer.mrmlScene.AddNewNodeByClass("vtkMRMLSegmentEditorNode")
    segmentEditorWidget.setMRMLSegmentEditorNode(segmentEditorNode)
    segmentEditorWidget.setSegmentationNode(segmentation_node)
    segmentEditorWidget.setMasterVolumeNode(masterVolumeNode)

    # Define the segment to select
    segmentEditorNode.SetSelectedSegmentID('Segment_1')

    # Smoothing
    segmentEditorWidget.setActiveEffectByName("Logical operators")
    effect = segmentEditorWidget.activeEffect()
    effect.setParameter("Operation", "UNION")
    effect.setParameter("ModifierSegmentID", 'Segment_2')
    effect.self().onApply()

    # Remove the segment_2
    segmentation = segmentation_node.GetSegmentation()
    segmentation.RemoveSegment('Segment_2')

    # Smoothing
    segmentEditorWidget.setActiveEffectByName("Smoothing")
    effect = segmentEditorWidget.activeEffect()
    effect.setParameter("SmoothingMethod", "MORPHOLOGICAL_CLOSING")
    effect.setParameter("KernelSizeMm", 11)
    
    effect.self().onApply()

    print("Smoothing procedure completed. Saving the output...")
    # Export segmentation to a labelmap
    labelmapVolumeNode = slicer.mrmlScene.AddNewNodeByClass('vtkMRMLLabelMapVolumeNode')
    slicer.modules.segmentations.logic().ExportVisibleSegmentsToLabelmapNode(segmentation_node, labelmapVolumeNode, masterVolumeNode)
    slicer.util.saveNode(labelmapVolumeNode, output_path)

if __name__ == '__main__':  
    combine_spine_and_brain()  
