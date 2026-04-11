"""Tests for cli._parse_kv_map — K=v,K2=v2 parsing and validation."""

import pytest

from voiceover.cli import _parse_kv_map


# --- Happy path ---

def test_single_pair():
    assert _parse_kv_map("V=lunastis") == {"V": "lunastis"}


def test_multiple_pairs():
    result = _parse_kv_map("V=lunastis,G=alaria")
    assert result == {"V": "lunastis", "G": "alaria"}


def test_whitespace_around_keys_and_values_stripped():
    result = _parse_kv_map(" V = lunastis , G = alaria ")
    assert result == {"V": "lunastis", "G": "alaria"}


def test_value_with_spaces():
    """Values may contain internal spaces (e.g., voice description)."""
    result = _parse_kv_map("V=my voice name")
    assert result == {"V": "my voice name"}


def test_three_pairs():
    result = _parse_kv_map("A=one,B=two,C=three")
    assert result == {"A": "one", "B": "two", "C": "three"}


# --- Edge cases (lenient) ---

def test_empty_string_returns_empty_dict():
    """Empty input has no valid pairs — returns empty dict."""
    assert _parse_kv_map("") == {}


def test_whitespace_only_returns_empty_dict():
    assert _parse_kv_map("   ") == {}


def test_trailing_comma_ignored():
    """Trailing comma produces an empty token that is silently skipped."""
    assert _parse_kv_map("K=v,") == {"K": "v"}


def test_double_comma_ignored():
    """Double comma is silently skipped."""
    assert _parse_kv_map("A=one,,B=two") == {"A": "one", "B": "two"}


# --- Malformed input (strict) ---

def test_no_equals_sign_raises():
    with pytest.raises(ValueError, match="KEY=VALUE"):
        _parse_kv_map("bad")


def test_empty_value_raises():
    with pytest.raises(ValueError, match="empty"):
        _parse_kv_map("K=")


def test_empty_key_raises():
    with pytest.raises(ValueError, match="empty"):
        _parse_kv_map("=value")
