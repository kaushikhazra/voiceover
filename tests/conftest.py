"""Shared test configuration.

Stubs heavy GPU dependencies (qwen_tts, torch, soundfile) at module level
so that voiceover.engine can be imported in any test without the actual
packages installed.  pytest loads conftest.py before test modules in the
same directory, so the stubs are guaranteed to be in place.
"""

import sys
import unittest.mock as mock

import pytest

# ---------------------------------------------------------------------------
# Module-level stubs — must run before any test imports voiceover.engine.
# setdefault preserves the real module if it happens to be installed already.
# ---------------------------------------------------------------------------
for _mod_name in ("qwen_tts", "torch", "soundfile"):
    sys.modules.setdefault(_mod_name, mock.MagicMock())


# ---------------------------------------------------------------------------
# Shared fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def voices_dir(tmp_path):
    """Temporary voices directory containing a single test WAV file."""
    d = tmp_path / "voices"
    d.mkdir()
    (d / "testvoice.wav").write_bytes(b"RIFF\x00\x00\x00\x00WAVEfmt ")
    return d
