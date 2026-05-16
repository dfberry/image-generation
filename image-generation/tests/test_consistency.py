"""test_consistency.py — Unit tests for Phase 2 Visual Consistency Controls.

All tests are pure Python (no subprocess, no generate.py invocation).
Fast, CI-appropriate, run on every push.

Covers PRD §11 Tier 1 test specifications T1.1–T1.15.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from consistency import (
    CLIPBudgetError,
    assemble_image_prompt,
    check_clip_budget,
    count_enforcement_tokens,
    load_and_validate,
    load_registry,
    resolve_profile,
    validate_registry,
)
from presets import estimate_tokens

# ---------------------------------------------------------------------------
# Shared test fixtures / helpers
# ---------------------------------------------------------------------------

_IMAGE_GEN_DIR = Path(__file__).parent.parent

_SCENES_PATH = _IMAGE_GEN_DIR / "scenes.json"
_CHARACTERS_PATH = _IMAGE_GEN_DIR / "characters.json"
_EXPRESSIONS_PATH = _IMAGE_GEN_DIR / "expressions.json"
_PROFILES_PATH = _IMAGE_GEN_DIR / "profiles.json"

_SCENES_SCHEMA = _IMAGE_GEN_DIR / "schemas" / "scenes.schema.json"
_CHARACTERS_SCHEMA = _IMAGE_GEN_DIR / "schemas" / "characters.schema.json"
_EXPRESSIONS_SCHEMA = _IMAGE_GEN_DIR / "schemas" / "expressions.schema.json"
_PROFILES_SCHEMA = _IMAGE_GEN_DIR / "schemas" / "profiles.schema.json"


@pytest.fixture(scope="module")
def scenes():
    return load_registry(_SCENES_PATH)


@pytest.fixture(scope="module")
def characters():
    return load_registry(_CHARACTERS_PATH)


@pytest.fixture(scope="module")
def expressions():
    return load_registry(_EXPRESSIONS_PATH)


@pytest.fixture(scope="module")
def profiles():
    return load_registry(_PROFILES_PATH)


def _woodshop_profile(profiles):
    return resolve_profile("woodshop-blog", profiles)


# ---------------------------------------------------------------------------
# T1.1 — Profile assembly: correct assembled prompt structure
# ---------------------------------------------------------------------------


def test_profile_assembly_woodshop_blog(scenes, characters, expressions, profiles):
    """Assembled prompt for woodshop-blog follows CLIP-priority token order."""
    profile = _woodshop_profile(profiles)
    image_entry = {
        "prompt_core": "Two men at a workbench",
        "characters": [
            {"name": "protagonist", "position": "left", "action": "holding a mallet"},
            {"name": "ai-agent", "position": "right", "action": "steadying the joint"},
        ],
        "expression": "focused",
    }
    result = assemble_image_prompt(
        image_entry, profile, scenes, characters, expressions, allow_over_budget=True
    )
    prompt = result["prompt"]

    # Style tokens at start
    assert prompt.startswith("Watercolor illustration") or "Watercolor illustration" in prompt[:50]

    # prompt_core after style tokens
    watercolor_pos = prompt.index("Watercolor illustration")
    core_pos = prompt.index("Two men at a workbench")
    assert core_pos > watercolor_pos

    # Protagonist (blue) before ai-agent (green)
    blue_pos = prompt.index("bright cobalt blue")
    green_pos = prompt.index("vivid emerald green")
    assert blue_pos < green_pos, "Protagonist (left) should appear before ai-agent (right)"

    # Expression tokens present
    assert "concentrated expression" in prompt

    # Scene tokens present
    assert "brick walls" in prompt

    # Ends with "no text"
    assert prompt.endswith("no text")


# ---------------------------------------------------------------------------
# T1.2 — Character token injection and negative prompt assembly
# ---------------------------------------------------------------------------


def test_character_token_injection_and_negatives(scenes, characters, expressions, profiles):
    """Character tokens appear in prompt; negatives from all characters merged."""
    profile = _woodshop_profile(profiles)
    image_entry = {
        "prompt_core": "Two professionals at a workbench",
        "characters": [
            {"name": "protagonist", "position": "left"},
            {"name": "ai-agent", "position": "right"},
        ],
    }
    result = assemble_image_prompt(
        image_entry, profile, scenes, characters, expressions, allow_over_budget=True
    )

    assert "bright cobalt blue long-sleeve shirt" in result["prompt"]
    assert "vivid emerald green long-sleeve shirt" in result["prompt"]

    # Protagonist negatives: "green shirt, emerald shirt"
    assert "green shirt" in result["negative_prompt"]
    assert "emerald shirt" in result["negative_prompt"]

    # ai-agent negatives: "cobalt blue shirt, blue shirt"
    assert "cobalt blue shirt" in result["negative_prompt"]
    assert "blue shirt" in result["negative_prompt"]


# ---------------------------------------------------------------------------
# T1.3 — Character count enforcement negatives
# ---------------------------------------------------------------------------


def test_count_enforcement_4_characters():
    """4 characters → negative contains three/five/six people, NOT four people."""
    result = count_enforcement_tokens(4)
    assert "three people" in result
    assert "five people" in result
    assert "six people" in result
    assert "four people" not in result


def test_count_enforcement_2_characters():
    """2 characters → negative contains one/three/four people, NOT two people."""
    result = count_enforcement_tokens(2)
    assert "one person" in result
    assert "three people" in result
    assert "four people" in result
    assert "two people" not in result


def test_count_enforcement_1_character():
    """1 character → negative contains two/three/four people, NOT one person."""
    result = count_enforcement_tokens(1)
    assert "two people" in result
    assert "three people" in result
    assert "four people" in result
    assert "one person" not in result


def test_count_enforcement_3_characters():
    """3 characters → negative contains two/four/five people, NOT three people."""
    result = count_enforcement_tokens(3)
    assert "two people" in result
    assert "four people" in result
    assert "five people" in result
    assert "three people" not in result


# ---------------------------------------------------------------------------
# T1.4 — Seed mode: sequential
# ---------------------------------------------------------------------------


def test_seed_mode_sequential(scenes, characters, expressions):
    """Sequential seeds: image[i].seed == seed_base + i."""
    profile = {
        "description": "Test",
        "seed_base": 1000,
        "seed_strategy": "sequential",
    }
    results = [
        assemble_image_prompt(
            {"prompt_core": f"Image {i}"},
            profile,
            scenes,
            characters,
            expressions,
            image_index=i,
        )
        for i in range(3)
    ]
    assert results[0]["seed"] == 1000
    assert results[1]["seed"] == 1001
    assert results[2]["seed"] == 1002


# ---------------------------------------------------------------------------
# T1.5 — Seed mode: fixed
# ---------------------------------------------------------------------------


def test_seed_mode_fixed(scenes, characters, expressions):
    """Fixed seed: all images get seed_base regardless of index."""
    profile = {
        "description": "Test",
        "seed_base": 42,
        "seed_strategy": "fixed",
    }
    results = [
        assemble_image_prompt(
            {"prompt_core": f"Image {i}"},
            profile,
            scenes,
            characters,
            expressions,
            image_index=i,
        )
        for i in range(3)
    ]
    assert all(r["seed"] == 42 for r in results)


# ---------------------------------------------------------------------------
# T1.6 — Profile inheritance
# ---------------------------------------------------------------------------


def test_profile_inheritance_woodshop_hero(profiles):
    """Child overrides size; parent fields (style, scene, negative_base) preserved."""
    resolved = resolve_profile("woodshop-blog-hero", profiles)
    assert resolved["size"] == "blog-hero"  # from child
    assert resolved["style"] == "watercolor"  # from parent
    assert resolved["scene"] == "woodshop"  # from parent
    assert resolved.get("negative_base"), "negative_base should be inherited from parent"
    assert "extends" not in resolved, "resolved profile should not expose 'extends'"


def test_profile_inheritance_no_deep_chains():
    """Depth > 1 raises ValueError mentioning the limit."""
    profiles_data = {
        "root": {"description": "Root"},
        "child": {"description": "Child", "extends": "root"},
        "grandchild": {"description": "Grandchild", "extends": "child"},
    }
    with pytest.raises(ValueError, match="depth > 1"):
        resolve_profile("grandchild", profiles_data)


# ---------------------------------------------------------------------------
# T1.7 — CLIP token budget
# ---------------------------------------------------------------------------


def _make_prompt_of_n_tokens(n: int) -> str:
    """Produce a string whose estimate_tokens() == n (approximately)."""
    # Each word = ~1 token; use short unique words
    words = [f"word{i}" for i in range(n)]
    return " ".join(words)


def test_clip_budget_warning_at_71_tokens(capsys):
    """71-token prompt → warning printed, no exception."""
    prompt = _make_prompt_of_n_tokens(71)
    assert estimate_tokens(prompt) == 71
    check_clip_budget(prompt)  # should not raise
    captured = capsys.readouterr()
    assert "Approaching CLIP limit" in captured.err


def test_clip_budget_no_warning_at_70_tokens(capsys):
    """70-token prompt → no warning, no exception."""
    prompt = _make_prompt_of_n_tokens(70)
    assert estimate_tokens(prompt) == 70
    check_clip_budget(prompt)
    captured = capsys.readouterr()
    assert "Approaching CLIP limit" not in captured.err


def test_clip_budget_error_at_78_tokens():
    """78-token prompt → raises CLIPBudgetError with count in message."""
    prompt = _make_prompt_of_n_tokens(78)
    assert estimate_tokens(prompt) == 78
    with pytest.raises(CLIPBudgetError, match="78"):
        check_clip_budget(prompt)


def test_clip_budget_override_flag(capsys):
    """78-token prompt + allow_over_budget=True → warning only, no exception."""
    prompt = _make_prompt_of_n_tokens(78)
    check_clip_budget(prompt, allow_over_budget=True)  # should not raise
    captured = capsys.readouterr()
    assert "CLIP token limit exceeded" in captured.err or "78" in captured.err


# ---------------------------------------------------------------------------
# T1.8 — Expression resolution
# ---------------------------------------------------------------------------


def test_expression_resolution_focused(expressions):
    """'focused' resolves to the correct SDXL token string."""
    tokens = expressions["focused"]["tokens"]
    assert tokens == "concentrated expression, intent gaze, engaged posture"


def test_expression_resolution_unknown_term(scenes, characters, expressions):
    """Unknown expression raises ValueError referencing the term."""
    profile = {"description": "Test"}
    image_entry = {"prompt_core": "A person working", "expression": "ecstatic"}
    with pytest.raises(ValueError, match="ecstatic"):
        assemble_image_prompt(image_entry, profile, scenes, characters, expressions)


# ---------------------------------------------------------------------------
# T1.9 — Schema validation: all registry files valid against their schemas
# ---------------------------------------------------------------------------


def test_scenes_json_valid_against_schema():
    """scenes.json validates against scenes.schema.json with no errors."""
    load_and_validate(_SCENES_PATH, _SCENES_SCHEMA)  # raises on failure


def test_characters_json_valid_against_schema():
    """characters.json validates against characters.schema.json with no errors."""
    load_and_validate(_CHARACTERS_PATH, _CHARACTERS_SCHEMA)


def test_expressions_json_valid_against_schema():
    """expressions.json validates against expressions.schema.json with no errors."""
    load_and_validate(_EXPRESSIONS_PATH, _EXPRESSIONS_SCHEMA)


def test_profiles_json_valid_against_schema():
    """profiles.json validates against profiles.schema.json with no errors."""
    load_and_validate(_PROFILES_PATH, _PROFILES_SCHEMA)


# ---------------------------------------------------------------------------
# T1.10 — Negative prompt merge + no-profile fallback
# ---------------------------------------------------------------------------


def test_negative_prompt_merge_explicit_wins(scenes, characters, expressions):
    """Explicit image-level negative_prompt is appended to assembled negatives."""
    profile = {
        "description": "Test",
        "negative_base": "blurry, bad quality",
    }
    image_entry = {
        "prompt_core": "A scene",
        "characters": [{"name": "protagonist"}],
        "negative_prompt": "no robots, no machinery",
    }
    result = assemble_image_prompt(image_entry, profile, scenes, characters, expressions)
    neg = result["negative_prompt"]

    # Both assembled tokens AND explicit tokens present
    assert "blurry" in neg
    assert "no robots" in neg
    assert "no machinery" in neg


def test_no_profile_fallback(scenes, characters, expressions):
    """No scene/character in profile → prompt == prompt_core (no consistency injection)."""
    profile = {"description": "Minimal"}  # no scene, no style, no characters
    image_entry = {"prompt_core": "A person sitting alone"}
    result = assemble_image_prompt(image_entry, profile, scenes, characters, expressions)

    # No scene tokens, no character tokens — only prompt_core + "no text"
    assert "brick walls" not in result["prompt"]
    assert "cobalt blue" not in result["prompt"]
    assert "person sitting alone" in result["prompt"]
    assert result["prompt"].endswith("no text")


# ---------------------------------------------------------------------------
# T1.11 — Profile determinism
# ---------------------------------------------------------------------------


def test_profile_assembly_deterministic(scenes, characters, expressions, profiles):
    """10 consecutive calls with identical inputs produce identical outputs."""
    profile = _woodshop_profile(profiles)
    image_entry = {
        "prompt_core": "Two men at a workbench",
        "characters": [
            {"name": "protagonist", "position": "left", "action": "holding a mallet"},
            {"name": "ai-agent", "position": "right", "action": "steadying the joint"},
        ],
        "expression": "focused",
        "seed": 71,
    }
    results = [
        assemble_image_prompt(
            image_entry, profile, scenes, characters, expressions, allow_over_budget=True
        )
        for _ in range(10)
    ]
    first_prompt = results[0]["prompt"]
    first_neg = results[0]["negative_prompt"]
    for r in results[1:]:
        assert r["prompt"] == first_prompt, "Prompt changed across runs"
        assert r["negative_prompt"] == first_neg, "Negative changed across runs"


# ---------------------------------------------------------------------------
# T1.12 — Malformed registry JSON raises validation error
# ---------------------------------------------------------------------------


def test_malformed_profile_missing_description():
    """profiles.json entry missing 'description' raises jsonschema.ValidationError."""
    import jsonschema

    schema = load_registry(_PROFILES_SCHEMA)
    bad_data = {"no-desc-profile": {"scene": "woodshop"}}  # missing required "description"
    with pytest.raises(jsonschema.ValidationError) as exc_info:
        validate_registry(bad_data, schema)
    assert "description" in str(exc_info.value).lower() or "required" in str(exc_info.value).lower()


def test_malformed_character_missing_required_fields():
    """characters.json entry missing 'tokens' raises jsonschema.ValidationError."""
    import jsonschema

    schema = load_registry(_CHARACTERS_SCHEMA)
    bad_data = {
        "bad-char": {
            "description": "Missing tokens",
            "negative_tokens": "blue shirt",
            "role": "tester",
        }
    }
    with pytest.raises(jsonschema.ValidationError) as exc_info:
        validate_registry(bad_data, schema)
    assert "tokens" in str(exc_info.value).lower() or "required" in str(exc_info.value).lower()


def test_malformed_scene_missing_required_fields():
    """scenes.json entry missing 'lighting_default' raises jsonschema.ValidationError."""
    import jsonschema

    schema = load_registry(_SCENES_SCHEMA)
    bad_data = {
        "bad-scene": {
            "description": "Missing lighting_default",
            "tokens": "brick walls",
        }
    }
    with pytest.raises(jsonschema.ValidationError) as exc_info:
        validate_registry(bad_data, schema)
    assert "lighting_default" in str(exc_info.value).lower() or "required" in str(exc_info.value).lower()


# ---------------------------------------------------------------------------
# T1.13 — Circular inheritance detection
# ---------------------------------------------------------------------------


def test_circular_profile_inheritance_direct():
    """A extends B, B extends A → ValueError mentioning 'circular' or 'cycle'."""
    profiles_data = {
        "profile-a": {"description": "A", "extends": "profile-b"},
        "profile-b": {"description": "B", "extends": "profile-a"},
    }
    with pytest.raises(ValueError, match="(?i)circular|cycle"):
        resolve_profile("profile-a", profiles_data)


def test_self_referential_profile_inheritance():
    """A extends A → ValueError mentioning self-reference."""
    profiles_data = {
        "profile-a": {"description": "Self-referential", "extends": "profile-a"},
    }
    with pytest.raises(ValueError):
        resolve_profile("profile-a", profiles_data)


# ---------------------------------------------------------------------------
# T1.14 — Character count > 3: warn, do not error
# ---------------------------------------------------------------------------


def test_character_count_4_warns_not_errors(scenes, characters, expressions, capsys):
    """4 characters → warning printed but assembly succeeds."""
    profile = {"description": "Test"}
    image_entry = {
        "prompt_core": "Four people working",
        "characters": [
            {"name": "protagonist"},
            {"name": "ai-agent"},
            {"name": "ai-team"},
            {"name": "protagonist"},
        ],
    }
    # Should not raise (allow_over_budget avoids CLIP error from accumulated tokens)
    result = assemble_image_prompt(
        image_entry, profile, scenes, characters, expressions, allow_over_budget=True
    )
    captured = capsys.readouterr()
    assert "unreliable" in captured.err.lower() or "above 3" in captured.err
    assert result["prompt"]  # prompt was produced


def test_character_count_3_no_warning(scenes, characters, expressions, capsys):
    """Exactly 3 characters → no count-unreliability warning, assembly proceeds."""
    profile = {"description": "Test"}
    image_entry = {
        "prompt_core": "Three people collaborating",
        "characters": [
            {"name": "protagonist"},
            {"name": "ai-agent"},
            {"name": "ai-team"},
        ],
    }
    result = assemble_image_prompt(image_entry, profile, scenes, characters, expressions)
    captured = capsys.readouterr()
    assert "unreliable" not in captured.err.lower() or "above 3" not in captured.err
    assert result["prompt"]


# ---------------------------------------------------------------------------
# T1.15 — CLIP overflow from profile assembly
# ---------------------------------------------------------------------------


def test_clip_overflow_from_full_profile_assembly(scenes, characters, expressions, capsys):
    """Profile assembly (style+scene+2chars+expression) inflates token count past 70."""
    profile = {
        "description": "Verbose profile",
        "style": "watercolor",
        "scene": "woodshop",
        "seed_base": 1,
        "seed_strategy": "sequential",
    }
    image_entry = {
        "prompt_core": "Two men working",
        "characters": [
            {"name": "protagonist", "position": "left"},
            {"name": "ai-agent", "position": "right"},
        ],
        "expression": "focused",
    }
    # Use allow_over_budget so we can inspect the assembled prompt even if >77
    result = assemble_image_prompt(
        image_entry, profile, scenes, characters, expressions, allow_over_budget=True
    )
    n = estimate_tokens(result["prompt"])
    # CLIP budget check runs AFTER full profile assembly (not against prompt_core alone)
    assert n > 70, f"Expected assembled prompt to exceed 70 tokens, got {n}"
    captured = capsys.readouterr()
    # Either >70 warning OR >77 warning must have been printed
    assert "CLIP" in captured.err, "Expected a CLIP budget message in stderr"


def test_clip_overflow_profile_assembly_error_threshold(scenes, characters, expressions):
    """Profile with verbose tokens + long prompt_core exceeds 77 → CLIPBudgetError."""
    profile = {
        "description": "Over-budget profile",
        "style": "watercolor",
        "scene": "woodshop",
    }
    # Force well over 77 tokens by using a long prompt_core (50 tokens alone)
    long_core = " ".join(["token"] * 50)
    image_entry = {
        "prompt_core": long_core,
        "characters": [
            {"name": "protagonist", "position": "left"},
            {"name": "ai-agent", "position": "right"},
        ],
        "expression": "focused",
    }
    with pytest.raises(CLIPBudgetError) as exc_info:
        assemble_image_prompt(image_entry, profile, scenes, characters, expressions)
    # Error message must include the 77-token limit
    assert "77" in str(exc_info.value)
