#!/usr/bin/env python3
import shutil
import argparse
from pathlib import Path

def copy_t1w_files(folder_names, source_parent, dest_parent):
    """
    Copy _T1w.nii.gz files from source folders to destination folders.
    
    Parameters:
    -----------
    folder_names : list
        List of folder names to process
    source_parent : str or Path
        Parent directory containing source folders
    dest_parent : str or Path
        Parent directory where files will be copied
    """
    source_parent = Path(source_parent)
    dest_parent = Path(dest_parent)
    
    copied_count = 0
    
    for folder_name in folder_names:
        source_folder = source_parent / folder_name / 'anat'
        dest_folder = dest_parent / folder_name
        
        # Find the T1w file in the source folder
        t1w_files = list(source_folder.glob("*_T1w.nii.gz"))
        
        if len(t1w_files) == 0:
            print(f"Warning: No _T1w.nii.gz file found in {source_folder}")
            continue
        elif len(t1w_files) > 1:
            print(f"Warning: Multiple _T1w.nii.gz files in {source_folder}, using first one")
        
        # Create destination folder if it doesn't exist
        dest_folder.mkdir(parents=True, exist_ok=True)
        
        # Copy the file
        source_file = t1w_files[0]
        dest_file = dest_folder / source_file.name
        shutil.copy2(source_file, dest_file)
        print(f"Copied: {source_file} -> {dest_file}")
        copied_count += 1
    
    print(f"\nTotal files copied: {copied_count}/{len(folder_names)}")

def main():
    parser = argparse.ArgumentParser(description='Copy _T1w.nii.gz files from source to destination folders')
    parser.add_argument('subjects_file', help='Text file containing folder names (one per line)')
    parser.add_argument('source_parent', help='Parent directory containing source folders')
    parser.add_argument('dest_parent', help='Parent directory for destination folders')
    
    args = parser.parse_args()
    
    # Read folder names from file
    with open(args.subjects_file, 'r') as f:
        folder_names = [line.strip() for line in f if line.strip()]
    
    print(f"Found {len(folder_names)} subjects in {args.subjects_file}")
    copy_t1w_files(folder_names, args.source_parent, args.dest_parent)

if __name__ == '__main__':
    main()