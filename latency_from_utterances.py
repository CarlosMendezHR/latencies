#!/usr/bin/env python3
"""
Calculate latency (response delay) between speakers in audio files
using AssemblyAI speaker diarization.
"""

import os
import csv
import sys
from pathlib import Path
from typing import List, Dict, Optional
from statistics import median
import assemblyai as aai

# Configuration
AUDIOS_FOLDER = "./audios"
OUTPUTS_FOLDER = "./outputs"
LANGUAGE_CODE = "es"  # Change to "en" for English, etc.
API_KEY_ENV = "ASSEMBLYAI_API_KEY"

# Supported audio file extensions
SUPPORTED_EXTENSIONS = {".mp3", ".wav", ".m4a", ".mp4", ".flac", ".ogg"}


def setup_folders():
    """Create output folder if it doesn't exist."""
    Path(OUTPUTS_FOLDER).mkdir(parents=True, exist_ok=True)
    print(f"✓ Output folder ready: {OUTPUTS_FOLDER}")


def check_api_key():
    """Check if AssemblyAI API key is set."""
    api_key = os.getenv(API_KEY_ENV)
    if not api_key:
        print(f"\n❌ ERROR: AssemblyAI API key not found!")
        print(f"   Please set the {API_KEY_ENV} environment variable.")
        print(f"   Run: export {API_KEY_ENV}='your-api-key-here'")
        print(f"   Or add it to your ~/.zshrc file (for Mac).\n")
        sys.exit(1)
    return api_key


def get_audio_files() -> List[Path]:
    """Get all supported audio files from the audios folder."""
    audios_path = Path(AUDIOS_FOLDER)
    
    if not audios_path.exists():
        print(f"\n❌ ERROR: Audio folder '{AUDIOS_FOLDER}' does not exist!")
        print(f"   Please create the folder and add your audio files.\n")
        sys.exit(1)
    
    audio_files = [
        f for f in audios_path.iterdir()
        if f.is_file() and f.suffix.lower() in SUPPORTED_EXTENSIONS
    ]
    
    if not audio_files:
        print(f"\n❌ ERROR: No audio files found in '{AUDIOS_FOLDER}'!")
        print(f"   Supported formats: {', '.join(SUPPORTED_EXTENSIONS)}\n")
        sys.exit(1)
    
    print(f"✓ Found {len(audio_files)} audio file(s)")
    return sorted(audio_files)


def transcribe_audio(file_path: Path, api_key: str) -> Optional[aai.Transcript]:
    """
    Transcribe audio file with speaker diarization enabled.
    Returns Transcript object or None if failed.
    """
    print(f"\n📝 Processing: {file_path.name}")
    
    # Set API key
    aai.settings.api_key = api_key
    
    # Create config with speaker diarization and utterances
    config = aai.TranscriptionConfig(
        speaker_labels=True,
        language_code=LANGUAGE_CODE,
    )
    
    try:
        # Transcribe the file
        transcriber = aai.Transcriber(config=config)
        transcript = transcriber.transcribe(str(file_path.absolute()))
        
        if transcript.status == aai.TranscriptStatus.error:
            print(f"   ❌ Transcription failed: {transcript.error}")
            return None
        
        if transcript.status != aai.TranscriptStatus.completed:
            print(f"   ❌ Transcription incomplete: status = {transcript.status}")
            return None
        
        print(f"   ✓ Transcription completed")
        return transcript
        
    except Exception as e:
        print(f"   ❌ Error during transcription: {str(e)}")
        return None


def process_transcript(transcript: aai.Transcript, audio_filename: str) -> List[Dict]:
    """
    Process transcript utterances and calculate gaps between turns.
    Returns list of dictionaries with turn data.
    """
    # Get utterances (turn-level segments)
    utterances = transcript.utterances
    
    if not utterances:
        print(f"   ⚠️  No utterances found in transcript. Skipping file.")
        return []
    
    print(f"   ✓ Found {len(utterances)} speaker turn(s)")
    
    # Sort utterances by start time
    sorted_utterances = sorted(utterances, key=lambda u: u.start)
    
    turns = []
    
    for idx, utterance in enumerate(sorted_utterances):
        turn_index = idx + 1  # Start at 1
        start_ms = int(utterance.start)
        end_ms = int(utterance.end)
        duration_ms = end_ms - start_ms
        speaker = utterance.speaker
        text = utterance.text if hasattr(utterance, 'text') else ""
        
        # Get next utterance info
        next_speaker = None
        next_start_ms = None
        gap_to_next_ms = None
        speaker_change = None
        
        if idx < len(sorted_utterances) - 1:
            next_utterance = sorted_utterances[idx + 1]
            next_speaker = next_utterance.speaker
            next_start_ms = int(next_utterance.start)
            gap_to_next_ms = next_start_ms - end_ms
            speaker_change = (speaker != next_speaker)
        else:
            # Last turn
            speaker_change = False
        
        turn_data = {
            "file": audio_filename,
            "turn_index": turn_index,
            "speaker": speaker,
            "start_ms": start_ms,
            "end_ms": end_ms,
            "duration_ms": duration_ms,
            "text": text,
            "next_speaker": next_speaker if next_speaker is not None else "",
            "next_start_ms": next_start_ms if next_start_ms is not None else "",
            "gap_to_next_ms": gap_to_next_ms if gap_to_next_ms is not None else "",
            "speaker_change": speaker_change if speaker_change is not None else False,
        }
        
        turns.append(turn_data)
    
    return turns


def save_per_audio_csv(turns: List[Dict], audio_filename: str):
    """Save per-audio CSV file."""
    if not turns:
        return
    
    csv_filename = Path(OUTPUTS_FOLDER) / f"{Path(audio_filename).stem}_turns.csv"
    
    fieldnames = [
        "file", "turn_index", "speaker", "start_ms", "end_ms", "duration_ms",
        "text", "next_speaker", "next_start_ms", "gap_to_next_ms", "speaker_change"
    ]
    
    with open(csv_filename, "w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(turns)
    
    print(f"   ✓ Saved: {csv_filename.name}")


def calculate_summary_stats(turns: List[Dict]) -> Dict:
    """Calculate summary statistics for speaker-change gaps."""
    if not turns:
        return {}
    
    # Get gaps only for speaker changes
    speaker_change_gaps = [
        turn["gap_to_next_ms"]
        for turn in turns
        if turn.get("speaker_change") and turn.get("gap_to_next_ms") != ""
    ]
    
    if not speaker_change_gaps:
        # If no speaker changes, use all gaps
        speaker_change_gaps = [
            turn["gap_to_next_ms"]
            for turn in turns
            if turn.get("gap_to_next_ms") != ""
        ]
    
    if not speaker_change_gaps:
        return {
            "avg_gap_ms": "",
            "median_gap_ms": "",
            "p95_gap_ms": "",
            "overlap_rate": "",
            "avg_positive_gap_ms": "",
        }
    
    # Calculate statistics
    avg_gap_ms = sum(speaker_change_gaps) / len(speaker_change_gaps)
    
    sorted_gaps = sorted(speaker_change_gaps)
    median_gap_ms = median(sorted_gaps)
    p95_index = int(len(sorted_gaps) * 0.95)
    p95_gap_ms = sorted_gaps[min(p95_index, len(sorted_gaps) - 1)]
    
    # Overlap rate (percentage of negative gaps)
    negative_gaps = [g for g in speaker_change_gaps if g < 0]
    overlap_rate = (len(negative_gaps) / len(speaker_change_gaps)) * 100
    
    # Average positive gap (only gaps > 0)
    positive_gaps = [g for g in speaker_change_gaps if g > 0]
    avg_positive_gap_ms = sum(positive_gaps) / len(positive_gaps) if positive_gaps else 0
    
    return {
        "avg_gap_ms": round(avg_gap_ms, 2),
        "median_gap_ms": round(median_gap_ms, 2),
        "p95_gap_ms": round(p95_gap_ms, 2),
        "overlap_rate": round(overlap_rate, 2),
        "avg_positive_gap_ms": round(avg_positive_gap_ms, 2) if positive_gaps else "",
    }


def save_summary_csv(all_summaries: List[Dict]):
    """Save overall summary CSV with statistics from all audio files."""
    if not all_summaries:
        print("\n⚠️  No summary data to save.")
        return
    
    csv_filename = Path(OUTPUTS_FOLDER) / "summary_all_audios.csv"
    
    fieldnames = [
        "file", "turns", "speaker_changes",
        "avg_gap_ms", "median_gap_ms", "p95_gap_ms",
        "overlap_rate", "avg_positive_gap_ms"
    ]
    
    with open(csv_filename, "w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(all_summaries)
    
    print(f"\n✓ Summary saved: {csv_filename.name}")


def main():
    """Main function to process all audio files."""
    print("=" * 60)
    print("Latency Calculator - AssemblyAI Speaker Diarization")
    print("=" * 60)
    
    # Setup
    setup_folders()
    api_key = check_api_key()
    audio_files = get_audio_files()
    
    # Process each audio file
    all_summaries = []
    
    for audio_file in audio_files:
        # Transcribe
        transcript = transcribe_audio(audio_file, api_key)
        if not transcript:
            continue
        
        # Process utterances
        turns = process_transcript(transcript, audio_file.name)
        if not turns:
            continue
        
        # Save per-audio CSV
        save_per_audio_csv(turns, audio_file.name)
        
        # Calculate summary statistics
        stats = calculate_summary_stats(turns)
        num_speaker_changes = sum(1 for t in turns if t.get("speaker_change"))
        
        summary = {
            "file": audio_file.name,
            "turns": len(turns),
            "speaker_changes": num_speaker_changes,
            **stats,
        }
        all_summaries.append(summary)
    
    # Save overall summary
    if all_summaries:
        save_summary_csv(all_summaries)
    
    print("\n" + "=" * 60)
    print(f"✓ Processing complete! Results saved in '{OUTPUTS_FOLDER}' folder")
    print("=" * 60)


if __name__ == "__main__":
    main()
