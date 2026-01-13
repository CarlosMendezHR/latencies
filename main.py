#!/usr/bin/env python3
"""
FastAPI wrapper for latency calculator.
Accepts audio file uploads and returns summary CSV.
"""

import os
import csv
import tempfile
import shutil
import uuid
from pathlib import Path
from typing import List, Dict, Optional
from statistics import median

from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.responses import Response
import assemblyai as aai

# Import constants and functions from the existing script
import latency_from_utterances as latency_module
SUPPORTED_EXTENSIONS = latency_module.SUPPORTED_EXTENSIONS
LANGUAGE_CODE = latency_module.LANGUAGE_CODE

app = FastAPI(title="Latency Calculator API", version="1.0.0")


def check_api_key() -> str:
    """Check if AssemblyAI API key is set."""
    api_key = os.getenv("ASSEMBLYAI_API_KEY")
    if not api_key:
        raise HTTPException(
            status_code=500,
            detail="ASSEMBLYAI_API_KEY environment variable is not set. Please configure it in Railway."
        )
    return api_key


def process_uploaded_files(files: List[UploadFile], temp_dir: Path, api_key: str) -> List[Dict]:
    """
    Process uploaded audio files and return summary statistics.
    """
    all_summaries = []
    
    for uploaded_file in files:
        # Check file extension
        file_ext = Path(uploaded_file.filename).suffix.lower()
        if file_ext not in SUPPORTED_EXTENSIONS:
            raise HTTPException(
                status_code=400,
                detail=f"Unsupported file type: {uploaded_file.filename}. Supported formats: {', '.join(SUPPORTED_EXTENSIONS)}"
            )
        
        # Save uploaded file to temp directory
        file_path = temp_dir / uploaded_file.filename
        try:
            with open(file_path, "wb") as f:
                shutil.copyfileobj(uploaded_file.file, f)
        except Exception as e:
            raise HTTPException(
                status_code=500,
                detail=f"Failed to save uploaded file {uploaded_file.filename}: {str(e)}"
            )
        
        # Transcribe
        transcript = latency_module.transcribe_audio(file_path, api_key)
        if not transcript:
            raise HTTPException(
                status_code=500,
                detail=f"Transcription failed for file: {uploaded_file.filename}"
            )
        
        # Process utterances
        turns = latency_module.process_transcript(transcript, uploaded_file.filename)
        if not turns:
            # Skip files with no utterances, but don't fail the whole request
            continue
        
        # Calculate summary statistics
        stats = latency_module.calculate_summary_stats(turns)
        num_speaker_changes = sum(1 for t in turns if t.get("speaker_change"))
        
        summary = {
            "file": uploaded_file.filename,
            "turns": len(turns),
            "speaker_changes": num_speaker_changes,
            **stats,
        }
        all_summaries.append(summary)
    
    return all_summaries


@app.get("/")
async def root():
    """Health check endpoint."""
    return {
        "status": "ok",
        "message": "Latency Calculator API",
        "endpoint": "POST /analyze"
    }


@app.post("/analyze")
async def analyze_audio(files: List[UploadFile] = File(...)):
    """
    Analyze uploaded audio files and return summary CSV.
    
    Accepts multiple audio files via multipart/form-data with field name "files".
    Returns summary_all_audios.csv as a downloadable CSV file.
    """
    # Check if files were uploaded
    if not files:
        raise HTTPException(
            status_code=400,
            detail="No files uploaded. Please upload at least one audio file."
        )
    
    # Check API key
    api_key = check_api_key()
    
    # Create unique temp directory for this request
    temp_dir = Path(tempfile.mkdtemp(prefix="latency_"))
    
    try:
        # Process files
        all_summaries = process_uploaded_files(files, temp_dir, api_key)
        
        if not all_summaries:
            raise HTTPException(
                status_code=400,
                detail="No valid audio data found in uploaded files. Please check that files contain speaker diarization data."
            )
        
        # Create summary CSV in memory
        fieldnames = [
            "file", "turns", "speaker_changes",
            "avg_gap_ms", "median_gap_ms", "p95_gap_ms",
            "overlap_rate", "avg_positive_gap_ms"
        ]
        
        # Write CSV to string
        import io
        output = io.StringIO()
        writer = csv.DictWriter(output, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(all_summaries)
        csv_content = output.getvalue()
        output.close()
        
        # Return CSV file
        return Response(
            content=csv_content,
            media_type="text/csv",
            headers={
                "Content-Disposition": 'attachment; filename="summary_all_audios.csv"'
            }
        )
    
    except HTTPException:
        # Re-raise HTTP exceptions
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Processing failed: {str(e)}"
        )
    finally:
        # Clean up temp directory
        if temp_dir.exists():
            shutil.rmtree(temp_dir, ignore_errors=True)


if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
