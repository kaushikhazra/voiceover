# Voiceover CLI — Design

## Package Structure

```
C:/Projects/voiceover/
  pyproject.toml
  src/voiceover/
    __init__.py          — Version string
    cli.py               — CLI entry point (argparse), config merging
    config.py            — Config loading from ~/.voiceover/config.yml
    engine.py            — TTS model, generation, chunking, audio utils
    script.py            — Script/dialogue parsing (DialogueLine, parse_script, strip_markdown)
  tests/
    test_config.py
    test_preprocessing.py
    test_chunking.py
    test_script.py
  config/
    config.example.yml   — Documented example config
```

Matches the structure already defined in `CLAUDE.md`.

---

## What Changes from mythline's `voiceover.py`

| Aspect | mythline (before) | voiceover package (after) |
|--------|-------------------|--------------------------|
| Voice path | `voices/{actor}.wav` relative to CWD | `~/.voiceover/voices/{voice}.wav` (configurable) |
| CLI flag | `--actor` | `--voice` (clearer for a standalone tool) |
| Config | None | `~/.voiceover/config.yml` for defaults |
| Model device | Hardcoded `cuda:0` | Configurable via config (`device` key) |
| Installation | Run as `python -m src.voiceover` | `pip install .` → `voiceover` command |
| Text input | Positional only | Positional or stdin |
| Script/dialogue mode | Not supported | `--script` with `--voice-map` and `--instruct-map`; per-speaker generation, 500ms inter-turn gaps |

Core logic (preprocessing, chunking, normalization, generation) is **unchanged** — direct extraction.

---

## Module Responsibilities

### `cli.py`
- Argparse definition with all flags.
- Load config via `config.load_config()`.
- Merge: CLI args override config defaults.
- Resolve voice path: `voices_dir / {voice}.wav`.
- Validate inputs (voice file exists, text provided).
- Call `engine.generate_audio()`, write output with `soundfile`.
- Print progress/status to stderr, only write audio file as side effect.

**Script mode** (when `--script` is provided):
- New flags: `--script PATH`, `--voice-map "V=lunastis,G=alaria"`, `--instruct-map "V=quiet intensity,G=thoughtful"`.
- `--script` is mutually exclusive with positional `text`. Note: argparse cannot enforce mutual exclusion on positionals — make `text` `nargs='?'` and validate manually in `main()` (error if both `--script` and `text` provided, or neither).
- Parse `--voice-map` string into a dict at startup (`"K=v,K2=v2"` → `{"K": "v", "K2": "v2"}`). Same for `--instruct-map` (optional; defaults to all-empty).
- Error at startup if any speaker found in the parsed script has no entry in `--voice-map`.
- For each `DialogueLine` from `script.parse_script(path)`: resolve `voice_path = voices_dir / f"{voice_map[line.speaker]}.wav"`, resolve instruct from `instruct_map.get(line.speaker, "")`, call `engine.generate_audio(line.text, voice_path, instruct, ref_text="", device)`, collect resulting array.
- Print `[SPEAKER] text[:60]...` to stderr before generating each speaker turn.
- Concatenate all per-turn arrays with 500ms silence between turns. Within each turn, chunking and 300ms inter-chunk gaps are handled internally by `engine.generate_audio()`.
- Write the final concatenated audio with `soundfile`.

### `config.py`
- `CONFIG_DIR = Path.home() / ".voiceover"` — base directory.
- `DEFAULT_VOICES_DIR = CONFIG_DIR / "voices"` — default voices location.
- `CONFIG_FILE = CONFIG_DIR / "config.yml"` — optional config.
- `load_config() -> dict` — load and return config dict. Returns empty dict if file missing.
- Config schema (all keys optional):

```yaml
# ~/.voiceover/config.yml
voice: lunastis          # default voice name
voices_dir: ~/.voiceover/voices  # override voices directory
device: cuda:0           # torch device
instruct: ""             # default instruct text
```

- `voices_dir` supports `~` expansion.
- Pattern follows Velhari's `config.py` — load once, cache, simple accessor functions.

### `engine.py`
Extracted directly from `mythline/src/voiceover.py`:
- `preprocess_text(text: str) -> str` — unchanged.
- `split_into_chunks(text: str) -> list[str]` — unchanged.
- `normalize_audio(audio, target_level) -> ndarray` — unchanged.
- `silence(duration_ms, sample_rate) -> ndarray` — unchanged.
- `TTSModel` class — singleton pattern, unchanged except:
  - `get_instance(device: str = "cuda:0")` — accepts device parameter instead of hardcoding.
- `generate_audio(text, voice_path, instruct, ref_text, device) -> tuple[ndarray, int]` — passes device through.

### `script.py`

Handles markdown dialogue files where each speaker turn is introduced by a `**SPEAKER:**` tag at the start of a line (e.g. `**V:**`, `**G:**`). The format matches the `.gemma-dialogue.md` convention used in ai-persona.

- `DialogueLine` — dataclass: `speaker: str`, `text: str` (already cleaned for TTS).
- `parse_script(path: str) -> list[DialogueLine]` — parse a markdown dialogue file into an ordered list of `DialogueLine` objects.
  - Split the file on the pattern `^\*\*([^:]+):\*\*` at line start (regex, multiline). Each match captures the speaker name and begins a new block; everything up to the next match is that speaker's body.
  - Pass the raw body through `strip_markdown()`, then strip whitespace. Skip any resulting empty blocks (e.g. a stray `---` section with no real content).
  - Return lines in document order.
- `strip_markdown(text: str) -> str` — clean a dialogue body block for TTS. Public for testing. Rules applied in order:
  1. `---` lines → remove entirely.
  2. `#{1,6} N. Title` or `#{1,6} Title` header lines → keep title text only (drop all leading `#` marks and any leading `\d+\.\s*`). Handles `###`, `####`, etc.
  3. `**text**` and `*text*` → plain `text` (strip surrounding asterisks).
  4. Bullet prefixes `^\s*[\*\-]\s+` at line start → strip the prefix, keep content.
  5. Collapse runs of whitespace / blank lines between sentences → single space (produces a single flat string suitable for `split_into_chunks`).
  6. Strip leading/trailing whitespace.

### `__init__.py`
- `__version__ = "0.1.0"`
- Public API exports: `generate_audio`, `preprocess_text` (for programmatic use).

---

## pyproject.toml

```toml
[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[project]
name = "voiceover"
version = "0.1.0"
description = "Text-to-speech with voice cloning using Qwen3-TTS."
requires-python = ">=3.11"
dependencies = [
    "qwen_tts",
    "torch",
    "soundfile",
    "numpy",
    "pyyaml>=6.0",
]

[project.scripts]
voiceover = "voiceover.cli:main"

[tool.hatch.build.targets.wheel]
packages = ["src/voiceover"]
```

Uses hatchling (same as Velhari). `packages` points to `src/voiceover` for src-layout.

---

## Config Loading Flow

```
CLI invocation
  │
  ├─ parse args (argparse)
  ├─ load_config()  →  ~/.voiceover/config.yml (if exists)
  │
  ├─ merge: for each key, CLI arg wins if provided, else config value, else hardcoded default
  │    voices_dir: (no CLI flag)   || config["voices_dir"] || ~/.voiceover/voices
  │    device:     (no CLI flag)   || config["device"]     || "cuda:0"
  │
  ├─ BRANCH: if --script provided → script mode
  │    ├─ validate --voice-map provided (error if missing)
  │    ├─ parse voice-map and instruct-map into dicts
  │    ├─ parse_script(path) → list[DialogueLine]
  │    ├─ validate all speakers have voice-map entries
  │    ├─ for each line: resolve voice, generate, collect
  │    └─ concatenate with 500ms gaps, write output
  │
  └─ BRANCH: else → single-voice mode
       ├─ voice:    args.voice    || config["voice"]    || None (error if still None)
       ├─ instruct: args.instruct || config["instruct"] || ""
       ├─ resolve voice_path = voices_dir / f"{voice}.wav"
       ├─ validate voice_path exists
       └─ engine.generate_audio(text, voice_path, instruct, ref_text, device)
```

---

## Error Handling

- **Voice not found**: Print expected path, list available voices in the directory, exit 1.
- **No text provided**: Print usage hint, exit 1.
- **Model load failure**: Let torch/qwen_tts exceptions propagate naturally — no wrapping.
- **Config parse error**: Print warning to stderr, continue with defaults.
- **Output directory**: `os.makedirs` on the output path's parent before writing — never assume the directory exists.

---

## What This Spec Does NOT Cover

- No new TTS features (different models, streaming, etc.).
- No daemon/server mode.
- No voice management commands (add/list/remove voices).
- No GPU selection via CLI flag (config-only for now — CLI flag can come later).
