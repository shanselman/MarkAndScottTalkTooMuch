#!/usr/bin/env python3
"""
Podcast Transcript Analyzer
Analyzes DOCX transcript files to determine speaking time and word count for Mark and Scott
"""

import argparse
import re
import sys
from pathlib import Path
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass
from datetime import datetime, timedelta

try:
    from docx import Document
except ImportError:
    print("Error: python-docx library not found. Please install it with:")
    print("pip install python-docx")
    sys.exit(1)


def find_transcript_files(directory: Optional[Path] = None) -> List[Path]:
    """Find private speaker-labeled transcript files in the working directory."""
    search_dir = directory or Path('.')
    transcript_files = []
    patterns_by_dir = {
        search_dir: ('*.docx',),
        search_dir / 'transcripts': ('*.docx', '*.txt'),
    }

    for candidate_dir, patterns in patterns_by_dir.items():
        if not candidate_dir.exists():
            continue

        for pattern in patterns:
            transcript_files.extend(
                file_path for file_path in candidate_dir.glob(pattern)
                if file_path.is_file() and not file_path.name.endswith(':sec.endpointdlp')
            )

    return sorted(set(transcript_files))


def print_transcript_setup_help():
    """Explain how the analyzer expects transcripts to be prepared."""
    print("No transcript files found to analyze.")
    print("This project expects private, speaker-labeled DOCX or TXT transcripts")
    print("in the repo root or a local transcripts/ folder.")
    print("Raw YouTube auto-captions usually mark speaker changes with '>>' but do not")
    print("reliably identify whether the speaker is Mark or Scott.")
    print("Prepare transcripts with lines such as 'Mark: ...' or 'Scott: ...' and rerun.")
    print('To fetch the latest captions first, use: python -m yt_dlp --skip-download')
    print('--write-auto-sub --sub-langs en-orig --sub-format vtt "<youtube-url>"')


@dataclass
class SpeakingSegment:
    """Represents a speaking segment with speaker, content, start and end times"""
    speaker: str
    content: str
    start_time: Optional[str] = None
    end_time: Optional[str] = None
    word_count: int = 0


class TranscriptAnalyzer:
    """Analyzes podcast transcripts to extract speaking statistics"""
    
    def __init__(self):
        self.speakers = {'mark': 'Mark', 'scott': 'Scott'}
        # Common patterns for speaker identification
        self.speaker_patterns = [
            r'^(Mark|Scott):\s*(.+)$',  # "Mark: content"
            r'^(Mark|Scott)\s+(.+)$',   # "Mark content"
            r'^\[(Mark|Scott)\]\s*(.+)$',  # "[Mark] content"
            r'^(Mark|Scott)\s*-\s*(.+)$',  # "Mark - content"
        ]
        # Time patterns (various formats)
        self.time_patterns = [
            r'(\d{1,2}:\d{2}:\d{2})',  # HH:MM:SS
            r'(\d{1,2}:\d{2})',        # MM:SS or HH:MM
            r'\[(\d{1,2}:\d{2}:\d{2})\]',  # [HH:MM:SS]
            r'\[(\d{1,2}:\d{2})\]',        # [MM:SS]
        ]
    
    def read_docx(self, file_path: Path) -> str:
        """Read text content from a DOCX file"""
        try:
            doc = Document(file_path)
            full_text = []
            for paragraph in doc.paragraphs:
                if paragraph.text.strip():
                    full_text.append(paragraph.text.strip())
            return '\n'.join(full_text)
        except Exception as e:
            print(f"Error reading {file_path}: {e}")
            return ""

    def read_text_file(self, file_path: Path) -> str:
        """Read text content from a UTF-8 transcript file."""
        try:
            return file_path.read_text(encoding='utf-8')
        except UnicodeDecodeError:
            return file_path.read_text(encoding='utf-8-sig')
        except Exception as e:
            print(f"Error reading {file_path}: {e}")
            return ""

    def read_transcript(self, file_path: Path) -> str:
        """Read transcript content from supported file types."""
        suffix = file_path.suffix.lower()
        if suffix == '.docx':
            return self.read_docx(file_path)
        if suffix == '.txt':
            return self.read_text_file(file_path)

        print(f"Unsupported transcript format: {file_path}")
        return ""
    
    def extract_timestamps(self, text: str) -> List[str]:
        """Extract timestamps from text"""
        timestamps = []
        for pattern in self.time_patterns:
            matches = re.findall(pattern, text, re.IGNORECASE)
            timestamps.extend(matches)
        return timestamps
    
    def parse_time_to_seconds(self, time_str: str) -> int:
        """Convert time string to seconds"""
        try:
            parts = time_str.split(':')
            if len(parts) == 3:  # HH:MM:SS
                hours, minutes, seconds = map(int, parts)
                return hours * 3600 + minutes * 60 + seconds
            elif len(parts) == 2:  # MM:SS or HH:MM
                # Assume MM:SS if value is reasonable for minutes
                first, second = map(int, parts)
                if first > 59:  # Likely HH:MM format
                    return first * 3600 + second * 60
                else:  # MM:SS format
                    return first * 60 + second
            else:
                return 0
        except ValueError:
            return 0
    
    def identify_speaker_segments(self, text: str) -> List[SpeakingSegment]:
        """Parse transcript text and identify speaking segments"""
        segments = []
        lines = text.split('\n')
        current_speaker = None
        current_content = []
        
        for line in lines:
            line = line.strip()
            if not line:
                continue
            
            # Check for speaker identification patterns
            speaker_found = False
            for pattern in self.speaker_patterns:
                match = re.match(pattern, line, re.IGNORECASE)
                if match:
                    # Save previous segment if exists
                    if current_speaker and current_content:
                        content = ' '.join(current_content)
                        segments.append(SpeakingSegment(
                            speaker=current_speaker,
                            content=content,
                            word_count=len(content.split())
                        ))
                    
                    # Start new segment
                    current_speaker = match.group(1).title()
                    current_content = [match.group(2).strip()]
                    speaker_found = True
                    break
            
            if not speaker_found:
                # If no speaker pattern found, add to current speaker's content
                if current_speaker:
                    current_content.append(line)
                else:
                    # Try to infer speaker from context or skip
                    continue
        
        # Add final segment
        if current_speaker and current_content:
            content = ' '.join(current_content)
            segments.append(SpeakingSegment(
                speaker=current_speaker,
                content=content,
                word_count=len(content.split())
            ))
        
        return segments
    
    def calculate_speaking_time(self, segments: List[SpeakingSegment], total_duration: int = None) -> Dict[str, int]:
        """Calculate approximate speaking time based on word count and speech rate"""
        # Average speaking rate: ~150 words per minute
        words_per_minute = 150
        
        speaking_time = {'Mark': 0, 'Scott': 0}
        
        for segment in segments:
            if segment.speaker in speaking_time:
                # Convert word count to approximate time in seconds
                time_seconds = (segment.word_count / words_per_minute) * 60
                speaking_time[segment.speaker] += int(time_seconds)
        
        return speaking_time
    
    def analyze_transcript(self, file_path: Path) -> Dict:
        """Analyze a single transcript file"""
        print(f"Analyzing: {file_path.name}")
        
        # Read the document
        text = self.read_transcript(file_path)
        if not text:
            return None
        
        # Extract speaking segments
        segments = self.identify_speaker_segments(text)
        
        if not segments:
            print(f"Warning: No speaking segments found in {file_path.name}")
            return None
        
        # Calculate statistics
        word_counts = {'Mark': 0, 'Scott': 0}
        segment_counts = {'Mark': 0, 'Scott': 0}
        
        for segment in segments:
            if segment.speaker in word_counts:
                word_counts[segment.speaker] += segment.word_count
                segment_counts[segment.speaker] += 1
        
        # Calculate speaking time
        speaking_time = self.calculate_speaking_time(segments)
        
        return {
            'file': file_path.name,
            'total_segments': len(segments),
            'word_counts': word_counts,
            'segment_counts': segment_counts,
            'speaking_time_seconds': speaking_time,
            'segments': segments
        }
    
    def format_time(self, seconds: int) -> str:
        """Format seconds as HH:MM:SS"""
        hours = seconds // 3600
        minutes = (seconds % 3600) // 60
        secs = seconds % 60
        return f"{hours:02d}:{minutes:02d}:{secs:02d}"
    
    def print_analysis_results(self, results: List[Dict]):
        """Print comprehensive analysis results"""
        if not results:
            print("No valid transcript files found.")
            return
        
        # Aggregate totals
        total_words = {'Mark': 0, 'Scott': 0}
        total_time = {'Mark': 0, 'Scott': 0}
        total_segments = {'Mark': 0, 'Scott': 0}
        
        print("\n" + "="*60)
        print("PODCAST TRANSCRIPT ANALYSIS RESULTS")
        print("="*60)
        
        # Per-file results
        for result in results:
            print(f"\nFile: {result['file']}")
            print("-" * 40)
            
            for speaker in ['Mark', 'Scott']:
                words = result['word_counts'][speaker]
                time_sec = result['speaking_time_seconds'][speaker]
                segments = result['segment_counts'][speaker]
                
                print(f"{speaker:5}: {words:4} words | {self.format_time(time_sec)} | {segments} segments")
                
                # Add to totals
                total_words[speaker] += words
                total_time[speaker] += time_sec
                total_segments[speaker] += segments
        
        # Overall totals
        print("\n" + "="*60)
        print("OVERALL TOTALS")
        print("="*60)
        
        total_all_words = sum(total_words.values())
        total_all_time = sum(total_time.values())
        
        for speaker in ['Mark', 'Scott']:
            words = total_words[speaker]
            time_sec = total_time[speaker]
            segments = total_segments[speaker]
            
            word_percentage = (words / total_all_words * 100) if total_all_words > 0 else 0
            time_percentage = (time_sec / total_all_time * 100) if total_all_time > 0 else 0
            
            print(f"\n{speaker}:")
            print(f"  Words:    {words:5} ({word_percentage:5.1f}%)")
            print(f"  Time:     {self.format_time(time_sec)} ({time_percentage:5.1f}%)")
            print(f"  Segments: {segments:5}")
        
        print(f"\nTotal words: {total_all_words}")
        print(f"Total time:  {self.format_time(total_all_time)}")
        
        # Determine who talks more
        if total_words['Mark'] > total_words['Scott']:
            word_winner = 'Mark'
            word_diff = total_words['Mark'] - total_words['Scott']
        else:
            word_winner = 'Scott'
            word_diff = total_words['Scott'] - total_words['Mark']
        
        if total_time['Mark'] > total_time['Scott']:
            time_winner = 'Mark'
            time_diff = total_time['Mark'] - total_time['Scott']
        else:
            time_winner = 'Scott'
            time_diff = total_time['Scott'] - total_time['Mark']
        
        print("\n" + "="*60)
        print("WHO TALKS MORE?")
        print("="*60)
        print(f"By word count: {word_winner} (+{word_diff} words)")
        print(f"By time:       {time_winner} (+{self.format_time(time_diff)})")


def main():
    """Main function to run the transcript analyzer"""
    parser = argparse.ArgumentParser(
        description="Analyze podcast transcripts to determine who talks more"
    )
    parser.add_argument(
        'files',
        nargs='*',
        help='Transcript files to analyze (DOCX/TXT). If none are specified, analyzes local transcript files automatically.'
    )
    parser.add_argument(
        '--verbose', '-v',
        action='store_true',
        help='Show verbose output including individual segments'
    )
    
    args = parser.parse_args()
    
    analyzer = TranscriptAnalyzer()
    
    # Determine files to analyze
    if args.files:
        file_paths = [Path(f) for f in args.files]
    else:
        file_paths = find_transcript_files()
    
    if not file_paths:
        print_transcript_setup_help()
        return
    
    print(f"Found {len(file_paths)} transcript files to analyze...")
    
    # Analyze each file
    results = []
    for file_path in file_paths:
        if file_path.exists() and file_path.suffix.lower() in {'.docx', '.txt'}:
            result = analyzer.analyze_transcript(file_path)
            if result:
                results.append(result)
        else:
            print(f"Warning: {file_path} does not exist or is not a supported transcript file")
    
    # Print results
    analyzer.print_analysis_results(results)


if __name__ == '__main__':
    main()
