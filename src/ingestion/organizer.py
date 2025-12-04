"""Organize downloaded files into proper directory structure."""

from pathlib import Path
import shutil
from typing import Dict, List
from ..utils.logger import get_logger
from ..utils.progress import create_progress_bar

logger = get_logger(__name__)


class DataOrganizer:
    """Organizes downloaded files into standardized directory structure."""

    def __init__(self, raw_dir: Path = Path("data/raw")):
        """
        Initialize organizer.

        Args:
            raw_dir: Root directory for raw data
        """
        self.raw_dir = Path(raw_dir)
        self.audio_dir = self.raw_dir / "audio"
        self.transcript_dir = self.raw_dir / "transcripts"
        self.metadata_dir = self.raw_dir / "metadata"

        # Create directories
        self.audio_dir.mkdir(parents=True, exist_ok=True)
        self.transcript_dir.mkdir(parents=True, exist_ok=True)
        self.metadata_dir.mkdir(parents=True, exist_ok=True)

        logger.info(f"Initialized organizer with root: {self.raw_dir}")

    def organize_files(self, downloaded_files: Dict[str, List[Path]]) -> Dict[str, List[Path]]:
        """
        Organize downloaded files into proper structure.

        Args:
            downloaded_files: Dictionary from downloader with 'audio', 'transcripts', 'metadata' keys

        Returns:
            Dictionary with organized file paths
        """
        logger.info("Organizing downloaded files")

        organized = {
            'audio': [],
            'transcripts': [],
            'metadata': []
        }

        total_files = sum(len(files) for files in downloaded_files.values())
        pbar = create_progress_bar(total=total_files, desc="Organizing files", unit="files")

        # Organize audio files
        for audio_file in downloaded_files.get('audio', []):
            target = self.audio_dir / audio_file.name
            if audio_file != target:
                shutil.move(str(audio_file), str(target))
            organized['audio'].append(target)
            pbar.update(1)

        # Organize transcript files
        for transcript_file in downloaded_files.get('transcripts', []):
            target = self.transcript_dir / transcript_file.name
            if transcript_file != target:
                shutil.move(str(transcript_file), str(target))
            organized['transcripts'].append(target)
            pbar.update(1)

        # Organize metadata files
        for metadata_file in downloaded_files.get('metadata', []):
            target = self.metadata_dir / metadata_file.name
            if metadata_file != target:
                shutil.move(str(metadata_file), str(target))
            organized['metadata'].append(target)
            pbar.update(1)

        pbar.close()

        logger.info(f"Organization complete: {len(organized['audio'])} audio, "
                   f"{len(organized['transcripts'])} transcripts, "
                   f"{len(organized['metadata'])} metadata files")

        return organized

    def verify_structure(self) -> Dict[str, int]:
        """
        Verify the organized directory structure.

        Returns:
            Dictionary with counts of files in each directory
        """
        counts = {
            'audio': len(list(self.audio_dir.glob('*.wav'))),
            'transcripts': len(list(self.transcript_dir.glob('*.txt'))),
            'metadata': len(list(self.metadata_dir.glob('*.csv')))
        }

        logger.info(f"Directory structure verified: {counts}")
        return counts

    def get_conversation_pairs(self) -> List[tuple]:
        """
        Get pairs of matching audio and transcript files.

        Returns:
            List of (audio_path, transcript_path) tuples
        """
        audio_files = sorted(self.audio_dir.glob('*.wav'))
        transcript_files = sorted(self.transcript_dir.glob('*.txt'))

        # Match by filename
        pairs = []
        audio_dict = {f.stem: f for f in audio_files}
        transcript_dict = {f.stem: f for f in transcript_files}

        for name in audio_dict.keys():
            if name in transcript_dict:
                pairs.append((audio_dict[name], transcript_dict[name]))

        logger.info(f"Found {len(pairs)} matching audio-transcript pairs")
        return pairs


def main():
    """Test the organizer."""
    from ..utils.logger import setup_logger

    # Setup logging
    setup_logger(__name__, level=20)  # INFO level

    # Create organizer
    organizer = DataOrganizer()

    # Verify current structure
    counts = organizer.verify_structure()
    print("\n=== Directory Structure ===")
    print(f"Audio files: {counts['audio']}")
    print(f"Transcript files: {counts['transcripts']}")
    print(f"Metadata files: {counts['metadata']}")

    # Get conversation pairs
    pairs = organizer.get_conversation_pairs()
    if pairs:
        print(f"\n=== Conversation Pairs ===")
        print(f"Found {len(pairs)} pairs")
        print(f"First pair: {pairs[0][0].name} <-> {pairs[0][1].name}")


if __name__ == "__main__":
    main()
