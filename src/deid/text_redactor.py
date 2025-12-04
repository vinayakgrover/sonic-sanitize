"""Replace PII in text with tags."""

from typing import List, Dict
from .pii_detector import PIIMatch
from ..utils.logger import get_logger

logger = get_logger(__name__)


class TextRedactor:
    """Replaces detected PII with placeholder tags."""

    def __init__(self):
        """Initialize text redactor."""
        logger.info("Initialized TextRedactor")

    def redact_text(self, text: str, matches: List[PIIMatch]) -> tuple[str, List[Dict]]:
        """
        Replace PII in text with tags.

        Args:
            text: Original text
            matches: List of PIIMatch objects (must be sorted by position)

        Returns:
            Tuple of (redacted_text, replacements_log)
        """
        if not matches:
            return text, []

        # Sort matches by position (descending) to replace from end to start
        sorted_matches = sorted(matches, key=lambda x: x.start, reverse=True)

        # Track replacements
        replacements = []
        redacted = text

        # Replace from end to start to preserve positions
        for match in sorted_matches:
            # Replace the PII value with its tag
            redacted = redacted[:match.start] + match.tag + redacted[match.end:]

            # Log the replacement
            replacements.append({
                'original': match.value,
                'category': match.category,
                'tag': match.tag,
                'position': match.start
            })

        # Reverse replacements list to show chronological order
        replacements.reverse()

        logger.debug(f"Redacted {len(replacements)} PII instances")

        return redacted, replacements

    def redact_segments(self, segments: List, pii_matches: Dict[int, List[PIIMatch]]) -> tuple[List, Dict]:
        """
        Redact PII in multiple segments.

        NOTE: pii_matches contains PIIMatch objects with GLOBAL offsets
        (relative to full transcript). We need to convert them to LOCAL
        offsets (relative to individual segment) before redacting.

        Args:
            segments: List of TranscriptSegment objects
            pii_matches: Dictionary mapping segment index to PIIMatch list
                        (with global offsets from PIIDetector)

        Returns:
            Tuple of (redacted_segments, redaction_log)
        """
        from ..utils.transcript_utils import prepare_full_transcript

        redacted_segments = []
        redaction_log = {
            'total_replacements': 0,
            'by_segment': {},
            'by_category': {}
        }

        # Get segment offsets to convert global→local positions
        _, segment_offsets = prepare_full_transcript(segments)

        for i, segment in enumerate(segments):
            if i in pii_matches:
                # Convert global offsets to local offsets for this segment
                segment_offset = segment_offsets[i]
                local_matches = []

                for match in pii_matches[i]:
                    # Create new match with local offsets
                    local_match = PIIMatch(
                        category=match.category,
                        value=match.value,
                        start=match.start - segment_offset,  # Global → Local
                        end=match.end - segment_offset,
                        tag=match.tag
                    )
                    local_matches.append(local_match)

                # Redact this segment with local offsets
                redacted_text, replacements = self.redact_text(segment.text, local_matches)

                # Create new segment with redacted text
                from ..parsing.transcript_parser import TranscriptSegment
                redacted_segment = TranscriptSegment(
                    speaker=segment.speaker,
                    text=redacted_text,
                    start_time=segment.start_time,
                    end_time=segment.end_time
                )

                redacted_segments.append(redacted_segment)

                # Log redactions for this segment
                redaction_log['by_segment'][i] = replacements
                redaction_log['total_replacements'] += len(replacements)

                # Update category counts
                for repl in replacements:
                    category = repl['category']
                    redaction_log['by_category'][category] = \
                        redaction_log['by_category'].get(category, 0) + 1
            else:
                # No PII, keep original segment
                redacted_segments.append(segment)

        logger.info(f"Redacted {redaction_log['total_replacements']} PII instances across {len(pii_matches)} segments")

        return redacted_segments, redaction_log


def main():
    """Test the text redactor."""
    from ..utils.logger import setup_logger
    from .pii_detector import PIIDetector

    # Setup logging
    setup_logger(__name__, level=20)  # INFO level

    # Create detector and redactor
    detector = PIIDetector()
    redactor = TextRedactor()

    # Test text
    test_text = "I'm from Dallas, Texas and I visited Houston on Friday in January."

    print("\n=== Testing Text Redaction ===")
    print(f"Original: {test_text}")

    # Detect PII
    matches = detector.detect_in_text(test_text)

    # Redact
    redacted_text, replacements = redactor.redact_text(test_text, matches)

    print(f"\nRedacted: {redacted_text}")
    print(f"\nReplacements made:")
    for repl in replacements:
        print(f"  '{repl['original']}' -> {repl['tag']} ({repl['category']})")


if __name__ == "__main__":
    main()
