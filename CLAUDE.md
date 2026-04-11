# Voiceover

System-wide CLI tool for text-to-speech with voice cloning using Qwen3-TTS.

## Project Structure

```
src/voiceover/       — Package source
  __init__.py
  cli.py             — CLI entry point
  config.py          — Config loading from ~/.voiceover/
  engine.py          — TTS generation, chunking, normalization
tests/               — Tests
config/              — Default config templates
.claude/specs/       — Spec-driven development
```

## User Config

- `~/.voiceover/voices/` — Voice reference WAV files
- `~/.voiceover/config.yml` — Optional defaults (voice, device, voices_dir)

## CLI Usage

```
voiceover "text to speak" --voice lunastis --instruct "quiet intensity" -o out.wav
```

## Dependencies

- qwen_tts (Qwen3-TTS-12Hz-1.7B-Base)
- torch (CUDA)
- soundfile, numpy
