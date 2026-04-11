# Voiceover CLI — Requirements

## Context

A working TTS-with-voice-cloning script exists in `mythline/src/voiceover.py`. It uses Qwen3-TTS, supports chunking long text, normalizing audio, and cloning from reference WAV files. It works but is tightly coupled to mythline's directory structure (`voices/{actor}.wav` relative to CWD) and is not installable as a standalone tool.

**Goal**: Extract into a pip-installable package that provides a system-wide `voiceover` command.

---

## User Stories

### US-1: Install and invoke globally
**As** a user,
**I want** to `pip install .` the voiceover package and run `voiceover` from any directory,
**So that** I can generate speech without navigating to a specific project folder.

**Acceptance Criteria**:
- `pip install .` (or `pip install -e .`) succeeds.
- `voiceover --help` works from any directory.
- Console entry point is `voiceover` → `voiceover.cli:main`.

### US-2: Generate speech with voice cloning
**As** a user,
**I want** to run `voiceover "text" --voice lunastis --instruct "quiet intensity" -o out.wav`,
**So that** I get a WAV file with the text spoken in the cloned voice.

**Acceptance Criteria**:
- Positional `text` argument is required.
- `--voice` selects a voice reference from the voices directory (`{voice}.wav`).
- `--instruct` is optional, passes emotion/style instruction to the model.
- `--ref-text` is optional, provides transcript of reference audio for higher-quality cloning.
- `-o` / `--output` specifies the output WAV path (required).
- Long text is chunked at sentence boundaries, chunks concatenated with silence gaps.
- Output audio is RMS-normalized.

### US-3: Voice references in a standard location
**As** a user,
**I want** voice reference files to live in `~/.voiceover/voices/` by default,
**So that** they're available system-wide regardless of CWD.

**Acceptance Criteria**:
- Default voices directory is `~/.voiceover/voices/`.
- If `--voice lunastis` is specified, the tool looks for `~/.voiceover/voices/lunastis.wav`.
- Clear error message if the voice WAV is not found, including the expected path.

### US-4: Optional config file for defaults
**As** a user,
**I want** to set defaults in `~/.voiceover/config.yml` so I don't have to repeat common flags,
**So that** I can just run `voiceover "text" -o out.wav` with my preferred voice.

**Acceptance Criteria**:
- Config file at `~/.voiceover/config.yml` is optional — tool works without it.
- Supported config keys:
  - `voice` — default voice name (used when `--voice` is omitted)
  - `voices_dir` — override the voices directory path
  - `device` — torch device string (default: `cuda:0`)
  - `instruct` — default instruct text
- CLI flags always override config file values.
- Missing or empty config file is not an error.

### US-5: Stdin support for piped text
**As** a user,
**I want** to pipe text via stdin when no positional text argument is given,
**So that** I can use voiceover in shell pipelines (e.g., `echo "hello" | voiceover --voice luna -o out.wav`).

**Acceptance Criteria**:
- If `text` argument is `-` or omitted and stdin is not a TTY, read from stdin.
- If stdin is a TTY and no text provided, print error and exit.

### US-6: Script mode for multi-speaker dialogues
**As** a user,
**I want** to run `voiceover --script dialogue.md --voice-map "V=lunastis,G=alaria" -o out.wav`,
**So that** I can render a multi-speaker markdown dialogue into a single WAV file with each speaker in their own cloned voice.

**Acceptance Criteria**:
- `--script <path>` accepts a markdown dialogue file; it is mutually exclusive with the positional `text` argument.
- `--voice-map "V=lunastis,G=alaria"` maps speaker tag labels to voice names; it is mutually exclusive with `--voice`.
- `--instruct-map "V=quiet intensity,G=thoughtful and analytical"` maps speaker tag labels to instruct text (optional; per-speaker overrides).
- Speaker blocks are identified by the pattern `**SPEAKER:**` at the start of a line (e.g., `**V:**`, `**G:**`); everything that follows until the next speaker tag is that speaker's block.
- Markdown formatting is stripped before TTS input: `###` section markers, `**bold**`, `*italic*`, list bullet prefixes (`- `, `*   `), and `---` horizontal rule separators.
- Numbered section headers within a speaker's block (e.g., `### 1. The Liquid as Medium`) are spoken as plain prose — the leading `###` and any leading number+period prefix are removed, leaving only the title words.
- Output is a single WAV file containing all speaker turns concatenated in document order, with a silence gap between each turn.
- `--output` / `-o` remains required when `--script` is used.
- Clear error message if a speaker tag in the file has no entry in `--voice-map`.
