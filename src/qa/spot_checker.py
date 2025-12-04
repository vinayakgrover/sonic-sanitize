"""Generate spot-check samples for manual QA."""

import json
import random
from pathlib import Path
from typing import List, Dict
from ..utils.logger import get_logger

logger = get_logger(__name__)


class SpotChecker:
    """Generates samples for manual spot-checking of de-identification quality."""

    def __init__(self, seed: int = 42):
        """
        Initialize spot checker.

        Args:
            seed: Random seed for reproducibility
        """
        random.seed(seed)
        logger.info("Initialized SpotChecker")

    def generate_samples(
        self,
        conversations: List[Dict],
        num_samples: int = 10
    ) -> List[Dict]:
        """
        Generate random samples from conversations.

        Args:
            conversations: List of conversation dictionaries
            num_samples: Number of samples to generate

        Returns:
            List of sample dictionaries
        """
        samples = []

        # Ensure we don't try to sample more than available
        num_samples = min(num_samples, len(conversations))

        selected_convs = random.sample(conversations, num_samples)

        for conv in selected_convs:
            conv_id = conv.get('conversation_id')
            segments = conv.get('segments', [])

            if not segments:
                continue

            # Pick a random segment
            segment = random.choice(segments)

            if isinstance(segment, dict):
                sample = {
                    'conversation_id': conv_id,
                    'segment_index': segments.index(segment),
                    'speaker': segment.get('speaker'),
                    'text': segment.get('text'),
                    'start_time': segment.get('start_time'),
                    'end_time': segment.get('end_time')
                }
            else:
                sample = {
                    'conversation_id': conv_id,
                    'segment_index': segments.index(segment),
                    'speaker': segment.speaker,
                    'text': segment.text,
                    'start_time': segment.start_time,
                    'end_time': segment.end_time
                }

            samples.append(sample)

        logger.info(f"Generated {len(samples)} spot-check samples")

        return samples

    def save_samples(self, samples: List[Dict], output_path: Path):
        """
        Save samples to JSONL file.

        Args:
            samples: List of sample dictionaries
            output_path: Path to save samples
        """
        output_path.parent.mkdir(parents=True, exist_ok=True)

        with open(output_path, 'w') as f:
            for sample in samples:
                f.write(json.dumps(sample) + '\n')

        logger.info(f"Saved {len(samples)} samples to {output_path}")

    def generate_comparison_samples(
        self,
        original_conversations: List[Dict],
        deid_conversations: List[Dict],
        num_samples: int = 5
    ) -> List[Dict]:
        """
        Generate side-by-side comparison samples.

        Args:
            original_conversations: Original conversations
            deid_conversations: De-identified conversations
            num_samples: Number of samples to generate

        Returns:
            List of comparison dictionaries
        """
        comparisons = []

        # Match conversations by ID
        orig_dict = {c.get('conversation_id'): c for c in original_conversations}
        deid_dict = {c.get('conversation_id'): c for c in deid_conversations}

        common_ids = list(set(orig_dict.keys()) & set(deid_dict.keys()))

        if not common_ids:
            logger.warning("No common conversation IDs found")
            return []

        num_samples = min(num_samples, len(common_ids))
        selected_ids = random.sample(common_ids, num_samples)

        for conv_id in selected_ids:
            orig_segments = orig_dict[conv_id].get('segments', [])
            deid_segments = deid_dict[conv_id].get('segments', [])

            if not orig_segments or not deid_segments:
                continue

            # Pick matching segment
            seg_idx = random.randint(0, min(len(orig_segments), len(deid_segments)) - 1)

            orig_seg = orig_segments[seg_idx]
            deid_seg = deid_segments[seg_idx]

            comparison = {
                'conversation_id': conv_id,
                'segment_index': seg_idx,
                'original': self._segment_to_dict(orig_seg),
                'de_identified': self._segment_to_dict(deid_seg)
            }

            comparisons.append(comparison)

        logger.info(f"Generated {len(comparisons)} comparison samples")

        return comparisons

    def _segment_to_dict(self, segment) -> Dict:
        """Convert segment to dict format."""
        if isinstance(segment, dict):
            return segment
        else:
            return {
                'speaker': segment.speaker,
                'text': segment.text,
                'start_time': segment.start_time,
                'end_time': segment.end_time
            }


def main():
    """Test the spot checker."""
    from ..utils.logger import setup_logger

    # Setup logging
    setup_logger(__name__, level=20)  # INFO level

    print("\n=== Spot Checker Ready ===")
    print("Can generate:")
    print("  - Random sample segments")
    print("  - Side-by-side comparisons")
    print("  - JSONL output for manual review")


if __name__ == "__main__":
    main()
