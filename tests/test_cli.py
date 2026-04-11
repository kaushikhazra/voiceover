"""Tests for cli.main — end-to-end CLI behaviour with mocked engine."""

import sys
import textwrap
from pathlib import Path
from unittest.mock import patch

import numpy as np
import pytest

from voiceover.cli import main


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def cli_env(tmp_path, monkeypatch, voices_dir):
    """Set up a clean CLI environment: tmp voices dir + mocked config."""
    monkeypatch.setattr(
        "voiceover.cli.cfg.load_config",
        lambda: {"voices_dir": voices_dir, "device": "cpu"},
    )
    return {"tmp_path": tmp_path, "voices_dir": voices_dir}


# ---------------------------------------------------------------------------
# Single-voice mode
# ---------------------------------------------------------------------------

@patch("voiceover.cli.sf")
@patch("voiceover.cli.generate_audio")
def test_single_voice_produces_output(mock_gen, mock_sf, cli_env, monkeypatch):
    """Basic single-voice invocation calls generate_audio and writes output."""
    mock_gen.return_value = (np.zeros(24000, dtype=np.float32), 24000)

    output = cli_env["tmp_path"] / "out.wav"
    monkeypatch.setattr(
        sys, "argv",
        ["voiceover", "Hello world", "--voice", "testvoice", "-o", str(output)],
    )

    main()

    mock_gen.assert_called_once()
    # Verify the text was forwarded correctly
    assert mock_gen.call_args.kwargs["text"] == "Hello world"
    assert mock_gen.call_args.kwargs["voice_path"].endswith("testvoice.wav")
    mock_sf.write.assert_called_once()


@patch("voiceover.cli.sf")
@patch("voiceover.cli.generate_audio")
def test_instruct_forwarded(mock_gen, mock_sf, cli_env, monkeypatch):
    """--instruct text is passed through to generate_audio."""
    mock_gen.return_value = (np.zeros(1000, dtype=np.float32), 24000)

    output = cli_env["tmp_path"] / "out.wav"
    monkeypatch.setattr(
        sys, "argv",
        [
            "voiceover", "Hi", "--voice", "testvoice",
            "--instruct", "quiet intensity", "-o", str(output),
        ],
    )

    main()

    assert mock_gen.call_args.kwargs["instruct"] == "quiet intensity"


# ---------------------------------------------------------------------------
# Missing voice file
# ---------------------------------------------------------------------------

@patch("voiceover.cli.sf")
@patch("voiceover.cli.generate_audio")
def test_missing_voice_gives_clear_error(
    mock_gen, mock_sf, cli_env, monkeypatch, capsys,
):
    """A non-existent voice file prints an error and exits with code 1."""
    output = cli_env["tmp_path"] / "out.wav"
    monkeypatch.setattr(
        sys, "argv",
        ["voiceover", "Hello", "--voice", "nonexistent", "-o", str(output)],
    )

    with pytest.raises(SystemExit) as exc_info:
        main()

    assert exc_info.value.code == 1
    captured = capsys.readouterr()
    assert "Voice file not found" in captured.err
    mock_gen.assert_not_called()


# ---------------------------------------------------------------------------
# Script / dialogue mode
# ---------------------------------------------------------------------------

@patch("voiceover.cli.sf")
@patch("voiceover.cli.generate_audio")
def test_script_mode_produces_output(mock_gen, mock_sf, cli_env, monkeypatch):
    """--script mode calls generate_audio once per speaker turn."""
    # Create voice files for both speakers
    (cli_env["voices_dir"] / "voice_a.wav").write_bytes(b"fake")
    (cli_env["voices_dir"] / "voice_b.wav").write_bytes(b"fake")

    script = cli_env["tmp_path"] / "dialogue.md"
    script.write_text(
        textwrap.dedent("""\
            **A:** Hello there.

            **B:** Hi back.

            **A:** Goodbye.
        """),
        encoding="utf-8",
    )

    mock_gen.return_value = (np.zeros(1000, dtype=np.float32), 24000)

    output = cli_env["tmp_path"] / "out.wav"
    monkeypatch.setattr(
        sys, "argv",
        [
            "voiceover",
            "--script", str(script),
            "--voice-map", "A=voice_a,B=voice_b",
            "-o", str(output),
        ],
    )

    main()

    # Three turns → three generate_audio calls
    assert mock_gen.call_count == 3
    mock_sf.write.assert_called_once()


@patch("voiceover.cli.sf")
@patch("voiceover.cli.generate_audio")
def test_script_mode_missing_voice_map_errors(
    mock_gen, mock_sf, cli_env, monkeypatch,
):
    """--script without --voice-map should cause argparse to error."""
    script = cli_env["tmp_path"] / "dialogue.md"
    script.write_text("**A:** Hello.\n", encoding="utf-8")

    output = cli_env["tmp_path"] / "out.wav"
    monkeypatch.setattr(
        sys, "argv",
        ["voiceover", "--script", str(script), "-o", str(output)],
    )

    with pytest.raises(SystemExit) as exc_info:
        main()

    assert exc_info.value.code == 2  # argparse error


# ---------------------------------------------------------------------------
# Help
# ---------------------------------------------------------------------------

def test_help_exits_zero(monkeypatch):
    """--help prints usage and exits with code 0."""
    monkeypatch.setattr(sys, "argv", ["voiceover", "--help"])

    with pytest.raises(SystemExit) as exc_info:
        main()

    assert exc_info.value.code == 0
