#!/usr/bin/env python3
"""
Generate violin plots comparing unshimmed vs shimmed B0 data for all subjects.
"""

import numpy as np
import nibabel as nib
from pathlib import Path
import argparse
import os
import matplotlib.pyplot as plt
import seaborn as sns
import pandas as pd
from tqdm import tqdm

def process_all_subjects(bids_dir):
    bids_dir = Path(bids_dir)
    
    # Find all subjects
    subjects = [
        x.name for x in bids_dir.iterdir() 
        if x.is_dir() and x.name.startswith("sub-")
    ]
    
    # Remove excluded subjects (as in your original code)
    subjects = [
        x for x in subjects if x != "sub-unfErssm001" and x != "sub-unfErssm021"
    ]
    
    print(f"Processing {len(subjects)} subjects...")
    
    all_data = []
    
    for subject in tqdm(subjects):
        subject_dir = bids_dir / subject
        
        # Load brain mask
        mask_path = subject_dir / f"{subject}_mask_brain.nii.gz"
        if not mask_path.exists():
            print(f"Warning: No brain mask for {subject}, skipping")
            continue
            
        mask_img = nib.load(mask_path)
        mask_data = mask_img.get_fdata()
        mask_bool = mask_data.astype(bool)
        
        # Load unshimmed B0
        unshimmed_path = subject_dir / f"{subject}_T1w_fmap_b0-sim_head.nii.gz"
        if not unshimmed_path.exists():
            print(f"Warning: No unshimmed data for {subject}, skipping")
            continue
            
        unshimmed_img = nib.load(unshimmed_path)
        unshimmed_data = unshimmed_img.get_fdata()
        
        # Apply mask and get statistics
        unshimmed_masked = unshimmed_data[mask_bool]
        unshimmed_masked = unshimmed_masked[np.isfinite(unshimmed_masked)]
        
        # Sample a reasonable number of voxels to avoid memory issues
        if len(unshimmed_masked) > 10000:
            unshimmed_masked = np.random.choice(unshimmed_masked, 10000, replace=False)
        
        # Calculate subject-level statistics for unshimmed
        all_data.append({
            'subject': subject,
            'condition': 'Unshimmed',
            'std': np.std(unshimmed_masked),
            'mean_abs': np.mean(np.abs(unshimmed_masked)),
            'data_sample': unshimmed_masked
        })
        
        # Process step1 shimmed
        step1_path = subject_dir / "output-paper-step1" / "fieldmap_calculated_shim.nii.gz"
        if step1_path.exists():
            step1_img = nib.load(step1_path)
            step1_data = step1_img.get_fdata()
            step1_masked = step1_data[mask_bool]
            step1_masked = step1_masked[np.isfinite(step1_masked)]
            
            if len(step1_masked) > 10000:
                step1_masked = np.random.choice(step1_masked, 10000, replace=False)
            
            all_data.append({
                'subject': subject,
                'condition': 'Step1 Shimmed',
                'std': np.std(step1_masked),
                'mean_abs': np.mean(np.abs(step1_masked)),
                'data_sample': step1_masked
            })
        
        # Process step2 shimmed
        step2_path = subject_dir / "output-paper-step2" / "fieldmap_calculated_shim.nii.gz"
        if step2_path.exists():
            step2_img = nib.load(step2_path)
            step2_data = step2_img.get_fdata()
            step2_masked = step2_data[mask_bool]
            step2_masked = step2_masked[np.isfinite(step2_masked)]
            
            if len(step2_masked) > 10000:
                step2_masked = np.random.choice(step2_masked, 10000, replace=False)
            
            all_data.append({
                'subject': subject,
                'condition': 'Step2 Shimmed', 
                'std': np.std(step2_masked),
                'mean_abs': np.mean(np.abs(step2_masked)),
                'data_sample': step2_masked
            })
    
    return all_data

def create_summary_violin_plots(all_data):
    """Create cohort-level violin plots"""
    
    # Prepare data for distribution plots
    plot_data = []
    for item in all_data:
        for value in item['data_sample'][::10]:  # Subsample for plotting
            plot_data.append({
                'subject': item['subject'],
                'condition': item['condition'],
                'B0_Hz': value
            })
    
    df = pd.DataFrame(plot_data)
    
    # Plot 1: Distribution comparison
    plt.figure(figsize=(12, 8))
    sns.violinplot(x='condition', y='B0_Hz', data=df, cut=0, inner='box')
    plt.title('B0 Field Distributions - All Subjects (Brain Mask)')
    plt.ylabel('B0 Field (Hz)')
    plt.grid(True, alpha=0.3, axis='y')
    plt.savefig('cohort_b0_distributions.png', dpi=300, bbox_inches='tight')
    
    # Plot 2: Standard deviation comparison
    std_data = []
    for item in all_data:
        std_data.append({
            'subject': item['subject'],
            'condition': item['condition'],
            'std': item['std']
        })
    
    std_df = pd.DataFrame(std_data)
    
    plt.figure(figsize=(10, 6))
    sns.boxplot(x='condition', y='std', data=std_df)
    plt.title('B0 Field Standard Deviation - All Subjects')
    plt.ylabel('Standard Deviation (Hz)')
    plt.grid(True, alpha=0.3, axis='y')
    plt.savefig('cohort_b0_std_comparison.png', dpi=300, bbox_inches='tight')
    
    # Plot 3: Improvement scatter plot
    improvement_data = []
    subjects = list(set([item['subject'] for item in all_data]))
    
    for subject in subjects:
        subject_data = [item for item in all_data if item['subject'] == subject]
        unshimmed = next((item for item in subject_data if item['condition'] == 'Unshimmed'), None)
        step1 = next((item for item in subject_data if item['condition'] == 'Step1 Shimmed'), None)
        step2 = next((item for item in subject_data if item['condition'] == 'Step2 Shimmed'), None)
        
        if unshimmed and step1:
            improvement_data.append({
                'subject': subject,
                'improvement_type': 'Step1 vs Unshimmed',
                'std_improvement': (unshimmed['std'] - step1['std']) / unshimmed['std'] * 100
            })
        
        if unshimmed and step2:
            improvement_data.append({
                'subject': subject,
                'improvement_type': 'Step2 vs Unshimmed', 
                'std_improvement': (unshimmed['std'] - step2['std']) / unshimmed['std'] * 100
            })
    
    if improvement_data:
        improv_df = pd.DataFrame(improvement_data)
        plt.figure(figsize=(10, 6))
        sns.boxplot(x='improvement_type', y='std_improvement', data=improv_df)
        plt.title('B0 Field Standard Deviation Improvement')
        plt.ylabel('Improvement (%)')
        plt.grid(True, alpha=0.3, axis='y')
        plt.savefig('cohort_improvement_comparison.png', dpi=300, bbox_inches='tight')

def create_faceted_plots(all_data):
    """Create faceted plots for better visualization"""
    
    # Convert to DataFrame for summary statistics
    summary_data = []
    for item in all_data:
        summary_data.append({
            'subject': item['subject'],
            'condition': item['condition'],
            'std': item['std'],
            'mean_abs': item['mean_abs']
        })
    
    df = pd.DataFrame(summary_data)
    
    # Facet plot by condition
    g = sns.FacetGrid(df, col='condition', height=6, aspect=1)
    g.map(sns.histplot, 'std', kde=True)
    g.set_titles('{col_name}')
    g.set_axis_labels('Standard Deviation (Hz)', 'Count')
    g.fig.suptitle('Distribution of B0 Standard Deviation by Condition', y=1.02)
    plt.savefig('faceted_std_distributions.png', dpi=300, bbox_inches='tight')

def main(bids_dir):
    all_data = process_all_subjects(bids_dir)
    
    if not all_data:
        print("No data processed. Check file paths and subject directories.")
        return
    
    print(f"Processed data for {len(set([item['subject'] for item in all_data]))} subjects")
    
    # Create various summary plots
    create_summary_violin_plots(all_data)
    create_faceted_plots(all_data)
    
    # Print summary statistics
    df = pd.DataFrame([{k: v for k, v in item.items() if k != 'data_sample'} for item in all_data])
    
    print("\nSummary Statistics:")
    print("=" * 50)
    summary = df.groupby('condition').agg({
        'std': ['mean', 'std', 'min', 'max'],
        'mean_abs': ['mean', 'std']
    }).round(2)
    
    print(summary)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Generate violin plots comparing unshimmed vs shimmed B0 data for all subjects."
    )
    
    parser.add_argument(
        "-b", "--bids_dir", required=True, 
        help="Path to the BIDS derivatives directory with b0shim_brain_joint"
    )
    
    args = parser.parse_args()
    main(args.bids_dir)