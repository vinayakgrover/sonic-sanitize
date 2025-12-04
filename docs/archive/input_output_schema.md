# Input/Output Data Schema

**Status:** ✅ Complete (based on exploration findings)
**Date:** 2025-12-02
**Version:** v1

---

## Input Data Schema

### Source
- **Dataset:** Appenlimited/1000h-us-english-smartphone-conversation
- **Size:** 40 conversations
- **Format:** WAV audio + TXT transcripts + CSV metadata
- **Access:** HuggingFace Hub repository

### Input File Structure

```
HuggingFace Repository:
├── audio/
│   ├── F2M2_USA_USA_002.wav
│   ├── F2308F2308_USA_USA_001.wav
│   ├── M349M349_USA_USA_001.wav
│   └── ... (40 total WAV files)
│
├── USE_ASR003_Sample/TRANSCRIPTION_AUTO_SEGMENTED/
│   ├── F2M2/
│   │   ├── F2M2_USA_USA_002.txt
│   │   └── ...
│   ├── F2308F2308/
│   │   ├── F2308F2308_USA_USA_001.txt
│   │   └── ...
│   └── M349M349/
│       ├── M349M349_USA_USA_001.txt
│       └── ...
│
└── metadata.csv (40 rows)
```

### Audio Format

**Specification:**
- **Format:** WAV (uncompressed)
- **Channels:** Mono or Stereo (varies by file)
- **Sample Rate:** 16kHz (typical for speech)
- **Bit Depth:** 16-bit
- **Duration:** 105-608 seconds per conversation
- **Naming:** `{SpeakerID}_{Country}_{Country}_{Number}.wav`

**Example:** `F2M2_USA_USA_002.wav`

### Transcript Format

**Structure:**
```
[timestamp]
<Speaker_X> text with <annotations>
[timestamp]
more text
```

**Example:**
```
[0.000]
<Speaker_1> I'm from Dallas , Texas
[3.500]
and I love visiting New York on Fridays
[7.200]
<Speaker_2> oh cool , I'm from Houston
```

**Features:**
- **Timestamps:** `[seconds]` format (e.g., `[0.000]`, `[3.500]`)
- **Speakers:** `<Speaker_1>`, `<Speaker_2>`
- **Annotations:** `<no-speech>`, `<lipsmack>`, `<cough>`, `<hesitation>`, `<int>`
- **Encoding:** UTF-8
- **Line breaks:** Segments separated by timestamp markers

### Metadata Schema (CSV)

**File:** `metadata.csv`

| Column | Type | Description | Example |
|--------|------|-------------|---------|
| file_name | string | Path to audio file | audio/F2M2_USA_USA_002.wav |
| domains-topics | string | Conversation topic | hometown, punctuality, film |
| device-type | string | Recording device | samsung galaxy J3 |
| gender01 | string | Speaker 1 gender | Female, Male |
| gender02 | string | Speaker 2 gender | Female, Male |
| age-group01 | string | Speaker 1 age range | 25-34, 20-24, 18-19 |
| age-group02 | string | Speaker 2 age range | 25-34, 20-24 |
| country-of-residence01 | string | Speaker 1 residence | United States |
| country-of-residence02 | string | Speaker 2 residence | United States |
| country-of-origin01 | string | Speaker 1 origin | United States |
| country-of-origin02 | string | Speaker 2 origin | United States |

### File Name Mapping

**Pattern:**
```
Audio:       audio/F2M2_USA_USA_002.wav
Transcript:  TRANSCRIPTION_AUTO_SEGMENTED/F2M2/F2M2_USA_USA_002.txt
Metadata:    Row where file_name = "audio/F2M2_USA_USA_002.wav"
```

---

## Processing Pipeline Data Flow

### Stage 1: Raw Ingestion

**Input:** HuggingFace repository files
**Output:** Local organized structure

```
data/raw/
├── audio/
│   ├── conv_001.wav
│   └── ...
├── transcripts/
│   ├── conv_001.txt
│   └── ...
└── metadata/
    └── conversations.csv
```

### Stage 2: Parsed Transcripts

**Format:** JSON with structured segments

```json
{
  "conversation_id": "conv_001",
  "source_file": "F2M2_USA_USA_002.wav",
  "segments": [
    {
      "start_time": 0.000,
      "end_time": 3.500,
      "speaker": "Speaker_1",
      "text": "I'm from Dallas , Texas",
      "annotations": []
    },
    {
      "start_time": 3.500,
      "end_time": 7.200,
      "speaker": "Speaker_1",
      "text": "and I love visiting New York on Fridays",
      "annotations": ["<no-speech>"]
    }
  ]
}
```

### Stage 3: Word-Level Alignment

**Tool:** aeneas forced alignment
**Output:** Word-level timestamps

```json
{
  "conversation_id": "conv_001",
  "words": [
    {"word": "I'm", "start": 0.000, "end": 0.150, "speaker": "Speaker_1"},
    {"word": "from", "start": 0.150, "end": 0.350, "speaker": "Speaker_1"},
    {"word": "Dallas", "start": 0.350, "end": 0.750, "speaker": "Speaker_1"},
    {"word": "Texas", "start": 0.850, "end": 1.200, "speaker": "Speaker_1"}
  ]
}
```

### Stage 4: PII Detection

**Output:** PII annotations

```json
{
  "conversation_id": "conv_001",
  "pii_detections": [
    {
      "word": "Dallas",
      "category": "cities",
      "tag": "[CITY]",
      "start_time": 0.350,
      "end_time": 0.750,
      "segment_index": 0,
      "word_index": 2
    },
    {
      "word": "Texas",
      "category": "states",
      "tag": "[STATE]",
      "start_time": 0.850,
      "end_time": 1.200,
      "segment_index": 0,
      "word_index": 3
    }
  ]
}
```

---

## Output Data Schema

### Output Directory Structure

```
output/
├── audio/
│   └── train/
│       ├── conv_001.flac
│       ├── conv_002.flac
│       └── ... (40 files)
│
├── transcripts_raw/
│   └── train/
│       ├── conv_001.json
│       ├── conv_002.json
│       └── ...
│
├── transcripts_deid/
│   └── train/
│       ├── conv_001.json
│       ├── conv_002.json
│       └── ...
│
├── alignments/
│   └── train/
│       ├── conv_001.json (word-level timestamps)
│       └── ...
│
├── metadata/
│   ├── conversations.parquet
│   ├── schema.json
│   └── README.md
│
└── qa/
    ├── deid_spot_checks.jsonl
    ├── pii_statistics.json
    └── qa_report.md
```

### De-identified Transcript Format

```json
{
  "conversation_id": "conv_001",
  "source_file": "F2M2_USA_USA_002.wav",
  "deid_version": "2025-12-02_v1",
  "segments": [
    {
      "start_time": 0.000,
      "end_time": 3.500,
      "speaker": "Speaker_1",
      "text": "I'm from [CITY] , [STATE]",
      "original_text_length": 24,
      "deid_text_length": 26,
      "pii_count": 2
    }
  ],
  "pii_summary": {
    "total_pii_found": 5,
    "categories": {
      "cities": 2,
      "states": 1,
      "days": 1,
      "months": 1
    }
  },
  "word_alignments": [
    {
      "word": "[CITY]",
      "original": "REDACTED",
      "start": 0.350,
      "end": 0.750,
      "audio_modified": true
    }
  ]
}
```

### De-identified Audio Format

**Specification:**
- **Format:** FLAC (lossless compression)
- **Codec:** FLAC 1.3+
- **Sample Rate:** Original (16kHz)
- **Channels:** Original (mono/stereo)
- **Modifications:** PII segments muted or beeped
- **Naming:** `conv_{number}.flac`

**Audio Modification Methods:**
1. **Muting:** Replace PII audio with silence
2. **Beeping:** Replace with 1kHz tone (optional)
3. **Metadata:** JSON sidecar with modification log

### Metadata Output (Parquet)

**File:** `metadata/conversations.parquet`

**Schema:**
```python
{
  # Identifiers
  "conversation_id": str,              # conv_001, conv_002, ...
  "source_file": str,                  # Original filename

  # Audio info
  "duration_sec": float,               # 412.5
  "sample_rate": int,                  # 16000
  "channels": int,                     # 1 or 2
  "audio_format": str,                 # "flac"

  # Speaker info
  "num_speakers": int,                 # 2
  "gender_01": str,                    # "Female", "Male"
  "gender_02": str,
  "age_group_01": str,                 # "25-34"
  "age_group_02": str,

  # Content info
  "topic": str,                        # "hometown", "film", etc.
  "device_type": str,                  # "samsung galaxy J3"

  # De-identification info
  "has_pii": bool,                     # True/False
  "pii_count_original": int,           # 5
  "pii_categories": str,               # JSON: {"cities": 2, "states": 1, ...}
  "deid_version": str,                 # "2025-12-02_v1"
  "deid_timestamp": str,               # ISO 8601 timestamp

  # QA info
  "qa_status": str,                    # "approved", "pending", "review"
  "qa_notes": str,                     # Optional notes

  # Processing info
  "alignment_method": str,             # "aeneas"
  "alignment_confidence": float,       # 0.95
  "audio_modified": bool,              # True
  "audio_mute_segments": int           # 5
}
```

### QA Spot Check Format

**File:** `qa/deid_spot_checks.jsonl`

```jsonl
{"conversation_id": "conv_001", "segment_id": 0, "original_text": "I'm from Dallas", "deid_text": "I'm from [CITY]", "pii_found": ["Dallas"], "category": "cities", "audio_time": "0.35-0.75", "status": "approved", "reviewer": "automated"}
{"conversation_id": "conv_001", "segment_id": 0, "original_text": "Dallas, Texas", "deid_text": "[CITY], [STATE]", "pii_found": ["Dallas", "Texas"], "category": "cities,states", "audio_time": "0.35-1.20", "status": "approved", "reviewer": "automated"}
```

### PII Statistics Format

**File:** `qa/pii_statistics.json`

```json
{
  "dataset_summary": {
    "total_conversations": 40,
    "conversations_with_pii": 35,
    "total_pii_instances": 142
  },
  "pii_by_category": {
    "days": {
      "count": 12,
      "unique_values": 5,
      "conversations": 10
    },
    "months": {
      "count": 18,
      "unique_values": 8,
      "conversations": 15
    },
    "colors": {
      "count": 3,
      "unique_values": 2,
      "conversations": 3
    },
    "cities": {
      "count": 67,
      "unique_values": 12,
      "conversations": 32
    },
    "states": {
      "count": 42,
      "unique_values": 8,
      "conversations": 28
    }
  },
  "verification": {
    "pii_remaining_in_transcripts": 0,
    "audio_segments_modified": 142,
    "qa_pass_rate": 1.0
  }
}
```

---

## Data Validation Rules

### Input Validation
- ✅ Audio file exists and is readable
- ✅ Transcript file exists and matches audio filename
- ✅ Metadata row exists for conversation
- ✅ Audio duration > 0
- ✅ Transcript has at least 1 segment

### Output Validation
- ✅ No PII words remain in de-identified transcripts
- ✅ Audio file playable and same duration as original
- ✅ Metadata complete for all conversations
- ✅ QA spot checks generated
- ✅ PII statistics accurate

---

## Technical Specifications

### Text Encoding
- **Format:** UTF-8
- **Line Endings:** Unix (LF)
- **Special Characters:** Preserved in original form

### Audio Specifications
- **Input:** WAV, 16kHz, 16-bit
- **Output:** FLAC, 16kHz, same bit depth
- **Compression:** FLAC level 5 (balanced)
- **Metadata:** Preserved from source

### Timestamps
- **Format:** Decimal seconds (e.g., 0.000, 3.500, 7.245)
- **Precision:** Milliseconds (3 decimal places)
- **Reference:** Start of audio file (0.000)

### File Naming Conventions
- **Input:** Original names preserved
- **Output:** Normalized to `conv_{001-040}.{ext}`
- **Zero-padding:** 3 digits (001, 002, ..., 040)

---

**Status:** Ready for implementation ✅
