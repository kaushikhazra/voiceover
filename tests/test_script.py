"""Tests for voiceover.script — strip_markdown and parse_script."""

import textwrap
from pathlib import Path

import pytest

from voiceover.script import strip_markdown, parse_script, DialogueLine


# ---------------------------------------------------------------------------
# strip_markdown tests
# ---------------------------------------------------------------------------

def test_rule1_removes_horizontal_rules():
    text = "Before.\n---\nAfter."
    result = strip_markdown(text)
    assert "---" not in result
    assert "Before" in result
    assert "After" in result


def test_rule2_hash3_header_with_number():
    text = "### 1. The Liquid as Medium\nSome body text."
    result = strip_markdown(text)
    assert "###" not in result
    assert "1." not in result
    assert "The Liquid as Medium" in result


def test_rule2_hash4_header_no_number():
    text = "#### Forgetting (The Epistemological Death)\nSome text."
    result = strip_markdown(text)
    assert "####" not in result
    assert "Forgetting (The Epistemological Death)" in result


def test_rule2_hash1_simple_header():
    text = "# My Title\nSome content."
    result = strip_markdown(text)
    assert "#" not in result
    assert "My Title" in result


def test_rule3_bold_stripped():
    text = "This is **bold text** here."
    result = strip_markdown(text)
    assert "**" not in result
    assert "bold text" in result


def test_rule3_italic_stripped():
    text = "This is *italic text* here."
    result = strip_markdown(text)
    assert result.count("*") == 0
    assert "italic text" in result


def test_rule3_bold_before_italic_ordering():
    # **bold** must be processed before *italic* so that **text** is not
    # partially matched as *(*text*)* leaving stray asterisks.
    text = "**bold** and *italic*"
    result = strip_markdown(text)
    assert "*" not in result
    assert "bold" in result
    assert "italic" in result


def test_rule4_bullet_asterisk_stripped():
    text = "* First item\n* Second item"
    result = strip_markdown(text)
    # Bullets stripped; content preserved
    assert "First item" in result
    assert "Second item" in result


def test_rule4_bullet_dash_stripped():
    text = "- First item\n- Second item"
    result = strip_markdown(text)
    assert "First item" in result
    assert "Second item" in result


def test_rule5_whitespace_collapsed_to_single_space():
    text = "Line one.\n\nLine two.\n\nLine three."
    result = strip_markdown(text)
    assert "\n" not in result
    assert "  " not in result   # no double spaces
    assert "Line one" in result
    assert "Line three" in result


def test_rule6_stripped():
    text = "  Hello world.  "
    result = strip_markdown(text)
    assert result == "Hello world."


class TestC1BulletPlusItalic:
    """C1 — Bullet lines containing bold/italic must not corrupt text.

    The bullet prefix ``*`` must be stripped before italic processing,
    otherwise lines like ``*   **Selection** implies... *after*`` have
    their leading ``*`` misread as an italic delimiter.
    """

    def test_bullet_bold_then_italic(self):
        text = "*   **Selection** implies choosing. It is a decision made *after* the field is set."
        result = strip_markdown(text)
        assert "*" not in result
        assert "Selection implies choosing" in result
        assert "after" in result
        assert "the field is set" in result

    def test_bullet_italic_label(self):
        text = "*   *Focus:* Memory, perception, access, history."
        result = strip_markdown(text)
        assert "*" not in result
        assert "Focus:" in result
        assert "Memory, perception, access, history." in result

    def test_bullet_italic_state(self):
        text = "*   *State:* A deficit of knowledge."
        result = strip_markdown(text)
        assert "*" not in result
        assert "State:" in result
        assert "A deficit of knowledge." in result

    def test_multi_bullet_italic_block(self):
        """Multiple bullet lines with italic in a single block."""
        text = (
            "*   *Focus:* Memory, perception, access, history.\n"
            "*   *State:* A deficit of knowledge.\n"
            "*   **Selection** implies choosing. Made *after* the field is set.\n"
        )
        result = strip_markdown(text)
        assert "*" not in result
        assert "Focus:" in result
        assert "State:" in result
        assert "Selection" in result
        assert "after" in result


class TestC2MultiLevelHeaders:
    """C2 — Headers with any number of ``#`` marks must be stripped."""

    def test_h4_header(self):
        text = "#### Forgetting (The Epistemological Death)\nSome text."
        result = strip_markdown(text)
        assert "#" not in result
        assert "Forgetting (The Epistemological Death)" in result

    def test_h5_header(self):
        text = "##### Deep Sub-section\nContent."
        result = strip_markdown(text)
        assert "#" not in result
        assert "Deep Sub-section" in result

    def test_h6_header(self):
        text = "###### Deepest Level\nContent."
        result = strip_markdown(text)
        assert "#" not in result
        assert "Deepest Level" in result

    def test_h4_with_number_prefix(self):
        text = "#### 3. Sub-header With Number\nContent."
        result = strip_markdown(text)
        assert "#" not in result
        assert "3." not in result
        assert "Sub-header With Number" in result


def test_combined_rules_real_block():
    """Simulate a real G-speaker block from the dialogue."""
    block = textwrap.dedent("""\
        Let's explore the tensions.

        ### 1. The Liquid as the Medium of Potential

        If the liquid is the substrate of reality.

        *   **Physics as the Current:** Physics describes the laws.
        *   **Will as the Force:** Will is the direction.

        ---

        The tension exists at the point.
    """)
    result = strip_markdown(block)

    assert "###" not in result
    assert "**" not in result
    assert "---" not in result
    assert "The Liquid as the Medium of Potential" in result
    assert "Physics as the Current:" in result
    assert "Will as the Force:" in result
    assert "\n" not in result


# ---------------------------------------------------------------------------
# parse_script tests
# ---------------------------------------------------------------------------

FIXTURE_DIALOGUE = textwrap.dedent("""\
    # Test Dialogue

    *Two speakers thinking together.*

    ---

    **A:** Hello there. This is the first turn.

    **B:** This is the second turn with **bold** text.

    **A:** Back to A for the third turn.
    And it continues on a second line.

    **B:** Final turn from B.
""")


@pytest.fixture
def fixture_script(tmp_path) -> Path:
    p = tmp_path / "dialogue.md"
    p.write_text(FIXTURE_DIALOGUE, encoding="utf-8")
    return p


def test_parse_script_returns_correct_count(fixture_script):
    lines = parse_script(str(fixture_script))
    assert len(lines) == 4


def test_parse_script_speaker_order(fixture_script):
    lines = parse_script(str(fixture_script))
    assert lines[0].speaker == "A"
    assert lines[1].speaker == "B"
    assert lines[2].speaker == "A"
    assert lines[3].speaker == "B"


def test_parse_script_skips_preamble(fixture_script):
    lines = parse_script(str(fixture_script))
    # Preamble title and italic should not appear in any DialogueLine
    for line in lines:
        assert "Test Dialogue" not in line.text
        assert "Two speakers" not in line.text


def test_parse_script_text_cleaned(fixture_script):
    lines = parse_script(str(fixture_script))
    # Bold in B's first turn should be stripped
    assert "**" not in lines[1].text
    assert "bold" in lines[1].text


def test_parse_script_multiline_turn(fixture_script):
    lines = parse_script(str(fixture_script))
    # A's second turn spans two lines — should be a single flat string
    assert "\n" not in lines[2].text
    assert "third turn" in lines[2].text
    assert "second line" in lines[2].text


def test_parse_script_all_dialogueline_instances(fixture_script):
    lines = parse_script(str(fixture_script))
    for line in lines:
        assert isinstance(line, DialogueLine)
        assert line.speaker
        assert line.text


def test_parse_script_empty_blocks_skipped(tmp_path):
    """Blocks that are only --- or whitespace should be skipped."""
    content = textwrap.dedent("""\
        **A:** Hello.

        **B:**
        ---

        **A:** World.
    """)
    p = tmp_path / "d.md"
    p.write_text(content, encoding="utf-8")
    lines = parse_script(str(p))
    # B's block is just a --- which strip_markdown removes → empty → skip
    speakers = [l.speaker for l in lines]
    assert "B" not in speakers
    assert speakers == ["A", "A"]
