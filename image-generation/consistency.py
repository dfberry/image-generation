"""consistency.py — Visual consistency assembler for simple_config.py Phase 2.

Handles:
- Registry loading (scenes, characters, expressions, profiles)
- Profile inheritance resolution (one level only)
- Prompt assembly in CLIP-priority-aware token order
- Negative prompt assembly (character negatives + count enforcement)
- CLIP token budget enforcement (warn >70, error >77)
- Seed strategies (sequential, fixed, manual)
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

from presets import STYLES, estimate_tokens

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------

_IMAGE_GEN_DIR = Path(__file__).parent
_SCHEMAS_DIR = _IMAGE_GEN_DIR / "schemas"

# ---------------------------------------------------------------------------
# Exceptions
# ---------------------------------------------------------------------------


class CLIPBudgetError(ValueError):
    """Raised when an assembled prompt exceeds the CLIP 77-token hard limit."""


# ---------------------------------------------------------------------------
# Registry loading and validation
# ---------------------------------------------------------------------------


def load_registry(path: Path) -> dict:
    """Load and parse a JSON registry file. Returns the parsed dict."""
    return json.loads(path.read_text(encoding="utf-8"))


def validate_registry(data: dict, schema: dict) -> None:
    """Validate data against a JSON Schema. Raises jsonschema.ValidationError if invalid."""
    try:
        import jsonschema
    except ImportError as exc:
        raise ImportError(
            "jsonschema is required for registry validation. "
            "Install it with: pip install jsonschema"
        ) from exc
    jsonschema.validate(data, schema)


def load_and_validate(registry_path: Path, schema_path: Path) -> dict:
    """Load a JSON registry file and validate it against its schema. Returns the parsed dict."""
    data = load_registry(registry_path)
    schema = load_registry(schema_path)
    validate_registry(data, schema)
    return data


def load_registries(base_dir: Path | None = None) -> tuple[dict, dict, dict, dict]:
    """Load and validate all four registries.

    Returns: (scenes, characters, expressions, profiles)
    """
    if base_dir is None:
        base_dir = _IMAGE_GEN_DIR
    schemas_dir = base_dir / "schemas"
    scenes = load_and_validate(base_dir / "scenes.json", schemas_dir / "scenes.schema.json")
    characters = load_and_validate(base_dir / "characters.json", schemas_dir / "characters.schema.json")
    expressions = load_and_validate(base_dir / "expressions.json", schemas_dir / "expressions.schema.json")
    profiles = load_and_validate(base_dir / "profiles.json", schemas_dir / "profiles.schema.json")
    return scenes, characters, expressions, profiles


# ---------------------------------------------------------------------------
# Profile inheritance
# ---------------------------------------------------------------------------


def resolve_profile(name: str, profiles: dict) -> dict:
    """Return a merged profile dict with one-level inheritance applied.

    Raises ValueError for:
    - Unknown profile name
    - Self-referential inheritance
    - Depth > 1 (deep chains are blocked)
    - Circular inheritance
    """
    if name not in profiles:
        raise ValueError(f"Unknown profile '{name}'. Available: {sorted(profiles)}")

    profile = dict(profiles[name])
    parent_name = profile.get("extends")

    if parent_name is None:
        return profile

    # Self-reference check
    if parent_name == name:
        raise ValueError(f"Profile '{name}' has self-referential inheritance: extends itself.")

    if parent_name not in profiles:
        raise ValueError(f"Profile '{name}' extends unknown parent '{parent_name}'.")

    parent = dict(profiles[parent_name])

    # Check parent doesn't also extend (would be depth 2)
    grandparent_name = parent.get("extends")
    if grandparent_name is not None:
        if grandparent_name == name:
            raise ValueError(
                f"Circular inheritance detected: '{name}' extends '{parent_name}' "
                f"which extends '{name}'."
            )
        raise ValueError(
            f"Profile inheritance depth > 1 not supported. "
            f"'{name}' -> '{parent_name}' -> '{grandparent_name}' "
            f"exceeds the one-level limit."
        )

    # Merge: start from parent, override with child's explicit fields
    merged = dict(parent)
    merged.pop("extends", None)
    for k, v in profile.items():
        if k != "extends":
            merged[k] = v

    return merged


# ---------------------------------------------------------------------------
# Position prefix translation
# ---------------------------------------------------------------------------

_POSITION_MAP: dict[str, str] = {
    "left": "on the left a",
    "right": "on the right a",
    "center": "in the center a",
    "foreground": "in the foreground a",
    "background": "in the background a",
}


def _position_prefix(position: str | None) -> str:
    """Return positional language prefix, or empty string if no position given.

    Raises ValueError for unrecognised position values so that typos (e.g.
    "bottom") surface immediately rather than silently producing an empty token.
    """
    if position is None:
        return ""
    key = position.lower()
    if key not in _POSITION_MAP:
        raise ValueError(
            f"Unknown position {position!r}. "
            f"Expected one of: {sorted(_POSITION_MAP)}"
        )
    return _POSITION_MAP[key]


# ---------------------------------------------------------------------------
# Count enforcement tokens
# ---------------------------------------------------------------------------

_COUNT_WORDS: dict[int, str] = {
    1: "one person",
    2: "two people",
    3: "three people",
    4: "four people",
    5: "five people",
    6: "six people",
    7: "seven people",
    8: "eight people",
}


def count_enforcement_tokens(n: int) -> str:
    """Return count-enforcement negative tokens for N characters.

    Produces: [N-1, N+1, N+2] — excluding N itself — to tell SDXL
    what count is NOT wanted. For N=1, [N+1, N+2, N+3] (no N-1 < 1).
    """
    if n <= 1:
        raw = [n + 1, n + 2, n + 3]
    else:
        raw = [n - 1, n + 1, n + 2]
    tokens = [_COUNT_WORDS[c] for c in raw if c in _COUNT_WORDS]
    return ", ".join(tokens)


# ---------------------------------------------------------------------------
# CLIP token budget check
# ---------------------------------------------------------------------------

_CLIP_WARN_THRESHOLD = 70
_CLIP_ERROR_THRESHOLD = 77


def check_clip_budget(assembled_prompt: str, *, allow_over_budget: bool = False) -> None:
    """Check CLIP token budget for assembled_prompt.

    Prints warning to stderr at >70 tokens.
    Raises CLIPBudgetError at >77 tokens (unless allow_over_budget=True).
    """
    n = estimate_tokens(assembled_prompt)
    if n > _CLIP_ERROR_THRESHOLD:
        msg = (
            f"⚠️ CLIP token limit exceeded: {n}/{_CLIP_ERROR_THRESHOLD}. "
            "Prompt will be truncated by SDXL's text encoder."
        )
        if allow_over_budget:
            print(msg, file=sys.stderr)
        else:
            raise CLIPBudgetError(msg)
    elif n > _CLIP_WARN_THRESHOLD:
        print(
            f"⚠️ Approaching CLIP limit ({n}/77). Consider trimming scene tokens.",
            file=sys.stderr,
        )


# ---------------------------------------------------------------------------
# Style token resolution
# ---------------------------------------------------------------------------


def _get_style_tokens(style_name: str | None) -> str:
    """Return style tokens string for the given style name.

    Returns "" for passthrough styles (oil-painting, sketch, anime) or None.
    """
    if style_name is None:
        return ""
    style_lower = style_name.lower()
    if style_lower == "none":
        return ""
    if style_lower not in STYLES:
        return ""
    style_data = STYLES[style_lower]
    if style_data.get("passthrough"):
        return ""
    return style_data.get("tokens", "")


# ---------------------------------------------------------------------------
# Character token block builder
# ---------------------------------------------------------------------------


def _build_char_token_block(
    char_entry: dict,
    characters: dict,
    per_char_expressions: dict[str, str] | None,
    expressions: dict,
) -> tuple[str, str]:
    """Build the token block for a single character entry.

    Returns (token_block, negative_tokens).
    """
    char_name = char_entry.get("name", "")
    if char_name not in characters:
        raise ValueError(f"Unknown character '{char_name}'. Available: {sorted(characters)}")

    char_data = characters[char_name]
    tokens = char_data["tokens"]
    negative = char_data.get("negative_tokens", "")

    position = char_entry.get("position")
    action = char_entry.get("action")

    prefix = _position_prefix(position)
    block = f"{prefix} {tokens}" if prefix else tokens

    # Per-character expression appended inline to this character's block
    if per_char_expressions and char_name in per_char_expressions:
        expr_name = per_char_expressions[char_name]
        if expr_name not in expressions:
            raise ValueError(f"Unknown expression '{expr_name}'. Available: {sorted(expressions)}")
        expr_tokens = expressions[expr_name]["tokens"]
        block = block.rstrip(", ") + ", " + expr_tokens

    if action:
        block = block.rstrip(", ") + ", " + action

    return block, negative


# ---------------------------------------------------------------------------
# Core assembler
# ---------------------------------------------------------------------------


def assemble_image_prompt(
    image_entry: dict,
    profile: dict,
    scenes: dict,
    characters: dict,
    expressions: dict,
    *,
    scene_variant: str | None = None,
    image_index: int = 0,
    allow_over_budget: bool = False,
) -> dict:
    """Assemble prompt, negative prompt, and seed for one image entry.

    Prompt order (CLIP-priority-aware):
        {style_tokens}, {prompt_core}, {char_tokens}, {expr_tokens},
        {scene_tokens}, {lighting_tokens}, no text

    Returns dict: {prompt, negative_prompt, seed, output}
    """
    # 1. Style tokens
    style_tokens = _get_style_tokens(profile.get("style"))

    # 2. Prompt core
    prompt_core = image_entry.get("prompt_core", "")

    # 3. Character tokens
    char_entries = image_entry.get("characters", [])

    # Per-character expressions dict vs group expression string
    per_char_expressions: dict[str, str] | None = None
    raw_expressions = image_entry.get("expressions")
    if isinstance(raw_expressions, dict):
        per_char_expressions = raw_expressions

    # Warn when count > 3 (SDXL unreliable)
    if len(char_entries) > 3:
        print(
            f"⚠️ SDXL is unreliable for exact counts above 3 "
            f"({len(char_entries)} characters specified). "
            "Generated image may not contain the correct number of people.",
            file=sys.stderr,
        )

    char_blocks: list[str] = []
    all_char_negatives: list[str] = []
    for char_entry in char_entries:
        block, neg = _build_char_token_block(char_entry, characters, per_char_expressions, expressions)
        char_blocks.append(block)
        if neg:
            all_char_negatives.append(neg)

    char_token_str = ", ".join(char_blocks)

    # 4. Group expression tokens (only when per-char expressions not in use)
    group_expr_tokens = ""
    if per_char_expressions is None:
        expr_name = image_entry.get("expression")
        if expr_name:
            if expr_name not in expressions:
                raise ValueError(f"Unknown expression '{expr_name}'. Available: {sorted(expressions)}")
            group_expr_tokens = expressions[expr_name]["tokens"]

    # 5. Scene tokens + lighting
    scene_name = profile.get("scene")
    scene_tokens = ""
    lighting_tokens = ""
    if scene_name:
        if scene_name not in scenes:
            raise ValueError(f"Unknown scene '{scene_name}'. Available: {sorted(scenes)}")
        scene_data = scenes[scene_name]
        scene_tokens = scene_data.get("tokens", "")

        # Scene variant (per-image override takes precedence over flag)
        effective_variant = image_entry.get("scene_variant") or scene_variant
        if effective_variant:
            variations = scene_data.get("variations", {})
            if effective_variant in variations:
                lighting_tokens = variations[effective_variant]
            else:
                print(
                    f"⚠️ Unknown scene variant '{effective_variant}' for scene '{scene_name}'. "
                    f"Using default lighting. Available: {sorted(variations)}",
                    file=sys.stderr,
                )
                lighting_tokens = scene_data.get("lighting_default", "")
        else:
            lighting_tokens = scene_data.get("lighting_default", "")

    # 6. Assemble prompt in CLIP-priority order
    parts: list[str] = []
    for segment in [style_tokens, prompt_core, char_token_str, group_expr_tokens, scene_tokens, lighting_tokens]:
        cleaned = segment.strip(" ,")
        if cleaned:
            parts.append(cleaned)
    parts.append("no text")

    assembled_prompt = ", ".join(parts)

    # 7. CLIP budget check
    check_clip_budget(assembled_prompt, allow_over_budget=allow_over_budget)

    # 8. Negative prompt assembly
    negative_parts: list[str] = []

    # a. Profile base negative
    neg_base = profile.get("negative_base", "")
    if neg_base:
        negative_parts.append(neg_base.strip(" ,"))

    # b. Character-specific negative tokens
    for neg in all_char_negatives:
        cleaned = neg.strip(" ,")
        if cleaned:
            negative_parts.append(cleaned)

    # c. Count enforcement
    if char_entries:
        count_neg = count_enforcement_tokens(len(char_entries))
        if count_neg:
            negative_parts.append(count_neg)

    # d. Image-level explicit negative (appended last)
    explicit_neg = image_entry.get("negative_prompt", "")
    if explicit_neg:
        negative_parts.append(explicit_neg.strip(" ,"))

    assembled_negative = ", ".join(p for p in negative_parts if p)

    # 9. Seed assignment
    seed_strategy = profile.get("seed_strategy", "sequential")
    seed_base = profile.get("seed_base", 0)

    # Image-level seed override always wins over strategy
    if "seed" in image_entry:
        seed = image_entry["seed"]
    elif seed_strategy == "sequential":
        seed = seed_base + image_index
    elif seed_strategy == "fixed":
        seed = seed_base
    elif seed_strategy == "manual":
        raise ValueError(
            f"seed_strategy='manual' requires every image entry to specify a 'seed'. "
            f"Image at index {image_index} has no 'seed' field."
        )
    else:
        seed = seed_base + image_index

    return {
        "prompt": assembled_prompt,
        "negative_prompt": assembled_negative,
        "seed": seed,
        "output": image_entry.get("output"),
    }


# ---------------------------------------------------------------------------
# Batch assembler entry point
# ---------------------------------------------------------------------------


def assemble_v2_batch(
    batch_data: dict,
    *,
    scene_variant: str | None = None,
    allow_over_budget: bool = False,
    base_dir: Path | None = None,
) -> list[dict]:
    """Assemble a v2 batch JSON into a flat list of resolved job dicts.

    batch_data must contain 'profile' (str) and 'images' (list) keys.
    Returns list of {prompt, negative_prompt, seed, output} dicts
    ready for generate.py.
    """
    if base_dir is None:
        base_dir = _IMAGE_GEN_DIR

    scenes, characters, expressions, profiles = load_registries(base_dir)

    profile_name = batch_data["profile"]
    profile = resolve_profile(profile_name, profiles)
    images = batch_data["images"]

    resolved: list[dict] = []
    for i, image_entry in enumerate(images):
        job = assemble_image_prompt(
            image_entry,
            profile,
            scenes,
            characters,
            expressions,
            scene_variant=scene_variant,
            image_index=i,
            allow_over_budget=allow_over_budget,
        )
        resolved.append(job)

    return resolved


# ---------------------------------------------------------------------------
# Preview output helper
# ---------------------------------------------------------------------------


def print_preview(resolved_jobs: list[dict]) -> None:
    """Print assembled prompts and negatives to stdout (--preview-prompts mode)."""
    for i, job in enumerate(resolved_jobs, 1):
        prompt = job.get("prompt", "")
        negative = job.get("negative_prompt", "")
        n_tokens = estimate_tokens(prompt)

        print(f"\n[simple_config] Image {i} -- Assembled prompt:")
        print(f"  {prompt}")
        print("\n[simple_config] Assembled negative prompt:")
        print(f"  {negative}")

        if n_tokens > _CLIP_ERROR_THRESHOLD:
            status = f"[!] {n_tokens}/77 -- EXCEEDS CLIP limit"
        elif n_tokens > _CLIP_WARN_THRESHOLD:
            status = f"[!] {n_tokens}/77 -- approaching CLIP warning threshold of 70"
        else:
            status = f"{n_tokens}/77  (below warning threshold of 70 -- no action needed)"

        print(f"\n[simple_config] Estimated tokens: {status}")
