# Latency Calculator - AssemblyAI Speaker Diarization

This tool calculates response delays (latency) between speakers in audio files using AssemblyAI's speaker diarization feature.

## What It Does

- Processes audio files with speaker diarization to identify who speaks when
- Calculates gaps between consecutive speaker turns
- Generates CSV files you can open in Excel:
  - One detailed CSV per audio file with all speaker turns
  - One summary CSV with statistics across all audio files

## Prerequisites

- **Mac OS** (instructions are for Mac)
- **Python 3** (version 3.7 or higher)
- **AssemblyAI API Key** (free tier available at [assemblyai.com](https://www.assemblyai.com))

## Step-by-Step Setup Instructions

### Step 1: Install Python (if needed)

Check if Python 3 is installed:
```bash
python3 --version
```

If you see a version number (like `Python 3.9.7`), you're good! If not, install Python from [python.org](https://www.python.org/downloads/).

### Step 2: Install Required Python Package

Open Terminal (Applications → Utilities → Terminal) and run:

```bash
pip3 install assemblyai
```

If that doesn't work, try:
```bash
python3 -m pip install assemblyai
```

### Step 3: Get Your AssemblyAI API Key

1. Go to [https://www.assemblyai.com](https://www.assemblyai.com)
2. Sign up for a free account (or log in if you have one)
3. Go to your dashboard/account settings
4. Copy your API key

### Step 4: Set Your API Key

**Option A: Temporary (for current session only)**
```bash
export ASSEMBLYAI_API_KEY='your-api-key-here'
```

Replace `'your-api-key-here'` with your actual API key.

**Option B: Permanent (recommended)**

Add the API key to your shell configuration file so it's always available:

1. Open Terminal
2. Run:
   ```bash
   nano ~/.zshrc
   ```
3. Add this line at the end (replace with your actual key):
   ```bash
   export ASSEMBLYAI_API_KEY='your-api-key-here'
   ```
4. Press `Ctrl+X`, then `Y`, then `Enter` to save
5. Run this to apply the changes:
   ```bash
   source ~/.zshrc
   ```

### Step 5: Prepare Your Audio Files

1. Create a folder called `audios` in the same directory as the script:
   ```bash
   mkdir audios
   ```

2. Copy your audio files into the `audios` folder
   - Supported formats: `.mp3`, `.wav`, `.m4a`, `.mp4`, `.flac`, `.ogg`

### Step 6: Run the Script

In Terminal, navigate to the script's directory:
```bash
cd /Users/carlosmendez/Documents/latencies
```

Then run:
```bash
python3 latency_from_utterances.py
```

The script will:
- Process all audio files in the `audios` folder
- Show progress messages
- Create CSV files in the `outputs` folder

## Output Files

### Per-Audio CSV Files
- Located in the `outputs` folder
- Named: `[audio_filename]_turns.csv`
- Columns:
  - `file`: Audio file name
  - `turn_index`: Turn number (1, 2, 3...)
  - `speaker`: Speaker label (A, B, C...)
  - `start_ms`: Start time in milliseconds
  - `end_ms`: End time in milliseconds
  - `duration_ms`: Duration of this turn
  - `text`: Transcribed text
  - `next_speaker`: Next speaker label
  - `next_start_ms`: Next turn start time
  - `gap_to_next_ms`: Gap between this turn end and next turn start
    - Positive = silence/delay
    - Negative = overlap (talk-over)
  - `speaker_change`: True if next speaker is different

### Summary CSV
- File: `outputs/summary_all_audios.csv`
- One row per audio file with:
  - `file`: Audio file name
  - `turns`: Total number of speaker turns
  - `speaker_changes`: Number of speaker changes
  - `avg_gap_ms`: Average gap between speaker changes (ms)
  - `median_gap_ms`: Median gap (ms)
  - `p95_gap_ms`: 95th percentile gap (ms)
  - `overlap_rate`: Percentage of speaker changes with overlap (< 0ms gap)
  - `avg_positive_gap_ms`: Average gap when there's a delay (only positive gaps)

## Opening CSV Files in Excel

1. Double-click any CSV file in the `outputs` folder
2. Excel should open it automatically
3. If encoding issues occur, open Excel first, then:
   - File → Open → Select CSV
   - Choose "Unicode UTF-8" encoding

## Changing Language

The script defaults to Spanish (`language_code="es"`). To change:

1. Open `latency_from_utterances.py` in a text editor
2. Find this line near the top:
   ```python
   LANGUAGE_CODE = "es"
   ```
3. Change to your language code:
   - `"en"` for English
   - `"fr"` for French
   - `"de"` for German
   - etc. (see AssemblyAI docs for full list)

## Troubleshooting

### "API key not found" error
- Make sure you set the `ASSEMBLYAI_API_KEY` environment variable
- Try Option B in Step 4 above (permanent setup)

### "No audio files found" error
- Make sure the `audios` folder exists in the same directory as the script
- Check that your audio files have supported extensions (`.mp3`, `.wav`, etc.)

### "No utterances found" warning
- This means the transcription didn't detect speaker turns
- The audio might be too short, unclear, or have poor quality
- Try a different audio file

### Transcription takes a long time
- Large files take longer to process
- AssemblyAI processes files in the cloud, so internet speed matters
- Progress messages will show when each file is done

### Import errors
- Make sure you installed `assemblyai`: `pip3 install assemblyai`
- Try upgrading: `pip3 install --upgrade assemblyai`

## API / Web Deployment

This project includes a FastAPI web API that can be deployed to Railway or run locally.

### Local API Run

1. Install dependencies:
   ```bash
   pip3 install -r requirements.txt
   ```

2. Set your API key:
   ```bash
   export ASSEMBLYAI_API_KEY='your-api-key-here'
   ```

3. Run the FastAPI server:
   ```bash
   uvicorn main:app --reload
   ```

   The API will be available at `http://localhost:8000`

4. Test the API:
   ```bash
   curl -X POST "http://localhost:8000/analyze" \
     -F "files=@path/to/audio1.mp3" \
     -F "files=@path/to/audio2.mp4" \
     -o summary.csv
   ```

### API Endpoints

- **GET /** - Health check endpoint
- **POST /analyze** - Upload audio files and get summary CSV
  - Accepts multiple files via `multipart/form-data` with field name `files`
  - Returns `summary_all_audios.csv` as downloadable file

### Railway Deployment

1. **Create Railway Account**
   - Go to [railway.app](https://railway.app)
   - Sign up/login with GitHub

2. **Deploy from GitHub**
   - Click "New Project"
   - Select "Deploy from GitHub repo"
   - Choose this repository (`latencies`)

3. **Configure Environment Variables**
   - Go to your project settings
   - Add environment variable:
     - Name: `ASSEMBLYAI_API_KEY`
     - Value: Your AssemblyAI API key

4. **Configure Start Command**
   - In Railway project settings, set the start command:
     ```
     uvicorn main:app --host 0.0.0.0 --port $PORT
     ```
   - Railway automatically sets the `$PORT` environment variable

5. **Deploy**
   - Railway will automatically detect `requirements.txt` and install dependencies
   - The app will be deployed and you'll get a public URL

6. **Test Your Deployment**
   ```bash
   curl -X POST "https://your-app.railway.app/analyze" \
     -F "files=@audio.mp3" \
     -o summary.csv
   ```

### API Error Responses

The API returns friendly error messages for:
- Missing `ASSEMBLYAI_API_KEY` environment variable
- No files uploaded
- Unsupported file types
- Transcription failures (includes filename)

## Need Help?

Check the AssemblyAI documentation: [https://www.assemblyai.com/docs](https://www.assemblyai.com/docs)
