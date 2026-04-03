#!/usr/bin/env python3
"""
Visualize talk time data with two charts:
1. Total accumulated talk time per speaker
2. Episode-by-episode talk time comparison
"""

import matplotlib.pyplot as plt
import numpy as np
from transcript_analyzer import (
    TranscriptAnalyzer,
    find_transcript_files,
    print_transcript_setup_help,
)
import re


def extract_episode_number(filename):
    """Extract episode number for sorting"""
    # Look for patterns like EP1, EP2, etc.
    match = re.search(r'EP(\d+)', filename, re.IGNORECASE)
    if match:
        return int(match.group(1))
    
    # Look for SMLT patterns
    match = re.search(r'SMLT.*EP(\d+)', filename, re.IGNORECASE)
    if match:
        return int(match.group(1))
    
    # For other files, assign high numbers to put them at the end
    if 'Bonus' in filename:
        return 1000
    elif 'Ship' in filename:
        return 1001
    elif 'AI limitations' in filename:
        return 1002
    else:
        return 999


def visualize_talk_time():
    """Generate visualizations for talk time analysis"""
    # Set matplotlib to use a non-interactive backend
    import matplotlib
    matplotlib.use('Agg')
    
    analyzer = TranscriptAnalyzer()
    
    file_paths = find_transcript_files()
    
    if not file_paths:
        print_transcript_setup_help()
        return
    
    print("📊 Generating talk time visualizations...")
    
    # Analyze each file
    results = []
    for file_path in file_paths:
        if file_path.exists():
            result = analyzer.analyze_transcript(file_path)
            if result:
                results.append(result)
    
    if not results:
        print("No valid results to visualize.")
        return
    
    # Sort results by episode number
    results.sort(key=lambda x: extract_episode_number(x['file']))
    
    # Extract data for plotting
    episode_names = [r['file'].replace('.docx', '').replace('Scott&Mark - ', '').replace('SMLT - ', '') for r in results]
    mark_times = [r['speaking_time_seconds']['Mark'] / 60 for r in results]  # Convert to minutes
    scott_times = [r['speaking_time_seconds']['Scott'] / 60 for r in results]  # Convert to minutes
    
    # Create figure with 2 subplots
    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(15, 12))
    fig.suptitle('Mark & Scott Talk Too Much - Speaking Time Analysis', fontsize=16, fontweight='bold')
    
    # Chart 1: Episode-by-Episode Talk Time
    x = np.arange(len(episode_names))
    width = 0.35
    
    bars1 = ax1.bar(x - width/2, mark_times, width, label='Mark', color='#1f77b4', alpha=0.8)
    bars2 = ax1.bar(x + width/2, scott_times, width, label='Scott', color='#ff7f0e', alpha=0.8)
    
    ax1.set_xlabel('Episodes')
    ax1.set_ylabel('Speaking Time (minutes)')
    ax1.set_title('Episode-by-Episode Speaking Time Comparison')
    ax1.set_xticks(x)
    ax1.set_xticklabels(episode_names, rotation=45, ha='right', fontsize=8)
    ax1.legend()
    ax1.grid(True, alpha=0.3)
    
    # Add value labels on bars
    for bar in bars1:
        height = bar.get_height()
        ax1.annotate(f'{height:.0f}m',
                    xy=(bar.get_x() + bar.get_width() / 2, height),
                    xytext=(0, 3),  # 3 points vertical offset
                    textcoords="offset points",
                    ha='center', va='bottom', fontsize=6)
    
    for bar in bars2:
        height = bar.get_height()
        ax1.annotate(f'{height:.0f}m',
                    xy=(bar.get_x() + bar.get_width() / 2, height),
                    xytext=(0, 3),  # 3 points vertical offset
                    textcoords="offset points",
                    ha='center', va='bottom', fontsize=6)
    
    # Chart 2: Total Accumulated Talk Time
    total_mark = sum(mark_times)
    total_scott = sum(scott_times)
    
    speakers = ['Mark', 'Scott']
    totals = [total_mark, total_scott]
    colors = ['#1f77b4', '#ff7f0e']
    
    bars = ax2.bar(speakers, totals, color=colors, alpha=0.8, width=0.6)
    ax2.set_ylabel('Total Speaking Time (minutes)')
    ax2.set_title('Total Accumulated Speaking Time Across All Episodes')
    ax2.grid(True, alpha=0.3)
    
    # Add percentage labels
    total_time = total_mark + total_scott
    for i, (bar, total) in enumerate(zip(bars, totals)):
        percentage = (total / total_time) * 100
        hours = int(total // 60)
        minutes = int(total % 60)
        ax2.annotate(f'{total:.0f}m\n({hours}h {minutes}m)\n{percentage:.1f}%',
                    xy=(bar.get_x() + bar.get_width() / 2, total),
                    xytext=(0, 5),
                    textcoords="offset points",
                    ha='center', va='bottom', fontweight='bold', fontsize=12)
    
    # Add winner annotation
    winner = 'Scott' if total_scott > total_mark else 'Mark'
    difference = abs(total_scott - total_mark)
    diff_hours = int(difference // 60)
    diff_minutes = int(difference % 60)
    
    ax2.text(0.5, max(totals) * 0.7, 
             f'Winner: {winner}\n+{difference:.0f} minutes\n({diff_hours}h {diff_minutes}m more)',
             ha='center', va='center', fontsize=11, fontweight='bold',
             bbox=dict(boxstyle="round,pad=0.3", facecolor="lightblue", alpha=0.7))
    
    plt.tight_layout()
    
    # Save the plot
    output_file = 'talk_time_analysis.png'
    plt.savefig(output_file, dpi=300, bbox_inches='tight')
    print(f"📈 Visualization saved as: {output_file}")
    
    # Show summary stats
    print(f"\n📊 SUMMARY STATISTICS:")
    print(f"   Mark:  {total_mark:.0f} minutes ({total_mark/60:.1f} hours) - {(total_mark/total_time)*100:.1f}%")
    print(f"   Scott: {total_scott:.0f} minutes ({total_scott/60:.1f} hours) - {(total_scott/total_time)*100:.1f}%")
    print(f"   Total: {total_time:.0f} minutes ({total_time/60:.1f} hours)")
    print(f"   Winner: {winner} by {difference:.0f} minutes ({diff_hours}h {diff_minutes}m)")
    
    # Close the plot instead of showing it (for headless environments)
    plt.close()


if __name__ == '__main__':
    try:
        visualize_talk_time()
    except ImportError:
        print("Error: matplotlib is required for visualization.")
        print("Install it with: pip install matplotlib")
        print("Or run: python3 -m pip install matplotlib")
