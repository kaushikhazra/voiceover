"""Tests for engine.preprocess_text — normalization rules."""

# Heavy-dep stubs (qwen_tts, torch, soundfile) are in conftest.py.

from voiceover.engine import preprocess_text


def test_em_dash_replaced_with_comma():
    result = preprocess_text("Hello\u2014world")
    assert result == "Hello, world"


def test_curly_single_quotes_normalized():
    result = preprocess_text("\u2018hello\u2019")
    assert result == "'hello'"


def test_curly_double_quotes_normalized():
    result = preprocess_text("\u201chello\u201d")
    assert result == '"hello"'


def test_asterisks_removed():
    result = preprocess_text("**bold** and *italic*")
    assert "*" not in result
    assert "bold" in result
    assert "italic" in result


def test_semicolon_before_capital_becomes_comma():
    result = preprocess_text("Hello; World")
    assert result == "Hello, World"


def test_semicolon_before_lowercase_unchanged():
    result = preprocess_text("a; b")
    assert result == "a; b"


def test_empty_string_returns_empty():
    assert preprocess_text("") == ""


def test_ellipsis_normalized():
    result = preprocess_text("Wait\u2026")
    assert result == "Wait..."


def test_strip_leading_trailing_whitespace():
    result = preprocess_text("  hello  ")
    assert result == "hello"
