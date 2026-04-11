"""Tests for engine.silence — generate silent audio buffers."""

import numpy as np

from voiceover.engine import silence


def test_correct_length_at_24khz():
    """500 ms of silence at 24 kHz should be 12 000 samples."""
    result = silence(500, 24000)
    assert len(result) == 12000


def test_correct_length_at_44100():
    """1 000 ms of silence at 44 100 Hz should be 44 100 samples."""
    result = silence(1000, 44100)
    assert len(result) == 44100


def test_all_zeros():
    """Silence buffer must contain only zeros."""
    result = silence(100, 16000)
    np.testing.assert_array_equal(result, np.zeros(1600, dtype=np.float32))


def test_dtype_is_float32():
    """Silence should be float32 for audio processing compatibility."""
    result = silence(10, 24000)
    assert result.dtype == np.float32


def test_zero_duration():
    """Zero milliseconds should produce an empty array."""
    result = silence(0, 24000)
    assert len(result) == 0
