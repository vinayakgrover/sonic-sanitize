"""Parse transcript files with timestamp format."""

import re
from pathlib import Path
from typing import List, Optional
from dataclasses import dataclass
from ..utils.logger import get_logger

logger = get_logger(__name__)


@dataclass
class TranscriptSegment:
    """Represents a segment of conversation."""
    speaker: str
    text: str
    start_time: float
    end_time: Optional[float] = None

    def to_dict(self) -> dict:
        """Convert to dictionary format."""
        return {
            'speaker': self.speaker,
            'text': self.text,
            'start_time': self.start_time,
            'end_time': self.end_time
        }


class TranscriptParser:
    """
    Parses transcript files in the format:
    [0.000] <Speaker_1> text here [5.500] more text
    """

    # Regex patterns
    TIMESTAMP_PATTERN = r'\[(\d+\.\d+)\]'
    SPEAKER_PATTERN = r'<(Speaker_\d+)>'

    def __init__(self):
        """Initialize parser."""
        logger.info("Initialized TranscriptParser")

    def parse_file(self, filepath: Path) -> List[TranscriptSegment]:
        """
        Parse a transcript file into segments.

        Args:
            filepath: Path to transcript file

        Returns:
            List of TranscriptSegment objects
        """
        logger.info(f"Parsing transcript: {filepath.name}")

        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()

        segments = self.parse_content(content)
        logger.info(f"Parsed {len(segments)} segments from {filepath.name}")

        return segments

    def parse_content(self, content: str) -> List[TranscriptSegment]:
        """
        Parse transcript content into segments.

        Args:
            content: Raw transcript text

        Returns:
            List of TranscriptSegment objects
        """
        segments = []

        # Split by timestamps to get chunks
        parts = re.split(self.TIMESTAMP_PATTERN, content)

        # parts will be: ['', timestamp1, content1, timestamp2, content2, ...]
        # Process pairs of (timestamp, content)
        i = 1  # Start at first timestamp
        while i < len(parts) - 1:
            timestamp = float(parts[i])
            content_chunk = parts[i + 1].strip()

            if content_chunk:
                # Parse this chunk for speaker and text
                segment = self._parse_chunk(timestamp, content_chunk)
                if segment:
                    segments.append(segment)

            i += 2

        # Calculate end times (use next segment's start time)
        for j in range(len(segments) - 1):
            segments[j].end_time = segments[j + 1].start_time

        # Last segment's end time stays None (will be set to audio duration later)

        return segments

    def _parse_chunk(self, timestamp: float, chunk: str) -> Optional[TranscriptSegment]:
        """
        Parse a chunk of text with speaker and content.

        Args:
            timestamp: Start timestamp for this chunk
            chunk: Text chunk (may contain speaker tag)

        Returns:
            TranscriptSegment or None if chunk is empty
        """
        # Look for speaker tag
        speaker_match = re.search(self.SPEAKER_PATTERN, chunk)

        if speaker_match:
            speaker = speaker_match.group(1)
            # Remove speaker tag from text
            text = re.sub(self.SPEAKER_PATTERN, '', chunk).strip()
        else:
            # No speaker tag, might be continuation
            speaker = "Unknown"
            text = chunk.strip()

        if not text:
            return None

        return TranscriptSegment(
            speaker=speaker,
            text=text,
            start_time=timestamp,
            end_time=None  # Will be filled later
        )

    def segments_to_dict(self, segments: List[TranscriptSegment]) -> dict:
        """
        Convert segments to dictionary format for JSON export.

        Args:
            segments: List of TranscriptSegment objects

        Returns:
            Dictionary with segments and metadata
        """
        return {
            'segments': [seg.to_dict() for seg in segments],
            'total_segments': len(segments),
            'speakers': list(set(seg.speaker for seg in segments))
        }


def main():
    """Test the parser with a sample transcript."""
    from ..utils.logger import setup_logger

    # Setup logging
    setup_logger(__name__, level=20)  # INFO level

    # Create test transcript content
    test_content = """
    [0.000] <Speaker_1> Hello, I'm from Dallas, Texas.
    [3.500] <Speaker_2> Nice to meet you! I visited Houston on Friday.
    [8.200] <Speaker_1> That's great. I was there in January.
    [12.100] <Speaker_2> The weather was nice.
    """

    # Parse
    parser = TranscriptParser()
    segments = parser.parse_content(test_content)

    # Display results
    print("\n=== Parsed Segments ===")
    for i, seg in enumerate(segments):
        print(f"\nSegment {i + 1}:")
        print(f"  Speaker: {seg.speaker}")
        print(f"  Time: {seg.start_time}s - {seg.end_time}s")
        print(f"  Text: {seg.text}")

    # Convert to dict
    result = parser.segments_to_dict(segments)
    print(f"\n=== Summary ===")
    print(f"Total segments: {result['total_segments']}")
    print(f"Speakers: {', '.join(result['speakers'])}")


if __name__ == "__main__":
    main()
