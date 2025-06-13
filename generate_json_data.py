#!/usr/bin/env python3
"""
Generate JSON data file for the interactive visualization
"""

import json
import re
from pathlib import Path
from transcript_analyzer import TranscriptAnalyzer


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


def generate_json_data():
    """Generate JSON data for the interactive visualization"""
    analyzer = TranscriptAnalyzer()
    
    # Find all .docx files
    current_dir = Path('.')
    file_paths = list(current_dir.glob('*.docx'))
    file_paths = [f for f in file_paths if not f.name.endswith(':sec.endpointdlp')]
    
    if not file_paths:
        print("No DOCX files found.")
        return
    
    print(f"📊 Processing {len(file_paths)} files for interactive visualization...")
    
    # Analyze each file
    data = []
    for file_path in file_paths:
        if file_path.exists() and file_path.suffix.lower() == '.docx':
            result = analyzer.analyze_transcript(file_path)
            if result:
                episode_data = {
                    'episode': result['file'].replace('.docx', ''),
                    'markTime': round(result['speaking_time_seconds']['Mark'] / 60, 1),  # Convert to minutes
                    'scottTime': round(result['speaking_time_seconds']['Scott'] / 60, 1),
                    'markWords': result['word_counts']['Mark'],
                    'scottWords': result['word_counts']['Scott'],
                    'markSegments': result['segment_counts']['Mark'],
                    'scottSegments': result['segment_counts']['Scott'],
                    'episodeNumber': extract_episode_number(result['file'])
                }
                
                # Calculate additional metrics
                episode_data['totalTime'] = episode_data['markTime'] + episode_data['scottTime']
                episode_data['totalWords'] = episode_data['markWords'] + episode_data['scottWords']
                episode_data['markPercentage'] = round((episode_data['markTime'] / episode_data['totalTime']) * 100, 1) if episode_data['totalTime'] > 0 else 0
                episode_data['scottPercentage'] = round((episode_data['scottTime'] / episode_data['totalTime']) * 100, 1) if episode_data['totalTime'] > 0 else 0
                episode_data['timeDifference'] = round(abs(episode_data['scottTime'] - episode_data['markTime']), 1)
                episode_data['winner'] = 'Scott' if episode_data['scottTime'] > episode_data['markTime'] else 'Mark'
                
                data.append(episode_data)
    
    # Sort by episode number
    data.sort(key=lambda x: x['episodeNumber'])
    
    # Write JSON file
    output_file = 'transcript_data.json'
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    
    print(f"✅ JSON data generated: {output_file}")
    
    # Generate summary stats
    total_mark = sum(d['markTime'] for d in data)
    total_scott = sum(d['scottTime'] for d in data)
    total_episodes = len(data)
    scott_wins = sum(1 for d in data if d['winner'] == 'Scott')
    mark_wins = total_episodes - scott_wins
    
    print(f"\n📈 DATA SUMMARY:")
    print(f"   Episodes: {total_episodes}")
    print(f"   Mark:     {total_mark:.1f} minutes ({total_mark/60:.1f} hours)")
    print(f"   Scott:    {total_scott:.1f} minutes ({total_scott/60:.1f} hours)")
    print(f"   Scott wins: {scott_wins}/{total_episodes} episodes ({scott_wins/total_episodes*100:.1f}%)")
    print(f"   Mark wins:  {mark_wins}/{total_episodes} episodes ({mark_wins/total_episodes*100:.1f}%)")
    
    return data


if __name__ == '__main__':
    generate_json_data()
