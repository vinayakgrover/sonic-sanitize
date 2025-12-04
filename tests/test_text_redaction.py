"""Test text redaction with global offsets."""

import pytest
from pathlib import Path
import sys

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.parsing.transcript_parser import TranscriptSegment
from src.deid.pii_detector import PIIDetector
from src.deid.text_redactor import TextRedactor


def test_single_segment_redaction():
    """Test redaction in a single segment."""
    segments = [
        TranscriptSegment(speaker="S1", text="I'm from Dallas, Texas", start_time=0.0)
    ]

    detector = PIIDetector()
    redactor = TextRedactor()

    # Detect PII (returns global offsets)
    pii_matches = detector.detect_in_segments(segments)

    # Redact
    redacted_segments, log = redactor.redact_segments(segments, pii_matches)

    # Check redaction worked
    assert len(redacted_segments) == 1
    assert "[CITY]" in redacted_segments[0].text
    assert "[STATE]" in redacted_segments[0].text
    assert "Dallas" not in redacted_segments[0].text
    assert "Texas" not in redacted_segments[0].text


def test_multi_segment_redaction():
    """Test redaction across multiple segments (critical test for global offsets)."""
    segments = [
        TranscriptSegment(speaker="S1", text="Hello from Dallas", start_time=0.0),
        TranscriptSegment(speaker="S2", text="I like Houston", start_time=3.0),
        TranscriptSegment(speaker="S1", text="San Antonio is nice", start_time=6.0)
    ]

    detector = PIIDetector()
    redactor = TextRedactor()

    # Detect PII (returns global offsets)
    pii_matches = detector.detect_in_segments(segments)

    # Should find PII in all 3 segments
    assert 0 in pii_matches, "No PII in segment 0"
    assert 1 in pii_matches, "No PII in segment 1"
    assert 2 in pii_matches, "No PII in segment 2"

    # Redact
    redacted_segments, log = redactor.redact_segments(segments, pii_matches)

    # Check all segments were redacted correctly
    assert len(redacted_segments) == 3

    # Segment 0: Dallas should be replaced
    assert "Dallas" not in redacted_segments[0].text
    assert "[CITY]" in redacted_segments[0].text
    assert redacted_segments[0].text == "Hello from [CITY]"

    # Segment 1: Houston should be replaced (THIS IS THE CRITICAL TEST)
    assert "Houston" not in redacted_segments[1].text
    assert "[CITY]" in redacted_segments[1].text
    assert redacted_segments[1].text == "I like [CITY]"

    # Segment 2: San Antonio should be replaced
    assert "San Antonio" not in redacted_segments[2].text
    assert "[CITY]" in redacted_segments[2].text
    assert redacted_segments[2].text == "[CITY] is nice"


def test_complex_multi_segment():
    """Test complex scenario with multiple PII types across segments."""
    segments = [
        TranscriptSegment(speaker="S1", text="I'm from Dallas, Texas on Monday", start_time=0.0),
        TranscriptSegment(speaker="S2", text="I went to Houston in January", start_time=5.0),
        TranscriptSegment(speaker="S1", text="San Antonio is nice on Friday", start_time=10.0)
    ]

    detector = PIIDetector()
    redactor = TextRedactor()

    # Detect and redact
    pii_matches = detector.detect_in_segments(segments)
    redacted_segments, log = redactor.redact_segments(segments, pii_matches)

    # Check segment 0
    assert "Dallas" not in redacted_segments[0].text
    assert "Texas" not in redacted_segments[0].text
    assert "Monday" not in redacted_segments[0].text
    assert "[CITY]" in redacted_segments[0].text
    assert "[STATE]" in redacted_segments[0].text
    assert "[DAY]" in redacted_segments[0].text

    # Check segment 1 (critical - tests global→local offset conversion)
    assert "Houston" not in redacted_segments[1].text
    assert "January" not in redacted_segments[1].text
    assert "[CITY]" in redacted_segments[1].text
    assert "[MONTH]" in redacted_segments[1].text

    # Check segment 2
    assert "San Antonio" not in redacted_segments[2].text
    assert "Friday" not in redacted_segments[2].text
    assert "[CITY]" in redacted_segments[2].text
    assert "[DAY]" in redacted_segments[2].text

    # Check redaction log
    assert log['total_replacements'] >= 7  # At least 7 PII instances
    assert 0 in log['by_segment']
    assert 1 in log['by_segment']
    assert 2 in log['by_segment']


def test_no_pii_segment():
    """Test that segments without PII are unchanged."""
    segments = [
        TranscriptSegment(speaker="S1", text="Hello there", start_time=0.0),
        TranscriptSegment(speaker="S2", text="How are you", start_time=3.0)
    ]

    detector = PIIDetector()
    redactor = TextRedactor()

    pii_matches = detector.detect_in_segments(segments)
    redacted_segments, log = redactor.redact_segments(segments, pii_matches)

    # No redaction should occur
    assert redacted_segments[0].text == "Hello there"
    assert redacted_segments[1].text == "How are you"
    assert log['total_replacements'] == 0


def test_mixed_segments():
    """Test mix of segments with and without PII."""
    segments = [
        TranscriptSegment(speaker="S1", text="I'm from Dallas", start_time=0.0),
        TranscriptSegment(speaker="S2", text="That's interesting", start_time=3.0),
        TranscriptSegment(speaker="S1", text="I went to Houston", start_time=6.0)
    ]

    detector = PIIDetector()
    redactor = TextRedactor()

    pii_matches = detector.detect_in_segments(segments)
    redacted_segments, log = redactor.redact_segments(segments, pii_matches)

    # Segment 0: has PII
    assert "[CITY]" in redacted_segments[0].text

    # Segment 1: no PII
    assert redacted_segments[1].text == "That's interesting"

    # Segment 2: has PII (tests that offset conversion still works after skipped segment)
    assert "Houston" not in redacted_segments[2].text
    assert "[CITY]" in redacted_segments[2].text


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
