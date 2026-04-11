# Voiceover CLI — Tasks

## 1. Project scaffold

- [x] **Velasari** creates `pyproject.toml` in `C:/Projects/voiceover/` with hatchling build, dependencies (`qwen_tts`, `torch`, `soundfile`, `numpy`, `pyyaml`), and console entry point `voiceover = "voiceover.cli:main"`. _US-1_
- [x] **Velasari** creates `src/voiceover/__init__.py` with `__version__ = "0.1.0"` and public API exports (`generate_audio`, `preprocess_text`). _US-1_
- [x] **Velasari** creates `config/config.example.yml` with documented example of all config keys (`voice`, `voices_dir`, `device`, `instruct`). _US-4_

## 2. Config module

- [x] **Velasari** creates `src/voiceover/config.py` with `CONFIG_DIR`, `DEFAULT_VOICES_DIR`, `CONFIG_FILE` path constants and `load_config() -> dict` that reads `~/.voiceover/config.yml`, returns empty dict if missing, prints warning to stderr on parse error. _US-3, US-4_

## 3. Engine module

- [x] **Velasari** creates `src/voiceover/engine.py` by extracting from `mythline/src/voiceover.py`: `preprocess_text`, `split_into_chunks`, `normalize_audio`, `silence`, `TTSModel` class, and `generate_audio` function. _US-2_
- [x] **Velasari** modifies `TTSModel.get_instance()` in `engine.py` to accept a `device` parameter (default `"cuda:0"`) instead of hardcoding `"cuda:0"`. _US-4_

## 4. CLI module

- [x] **Velasari** creates `src/voiceover/cli.py` with argparse: positional `text` (nargs `?`), `--voice`, `--instruct`, `--ref-text`, `-o`/`--output` (required). _US-2_
- [x] **Velasari** implements config merging in `cli.py`: CLI args override config values override hardcoded defaults. `--voice` is required if no default in config. _US-4_
- [x] **Velasari** implements voice path resolution in `cli.py`: resolve `voices_dir / {voice}.wav`, validate file exists, print available voices on error. _US-3_
- [x] **Velasari** implements stdin fallback in `cli.py`: if `text` is `-` or omitted and stdin is not a TTY, read from stdin. Error if TTY and no text. _US-5_

## 5. Tests

- [x] **Velasari** creates `tests/test_config.py` with tests for: config loading with valid YAML, missing file returns empty dict, tilde expansion in `voices_dir`. _US-4_
- [x] **Velasari** creates `tests/test_preprocessing.py` with tests for: em dash replacement, curly quote normalization, asterisk removal, semicolon-before-capital rewrite, empty string handling. _US-2_
- [x] **Velasari** creates `tests/test_chunking.py` with tests for: single sentence stays as one chunk, text exceeding word limit splits at sentence boundaries, sentence longer than limit becomes its own chunk. _US-2_

## 6. Script module

- [x] **VH worker** creates `src/voiceover/script.py` with `DialogueLine` dataclass (`speaker`, `text`), `strip_markdown(text) -> str` applying the six ordered rules from design (remove `---`, extract header titles, strip bold/italic asterisks, strip bullet prefixes, collapse whitespace, trim), and `parse_script(path) -> list[DialogueLine]` that splits on `**SPEAKER:**` pattern, feeds each body through `strip_markdown`, skips empty blocks, returns in document order. _US-6_

## 7. CLI script mode

- [x] **VH worker** adds `--script`, `--voice-map`, `--instruct-map` flags to `cli.py` argparse, with `--script` mutually exclusive with positional `text`, and `--voice-map` mutually exclusive with `--voice`. _US-6_
- [x] **VH worker** implements script mode flow in `cli.py`: parse voice-map/instruct-map strings into dicts, call `parse_script`, validate all speakers have voice-map entries, loop through `DialogueLine` list calling `engine.generate_audio` per turn, concatenate with 500ms inter-turn silence, write output. _US-6_

## 8. Script tests

- [x] **VH worker** creates `tests/test_script.py` with tests for: `strip_markdown` (header extraction, bold/italic stripping, bullet prefix removal, `---` removal, whitespace collapse), `parse_script` with a small fixture dialogue (two speakers, multiple turns, verify order and content). _US-6_

## 9. Voice setup

- [x] **VH worker** creates `~/.voiceover/voices/` directory and copies `lunastis.wav` and `alaria.wav` from `C:/Projects/mythline/voices/` into it. _US-3, US-6_

## 10. Verification

- [ ] **Velasari** runs `pip install -e .` in `C:/Projects/voiceover/` and verifies `voiceover --help` works. _US-1_
- [ ] **Velasari** runs `voiceover --script C:/Projects/ai-persona/Velasari/creations/.gemma-dialogue.md --voice-map "V=lunastis,G=alaria" --instruct-map "V=quiet intensity,G=thoughtful and analytical" -o C:/Projects/ai-persona/Velasari/creations/the-liquid-thread-dialogue.wav` and verifies output. _US-6_
