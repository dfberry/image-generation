#!/usr/bin/env python3
"""simple_config.py — User-friendly CLI wrapper for generate.py.

Translates plain-English quality/style/size terms into SDXL parameters,
then delegates to generate.py via subprocess.run.

Usage:
  python simple_config.py "a sunset over mountains" --preset quick-draft --seed 42
  python simple_config.py --prompt "a developer at a desk" --preset production \\
    --style watercolor --size blog-hero --output hero.png
  python simple_config.py --preset standard --dry-run
  python simple_config.py --preset production --style watercolor --batch-file jobs.json
"""

from __future__ import annotations

import argparse
import json
import shlex
import subprocess
import sys
from pathlib import Path

from presets import (
    LORAS,
    MODIFIERS,
    PRESETS,
    PROMPT_TEMPLATES,
    SIZES,
    STYLES,
    apply_modifier,
    apply_style_tokens,
    check_guidance_warning,
    check_vague_colors,
    estimate_tokens,
    load_loras,
    resolve_lora_weight,
    resolve_preset,
)

_GENERATE_PY = Path(__file__).parent / "generate.py"
_LORAS_JSON = Path(__file__).parent / "loras.json"
_DEFAULT_PRESET = "standard"
_DEFAULT_NEGATIVE_PROMPT = (
    "text, letters, words, no text, no letters, no words, no writing, "
    "watermark, signature, blurry, low quality, distorted"
)

# ---------------------------------------------------------------------------
# LoRA system — registry, resolution, compatibility, trigger word injection
# ---------------------------------------------------------------------------

MODEL_TYPE_MAP: dict[str, str] = {
    "precise": "sdxl",
    "balanced": "sd3",
    "creative": "flux",
}

_VALID_MODEL_TYPES = frozenset(MODEL_TYPE_MAP.values())


def _load_registry(path: Path | None = None) -> dict:
    """Load the full loras.json document (version + loras dict)."""
    p = path or _LORAS_JSON
    if not p.exists():
        return {"version": 1, "loras": {}}
    return json.loads(p.read_text(encoding="utf-8"))


def _save_registry(data: dict, path: Path | None = None) -> None:
    """Write the registry atomically via a temp file → rename."""
    p = path or _LORAS_JSON
    tmp = p.parent / ".loras.json.tmp"
    tmp.write_text(json.dumps(data, indent=2), encoding="utf-8")
    tmp.replace(p)


def lora_add(
    name: str,
    entry: dict,
    path: Path | None = None,
    overwrite: bool = False,
) -> None:
    """Add a LoRA entry to the registry.

    Args:
        name: Friendly name key for the registry.
        entry: Dict with model_id, default_weight, compatible_models, etc.
        path: Override registry file path (for testing).
        overwrite: If True, replace an existing entry with the same name.

    Raises:
        ValueError: If entry fields fail validation.
        KeyError: If name already exists and overwrite=False.
    """
    if not entry.get("model_id"):
        raise ValueError("model_id must be a non-empty string")
    for m in entry.get("compatible_models", []):
        if m not in _VALID_MODEL_TYPES:
            raise ValueError(
                f"Unknown model type '{m}'. Must be one of {sorted(_VALID_MODEL_TYPES)}"
            )
    data = _load_registry(path)
    if name in data["loras"] and not overwrite:
        raise KeyError(f"'{name}' already exists in loras.json. Pass overwrite=True to replace.")
    data["loras"][name] = entry
    _save_registry(data, path)


def lora_remove(name: str, path: Path | None = None) -> None:
    """Remove a LoRA entry from the registry (no-op if not found)."""
    data = _load_registry(path)
    data["loras"].pop(name, None)
    _save_registry(data, path)


def resolve_lora(
    style_name: str | None,
    explicit_lora: str | None,
    explicit_weight: str | float | None,
    loras: dict,
) -> tuple[str | None, float | None]:
    """Return (model_id, weight) for the effective LoRA, or (None, None).

    Precedence (highest to lowest):
        1. explicit_lora from --lora flag
        2. Style's declared lora from STYLES dict
        3. No LoRA → (None, None)

    Weight precedence (highest to lowest):
        1. explicit_weight (from --lora-weight or colon syntax)
        2. Style entry's lora_weight
        3. Registry entry's default_weight
        4. 0.8 fallback (raw HF ID passthrough)
    """
    lora_name = explicit_lora
    if lora_name is None and style_name:
        lora_name = STYLES.get(style_name, {}).get("lora")

    if lora_name is None:
        return None, None

    if lora_name in loras:
        entry = loras[lora_name]
        model_id = entry["model_id"]
        weight_src = explicit_weight
        if weight_src is None:
            style_entry = STYLES.get(style_name or "", {})
            weight_src = style_entry.get("lora_weight")
        if weight_src is None:
            weight_src = entry["default_weight"]
    else:
        # Raw HuggingFace model ID passthrough — no registry metadata
        model_id = lora_name
        weight_src = explicit_weight if explicit_weight is not None else 0.8

    return model_id, resolve_lora_weight(weight_src)


def check_lora_compatibility(
    lora_name: str,
    model_alias: str,
    loras: dict,
) -> None:
    """Hard error (SystemExit) if the selected LoRA is incompatible with the model.

    Skips the check if lora_name is not in the registry (raw HF ID passthrough).
    """
    if lora_name not in loras:
        return  # no metadata → no check

    model_type = MODEL_TYPE_MAP.get(model_alias, model_alias)
    compatible = loras[lora_name].get("compatible_models", [])

    if compatible and model_type not in compatible:
        raise SystemExit(
            f"\n[error] LoRA '{lora_name}' is compatible with: {compatible}.\n"
            f"        Selected model '{model_alias}' is type '{model_type}'.\n"
            f"        Use --model precise (SDXL) or choose a different LoRA.\n"
        )


def check_and_inject_trigger_words(
    prompt: str,
    lora_name: str,
    loras: dict,
    interactive: bool = True,
) -> str:
    """Check for required trigger words; inject them if absent.

    Args:
        prompt: The assembled prompt text.
        lora_name: Friendly name to look up in the registry.
        loras: The loaded LORAS registry dict.
        interactive: If True, prompts the user before injecting (TTY).
                     If False, injects silently and logs to stderr.

    Returns:
        The (possibly modified) prompt string.
    """
    if lora_name not in loras:
        return prompt
    trigger_words = loras[lora_name].get("trigger_words", [])
    if not trigger_words:
        return prompt

    missing = [w for w in trigger_words if w.lower() not in prompt.lower()]
    if not missing:
        return prompt

    if interactive:
        print(f"[warn] LoRA '{lora_name}' requires trigger word(s): {missing}")
        print("       Not detected in prompt. Add for best results.")
        answer = input("       → Inject automatically? [Y/n]: ").strip().lower()
        if answer in ("", "y", "yes"):
            return prompt.rstrip(", ") + ", " + ", ".join(missing)
        return prompt
    else:
        print(
            f"[info] Auto-injecting trigger word(s) for '{lora_name}': {missing}",
            file=sys.stderr,
        )
        return prompt.rstrip(", ") + ", " + ", ".join(missing)


def _extract_effective_lora(
    lora_list: list[str] | None,
) -> tuple[str | None, str | None]:
    """Extract the single effective (lora_name, per_lora_weight) from the CLI list.

    For v1 (single-LoRA path):
    - If multiple --lora flags, warns and uses the last one.
    - Parses colon syntax: "name:intensity" → ("name", "intensity").
    - Returns (None, None) if no loras specified.
    """
    if not lora_list:
        return None, None
    if len(lora_list) > 1:
        last_name = lora_list[-1].rsplit(":", 1)[0]
        print(
            f"[warn] Multiple --lora flags detected. Only the last value "
            f"('{last_name}') will be used.\n"
            f"       Multi-LoRA stacking requires prd-engine.md Phase 1 (adapter naming fix).",
            file=sys.stderr,
        )
    effective = lora_list[-1]
    if ":" in effective:
        name, intensity = effective.rsplit(":", 1)
        return name, intensity
    return effective, None


# ---------------------------------------------------------------------------
# Argument parser
# ---------------------------------------------------------------------------


def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="simple_config.py",
        description=(
            "User-friendly wrapper for generate.py.\n"
            "Translates plain-English terms (preset/style/size) to SDXL parameters."
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
examples:
  # Quick draft
  python simple_config.py "a glowing tropical garden" --preset quick-draft --seed 42

  # Production watercolor blog hero
  python simple_config.py --prompt "a developer at a desk, warm light, no text" \\
    --preset production --style watercolor --size blog-hero --output outputs/hero.png --cpu

  # Dry run to preview resolved parameters
  python simple_config.py --preset production --style watercolor --dry-run

  # Batch processing
  python simple_config.py --preset production --style watercolor --batch-file jobs.json --dry-run
""",
    )

    # Prompt: positional (convenience) or named --prompt (canonical)
    parser.add_argument(
        "pos_prompt",
        nargs="?",
        default=None,
        metavar="PROMPT",
        help="Text prompt (positional shorthand; use --prompt for named form)",
    )
    parser.add_argument(
        "--prompt",
        dest="named_prompt",
        default=None,
        metavar="TEXT",
        help="Text prompt for image generation",
    )

    # Quality / preset
    parser.add_argument(
        "--preset",
        "--quality",
        dest="preset",
        default=_DEFAULT_PRESET,
        choices=list(PRESETS),
        metavar="PRESET",
        help=f"Quality preset: {', '.join(PRESETS)} (default: {_DEFAULT_PRESET})",
    )

    # Modifiers (repeatable)
    parser.add_argument(
        "--modifier",
        action="append",
        dest="modifiers",
        default=None,
        metavar="MODIFIER",
        help=(
            "Adjust parameters on top of preset (repeatable). "
            f"Choices: {', '.join(sorted(MODIFIERS))}"
        ),
    )

    # Style
    parser.add_argument(
        "--style",
        default=None,
        choices=list(STYLES) + ["none"],
        metavar="STYLE",
        help=f"Style preset: {', '.join(STYLES)}, none",
    )
    parser.add_argument(
        "--no-default-style",
        action="store_true",
        dest="no_default_style",
        help="Suppress folk-art default style tokens (same as --style none)",
    )

    # Size
    parser.add_argument(
        "--size",
        default=None,
        choices=list(SIZES),
        metavar="SIZE",
        help=f"Image size preset: {', '.join(SIZES)}",
    )

    # Passthrough args forwarded to generate.py
    parser.add_argument("--seed", type=int, default=None, help="Random seed for reproducibility")
    parser.add_argument("--output", default=None, help="Output file path")
    parser.add_argument("--cpu", action="store_true", help="Force CPU mode (slow, no GPU required)")
    parser.add_argument(
        "--model",
        default=None,
        choices=["creative", "precise", "balanced"],
        help="Model override (overrides any modifier-applied model)",
    )
    parser.add_argument(
        "--negative-prompt",
        dest="negative_prompt",
        default=None,
        help="Negative prompt override",
    )
    parser.add_argument(
        "--lora",
        action="append",
        dest="lora",
        default=None,
        metavar="NAME[:INTENSITY]",
        help=(
            "LoRA model by registry name or raw HuggingFace ID. "
            "Use colon syntax for per-LoRA intensity: name:strong. "
            "Repeatable (v1: last value wins with warning)."
        ),
    )
    parser.add_argument(
        "--lora-weight",
        type=str,
        dest="lora_weight",
        default=None,
        help="LoRA adapter weight: light (0.4) / medium (0.7) / strong (0.9) or a float (e.g. 0.8)",
    )
    parser.add_argument(
        "--width",
        type=int,
        default=None,
        help="Image width override in pixels (must be divisible by 8)",
    )
    parser.add_argument(
        "--height",
        type=int,
        default=None,
        help="Image height override in pixels (must be divisible by 8)",
    )

    # simple_config.py control flags
    parser.add_argument(
        "--dry-run",
        action="store_true",
        dest="dry_run",
        help="Print resolved generate.py command without executing",
    )
    parser.add_argument(
        "--assist",
        "--prompt-help",
        action="store_true",
        dest="assist",
        help="Pre-flight prompt engineering assistance (token check, style preview, suggestions)",
    )
    parser.add_argument(
        "--template",
        default=None,
        choices=list(PROMPT_TEMPLATES),
        help="Prompt scaffold template (requires --assist)",
    )
    parser.add_argument(
        "--batch-file",
        dest="batch_file",
        default=None,
        metavar="PATH",
        help="JSON file with array of generation jobs",
    )

    return parser.parse_args(argv)


# ---------------------------------------------------------------------------
# Parameter resolution
# ---------------------------------------------------------------------------


def _effective_prompt(args: argparse.Namespace) -> str:
    """Return the final user-supplied prompt text (before style injection)."""
    return args.named_prompt if args.named_prompt is not None else (args.pos_prompt or "")


def resolve_base_params(args: argparse.Namespace) -> dict:
    """Resolve preset + modifiers + size + passthrough args (no style tokens yet).

    Style token injection is done separately so batch jobs can each get their
    own prompt with shared style applied.
    """
    params = resolve_preset(args.preset)

    for mod_name in args.modifiers or []:
        if mod_name not in MODIFIERS:
            print(
                f"[simple_config] ❌ Unknown modifier '{mod_name}'. "
                f"Available: {', '.join(sorted(MODIFIERS))}",
                file=sys.stderr,
            )
            sys.exit(1)
        apply_modifier(params, mod_name)

    # Print any guidance warnings after all modifiers are applied
    for warning in check_guidance_warning(params):
        print(warning, file=sys.stderr)

    # CLI --model takes highest priority over modifier-applied model
    if args.model:
        params["model"] = args.model

    # Size resolution
    params["width"] = 1024
    params["height"] = 1024
    if args.size:
        params.update(SIZES[args.size])
    if args.width is not None:
        params["width"] = args.width
    if args.height is not None:
        params["height"] = args.height

    # Passthrough args
    params["seed"] = args.seed
    params["output"] = args.output
    params["cpu"] = args.cpu
    params["negative_prompt"] = args.negative_prompt

    return params


def apply_prompt_and_style(
    base_params: dict,
    prompt: str,
    style: str | None,
    no_default_style: bool,
    lora_override: str | None,
    lora_weight_override: str | float | None,
) -> dict:
    """Apply style tokens, registry LoRA resolution, compatibility check, and trigger injection.

    Returns a new param dict with 'prompt', 'lora', 'lora_weight' set.
    """
    params = dict(base_params)

    effective_style = None if (style is None or style.lower() == "none") else style
    no_default = no_default_style or (style is not None and style.lower() == "none")

    # If a registered LoRA has style_tokens and no explicit style is set,
    # use the registry's style_tokens instead of the folk-art default.
    lora_style_tokens: str | None = None
    if lora_override and not effective_style and not no_default:
        reg_entry = LORAS.get(lora_override)
        if reg_entry:
            lora_style_tokens = reg_entry.get("style_tokens") or None

    if lora_style_tokens:
        final_prompt = f"{lora_style_tokens} {prompt}" if prompt else lora_style_tokens
        passthrough_style = None
    else:
        final_prompt, _, _, passthrough_style = apply_style_tokens(
            prompt,
            effective_style,
            no_default_style=no_default,
        )

    params["prompt"] = final_prompt

    # Resolve LoRA via registry (friendly name → model_id + weight)
    model_id, final_weight = resolve_lora(
        effective_style, lora_override, lora_weight_override, LORAS
    )

    # Apply guidance_delta from registry (signed adjustment, applied silently)
    lora_name_for_meta = lora_override or (
        STYLES.get(effective_style or "", {}).get("lora") if effective_style else None
    )
    if lora_name_for_meta and lora_name_for_meta in LORAS:
        guidance_delta = LORAS[lora_name_for_meta].get("guidance_delta", 0)
        if guidance_delta:
            params["guidance"] = params.get("guidance", 6.5) + guidance_delta

    # Compatibility check (runs after all modifier resolution; only for registered LoRAs)
    if lora_override:
        model_alias = params.get("model")
        if model_alias:
            check_lora_compatibility(lora_override, model_alias, LORAS)

    if model_id:
        params["lora"] = model_id
        params["lora_weight"] = final_weight if final_weight is not None else 0.8
    else:
        params["lora"] = None
        params["lora_weight"] = 0.8

    # Trigger word injection (interactive on TTY, silent in non-interactive contexts)
    if model_id and lora_override and lora_override in LORAS:
        params["prompt"] = check_and_inject_trigger_words(
            params["prompt"],
            lora_override,
            LORAS,
            interactive=sys.stdin.isatty(),
        )

    if passthrough_style:
        params["style_passthrough"] = passthrough_style

    return params


# ---------------------------------------------------------------------------
# Command builder
# ---------------------------------------------------------------------------


def build_generate_cmd(params: dict) -> list[str]:
    """Convert a resolved params dict to a generate.py CLI arg list.

    Omits args that match generate.py defaults to keep the command concise.
    """
    cmd = [sys.executable, str(_GENERATE_PY)]

    if params.get("prompt"):
        cmd += ["--prompt", params["prompt"]]

    # Core inference params (always include steps + guidance)
    cmd += ["--steps", str(params["steps"])]
    cmd += ["--guidance", str(params["guidance"])]

    if params.get("refine"):
        cmd.append("--refine")

    # Omit --refiner-steps if it matches generate.py default (10)
    refiner_steps = params.get("refiner_steps", 10)
    if refiner_steps != 10:
        cmd += ["--refiner-steps", str(refiner_steps)]

    # Omit --refiner-guidance if it matches generate.py default (5.0)
    refiner_guidance = params.get("refiner_guidance", 5.0)
    if refiner_guidance != 5.0:
        cmd += ["--refiner-guidance", str(refiner_guidance)]

    # LoRA
    if params.get("lora"):
        cmd += ["--lora", params["lora"]]
        cmd += ["--lora-weight", str(params.get("lora_weight", 0.8))]

    # Passthrough style (for styles like oil-painting, sketch, anime)
    if params.get("style_passthrough"):
        cmd += ["--style", params["style_passthrough"]]

    # Dimensions — omit if square (1024×1024, the generate.py defaults)
    width = params.get("width", 1024)
    height = params.get("height", 1024)
    if width != 1024 or height != 1024:
        cmd += ["--width", str(width), "--height", str(height)]

    # Model override (only if set — None means use generate.py default)
    if params.get("model"):
        cmd += ["--model", params["model"]]

    # Scheduler (only if non-default)
    scheduler = params.get("scheduler", "DPMSolverMultistepScheduler")
    if scheduler != "DPMSolverMultistepScheduler":
        cmd += ["--scheduler", scheduler]

    # Passthrough args
    if params.get("seed") is not None:
        cmd += ["--seed", str(params["seed"])]
    if params.get("output"):
        cmd += ["--output", params["output"]]
    if params.get("negative_prompt"):
        cmd += ["--negative-prompt", params["negative_prompt"]]
    if params.get("cpu"):
        cmd.append("--cpu")

    return cmd


# ---------------------------------------------------------------------------
# Prompt assist
# ---------------------------------------------------------------------------

_LIGHTING_WORDS = frozenset(
    "light lighting morning afternoon evening sunset sunrise glow bright dark shadow dusk dawn".split()
)


def run_assist(params: dict, args: argparse.Namespace) -> dict:
    """Run prompt engineering checks; modifies params['prompt'] as needed.

    Interactive when a TTY is detected; applies silent safe defaults otherwise.
    (See OQ-7, OQ-10 in prd-wrapper-core.md.)
    """
    is_interactive = sys.stdin.isatty()
    prompt = params.get("prompt", "")
    raw_prompt = _effective_prompt(args)

    # Template handling (--assist --template)
    if args.template and not raw_prompt:
        scaffold = PROMPT_TEMPLATES[args.template]
        print(f"\n[assist] Prompt template ({args.template}):\n  {scaffold}")
        if is_interactive:
            resp = input("  → Use this as your starting prompt? [Y/n]: ").strip().lower()
            if resp in ("", "y", "yes"):
                params["prompt"] = scaffold
                prompt = scaffold
        return params

    if not prompt:
        return params

    # "no text" enforcement
    if "no text" not in prompt.lower():
        if is_interactive:
            print('\n[assist] "no text" rule not detected in your prompt.')
            resp = input('  Suggestion: append ", no text". → Apply? [Y/n]: ').strip().lower()
            if resp in ("", "y", "yes"):
                params["prompt"] = prompt.rstrip(" ,") + ", no text"
                prompt = params["prompt"]
        else:
            params["prompt"] = prompt.rstrip(" ,") + ", no text"
            prompt = params["prompt"]

    # Negative prompt auto-add
    if not params.get("negative_prompt"):
        if is_interactive:
            print(f'\n[assist] Negative prompt will be applied automatically:\n  "{_DEFAULT_NEGATIVE_PROMPT}"')
            resp = input("  → Accept? [Y/n]: ").strip().lower()
            if resp in ("", "y", "yes"):
                params["negative_prompt"] = _DEFAULT_NEGATIVE_PROMPT
        else:
            params["negative_prompt"] = _DEFAULT_NEGATIVE_PROMPT

    # Token count check
    token_count = estimate_tokens(prompt)
    print(f"\n[assist] Token check: {token_count} / 77 CLIP limit. ", end="")
    if token_count < 60:
        print("✅ OK.")
    elif token_count < 77:
        print(f"⚠️  {token_count} tokens — consider trimming to under 60.")
        if is_interactive:
            input("  → Press Enter to continue... ")
    else:
        print(f"❌ {token_count} tokens — prompt will be truncated by SDXL's text encoder.")
        if is_interactive:
            resp = input("  → Proceed anyway? [y/N]: ").strip().lower()
            if resp not in ("y", "yes"):
                sys.exit(1)

    # Color specificity suggestion
    vague = check_vague_colors(raw_prompt)
    if vague:
        print(f"\n[assist] Vague color words detected: {', '.join(vague)}")
        print("  Suggestion: use specifics like 'bright cobalt blue', 'deep crimson red', etc.")

    # Scene expansion suggestion
    raw_words = raw_prompt.split()
    has_lighting = any(w.lower() in _LIGHTING_WORDS for w in raw_words)
    if len(raw_words) < 8 and not has_lighting:
        suggestion = raw_prompt.rstrip(" ,") + ", warm afternoon light"
        print('\n[assist] Scene suggestion: minimal prompt detected (no lighting cues).')
        print(f'  Suggested expansion: "{suggestion}"')
        if is_interactive:
            resp = input("  → Use suggestion? [Y/n]: ").strip().lower()
            if resp in ("", "y", "yes"):
                # params["prompt"] already has style tokens prepended; just extend it
                params["prompt"] = params["prompt"].rstrip(" ,") + ", warm afternoon light"

    return params


# ---------------------------------------------------------------------------
# Single-image execution
# ---------------------------------------------------------------------------


def run_single(args: argparse.Namespace) -> int:
    """Resolve params for a single image and invoke (or dry-run) generate.py."""
    prompt = _effective_prompt(args)

    if not prompt and not args.dry_run:
        print(
            "[simple_config] ❌ --prompt is required for image generation. "
            "Use --dry-run to preview without a prompt.",
            file=sys.stderr,
        )
        return 1

    base = resolve_base_params(args)
    effective_lora, per_lora_weight = _extract_effective_lora(args.lora)
    effective_weight = per_lora_weight if per_lora_weight is not None else args.lora_weight
    params = apply_prompt_and_style(
        base,
        prompt,
        args.style,
        args.no_default_style,
        effective_lora,
        effective_weight,
    )

    if args.assist:
        params = run_assist(params, args)

    cmd = build_generate_cmd(params)
    cmd_str = " ".join(shlex.quote(c) for c in cmd)
    print(f"[simple_config] Resolved command:\n  {cmd_str}\n")

    if args.dry_run:
        print("[dry-run] 0 generate.py calls made.")
        return 0

    result = subprocess.run(cmd, cwd=Path(__file__).parent, timeout=3600)
    return result.returncode


# ---------------------------------------------------------------------------
# Batch-file execution
# ---------------------------------------------------------------------------


def run_batch(args: argparse.Namespace) -> int:
    """Process a JSON batch file of generation jobs."""
    batch_path = Path(args.batch_file)
    if not batch_path.is_absolute():
        # Resolve relative paths from the current working directory
        batch_path = Path.cwd() / batch_path

    if not batch_path.exists():
        print(f"[simple_config] ❌ Batch file not found: {args.batch_file}", file=sys.stderr)
        return 1

    try:
        jobs = json.loads(batch_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        print(f"[simple_config] ❌ Invalid JSON in batch file: {exc}", file=sys.stderr)
        return 1

    if not isinstance(jobs, list):
        print("[simple_config] ❌ Batch file must contain a JSON array of job objects.", file=sys.stderr)
        return 1

    base = resolve_base_params(args)
    effective_lora, per_lora_weight = _extract_effective_lora(args.lora)
    effective_weight = per_lora_weight if per_lora_weight is not None else args.lora_weight
    total = len(jobs)
    failures: list[int] = []

    for i, job in enumerate(jobs, 1):
        if not isinstance(job, dict):
            print(f"[simple_config] ❌ Job {i}/{total} is not a dict — skipping.", file=sys.stderr)
            failures.append(i)
            continue

        job_prompt = job.get("prompt", "")
        if not job_prompt:
            print(f"[simple_config] ❌ Job {i}/{total} has no 'prompt' field — skipping.", file=sys.stderr)
            failures.append(i)
            continue

        params = apply_prompt_and_style(
            base,
            job_prompt,
            args.style,
            args.no_default_style,
            effective_lora,
            effective_weight,
        )

        # Apply per-job field overrides with type validation
        _JOB_FIELD_TYPES: dict[str, type | tuple] = {
            "seed": int,
            "output": str,
            "steps": int,
            "guidance": (int, float),
            "width": int,
            "height": int,
            "model": str,
        }
        _MODEL_CHOICES = frozenset({"creative", "precise", "balanced"})
        job_valid = True
        for field, expected_type in _JOB_FIELD_TYPES.items():
            if field not in job:
                continue
            value = job[field]
            if not isinstance(value, expected_type):
                print(
                    f"[simple_config] ❌ Job {i}/{total}: field '{field}' must be "
                    f"{expected_type if isinstance(expected_type, type) else '/'.join(t.__name__ for t in expected_type)}"
                    f", got {type(value).__name__} — skipping job.",
                    file=sys.stderr,
                )
                job_valid = False
                break
            if field == "model" and value not in _MODEL_CHOICES:
                print(
                    f"[simple_config] ❌ Job {i}/{total}: field 'model' must be one of "
                    f"{sorted(_MODEL_CHOICES)}, got '{value}' — skipping job.",
                    file=sys.stderr,
                )
                job_valid = False
                break
            params[field] = value
        if not job_valid:
            failures.append(i)
            continue

        # --assist runs in non-interactive (silent safe-defaults) mode for batch
        if args.assist:
            if "no text" not in params.get("prompt", "").lower():
                params["prompt"] = params.get("prompt", "").rstrip(" ,") + ", no text"
            if not params.get("negative_prompt"):
                params["negative_prompt"] = _DEFAULT_NEGATIVE_PROMPT

        cmd = build_generate_cmd(params)
        cmd_str = " ".join(shlex.quote(c) for c in cmd)
        print(f"[job {i}/{total}] {cmd_str}")

        if not args.dry_run:
            result = subprocess.run(cmd, cwd=Path(__file__).parent, timeout=3600)
            if result.returncode != 0:
                failures.append(i)

    if args.dry_run:
        print(f"[dry-run] {total} jobs resolved. 0 generate.py calls made.")
        return 0

    if failures:
        print(f"\n[simple_config] ⚠️  {len(failures)}/{total} jobs failed: {failures}")
        return 1

    print(f"\n[simple_config] ✅ {total}/{total} jobs completed.")
    return 0


# ---------------------------------------------------------------------------
# LoRA subcommands: lora add | list | show | remove
# ---------------------------------------------------------------------------


def _lora_list() -> int:
    """Print a tabular list of all registered LoRAs."""
    loras = load_loras()
    if not loras:
        print("(no LoRAs registered — run: python simple_config.py lora add ...)")
        return 0
    col_name = max(len("NAME"), max(len(n) for n in loras))
    col_desc = max(len("DESCRIPTION"), max(len(e.get("description", "")) for e in loras.values()))
    col_desc = min(col_desc, 50)
    header = f"{'NAME':<{col_name}}  {'DESCRIPTION':<{col_desc}}  {'MODELS':<8}  {'WEIGHT'}"
    print(header)
    print("-" * len(header))
    for name, entry in sorted(loras.items()):
        models = ",".join(entry.get("compatible_models", []))
        desc = entry.get("description", "")
        if len(desc) > col_desc:
            desc = desc[: col_desc - 3] + "..."
        weight = entry.get("default_weight", "?")
        print(f"{name:<{col_name}}  {desc:<{col_desc}}  {models:<8}  {weight}")
    return 0


def _lora_show(name: str) -> int:
    """Print full metadata for one registered LoRA."""
    loras = load_loras()
    if name not in loras:
        print(f"[error] LoRA '{name}' not found. Run: python simple_config.py lora list", file=sys.stderr)
        return 1
    entry = loras[name]
    trigger_words = entry.get("trigger_words", [])
    tw_display = ", ".join(trigger_words) if trigger_words else "(none)"
    style_tokens = entry.get("style_tokens", "") or "(none)"
    print(f"Name:              {name}")
    print(f"Model ID:          {entry.get('model_id', '')}")
    print(f"Default weight:    {entry.get('default_weight', '')}")
    print(f"Compatible models: {', '.join(entry.get('compatible_models', []))}")
    print(f"Trigger words:     {tw_display}")
    print(f"Guidance delta:    {entry.get('guidance_delta', 0)}")
    print(f"Style tokens:      {style_tokens}")
    print(f"Description:       {entry.get('description', '')}")
    return 0


def _lora_add_cmd(argv: list[str]) -> int:
    """CLI handler for: simple_config.py lora add <name> --id ... --weight ... --models ..."""
    import argparse as _ap

    parser = _ap.ArgumentParser(prog="simple_config.py lora add", add_help=True)
    parser.add_argument("name", help="Friendly registry name for the LoRA")
    parser.add_argument("--id", required=True, dest="model_id", help="HuggingFace model ID (author/repo)")
    parser.add_argument("--weight", required=True, help="Default weight: light/medium/strong or float")
    parser.add_argument("--models", required=True, nargs="+", dest="compatible_models", help="Compatible base models: sdxl flux sd3")
    parser.add_argument("--triggers", nargs="+", default=[], dest="trigger_words", help="Required trigger words/phrases")
    parser.add_argument("--description", default="", help="One-line description of the visual effect")
    args = parser.parse_args(argv)

    try:
        weight = resolve_lora_weight(args.weight)
    except ValueError as exc:
        print(f"[error] {exc}", file=sys.stderr)
        return 1

    entry = {
        "model_id": args.model_id,
        "default_weight": weight,
        "trigger_words": args.trigger_words,
        "compatible_models": args.compatible_models,
        "guidance_delta": 0,
        "style_tokens": "",
        "description": args.description,
    }

    # Duplicate check — prompt before overwrite (interactive only)
    data = _load_registry()
    if args.name in data["loras"]:
        if sys.stdin.isatty():
            answer = input(f"'{args.name}' already exists. Overwrite? [y/N]: ").strip().lower()
            if answer not in ("y", "yes"):
                print("Aborted.")
                return 0
        overwrite = True
    else:
        overwrite = False

    try:
        lora_add(args.name, entry, overwrite=overwrite)
    except (ValueError, KeyError) as exc:
        print(f"[error] {exc}", file=sys.stderr)
        return 1

    print(f"✅ '{args.name}' added to loras.json.")
    if args.trigger_words:
        print(f"Trigger words: {args.trigger_words}")
    print(f"Run: python simple_config.py lora show {args.name}")
    return 0


def _lora_remove_cmd(name: str) -> int:
    """CLI handler for: simple_config.py lora remove <name>."""
    loras = load_loras()
    if name not in loras:
        print(f"[error] LoRA '{name}' not found in registry.", file=sys.stderr)
        return 1
    lora_remove(name)
    print(f"✅ '{name}' removed from loras.json.")
    return 0


def _handle_lora_subcommand(argv: list[str]) -> int:
    """Route lora subcommands: add | list | show | remove."""
    if not argv:
        print(
            "Usage: python simple_config.py lora <add|list|show|remove> ...\n"
            "  lora list                           — show all registered LoRAs\n"
            "  lora show <name>                    — show full metadata\n"
            "  lora add <name> --id ... --weight ...\n"
            "  lora remove <name>",
            file=sys.stderr,
        )
        return 1
    subcmd = argv[0]
    if subcmd == "list":
        return _lora_list()
    elif subcmd == "show":
        if len(argv) < 2:
            print("[error] lora show requires a LoRA name.", file=sys.stderr)
            return 1
        return _lora_show(argv[1])
    elif subcmd == "remove":
        if len(argv) < 2:
            print("[error] lora remove requires a LoRA name.", file=sys.stderr)
            return 1
        return _lora_remove_cmd(argv[1])
    elif subcmd == "add":
        return _lora_add_cmd(argv[1:])
    else:
        print(f"[error] Unknown lora subcommand '{subcmd}'. Use add | list | show | remove.", file=sys.stderr)
        return 1


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------


def main(argv: list[str] | None = None) -> int:
    if argv is None:
        argv = sys.argv[1:]

    # Route lora subcommands before the main argparse parser
    if argv and argv[0] == "lora":
        return _handle_lora_subcommand(argv[1:])

    args = _parse_args(argv)

    if args.batch_file:
        return run_batch(args)
    return run_single(args)


if __name__ == "__main__":
    sys.exit(main())

