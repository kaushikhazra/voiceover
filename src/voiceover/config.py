"""Config loading from ~/.voiceover/config.yml."""

import sys
from pathlib import Path

import yaml

CONFIG_DIR = Path.home() / ".voiceover"
DEFAULT_VOICES_DIR = CONFIG_DIR / "voices"
CONFIG_FILE = CONFIG_DIR / "config.yml"


def load_config() -> dict:
    """Load config from ~/.voiceover/config.yml.

    Returns an empty dict if the file does not exist.
    Prints a warning to stderr on YAML parse error and returns empty dict.
    """
    defaults = {"voices_dir": DEFAULT_VOICES_DIR}

    if not CONFIG_FILE.exists():
        return defaults

    try:
        with open(CONFIG_FILE, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f)
        if data is None:
            return defaults
        if not isinstance(data, dict):
            print(
                f"Warning: {CONFIG_FILE} is not a valid YAML mapping — ignoring.",
                file=sys.stderr,
            )
            return defaults
        # Ensure voices_dir is always a Path object
        if "voices_dir" in data and data["voices_dir"]:
            data["voices_dir"] = Path(str(data["voices_dir"])).expanduser()
        else:
            data["voices_dir"] = DEFAULT_VOICES_DIR
        return data
    except yaml.YAMLError as exc:
        print(
            f"Warning: Failed to parse {CONFIG_FILE}: {exc} — using defaults.",
            file=sys.stderr,
        )
        return defaults
