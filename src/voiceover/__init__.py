"""Voiceover — text-to-speech with voice cloning using Qwen3-TTS."""

__version__ = "1.0.0"

from voiceover.engine import generate_audio, preprocess_text

__all__ = ["generate_audio", "preprocess_text", "__version__"]
