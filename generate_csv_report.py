#!/usr/bin/env python3
"""
Generate CSV report from transcript analysis
"""

import csv
import sys
from transcript_analyzer import (
    TranscriptAnalyzer,
    find_transcript_files,
    print_transcript_setup_help,
)


def generate_csv_report(output_file: str = "transcript_analysis_report.csv"):
    """Generate a CSV report of the transcript analysis"""
    analyzer = TranscriptAnalyzer()
    
    file_paths = find_transcript_files()
    
    if not file_paths:
        print_transcript_setup_help()
        return
    
    print(f"Analyzing {len(file_paths)} files for CSV report...")
    
    # Analyze each file
    results = []
    for file_path in file_paths:
        if file_path.exists():
            result = analyzer.analyze_transcript(file_path)
            if result:
                results.append(result)
    
    if not results:
        print("No valid results to write to CSV.")
        return
    
    # Write CSV report
    with open(output_file, 'w', newline='', encoding='utf-8') as csvfile:
        fieldnames = [
            'Episode', 'Mark_Words', 'Scott_Words', 'Mark_Time_Seconds', 
            'Scott_Time_Seconds', 'Mark_Time_Formatted', 'Scott_Time_Formatted',
            'Mark_Segments', 'Scott_Segments', 'Total_Words', 
            'Mark_Word_Percentage', 'Scott_Word_Percentage',
            'Winner_by_Words', 'Word_Difference'
        ]
        
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        writer.writeheader()
        
        for result in results:
            mark_words = result['word_counts']['Mark']
            scott_words = result['word_counts']['Scott']
            mark_time = result['speaking_time_seconds']['Mark']
            scott_time = result['speaking_time_seconds']['Scott']
            mark_segments = result['segment_counts']['Mark']
            scott_segments = result['segment_counts']['Scott']
            
            total_words = mark_words + scott_words
            mark_percentage = (mark_words / total_words * 100) if total_words > 0 else 0
            scott_percentage = (scott_words / total_words * 100) if total_words > 0 else 0
            
            winner = 'Scott' if scott_words > mark_words else 'Mark'
            word_diff = abs(scott_words - mark_words)
            
            writer.writerow({
                'Episode': result['file'],
                'Mark_Words': mark_words,
                'Scott_Words': scott_words,
                'Mark_Time_Seconds': mark_time,
                'Scott_Time_Seconds': scott_time,
                'Mark_Time_Formatted': analyzer.format_time(mark_time),
                'Scott_Time_Formatted': analyzer.format_time(scott_time),
                'Mark_Segments': mark_segments,
                'Scott_Segments': scott_segments,
                'Total_Words': total_words,
                'Mark_Word_Percentage': round(mark_percentage, 1),
                'Scott_Word_Percentage': round(scott_percentage, 1),
                'Winner_by_Words': winner,
                'Word_Difference': word_diff
            })
    
    print(f"CSV report generated: {output_file}")


if __name__ == '__main__':
    output_file = sys.argv[1] if len(sys.argv) > 1 else "transcript_analysis_report.csv"
    generate_csv_report(output_file)
