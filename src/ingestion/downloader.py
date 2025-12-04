"""Download dataset files from HuggingFace."""

from pathlib import Path
from typing import List, Optional
from huggingface_hub import list_repo_files, hf_hub_download
from ..utils.logger import get_logger
from ..utils.progress import create_progress_bar

logger = get_logger(__name__)


class HuggingFaceDownloader:
    """Downloads dataset files from HuggingFace repository."""

    def __init__(
        self,
        repo_id: str = "Appenlimited/1000h-us-english-smartphone-conversation",
        output_dir: Path = Path("data/raw")
    ):
        """
        Initialize downloader.

        Args:
            repo_id: HuggingFace repository ID
            output_dir: Directory to save downloaded files
        """
        self.repo_id = repo_id
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        logger.info(f"Initialized downloader for {repo_id}")

    def list_files(self, pattern: Optional[str] = None) -> List[str]:
        """
        List all files in the repository.

        Args:
            pattern: Optional pattern to filter files (e.g., '.wav', '.txt')

        Returns:
            List of file paths in the repository
        """
        logger.info(f"Listing files from {self.repo_id}")
        files = list_repo_files(self.repo_id, repo_type="dataset")

        if pattern:
            files = [f for f in files if pattern in f]
            logger.info(f"Found {len(files)} files matching pattern '{pattern}'")
        else:
            logger.info(f"Found {len(files)} total files")

        return files

    def download_file(self, filename: str) -> Path:
        """
        Download a single file from the repository.

        Args:
            filename: Path to file in the repository

        Returns:
            Path to downloaded file
        """
        logger.debug(f"Downloading {filename}")
        local_path = hf_hub_download(
            repo_id=self.repo_id,
            filename=filename,
            repo_type="dataset",
            local_dir=self.output_dir,
            local_dir_use_symlinks=False
        )
        return Path(local_path)

    def download_dataset(
        self,
        audio_only: bool = False,
        transcript_only: bool = False,
        limit: Optional[int] = None
    ) -> dict:
        """
        Download the complete dataset or subset.

        Args:
            audio_only: Download only audio files
            transcript_only: Download only transcript files
            limit: Maximum number of conversations to download (None = all)

        Returns:
            Dictionary with downloaded file paths by type
        """
        logger.info("Starting dataset download")

        # Get all files
        all_files = self.list_files()

        # Categorize files
        audio_files = [f for f in all_files if f.endswith('.wav')]
        transcript_files = [f for f in all_files if f.endswith('.txt') and 'TRANSCRIPTION_AUTO_SEGMENTED' in f]
        metadata_files = [f for f in all_files if f.endswith('.csv')]

        # Apply limit if specified
        if limit:
            audio_files = audio_files[:limit]
            transcript_files = transcript_files[:limit]
            logger.info(f"Limited to {limit} conversations")

        # Determine what to download
        files_to_download = []
        if not transcript_only:
            files_to_download.extend(audio_files)
        if not audio_only:
            files_to_download.extend(transcript_files)
            files_to_download.extend(metadata_files)

        logger.info(f"Downloading {len(files_to_download)} files")

        # Download with progress bar
        downloaded = {
            'audio': [],
            'transcripts': [],
            'metadata': []
        }

        pbar = create_progress_bar(
            total=len(files_to_download),
            desc="Downloading files",
            unit="files"
        )

        for file in files_to_download:
            try:
                local_path = self.download_file(file)

                # Categorize downloaded file
                if file.endswith('.wav'):
                    downloaded['audio'].append(local_path)
                elif file.endswith('.txt'):
                    downloaded['transcripts'].append(local_path)
                elif file.endswith('.csv'):
                    downloaded['metadata'].append(local_path)

                pbar.update(1)
            except Exception as e:
                logger.error(f"Failed to download {file}: {e}")

        pbar.close()

        logger.info(f"Download complete: {len(downloaded['audio'])} audio, "
                   f"{len(downloaded['transcripts'])} transcripts, "
                   f"{len(downloaded['metadata'])} metadata files")

        return downloaded


def main():
    """Test the downloader by downloading 3 sample conversations."""
    from ..utils.logger import setup_logger

    # Setup logging
    setup_logger(__name__, level=20)  # INFO level

    # Create downloader
    downloader = HuggingFaceDownloader()

    # Download first 3 conversations for testing
    logger.info("Testing downloader with 3 conversations")
    result = downloader.download_dataset(limit=3)

    # Print summary
    print("\n=== Download Summary ===")
    print(f"Audio files: {len(result['audio'])}")
    print(f"Transcript files: {len(result['transcripts'])}")
    print(f"Metadata files: {len(result['metadata'])}")

    if result['audio']:
        print(f"\nFirst audio file: {result['audio'][0]}")
    if result['transcripts']:
        print(f"First transcript: {result['transcripts'][0]}")


if __name__ == "__main__":
    main()
