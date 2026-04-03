#!/usr/bin/env python3
"""
Refresh the full-show analysis from the public YouTube playlist.

This is a local-first workflow:
1. Download English auto-captions for the playlist
2. Convert them into speaker-labeled TXT transcripts
3. Regenerate the existing analysis artifacts

Speaker inference is heuristic. YouTube captions usually mark turn changes with `>>`,
but they do not reliably name Mark vs Scott. This script alternates speaker turns,
uses direct-address clues such as "Mark, ..." and "Scott, ...", and supports local
manual overrides in transcripts\\speaker_overrides.json for episodes that need review.
"""

import argparse
import csv
import html
import json
import re
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional, Tuple


DEFAULT_PLAYLIST_URL = "https://www.youtube.com/playlist?list=PL0M0zPgJ3HSf4XZvYgZPUXgSrfzBN26pf"
PROJECT_ROOT = Path(__file__).resolve().parent
TRANSCRIPTS_DIR = PROJECT_ROOT / "transcripts"
RAW_CAPTIONS_DIR = TRANSCRIPTS_DIR / "raw"
OVERRIDES_PATH = TRANSCRIPTS_DIR / "speaker_overrides.json"
MANIFEST_PATH = TRANSCRIPTS_DIR / "episode_manifest.json"
REVIEW_PATH = TRANSCRIPTS_DIR / "speaker_review.csv"

TIMESTAMP_RE = re.compile(r"^\d{2}:\d{2}:\d{2}\.\d+\s+-->\s+\d{2}:\d{2}:\d{2}\.\d+")


@dataclass
class EpisodeArtifact:
    """Tracks the generated files and inference details for an episode."""

    video_id: str
    title: str
    transcript_path: Path
    caption_path: Path
    speaker_map: Dict[str, str]
    confidence: str
    reason: str
    segment_count: int


@dataclass
class CaptionCue:
    """A single timestamped caption update from a VTT file."""

    start_seconds: float
    end_seconds: float
    text: str
    has_speaker_marker: bool = False


def run_command(command: List[str], cwd: Optional[Path] = None) -> str:
    """Run a subprocess and return stdout or raise a readable error."""
    result = subprocess.run(
        command,
        cwd=str(cwd) if cwd else None,
        capture_output=True,
        text=True,
    )

    if result.returncode != 0:
        stderr = result.stderr.strip() or result.stdout.strip()
        raise RuntimeError(f"Command failed ({result.returncode}): {' '.join(command)}\n{stderr}")

    return result.stdout


def ensure_dependencies() -> None:
    """Verify yt-dlp is available in the current Python environment."""
    try:
        run_command([sys.executable, "-m", "yt_dlp", "--version"])
    except Exception as exc:
        raise RuntimeError(
            "yt-dlp is required for the YouTube refresh workflow. "
            "Install it with: python -m pip install yt-dlp"
        ) from exc


def sanitize_filename(name: str) -> str:
    """Make a title safe for use as a Windows filename."""
    sanitized = re.sub(r'[<>:"/\\\\|?*]', "", name)
    sanitized = re.sub(r"\s+", " ", sanitized).strip().rstrip(".")
    return sanitized[:140] or "episode"


def normalize_episode_title(title: str) -> str:
    """Shorten playlist titles into stable transcript filenames."""
    normalized = title.strip()
    match = re.match(r"^EPISODE\s+(\d+)\s*-\s*(.+)$", normalized, re.IGNORECASE)
    if match:
        normalized = f"EP{int(match.group(1))} - {match.group(2).strip()}"

    normalized = re.sub(
        r"^(EP\d+\s*-\s*)Scott\s*&\s*Mark Learn To\.\.\.?",
        r"\1",
        normalized,
        flags=re.IGNORECASE,
    )
    normalized = re.sub(
        r"^(EP\d+\s*-\s*)Scott\s+and\s+Mark Learn To\.\.\.?",
        r"\1",
        normalized,
        flags=re.IGNORECASE,
    )

    prefixes = [
        "Scott & Mark Learn To...",
        "Scott and Mark Learn To...",
        "Scott & Mark learn to",
        "Scott and Mark learn to",
    ]
    for prefix in prefixes:
        if normalized.lower().startswith(prefix.lower()):
            normalized = normalized[len(prefix):].strip(" -.:")
            break

    normalized = normalized.replace("…", "...").strip()
    return normalized or title.strip()


def fetch_playlist_entries(playlist_url: str, playlist_end: Optional[int]) -> List[Dict[str, str]]:
    """List playlist videos using yt-dlp's flat-playlist output."""
    command = [sys.executable, "-m", "yt_dlp", "--flat-playlist", "--dump-json"]
    if playlist_end:
        command.extend(["--playlist-end", str(playlist_end)])
    command.append(playlist_url)

    stdout = run_command(command, cwd=PROJECT_ROOT)
    entries = []
    for line in stdout.splitlines():
        line = line.strip()
        if not line:
            continue
        item = json.loads(line)
        entries.append(
            {
                "id": item["id"],
                "title": normalize_episode_title(item.get("title", item["id"])),
                "original_title": item.get("title", item["id"]),
            }
        )
    return entries


def find_caption_file(stem: str) -> Optional[Path]:
    """Prefer en-orig captions, then fall back to en captions."""
    for suffix in (".en-orig.vtt", ".en.vtt"):
        candidate = RAW_CAPTIONS_DIR / f"{stem}{suffix}"
        if candidate.exists():
            return candidate
    return None


def download_caption(video_id: str, title: str, force: bool) -> Path:
    """Download the English automatic caption file for a video."""
    RAW_CAPTIONS_DIR.mkdir(parents=True, exist_ok=True)
    safe_title = sanitize_filename(title)
    stem = f"{safe_title} [{video_id}]"

    existing = find_caption_file(stem)
    if existing and not force:
        return existing

    command = [
        sys.executable,
        "-m",
        "yt_dlp",
        "--skip-download",
        "--write-auto-sub",
        "--sub-langs",
        "en-orig,en",
        "--sub-format",
        "vtt",
        "-o",
        str(RAW_CAPTIONS_DIR / f"{stem}.%(ext)s"),
        f"https://www.youtube.com/watch?v={video_id}",
    ]
    run_command(command, cwd=PROJECT_ROOT)

    caption_path = find_caption_file(stem)
    if not caption_path:
        raise RuntimeError(f"Could not locate a downloaded caption file for {title} ({video_id})")
    return caption_path


def clean_caption_line(line: str) -> str:
    """Strip HTML timing spans and normalize spacing."""
    cleaned = html.unescape(line)
    cleaned = re.sub(r"<[^>]+>", "", cleaned)
    cleaned = cleaned.replace("\xa0", " ")
    cleaned = cleaned.replace("&nbsp;", " ")
    cleaned = re.sub(r"\s+", " ", cleaned).strip()
    return cleaned


def split_turn_markers(text: str) -> List[Tuple[bool, str]]:
    """Split a caption cue into speaker-change chunks."""
    parts = re.split(r"(?=>>)", text)
    results = []
    for part in parts:
        part = part.strip()
        if not part:
            continue
        speaker_change = part.startswith(">>")
        if speaker_change:
            part = part.lstrip(">").strip()
        results.append((speaker_change, part))
    return results


def append_incremental_text(existing: str, new_text: str) -> str:
    """Merge progressive caption fragments into a single readable utterance."""
    if not existing:
        return new_text
    if not new_text:
        return existing
    if new_text == existing:
        return existing
    if new_text.startswith(existing):
        return new_text
    if existing.startswith(new_text) or existing.endswith(new_text):
        return existing

    existing_words = existing.split()
    new_words = new_text.split()
    max_overlap = min(len(existing_words), len(new_words))

    for overlap_size in range(max_overlap, 0, -1):
        if existing_words[-overlap_size:] == new_words[:overlap_size]:
            merged_words = existing_words + new_words[overlap_size:]
            return " ".join(merged_words)

    if new_text in existing:
        return existing

    return f"{existing} {new_text}".strip()


def extract_incremental_text(previous_text: str, current_text: str) -> str:
    """Keep only the new words added by the next on-screen caption state."""
    if not previous_text:
        return current_text
    if current_text == previous_text:
        return ""
    if current_text.startswith(previous_text):
        return current_text[len(previous_text):].strip()

    previous_words = previous_text.split()
    current_words = current_text.split()
    max_overlap = min(len(previous_words), len(current_words))

    for overlap_size in range(max_overlap, 0, -1):
        if previous_words[-overlap_size:] == current_words[:overlap_size]:
            return " ".join(current_words[overlap_size:]).strip()

    return current_text


def parse_timecode(value: str) -> float:
    """Convert a VTT timecode into seconds."""
    hours, minutes, seconds = value.split(":")
    return (int(hours) * 3600) + (int(minutes) * 60) + float(seconds)


def split_long_turn(turn: str, target_words: int = 38) -> List[str]:
    """Break a long monologue into smaller sentence groups."""
    sentences = [
        sentence.strip()
        for sentence in re.split(r"(?<=[\.\?\!])\s+(?=[A-Z\"'])", turn)
        if sentence.strip()
    ]

    if len(sentences) <= 1:
        words = turn.split()
        if len(words) <= target_words:
            return [turn]

        chunks = []
        for start in range(0, len(words), target_words):
            chunks.append(" ".join(words[start:start + target_words]))
        return chunks

    grouped: List[str] = []
    current_group: List[str] = []
    current_word_count = 0

    for sentence in sentences:
        sentence_words = len(sentence.split())
        if current_group and current_word_count + sentence_words > target_words:
            grouped.append(" ".join(current_group).strip())
            current_group = [sentence]
            current_word_count = sentence_words
        else:
            current_group.append(sentence)
            current_word_count += sentence_words

    if current_group:
        grouped.append(" ".join(current_group).strip())

    return grouped


def build_heuristic_turns(cues: List[CaptionCue]) -> List[str]:
    """Infer conversational turns when YouTube captions do not mark speaker changes."""
    turns: List[str] = []
    current_parts: List[str] = []
    current_words = 0
    previous_end: Optional[float] = None

    for cue in cues:
        text = re.sub(r"\s+", " ", cue.text).strip()
        if not text:
            continue

        start_new_turn = False
        if current_parts:
            gap = cue.start_seconds - (previous_end or cue.start_seconds)
            previous_text = current_parts[-1]

            if gap >= 1.2:
                start_new_turn = True
            elif re.search(r'[\.\?\!]["\']?$', previous_text):
                start_new_turn = True
            elif current_words >= 24 and re.match(r"^(yeah|yes|no|well|so|okay|all right|right|uh|huh|interesting|exactly|sure|absolutely)\b", text, re.IGNORECASE):
                start_new_turn = True
            elif current_words >= 40 and text[:1].isupper():
                start_new_turn = True

        if start_new_turn and current_parts:
            turns.extend(split_long_turn(" ".join(current_parts).strip()))
            current_parts = [text]
            current_words = len(text.split())
        else:
            current_parts.append(text)
            current_words += len(text.split())

        previous_end = cue.end_seconds

    if current_parts:
        turns.extend(split_long_turn(" ".join(current_parts).strip()))

    return [turn for turn in turns if turn]


def parse_segments_from_vtt(caption_path: Path) -> List[str]:
    """Extract speaker turns from a YouTube VTT file."""
    raw_text = caption_path.read_text(encoding="utf-8")
    blocks: List[List[str]] = []
    current_block: List[str] = []

    for raw_line in raw_text.splitlines():
        line = raw_line.strip()
        if not line:
            if current_block:
                blocks.append(current_block)
                current_block = []
            continue
        current_block.append(line)

    if current_block:
        blocks.append(current_block)

    cues: List[CaptionCue] = []
    previous_display = ""

    for block in blocks:
        if not block:
            continue
        if block[0] in {"WEBVTT", "Kind: captions"} or block[0].startswith("Language:"):
            continue

        start_seconds = 0.0
        end_seconds = 0.0
        text_lines = block
        if TIMESTAMP_RE.match(block[0]):
            time_match = re.match(r"^(\d{2}:\d{2}:\d{2}\.\d+)\s+-->\s+(\d{2}:\d{2}:\d{2}\.\d+)", block[0])
            if time_match:
                start_seconds = parse_timecode(time_match.group(1))
                end_seconds = parse_timecode(time_match.group(2))
            text_lines = block[1:]

        cleaned_lines = [clean_caption_line(line) for line in text_lines if clean_caption_line(line)]
        if not cleaned_lines:
            continue

        display_text = " ".join(cleaned_lines).strip()
        if not display_text:
            continue

        delta = extract_incremental_text(previous_display, display_text)
        previous_display = display_text
        if delta:
            cues.append(
                CaptionCue(
                    start_seconds=start_seconds,
                    end_seconds=end_seconds,
                    text=delta,
                    has_speaker_marker=">>" in delta,
                )
            )

    if not cues:
        return []

    if not any(cue.has_speaker_marker for cue in cues):
        return build_heuristic_turns(cues)

    segments: List[str] = []
    current_segment = ""

    for cue in cues:
        cue_text = re.sub(r"\s+", " ", cue.text).strip()
        if not cue_text:
            continue

        for speaker_change, text in split_turn_markers(cue_text):
            if not text:
                continue

            if speaker_change and current_segment:
                segments.append(current_segment.strip())
                current_segment = text
            else:
                current_segment = append_incremental_text(current_segment, text)

    if current_segment:
        segments.append(current_segment.strip())

    cleaned_segments = []
    for segment in segments:
        normalized = re.sub(r"\s+", " ", segment).strip()
        if normalized and (not cleaned_segments or normalized != cleaned_segments[-1]):
            cleaned_segments.append(normalized)

    return cleaned_segments


def load_overrides() -> Dict[str, Dict[str, str]]:
    """Load local speaker overrides if present."""
    if not OVERRIDES_PATH.exists():
        OVERRIDES_PATH.parent.mkdir(parents=True, exist_ok=True)
        OVERRIDES_PATH.write_text("{}\n", encoding="utf-8")
        return {}

    return json.loads(OVERRIDES_PATH.read_text(encoding="utf-8"))


def infer_speaker_map(video_id: str, title: str, segments: List[str], overrides: Dict[str, Dict[str, str]]) -> Tuple[Dict[str, str], str, str]:
    """Map alternating speaker slots A/B to Mark/Scott."""
    override = overrides.get(video_id) or overrides.get(title)
    if override and override.get("A") and override.get("B"):
        return {"A": override["A"], "B": override["B"]}, "override", "Applied local speaker override"

    votes = {
        "A": {"Mark": 0, "Scott": 0},
        "B": {"Mark": 0, "Scott": 0},
    }
    reasons: List[str] = []

    for index, segment in enumerate(segments):
        slot = "A" if index % 2 == 0 else "B"
        lowered = segment.lower()

        if re.match(r"^(hey\s+)?mark\b[,\?\!:\- ]", lowered):
            votes[slot]["Scott"] += 3
            reasons.append(f"{slot} addressed Mark")
        if re.match(r"^(hey\s+)?scott\b[,\?\!:\- ]", lowered):
            votes[slot]["Mark"] += 3
            reasons.append(f"{slot} addressed Scott")
        if re.search(r"\bi[' ]?m\s+mark\b|\bthis is mark\b", lowered):
            votes[slot]["Mark"] += 5
            reasons.append(f"{slot} self-identified as Mark")
        if re.search(r"\bi[' ]?m\s+scott\b|\bthis is scott\b", lowered):
            votes[slot]["Scott"] += 5
            reasons.append(f"{slot} self-identified as Scott")

    mapping: Dict[str, str]
    if votes["A"]["Mark"] != votes["A"]["Scott"]:
        mapping = {"A": "Mark", "B": "Scott"} if votes["A"]["Mark"] > votes["A"]["Scott"] else {"A": "Scott", "B": "Mark"}
    elif votes["B"]["Mark"] != votes["B"]["Scott"]:
        mapping = {"B": "Mark", "A": "Scott"} if votes["B"]["Mark"] > votes["B"]["Scott"] else {"B": "Scott", "A": "Mark"}
    else:
        mapping = {"A": "Scott", "B": "Mark"}

    total_votes = sum(sum(host_votes.values()) for host_votes in votes.values())
    if total_votes >= 6:
        confidence = "high"
    elif total_votes >= 3:
        confidence = "medium"
    else:
        confidence = "low"

    reason = "; ".join(sorted(set(reasons))) if reasons else "Defaulted to alternating two-host heuristic"
    return mapping, confidence, reason


def write_transcript(title: str, segments: List[str], speaker_map: Dict[str, str]) -> Path:
    """Write a speaker-labeled TXT transcript that the analyzer can consume."""
    TRANSCRIPTS_DIR.mkdir(parents=True, exist_ok=True)
    transcript_path = TRANSCRIPTS_DIR / f"{sanitize_filename(title)}.txt"

    lines = []
    for index, segment in enumerate(segments):
        speaker_slot = "A" if index % 2 == 0 else "B"
        speaker_name = speaker_map[speaker_slot]
        lines.append(f"{speaker_name}: {segment}")

    transcript_path.write_text("\n\n".join(lines) + "\n", encoding="utf-8")
    return transcript_path


def write_review_files(artifacts: List[EpisodeArtifact]) -> None:
    """Persist a manifest and review CSV for manual spot checks."""
    manifest = [
        {
            "video_id": artifact.video_id,
            "title": artifact.title,
            "caption_file": str(artifact.caption_path),
            "transcript_file": str(artifact.transcript_path),
            "speaker_map": artifact.speaker_map,
            "confidence": artifact.confidence,
            "reason": artifact.reason,
            "segment_count": artifact.segment_count,
        }
        for artifact in artifacts
    ]
    MANIFEST_PATH.write_text(json.dumps(manifest, indent=2), encoding="utf-8")

    with REVIEW_PATH.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=[
                "title",
                "video_id",
                "speaker_a",
                "speaker_b",
                "confidence",
                "reason",
                "segment_count",
                "transcript_file",
            ],
        )
        writer.writeheader()
        for artifact in artifacts:
            writer.writerow(
                {
                    "title": artifact.title,
                    "video_id": artifact.video_id,
                    "speaker_a": artifact.speaker_map["A"],
                    "speaker_b": artifact.speaker_map["B"],
                    "confidence": artifact.confidence,
                    "reason": artifact.reason,
                    "segment_count": artifact.segment_count,
                    "transcript_file": str(artifact.transcript_path),
                }
            )


def refresh_playlist(playlist_url: str, playlist_end: Optional[int], force: bool) -> List[EpisodeArtifact]:
    """Download captions, infer speakers, and generate local transcripts."""
    ensure_dependencies()
    entries = fetch_playlist_entries(playlist_url, playlist_end)
    overrides = load_overrides()
    TRANSCRIPTS_DIR.mkdir(parents=True, exist_ok=True)

    for existing_transcript in TRANSCRIPTS_DIR.glob("*.txt"):
        existing_transcript.unlink()

    artifacts: List[EpisodeArtifact] = []
    for entry in entries:
        caption_path = download_caption(entry["id"], entry["title"], force=force)
        segments = parse_segments_from_vtt(caption_path)
        speaker_map, confidence, reason = infer_speaker_map(entry["id"], entry["title"], segments, overrides)
        transcript_path = write_transcript(entry["title"], segments, speaker_map)

        artifacts.append(
            EpisodeArtifact(
                video_id=entry["id"],
                title=entry["title"],
                transcript_path=transcript_path,
                caption_path=caption_path,
                speaker_map=speaker_map,
                confidence=confidence,
                reason=reason,
                segment_count=len(segments),
            )
        )

    write_review_files(artifacts)
    return artifacts


def run_analysis_scripts() -> None:
    """Regenerate the existing repo outputs from the fresh transcript set."""
    for script_name in (
        "quick_summary.py",
        "generate_csv_report.py",
        "generate_json_data.py",
        "visualize_talk_time.py",
    ):
        print(f"\n=== Running {script_name} ===")
        subprocess.run([sys.executable, script_name], cwd=str(PROJECT_ROOT), check=True)


def main() -> None:
    parser = argparse.ArgumentParser(description="Refresh the Mark/Scott analysis from the public YouTube playlist.")
    parser.add_argument("--playlist-url", default=DEFAULT_PLAYLIST_URL, help="YouTube playlist URL for the show")
    parser.add_argument("--playlist-end", type=int, default=None, help="Only process the first N playlist items")
    parser.add_argument("--force", action="store_true", help="Re-download caption files even if they already exist")
    parser.add_argument("--run-analysis", action="store_true", help="Regenerate quick summary, CSV, and JSON outputs after refresh")
    args = parser.parse_args()

    artifacts = refresh_playlist(args.playlist_url, args.playlist_end, force=args.force)

    low_confidence = sum(1 for artifact in artifacts if artifact.confidence == "low")
    print(f"Generated {len(artifacts)} local transcripts in {TRANSCRIPTS_DIR}")
    print(f"Review summary saved to {REVIEW_PATH}")
    if low_confidence:
        print(f"{low_confidence} episodes used the default two-host heuristic and may need speaker overrides.")

    if args.run_analysis:
        run_analysis_scripts()


if __name__ == "__main__":
    main()
