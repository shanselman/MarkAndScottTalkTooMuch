# Podcast Transcript Analyzer

A Python command-line tool to analyze podcast transcripts from DOCX files and determine who talks more between Mark and Scott.

## Features

- **Word Count Analysis**: Counts total words spoken by each speaker
- **Speaking Time Estimation**: Estimates speaking time based on word count and average speech rate
- **Segment Analysis**: Counts number of speaking segments per person
- **Comprehensive Reports**: Shows per-file and overall statistics
- **Flexible Input**: Analyze specific files or all DOCX files in directory
- **Interactive D3.js Visualization**: NY Times-style web interface with filtering, sorting, and animations
- **Visualization Charts**: Beautiful bar charts showing episode-by-episode and total speaking time
- **CSV Export**: Spreadsheet-ready data for further analysis

## Installation

1. Make sure you have Python 3.7+ installed
2. Install the required dependencies:

```bash
pip install -r requirements.txt
```

**Note**: For visualizations, you'll need matplotlib and numpy (included in requirements.txt)

## Usage

### Quick Summary (Recommended):
```bash
python3 quick_summary.py
```
Shows a concise overview with key statistics and who talks more overall.

### Detailed Analysis - All files:
```bash
python3 transcript_analyzer.py
```

### Detailed Analysis - Specific files:
```bash
python3 transcript_analyzer.py "EP1 - Introduction.docx" "EP2 - Follow-up.docx"
```

### Generate CSV Report:
```bash
python3 generate_csv_report.py
```
Creates a CSV file with detailed episode-by-episode statistics.

### Generate Visual Charts:
```bash
python3 visualize_talk_time.py
```
Creates beautiful charts showing:
1. Episode-by-episode speaking time comparison (bar chart)
2. Total accumulated speaking time per speaker
Saves as `talk_time_analysis.png`

### Interactive Web Visualization:
```bash
# Generate data for interactive charts
python3 generate_json_data.py

# Open interactive_analysis.html in your browser
open interactive_analysis.html
```
Features NY Times-style interactive D3.js visualization with:
- Multiple view types (episodes, totals, percentages, timeline)
- Real-time filtering and sorting
- Smooth animations and hover tooltips
- Responsive design for all devices
- Client-side only (no server required)

### Verbose output (shows individual segments):
```bash
python3 transcript_analyzer.py --verbose
```

## How It Works

The analyzer uses several methods to identify speakers and content:

1. **Speaker Detection**: Looks for common patterns like:
   - `Mark: content`
   - `Scott: content` 
   - `[Mark] content`
   - `Mark - content`

2. **Word Counting**: Counts words in each speaker's segments

3. **Time Estimation**: Uses average speaking rate (150 words/minute) to estimate speaking time

4. **Aggregation**: Combines results across all analyzed files

## Output Format

The tool provides:
- Per-file breakdown showing words, estimated time, and segments for each speaker
- Overall totals with percentages
- Clear summary of who talks more by both word count and time

## Your Podcast Analysis Results 🎉

Based on the analysis of 22 episodes:

**🏆 WINNER: SCOTT TALKS MORE!**

- **Scott**: 75,191 words (59.7%) | 8 hours 7 minutes speaking time
- **Mark**: 50,821 words (40.3%) | 5 hours 25 minutes speaking time

**Episode Wins**: Scott dominates 20 out of 22 episodes (90.9%)

**Conclusion**: Scott talks 19.3% more than Mark overall (+24,370 words, +2 hours 41 minutes)

## Sample Output

```
PODCAST TRANSCRIPT ANALYSIS RESULTS
============================================================

File: EP1 - Introduction.docx
----------------------------------------
Mark :  150 words | 00:01:00 | 3 segments
Scott:  200 words | 00:01:20 | 4 segments

============================================================
OVERALL TOTALS
============================================================

Mark:
  Words:     150 ( 42.9%)
  Time:     00:01:00 ( 42.9%)
  Segments:     3

Scott:
  Words:     200 ( 57.1%)
  Time:     00:01:20 ( 57.1%)
  Segments:     4

Total words: 350
Total time:  00:02:20

============================================================
WHO TALKS MORE?
============================================================
By word count: Scott (+50 words)
By time:       Scott (+00:00:20)
```

## Customization

You can modify the script to:
- Add recognition for additional speakers
- Adjust speaking rate estimation
- Change speaker detection patterns
- Add support for timestamps in transcripts

## Notes

- The tool filters out files ending with `:sec.endpointdlp`
- Speaking time is estimated based on word count (150 words/minute average)
- If actual timestamps are present in transcripts, the tool can be enhanced to use them
- The analyzer is case-insensitive for speaker names
