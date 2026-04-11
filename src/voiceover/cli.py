"""CLI entry point for the voiceover tool."""

import argparse
import os
import sys
from pathlib import Path

import numpy as np
import soundfile as sf

from voiceover import config as cfg
from voiceover.engine import generate_audio, silence
from voiceover.script import parse_script


def _parse_kv_map(s: str, label: str = "map") -> dict[str, str]:
    """Parse a ``K=v,K2=v2`` string into a dict. Values may contain spaces.

    Raises *ValueError* on malformed tokens (missing ``=`` or empty key/value).
    """
    result = {}
    for token in s.split(','):
        token = token.strip()
        if not token:
            continue
        if '=' not in token:
            raise ValueError(
                f"Invalid {label} entry '{token}': expected KEY=VALUE format."
            )
        key, _, value = token.partition('=')
        key = key.strip()
        value = value.strip()
        if not key:
            raise ValueError(
                f"Invalid {label} entry '{token}': key cannot be empty."
            )
        if not value:
            raise ValueError(
                f"Invalid {label} entry '{token}': value cannot be empty for key '{key}'."
            )
        result[key] = value
    return result


def _list_available_voices(voices_dir: Path) -> None:
    """Print available voices in voices_dir to stderr."""
    if voices_dir.exists():
        wavs = sorted(voices_dir.glob("*.wav"))
        if wavs:
            print("Available voices:", file=sys.stderr)
            for wav in wavs:
                print(f"  {wav.stem}", file=sys.stderr)
        else:
            print(f"No voice WAV files found in {voices_dir}", file=sys.stderr)
    else:
        print(f"Voices directory does not exist: {voices_dir}", file=sys.stderr)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Generate voice-cloned speech from text using Qwen3-TTS.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "Examples:\n"
            "  voiceover \"Hello world\" --voice lunastis -o out.wav\n"
            "  echo \"Hello\" | voiceover --voice lunastis -o out.wav\n"
            "  voiceover --script dialogue.md --voice-map \"V=lunastis,G=alaria\" -o out.wav\n"
        ),
    )

    # Positional — optional so --script can be used instead
    parser.add_argument(
        "text",
        nargs="?",
        default=None,
        help="Text to speak. Use '-' to read from stdin. Omit when using --script.",
    )

    # Single-voice flags
    parser.add_argument(
        "--voice",
        default=None,
        help="Voice name (loads {voices_dir}/{voice}.wav). Required unless set in config.",
    )
    parser.add_argument(
        "--instruct",
        default=None,
        help="Emotion/style instruction (e.g., 'calm but determined').",
    )
    parser.add_argument(
        "--ref-text",
        default="",
        help="Transcript of the voice reference audio (improves cloning quality).",
    )

    # Script/dialogue mode flags
    parser.add_argument(
        "--script",
        default=None,
        metavar="PATH",
        help="Markdown dialogue file. Mutually exclusive with positional text.",
    )
    parser.add_argument(
        "--voice-map",
        default=None,
        metavar="MAP",
        help='Speaker-to-voice mapping, e.g. "V=lunastis,G=alaria". Required with --script.',
    )
    parser.add_argument(
        "--instruct-map",
        default=None,
        metavar="MAP",
        help='Per-speaker instruct text, e.g. "V=quiet intensity,G=thoughtful". Optional.',
    )

    # Output
    parser.add_argument(
        "-o", "--output",
        required=True,
        help="Output WAV file path.",
    )

    args = parser.parse_args()

    # --- Manual mutual-exclusion validation ---
    if args.script and args.text is not None:
        parser.error("Cannot use both --script and positional text argument.")

    # --- Resolve text / stdin ---
    text: str | None = None
    if not args.script:
        if args.text == '-' or (args.text is None and not sys.stdin.isatty()):
            text = sys.stdin.read()
        elif args.text is not None:
            text = args.text
        else:
            parser.error(
                "No text provided. Pass text as a positional argument, "
                "pipe via stdin, or use --script for dialogue mode."
            )

    # --- Load config and resolve shared settings ---
    conf = cfg.load_config()

    voices_dir: Path = conf["voices_dir"]
    device: str = conf.get("device", "cuda:0")

    # --- Ensure output directory exists ---
    output_path = Path(args.output)
    os.makedirs(output_path.parent, exist_ok=True)

    # =========================================================
    # BRANCH: Script / dialogue mode
    # =========================================================
    if args.script:
        if not args.voice_map:
            parser.error("--voice-map is required when using --script.")

        try:
            voice_map = _parse_kv_map(args.voice_map, label="--voice-map")
        except ValueError as exc:
            parser.error(str(exc))
        try:
            instruct_map = _parse_kv_map(args.instruct_map, label="--instruct-map") if args.instruct_map else {}
        except ValueError as exc:
            parser.error(str(exc))

        # Parse dialogue — pass known speakers so bold labels aren't mistaken for tags
        dialogue = parse_script(args.script, speakers=set(voice_map.keys()))
        if not dialogue:
            print("Error: No speaker turns found in the script.", file=sys.stderr)
            sys.exit(1)

        # Validate all speakers have voice-map entries
        speakers_in_file = {line.speaker for line in dialogue}
        missing = speakers_in_file - set(voice_map)
        if missing:
            print(
                f"Error: Speaker(s) {sorted(missing)} found in script "
                f"but not in --voice-map.",
                file=sys.stderr,
            )
            sys.exit(1)

        # Pre-flight: resolve and verify ALL voice WAV files before spending
        # GPU time on generation.  Fail fast with a clear listing.
        missing_files: list[str] = []
        for speaker, voice_name in voice_map.items():
            vpath = voices_dir / f"{voice_name}.wav"
            if not vpath.exists():
                missing_files.append(f"  {speaker} -> {vpath}")
        if missing_files:
            print(
                "Error: The following voice files are missing:\n"
                + "\n".join(missing_files),
                file=sys.stderr,
            )
            _list_available_voices(voices_dir)
            sys.exit(1)

        # Generate per turn
        audio_parts: list[np.ndarray] = []
        sample_rate: int | None = None

        for i, line in enumerate(dialogue):
            voice_name = voice_map[line.speaker]
            voice_path = str(voices_dir / f"{voice_name}.wav")
            instruct = instruct_map.get(line.speaker, "")

            preview = line.text[:60] + ("..." if len(line.text) > 60 else "")
            print(f"[{line.speaker}] {preview}", file=sys.stderr)

            audio, sr = generate_audio(
                text=line.text,
                voice_path=voice_path,
                instruct=instruct,
                ref_text="",
                device=device,
            )
            audio_parts.append(audio)
            sample_rate = sr

        # Concatenate with 500ms inter-turn gaps
        gap = silence(500, sample_rate)
        result = audio_parts[0]
        for part in audio_parts[1:]:
            result = np.concatenate([result, gap, part])

        sf.write(str(output_path), result, sample_rate)
        duration_sec = len(result) / sample_rate
        print(f"Saved: {output_path} ({duration_sec:.1f}s, {len(dialogue)} turns)", file=sys.stderr)
        return

    # =========================================================
    # BRANCH: Single-voice mode
    # =========================================================
    voice = args.voice or conf.get("voice")
    if not voice:
        parser.error(
            "No voice specified. Use --voice or set 'voice' in ~/.voiceover/config.yml."
        )

    instruct = args.instruct if args.instruct is not None else conf.get("instruct", "")
    voice_path = voices_dir / f"{voice}.wav"

    if not voice_path.exists():
        print(f"Error: Voice file not found: {voice_path}", file=sys.stderr)
        _list_available_voices(voices_dir)
        sys.exit(1)

    print(f"Voice: {voice}", file=sys.stderr)
    if instruct:
        print(f"Instruct: {instruct}", file=sys.stderr)
    preview = text[:80] + ("..." if len(text) > 80 else "")
    print(f"Text: {preview}", file=sys.stderr)

    audio, sr = generate_audio(
        text=text,
        voice_path=str(voice_path),
        instruct=instruct,
        ref_text=args.ref_text,
        device=device,
    )

    sf.write(str(output_path), audio, sr)
    duration_sec = len(audio) / sr
    print(f"Saved: {output_path} ({duration_sec:.1f}s)", file=sys.stderr)


if __name__ == "__main__":
    main()
