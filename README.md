# Podcast Transcript Analyzer

A Python command-line tool to analyze podcast transcripts from speaker-labeled DOCX/TXT files and refresh the whole show from public YouTube captions to determine who talks more between Mark and Scott.

## Features

- **Word Count Analysis**: Counts total words spoken by each speaker
- **Speaking Time Estimation**: Estimates speaking time based on word count and average speech rate
- **Segment Analysis**: Counts number of speaking segments per person
- **Comprehensive Reports**: Shows per-file and overall statistics
- **Flexible Input**: Analyze specific files or all supported transcript files in the repo/transcripts folder
- **YouTube Refresh Workflow**: Pull the full playlist locally with `yt-dlp` and regenerate the reports
- **Speaker Review Loop**: Flag low-confidence episodes and support local overrides without code changes
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

### Refresh from the full YouTube show playlist:
```bash
python3 refresh_from_youtube.py --run-analysis
```
This downloads the latest English auto-captions for the playlist, converts them into
local speaker-labeled `.txt` transcripts in `transcripts\`, and regenerates the summary,
CSV, JSON, and PNG chart outputs.

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
# Refresh the data first
python3 refresh_from_youtube.py --run-analysis

# Serve the folder locally so the page can fetch transcript_data.json
python -m http.server 8765

# Then open:
# http://127.0.0.1:8765/interactive_analysis.html
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

## Transcript Source and Speaker Attribution

There are now **two supported input modes**:

1. **Direct labeled transcripts**: private `.docx` or `.txt` files with each paragraph prefixed by
   `Mark:` or `Scott:`
2. **Whole-show YouTube refresh**: public auto-captions pulled from the playlist and converted into
   local `.txt` transcripts using a best-effort two-host speaker heuristic

The parser looks for patterns such as:

- `Mark: content`
- `Scott: content`
- `[Mark] content`
- `Scott - content`

Raw YouTube auto-captions do **not** reliably say whether the speaker is Mark or Scott. Some
episodes include speaker-change markers; many do not. The refresh script therefore:

1. Downloads the English caption track for each episode
2. Reconstructs caption deltas from rolling VTT text
3. Splits long unlabeled caption streams into conversation-sized turns using timing gaps, sentence
   boundaries, and short interjection cues
4. Alternates the two-host turns and applies name-based hints such as `Mark, ...` or `Scott, ...`
5. Writes local transcripts and a review file for any episode that still needs manual correction

This is a **local-first heuristic workflow**, not diarization or voice recognition. It passes a
good sniff test after the turn-splitting fix, but manual overrides are still the right tool for
episodes that remain ambiguous.

### Refreshing with the latest YouTube episode

1. Download the latest English auto-captions:

   ```bash
   python -m yt_dlp --skip-download --write-auto-sub --sub-langs en-orig --sub-format vtt "<youtube-url>"
   ```

2. Convert the captions into a private `.docx` or `.txt` transcript with paragraphs prefixed by
   `Mark:` or `Scott:`.
3. Put the transcript in the repository root or `transcripts\`. These files are gitignored on
   purpose.
4. Re-run `python3 quick_summary.py` or regenerate `transcript_data.json` with
   `python3 generate_json_data.py`.

### Whole-show local workflow

For the YouTube-hosted version of the show, use:

```bash
python3 refresh_from_youtube.py --run-analysis
```

What it does:

1. Lists the current playlist episodes with `yt-dlp`
2. Downloads English auto-captions for each episode
3. Reconstructs conversational turns from the rolling VTT caption text
4. Uses a two-host heuristic to map the resulting turns to `Mark` and `Scott`
5. Writes local `.txt` transcripts to `transcripts\`
6. Saves a review file at `transcripts\speaker_review.csv`

For quick iteration while tuning the heuristics, you can limit the run:

```bash
python3 refresh_from_youtube.py --playlist-end 5 --run-analysis
```

If an episode needs manual correction, add an override in `transcripts\speaker_overrides.json`
using either the YouTube video ID or the episode title:

```json
{
  "PQlIZaMyu80": { "A": "Scott", "B": "Mark" }
}
```

This keeps the workflow local and repeatable while making low-confidence speaker inference easy to
fix without editing code.

## How It Works

The analyzer uses several methods to identify speakers and content:

1. **Speaker Detection**: Looks for common patterns like:
   - `Mark: content`
   - `Scott: content` 
   - `[Mark] content`
   - `Mark - content`

2. **YouTube Turn Inference**: When refreshing from the playlist, reconstructs turns from VTT
   captions before assigning them to Mark or Scott

3. **Word Counting**: Counts words in each speaker's segments

4. **Time Estimation**: Uses average speaking rate (150 words/minute) to estimate speaking time

5. **Aggregation**: Combines results across all analyzed files

## Output Format

The tool provides:
- Per-file breakdown showing words, estimated time, and segments for each speaker
- Overall totals with percentages
- Clear summary of who talks more by both word count and time

## Latest Whole-Show Refresh Snapshot

Based on the latest local YouTube refresh of **37 shows**:

**Current result: effectively a toss-up**

- **Mark**: 84,594 words (50.1%) | 9 hours 3 minutes speaking time
- **Scott**: 84,169 words (49.9%) | 8 hours 59 minutes speaking time

**Episode wins**: Scott 20 of 37, Mark 17 of 37

**Important caveat**: these numbers come from the local caption-ingest heuristic. They are much
closer to the human sniff test after fixing the collapsed single-speaker bug, but low-confidence
episodes should still be reviewed through `transcripts\speaker_review.csv` and, if needed,
corrected via `transcripts\speaker_overrides.json`.

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
- `refresh_from_youtube.py` keeps the raw caption files and inferred transcripts local and untracked
- If you only have raw YouTube captions, prefer the local refresh workflow and then review the
  confidence report before trusting the totals
- Speaking time is estimated based on word count (150 words/minute average)
- If actual timestamps are present in transcripts, the tool can be enhanced to use them
- The analyzer is case-insensitive for speaker names
