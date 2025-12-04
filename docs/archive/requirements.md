# PII De-Identification Pipeline - Requirements Specification

**Project:** Privacy-Preserving Conversational Audio Dataset
**Date:** 2025-12-02
**Version:** 1.0

---

## 1. Executive Summary

Build a lightweight, privacy-preserving pipeline that ingests conversational audio with transcripts, identifies and removes fake PII categories (days, months, colors, cities, states), and outputs a clean dataset suitable for sale to AI model developers and researchers.

**Scope:** Process ~40 conversations from the Appenlimited smartphone conversation dataset within a 2-4 hour implementation window.

---

## 2. Functional Requirements

### 2.1 Data Ingestion (FR-ING)

**FR-ING-01: Download Audio Files**
- System SHALL download 40 WAV audio files from HuggingFace repository
- System SHALL preserve original audio quality (16kHz, 16-bit)
- System SHALL validate audio files are readable and non-corrupted

**FR-ING-02: Download Transcripts**
- System SHALL download corresponding transcript files (TRANSCRIPTION_AUTO_SEGMENTED)
- System SHALL map transcripts to audio files by filename
- System SHALL validate transcript format and completeness

**FR-ING-03: Load Metadata**
- System SHALL load metadata.csv containing conversation details
- System SHALL extract speaker demographics, topics, and device info
- System SHALL associate metadata with corresponding audio/transcript pairs

**FR-ING-04: Organize Data**
- System SHALL store raw data in logical folder structure
- System SHALL generate conversation IDs (conv_001 to conv_040)
- System SHALL create summary statistics (count, total duration, metadata)

### 2.2 Transcript De-Identification (FR-TXT)

**FR-TXT-01: Parse Transcript Format**
- System SHALL parse timestamped transcript format: `[timestamp]` and `<Speaker_X>`
- System SHALL extract segments with start times, speakers, and text
- System SHALL preserve speaker labels and annotations

**FR-TXT-02: PII Detection**
- System SHALL detect PII using configurable word lists from config.yaml
- System SHALL support 5 PII categories: days, months, colors, cities, states
- System SHALL handle case-insensitive matching with word boundaries
- System SHALL handle punctuation variations (e.g., "Dallas," vs "Dallas")

**FR-TXT-03: PII Replacement**
- System SHALL replace detected PII with category tags: [DAY], [MONTH], [COLOR], [CITY], [STATE]
- System SHALL maintain text readability and structure
- System SHALL preserve non-PII content exactly as-is

**FR-TXT-04: Logging**
- System SHALL log all PII replacements per conversation
- System SHALL record: original word, category, position, timestamp
- System SHALL generate replacement statistics

**FR-TXT-05: Output**
- System SHALL save raw transcripts in JSON format
- System SHALL save de-identified transcripts in separate JSON format
- System SHALL include metadata: version, timestamp, PII count

### 2.3 Audio De-Identification (FR-AUD)

**FR-AUD-01: Word-Level Alignment**
- System SHALL use forced alignment (aeneas) to obtain word-level timestamps
- System SHALL align original transcript text to audio
- System SHALL generate precise start/end times for each word
- System SHALL run alignment locally (no external API calls)

**FR-AUD-02: PII Timing Extraction**
- System SHALL identify audio timestamps for detected PII words
- System SHALL extract start/end times from alignment results
- System SHALL handle multi-word PII entities (e.g., "New York")

**FR-AUD-03: Audio Modification**
- System SHALL mute audio segments containing PII
- System SHALL preserve audio duration and quality
- System SHALL support alternative redaction methods (beeping, optional)

**FR-AUD-04: Output**
- System SHALL save de-identified audio in FLAC format
- System SHALL maintain original sample rate and bit depth
- System SHALL generate modification logs (which segments were muted)

### 2.4 Verification & QA (FR-QA)

**FR-QA-01: PII Verification**
- System SHALL verify no PII remains in de-identified transcripts
- System SHALL count PII instances before/after processing
- System SHALL flag any residual PII

**FR-QA-02: Spot Checking**
- System SHALL generate random samples for manual review
- System SHALL show original vs de-identified comparisons
- System SHALL include high-PII conversations in spot checks

**FR-QA-03: Statistics**
- System SHALL generate PII statistics by category
- System SHALL calculate total PII count, unique values, conversation coverage
- System SHALL compute QA pass rate

**FR-QA-04: Reporting**
- System SHALL output spot checks in JSONL format
- System SHALL output statistics in JSON format
- System SHALL generate QA summary report in Markdown

### 2.5 Dataset Curation (FR-CUR)

**FR-CUR-01: File Organization**
- System SHALL organize output in customer-ready structure
- System SHALL separate raw and de-identified content
- System SHALL include separate folders: audio/, transcripts_raw/, transcripts_deid/, metadata/, qa/

**FR-CUR-02: Metadata Generation**
- System SHALL generate conversations.parquet with complete metadata
- System SHALL include: IDs, duration, speakers, PII stats, QA status
- System SHALL preserve original metadata from source

**FR-CUR-03: Documentation**
- System SHALL include README explaining dataset structure
- System SHALL document PII categories and de-identification methods
- System SHALL provide schema documentation

**FR-CUR-04: Validation**
- System SHALL validate all output files are present and complete
- System SHALL verify file integrity (readable, correct format)
- System SHALL ensure file counts match expectations (40 conversations)

---

## 3. Non-Functional Requirements

### 3.1 Performance (NFR-PERF)

**NFR-PERF-01: Processing Time**
- System SHOULD process all 40 conversations within 30 minutes
- Ingestion: < 5 minutes
- Transcript de-ID: < 5 minutes
- Audio alignment: < 15 minutes
- QA generation: < 5 minutes

**NFR-PERF-02: Resource Usage**
- System SHOULD run on standard laptop (8GB RAM, 4 CPU cores)
- System SHOULD NOT require GPU
- System SHOULD use < 10GB disk space

### 3.2 Privacy & Security (NFR-PRIV)

**NFR-PRIV-01: Local Processing**
- System SHALL process all data locally
- System SHALL NOT send PII to external APIs or services
- System SHALL NOT require internet connection after dataset download

**NFR-PRIV-02: Data Isolation**
- System SHALL keep original data separate from de-identified data
- System SHALL NOT overwrite original files
- System SHALL clearly label de-identified outputs

**NFR-PRIV-03: Audit Trail**
- System SHALL maintain logs of all de-identification operations
- System SHALL record which PII was removed and when
- System SHALL enable reproducibility

### 3.3 Scalability (NFR-SCALE)

**NFR-SCALE-01: Dataset Size**
- System architecture SHOULD support scaling to 1,000+ conversations
- System SHOULD support parallel processing of conversations
- System SHOULD use efficient data formats (Parquet, FLAC)

**NFR-SCALE-02: PII Categories**
- System SHOULD support adding new PII categories via configuration
- System SHOULD support custom PII detection patterns
- System SHOULD NOT require code changes for new PII types

### 3.4 Maintainability (NFR-MAINT)

**NFR-MAINT-01: Code Quality**
- Code SHOULD be well-documented with docstrings
- Code SHOULD follow Python best practices (PEP 8)
- Code SHOULD include error handling and logging

**NFR-MAINT-02: Modularity**
- System SHOULD be organized into logical modules
- Modules SHOULD have clear interfaces and responsibilities
- Components SHOULD be testable independently

**NFR-MAINT-03: Configuration**
- PII categories SHOULD be configurable via YAML
- Output paths SHOULD be configurable
- Processing options SHOULD be parameterizable

### 3.5 Usability (NFR-USE)

**NFR-USE-01: Ease of Setup**
- System SHOULD install with standard Python package manager (pip)
- System SHOULD work with Python 3.8+
- Dependencies SHOULD be minimal and well-documented

**NFR-USE-02: Progress Reporting**
- System SHOULD display progress during processing
- System SHOULD report which conversation is being processed
- System SHOULD estimate time remaining

**NFR-USE-03: Error Handling**
- System SHOULD provide clear error messages
- System SHOULD recover gracefully from single-file failures
- System SHOULD continue processing remaining files after errors

---

## 4. Constraints

### 4.1 Technical Constraints

**TC-01: Time Budget**
- Implementation must fit within 2-4 hour timebox
- Some features may be stubbed or proposed rather than fully implemented

**TC-02: Dataset Size**
- Fixed at 40 conversations from specified HuggingFace dataset
- Cannot modify source dataset

**TC-03: PII Categories**
- Limited to 5 fake PII categories as specified in assignment
- Real PII detection not in scope

**TC-04: Platform**
- Must run on macOS (current development environment)
- Should be portable to Linux/Windows

### 4.2 Design Constraints

**DC-01: Forced Alignment Tool**
- Use aeneas for word-level alignment
- Alternative tools (Gentle, MFA) documented but not implemented

**DC-02: Output Formats**
- Audio: FLAC (lossless compression)
- Transcripts: JSON (structured, readable)
- Metadata: Parquet (efficient, standard)
- QA: JSONL (streamable)

**DC-03: No Transcription**
- Use existing transcripts from dataset
- Do NOT generate new transcripts with Whisper/other ASR

---

## 5. Assumptions

**A-01:** Existing transcripts are accurate enough for de-identification purposes

**A-02:** Forced alignment (aeneas) will work reasonably well on conversational speech

**A-03:** Segment-level timestamps in transcripts are accurate

**A-04:** Audio files are clean enough for alignment (no extreme noise/corruption)

**A-05:** PII words are spoken clearly enough to be aligned accurately

**A-06:** Muting PII segments preserves enough context for dataset usability

**A-07:** 40 conversations provide sufficient demonstration of pipeline capabilities

---

## 6. Success Criteria

### 6.1 Must Have (P0)

✅ All 40 conversations ingested successfully

✅ Transcripts de-identified with PII replaced by tags

✅ Audio de-identified with PII segments muted/bleeped

✅ No PII words remain in de-identified transcripts (verified)

✅ Output dataset organized in sellable structure

✅ Metadata file generated with conversation statistics

✅ QA spot checks generated

### 6.2 Should Have (P1)

✅ Word-level alignment using aeneas

✅ Precise audio muting (not entire segments)

✅ Comprehensive QA statistics

✅ Progress reporting during processing

✅ Error handling for edge cases

### 6.3 Nice to Have (P2)

⚪ Parallel processing of conversations

⚪ Alternative audio redaction methods (beeping, re-synthesis)

⚪ Interactive QA review tool

⚪ Advanced PII detection (ML-based)

⚪ Automated testing suite

---

## 7. Out of Scope

❌ Real PII detection (SSN, credit cards, etc.)

❌ Speaker diarization (already provided in transcripts)

❌ Transcript generation/correction

❌ Audio quality enhancement

❌ Dataset hosting/distribution infrastructure

❌ Production deployment (CI/CD, monitoring, etc.)

❌ Multi-language support

❌ Advanced audio de-ID (voice synthesis, voice conversion)

---

## 8. Dependencies

### 8.1 External Libraries

- **huggingface_hub** - Dataset download
- **pandas** - Metadata handling
- **soundfile/librosa** - Audio I/O
- **pydub** - Audio manipulation
- **aeneas** - Forced alignment
- **pyyaml** - Configuration
- **pyarrow** - Parquet support

### 8.2 Data Dependencies

- HuggingFace dataset: Appenlimited/1000h-us-english-smartphone-conversation
- Internet connection for initial dataset download
- ~5GB disk space for dataset + outputs

---

## 9. Risks & Mitigation

| Risk | Impact | Probability | Mitigation |
|------|--------|-------------|------------|
| aeneas alignment fails | High | Medium | Fall back to segment-level estimation; document limitation |
| PII not found in data | Medium | Low | Already verified PII exists in exploration |
| Audio files corrupted | Medium | Low | Validate during ingestion; skip bad files |
| Processing takes too long | Medium | Medium | Optimize or reduce sample size; parallelize |
| Dependencies hard to install | High | Medium | Document clearly; provide alternatives |

---

## 10. Acceptance Criteria

**The system is considered complete when:**

1. All 40 conversations processed end-to-end
2. No PII words remain in de-identified transcripts (100% removal)
3. Audio files playable with PII segments muted
4. Metadata file contains accurate statistics for all conversations
5. QA report shows verification results
6. Output structure matches specification
7. README explains how to use the dataset
8. System design document explains architecture and decisions

---

## 11. Future Enhancements

Beyond this assignment scope:

1. **Production Scaling:** Process 10,000+ conversations with distributed computing
2. **Advanced PII:** ML-based entity recognition for real PII
3. **Audio Quality:** Preserve naturalness with voice synthesis for PII words
4. **Multi-Modal:** Handle video, images, screen recordings
5. **Customization:** Customer-configurable PII categories and policies
6. **Compliance:** GDPR, HIPAA, CCPA compliance features
7. **Versioning:** Track multiple de-identification versions
8. **API:** REST API for on-demand de-identification

---

**Status:** ✅ Requirements Complete
**Next:** System Architecture Design
