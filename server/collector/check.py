#!/usr/bin/env python3
"""
Script to analyze which clips are valid/invalid and generate a detailed report.
This helps identify which prompts were NOT performed or had issues.
"""

import json
import csv
from collections import defaultdict

def analyze_clips(json_file='metadata_dump.json'):
    """Analyze clips and create reports for valid and invalid recordings."""
    
    # Load the JSON data
    with open(json_file, 'r') as f:
        data = json.load(f)
    
    clips = data.get('clips', [])
    
    # Categorize clips
    valid_clips = []
    invalid_clips = []
    missing_data_clips = []
    
    for clip in clips:
        summary = clip.get('summary', {})
        
        # Check if clip has required data
        has_timestamps = 'start_s' in summary and 'end_s' in summary
        has_prompt = 'promptText' in summary
        is_valid = summary.get('valid', False)
        
        if not has_timestamps or not has_prompt:
            missing_data_clips.append(summary)
        elif is_valid:
            valid_clips.append(summary)
        else:
            invalid_clips.append(summary)
    
    # Print summary
    print("=" * 70)
    print("CLIP ANALYSIS REPORT")
    print("=" * 70)
    print(f"Total clips found: {len(clips)}")
    print(f"Valid clips (user performed gesture): {len(valid_clips)}")
    print(f"Invalid clips (skipped/failed): {len(invalid_clips)}")
    print(f"Clips with missing data: {len(missing_data_clips)}")
    print("=" * 70)
    print()
    
    # Create detailed CSV report
    create_full_report(valid_clips, invalid_clips, missing_data_clips)
    
    # Show invalid clips details
    if invalid_clips:
        print(f"\n{'='*70}")
        print("INVALID/SKIPPED CLIPS (User did NOT perform these):")
        print(f"{'='*70}")
        for clip in invalid_clips:
            print(f"  Prompt: '{clip.get('promptText', 'N/A')}'")
            print(f"  Session: s{clip.get('sessionIndex', '???'):03d}")
            print(f"  Filename: {clip.get('filename', 'N/A')}")
            print(f"  Reason: User marked as invalid/skipped")
            print("-" * 70)
    else:
        print("\n✓ All clips are valid! User completed all prompts.")
    
    # Prompt statistics
    print_prompt_statistics(valid_clips, invalid_clips)
    
    return valid_clips, invalid_clips, missing_data_clips


def create_full_report(valid_clips, invalid_clips, missing_clips):
    """Create a comprehensive CSV report with all clips."""
    
    report_path = 'clip_analysis_report.csv'
    
    with open(report_path, 'w', newline='') as csvfile:
        writer = csv.writer(csvfile)
        
        # Header
        writer.writerow([
            'status', 'user_id', 'session', 'clip_index', 
            'filename', 'prompt_text', 'start_s', 'end_s', 'notes'
        ])
        
        # Valid clips
        for clip in sorted(valid_clips, key=lambda x: (x.get('sessionIndex', 0), x.get('clipIndex', 0))):
            writer.writerow([
                'VALID',
                clip.get('userId', ''),
                f"s{clip.get('sessionIndex', 0):03d}",
                clip.get('clipIndex', ''),
                clip.get('filename', ''),
                clip.get('promptText', ''),
                clip.get('start_s', ''),
                clip.get('end_s', ''),
                'User completed this gesture'
            ])
        
        # Invalid clips
        for clip in sorted(invalid_clips, key=lambda x: (x.get('sessionIndex', 0), x.get('clipIndex', 0))):
            writer.writerow([
                'INVALID',
                clip.get('userId', ''),
                f"s{clip.get('sessionIndex', 0):03d}",
                clip.get('clipIndex', ''),
                clip.get('filename', ''),
                clip.get('promptText', ''),
                clip.get('start_s', ''),
                clip.get('end_s', ''),
                'User SKIPPED or marked invalid'
            ])
        
        # Missing data clips
        for clip in missing_clips:
            writer.writerow([
                'MISSING_DATA',
                clip.get('userId', ''),
                f"s{clip.get('sessionIndex', 0):03d}",
                clip.get('clipIndex', ''),
                clip.get('filename', ''),
                clip.get('promptText', 'N/A'),
                '',
                '',
                'Incomplete recording data'
            ])
    
    print(f"✓ Detailed report saved to: {report_path}")
    print()


def print_prompt_statistics(valid_clips, invalid_clips):
    """Print statistics about which prompts were completed."""
    
    print(f"\n{'='*70}")
    print("PROMPT COMPLETION STATISTICS")
    print(f"{'='*70}")
    
    # Count prompts
    valid_prompts = defaultdict(int)
    invalid_prompts = defaultdict(int)
    
    for clip in valid_clips:
        prompt = clip.get('promptText', 'Unknown')
        valid_prompts[prompt] += 1
    
    for clip in invalid_clips:
        prompt = clip.get('promptText', 'Unknown')
        invalid_prompts[prompt] += 1
    
    # Get all unique prompts
    all_prompts = set(valid_prompts.keys()) | set(invalid_prompts.keys())
    
    print(f"{'Prompt':<20} {'Completed':<12} {'Skipped':<12} {'Status'}")
    print("-" * 70)
    
    for prompt in sorted(all_prompts):
        completed = valid_prompts.get(prompt, 0)
        skipped = invalid_prompts.get(prompt, 0)
        status = "✓ DONE" if skipped == 0 else "⚠ INCOMPLETE"
        print(f"{prompt:<20} {completed:<12} {skipped:<12} {status}")
    
    print("=" * 70)
    print()


if __name__ == '__main__':
    print("Analyzing clip data from metadata_dump.json...\n")
    analyze_clips()
    print("\n✓ Analysis complete!")
    print("\nFiles generated:")
    print("  1. clip_analysis_report.csv - Full report with valid/invalid status")
    print("  2. Console output - Summary of skipped/invalid clips")
