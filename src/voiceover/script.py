"""Dialogue script parsing for multi-speaker markdown files.

Handles the **SPEAKER:** convention used in .gemma-dialogue.md and
similar ai-persona dialogue files.
"""

import re
from dataclasses import dataclass


@dataclass
class DialogueLine:
    speaker: str
    text: str  # Already cleaned for TTS


def strip_markdown(text: str) -> str:
    """Clean a markdown dialogue body block for TTS input.

    Rules applied in order:
    1. Remove ``---`` horizontal rule lines.
    2. Header lines (#{1,6} [N. ]Title) → keep title text only.
    3. Bullet prefixes (``*  `` / ``-  `` at line start) → strip prefix.
    4. **bold** and *italic* → plain text.
    5. Collapse whitespace / blank lines → single space.
    6. Strip leading/trailing whitespace.
    """
    # Rule 1: Remove --- lines
    text = re.sub(r'(?m)^-{3,}\s*$', '', text)

    # Rule 2: Header lines → title text only (drop # marks and optional N. prefix)
    # Matches: # or ## or ### ... (1–6 hashes), optional digits+period+space, then title
    text = re.sub(r'(?m)^#{1,6}\s+(?:\d+\.\s*)?(.+)$', r'\1', text)

    # Rule 3: Bullet prefixes at line start → strip
    # MUST run before bold/italic so that bullet `*` is not misread as
    # an italic delimiter on lines like `*   **Selection** implies... *after*`.
    text = re.sub(r'(?m)^\s*[*\-]\s+', '', text)

    # Rule 4: **bold** → plain, then *italic* → plain
    # Bold first (double-star) before italic (single-star) to avoid partial matches.
    text = re.sub(r'\*\*([^*\n]+)\*\*', r'\1', text)
    # Italic: opening * must be followed by a non-space, non-asterisk char.
    text = re.sub(r'\*([^\s*][^*\n]*)\*', r'\1', text)

    # Rule 5: Collapse whitespace / blank lines → single space
    text = re.sub(r'\s+', ' ', text)

    # Rule 6: Strip leading/trailing whitespace
    return text.strip()


def parse_script(path: str, speakers: set[str] | None = None) -> list[DialogueLine]:
    """Parse a markdown dialogue file into an ordered list of DialogueLine objects.

    Speaker turns are identified by ``**SPEAKER:**`` at the start of a line.
    When *speakers* is provided, only those exact names are recognized as
    speaker tags — bold labels like ``**In summary:**`` are ignored.
    Content before the first speaker tag (title, preamble) is skipped.
    Empty blocks (e.g. stray separators with no speech) are also skipped.
    """
    with open(path, 'r', encoding='utf-8') as f:
        content = f.read()

    # Build a pattern that only matches known speaker names (if provided),
    # or any single-line non-colon sequence (fallback).
    if speakers:
        speaker_alt = '|'.join(re.escape(s) for s in speakers)
        pattern = re.compile(rf'(?m)^\*\*({speaker_alt}):\*\*\s*')
    else:
        pattern = re.compile(r'(?m)^\*\*([^:\n]+):\*\*\s*')

    matches = list(pattern.finditer(content))
    lines = []
    for i, match in enumerate(matches):
        speaker = match.group(1).strip()
        start = match.end()
        end = matches[i + 1].start() if i + 1 < len(matches) else len(content)
        body = content[start:end]
        text = strip_markdown(body).strip()
        if text:
            lines.append(DialogueLine(speaker=speaker, text=text))

    return lines
