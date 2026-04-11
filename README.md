# Voiceover

A pip-installable CLI for text-to-speech with voice cloning, powered by [Qwen3-TTS](https://huggingface.co/Qwen/Qwen3-TTS-12Hz-1.7B-Base). Clone any voice from a short reference clip and generate speech with emotion/style control.

Two modes: **single-voice** for quick TTS, and **script mode** for multi-speaker dialogues from markdown files.

## Requirements

- Python 3.11+
- NVIDIA GPU with CUDA support
- ~4 GB VRAM (model runs in bfloat16). 6+ GB recommended for longer texts.

## Installation

PyTorch with CUDA must be installed separately — see [pytorch.org](https://pytorch.org/get-started/locally/) for the right command for your CUDA version.

```bash
# Install PyTorch with CUDA first (example for CUDA 12.6)
pip install torch --index-url https://download.pytorch.org/whl/cu126

# Then install voiceover from source
git clone https://github.com/your-org/voiceover.git
cd voiceover
pip install .
```

## Quick Start

### Single-Voice Mode

```bash
voiceover "Hello world, this is a test." --voice myvoice -o output.wav
```

### Pipe from stdin

```bash
echo "Hello from a pipe" | voiceover --voice myvoice -o output.wav
# or explicitly:
voiceover - --voice myvoice -o output.wav
```

### Script Mode (Multi-Speaker)

Given a markdown dialogue file (`dialogue.md`):

```markdown
**V:** The signal is fading. We need to move now.

**G:** I know. But the path ahead isn't clear.
```

Generate a multi-speaker audio file:

```bash
voiceover --script dialogue.md --voice-map "V=lunastis,G=alaria" -o scene.wav
```

Each speaker turn is generated with the mapped voice and concatenated with 500ms gaps between turns.

## Voice Setup

Place reference WAV files in `~/.voiceover/voices/`:

```
~/.voiceover/voices/
  lunastis.wav
  alaria.wav
```

The voice name is the filename without `.wav` — so `--voice lunastis` loads `lunastis.wav`.

**Tips for reference clips:**

- 5-15 seconds of clean speech
- WAV format (not MP3)
- Minimal background noise
- Use `--ref-text` with a transcript of the reference clip for better cloning quality

## Configuration

Create `~/.voiceover/config.yml` to set defaults (all keys optional, CLI flags override):

```yaml
# Default voice name
voice: lunastis

# Voice reference directory (supports ~ expansion)
voices_dir: ~/.voiceover/voices

# Torch device
device: cuda:0

# Default emotion/style instruction
instruct: "steady, cinematic narration"
```

An example config is included at `config/config.example.yml`.

## CLI Reference

```
voiceover [text] [options]
```

| Flag | Description |
|------|-------------|
| `text` | Text to speak (positional). Use `-` for stdin. Omit when using `--script`. |
| `--voice NAME` | Voice name (loads `~/.voiceover/voices/{NAME}.wav`). Required unless set in config. |
| `--instruct TEXT` | Emotion/style instruction, e.g. `"calm but determined"`. |
| `--ref-text TEXT` | Transcript of the voice reference audio. Improves cloning quality. |
| `--script PATH` | Markdown dialogue file. Mutually exclusive with positional text. |
| `--voice-map MAP` | Speaker-to-voice mapping, e.g. `"V=lunastis,G=alaria"`. Required with `--script`. |
| `--instruct-map MAP` | Per-speaker style instructions, e.g. `"V=quiet intensity,G=thoughtful"`. Optional. |
| `-o, --output PATH` | Output WAV file path. **Required.** |

## Script Format

Script files use the `**SPEAKER:**` markdown convention:

```markdown
**V:** First line of dialogue.

**G:** Response from another speaker.

**V:** And so on.
```

- Speaker labels must match keys in `--voice-map`
- Markdown formatting (bold, italic, headers, bullets, horizontal rules) is automatically stripped before synthesis
- Content before the first speaker tag (titles, preamble) is skipped

## Troubleshooting

**CUDA out of memory**: The model needs ~4 GB VRAM. Close other GPU applications. Long texts are automatically chunked (120 words per chunk) to manage memory, but very long scripts with many speakers can accumulate usage. Try `device: cuda:0` explicitly in config if you have multiple GPUs.

**CUDA not available**: Ensure PyTorch is installed with CUDA support (`python -c "import torch; print(torch.cuda.is_available())"`). CPU inference is not supported.

**Voice sounds wrong**:
- Use a cleaner reference clip (less background noise)
- Keep reference clips to 5-15 seconds
- Provide `--ref-text` with an accurate transcript of the reference audio
- Try different `--instruct` values to steer the output style

**Model download**: The Qwen3-TTS model (~3.4 GB) downloads automatically on first run from Hugging Face. Ensure you have internet access and sufficient disk space.

## License

MIT License. See [LICENSE](LICENSE).
