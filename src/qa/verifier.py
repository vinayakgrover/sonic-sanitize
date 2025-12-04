"""Verify that PII has been completely removed."""

from pathlib import Path
from typing import List, Dict
from ..deid.pii_detector import PIIDetector
from ..utils.logger import get_logger

logger = get_logger(__name__)


class PIIVerifier:
    """Verifies that all PII has been removed from de-identified transcripts."""

    def __init__(self, config_path: Path = Path("config.yaml")):
        """
        Initialize verifier.

        Args:
            config_path: Path to config.yaml file
        """
        self.detector = PIIDetector(config_path)
        logger.info("Initialized PIIVerifier")

    def verify_text(self, text: str) -> Dict:
        """
        Verify that no PII remains in text.

        Args:
            text: De-identified text to verify

        Returns:
            Dictionary with verification results
        """
        matches = self.detector.detect_in_text(text)

        return {
            'passed': len(matches) == 0,
            'pii_found': len(matches),
            'matches': [
                {
                    'value': m.value,
                    'category': m.category,
                    'position': m.start
                }
                for m in matches
            ]
        }

    def verify_segments(self, segments: List) -> Dict:
        """
        Verify that no PII remains in segments.

        Args:
            segments: List of TranscriptSegment objects

        Returns:
            Dictionary with verification results
        """
        results = {
            'total_segments': len(segments),
            'failed_segments': [],
            'total_pii_found': 0,
            'passed': True
        }

        for i, segment in enumerate(segments):
            verification = self.verify_text(segment.text)

            if not verification['passed']:
                results['failed_segments'].append({
                    'segment_index': i,
                    'speaker': segment.speaker,
                    'text': segment.text,
                    'pii_found': verification['matches']
                })
                results['total_pii_found'] += verification['pii_found']
                results['passed'] = False

        logger.info(f"Verification: {results['total_pii_found']} PII instances found in "
                   f"{len(results['failed_segments'])} segments")

        return results

    def verify_dataset(self, conversations: List[Dict]) -> Dict:
        """
        Verify entire dataset.

        Args:
            conversations: List of conversation dictionaries with segments

        Returns:
            Dictionary with overall verification results
        """
        dataset_results = {
            'total_conversations': len(conversations),
            'failed_conversations': [],
            'total_pii_found': 0,
            'passed': True
        }

        for conv in conversations:
            conv_id = conv.get('conversation_id', 'unknown')
            segments = conv.get('segments', [])

            # Convert dict segments back to objects if needed
            from ..parsing.transcript_parser import TranscriptSegment
            if segments and isinstance(segments[0], dict):
                segments = [
                    TranscriptSegment(
                        speaker=s['speaker'],
                        text=s['text'],
                        start_time=s['start_time'],
                        end_time=s.get('end_time')
                    )
                    for s in segments
                ]

            verification = self.verify_segments(segments)

            if not verification['passed']:
                dataset_results['failed_conversations'].append({
                    'conversation_id': conv_id,
                    'pii_found': verification['total_pii_found'],
                    'failed_segments': verification['failed_segments']
                })
                dataset_results['total_pii_found'] += verification['total_pii_found']
                dataset_results['passed'] = False

        pass_rate = 1.0 - (len(dataset_results['failed_conversations']) /
                          len(conversations) if conversations else 0)

        dataset_results['pass_rate'] = pass_rate

        logger.info(f"Dataset verification: {dataset_results['total_pii_found']} PII found, "
                   f"pass rate: {pass_rate:.2%}")

        return dataset_results


def main():
    """Test the verifier."""
    from ..utils.logger import setup_logger

    # Setup logging
    setup_logger(__name__, level=20)  # INFO level

    verifier = PIIVerifier()

    # Test with text that should pass
    clean_text = "I'm from [CITY], [STATE] and visited [CITY] on [DAY]."
    result = verifier.verify_text(clean_text)
    print(f"\n=== Test 1: Clean Text ===")
    print(f"Text: {clean_text}")
    print(f"Passed: {result['passed']}")

    # Test with text that should fail
    dirty_text = "I'm from Dallas, Texas and visited Houston on Friday."
    result = verifier.verify_text(dirty_text)
    print(f"\n=== Test 2: Text with PII ===")
    print(f"Text: {dirty_text}")
    print(f"Passed: {result['passed']}")
    print(f"PII found: {result['pii_found']}")
    for match in result['matches']:
        print(f"  - {match['value']} ({match['category']})")


if __name__ == "__main__":
    main()
