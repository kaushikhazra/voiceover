"""Tests for engine.generate_audio — mocked TTS model, no GPU required."""

from unittest.mock import patch, MagicMock

import numpy as np
import pytest

from voiceover.engine import generate_audio, TTSModel


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

@pytest.fixture(autouse=True)
def _reset_tts_singleton():
    """Reset TTSModel singleton between tests to avoid cross-test leakage."""
    TTSModel._instance = None
    TTSModel._voice_prompts = {}
    yield
    TTSModel._instance = None
    TTSModel._voice_prompts = {}


def _make_mock_model(chunk_samples: int = 1000, sample_rate: int = 24000):
    """Return a MagicMock that behaves like a Qwen3TTSModel."""
    model = MagicMock()
    audio = np.ones(chunk_samples, dtype=np.float32) * 0.1
    model.generate_voice_clone.return_value = ([audio], sample_rate)
    model.create_voice_clone_prompt.return_value = "fake_prompt"
    return model


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

@patch.object(TTSModel, "get_voice_prompt", return_value="fake_prompt")
@patch.object(TTSModel, "get_instance")
def test_short_text_single_chunk(mock_get_instance, mock_get_prompt):
    """Short text stays in one chunk — model called exactly once."""
    mock_model = _make_mock_model()
    mock_get_instance.return_value = mock_model

    audio, sr = generate_audio("Hello world.", voice_path="fake.wav")

    assert isinstance(audio, np.ndarray)
    assert sr == 24000
    mock_model.generate_voice_clone.assert_called_once()


@patch.object(TTSModel, "get_voice_prompt", return_value="fake_prompt")
@patch.object(TTSModel, "get_instance")
def test_long_text_produces_multiple_chunks(mock_get_instance, mock_get_prompt):
    """Text exceeding the chunk word-limit triggers multiple model calls."""
    mock_model = _make_mock_model(chunk_samples=500)
    mock_get_instance.return_value = mock_model

    # 50 sentences × ~5 words each ≈ 250 words → multiple chunks at limit=120
    long_text = ". ".join(
        [f"This is sentence number {i}" for i in range(50)]
    ) + "."

    audio, sr = generate_audio(long_text, voice_path="fake.wav")

    assert isinstance(audio, np.ndarray)
    assert sr == 24000
    assert mock_model.generate_voice_clone.call_count > 1


@patch.object(TTSModel, "get_voice_prompt", return_value="fake_prompt")
@patch.object(TTSModel, "get_instance")
def test_chunks_concatenated_with_silence_gaps(mock_get_instance, mock_get_prompt):
    """Multi-chunk audio has 300 ms silence gaps between chunks."""
    chunk_samples = 500
    sample_rate = 24000
    mock_model = _make_mock_model(
        chunk_samples=chunk_samples, sample_rate=sample_rate,
    )
    mock_get_instance.return_value = mock_model

    long_text = ". ".join(
        [f"This is sentence {i}" for i in range(50)]
    ) + "."

    audio, sr = generate_audio(long_text, voice_path="fake.wav")

    n_chunks = mock_model.generate_voice_clone.call_count
    gap_samples = int(sample_rate * 300 / 1000)  # 300 ms
    expected_length = n_chunks * chunk_samples + (n_chunks - 1) * gap_samples
    assert len(audio) == expected_length


@patch.object(TTSModel, "get_voice_prompt", return_value="fake_prompt")
@patch.object(TTSModel, "get_instance")
def test_instruct_forwarded_to_model(mock_get_instance, mock_get_prompt):
    """Non-empty instruct text is passed through to generate_voice_clone."""
    mock_model = _make_mock_model()
    mock_get_instance.return_value = mock_model

    generate_audio("Hello.", voice_path="fake.wav", instruct="calm voice")

    kwargs = mock_model.generate_voice_clone.call_args.kwargs
    assert kwargs["instruct"] == "calm voice"


@patch.object(TTSModel, "get_voice_prompt", return_value="fake_prompt")
@patch.object(TTSModel, "get_instance")
def test_empty_instruct_becomes_none(mock_get_instance, mock_get_prompt):
    """Empty instruct string is translated to None for the model."""
    mock_model = _make_mock_model()
    mock_get_instance.return_value = mock_model

    generate_audio("Hello.", voice_path="fake.wav", instruct="")

    kwargs = mock_model.generate_voice_clone.call_args.kwargs
    assert kwargs["instruct"] is None


@patch.object(TTSModel, "get_voice_prompt", return_value="fake_prompt")
@patch.object(TTSModel, "get_instance")
def test_output_is_normalized(mock_get_instance, mock_get_prompt):
    """Output audio passes through normalize_audio (RMS near -18 dBFS)."""
    mock_model = _make_mock_model()
    mock_get_instance.return_value = mock_model

    audio, _ = generate_audio("Hello.", voice_path="fake.wav")

    rms = np.sqrt(np.mean(audio ** 2))
    target_linear = 10 ** (-18.0 / 20.0)  # default target
    assert abs(rms - target_linear) < 0.01
