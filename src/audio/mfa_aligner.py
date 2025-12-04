"""
Montreal Forced Aligner (MFA) wrapper for word-level audio-transcript alignment.

This module provides precise word-level timing using MFA, enabling accurate PII redaction
at the word level instead of segment level.

Requirements:
- MFA installed and available in PATH (conda install -c conda-forge montreal-forced-aligner)
- Acoustic model (e.g., english_us_arpa)
- Pronunciation dictionary (e.g., english_us_arpa)

Usage:
    aligner = MFAAligner(
        acoustic_model="english_us_arpa",
        dictionary="english_us_arpa",
        temp_dir="/tmp/mfa_temp"
    )

    word_timings = aligner.align(
        audio_path="/path/to/audio.wav",
        transcript_text="hello world"
    )
"""

import logging
import subprocess
import shutil
import tempfile
from pathlib import Path
from typing import List, Dict, Optional, NamedTuple
from dataclasses import dataclass
import re


logger = logging.getLogger(__name__)


class MFANotAvailableError(Exception):
    """Raised when MFA is not installed or not found in PATH."""
    pass


class MFAAlignmentError(Exception):
    """Raised when MFA alignment fails."""
    pass


@dataclass
class WordTiming:
    """Represents timing information for a single word."""
    word: str
    start_time: float
    end_time: float

    @property
    def duration(self) -> float:
        """Duration of the word in seconds."""
        return self.end_time - self.start_time


class MFAAligner:
    """
    Montreal Forced Aligner wrapper for word-level audio-transcript alignment.

    Uses the MFA CLI tool to generate word-level timestamps from audio and transcript.

    Attributes:
        acoustic_model: Name or path to MFA acoustic model
        dictionary: Name or path to MFA pronunciation dictionary
        temp_dir: Directory for temporary MFA working files
        cleanup: Whether to delete temp files after alignment
    """

    def __init__(
        self,
        acoustic_model: str = "english_us_arpa",
        dictionary: str = "english_us_arpa",
        temp_dir: Optional[str] = None,
        cleanup: bool = True
    ):
        """
        Initialize MFA aligner.

        Args:
            acoustic_model: MFA acoustic model name or path
            dictionary: MFA pronunciation dictionary name or path
            temp_dir: Temporary directory for MFA files (creates if None)
            cleanup: Whether to clean up temp files after alignment

        Raises:
            MFANotAvailableError: If MFA is not installed or not in PATH
        """
        self.acoustic_model = acoustic_model
        self.dictionary = dictionary
        self.temp_dir = Path(temp_dir) if temp_dir else None
        self.cleanup = cleanup

        # Check if MFA is available
        if not self.is_mfa_available():
            raise MFANotAvailableError(
                "MFA (Montreal Forced Aligner) not found in PATH. "
                "Please install: conda install -c conda-forge montreal-forced-aligner"
            )

        logger.info(f"MFA aligner initialized with model={acoustic_model}, dict={dictionary}")

    @staticmethod
    def is_mfa_available() -> bool:
        """Check if MFA CLI is available in PATH."""
        return shutil.which("mfa") is not None

    def align(
        self,
        audio_path: str,
        transcript_text: str,
        conversation_id: Optional[str] = None
    ) -> List[WordTiming]:
        """
        Align audio with transcript to get word-level timings.

        Args:
            audio_path: Path to audio file (WAV recommended)
            transcript_text: Transcript text to align
            conversation_id: Optional conversation ID for logging

        Returns:
            List of WordTiming objects with word-level timestamps

        Raises:
            MFAAlignmentError: If alignment fails
        """
        audio_path = Path(audio_path)

        if not audio_path.exists():
            raise MFAAlignmentError(f"Audio file not found: {audio_path}")

        # Create temp directory structure for MFA
        with tempfile.TemporaryDirectory() as temp_base:
            temp_base = Path(temp_base)

            # MFA expects: input_dir/audio.wav and input_dir/audio.txt
            input_dir = temp_base / "input"
            output_dir = temp_base / "output"
            input_dir.mkdir()
            output_dir.mkdir()

            # Copy audio to input dir with same stem
            audio_copy = input_dir / f"{audio_path.stem}.wav"

            # Convert to WAV if needed (MFA prefers WAV)
            if audio_path.suffix.lower() != '.wav':
                self._convert_to_wav(audio_path, audio_copy)
            else:
                shutil.copy(audio_path, audio_copy)

            # Write transcript to matching .txt file
            transcript_file = input_dir / f"{audio_path.stem}.txt"
            transcript_file.write_text(transcript_text, encoding='utf-8')

            try:
                # Run MFA alignment
                logger.info(f"Running MFA alignment for {conversation_id or audio_path.stem}...")
                self._run_mfa_align(input_dir, output_dir)

                # Parse TextGrid output
                textgrid_path = output_dir / f"{audio_path.stem}.TextGrid"

                if not textgrid_path.exists():
                    raise MFAAlignmentError(f"MFA did not produce TextGrid: {textgrid_path}")

                word_timings = self._parse_textgrid(textgrid_path)

                logger.info(f"MFA alignment successful: {len(word_timings)} words aligned")
                return word_timings

            except subprocess.CalledProcessError as e:
                raise MFAAlignmentError(f"MFA alignment failed: {e.stderr}") from e
            except Exception as e:
                raise MFAAlignmentError(f"Unexpected error during MFA alignment: {e}") from e

    def _run_mfa_align(self, input_dir: Path, output_dir: Path) -> None:
        """
        Run MFA align command via subprocess.

        Args:
            input_dir: Directory containing audio + transcript
            output_dir: Directory for TextGrid output

        Raises:
            subprocess.CalledProcessError: If MFA command fails
        """
        cmd = [
            "mfa", "align",
            str(input_dir),          # Input directory
            str(self.dictionary),    # Dictionary
            str(self.acoustic_model), # Acoustic model
            str(output_dir),         # Output directory
            "--clean",               # Clean previous runs
            "--single_speaker"       # Assume single speaker per file
        ]

        logger.debug(f"Running MFA command: {' '.join(cmd)}")

        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            check=True
        )

        logger.debug(f"MFA stdout: {result.stdout}")
        if result.stderr:
            logger.debug(f"MFA stderr: {result.stderr}")

    def _parse_textgrid(self, textgrid_path: Path) -> List[WordTiming]:
        """
        Parse Praat TextGrid file to extract word timings.

        TextGrid format (simplified):
            intervals [1]:
                xmin = 0.0
                xmax = 0.5
                text = "hello"
            intervals [2]:
                xmin = 0.5
                xmax = 1.0
                text = "world"

        Args:
            textgrid_path: Path to TextGrid file

        Returns:
            List of WordTiming objects
        """
        word_timings = []

        content = textgrid_path.read_text(encoding='utf-8')

        # Find the words tier (usually the second tier after phones)
        # Look for tier with "words" in the name
        tiers = content.split('item [')

        words_tier = None
        for tier in tiers:
            if 'name = "words"' in tier.lower():
                words_tier = tier
                break

        if not words_tier:
            # Fallback: use last tier (often the word tier)
            words_tier = tiers[-1] if tiers else ""

        # Parse intervals in the words tier
        # Pattern: intervals [N]: xmin = X xmax = Y text = "word"
        interval_pattern = re.compile(
            r'intervals\s*\[\d+\]:\s*'
            r'xmin\s*=\s*([\d.]+)\s*'
            r'xmax\s*=\s*([\d.]+)\s*'
            r'text\s*=\s*"([^"]*)"',
            re.DOTALL
        )

        for match in interval_pattern.finditer(words_tier):
            xmin = float(match.group(1))
            xmax = float(match.group(2))
            text = match.group(3).strip()

            # Skip empty intervals and silence markers
            if text and text not in ['', 'sp', 'sil', '<s>', '</s>']:
                word_timings.append(WordTiming(
                    word=text,
                    start_time=xmin,
                    end_time=xmax
                ))

        return word_timings

    def _convert_to_wav(self, input_path: Path, output_path: Path) -> None:
        """
        Convert audio to WAV format using soundfile.

        Args:
            input_path: Input audio file (any format soundfile supports)
            output_path: Output WAV file path
        """
        try:
            import soundfile as sf

            audio_data, sample_rate = sf.read(str(input_path))
            sf.write(str(output_path), audio_data, sample_rate, format='WAV')

            logger.debug(f"Converted {input_path.suffix} to WAV: {output_path}")

        except Exception as e:
            raise MFAAlignmentError(f"Failed to convert audio to WAV: {e}") from e


class MFAAlignerFactory:
    """
    Factory for creating MFAAligner instances with configuration.

    Useful for dependency injection and testing.
    """

    @staticmethod
    def create_from_config(config: Dict) -> MFAAligner:
        """
        Create MFAAligner from configuration dictionary.

        Args:
            config: Dict with keys: acoustic_model, dictionary, temp_dir, cleanup

        Returns:
            Configured MFAAligner instance

        Raises:
            MFANotAvailableError: If MFA is not installed
        """
        return MFAAligner(
            acoustic_model=config.get('acoustic_model', 'english_us_arpa'),
            dictionary=config.get('dictionary', 'english_us_arpa'),
            temp_dir=config.get('temp_dir'),
            cleanup=config.get('cleanup', True)
        )

    @staticmethod
    def is_available() -> bool:
        """Check if MFA is available without creating an instance."""
        return MFAAligner.is_mfa_available()
