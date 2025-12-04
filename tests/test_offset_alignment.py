"""Test offset alignment between PII detection and forced alignment."""

import pytest
from pathlib import Path
import sys

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.parsing.transcript_parser import TranscriptSegment
from src.deid.pii_detector import PIIDetector
from src.utils.transcript_utils import prepare_full_transcript


def test_single_segment_offset():
    """Test that PII offsets are correct for single segment."""
    segments = [
        TranscriptSegment(speaker="S1", text="I'm from Dallas, Texas", start_time=0.0)
    ]

    detector = PIIDetector()
    matches = detector.detect_in_segments(segments)

    # Should find Dallas and Texas
    assert 0 in matches, "No PII found in segment 0"
    assert len(matches[0]) == 2, f"Expected 2 PII, got {len(matches[0])}"

    # Check Dallas position (should be at char 9)
    dallas_match = [m for m in matches[0] if m.value == "Dallas"][0]
    assert dallas_match.start == 9, f"Dallas should start at 9, got {dallas_match.start}"

    # Check Texas position (should be at char 17)
    texas_match = [m for m in matches[0] if m.value == "Texas"][0]
    assert texas_match.start == 17, f"Texas should start at 17, got {texas_match.start}"


def test_multiword_pii():
    """Test that multi-word PII (New York, San Antonio) is detected correctly."""
    segments = [
        TranscriptSegment(speaker="S1", text="I'm from New York", start_time=0.0)
    ]

    detector = PIIDetector()
    matches = detector.detect_in_segments(segments)

    assert 0 in matches, "No PII found"
    new_york_matches = [m for m in matches[0] if "New York" in m.value]
    assert len(new_york_matches) > 0, "New York not detected"

    # New York should start at position 9
    ny_match = new_york_matches[0]
    assert ny_match.start == 9, f"New York should start at 9, got {ny_match.start}"
    assert ny_match.end == 17, f"New York should end at 17, got {ny_match.end}"


def test_cross_segment_offsets():
    """Test that PII offsets are global across multiple segments."""
    segments = [
        TranscriptSegment(speaker="S1", text="Hello from Dallas", start_time=0.0),
        TranscriptSegment(speaker="S2", text="I like Houston", start_time=3.0)
    ]

    detector = PIIDetector()
    matches = detector.detect_in_segments(segments)

    # Check Dallas in segment 0
    assert 0 in matches, "No PII in segment 0"
    dallas_match = matches[0][0]
    assert dallas_match.value == "Dallas"
    assert dallas_match.start == 11, f"Dallas should start at 11, got {dallas_match.start}"

    # Check Houston in segment 1
    assert 1 in matches, "No PII in segment 1"
    houston_match = matches[1][0]
    assert houston_match.value == "Houston"

    # Houston's global offset should be len("Hello from Dallas") + 1 + len("I like ")
    # = 17 + 1 + 7 = 25
    expected_offset = 17 + 1 + 7
    assert houston_match.start == expected_offset, \
        f"Houston should start at {expected_offset}, got {houston_match.start}"


def test_transcript_preparation_consistency():
    """Test that transcript preparation is consistent."""
    segments = [
        TranscriptSegment(speaker="S1", text="First segment", start_time=0.0),
        TranscriptSegment(speaker="S2", text="Second segment", start_time=3.0),
        TranscriptSegment(speaker="S3", text="Third segment", start_time=6.0)
    ]

    full_text, offsets = prepare_full_transcript(segments)

    # Check full text
    assert full_text == "First segment Second segment Third segment"

    # Check offsets
    assert len(offsets) == 3, f"Expected 3 offsets, got {len(offsets)}"
    assert offsets[0] == 0, "First segment should start at 0"
    assert offsets[1] == 14, f"Second segment should start at 14, got {offsets[1]}"
    assert offsets[2] == 29, f"Third segment should start at 29, got {offsets[2]}"

    # Verify each segment can be extracted correctly
    for i, (segment, offset) in enumerate(zip(segments, offsets)):
        extracted = full_text[offset:offset + len(segment.text)]
        assert extracted == segment.text, \
            f"Segment {i} extraction failed: expected '{segment.text}', got '{extracted}'"


def test_complex_scenario():
    """Test complex scenario with multiple PII in multiple segments."""
    segments = [
        TranscriptSegment(speaker="S1", text="I'm from Dallas, Texas on Monday", start_time=0.0),
        TranscriptSegment(speaker="S2", text="I went to Houston in January", start_time=5.0),
        TranscriptSegment(speaker="S1", text="San Antonio is nice on Friday", start_time=10.0)
    ]

    detector = PIIDetector()
    matches = detector.detect_in_segments(segments)

    # Prepare full transcript for verification
    full_text, segment_offsets = prepare_full_transcript(segments)

    # Check all PII matches align with full text
    for segment_idx, pii_list in matches.items():
        for pii_match in pii_list:
            # Extract the text at the global position
            extracted_text = full_text[pii_match.start:pii_match.end]

            # Should match the PII value (case-insensitive)
            assert extracted_text.lower() == pii_match.value.lower(), \
                f"Mismatch: expected '{pii_match.value}' at position {pii_match.start}, " \
                f"but found '{extracted_text}' in full text"


def test_empty_segments():
    """Test handling of empty segments."""
    segments = []

    detector = PIIDetector()
    matches = detector.detect_in_segments(segments)

    assert len(matches) == 0, "Should have no matches for empty segments"


def test_no_pii_segments():
    """Test segments with no PII."""
    segments = [
        TranscriptSegment(speaker="S1", text="Hello there", start_time=0.0),
        TranscriptSegment(speaker="S2", text="How are you", start_time=3.0)
    ]

    detector = PIIDetector()
    matches = detector.detect_in_segments(segments)

    assert len(matches) == 0, "Should have no matches when no PII present"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
