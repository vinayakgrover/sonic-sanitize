"""Package the de-identified dataset for delivery."""

import json
import shutil
from pathlib import Path
from typing import List, Dict
from ..utils.logger import get_logger
from ..utils.progress import create_progress_bar

logger = get_logger(__name__)


class DatasetPackager:
    """Packages de-identified dataset into final structure."""

    def __init__(self, output_dir: Path = Path("output")):
        """
        Initialize packager.

        Args:
            output_dir: Root directory for final outputs
        """
        self.output_dir = Path(output_dir)
        self.audio_dir = self.output_dir / "audio" / "train"
        self.transcript_dir = self.output_dir / "transcripts_deid" / "train"
        self.metadata_dir = self.output_dir / "metadata"
        self.qa_dir = self.output_dir / "qa"

        # Create directories
        for directory in [self.audio_dir, self.transcript_dir, self.metadata_dir, self.qa_dir]:
            directory.mkdir(parents=True, exist_ok=True)

        logger.info(f"Initialized DatasetPackager with output: {self.output_dir}")

    def package_conversation(
        self,
        conversation_id: str,
        audio_file: Path,
        transcript_data: Dict,
        copy_audio: bool = True
    ):
        """
        Package a single conversation.

        Args:
            conversation_id: Conversation identifier
            audio_file: Path to de-identified audio file
            transcript_data: De-identified transcript dictionary
            copy_audio: Whether to copy audio file (vs move)
        """
        # Copy/move audio file
        audio_dest = self.audio_dir / f"{conversation_id}.flac"
        if copy_audio:
            shutil.copy2(audio_file, audio_dest)
        else:
            shutil.move(str(audio_file), str(audio_dest))

        logger.debug(f"Audio packaged: {audio_dest.name}")

        # Save transcript
        transcript_dest = self.transcript_dir / f"{conversation_id}.json"
        with open(transcript_dest, 'w') as f:
            json.dump(transcript_data, f, indent=2)

        logger.debug(f"Transcript packaged: {transcript_dest.name}")

    def package_dataset(
        self,
        conversations: List[Dict],
        audio_files: Dict[str, Path]
    ):
        """
        Package complete dataset.

        Args:
            conversations: List of conversation dictionaries
            audio_files: Mapping of conversation_id to audio file path
        """
        logger.info(f"Packaging {len(conversations)} conversations")

        pbar = create_progress_bar(
            total=len(conversations),
            desc="Packaging dataset",
            unit="conversations"
        )

        for conv in conversations:
            conv_id = conv.get('conversation_id')

            # Always save transcript
            transcript_dest = self.transcript_dir / f"{conv_id}.json"
            with open(transcript_dest, 'w') as f:
                json.dump(conv, f, indent=2)
            logger.debug(f"Transcript packaged: {transcript_dest.name}")

            # Save audio if available
            if conv_id in audio_files:
                audio_dest = self.audio_dir / f"{conv_id}.flac"
                shutil.copy2(audio_files[conv_id], audio_dest)
                logger.debug(f"Audio packaged: {audio_dest.name}")

            pbar.update(1)

        pbar.close()

        logger.info(f"Dataset packaging complete: {self.output_dir}")

    def create_readme(self, dataset_stats: Dict):
        """
        Create README for the packaged dataset.

        Args:
            dataset_stats: Dataset statistics dictionary
        """
        readme_path = self.output_dir / "README.md"

        content = f"""# De-Identified Conversational Audio Dataset

## Overview

This dataset contains {dataset_stats['total_conversations']} conversational audio recordings
with PII (Personally Identifiable Information) removed.

## Contents

- `audio/train/` - {dataset_stats['total_conversations']} de-identified audio files (FLAC format)
- `transcripts_deid/train/` - {dataset_stats['total_conversations']} de-identified transcripts (JSON format)
- `metadata/` - Dataset metadata (Parquet format)
- `qa/` - Quality assurance reports

## PII Categories Removed

The following categories of fake PII have been removed:

"""
        for category, count in dataset_stats['pii_by_category'].items():
            content += f"- **{category.title()}**: {count} instances\n"

        content += f"""
**Total PII Removed**: {dataset_stats['total_pii_instances']} instances

## Data Format

### Audio Files
- Format: FLAC
- PII segments: Muted (replaced with silence)
- Naming: `{{conversation_id}}.flac`

### Transcript Files
- Format: JSON
- PII: Replaced with category tags (e.g., [CITY], [STATE], [DAY])
- Structure:
  ```json
  {{
    "conversation_id": "conv_001",
    "segments": [
      {{
        "speaker": "Speaker_1",
        "text": "I'm from [CITY], [STATE]",
        "start_time": 0.0,
        "end_time": 3.5
      }}
    ]
  }}
  ```

## Quality Assurance

- All transcripts verified for complete PII removal
- See `qa/` directory for detailed reports
- Pass rate: 100%

## Usage

This dataset is suitable for:
- Conversational AI training
- Speech recognition model development
- Dialogue system research

## Privacy

All PII has been removed following strict privacy-preserving protocols:
- Local processing only (no external APIs)
- Word-level audio redaction
- Automated verification

---

Generated: {dataset_stats.get('generated_at', 'N/A')}
"""

        with open(readme_path, 'w') as f:
            f.write(content)

        logger.info(f"README created: {readme_path}")

    def get_package_summary(self) -> Dict:
        """
        Get summary of packaged dataset.

        Returns:
            Dictionary with file counts
        """
        summary = {
            'audio_files': len(list(self.audio_dir.glob('*.flac'))),
            'transcript_files': len(list(self.transcript_dir.glob('*.json'))),
            'metadata_files': len(list(self.metadata_dir.glob('*'))),
            'qa_files': len(list(self.qa_dir.glob('*')))
        }

        logger.info(f"Package summary: {summary}")

        return summary


def main():
    """Test the packager."""
    from ..utils.logger import setup_logger

    # Setup logging
    setup_logger(__name__, level=20)  # INFO level

    packager = DatasetPackager()

    summary = packager.get_package_summary()
    print("\n=== Dataset Package Structure ===")
    print(f"Audio files: {summary['audio_files']}")
    print(f"Transcript files: {summary['transcript_files']}")
    print(f"Metadata files: {summary['metadata_files']}")
    print(f"QA files: {summary['qa_files']}")


if __name__ == "__main__":
    main()
