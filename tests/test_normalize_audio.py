"""Tests for engine.normalize_audio — dBFS normalization."""

import numpy as np

from voiceover.engine import normalize_audio


def test_normalizes_to_target_dbfs():
    """Audio is scaled so its RMS matches the target dBFS level."""
    sr = 24000
    t = np.linspace(0, 1, sr, dtype=np.float32)
    audio = 0.5 * np.sin(2 * np.pi * 440 * t)  # RMS ≈ 0.354

    target_dbfs = -20.0
    result = normalize_audio(audio, target_level=target_dbfs)

    rms_out = np.sqrt(np.mean(result ** 2))
    target_linear = 10 ** (target_dbfs / 20.0)
    assert abs(rms_out - target_linear) < 1e-3


def test_silence_input_returns_unchanged():
    """All-zero audio is returned as-is (no division by zero)."""
    audio = np.zeros(1000, dtype=np.float32)
    result = normalize_audio(audio)
    np.testing.assert_array_equal(result, audio)


def test_near_silence_returns_unchanged():
    """Audio with RMS below threshold (1e-6) is returned as-is."""
    audio = np.full(1000, 1e-8, dtype=np.float32)
    result = normalize_audio(audio)
    np.testing.assert_array_equal(result, audio)


def test_empty_array_returns_empty():
    """Empty input produces empty output without error."""
    audio = np.array([], dtype=np.float32)
    result = normalize_audio(audio)
    assert result.size == 0


def test_already_normalized_stays_close():
    """Audio already at target level is not significantly changed."""
    target_dbfs = -20.0
    target_linear = 10 ** (target_dbfs / 20.0)

    # Sine wave with RMS exactly at target: amplitude = target * sqrt(2)
    sr = 24000
    t = np.linspace(0, 1, sr, dtype=np.float32)
    audio = target_linear * np.sqrt(2) * np.sin(2 * np.pi * 440 * t)

    result = normalize_audio(audio, target_level=target_dbfs)
    rms_out = np.sqrt(np.mean(result ** 2))
    assert abs(rms_out - target_linear) < 1e-3


def test_output_clipped_to_valid_range():
    """Extreme amplification clips output to [-0.999, 0.999]."""
    # Very quiet audio + aggressive target → large scaling → clipping
    audio = np.array([0.0001, -0.0001, 0.0001], dtype=np.float32)
    result = normalize_audio(audio, target_level=0.0)
    assert np.all(result <= 0.999)
    assert np.all(result >= -0.999)
