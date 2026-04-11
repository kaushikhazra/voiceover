"""Tests for voiceover.config — loading, missing file, tilde expansion."""

import sys
from pathlib import Path

import pytest
import yaml

# Make sure the package is importable without an installed qwen_tts
# (engine imports it at module level; config does not).


def test_load_valid_yaml(tmp_path, monkeypatch):
    """load_config() returns the dict from a well-formed YAML file."""
    config_file = tmp_path / "config.yml"
    config_file.write_text("voice: lunastis\ndevice: cpu\n", encoding="utf-8")

    import voiceover.config as cfg

    monkeypatch.setattr(cfg, "CONFIG_FILE", config_file)
    result = cfg.load_config()

    assert result["voice"] == "lunastis"
    assert result["device"] == "cpu"
    assert isinstance(result["voices_dir"], Path)  # always present


def test_missing_file_returns_defaults(tmp_path, monkeypatch):
    """load_config() returns defaults (with voices_dir) when config file does not exist."""
    import voiceover.config as cfg

    monkeypatch.setattr(cfg, "CONFIG_FILE", tmp_path / "nonexistent.yml")
    result = cfg.load_config()

    assert "voices_dir" in result
    assert isinstance(result["voices_dir"], Path)
    assert len(result) == 1  # only the voices_dir default


def test_empty_file_returns_defaults(tmp_path, monkeypatch):
    """load_config() returns defaults (with voices_dir) for an empty config file."""
    config_file = tmp_path / "config.yml"
    config_file.write_text("", encoding="utf-8")

    import voiceover.config as cfg

    monkeypatch.setattr(cfg, "CONFIG_FILE", config_file)
    result = cfg.load_config()

    assert "voices_dir" in result
    assert isinstance(result["voices_dir"], Path)
    assert len(result) == 1  # only the voices_dir default


def test_tilde_expansion(tmp_path, monkeypatch):
    """load_config() expands ~ in voices_dir to an absolute path."""
    config_file = tmp_path / "config.yml"
    config_file.write_text("voices_dir: ~/.voiceover/voices\n", encoding="utf-8")

    import voiceover.config as cfg

    monkeypatch.setattr(cfg, "CONFIG_FILE", config_file)
    result = cfg.load_config()

    voices_dir = result["voices_dir"]
    assert isinstance(voices_dir, Path)
    assert not str(voices_dir).startswith("~"), "Tilde should have been expanded"
    assert str(voices_dir).endswith(".voiceover/voices") or str(voices_dir).endswith(r".voiceover\voices")


def test_parse_error_returns_defaults(tmp_path, monkeypatch, capsys):
    """load_config() returns defaults and warns on YAML parse error."""
    config_file = tmp_path / "config.yml"
    config_file.write_text("key: [unclosed bracket\n", encoding="utf-8")

    import voiceover.config as cfg

    monkeypatch.setattr(cfg, "CONFIG_FILE", config_file)
    result = cfg.load_config()

    assert "voices_dir" in result
    assert isinstance(result["voices_dir"], Path)
    assert len(result) == 1  # only the voices_dir default
    captured = capsys.readouterr()
    assert "Warning" in captured.err
