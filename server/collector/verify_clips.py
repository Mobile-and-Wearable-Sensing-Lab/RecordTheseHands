#!/usr/bin/env python3
"""
Enhanced verification script to check clip quality and completion confidence.
Provides additional checks beyond just the 'valid' flag.
"""

import json
import csv
from collections import defaultdict

def verify_clip_quality(json_file='metadata_dump.json'):
    """Verify clip quality with multiple confidence checks."""
    
    with open(json_file, 'r') as f:
        data = json.load(f)
    
    clips = data.get('clips', [])
    
    results = {
        'high_confidence': [],      # valid=True + good timestamps + complete data
        'medium_confidence': [],    # valid=True but suspicious duration
        'low_confidence': [],       # valid=True but missing some data
        'invalid': [],              # valid=False
        'incomplete': []            # Missing critical data
    }
    
    print("=" * 80)
    print("CLIP QUALITY VERIFICATION REPORT")
    print("=" * 80)
    print()
    
    for clip in clips:
        summary = clip.get('summary', {})
        full = clip.get('full', {})
        
        # Extract key fields
        prompt = summary.get('promptText', 'N/A')
        valid = summary.get('valid', False)
        start_s = summary.get('start_s')
        end_s = summary.get('end_s')
        filename = summary.get('filename', 'N/A')
        session = summary.get('sessionIndex', 0)
        
        # Calculate duration if timestamps exist
        duration = None
        if start_s is not None and end_s is not None:
            duration = end_s - start_s
        
        clip_info = {
            'prompt': prompt,
            'session': f"s{session:03d}",
            'filename': filename,
            'valid': valid,
            'start_s': start_s,
            'end_s': end_s,
            'duration': duration,
            'issues': []
        }
        
        # Categorize based on quality checks
        if not valid:
            clip_info['issues'].append("User marked as INVALID")
            results['invalid'].append(clip_info)
            
        elif start_s is None or end_s is None or prompt == 'N/A':
            clip_info['issues'].append("Missing critical data")
            results['incomplete'].append(clip_info)
            
        elif duration is not None:
            # Check duration (typical sign language gestures: 1-10 seconds)
            if duration < 0.5:
                clip_info['issues'].append(f"Too short ({duration:.2f}s)")
                results['low_confidence'].append(clip_info)
            elif duration > 20:
                clip_info['issues'].append(f"Unusually long ({duration:.2f}s)")
                results['medium_confidence'].append(clip_info)
            elif duration < 1:
                clip_info['issues'].append(f"Very short ({duration:.2f}s)")
                results['medium_confidence'].append(clip_info)
            else:
                clip_info['issues'].append(f"Good duration ({duration:.2f}s)")
                results['high_confidence'].append(clip_info)
        else:
            results['low_confidence'].append(clip_info)
    
    # Print summary
    total = len(clips)
    print(f"Total clips analyzed: {total}")
    print()
    print("CONFIDENCE BREAKDOWN:")
    print(f"  ✓ HIGH Confidence (completed well):     {len(results['high_confidence']):<4} "
          f"({len(results['high_confidence'])/total*100:.1f}%)")
    print(f"  ⚠ MEDIUM Confidence (minor issues):     {len(results['medium_confidence']):<4} "
          f"({len(results['medium_confidence'])/total*100:.1f}%)")
    print(f"  ⚠ LOW Confidence (suspicious data):     {len(results['low_confidence']):<4} "
          f"({len(results['low_confidence'])/total*100:.1f}%)")
    print(f"  ✗ INVALID (user skipped):               {len(results['invalid']):<4} "
          f"({len(results['invalid'])/total*100:.1f}%)")
    print(f"  ✗ INCOMPLETE (missing data):            {len(results['incomplete']):<4} "
          f"({len(results['incomplete'])/total*100:.1f}%)")
    print()
    print("=" * 80)
    
    # Show suspicious clips
    if results['medium_confidence'] or results['low_confidence']:
        print("\n⚠ CLIPS REQUIRING MANUAL REVIEW:")
        print("=" * 80)
        
        for clip in results['medium_confidence'] + results['low_confidence']:
            print(f"Prompt: {clip['prompt']:<15} Session: {clip['session']}")
            print(f"  Duration: {clip['duration']:.2f}s" if clip['duration'] else "  Duration: N/A")
            print(f"  Issues: {', '.join(clip['issues'])}")
            print(f"  File: {clip['filename']}")
            print("-" * 80)
    
    # Show invalid clips
    if results['invalid']:
        print("\n✗ CLIPS USER MARKED AS INVALID (NOT PERFORMED):")
        print("=" * 80)
        for clip in results['invalid']:
            print(f"Prompt: {clip['prompt']:<15} Session: {clip['session']}")
            print(f"  Reason: {', '.join(clip['issues'])}")
            print("-" * 80)
    
    # Create detailed CSV report
    create_verification_csv(results)
    
    # Calculate overall confidence
    calculate_overall_confidence(results, total)
    
    return results


def create_verification_csv(results):
    """Create CSV with confidence ratings."""
    
    csv_path = 'clip_verification_report.csv'
    
    with open(csv_path, 'w', newline='') as csvfile:
        writer = csv.writer(csvfile)
        writer.writerow([
            'confidence', 'prompt', 'session', 'duration_s', 
            'valid_flag', 'issues', 'filename'
        ])
        
        for confidence, clips in results.items():
            for clip in clips:
                writer.writerow([
                    confidence.upper(),
                    clip['prompt'],
                    clip['session'],
                    f"{clip['duration']:.2f}" if clip['duration'] else 'N/A',
                    'YES' if clip['valid'] else 'NO',
                    '; '.join(clip['issues']),
                    clip['filename']
                ])
    
    print(f"\n✓ Detailed verification report saved to: {csv_path}")


def calculate_overall_confidence(results, total):
    """Calculate overall confidence score."""
    
    print("\n" + "=" * 80)
    print("OVERALL CONFIDENCE ASSESSMENT")
    print("=" * 80)
    
    high = len(results['high_confidence'])
    medium = len(results['medium_confidence'])
    low = len(results['low_confidence'])
    
    # Weighted confidence score
    confidence_score = (high * 1.0 + medium * 0.7 + low * 0.3) / total * 100
    
    print(f"\nOverall Confidence Score: {confidence_score:.1f}%")
    print()
    
    if confidence_score >= 95:
        print("✓ EXCELLENT: Very high confidence in data quality")
        print("  → Most clips are properly completed with good timestamps")
    elif confidence_score >= 85:
        print("✓ GOOD: High confidence with minor issues")
        print("  → Some clips may need manual review but most are valid")
    elif confidence_score >= 70:
        print("⚠ FAIR: Moderate confidence")
        print("  → Several clips need manual verification")
    else:
        print("✗ POOR: Low confidence in data quality")
        print("  → Many clips have issues - recommend manual review")
    
    print()
    print("RECOMMENDATION:")
    if len(results['invalid']) > 0:
        print(f"  • {len(results['invalid'])} clips were NOT performed (user marked invalid)")
    if len(results['medium_confidence']) + len(results['low_confidence']) > 0:
        print(f"  • {len(results['medium_confidence']) + len(results['low_confidence'])} "
              "clips need manual review")
    if high > total * 0.9:
        print("  • Data quality is excellent - safe to proceed with analysis")
    
    print("=" * 80)


if __name__ == '__main__':
    print("Running enhanced clip verification...\n")
    verify_clip_quality()
    print("\n✓ Verification complete!")
    print("\nFiles generated:")
    print("  • clip_verification_report.csv - Detailed confidence ratings")
