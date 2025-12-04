"""Modify audio files to mute PII segments."""

import numpy as np
from pathlib import Path
from typing import List, Dict
import soundfile as sf

from ..utils.logger import get_logger

logger = get_logger(__name__)


class AudioModifier:
    """Modifies audio files by muting specified segments."""

    def __init__(self, fade_duration: float = 0.01):
        """
        Initialize audio modifier.

        Args:
            fade_duration: Duration of fade in/out in seconds (to avoid clicks)
        """
        self.fade_duration = fade_duration
        logger.info(f"Initialized AudioModifier with {fade_duration}s fade")

    def load_audio(self, audio_path: Path) -> tuple[np.ndarray, int]:
        """
        Load audio file.

        Args:
            audio_path: Path to audio file

        Returns:
            Tuple of (audio_data, sample_rate)
        """
        logger.debug(f"Loading audio: {audio_path.name}")
        audio_data, sample_rate = sf.read(str(audio_path))
        logger.debug(f"Loaded audio: {len(audio_data)} samples at {sample_rate}Hz")
        return audio_data, sample_rate

    def mute_segments(
        self,
        audio_data: np.ndarray,
        sample_rate: int,
        segments_to_mute: List[Dict]
    ) -> np.ndarray:
        """
        Mute specified segments in audio.

        Args:
            audio_data: Audio data array
            sample_rate: Sample rate in Hz
            segments_to_mute: List of dicts with 'start_time' and 'end_time' in seconds

        Returns:
            Modified audio data
        """
        if not segments_to_mute:
            logger.warning("No segments to mute")
            return audio_data

        # Make a copy to avoid modifying original
        modified_audio = audio_data.copy()

        logger.info(f"Muting {len(segments_to_mute)} segments")

        for segment in segments_to_mute:
            start_time = segment['start_time']
            end_time = segment['end_time']

            # Convert time to sample indices
            start_sample = int(start_time * sample_rate)
            end_sample = int(end_time * sample_rate)

            # Ensure indices are within bounds
            start_sample = max(0, start_sample)
            end_sample = min(len(modified_audio), end_sample)

            # Calculate fade samples
            fade_samples = int(self.fade_duration * sample_rate)

            # Apply muting with fade in/out to avoid clicks
            segment_length = end_sample - start_sample

            if segment_length > 2 * fade_samples:
                # Long enough for fade in and out
                fade_in = np.linspace(1, 0, fade_samples)
                fade_out = np.linspace(0, 1, fade_samples)

                # Apply fade in
                if audio_data.ndim == 1:  # Mono
                    modified_audio[start_sample:start_sample + fade_samples] *= fade_in
                    modified_audio[start_sample + fade_samples:end_sample - fade_samples] = 0
                    modified_audio[end_sample - fade_samples:end_sample] *= fade_out
                else:  # Stereo
                    modified_audio[start_sample:start_sample + fade_samples, :] *= fade_in[:, np.newaxis]
                    modified_audio[start_sample + fade_samples:end_sample - fade_samples, :] = 0
                    modified_audio[end_sample - fade_samples:end_sample, :] *= fade_out[:, np.newaxis]
            else:
                # Short segment, just mute completely
                modified_audio[start_sample:end_sample] = 0

            logger.debug(f"Muted {start_time:.3f}s to {end_time:.3f}s "
                        f"({segment.get('value', 'PII')})")

        return modified_audio

    def save_audio(
        self,
        audio_data: np.ndarray,
        sample_rate: int,
        output_path: Path,
        format: str = 'FLAC'
    ):
        """
        Save audio to file.

        Args:
            audio_data: Audio data array
            sample_rate: Sample rate in Hz
            output_path: Path for output file
            format: Audio format (default: FLAC)
        """
        output_path.parent.mkdir(parents=True, exist_ok=True)

        logger.debug(f"Saving audio: {output_path.name}")
        sf.write(str(output_path), audio_data, sample_rate, format=format)
        logger.info(f"Saved audio: {output_path}")

    def process_audio_file(
        self,
        input_path: Path,
        output_path: Path,
        segments_to_mute: List[Dict]
    ):
        """
        Complete workflow to process an audio file.

        Args:
            input_path: Input audio file path
            output_path: Output audio file path
            segments_to_mute: List of segments to mute
        """
        logger.info(f"Processing audio: {input_path.name}")

        # Load audio
        audio_data, sample_rate = self.load_audio(input_path)

        # Mute segments
        modified_audio = self.mute_segments(audio_data, sample_rate, segments_to_mute)

        # Save result
        self.save_audio(modified_audio, sample_rate, output_path)

        logger.info(f"Audio processing complete: {output_path.name}")


def main():
    """Test the audio modifier."""
    from ..utils.logger import setup_logger

    # Setup logging
    setup_logger(__name__, level=20)  # INFO level

    print("\n=== Audio Modifier Ready ===")
    print("AudioModifier can:")
    print("  - Load WAV files")
    print("  - Mute specific time segments")
    print("  - Save as FLAC format")
    print("  - Apply fade in/out to avoid clicks")


if __name__ == "__main__":
    main()
