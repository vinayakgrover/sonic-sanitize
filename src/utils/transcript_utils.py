"""Shared utilities for transcript processing."""

from typing import List, Tuple


def prepare_full_transcript(segments: List, separator: str = " ") -> Tuple[str, List[int]]:
    """
    Prepare full transcript with segment boundary tracking.

    This is the single source of truth for how segments are joined into
    a full transcript. Both PII detection and forced alignment use this
    to ensure offsets are calculated consistently.

    Args:
        segments: List of TranscriptSegment objects
        separator: String to join segments (default: single space)

    Returns:
        Tuple of (full_text, segment_offsets)
        - full_text: Combined transcript with separators
        - segment_offsets: List of starting character positions for each segment

    Example:
        segments = [
            Segment(text="Hello world", ...),
            Segment(text="How are you", ...)
        ]
        full_text, offsets = prepare_full_transcript(segments)
        # full_text = "Hello world How are you"
        # offsets = [0, 12]  # Second segment starts at char 12
    """
    if not segments:
        return "", []

    text_parts = []
    segment_offsets = []
    current_position = 0

    for i, segment in enumerate(segments):
        # Record where this segment starts in the full text
        segment_offsets.append(current_position)

        # Get segment text
        text = segment.text if hasattr(segment, 'text') else str(segment)
        text_parts.append(text)

        # Update position for next segment
        current_position += len(text)

        # Add separator length if not last segment
        if i < len(segments) - 1:
            current_position += len(separator)

    full_text = separator.join(text_parts)

    return full_text, segment_offsets


def get_segment_boundaries(segments: List, separator: str = " ") -> List[Tuple[int, int]]:
    """
    Get character boundaries for each segment in the full transcript.

    Args:
        segments: List of TranscriptSegment objects
        separator: String to join segments

    Returns:
        List of (start, end) tuples for each segment

    Example:
        segments = [Segment(text="Hello"), Segment(text="World")]
        boundaries = get_segment_boundaries(segments)
        # [(0, 5), (6, 11)]
    """
    _, offsets = prepare_full_transcript(segments, separator)
    boundaries = []

    for i, offset in enumerate(offsets):
        text = segments[i].text if hasattr(segments[i], 'text') else str(segments[i])
        end = offset + len(text)
        boundaries.append((offset, end))

    return boundaries


def main():
    """Test the transcript utilities."""
    from ..parsing.transcript_parser import TranscriptSegment

    # Create test segments
    segments = [
        TranscriptSegment(speaker="S1", text="Hello from Dallas", start_time=0.0),
        TranscriptSegment(speaker="S2", text="I like Houston", start_time=3.0),
        TranscriptSegment(speaker="S1", text="Nice to meet you", start_time=6.0)
    ]

    # Test full transcript preparation
    full_text, offsets = prepare_full_transcript(segments)

    print("\n=== Transcript Preparation Test ===")
    print(f"Full text: {full_text}")
    print(f"\nSegment offsets: {offsets}")

    for i, (segment, offset) in enumerate(zip(segments, offsets)):
        print(f"\nSegment {i}:")
        print(f"  Text: '{segment.text}'")
        print(f"  Starts at: {offset}")
        print(f"  In full text: '{full_text[offset:offset+len(segment.text)]}'")

    # Test boundaries
    boundaries = get_segment_boundaries(segments)
    print(f"\nSegment boundaries: {boundaries}")


if __name__ == "__main__":
    main()
