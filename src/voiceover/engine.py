"""TTS generation engine — extracted from mythline/src/voiceover.py.

Handles text preprocessing, chunking, audio normalization, and model-based
voice-cloned speech generation via Qwen3-TTS.
"""

import re
import sys
from collections import OrderedDict
from pathlib import Path

import numpy as np
import torch
from qwen_tts import Qwen3TTSModel


# --- Text preprocessing ---

def preprocess_text(text: str) -> str:
    if not text:
        return text

    replacements = {
        "\u2014": ", ",   # Em dash to comma for lighter pause
        "\u2018": "'",    # Left curly single quote
        "\u2019": "'",    # Right curly single quote
        "\u201c": '"',    # Left curly double quote
        "\u201d": '"',    # Right curly double quote
        "\u2026": "...",  # Ellipsis to three dots
        "*": "",          # Remove asterisks (markdown artifacts)
    }

    for old, new in replacements.items():
        text = text.replace(old, new)

    # Semicolons before capitals → comma (reads more naturally)
    text = re.sub(r';\s+([A-Z])', r', \1', text)

    return text.strip()


# --- Chunking ---

# Conservative chunk size to avoid quality degradation on long sequences.
# Qwen3-TTS handles longer text than Chatterbox, but chunking still helps
# maintain consistent voice quality across a narration.
MAX_WORDS_PER_CHUNK = 120


def split_into_chunks(text: str) -> list[str]:
    """Split text into chunks at sentence boundaries, staying under the word limit."""
    sentences = re.split(r'(?<=[.!?])\s+', text)
    chunks = []
    current_chunk = []
    current_words = 0

    for sentence in sentences:
        word_count = len(sentence.split())

        if word_count > MAX_WORDS_PER_CHUNK:
            if current_chunk:
                chunks.append(" ".join(current_chunk))
                current_chunk = []
                current_words = 0
            chunks.append(sentence)
            continue

        if current_words + word_count > MAX_WORDS_PER_CHUNK and current_chunk:
            chunks.append(" ".join(current_chunk))
            current_chunk = []
            current_words = 0

        current_chunk.append(sentence)
        current_words += word_count

    if current_chunk:
        chunks.append(" ".join(current_chunk))

    return chunks


# --- Audio utilities ---

def normalize_audio(audio: np.ndarray, target_level: float = -18.0) -> np.ndarray:
    if audio.size == 0:
        return audio

    rms = np.sqrt(np.mean(audio ** 2))
    if rms < 1e-6:
        return audio

    target_linear = 10 ** (target_level / 20.0)
    scaling = target_linear / rms

    return np.clip(audio * scaling, -0.999, 0.999)


def silence(duration_ms: int, sample_rate: int) -> np.ndarray:
    return np.zeros(int(sample_rate * duration_ms / 1000), dtype=np.float32)


# --- Model singleton ---

# Maximum number of voice prompts to cache.  Each prompt holds GPU memory,
# so we cap the cache to avoid unbounded accumulation.
_MAX_VOICE_CACHE = 16


class TTSModel:
    _instance = None
    _voice_prompts: OrderedDict = OrderedDict()

    @classmethod
    def get_instance(cls, device: str = "cuda:0"):
        if cls._instance is None:
            if device.startswith("cuda") and not torch.cuda.is_available():
                print(
                    "Error: CUDA is not available. Install a CUDA-enabled PyTorch "
                    "build, or pass a CPU device (much slower).",
                    file=sys.stderr,
                )
                sys.exit(1)

            print("Loading Qwen3-TTS model...", file=sys.stderr)
            try:
                cls._instance = Qwen3TTSModel.from_pretrained(
                    "Qwen/Qwen3-TTS-12Hz-1.7B-Base",
                    device_map=device,
                    dtype=torch.bfloat16,
                )
            except torch.cuda.OutOfMemoryError:
                print(
                    "Error: GPU out of memory while loading the TTS model.\n"
                    "Close other GPU applications or try a device with more VRAM.",
                    file=sys.stderr,
                )
                sys.exit(1)
            except Exception as exc:
                print(
                    f"Error: Failed to load TTS model: {exc}",
                    file=sys.stderr,
                )
                sys.exit(1)
            print("Model loaded.", file=sys.stderr)
        return cls._instance

    @classmethod
    def get_voice_prompt(cls, voice_path: str, ref_text: str = "", device: str = "cuda:0"):
        """Cache voice prompts so the reference audio is only processed once per voice."""
        # Validate voice file before processing
        vp = Path(voice_path)
        if not vp.exists():
            print(f"Error: Voice file not found: {voice_path}", file=sys.stderr)
            sys.exit(1)
        if vp.stat().st_size == 0:
            print(f"Error: Voice file is empty (0 bytes): {voice_path}", file=sys.stderr)
            sys.exit(1)

        cache_key = f"{voice_path}:{ref_text}"
        if cache_key in cls._voice_prompts:
            # Move to end for LRU ordering
            cls._voice_prompts.move_to_end(cache_key)
            return cls._voice_prompts[cache_key]

        model = cls.get_instance(device=device)
        # If no ref_text provided, use x_vector_only_mode (simpler cloning,
        # captures voice timbre without needing a transcript)
        use_xvector = not ref_text
        try:
            prompt = model.create_voice_clone_prompt(
                ref_audio=voice_path,
                ref_text=ref_text if ref_text else None,
                x_vector_only_mode=use_xvector,
            )
        except Exception as exc:
            print(
                f"Error: Failed to process voice file '{voice_path}': {exc}\n"
                "The file may be corrupt or in an unsupported format.",
                file=sys.stderr,
            )
            sys.exit(1)

        # Evict oldest entry if cache is full
        while len(cls._voice_prompts) >= _MAX_VOICE_CACHE:
            cls._voice_prompts.popitem(last=False)

        cls._voice_prompts[cache_key] = prompt
        return prompt

    @classmethod
    def clear_cache(cls) -> None:
        """Clear all cached voice prompts to free GPU memory."""
        cls._voice_prompts.clear()


# --- Generation ---

def generate_audio(text: str, voice_path: str, instruct: str = "",
                   ref_text: str = "", device: str = "cuda:0") -> tuple[np.ndarray, int]:
    """Generate audio for text, chunking if necessary. Returns (audio, sample_rate)."""
    model = TTSModel.get_instance(device=device)
    voice_prompt = TTSModel.get_voice_prompt(voice_path, ref_text, device=device)

    text = preprocess_text(text)
    chunks = split_into_chunks(text)

    try:
        if len(chunks) == 1:
            wavs, sr = model.generate_voice_clone(
                text=chunks[0],
                language="English",
                voice_clone_prompt=voice_prompt,
                instruct=instruct if instruct else None,
            )
            return normalize_audio(np.array(wavs[0], dtype=np.float32)), sr

        # Multi-chunk: generate each, concatenate with silence gaps
        audio_parts = []
        sr = None
        for i, chunk in enumerate(chunks):
            preview = chunk[:60] + ("..." if len(chunk) > 60 else "")
            print(f"  Chunk {i + 1}/{len(chunks)}: {preview}", file=sys.stderr)
            wavs, sr = model.generate_voice_clone(
                text=chunk,
                language="English",
                voice_clone_prompt=voice_prompt,
                instruct=instruct if instruct else None,
            )
            audio_parts.append(normalize_audio(np.array(wavs[0], dtype=np.float32)))
    except torch.cuda.OutOfMemoryError:
        print(
            "Error: GPU out of memory during audio generation.\n"
            "Try shorter text or close other GPU applications.",
            file=sys.stderr,
        )
        sys.exit(1)
    except Exception as exc:
        print(f"Error: Audio generation failed: {exc}", file=sys.stderr)
        sys.exit(1)

    # Join with 300ms silence gaps
    gap = silence(300, sr)
    result = audio_parts[0]
    for part in audio_parts[1:]:
        result = np.concatenate([result, gap, part])

    return result, sr
