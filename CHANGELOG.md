# Changelog

## [1.0.0] - 2026-04-11

Initial release.

### Added

- Single-voice TTS with voice cloning via Qwen3-TTS (Qwen3-TTS-12Hz-1.7B-Base)
- Multi-speaker script mode with `--script` and `--voice-map` for markdown dialogue files
- Emotion/style control via `--instruct` flag and per-speaker `--instruct-map`
- LRU voice prompt cache (reference audio processed once per voice, bounded memory)
- Automatic text chunking at sentence boundaries (120-word limit) for consistent quality
- Audio normalization to -20 dB
- Text preprocessing: smart quotes, em dashes, ellipsis, markdown artifacts
- Markdown stripping in script mode: bold, italic, headers, bullets, horizontal rules
- `_parse_kv_map` input validation with clear error messages for malformed key=value pairs
- Pre-flight WAV file checks (existence, format validity) before TTS generation
- `strip_markdown` rule order fix (bold before italic to prevent residual asterisks)
- Error handling throughout CLI and engine with user-friendly messages
- `--ref-text` support for transcript-guided voice cloning
- Stdin input support (pipe text or use `-`)
- User configuration via `~/.voiceover/config.yml` (voice, device, voices_dir, instruct)
- Full packaging metadata (classifiers, license, URLs, entry point)
- Comprehensive test suite (81 tests): chunking, CLI, config, audio generation, normalization, kv parsing, preprocessing, script parsing, silence generation
