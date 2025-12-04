"""
Unit tests for MFA (Montreal Forced Aligner) integration.

Tests MFAAligner class with mocked MFA CLI calls and fake TextGrid files.
"""

import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock, mock_open
import tempfile
import subprocess

from src.audio.mfa_aligner import (
    MFAAligner,
    MFANotAvailableError,
    MFAAlignmentError,
    WordTiming,
    MFAAlignerFactory
)


# Sample TextGrid content for testing
SAMPLE_TEXTGRID = """File type = "ooTextFile"
Object class = "TextGrid"

xmin = 0
xmax = 2.5
tiers? <exists>
size = 2
item []:
    item [1]:
        class = "IntervalTier"
        name = "phones"
        xmin = 0
        xmax = 2.5
        intervals: size = 5
    item [2]:
        class = "IntervalTier"
        name = "words"
        xmin = 0
        xmax = 2.5
        intervals: size = 3
        intervals [1]:
            xmin = 0.0
            xmax = 0.5
            text = "hello"
        intervals [2]:
            xmin = 0.5
            xmax = 1.2
            text = "world"
        intervals [3]:
            xmin = 1.2
            xmax = 2.5
            text = "test"
"""


class TestMFAAligner:
    """Test suite for MFAAligner."""

    @patch('shutil.which')
    def test_mfa_not_available_raises_error(self, mock_which):
        """Test that MFANotAvailableError is raised when MFA is not installed."""
        mock_which.return_value = None  # MFA not found

        with pytest.raises(MFANotAvailableError, match="MFA.*not found"):
            MFAAligner()

    @patch('shutil.which')
    def test_mfa_available_initializes(self, mock_which):
        """Test that MFAAligner initializes successfully when MFA is available."""
        mock_which.return_value = "/usr/bin/mfa"  # MFA found

        aligner = MFAAligner(
            acoustic_model="test_model",
            dictionary="test_dict"
        )

        assert aligner.acoustic_model == "test_model"
        assert aligner.dictionary == "test_dict"
        assert aligner.cleanup is True

    @patch('shutil.which')
    def test_is_mfa_available(self, mock_which):
        """Test is_mfa_available static method."""
        # MFA available
        mock_which.return_value = "/usr/bin/mfa"
        assert MFAAligner.is_mfa_available() is True

        # MFA not available
        mock_which.return_value = None
        assert MFAAligner.is_mfa_available() is False

    @patch('shutil.which')
    @patch('subprocess.run')
    @patch('pathlib.Path.exists')
    @patch('pathlib.Path.read_text')
    @patch('shutil.copy')
    def test_align_success(self, mock_copy, mock_read_text, mock_exists,
                          mock_subprocess, mock_which):
        """Test successful MFA alignment."""
        # Setup mocks
        mock_which.return_value = "/usr/bin/mfa"
        mock_exists.return_value = True
        mock_read_text.return_value = SAMPLE_TEXTGRID
        mock_subprocess.return_value = MagicMock(
            stdout="MFA alignment complete",
            stderr="",
            returncode=0
        )

        # Create aligner
        aligner = MFAAligner()

        # Create temp audio file
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
            audio_path = f.name

        try:
            # Run alignment
            word_timings = aligner.align(
                audio_path=audio_path,
                transcript_text="hello world test",
                conversation_id="test_001"
            )

            # Verify results
            assert len(word_timings) == 3
            assert word_timings[0].word == "hello"
            assert word_timings[0].start_time == 0.0
            assert word_timings[0].end_time == 0.5
            assert word_timings[1].word == "world"
            assert word_timings[2].word == "test"

            # Verify subprocess was called
            assert mock_subprocess.called
            call_args = mock_subprocess.call_args[0][0]
            assert "mfa" in call_args
            assert "align" in call_args

        finally:
            Path(audio_path).unlink(missing_ok=True)

    @patch('shutil.which')
    def test_align_audio_not_found(self, mock_which):
        """Test that MFAAlignmentError is raised when audio file doesn't exist."""
        mock_which.return_value = "/usr/bin/mfa"

        aligner = MFAAligner()

        with pytest.raises(MFAAlignmentError, match="Audio file not found"):
            aligner.align(
                audio_path="/nonexistent/audio.wav",
                transcript_text="test"
            )

    @patch('shutil.which')
    @patch('subprocess.run')
    @patch('pathlib.Path.exists')
    def test_align_mfa_cli_failure(self, mock_exists, mock_subprocess, mock_which):
        """Test that MFAAlignmentError is raised when MFA CLI fails."""
        mock_which.return_value = "/usr/bin/mfa"
        mock_exists.return_value = True

        # Mock MFA CLI failure
        mock_subprocess.side_effect = subprocess.CalledProcessError(
            returncode=1,
            cmd="mfa align",
            stderr="MFA error: alignment failed"
        )

        aligner = MFAAligner()

        # Create temp audio file
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
            audio_path = f.name

        try:
            with pytest.raises(MFAAlignmentError, match="MFA alignment failed"):
                aligner.align(
                    audio_path=audio_path,
                    transcript_text="test"
                )
        finally:
            Path(audio_path).unlink(missing_ok=True)

    def test_parse_textgrid(self):
        """Test TextGrid parsing."""
        with tempfile.NamedTemporaryFile(mode='w', suffix=".TextGrid", delete=False) as f:
            f.write(SAMPLE_TEXTGRID)
            textgrid_path = Path(f.name)

        try:
            with patch('shutil.which', return_value="/usr/bin/mfa"):
                aligner = MFAAligner()
                word_timings = aligner._parse_textgrid(textgrid_path)

            assert len(word_timings) == 3
            assert word_timings[0].word == "hello"
            assert word_timings[1].word == "world"
            assert word_timings[2].word == "test"

        finally:
            textgrid_path.unlink(missing_ok=True)

    def test_parse_textgrid_with_silence(self):
        """Test TextGrid parsing filters out silence markers."""
        textgrid_with_silence = """File type = "ooTextFile"
Object class = "TextGrid"

xmin = 0
xmax = 2.5
tiers? <exists>
size = 1
item []:
    item [1]:
        class = "IntervalTier"
        name = "words"
        xmin = 0
        xmax = 2.5
        intervals: size = 5
        intervals [1]:
            xmin = 0.0
            xmax = 0.2
            text = "sp"
        intervals [2]:
            xmin = 0.2
            xmax = 0.7
            text = "hello"
        intervals [3]:
            xmin = 0.7
            xmax = 0.9
            text = ""
        intervals [4]:
            xmin = 0.9
            xmax = 1.4
            text = "world"
        intervals [5]:
            xmin = 1.4
            xmax = 2.5
            text = "sil"
"""

        with tempfile.NamedTemporaryFile(mode='w', suffix=".TextGrid", delete=False) as f:
            f.write(textgrid_with_silence)
            textgrid_path = Path(f.name)

        try:
            with patch('shutil.which', return_value="/usr/bin/mfa"):
                aligner = MFAAligner()
                word_timings = aligner._parse_textgrid(textgrid_path)

            # Should only have "hello" and "world", not sp, sil, or empty
            assert len(word_timings) == 2
            assert word_timings[0].word == "hello"
            assert word_timings[1].word == "world"

        finally:
            textgrid_path.unlink(missing_ok=True)

    def test_word_timing_duration(self):
        """Test WordTiming duration property."""
        wt = WordTiming(word="test", start_time=1.0, end_time=1.5)
        assert wt.duration == 0.5


class TestMFAAlignerFactory:
    """Test suite for MFAAlignerFactory."""

    @patch('shutil.which')
    def test_create_from_config(self, mock_which):
        """Test factory creates aligner from config dict."""
        mock_which.return_value = "/usr/bin/mfa"

        config = {
            'acoustic_model': 'custom_model',
            'dictionary': 'custom_dict',
            'temp_dir': '/tmp/mfa',
            'cleanup': False
        }

        aligner = MFAAlignerFactory.create_from_config(config)

        assert aligner.acoustic_model == 'custom_model'
        assert aligner.dictionary == 'custom_dict'
        assert aligner.temp_dir == Path('/tmp/mfa')
        assert aligner.cleanup is False

    @patch('shutil.which')
    def test_create_from_config_with_defaults(self, mock_which):
        """Test factory uses defaults for missing config values."""
        mock_which.return_value = "/usr/bin/mfa"

        config = {}  # Empty config

        aligner = MFAAlignerFactory.create_from_config(config)

        assert aligner.acoustic_model == 'english_us_arpa'
        assert aligner.dictionary == 'english_us_arpa'
        assert aligner.cleanup is True

    @patch('shutil.which')
    def test_factory_is_available(self, mock_which):
        """Test factory is_available method."""
        # MFA available
        mock_which.return_value = "/usr/bin/mfa"
        assert MFAAlignerFactory.is_available() is True

        # MFA not available
        mock_which.return_value = None
        assert MFAAlignerFactory.is_available() is False


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
