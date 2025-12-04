# System Architecture - PII De-Identification Pipeline

**Project:** Privacy-Preserving Conversational Audio Dataset
**Date:** 2025-12-02
**Version:** 1.0

---

## 1. Architecture Overview

### 1.1 System Purpose

Transform raw conversational audio dataset into privacy-preserving, sellable dataset by detecting and removing fake PII from both transcripts and audio while maintaining data quality and usability.

### 1.2 High-Level Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                         INPUT LAYER                              │
├─────────────────────────────────────────────────────────────────┤
│  HuggingFace Repository                                         │
│  ├── Audio Files (WAV)                                          │
│  ├── Transcripts (TXT with timestamps)                          │
│  └── Metadata (CSV)                                             │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│                      PROCESSING PIPELINE                         │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  ┌──────────────┐      ┌──────────────┐      ┌──────────────┐ │
│  │  Ingestion   │ ───→ │   Parsing    │ ───→ │  Alignment   │ │
│  │   Module     │      │    Module    │      │   Module     │ │
│  └──────────────┘      └──────────────┘      └──────────────┘ │
│         ↓                      ↓                      ↓         │
│  ┌──────────────┐      ┌──────────────┐      ┌──────────────┐ │
│  │ PII Detection│ ───→ │   De-ID      │ ───→ │  Audio       │ │
│  │   Module     │      │   Module     │      │  Processor   │ │
│  └──────────────┘      └──────────────┘      └──────────────┘ │
│         ↓                                            ↓         │
│  ┌──────────────┐      ┌──────────────┐      ┌──────────────┐ │
│  │      QA      │ ───→ │  Validation  │ ───→ │   Curation   │ │
│  │   Module     │      │    Module    │      │    Module    │ │
│  └──────────────┘      └──────────────┘      └──────────────┘ │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│                         OUTPUT LAYER                             │
├─────────────────────────────────────────────────────────────────┤
│  De-identified Dataset                                          │
│  ├── Audio (FLAC, PII muted)                                    │
│  ├── Transcripts (JSON, PII tagged)                             │
│  ├── Metadata (Parquet)                                         │
│  └── QA Reports (JSONL, Markdown)                               │
└─────────────────────────────────────────────────────────────────┘
```

---

## 2. Component Architecture

### 2.1 Module Overview

| Module | Responsibility | Input | Output |
|--------|---------------|-------|--------|
| **Ingestion** | Download and organize raw data | HF repo | Local files |
| **Parsing** | Extract structure from transcripts | TXT files | JSON segments |
| **Alignment** | Get word-level timestamps | Audio + Text | Word timings |
| **PII Detection** | Find PII in transcripts | JSON + Config | PII annotations |
| **De-ID** | Replace PII with tags | Annotations | Clean transcripts |
| **Audio Processor** | Mute PII in audio | Audio + Timings | Clean audio |
| **QA** | Verify de-identification | All outputs | QA reports |
| **Validation** | Check data integrity | Outputs | Pass/Fail |
| **Curation** | Organize final dataset | All outputs | Packaged dataset |

### 2.2 Directory Structure

```
src/
├── __init__.py
├── main.py                    # Pipeline orchestrator
│
├── ingestion/
│   ├── __init__.py
│   ├── downloader.py          # HuggingFace download
│   ├── organizer.py           # File organization
│   └── metadata_loader.py     # CSV parsing
│
├── parsing/
│   ├── __init__.py
│   ├── transcript_parser.py   # Parse timestamped format
│   └── segment_extractor.py   # Extract segments
│
├── alignment/
│   ├── __init__.py
│   ├── forced_aligner.py      # aeneas wrapper
│   └── timing_utils.py        # Timestamp utilities
│
├── deid/
│   ├── __init__.py
│   ├── pii_detector.py        # Pattern matching
│   ├── text_redactor.py       # Text replacement
│   └── config_loader.py       # Load PII categories
│
├── audio/
│   ├── __init__.py
│   ├── audio_loader.py        # Load WAV/FLAC
│   ├── audio_modifier.py      # Mute/beep segments
│   └── audio_saver.py         # Save FLAC
│
├── qa/
│   ├── __init__.py
│   ├── verifier.py            # Check PII removal
│   ├── spot_checker.py        # Generate samples
│   └── statistics.py          # Compute stats
│
├── curation/
│   ├── __init__.py
│   ├── packager.py            # Organize outputs
│   └── metadata_generator.py  # Create Parquet
│
└── utils/
    ├── __init__.py
    ├── logger.py              # Logging setup
    ├── progress.py            # Progress reporting
    └── validation.py          # Data validation
```

---

## 3. Detailed Component Design

### 3.1 Ingestion Module

**Purpose:** Download dataset from HuggingFace and organize locally

**Components:**

```python
class HuggingFaceDownloader:
    """Downloads files from HuggingFace repository"""

    def list_files(repo_id: str) -> List[str]:
        """List all files in repository"""

    def download_audio(repo_id: str, output_dir: str):
        """Download all audio files"""

    def download_transcripts(repo_id: str, output_dir: str):
        """Download transcript files"""

    def download_metadata(repo_id: str, output_dir: str):
        """Download metadata.csv"""


class DataOrganizer:
    """Organizes downloaded files into structured layout"""

    def create_directory_structure():
        """Create data/raw/ folders"""

    def assign_conversation_ids(files: List[str]) -> Dict[str, str]:
        """Map original filenames to conv_XXX IDs"""

    def generate_summary() -> Dict:
        """Create ingestion summary statistics"""
```

**Data Flow:**
```
HuggingFace → download_audio() → data/raw/audio/
           → download_transcripts() → data/raw/transcripts/
           → download_metadata() → data/raw/metadata/
           → assign_ids() → conversation mapping
```

### 3.2 Parsing Module

**Purpose:** Parse timestamped transcript format into structured JSON

**Components:**

```python
class TranscriptParser:
    """Parses transcript TXT format"""

    def parse_file(file_path: str) -> Dict:
        """Parse entire transcript file"""

    def extract_segments(content: str) -> List[Segment]:
        """Extract timestamp-delimited segments"""

    def parse_segment(segment: str) -> Segment:
        """Parse single segment: timestamp, speaker, text"""

    def extract_speaker(text: str) -> Tuple[str, str]:
        """Extract speaker tag from text"""

    def clean_annotations(text: str) -> Tuple[str, List[str]]:
        """Remove/extract <annotations>"""


@dataclass
class Segment:
    start_time: float
    end_time: Optional[float]
    speaker: str
    text: str
    annotations: List[str]
```

**Data Flow:**
```
TXT file → extract_segments() → parse_segment() → Segment objects → JSON
```

### 3.3 Alignment Module

**Purpose:** Generate word-level timestamps using forced alignment

**Components:**

```python
class ForcedAligner:
    """Wrapper for aeneas forced alignment"""

    def __init__(self, language="eng"):
        """Initialize aligner"""

    def align_audio_to_text(
        audio_path: str,
        text: str
    ) -> List[WordTiming]:
        """Run forced alignment"""

    def align_conversation(
        audio_path: str,
        segments: List[Segment]
    ) -> List[WordTiming]:
        """Align all segments in conversation"""


@dataclass
class WordTiming:
    word: str
    start: float
    end: float
    speaker: str
    confidence: Optional[float]
```

**Integration with aeneas:**
```python
from aeneas.executetask import ExecuteTask
from aeneas.task import Task

task = Task(config_string=u"task_language=eng|...")
task.audio_file_path = audio_path
task.text_file_path = text_path
ExecuteTask(task).execute()
result = task.sync_map
```

**Data Flow:**
```
Audio + Segments → prepare_text() → aeneas.align() → parse_results() → WordTiming[]
```

### 3.4 PII Detection Module

**Purpose:** Identify PII words in transcripts

**Components:**

```python
class PIIDetector:
    """Detects PII using configured patterns"""

    def __init__(self, config_path: str):
        """Load PII categories from config.yaml"""

    def detect_in_text(text: str) -> List[PIIMatch]:
        """Find all PII instances in text"""

    def detect_in_segment(segment: Segment) -> List[PIIMatch]:
        """Find PII in single segment"""

    def match_word_to_alignment(
        pii: PIIMatch,
        alignments: List[WordTiming]
    ) -> Optional[WordTiming]:
        """Find timing for PII word"""


@dataclass
class PIIMatch:
    word: str
    category: str  # days, months, colors, cities, states
    tag: str       # [DAY], [MONTH], etc.
    position: Tuple[int, int]  # character positions
    segment_index: int
```

**Detection Algorithm:**
```python
def detect_in_text(text: str) -> List[PIIMatch]:
    matches = []
    for category, patterns in pii_config.items():
        for pattern in patterns:
            # Case-insensitive, word boundary matching
            regex = r'\b' + re.escape(pattern) + r'\b'
            for match in re.finditer(regex, text, re.IGNORECASE):
                matches.append(PIIMatch(
                    word=match.group(),
                    category=category,
                    tag=pii_config[category]['tag'],
                    position=(match.start(), match.end())
                ))
    return matches
```

**Data Flow:**
```
Segments + Config → detect_in_segment() → PIIMatch[] → match_to_alignment() → PIIMatch with timing
```

### 3.5 De-Identification Module

**Purpose:** Replace PII in transcripts with tags

**Components:**

```python
class TextRedactor:
    """Replaces PII with category tags"""

    def redact_segment(
        segment: Segment,
        pii_matches: List[PIIMatch]
    ) -> Segment:
        """Replace PII in segment text"""

    def redact_transcript(
        segments: List[Segment],
        all_pii: List[PIIMatch]
    ) -> List[Segment]:
        """Redact entire transcript"""

    def generate_redaction_log(pii: List[PIIMatch]) -> Dict:
        """Create log of replacements"""
```

**Redaction Strategy:**
```python
def redact_segment(segment: Segment, pii_matches: List[PIIMatch]) -> Segment:
    text = segment.text
    # Sort by position (reverse) to maintain offsets
    for pii in sorted(pii_matches, key=lambda x: x.position[0], reverse=True):
        start, end = pii.position
        text = text[:start] + pii.tag + text[end:]

    return Segment(
        start_time=segment.start_time,
        end_time=segment.end_time,
        speaker=segment.speaker,
        text=text,
        annotations=segment.annotations
    )
```

**Data Flow:**
```
Segments + PIIMatches → sort_by_position() → replace_text() → De-identified Segments
```

### 3.6 Audio Processor Module

**Purpose:** Mute PII segments in audio files

**Components:**

```python
class AudioModifier:
    """Modifies audio to remove PII"""

    def load_audio(path: str) -> Tuple[np.ndarray, int]:
        """Load WAV file"""

    def mute_segment(
        audio: np.ndarray,
        start: float,
        end: float,
        sample_rate: int
    ) -> np.ndarray:
        """Mute audio between timestamps"""

    def apply_modifications(
        audio: np.ndarray,
        pii_timings: List[WordTiming],
        sample_rate: int
    ) -> np.ndarray:
        """Mute all PII segments"""

    def save_audio(
        audio: np.ndarray,
        sample_rate: int,
        output_path: str
    ):
        """Save as FLAC"""
```

**Audio Modification Algorithm:**
```python
def mute_segment(audio, start, end, sample_rate):
    """Replace audio segment with silence"""
    start_sample = int(start * sample_rate)
    end_sample = int(end * sample_rate)

    # Ensure within bounds
    start_sample = max(0, start_sample)
    end_sample = min(len(audio), end_sample)

    # Mute (set to zero)
    audio[start_sample:end_sample] = 0

    return audio

# Alternative: Beep tone
def beep_segment(audio, start, end, sample_rate):
    """Replace with 1kHz beep tone"""
    duration = end - start
    beep = generate_beep(duration, sample_rate, frequency=1000)
    # ...insert beep...
```

**Data Flow:**
```
Audio + PII Timings → load_audio() → mute_segment() (for each PII) → save_audio() → FLAC
```

### 3.7 QA Module

**Purpose:** Verify de-identification quality

**Components:**

```python
class PIIVerifier:
    """Verifies no PII remains"""

    def verify_transcript(
        deid_transcript: List[Segment],
        pii_config: Dict
    ) -> VerificationResult:
        """Check for residual PII"""

    def compare_before_after(
        original: List[Segment],
        deid: List[Segment]
    ) -> ComparisonResult:
        """Compare PII counts"""


class SpotChecker:
    """Generates manual review samples"""

    def select_samples(
        conversations: List[Dict],
        n: int = 10
    ) -> List[str]:
        """Select diverse conversations for review"""

    def generate_spot_check(
        original: Segment,
        deid: Segment,
        pii_found: List[PIIMatch]
    ) -> Dict:
        """Create comparison record"""


class StatisticsGenerator:
    """Computes PII statistics"""

    def compute_category_stats(
        all_pii: List[PIIMatch]
    ) -> Dict:
        """Count PII by category"""

    def compute_coverage_stats(
        conversations: List[Dict]
    ) -> Dict:
        """Calculate conversation coverage"""
```

**Data Flow:**
```
Original + De-identified → verify_transcript() → VerificationResult → statistics → QA Reports
```

### 3.8 Curation Module

**Purpose:** Package final dataset

**Components:**

```python
class DatasetPackager:
    """Organizes final output structure"""

    def create_output_structure():
        """Create output/ folders"""

    def copy_files_to_output(conversations: List[Dict]):
        """Move files to output folders"""

    def generate_readme() -> str:
        """Create dataset README"""


class MetadataGenerator:
    """Creates conversations.parquet"""

    def collect_metadata(conversations: List[Dict]) -> pd.DataFrame:
        """Gather all metadata"""

    def save_parquet(df: pd.DataFrame, path: str):
        """Write Parquet file"""

    def generate_schema() -> Dict:
        """Document schema"""
```

**Data Flow:**
```
All processed files → organize_by_type() → copy_to_output() → generate_metadata() → Packaged Dataset
```

---

## 4. Data Flow Architecture

### 4.1 End-to-End Flow

```
[1] Download from HuggingFace
    ↓
[2] Organize raw files (assign IDs)
    ↓
[3] Parse transcripts → JSON
    ↓
[4] Run forced alignment → Word timings
    ↓
[5] Detect PII in transcripts
    ↓
[6] Match PII to word timings
    ↓
[7] De-identify transcripts (text)
    ↓
[8] De-identify audio (mute segments)
    ↓
[9] Verify no PII remains
    ↓
[10] Generate QA reports
    ↓
[11] Package dataset
```

### 4.2 Processing Loop (Per Conversation)

```python
def process_conversation(conv_id: str):
    # 1. Load data
    audio = load_audio(f"data/raw/audio/{conv_id}.wav")
    transcript = load_transcript(f"data/raw/transcripts/{conv_id}.txt")
    metadata = load_metadata(conv_id)

    # 2. Parse
    segments = parse_transcript(transcript)

    # 3. Align
    word_timings = align_audio_to_text(audio, segments)

    # 4. Detect PII
    pii_matches = detect_pii(segments)

    # 5. Match to timings
    pii_with_timings = match_pii_to_alignments(pii_matches, word_timings)

    # 6. De-identify text
    deid_segments = redact_transcript(segments, pii_matches)

    # 7. De-identify audio
    deid_audio = modify_audio(audio, pii_with_timings)

    # 8. Verify
    verification = verify_no_pii(deid_segments)

    # 9. Save outputs
    save_transcript(deid_segments, f"output/transcripts_deid/{conv_id}.json")
    save_audio(deid_audio, f"output/audio/{conv_id}.flac")

    # 10. Return stats
    return {
        "conv_id": conv_id,
        "pii_count": len(pii_matches),
        "verification": verification
    }
```

---

## 5. Technology Stack

### 5.1 Core Libraries

| Technology | Purpose | Justification |
|------------|---------|---------------|
| **Python 3.8+** | Language | Standard for data processing, rich ecosystem |
| **huggingface_hub** | Dataset download | Official HF API, reliable |
| **pandas** | Metadata handling | Industry standard, Parquet support |
| **numpy** | Audio processing | Efficient array operations |
| **soundfile** | Audio I/O | Clean interface, FLAC support |
| **librosa** | Audio analysis | Audio utilities, resampling |
| **pydub** | Audio manipulation | Simple muting/editing API |
| **aeneas** | Forced alignment | Lightweight, no ML models |
| **pyyaml** | Configuration | Human-readable config files |
| **pyarrow** | Parquet support | Efficient columnar format |

### 5.2 File Formats

| Format | Use Case | Rationale |
|--------|----------|-----------|
| **FLAC** | De-identified audio | Lossless, ~50% smaller than WAV, standard |
| **JSON** | Transcripts | Structured, human-readable, easy to parse |
| **Parquet** | Metadata | Efficient, schema evolution, analytics-ready |
| **JSONL** | QA spot checks | Streamable, line-delimited, easy to process |
| **YAML** | Configuration | Readable, comments support, hierarchical |
| **Markdown** | Documentation | Standard, renders nicely on GitHub |

---

## 6. Design Decisions & Trade-offs

### 6.1 Forced Alignment vs Estimation

**Decision:** Use aeneas for word-level forced alignment

**Alternatives Considered:**
- Segment-level estimation (faster, less accurate)
- Whisper word timestamps (requires transcription, privacy risk)
- Gentle (more accurate, harder to install)

**Rationale:**
- ✅ Privacy-preserving (no external APIs)
- ✅ Precise word-level timing
- ✅ Easy installation (pip install)
- ✅ Scalable to production
- ⚠️ May be less accurate than Gentle/MFA for conversational speech

**Trade-off:** Accuracy vs Ease of Use → Chose ease of use

### 6.2 Text-based vs ML-based PII Detection

**Decision:** Use regex pattern matching with word lists

**Alternatives Considered:**
- spaCy NER (real entity recognition)
- Custom ML model
- Cloud NER APIs (Google, AWS)

**Rationale:**
- ✅ Fake PII categories (not real entities)
- ✅ Configurable via YAML (no model training)
- ✅ Predictable and deterministic
- ✅ Fast processing
- ⚠️ Won't generalize to new categories automatically

**Trade-off:** Flexibility vs Simplicity → Chose simplicity

### 6.3 Muting vs Beeping vs Re-synthesis

**Decision:** Mute PII segments (silence)

**Alternatives Considered:**
- Beep tone (obvious redaction)
- Voice re-synthesis with TTS (preserve naturalness)
- White noise (less obvious than beep)

**Rationale:**
- ✅ Simplest implementation
- ✅ Clear indication of redaction
- ✅ No additional dependencies
- ✅ Preserves audio duration
- ⚠️ May disrupt conversation flow

**Trade-off:** Naturalness vs Simplicity → Chose simplicity (can upgrade later)

### 6.4 Streaming vs Batch Processing

**Decision:** Batch processing (process one conversation at a time)

**Alternatives Considered:**
- Streaming (process files as they download)
- Parallel (process multiple conversations simultaneously)

**Rationale:**
- ✅ Simpler error handling
- ✅ Clear progress tracking
- ✅ Lower memory footprint
- ✅ Easier debugging
- ⚠️ Could be faster with parallelization

**Trade-off:** Speed vs Simplicity → Chose simplicity (40 files is manageable)

### 6.5 JSON vs Parquet for Transcripts

**Decision:** JSON for transcripts, Parquet for metadata

**Rationale:**
- JSON transcripts: Human-readable, easy to inspect, standard format
- Parquet metadata: Efficient for analytics, supports schema evolution
- Different use cases warrant different formats

---

## 7. Error Handling Strategy

### 7.1 Error Categories

| Error Type | Handling Strategy |
|------------|------------------|
| **Download failure** | Retry 3 times, log and skip file |
| **Corrupt audio** | Validate during load, skip file, report in QA |
| **Missing transcript** | Log warning, skip conversation |
| **Alignment failure** | Fall back to segment-level estimation |
| **PII detection error** | Log but continue (conservative: don't fail pipeline) |
| **Audio save failure** | Retry, check disk space, raise if critical |

### 7.2 Error Handling Code Pattern

```python
def process_conversation(conv_id: str) -> Optional[Dict]:
    try:
        # Main processing logic
        result = do_processing(conv_id)
        return result

    except AudioCorruptedError as e:
        logger.warning(f"{conv_id}: Audio corrupted - {e}")
        return None  # Skip this conversation

    except AlignmentError as e:
        logger.warning(f"{conv_id}: Alignment failed - {e}")
        # Fall back to segment-level
        result = fallback_segment_level(conv_id)
        return result

    except Exception as e:
        logger.error(f"{conv_id}: Unexpected error - {e}")
        raise  # Re-raise for debugging
```

### 7.3 Validation Checkpoints

```
[✓] After download: Validate file exists and size > 0
[✓] After parsing: Validate segments extracted
[✓] After alignment: Validate word count matches roughly
[✓] After PII detection: Validate at least some PII found (if expected)
[✓] After de-ID: Validate no original PII remains
[✓] After audio save: Validate file playable and duration matches
```

---

## 8. Scalability Considerations

### 8.1 Current Implementation (40 conversations)

```
Sequential processing:
- 1 conversation at a time
- ~1-2 minutes per conversation
- Total: ~40-80 minutes

Memory: ~500MB peak (1 audio file in memory)
Disk: ~5GB input, ~3GB output
```

### 8.2 Scaling to 1,000 Conversations

**Approach:** Parallel processing with multiprocessing

```python
from multiprocessing import Pool

def main():
    conversations = load_conversation_list()

    with Pool(processes=4) as pool:
        results = pool.map(process_conversation, conversations)

    # Aggregate results
    generate_final_reports(results)
```

**Expected Performance:**
- 4 cores: ~250 conversations per hour
- 1,000 conversations: ~4 hours

### 8.3 Scaling to 10,000+ Conversations

**Approach:** Distributed processing with Dask or Spark

```python
import dask.bag as db

conversations = db.from_sequence(conversation_ids, npartitions=100)
results = conversations.map(process_conversation).compute()
```

**Infrastructure:**
- Multiple machines or cloud instances
- Shared storage (S3, NFS)
- Job queue (Celery, SQS)

---

## 9. Testing Strategy

### 9.1 Unit Tests

```python
# Test PII detection
def test_pii_detection():
    text = "I'm from Dallas, Texas"
    matches = detect_pii(text)
    assert len(matches) == 2
    assert matches[0].category == "cities"
    assert matches[1].category == "states"

# Test redaction
def test_redaction():
    text = "I'm from Dallas, Texas"
    redacted = redact_text(text, pii_matches)
    assert redacted == "I'm from [CITY], [STATE]"
    assert "Dallas" not in redacted
    assert "Texas" not in redacted
```

### 9.2 Integration Tests

```python
def test_end_to_end():
    """Test full pipeline on sample conversation"""
    # Use test fixture
    result = process_conversation("test_conv_001")

    # Verify outputs exist
    assert os.path.exists("output/audio/test_conv_001.flac")
    assert os.path.exists("output/transcripts_deid/test_conv_001.json")

    # Verify no PII in output
    deid_transcript = load_json("output/transcripts_deid/test_conv_001.json")
    assert verify_no_pii(deid_transcript) == True
```

### 9.3 QA Validation

```python
def test_qa_validation():
    """Ensure QA reports are generated"""
    results = process_all_conversations()

    qa_stats = generate_statistics(results)
    assert qa_stats['pii_remaining'] == 0
    assert qa_stats['conversations_processed'] == 40
```

---

## 10. Deployment & Usage

### 10.1 Installation

```bash
# Clone repository
git clone <repo-url>
cd gosumoai

# Create virtual environment
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

### 10.2 Configuration

Edit `config.yaml` to customize PII categories:

```yaml
pii_categories:
  cities:
    - Denver
    - Seattle
    tag: "[CITY]"
```

### 10.3 Running the Pipeline

```bash
# Run full pipeline
python -m src.main

# Options:
python -m src.main --conversations 10  # Process first 10 only
python -m src.main --skip-audio       # Skip audio de-ID (faster testing)
python -m src.main --output-dir /path # Custom output location
```

### 10.4 Output Structure

```
output/
├── audio/train/              # 40 FLAC files
├── transcripts_raw/train/    # 40 JSON files (original)
├── transcripts_deid/train/   # 40 JSON files (de-identified)
├── alignments/train/         # 40 JSON files (word timings)
├── metadata/
│   ├── conversations.parquet
│   ├── schema.json
│   └── README.md
└── qa/
    ├── deid_spot_checks.jsonl
    ├── pii_statistics.json
    └── qa_report.md
```

---

## 11. Future Architecture Improvements

1. **Microservices Architecture**
   - Separate services for alignment, de-ID, QA
   - REST APIs for each component
   - Scalable independently

2. **Event-Driven Processing**
   - Message queue (RabbitMQ, Kafka)
   - Asynchronous processing
   - Better fault tolerance

3. **Caching Layer**
   - Cache alignment results
   - Reuse for multiple de-ID runs
   - Speed up iterations

4. **Monitoring & Observability**
   - Prometheus metrics
   - Grafana dashboards
   - Error tracking (Sentry)

5. **ML-based PII Detection**
   - Train custom NER model
   - Handle new PII types automatically
   - Improve accuracy

---

**Status:** ✅ Architecture Complete
**Next:** Implementation
