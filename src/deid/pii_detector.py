"""Detect PII in text using pattern matching."""

import re
from pathlib import Path
from typing import List, Dict
from dataclasses import dataclass
from .config_loader import ConfigLoader
from ..utils.logger import get_logger

logger = get_logger(__name__)


@dataclass
class PIIMatch:
    """Represents a detected PII instance."""
    category: str
    value: str
    start: int
    end: int
    tag: str

    def to_dict(self) -> dict:
        """Convert to dictionary format."""
        return {
            'category': self.category,
            'value': self.value,
            'start': self.start,
            'end': self.end,
            'tag': self.tag
        }


class PIIDetector:
    """Detects PII in text using regex pattern matching."""

    def __init__(self, config_path: Path = Path("config.yaml")):
        """
        Initialize PII detector.

        Args:
            config_path: Path to config.yaml file
        """
        self.config_loader = ConfigLoader(config_path)
        self.patterns = {}
        self._compile_patterns()
        logger.info(f"Initialized PIIDetector with {len(self.patterns)} categories")

    def _compile_patterns(self):
        """Compile regex patterns for each PII category."""
        for category_name, category_data in self.config_loader.get_all_categories().items():
            items = self.config_loader.get_category_items(category_name)

            if not items:
                continue

            # Sort by length (longest first) to match longer items first
            items_sorted = sorted(items, key=len, reverse=True)

            # Escape special regex characters and create pattern with word boundaries
            escaped_items = [re.escape(item) for item in items_sorted]
            pattern = r'\b(' + '|'.join(escaped_items) + r')\b'

            # Compile pattern (case-insensitive by default)
            self.patterns[category_name] = re.compile(pattern, re.IGNORECASE)

            logger.debug(f"Compiled pattern for {category_name} with {len(items)} items")

    def detect_in_text(self, text: str) -> List[PIIMatch]:
        """
        Detect all PII instances in text.

        Args:
            text: Text to scan for PII

        Returns:
            List of PIIMatch objects
        """
        matches = []

        for category_name, pattern in self.patterns.items():
            tag = self.config_loader.get_category_tag(category_name)

            for match in pattern.finditer(text):
                pii_match = PIIMatch(
                    category=category_name,
                    value=match.group(0),
                    start=match.start(),
                    end=match.end(),
                    tag=tag
                )
                matches.append(pii_match)

        # Sort by position
        matches.sort(key=lambda x: x.start)

        return matches

    def detect_in_segments(self, segments: List) -> Dict[int, List[PIIMatch]]:
        """
        Detect PII in multiple text segments with global offsets.

        This method detects PII in each segment and adjusts the match offsets
        to be relative to the full concatenated transcript (not just the segment).
        This ensures consistency with forced alignment and text redaction.

        Args:
            segments: List of TranscriptSegment objects

        Returns:
            Dictionary mapping segment index to list of PIIMatch objects
            (with global offsets relative to full transcript)
        """
        from ..utils.transcript_utils import prepare_full_transcript

        results = {}

        # Get segment offsets in full transcript
        _, segment_offsets = prepare_full_transcript(segments)

        for i, segment in enumerate(segments):
            # Detect PII in this segment (gets local offsets)
            local_matches = self.detect_in_text(segment.text)

            if local_matches:
                # Adjust offsets to be global (relative to full transcript)
                global_matches = []
                for match in local_matches:
                    global_match = PIIMatch(
                        category=match.category,
                        value=match.value,
                        start=match.start + segment_offsets[i],  # Convert to global offset
                        end=match.end + segment_offsets[i],
                        tag=match.tag
                    )
                    global_matches.append(global_match)

                results[i] = global_matches

        logger.info(f"Detected PII in {len(results)} of {len(segments)} segments")

        return results

    def get_pii_summary(self, matches: List[PIIMatch]) -> Dict[str, int]:
        """
        Get summary statistics of detected PII.

        Args:
            matches: List of PIIMatch objects

        Returns:
            Dictionary with counts by category
        """
        summary = {}
        for match in matches:
            summary[match.category] = summary.get(match.category, 0) + 1
        return summary


def main():
    """Test the PII detector."""
    from ..utils.logger import setup_logger
    from ..parsing.transcript_parser import TranscriptParser

    # Setup logging
    setup_logger(__name__, level=20)  # INFO level

    # Create detector
    detector = PIIDetector()

    # Test with sample text
    test_text = "I'm from Dallas, Texas and I visited Houston on Friday in January."

    print("\n=== Testing PII Detection ===")
    print(f"Text: {test_text}")

    # Detect PII
    matches = detector.detect_in_text(test_text)

    print(f"\nFound {len(matches)} PII instances:")
    for match in matches:
        print(f"  {match.value} ({match.category}) -> {match.tag} [pos: {match.start}-{match.end}]")

    # Summary
    summary = detector.get_pii_summary(matches)
    print(f"\nSummary by category:")
    for category, count in summary.items():
        print(f"  {category}: {count}")


if __name__ == "__main__":
    main()
