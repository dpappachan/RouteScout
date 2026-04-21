"""Parser tolerant-lookup tests. Doesn't hit the LLM — just exercises the
trailhead name resolver that cleans up common LLM output quirks."""
import pytest

from backend.llm.parser import _resolve_trailhead_name


VALID = {
    "Happy Isles",
    "Glacier Point",
    "Lembert Dome / Dog Lake trailhead",
    "Tuolumne Meadows Ranger Station",
    "Agnew Meadows trailhead",
    "White Wolf trailhead",
    "Rush Creek trailhead (Silver Lake)",
}


def test_exact_match():
    assert _resolve_trailhead_name("Happy Isles", VALID) == "Happy Isles"


def test_case_insensitive():
    assert _resolve_trailhead_name("happy isles", VALID) == "Happy Isles"
    assert _resolve_trailhead_name("GLACIER POINT", VALID) == "Glacier Point"


def test_strips_parenthetical():
    # LLM sometimes appends a region description in parens
    assert _resolve_trailhead_name(
        "Happy Isles (Yosemite Valley)", VALID
    ) == "Happy Isles"


def test_adds_trailhead_suffix():
    # LLM drops the ' trailhead' suffix
    assert _resolve_trailhead_name("Agnew Meadows", VALID) == "Agnew Meadows trailhead"
    assert _resolve_trailhead_name("White Wolf", VALID) == "White Wolf trailhead"


def test_removes_trailhead_suffix():
    # Reverse direction: LLM adds " trailhead" where it shouldn't
    assert _resolve_trailhead_name("Happy Isles trailhead", VALID) == "Happy Isles"


def test_splits_on_or_disjunction():
    # Classic LLM failure mode — returns "X or Y"
    assert _resolve_trailhead_name(
        "Agnew Meadows or Rush Creek trailhead (Silver Lake)", VALID
    ) in VALID


def test_strips_quotes():
    assert _resolve_trailhead_name('"Happy Isles"', VALID) == "Happy Isles"
    assert _resolve_trailhead_name("'Glacier Point'", VALID) == "Glacier Point"


def test_unknown_raises():
    with pytest.raises(ValueError):
        _resolve_trailhead_name("Nonexistent Trailhead", VALID)
