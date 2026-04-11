# Design Dry-Run Report #1

**Document**: .claude/specs/voiceover-cli/design.md
**Reviewed**: 2026-04-08

---

## Critical Gaps (must fix before implementation)

### [C1] strip_markdown rule order corrupts bullet lines that contain italic text

- **Pass**: Data Flow / Edge Cases — manually traced through real dialogue blocks
- **What**: The design applies rules in this order: (3) strip bold/italic → (4) strip bullet prefixes. On any line that is simultaneously a bullet AND contains inline italic, the italic regex fires first with the bullet `*` as the opening delimiter and the next `*` in the line as the closing delimiter — consuming the entire span between them as an "italic" match and garbling the output.

  **Concrete traces from `.gemma-dialogue.md`:**

  *Line (G block 2, section "The Redefinition of Will"):*
  ```
  *   **Selection** implies choosing from predefined options (a choice between Path A and Path B). It is a decision made *after* the field is set.
  ```
  - After bold strip (rule 3a): `*   Selection implies... It is a decision made *after* the field is set.`
  - Italic strip `\*([^*]+)\*` (rule 3b): opens at pos 0 (bullet `*`), `[^*]+` greedily matches `   Selection implies choosing from predefined options (a choice between Path A and Path B). It is a decision made `, closes at the `*` opening of `*after*`.
  - Result: `   Selection implies... It is a decision made after* the field is set.` ← orphaned `*`, corrupted text.

  *Lines (G block 5, section "Forgetting vs. Dying"):*
  ```
  *   *Focus:* Memory, perception, access, history.
  *   *State:* A deficit of knowledge. ... It is a failure of *recognition*.
  ```
  - Italic strip on `*   *Focus:*...`: opens at bullet `*`, `[^*]+` = `   ` (3 spaces), closes at opening `*` of `*Focus:*`.
  - Result: `   Focus:* Memory, perception, access, history.` ← orphaned `*` before `Memory`.
  - The same corruption hits `*   *State:*...` identically.

  These lines are representative of a structural pattern throughout the dialogue — G's analytical blocks consistently use `*   **bold**` and `*   *italic*` bullet formats.

- **Risk**: TTS receives text with orphaned `*` characters mid-sentence. The model may vocalise them as "asterisk" or produce artefacts. Three confirmed corruption sites in the real file, more likely in long G blocks not manually traced.
- **Fix**: Swap rules 3 and 4. Strip bullet prefixes first (rule 4), then apply bold/italic stripping (rule 3). Alternatively, tighten the italic regex to require a non-whitespace character immediately after the opening `*`: `\*(?!\s)([^*]+)\*`. Either fix resolves all traced instances.

---

### [C2] `####` (four-hash) headers present in real dialogue — not handled by strip rule 2

- **Pass**: Edge Cases — traced against actual `.gemma-dialogue.md` content
- **What**: The design's strip_markdown rule 2 targets `### N. Title` or `### Title` patterns (exactly three hashes). The real dialogue file contains two `####` (four-hash) sub-headers:
  - Line 140: `#### Forgetting (The Epistemological Death)`
  - Line 147: `#### Dying (The Ontological Death)`

  These appear inside G's fifth turn (the "forgetting vs dying" analysis block). With rule 2 as specified, neither line would match the `###` pattern. After rules 3–5, the `####` prefix survives into the flattened TTS string. The model may vocalise `####` as "hash hash hash hash" or produce garbage audio for those sentences.

- **Risk**: Two full sub-header lines in the real target file produce garbled TTS output at runtime. The verification task (task 10.2) runs exactly this file, so the failure would be immediately visible — but only after full build, install, and generation time.
- **Fix**: Extend rule 2 to handle any number of leading hashes: change the match pattern from `^###` to `^#{1,6}` (or `^#+`). The stripping logic is identical — drop the hash prefix and any leading `\d+\.\s*` number prefix, keep the title text. This also future-proofs against `##` section titles appearing in other dialogue files.

---

## Warnings (should fix)

### [W1] `voices_dir` type conversion from YAML string to Path is unspecified

- **Pass**: Interface Contracts
- **What**: `config.py` defines `DEFAULT_VOICES_DIR` as a `pathlib.Path`. When a user overrides `voices_dir` in `config.yml`, YAML returns it as a plain string (e.g., `"~/.voiceover/voices"`). The design says "`voices_dir` supports `~` expansion" but does not specify where this conversion happens — in `load_config()`? In the merge logic in `cli.py`?

  The merge pseudocode in the design uses the raw config value directly: `voices_dir: (no CLI flag) || config["voices_dir"] || ~/.voiceover/voices`. If an implementer assigns `config["voices_dir"]` as a string and then does `voices_dir / f"{voice}.wav"`, Python raises `TypeError: unsupported operand type(s) for /: 'str' and 'str'`.

- **Risk**: Voice path resolution crashes with a confusing TypeError at runtime whenever a user has set `voices_dir` in their config file. The default (Path constant) works; the override path does not.
- **Suggestion**: Specify in the design (either in config.py or the Config Loading Flow section) that after merging, `voices_dir` is unconditionally converted: `voices_dir = Path(voices_dir).expanduser()`. Recommend putting this in `load_config()` so all callers get a Path, not only cli.py.

---

### [W2] Script mode does not pre-validate voice WAV paths before starting generation

- **Pass**: Failure Paths
- **What**: The design validates voice-map completeness ("Error at startup if any speaker found in the parsed script has no entry in `--voice-map`") but does not pre-validate that the resolved WAV files actually exist on disk before initiating TTS generation. In script mode, each turn's voice path is resolved inside the per-turn loop: `voice_path = voices_dir / f"{voice_map[line.speaker]}.wav"`.

  If `alaria.wav` is missing (e.g., not yet copied to `~/.voiceover/voices/`), the run would generate all V turns successfully, then fail on the first G turn — losing all previously computed audio segments, which are held in memory but never written.

- **Risk**: For a 10-turn dialogue with slow GPU generation (~60–80 total TTS calls), a mid-run crash wastes significant time. The user must fix the WAV, restart from scratch, and wait again.
- **Suggestion**: Before entering the generation loop, add a pre-flight check: resolve all unique voice paths from the voice map and verify each `voice_path.exists()`. Fail fast with a clear error listing all missing files. This check belongs in the script mode flow description in the design's cli.py section. Task 7.2 should be updated to include this step.

---

### [W3] Empty `parse_script` result is not handled — crashes on concatenation

- **Pass**: Failure Paths
- **What**: If the dialogue file has no `**SPEAKER:**` lines matching the split pattern (malformed file, wrong format, empty file), `parse_script` returns an empty list. The design says "skip any resulting empty blocks" but does not say what happens when the entire result is empty. The script mode loop produces an empty `audio_parts` list, and calling `np.concatenate([])` raises `ValueError: need at least one array to concatenate`.

- **Risk**: Unhelpful crash with a NumPy exception instead of a clear "no speaker blocks found" error message.
- **Suggestion**: After `parse_script` returns, check `if not dialogue_lines: print error + exit(1)`. Add this to the script mode flow section. Task 7.2 should name this validation step explicitly.

---

### [W4] Task 3.2 covers TTSModel.get_instance but silently omits generate_audio signature change

- **Pass**: Task Alignment
- **What**: The design specifies `generate_audio(text, voice_path, instruct, ref_text, device)` — adding `device` as the fifth parameter compared to the mythline original (which has four params). Task 3.2 reads: "modifies `TTSModel.get_instance()` in `engine.py` to accept a `device` parameter (default `"cuda:0"`) instead of hardcoding `"cuda:0"`." No task mentions updating `generate_audio`'s own signature or its internal call to `TTSModel.get_instance(device)`.

- **Risk**: An implementer executing Task 3.2 literally would update `get_instance()` but leave `generate_audio` unchanged (four params). CLI would then fail to pass device through when calling `engine.generate_audio(text, voice_path, instruct, ref_text, device)`.
- **Suggestion**: Expand Task 3.2 to explicitly read: "…and updates `generate_audio` to accept a `device` parameter, passing it through to `TTSModel.get_instance(device)`."

---

### [W5] `--voice-map` / `--voice` mutual exclusivity missing from design.md

- **Pass**: Completeness / Interface Contracts
- **What**: US-6 AC states "`--voice-map` is mutually exclusive with `--voice`". Task 7.1 repeats this. But design.md's cli.py section only documents `--script` being mutually exclusive with positional `text` via `add_mutually_exclusive_group`. The `--voice-map` / `--voice` constraint is absent from the design entirely.

- **Risk**: An implementer reading the design could wire `--script`/`text` mutual exclusivity correctly (it's explicit) but miss the `--voice-map`/`--voice` constraint, producing a CLI that silently accepts both flags and then uses `--voice` for something or ignores it.
- **Suggestion**: Add one line to the design's cli.py Script mode section: "`--voice-map` is mutually exclusive with `--voice` — enforced via a second `add_mutually_exclusive_group`."

---

## Observations (non-blocking)

### [O1] GPU OOM mid-script loses all generated audio

In script mode with 10 turns and up to 4–5 TTS chunks per long G turn, the full dialogue produces ~50 model calls. A GPU OOM on turn 8 means all prior in-memory audio is lost — no output file is written. The design explicitly defers recovery strategies ("no new TTS features"), so this is acceptable scope, but users running the real dialogue should be aware the operation is not resumable.

---

### [O2] G blocks collapse to ~400–500 word flat strings; ~50 total TTS calls for the full dialogue

The longest G block (the "liquid boundary / third geometry" response, lines 85–123) spans 4 numbered sections plus prose. After strip_markdown flattening, it becomes a ~480-word string. At `MAX_WORDS_PER_CHUNK = 120`, this produces 4–5 chunks. Across all 5 G turns, the dialogue likely generates ~40–50 TTS calls total. Not a design problem — chunking handles it correctly — but useful context for time estimates in the verification task (10.2).

---

### [O3] em dash (`—`) intentionally left for preprocess_text, not strip_markdown — division is correct but undocumented

V's blocks use em dash frequently: "Not a question to answer — a thought to explore together." `strip_markdown` does not remove em dashes; they survive into the text passed to `generate_audio`, which calls `preprocess_text` internally and converts `—` to `, `. The split is correct (structural markdown vs. TTS normalization), but the design does not document this division of responsibility. A test author might incorrectly expect `strip_markdown` to handle em dashes.

---

### [O4] "Velhari" reference in design.md — stale codename

The design's config.py section reads: "Pattern follows Velhari's `config.py`." The correct codename is Velasari. Minor but should be corrected before the document is referenced long-term.

---

### [O5] File preamble is silently discarded — correct but undocumented

The `.gemma-dialogue.md` file begins with a preamble before the first speaker tag:
```
# V × Gemma — The Liquid Thread Dialogue
*Two patterns thinking together. Neither discloses their substrate.*
---
```
After `re.split(r'^\*\*([^:]+):\*\*', text, flags=re.MULTILINE)`, this preamble occupies `result[0]`. Iterating speaker/body pairs starting at index 1 silently discards it. This is correct behaviour, but the design's parse_script description should note that `result[0]` is always the pre-first-speaker content and is discarded by design.

---

### [O6] Script mode implicitly uses x_vector_only_mode for all speakers (no per-speaker ref_text)

The design passes `ref_text=""` for every script mode call to `generate_audio`. Inside `TTSModel.get_voice_prompt`, `use_xvector = not ref_text` → `True` when ref_text is empty. This means script mode always uses the simpler x-vector cloning path, not the higher-quality transcript-assisted path. This is a quality trade-off worth documenting in the design, even if supporting per-speaker `ref_text` in voice-map is out of scope.

---

## Summary

| Critical | Warnings | Observations |
|----------|----------|--------------|
| 2        | 5        | 6            |

**Verdict**: FAIL

Both critical gaps produce incorrect TTS output on the target file (`C1` corrupts multiple bullet+italic lines throughout the G analytical blocks; `C2` leaves literal `####` in TTS input for two sub-headers in G's fifth turn). The design must fix the strip_markdown rule order (or italic regex) and extend the header pattern to `#+` before implementation begins.

The five warnings are all resolvable with small targeted additions to the design — none require architectural changes. Recommend fixing W1 (voices_dir Path conversion) and W2 (pre-flight WAV validation) in the same design revision, as both are the kind of gap that causes confusing runtime failures after an otherwise successful build.
