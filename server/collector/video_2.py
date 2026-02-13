#!/usr/bin/env python3
"""
Detect prompts that were completely skipped (user never clicked Start button).
This identifies gestures the user forgot to record.
"""

import json
import csv
from collections import defaultdict

def detect_missing_prompts(json_file='metadata_dump.json', expected_prompts_file=None):
    """
    Detect which prompts were never attempted (user never clicked Start).
    
    Three types of prompts:
    1. COMPLETED: User clicked Start, performed gesture, swiped forward (valid=true)
    2. ATTEMPTED BUT REJECTED: User clicked Start, but clicked "Mistake Made" (valid=false)
    3. COMPLETELY SKIPPED: User NEVER clicked Start button (no clip data at all)
    """
    
    with open(json_file, 'r') as f:
        data = json.load(f)
    
    clips = data.get('clips', [])
    
    # Track all prompts that have ANY recording (even rejected ones)
    attempted_prompts = set()
    completed_prompts = set()
    rejected_prompts = set()
    
    print("=" * 80)
    print("MISSING PROMPTS DETECTION")
    print("=" * 80)
    print()
    
    for clip in clips:
        summary = clip.get('summary', {})
        prompt = summary.get('promptText')
        valid = summary.get('valid', False)
        has_timestamps = 'start_s' in summary and 'end_s' in summary
        
        if prompt:
            attempted_prompts.add(prompt)
            if valid:
                completed_prompts.add(prompt)
            else:
                rejected_prompts.add(prompt)
    
    print(f"Total unique prompts found in data: {len(attempted_prompts)}")
    print(f"  ✓ Completed (accepted):          {len(completed_prompts)}")
    print(f"  ✗ Attempted but rejected:        {len(rejected_prompts - completed_prompts)}")
    print()
    
    # Check if we have an expected prompts list
    expected_prompts = None
    if expected_prompts_file:
        try:
            with open(expected_prompts_file, 'r') as f:
                expected_prompts = set(line.strip() for line in f if line.strip())
            print(f"Expected prompts loaded from file: {len(expected_prompts)}")
        except FileNotFoundError:
            print(f"⚠ Expected prompts file not found: {expected_prompts_file}")
    
    # Analyze what we can determine WITHOUT expected list
    print("=" * 80)
    print("PROMPT STATUS BREAKDOWN")
    print("=" * 80)
    print()
    
    # Create detailed report
    prompt_report = []
    
    for prompt in sorted(attempted_prompts):
        if prompt in completed_prompts and prompt not in rejected_prompts:
            status = "✓ COMPLETED (First attempt)"
            category = "completed_first_try"
        elif prompt in completed_prompts and prompt in rejected_prompts:
            status = "✓ COMPLETED (After retries)"
            category = "completed_with_retries"
        elif prompt in rejected_prompts and prompt not in completed_prompts:
            status = "⚠ ATTEMPTED BUT NEVER ACCEPTED"
            category = "never_accepted"
        else:
            status = "? UNKNOWN"
            category = "unknown"
        
        prompt_report.append({
            'prompt': prompt,
            'status': status,
            'category': category
        })
        
        print(f"{status:<35} '{prompt}'")
    
    print()
    
    # Check for missing prompts if we have expected list
    if expected_prompts:
        missing_prompts = expected_prompts - attempted_prompts
        
        if missing_prompts:
            print("=" * 80)
            print("⚠ COMPLETELY SKIPPED PROMPTS (Never clicked Start button):")
            print("=" * 80)
            print()
            print(f"Found {len(missing_prompts)} prompts that were NEVER attempted:")
            print()
            for prompt in sorted(missing_prompts):
                print(f"  ✗ '{prompt}' - User never clicked Start (forgot to record)")
            print()
        else:
            print("=" * 80)
            print("✓ ALL EXPECTED PROMPTS WERE ATTEMPTED")
            print("=" * 80)
            print("User clicked Start button for every prompt (though some may be rejected)")
            print()
    else:
        print("=" * 80)
        print("ℹ NOTE: Cannot detect completely skipped prompts")
        print("=" * 80)
        print()
        print("To detect prompts where user NEVER clicked Start button, provide")
        print("a file with the expected list of prompts.")
        print()
        print("Create a file 'expected_prompts.txt' with one prompt per line:")
        print("  Rich")
        print("  Poor")
        print("  Thick")
        print("  ...")
        print()
        print("Then run: python3 missing_prompts_detector.py")
        print()
    
    # Analyze sessions to detect gaps
    analyze_session_gaps(clips)
    
    # Create CSV report
    create_missing_prompts_csv(prompt_report, expected_prompts, attempted_prompts)
    
    return prompt_report


def analyze_session_gaps(clips):
    """Analyze clip indices to detect gaps that might indicate skipped prompts."""
    
    print("=" * 80)
    print("SESSION GAP ANALYSIS")
    print("=" * 80)
    print()
    print("Checking for missing clip indices (possible skipped recordings)...")
    print()
    
    # Group by session
    sessions = defaultdict(list)
    for clip in clips:
        summary = clip.get('summary', {})
        session = summary.get('sessionIndex')
        clip_index = summary.get('clipIndex')
        prompt = summary.get('promptText', 'Unknown')
        valid = summary.get('valid', False)
        
        if session is not None and clip_index is not None:
            sessions[session].append({
                'clip_index': clip_index,
                'prompt': prompt,
                'valid': valid
            })
    
    found_gaps = False
    
    for session in sorted(sessions.keys()):
        session_clips = sorted(sessions[session], key=lambda x: x['clip_index'])
        indices = [c['clip_index'] for c in session_clips]
        
        if not indices:
            continue
        
        # Check for gaps in sequence
        expected_indices = list(range(min(indices), max(indices) + 1))
        missing_indices = set(expected_indices) - set(indices)
        
        if missing_indices:
            found_gaps = True
            print(f"Session s{session:03d}:")
            print(f"  Clip indices found: {min(indices)} to {max(indices)}")
            print(f"  Missing indices: {sorted(missing_indices)}")
            print(f"  ⚠ Possible explanation: User swiped forward WITHOUT clicking Start")
            print()
    
    if not found_gaps:
        print("✓ No gaps found in clip indices")
        print("  All recorded clips have sequential indices")
        print()
    
    print("=" * 80)
    print()


def create_missing_prompts_csv(prompt_report, expected_prompts, attempted_prompts):
    """Create CSV report of all prompts and their status."""
    
    csv_path = 'prompt_status_report.csv'
    
    with open(csv_path, 'w', newline='') as csvfile:
        writer = csv.writer(csvfile)
        writer.writerow(['prompt', 'status', 'category', 'notes'])
        
        # Write attempted prompts
        for item in sorted(prompt_report, key=lambda x: x['prompt']):
            writer.writerow([
                item['prompt'],
                item['status'],
                item['category'],
                'User clicked Start button'
            ])
        
        # Write missing prompts if we have expected list
        if expected_prompts:
            missing = expected_prompts - attempted_prompts
            for prompt in sorted(missing):
                writer.writerow([
                    prompt,
                    '✗ NEVER ATTEMPTED',
                    'completely_skipped',
                    'User NEVER clicked Start - forgot to record'
                ])
    
    print(f"✓ Prompt status report saved to: {csv_path}")
    print()


def create_expected_prompts_template():
    """Helper to create a template expected prompts file."""
    
    template = """# Expected Prompts Template
# Add one prompt per line (without quotes)
# Lines starting with # are ignored

Rich
Poor
Thick
Thin
Expensive
Cheap
Flat
Curved
Loud
Mean
Tight
High
Low
Soft
Hard
Deep
Shallow
Clean
Happy
Dirty
Strong
Weak
Dead
Alive
Male
Female
"""
    
    with open('expected_prompts_template.txt', 'w') as f:
        f.write(template)
    
    print("✓ Created expected_prompts_template.txt")
    print("  Edit this file with your actual prompts, then rename to 'expected_prompts.txt'")


if __name__ == '__main__':
    import sys
    
    print("Detecting missing/skipped prompts...\n")
    
    # Check if expected prompts file exists
    expected_file = 'expected_prompts.txt'
    
    try:
        detect_missing_prompts(expected_prompts_file=expected_file)
    except FileNotFoundError:
        detect_missing_prompts()
        
        print("\n" + "=" * 80)
        print("💡 TIP: Create Expected Prompts List")
        print("=" * 80)
        print()
        print("To detect prompts user completely skipped, create 'expected_prompts.txt'")
        print("with one prompt per line. Would you like to create a template?")
        print()
        response = input("Create template? (y/n): ").strip().lower()
        if response == 'y':
            create_expected_prompts_template()
    
    print("\n✓ Analysis complete!")
    print("\nGenerated files:")
    print("  • prompt_status_report.csv - Status of all prompts")
