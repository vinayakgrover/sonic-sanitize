# Quick Start Guide

Get the pipeline running in 5 minutes!

## Prerequisites

- Python 3.8 or higher
- ~500MB free disk space for dependencies
- ~2GB free disk space for dataset (40 conversations)

## Step 1: Setup Environment

```bash
# Create virtual environment
python3 -m venv venv

# Activate it
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

### macOS Users: Install espeak

aeneas (forced alignment) requires espeak:

```bash
brew install espeak
```

## Step 2: Test Modules

Verify all modules are working:

```bash
python test_modules.py
```

You should see:
```
✓ All tests passed! Ready to run pipeline.
```

## Step 3: Run Pipeline (Test Mode)

Test with 3 conversations first:

```bash
python -m src.main --limit 3
```

This will:
1. Download 3 conversations from HuggingFace
2. Detect and remove PII
3. Generate de-identified audio and transcripts
4. Create QA reports

**Expected time:** ~5-10 minutes

## Step 4: Check Outputs

```bash
ls -R output/
```

You should see:
```
output/
├── audio/train/              # 3 de-identified FLAC files
├── transcripts_deid/train/   # 3 de-identified JSON files
├── metadata/                 # Parquet and manifest
├── qa/                       # QA reports
└── logs/                     # Pipeline logs
```

## Step 5: Run Full Pipeline

Process all 40 conversations:

```bash
python -m src.main
```

**Expected time:** ~20-30 minutes (depends on aeneas speed)

## Troubleshooting

### aeneas not installed

**Error:** `aeneas is not installed`

**Fix:**
```bash
# macOS
brew install espeak
pip install aeneas

# Linux
sudo apt-get install espeak
pip install aeneas
```

### Module import errors

**Error:** `ModuleNotFoundError`

**Fix:**
```bash
# Make sure you're in the virtual environment
source venv/bin/activate

# Reinstall dependencies
pip install -r requirements.txt
```

### Out of memory

**Error:** Pipeline crashes or slows down

**Fix:** Process in smaller batches:
```bash
# Process 10 at a time
python -m src.main --limit 10
```

### Config not found

**Error:** `Config file not found: config.yaml`

**Fix:** Make sure you're in the project root directory:
```bash
cd /path/to/gosumoai
python -m src.main
```

## Verify Results

### Check QA Report

```bash
cat output/qa/qa_report.md
```

Look for:
- **Status:** PASS
- **PII Remaining:** 0
- **Pass Rate:** 100%

### Spot-Check Sample

```bash
cat output/qa/spot_check_samples.jsonl | head -5
```

Verify that PII is replaced with tags like `[CITY]`, `[STATE]`, etc.

### Listen to Audio

Pick a random de-identified audio file:
```bash
open output/audio/train/*.flac  # macOS
# or
vlc output/audio/train/*.flac   # Linux
```

You should hear silence during PII segments.

## Next Steps

1. **Review outputs** in `output/` directory
2. **Read QA report** in `output/qa/qa_report.md`
3. **Check metadata** in `output/metadata/conversations.parquet`
4. **See SYSTEM_DESIGN.md** for technical details

## Common Commands

```bash
# Test with 5 conversations
python -m src.main --limit 5

# Full pipeline
python -m src.main

# Run module tests
python test_modules.py

# Test individual modules
python -m src.deid.pii_detector
python -m src.parsing.transcript_parser
```

## Getting Help

- Check logs: `output/logs/pipeline.log`
- Read documentation: `SYSTEM_DESIGN.md`
- Review TODO: `TODO.md`

---

**Ready?** Run `python -m src.main --limit 3` and let's go!
