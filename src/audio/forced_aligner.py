"""
Forced alignment with word-level timestamps.

Supports multiple alignment backends with automatic fallback:
1. MFA (Montreal Forced Aligner) - Preferred, most accurate
2. Segment-level fallback - Uses existing segment timestamps

The aligner automatically tries MFA first, and falls back to segment-level
if MFA is not available or fails.
"""

import json
import tempfile
from pathlib import Path
from typing import List, Dict, Optional
from dataclasses import dataclass

try:
    from aeneas.executetask import ExecuteTask
    from aeneas.task import Task
    AENEAS_AVAILABLE = True
except ImportError:
    AENEAS_AVAILABLE = False

from ..utils.logger import get_logger

logger = get_logger(__name__)


@dataclass
class WordTiming:
    """Represents timing information for a word."""
    word: str
    start_time: float
    end_time: float
    char_start: Optional[int] = None  # Character position in transcript text
    char_end: Optional[int] = None    # Character position in transcript text

    def to_dict(self) -> dict:
        """Convert to dictionary format."""
        return {
            'word': self.word,
            'start_time': self.start_time,
            'end_time': self.end_time,
            'char_start': self.char_start,
            'char_end': self.char_end
        }


class ForcedAligner:
    """
    Performs forced alignment with word-level timestamps.

    Tries MFA (Montreal Forced Aligner) first, falls back to segment-level
    timing if MFA is unavailable or fails.

    Attributes:
        use_mfa: Whether to attempt MFA alignment
        mfa_config: Configuration dict for MFA (model, dictionary, etc.)
        mfa_aligner: MFAAligner instance (if MFA available)
        alignment_method: Tracks which method was used ("mfa" or "segment")
    """

    def __init__(self, use_mfa: bool = True, mfa_config: Optional[Dict] = None):
        """
        Initialize forced aligner.

        Args:
            use_mfa: Whether to attempt MFA alignment (default: True)
            mfa_config: MFA configuration dict (acoustic_model, dictionary, etc.)
        """
        self.use_mfa = use_mfa
        self.mfa_config = mfa_config or {}
        self.mfa_aligner = None
        self.alignment_method = None

        # Try to initialize MFA if requested
        if self.use_mfa:
            try:
                from .mfa_aligner import MFAAligner, MFANotAvailableError

                self.mfa_aligner = MFAAligner(
                    acoustic_model=self.mfa_config.get('acoustic_model', 'english_us_arpa'),
                    dictionary=self.mfa_config.get('dictionary', 'english_us_arpa'),
                    temp_dir=self.mfa_config.get('temp_dir'),
                    cleanup=self.mfa_config.get('cleanup', True)
                )
                logger.info("✓ MFA aligner initialized (word-level precision)")

            except MFANotAvailableError as e:
                logger.warning(f"MFA not available: {e}")
                logger.warning("→ Will use segment-level fallback")
                self.mfa_aligner = None

            except Exception as e:
                logger.warning(f"Failed to initialize MFA: {e}")
                logger.warning("→ Will use segment-level fallback")
                self.mfa_aligner = None

        # Check aeneas (legacy support, not used in current implementation)
        if not AENEAS_AVAILABLE:
            logger.debug("aeneas not installed (not required with MFA)")

        if not self.mfa_aligner:
            logger.info("Using segment-level audio muting (fallback mode)")

    def align_audio_with_transcript(
        self,
        audio_path: Path,
        segments: List,
        language: str = "eng",
        conversation_id: Optional[str] = None
    ) -> List[WordTiming]:
        """
        Align audio with transcript to get word-level timestamps.

        Tries MFA first, falls back to segment-level timing if MFA fails.

        Args:
            audio_path: Path to audio file
            segments: List of TranscriptSegment objects
            language: Language code (default: "eng")
            conversation_id: Optional conversation ID for logging

        Returns:
            List of WordTiming objects
        """
        logger.info(f"Aligning {audio_path.name}")

        # Prepare transcript text
        transcript_text = self._prepare_transcript(segments)

        # Try MFA first if available
        if self.mfa_aligner:
            try:
                logger.info("→ Attempting MFA word-level alignment...")
                word_timings = self._run_mfa(audio_path, transcript_text, conversation_id)
                self.alignment_method = "mfa"
                logger.info(f"✓ MFA alignment successful: {len(word_timings)} words aligned")
                return word_timings

            except Exception as e:
                logger.warning(f"MFA alignment failed: {e}")
                logger.warning("→ Falling back to segment-level muting")

        # Fallback: Use segment-level timing
        logger.info("→ Using segment-level timing (fallback)")
        word_timings = self._fallback_segment_timing(segments)
        self.alignment_method = "segment"
        logger.info(f"✓ Segment-level timing: {len(word_timings)} segments")

        return word_timings

    def _prepare_transcript(self, segments: List) -> str:
        """
        Prepare transcript text for aeneas input.

        Uses the shared transcript utility to ensure consistent spacing
        with PII detection and text redaction.

        Args:
            segments: List of TranscriptSegment objects

        Returns:
            Combined transcript text
        """
        from ..utils.transcript_utils import prepare_full_transcript

        # Use shared utility for consistent spacing
        full_text, _ = prepare_full_transcript(segments)
        return full_text

    def _run_mfa(
        self,
        audio_path: Path,
        transcript_text: str,
        conversation_id: Optional[str] = None
    ) -> List[WordTiming]:
        """
        Run MFA forced alignment.

        Args:
            audio_path: Path to audio file
            transcript_text: Full transcript text
            conversation_id: Optional conversation ID for logging

        Returns:
            List of WordTiming objects (from MFA) with character spans

        Raises:
            Exception: If MFA alignment fails
        """
        from .mfa_aligner import MFAAlignmentError

        try:
            # Use MFA aligner
            mfa_word_timings = self.mfa_aligner.align(
                audio_path=str(audio_path),
                transcript_text=transcript_text,
                conversation_id=conversation_id
            )

            # Find actual character positions in the transcript for each word
            word_timings = []
            search_start = 0  # Start searching from here to handle repeated words

            for wt in mfa_word_timings:
                # Find this word in the transcript starting from search_start
                # Use case-insensitive search to handle capitalization differences
                word_lower = wt.word.lower()
                transcript_lower = transcript_text.lower()

                # Search for the word from search_start position
                char_start = transcript_lower.find(word_lower, search_start)

                if char_start == -1:
                    # Word not found, skip character positions for this word
                    word_timings.append(WordTiming(
                        word=wt.word,
                        start_time=wt.start_time,
                        end_time=wt.end_time,
                        char_start=None,
                        char_end=None
                    ))
                else:
                    char_end = char_start + len(wt.word)
                    word_timings.append(WordTiming(
                        word=wt.word,
                        start_time=wt.start_time,
                        end_time=wt.end_time,
                        char_start=char_start,
                        char_end=char_end
                    ))
                    # Update search_start to just after this word
                    search_start = char_end

            return word_timings

        except MFAAlignmentError as e:
            logger.error(f"MFA alignment error: {e}")
            raise

    def _fallback_segment_timing(self, segments: List) -> List[WordTiming]:
        """
        Fallback: Create word timings from segment timestamps.

        When word-level alignment is unavailable, treat each segment as a single "word"
        for timing purposes. This results in muting entire segments containing PII.

        Args:
            segments: List of TranscriptSegment objects

        Returns:
            List of WordTiming objects (one per segment)
        """
        word_timings = []

        for segment in segments:
            # Treat entire segment as a single timing unit
            word_timings.append(WordTiming(
                word=segment.text,  # Full segment text
                start_time=segment.start_time,
                end_time=segment.end_time if segment.end_time is not None else segment.start_time + 5.0
            ))

        return word_timings

    def _run_aeneas(
        self,
        audio_path: Path,
        transcript_text: str,
        language: str
    ) -> List[WordTiming]:
        """
        Run aeneas forced alignment (DEPRECATED - kept for legacy support).

        Args:
            audio_path: Path to audio file
            transcript_text: Full transcript text
            language: Language code

        Returns:
            List of WordTiming objects
        """
        # Create temporary text file for transcript
        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
            f.write(transcript_text)
            text_path = Path(f.name)

        # Create temporary output file for alignments
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            output_path = Path(f.name)

        try:
            # Configure aeneas task
            config_string = f"task_language={language}|is_text_type=plain|os_task_file_format=json"

            # Create and execute task
            task = Task(config_string=config_string)
            task.audio_file_path_absolute = str(audio_path)
            task.text_file_path_absolute = str(text_path)
            task.sync_map_file_path_absolute = str(output_path)

            ExecuteTask(task).execute()
            task.output_sync_map_file()

            # Parse results
            with open(output_path, 'r') as f:
                alignments = json.load(f)

            # Convert to WordTiming objects
            word_timings = []
            for fragment in alignments.get('fragments', []):
                word_timings.append(WordTiming(
                    word=fragment['lines'][0] if fragment.get('lines') else fragment.get('id', ''),
                    start_time=float(fragment['begin']),
                    end_time=float(fragment['end'])
                ))

            return word_timings

        finally:
            # Clean up temporary files
            text_path.unlink(missing_ok=True)
            output_path.unlink(missing_ok=True)

    def match_pii_to_words(
        self,
        pii_matches: List,
        word_timings: List[WordTiming]
    ) -> List[Dict]:
        """
        Match detected PII to word timings using actual character spans.

        Args:
            pii_matches: List of PIIMatch objects
            word_timings: List of WordTiming objects

        Returns:
            List of dictionaries with PII value, timing, and tag
        """
        pii_timings = []

        # Check if word timings have character positions
        has_char_positions = any(wt.char_start is not None for wt in word_timings)

        if has_char_positions:
            # Use actual character positions from MFA alignment
            word_map = []  # List of (word, timing, char_start, char_end)

            for word_timing in word_timings:
                if word_timing.char_start is not None and word_timing.char_end is not None:
                    word_map.append((
                        word_timing.word,
                        word_timing,
                        word_timing.char_start,
                        word_timing.char_end
                    ))

        else:
            # Fallback: Build synthetic word position map (legacy behavior)
            word_position = 0
            word_map = []  # List of (word, timing, char_start, char_end)

            for word_timing in word_timings:
                word = word_timing.word
                char_start = word_position
                char_end = word_position + len(word)
                word_map.append((word, word_timing, char_start, char_end))
                word_position = char_end + 1  # +1 for space

        # Match each PII to words
        for pii_match in pii_matches:
            # Find overlapping words
            matching_timings = []

            for word, word_timing, char_start, char_end in word_map:
                # Check if this word overlaps with PII position
                # Overlap occurs if: NOT (word ends before PII starts OR word starts after PII ends)
                if not (char_end <= pii_match.start or char_start >= pii_match.end):
                    matching_timings.append(word_timing)

            if matching_timings:
                pii_timings.append({
                    'value': pii_match.value,
                    'category': pii_match.category,
                    'tag': pii_match.tag,
                    'start_time': matching_timings[0].start_time,
                    'end_time': matching_timings[-1].end_time
                })

        logger.info(f"Matched {len(pii_timings)} PII instances to word timings")

        return pii_timings


def main():
    """Test the forced aligner."""
    from ..utils.logger import setup_logger

    # Setup logging
    setup_logger(__name__, level=20)  # INFO level

    if not AENEAS_AVAILABLE:
        print("\n⚠️  aeneas not installed")
        print("Install with: pip install aeneas")
        print("\nNote: On macOS, you may need:")
        print("  brew install espeak")
        print("  pip install aeneas")
        return

    print("\n✓ aeneas is installed and ready")
    print("\nForcedAligner can be used for word-level alignment")


if __name__ == "__main__":
    main()
