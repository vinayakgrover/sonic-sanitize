"""Generate metadata for the packaged dataset."""

import pandas as pd
from pathlib import Path
from typing import List, Dict
from ..utils.logger import get_logger

logger = get_logger(__name__)


class MetadataGenerator:
    """Generates metadata files for the de-identified dataset."""

    def __init__(self):
        """Initialize metadata generator."""
        logger.info("Initialized MetadataGenerator")

    def generate_conversations_metadata(
        self,
        conversations: List[Dict],
        output_path: Path
    ):
        """
        Generate conversations.parquet metadata file.

        Args:
            conversations: List of conversation dictionaries
            output_path: Path to save Parquet file
        """
        logger.info(f"Generating conversations metadata for {len(conversations)} conversations")

        rows = []
        for conv in conversations:
            conv_id = conv.get('conversation_id')
            segments = conv.get('segments', [])
            pii_summary = conv.get('pii_summary', {})

            # Calculate metadata
            if segments:
                if isinstance(segments[0], dict):
                    duration = segments[-1].get('end_time', 0)
                    speakers = list(set(s.get('speaker') for s in segments))
                else:
                    duration = segments[-1].end_time if segments[-1].end_time else 0
                    speakers = list(set(s.speaker for s in segments))
            else:
                duration = 0
                speakers = []

            row = {
                'conversation_id': conv_id,
                'num_segments': len(segments),
                'duration_seconds': duration,
                'num_speakers': len(speakers),
                'speakers': ','.join(speakers),
                'total_pii_found': pii_summary.get('total_pii_found', 0),
                'pii_categories': ','.join(pii_summary.get('categories', {}).keys()),
                'audio_file': f"{conv_id}.flac",
                'transcript_file': f"{conv_id}.json"
            }

            # Add PII category counts
            for category, count in pii_summary.get('categories', {}).items():
                row[f'pii_{category}'] = count

            rows.append(row)

        # Create DataFrame
        df = pd.DataFrame(rows)

        # Save as Parquet
        output_path.parent.mkdir(parents=True, exist_ok=True)
        df.to_parquet(output_path, index=False)

        logger.info(f"Conversations metadata saved: {output_path}")
        logger.info(f"  Columns: {list(df.columns)}")
        logger.info(f"  Rows: {len(df)}")

    def generate_dataset_manifest(
        self,
        dataset_stats: Dict,
        verification_results: Dict,
        output_path: Path
    ):
        """
        Generate dataset manifest with overall information.

        Args:
            dataset_stats: Dataset statistics
            verification_results: Verification results
            output_path: Path to save manifest
        """
        logger.info("Generating dataset manifest")

        manifest = {
            'dataset_name': 'PII De-Identified Conversational Audio',
            'version': '1.0',
            'total_conversations': dataset_stats['total_conversations'],
            'total_segments': dataset_stats['total_segments'],
            'total_duration_seconds': dataset_stats['total_duration'],
            'total_pii_removed': dataset_stats['total_pii_instances'],
            'pii_by_category': dataset_stats['pii_by_category'],
            'verification_passed': verification_results['passed'],
            'verification_pass_rate': verification_results['pass_rate'],
            'file_formats': {
                'audio': 'FLAC',
                'transcripts': 'JSON',
                'metadata': 'Parquet'
            },
            'directories': {
                'audio': 'audio/train/',
                'transcripts': 'transcripts_deid/train/',
                'metadata': 'metadata/',
                'qa': 'qa/'
            }
        }

        # Save as JSON
        import json
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, 'w') as f:
            json.dump(manifest, f, indent=2)

        logger.info(f"Dataset manifest saved: {output_path}")


def main():
    """Test the metadata generator."""
    from ..utils.logger import setup_logger

    # Setup logging
    setup_logger(__name__, level=20)  # INFO level

    print("\n=== Metadata Generator Ready ===")
    print("Can generate:")
    print("  - conversations.parquet")
    print("  - dataset_manifest.json")
    print("  - Complete metadata with PII statistics")


if __name__ == "__main__":
    main()
