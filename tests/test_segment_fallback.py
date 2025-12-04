"""Test segment-level muting fallback logic."""

import pytest
import numpy as np
from pathlib import Path
import sys

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.audio.audio_modifier import AudioModifier
from src.qa.statistics import StatisticsGenerator


def test_audio_modifier_segment_mute(tmp_path):
    """Verify AudioModifier.mute_segments zeroes the expected span."""
    sample_rate = 16000
    # 1-second mono sine wave
    t = np.linspace(0, 1, sample_rate, False)
    audio = np.sin(2 * np.pi * 440 * t).astype(np.float32)

    modifier = AudioModifier()
    muted = modifier.mute_segments(
        audio,
        sample_rate,
        [{'start_time': 0.25, 'end_time': 0.5}]
    )

    # Samples between 0.25s and 0.5s should become zero (accounting for fade)
    # The fade is 0.01s by default, so check the middle of the muted region
    start = int(0.25 * sample_rate)
    end = int(0.5 * sample_rate)
    fade_samples = int(0.01 * sample_rate)

    # Check the center of the muted region (avoiding fade zones)
    center_start = start + fade_samples
    center_end = end - fade_samples
    assert np.allclose(muted[center_start:center_end], 0.0, atol=1e-5)

    # Samples outside the range remain unchanged
    assert np.isclose(muted[0], audio[0])
    assert np.isclose(muted[-1], audio[-1])


def test_audio_modifier_multiple_segments(tmp_path):
    """Test muting multiple non-overlapping segments."""
    sample_rate = 16000
    # 2-second audio
    t = np.linspace(0, 2, 2 * sample_rate, False)
    audio = np.sin(2 * np.pi * 440 * t).astype(np.float32)

    modifier = AudioModifier()
    muted = modifier.mute_segments(
        audio,
        sample_rate,
        [
            {'start_time': 0.25, 'end_time': 0.5},
            {'start_time': 1.0, 'end_time': 1.25}
        ]
    )

    fade_samples = int(0.01 * sample_rate)

    # Check first muted region
    start1 = int(0.25 * sample_rate) + fade_samples
    end1 = int(0.5 * sample_rate) - fade_samples
    assert np.allclose(muted[start1:end1], 0.0, atol=1e-5)

    # Check second muted region
    start2 = int(1.0 * sample_rate) + fade_samples
    end2 = int(1.25 * sample_rate) - fade_samples
    assert np.allclose(muted[start2:end2], 0.0, atol=1e-5)

    # Check unmuted region between
    between_start = int(0.6 * sample_rate)
    between_end = int(0.9 * sample_rate)
    assert not np.allclose(muted[between_start:between_end], 0.0, atol=1e-5)


def test_statistics_generator_handles_missing_end_time():
    """Use a tiny conversation fixture and ensure StatisticsGenerator handles missing end_time."""
    conversations = [{
        'conversation_id': 'foo',
        'segments': [
            {'speaker': 'S1', 'text': 'Hi', 'start_time': 0.0, 'end_time': None},
            {'speaker': 'S2', 'text': 'Bye', 'start_time': 2.0, 'end_time': 3.0}
        ],
        'pii_summary': {
            'total_pii_found': 2,
            'categories': {'cities': 1, 'states': 1}
        },
        'redaction_log': {'total_replacements': 2}
    }]

    stats_gen = StatisticsGenerator()
    stats = stats_gen.generate_dataset_stats(conversations)

    assert stats['total_conversations'] == 1
    assert stats['total_pii_instances'] == 2
    assert stats['pii_by_category']['cities'] == 1
    assert stats['pii_by_category']['states'] == 1
    # Should use start_time when end_time is None (falls back to last segment's start_time)
    assert stats['total_duration'] >= 0  # Should not crash


def test_statistics_generator_all_missing_end_times():
    """Test when all segments have missing end_time."""
    conversations = [{
        'conversation_id': 'bar',
        'segments': [
            {'speaker': 'S1', 'text': 'Hello', 'start_time': 0.0, 'end_time': None},
            {'speaker': 'S2', 'text': 'World', 'start_time': 5.0, 'end_time': None}
        ],
        'pii_summary': {
            'total_pii_found': 0,
            'categories': {}
        },
        'redaction_log': {'total_replacements': 0}
    }]

    stats_gen = StatisticsGenerator()
    stats = stats_gen.generate_dataset_stats(conversations)

    assert stats['total_conversations'] == 1
    assert stats['total_pii_instances'] == 0
    # Should use the last segment's start_time as duration
    assert stats['total_duration'] == 5.0


def test_audio_modifier_empty_segments():
    """Test AudioModifier with no segments to mute."""
    sample_rate = 16000
    t = np.linspace(0, 1, sample_rate, False)
    audio = np.sin(2 * np.pi * 440 * t).astype(np.float32)

    modifier = AudioModifier()
    muted = modifier.mute_segments(audio, sample_rate, [])

    # Audio should be unchanged
    assert np.allclose(muted, audio)


def test_audio_modifier_stereo_audio():
    """Test muting on stereo audio."""
    sample_rate = 16000
    # 1-second stereo sine wave
    t = np.linspace(0, 1, sample_rate, False)
    left = np.sin(2 * np.pi * 440 * t).astype(np.float32)
    right = np.sin(2 * np.pi * 880 * t).astype(np.float32)
    audio = np.column_stack([left, right])

    modifier = AudioModifier()
    muted = modifier.mute_segments(
        audio,
        sample_rate,
        [{'start_time': 0.25, 'end_time': 0.5}]
    )

    fade_samples = int(0.01 * sample_rate)
    start = int(0.25 * sample_rate) + fade_samples
    end = int(0.5 * sample_rate) - fade_samples

    # Both channels should be muted
    assert np.allclose(muted[start:end, 0], 0.0, atol=1e-5)
    assert np.allclose(muted[start:end, 1], 0.0, atol=1e-5)

    # Samples outside remain unchanged
    assert np.isclose(muted[0, 0], audio[0, 0])
    assert np.isclose(muted[-1, 1], audio[-1, 1])


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
