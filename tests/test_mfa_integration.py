"""
Integration tests for MFA alignment with automatic fallback.

Tests the ForcedAligner integration with MFA, including:
- Successful MFA alignment
- Automatic fallback to segment-level when MFA fails
- No regression in existing functionality
"""

import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock
from dataclasses import dataclass

from src.audio.forced_aligner import ForcedAligner, WordTiming
from src.audio.mfa_aligner import MFANotAvailableError, MFAAlignmentError


# Mock TranscriptSegment for testing
@dataclass
class MockTranscriptSegment:
    """Mock transcript segment for testing."""
    speaker: str
    text: str
    start_time: float
    end_time: float

    def to_dict(self):
        return {
            'speaker': self.speaker,
            'text': self.text,
            'start_time': self.start_time,
            'end_time': self.end_time
        }


class TestMFAIntegration:
    """Integration tests for MFA alignment with fallback."""

    def create_mock_segments(self):
        """Create mock transcript segments for testing."""
        return [
            MockTranscriptSegment(
                speaker="Speaker_1",
                text="Hello world",
                start_time=0.0,
                end_time=2.0
            ),
            MockTranscriptSegment(
                speaker="Speaker_2",
                text="How are you today",
                start_time=2.0,
                end_time=5.0
            ),
            MockTranscriptSegment(
                speaker="Speaker_1",
                text="I'm from Dallas Texas",
                start_time=5.0,
                end_time=8.0
            )
        ]

    @patch('shutil.which')
    @patch('src.audio.mfa_aligner.MFAAligner.align')
    def test_mfa_success(self, mock_mfa_align, mock_which):
        """Test successful MFA alignment."""
        # Setup: MFA is available
        mock_which.return_value = "/usr/bin/mfa"

        # Mock successful MFA alignment returning word timings
        from src.audio.mfa_aligner import WordTiming as MFAWordTiming
        mock_mfa_align.return_value = [
            MFAWordTiming(word="Hello", start_time=0.0, end_time=0.5),
            MFAWordTiming(word="world", start_time=0.5, end_time=1.2),
            MFAWordTiming(word="How", start_time=2.0, end_time=2.3),
            MFAWordTiming(word="are", start_time=2.3, end_time=2.6),
            MFAWordTiming(word="you", start_time=2.6, end_time=2.9),
            MFAWordTiming(word="today", start_time=2.9, end_time=3.5),
        ]

        # Create forced aligner with MFA
        aligner = ForcedAligner(use_mfa=True)

        # Verify MFA aligner was created
        assert aligner.mfa_aligner is not None

        # Create mock audio path and segments
        import tempfile
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
            audio_path = Path(f.name)

        segments = self.create_mock_segments()[:2]  # First two segments

        try:
            # Run alignment
            word_timings = aligner.align_audio_with_transcript(
                audio_path=audio_path,
                segments=segments,
                conversation_id="test_001"
            )

            # Verify MFA was used
            assert mock_mfa_align.called
            assert aligner.alignment_method == "mfa"

            # Verify word timings
            assert len(word_timings) > 0
            assert all(isinstance(wt, WordTiming) for wt in word_timings)

        finally:
            audio_path.unlink(missing_ok=True)

    @patch('shutil.which')
    def test_mfa_not_available_fallback(self, mock_which):
        """Test fallback to segment-level when MFA not available."""
        # Setup: MFA is NOT available
        mock_which.return_value = None

        # Create forced aligner (MFA will not initialize)
        aligner = ForcedAligner(use_mfa=True)

        # Verify MFA aligner was not created
        assert aligner.mfa_aligner is None

        # Create mock audio path and segments
        import tempfile
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
            audio_path = Path(f.name)

        segments = self.create_mock_segments()

        try:
            # Run alignment (should use fallback)
            word_timings = aligner.align_audio_with_transcript(
                audio_path=audio_path,
                segments=segments,
                conversation_id="test_002"
            )

            # Verify fallback was used
            assert aligner.alignment_method == "segment"

            # Verify word timings (one per segment)
            assert len(word_timings) == len(segments)

            # Verify each timing matches a segment
            for i, wt in enumerate(word_timings):
                assert wt.start_time == segments[i].start_time
                assert wt.end_time == segments[i].end_time
                assert wt.word == segments[i].text

        finally:
            audio_path.unlink(missing_ok=True)

    @patch('shutil.which')
    @patch('src.audio.mfa_aligner.MFAAligner.align')
    def test_mfa_failure_fallback(self, mock_mfa_align, mock_which):
        """Test automatic fallback when MFA alignment fails."""
        # Setup: MFA is available
        mock_which.return_value = "/usr/bin/mfa"

        # Mock MFA alignment failure
        mock_mfa_align.side_effect = MFAAlignmentError("MFA failed")

        # Create forced aligner with MFA
        aligner = ForcedAligner(use_mfa=True)

        # Verify MFA aligner was created
        assert aligner.mfa_aligner is not None

        # Create mock audio path and segments
        import tempfile
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
            audio_path = Path(f.name)

        segments = self.create_mock_segments()

        try:
            # Run alignment (should fallback after MFA fails)
            word_timings = aligner.align_audio_with_transcript(
                audio_path=audio_path,
                segments=segments,
                conversation_id="test_003"
            )

            # Verify MFA was attempted
            assert mock_mfa_align.called

            # Verify fallback was used
            assert aligner.alignment_method == "segment"

            # Verify word timings (fallback to segment-level)
            assert len(word_timings) == len(segments)

        finally:
            audio_path.unlink(missing_ok=True)

    @patch('shutil.which')
    def test_use_mfa_false_uses_fallback(self, mock_which):
        """Test that use_mfa=False always uses segment-level fallback."""
        mock_which.return_value = "/usr/bin/mfa"  # MFA is available

        # Create forced aligner with use_mfa=False
        aligner = ForcedAligner(use_mfa=False)

        # Verify MFA aligner was NOT created (even though MFA is available)
        assert aligner.mfa_aligner is None

        # Create mock audio path and segments
        import tempfile
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
            audio_path = Path(f.name)

        segments = self.create_mock_segments()

        try:
            # Run alignment
            word_timings = aligner.align_audio_with_transcript(
                audio_path=audio_path,
                segments=segments
            )

            # Verify fallback was used
            assert aligner.alignment_method == "segment"
            assert len(word_timings) == len(segments)

        finally:
            audio_path.unlink(missing_ok=True)

    @patch('shutil.which')
    @patch('src.audio.mfa_aligner.MFAAligner.align')
    def test_mfa_config_injection(self, mock_mfa_align, mock_which):
        """Test that MFA configuration is properly injected."""
        mock_which.return_value = "/usr/bin/mfa"

        # Custom MFA configuration
        mfa_config = {
            'acoustic_model': 'custom_model',
            'dictionary': 'custom_dict',
            'temp_dir': '/tmp/test',
            'cleanup': False
        }

        # Create aligner with custom config
        aligner = ForcedAligner(use_mfa=True, mfa_config=mfa_config)

        # Verify config was injected
        assert aligner.mfa_aligner is not None
        assert aligner.mfa_aligner.acoustic_model == 'custom_model'
        assert aligner.mfa_aligner.dictionary == 'custom_dict'
        assert aligner.mfa_aligner.temp_dir == Path('/tmp/test')
        assert aligner.mfa_aligner.cleanup is False

    def test_segment_fallback_handles_none_end_time(self):
        """Test that fallback handles segments with None end_time."""
        # Create aligner without MFA
        with patch('shutil.which', return_value=None):
            aligner = ForcedAligner(use_mfa=True)

        # Create segment with None end_time
        segments = [
            MockTranscriptSegment(
                speaker="Speaker_1",
                text="Test text",
                start_time=0.0,
                end_time=None  # None end_time
            )
        ]

        import tempfile
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
            audio_path = Path(f.name)

        try:
            # Run alignment
            word_timings = aligner.align_audio_with_transcript(
                audio_path=audio_path,
                segments=segments
            )

            # Verify fallback handles None end_time (defaults to start + 5.0)
            assert len(word_timings) == 1
            assert word_timings[0].start_time == 0.0
            assert word_timings[0].end_time == 5.0  # Default

        finally:
            audio_path.unlink(missing_ok=True)

    @patch('shutil.which')
    @patch('src.audio.mfa_aligner.MFAAligner.align')
    def test_pii_matching_with_punctuation_and_repeated_words(self, mock_mfa_align, mock_which):
        """Test that PII matching uses actual character spans from MFA, not synthetic offsets."""
        # Setup: MFA is available
        mock_which.return_value = "/usr/bin/mfa"

        # Transcript with punctuation and repeated words
        # "I like that it's mostly hot . so , therefore you can do things throughout the day , a lot ."
        # The word "throughout" should NOT be matched when looking for a city name at a different position

        from src.audio.mfa_aligner import WordTiming as MFAWordTiming
        from src.deid.pii_detector import PIIMatch

        # Mock MFA alignment for transcript with punctuation
        # Simulating: "and it just beams all the time . it rarely gets cold and I don't really like it . like about the weather in [CITY] ?"
        # Character positions for words in actual transcript (with punctuation)
        transcript_text = "and it just beams all the time . it rarely gets cold and I don't really like it . like about the weather in Houston ?"

        mock_mfa_align.return_value = [
            MFAWordTiming(word="and", start_time=0.0, end_time=0.2),
            MFAWordTiming(word="it", start_time=0.2, end_time=0.4),
            MFAWordTiming(word="just", start_time=0.4, end_time=0.7),
            MFAWordTiming(word="beams", start_time=0.7, end_time=1.1),
            MFAWordTiming(word="all", start_time=1.1, end_time=1.3),
            MFAWordTiming(word="the", start_time=1.3, end_time=1.5),
            MFAWordTiming(word="time", start_time=1.5, end_time=1.9),
            MFAWordTiming(word="it", start_time=2.0, end_time=2.2),
            MFAWordTiming(word="rarely", start_time=2.2, end_time=2.7),
            MFAWordTiming(word="gets", start_time=2.7, end_time=3.0),
            MFAWordTiming(word="cold", start_time=3.0, end_time=3.3),
            MFAWordTiming(word="and", start_time=3.3, end_time=3.5),
            MFAWordTiming(word="I", start_time=3.5, end_time=3.6),
            MFAWordTiming(word="don't", start_time=3.6, end_time=3.9),
            MFAWordTiming(word="really", start_time=3.9, end_time=4.3),
            MFAWordTiming(word="like", start_time=4.3, end_time=4.6),
            MFAWordTiming(word="it", start_time=4.6, end_time=4.8),
            MFAWordTiming(word="like", start_time=5.0, end_time=5.3),
            MFAWordTiming(word="about", start_time=5.3, end_time=5.7),
            MFAWordTiming(word="the", start_time=5.7, end_time=5.9),
            MFAWordTiming(word="weather", start_time=5.9, end_time=6.3),
            MFAWordTiming(word="in", start_time=6.3, end_time=6.5),
            MFAWordTiming(word="Houston", start_time=6.5, end_time=7.2),
        ]

        # Create forced aligner
        aligner = ForcedAligner(use_mfa=True)

        # Create mock segments
        segments = [
            MockTranscriptSegment(
                speaker="Speaker_1",
                text=transcript_text,
                start_time=0.0,
                end_time=8.0
            )
        ]

        # Create mock audio path
        import tempfile
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
            audio_path = Path(f.name)

        try:
            # Run alignment
            word_timings = aligner.align_audio_with_transcript(
                audio_path=audio_path,
                segments=segments,
                conversation_id="test_pii_match"
            )

            # Verify character spans are populated
            assert any(wt.char_start is not None for wt in word_timings), \
                "Character spans should be populated from MFA"

            # Create PII match for "Houston" (starts at position 118 in transcript)
            houston_start = transcript_text.index("Houston")
            pii_matches = [
                PIIMatch(
                    value="Houston",
                    category="cities",
                    tag="[CITY]",
                    start=houston_start,
                    end=houston_start + len("Houston")
                )
            ]

            # Match PII to words
            pii_timings = aligner.match_pii_to_words(pii_matches, word_timings)

            # Verify: Should match exactly "Houston", not any other word
            assert len(pii_timings) == 1, "Should match exactly one PII instance"

            matched_pii = pii_timings[0]
            assert matched_pii['value'] == "Houston"
            assert matched_pii['start_time'] == 6.5  # "Houston" start time
            assert matched_pii['end_time'] == 7.2    # "Houston" end time

            # Find the word timing for "Houston"
            houston_timing = next((wt for wt in word_timings if wt.word == "Houston"), None)
            assert houston_timing is not None
            assert houston_timing.char_start == houston_start
            assert houston_timing.char_end == houston_start + len("Houston")

        finally:
            audio_path.unlink(missing_ok=True)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
